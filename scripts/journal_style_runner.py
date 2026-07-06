#!/usr/bin/env python3
"""P1: journal-style state-machine runner with single authoritative state source.

RC0 fix: current-run-state.json is the only authority. task-state.json and
wenheng-center-status.json are written as read-only mirrors, never read for
stage position.

No-skip guarantee: a step can only be marked completed when its governing gate
(from config/workflow-states.json) returns PASS/DEGRADED. Trust is NOT placed in
a stored gate verdict file: the runner re-runs the gate logic over the live
artifact at consume time (via gate_runner.py), so a hand-written or stale gate
verdict cannot let a bad artifact through. The stored 06-gates/<gate>.json is a
cache/receipt only. Steps with no gate cannot be auto-satisfied by resume (P6
rule lives in resume tool).

The runner does not perform CNKI/Zotero/PDF/RAG work (D1): it only orchestrates
local analysis steps and gate checks, and stops fail-closed on the first
unsatisfied step instead of compressing multiple steps into one action.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from journal_style_runtime import (
    GATE_ID_MAP,
    ReleaseIntegrityError,
    assert_release_integrity,
    integrity_failure_payload,
    load_state,
    load_workflow_states,
    now_iso,
    record_integrity_failure,
    resolve_gate_input,
    write_state,
    write_state_mirrors,
)
from task_adapter import (
    TaskAdapterError,
    adapter_failure_payload,
    load_task_adapter,
    validate_task_adapter,
)
from wenheng_native import WenhengNativeError, production_required, validate_binding_receipt

SCRIPTS_DIR = Path(__file__).resolve().parent
GATE_RUNNER = SCRIPTS_DIR / "gate_runner.py"


def rerun_gate(task_dir: Path, step: dict, overrides=None) -> tuple[bool, str]:
    """Re-run the step's governing gate over the LIVE artifact, right now.

    This is the moat: we never trust a stored verdict's marker/sha alone. We
    re-execute the gate logic so a forged or stale verdict cannot pass a bad
    artifact. The fresh verdict is also written to 06-gates/<gate>.json as a
    sha-chained receipt by gate_runner.
    """
    gate = step.get("gate")
    if not gate:
        return True, "no gate"
    gate_id = GATE_ID_MAP.get(gate)
    if not gate_id:
        return False, f"unknown gate '{gate}' (no GATE_ID_MAP entry)"
    gate_input = resolve_gate_input(task_dir, step, overrides)
    if gate_input is None:
        return False, f"cannot resolve gate input for step '{step.get('id')}'"
    if not gate_input.exists():
        return False, f"gate input artifact missing: {gate_input}"
    verdict_path = task_dir / "06-gates" / f"{gate}.json"
    proc = subprocess.run(
        [sys.executable, str(GATE_RUNNER), "--gate", gate_id, "--input", str(gate_input),
         "--task-dir", str(task_dir), "--output", str(verdict_path)],
        capture_output=True, text=True,
    )
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False, f"gate '{gate}' produced no valid JSON: {proc.stderr.strip()[:200]}"
    v = verdict.get("verdict")
    if v in {"PASS", "DEGRADED"}:
        return True, v
    return False, f"gate '{gate}' verdict {v}: {'; '.join(verdict.get('problems', []))[:200]}"


def step_satisfied(task_dir: Path, step: dict, overrides=None) -> tuple[bool, str]:
    for rel in step.get("requires_inputs", []):
        if not (task_dir / rel).exists():
            return False, f"missing required input: {rel}"
    # produced artifacts must exist on disk
    for rel in step.get("produces", []):
        if not (task_dir / rel).exists():
            return False, f"missing produced artifact: {rel}"
    # governing gate (if any) must pass when re-run NOW over the live artifact
    ok, detail = rerun_gate(task_dir, step, overrides)
    if not ok:
        return False, detail
    return True, "satisfied"


def resolve_run_mode(state: dict, requested_mode: str = "") -> str:
    """Resolve every formal or legacy task to the single full-depth path.

    Older tasks may still carry light/standard in their mirrors. Those fields
    are treated as historical request labels only; they must not re-open the
    metadata-only completion path.
    """
    return "full"


def workflow_steps_for_mode(workflow: dict, run_mode: str) -> tuple[list[dict], list[str]]:
    mode_cfg = (workflow.get("run_modes") or {}).get("full") or {}
    enabled_paths = set(mode_cfg.get("paths") or ["common", "metadata", "fulltext", "scoring"])
    steps = []
    skipped = []
    for step in workflow["steps"]:
        paths = set(step.get("paths") or ["common"])
        if paths & enabled_paths:
            steps.append(step)
        else:
            skipped.append(step["id"])
    return steps, skipped


def _entry_satisfied(step: dict, completed: set[str]) -> tuple[bool, str]:
    for condition in step.get("entry") or []:
        if condition == "task_skeleton_exists":
            continue
        if condition.endswith(".satisfied"):
            dep = condition.rsplit(".", 1)[0]
            if dep not in completed:
                return False, f"entry condition not satisfied: {condition}"
    return True, "entry satisfied"


def validate_step_order(steps: list[dict]) -> tuple[bool, str]:
    seen: set[str] = set()
    ids = {step.get("id") for step in steps}
    for step in steps:
        for condition in step.get("entry") or []:
            if condition == "task_skeleton_exists":
                continue
            if condition.endswith(".satisfied"):
                dep = condition.rsplit(".", 1)[0]
                if dep in ids and dep not in seen:
                    return False, f"workflow step '{step.get('id')}' appears before entry dependency '{dep}'"
        seen.add(step.get("id"))
    return True, "workflow order ok"


def compute_position(task_dir: Path, workflow: dict, overrides=None, run_mode: str = "full") -> dict:
    steps, skipped = workflow_steps_for_mode(workflow, run_mode)
    position = {
        "current_step": None,
        "next_step": None,
        "completed": [],
        "skipped_by_mode": skipped,
        "run_mode": run_mode,
        "blocked_reason": None,
    }
    order_ok, order_detail = validate_step_order(steps)
    if not order_ok:
        position["current_step"] = "workflow_config_error"
        position["next_step"] = None
        position["blocked_reason"] = order_detail
        return position
    for step in steps:
        entry_ok, entry_detail = _entry_satisfied(step, set(position["completed"]))
        if not entry_ok:
            position["current_step"] = step["id"]
            position["next_step"] = step["id"]
            position["blocked_reason"] = entry_detail
            break
        ok, detail = step_satisfied(task_dir, step, overrides)
        if ok:
            position["completed"].append(step["id"])
            continue
        position["current_step"] = step["id"]
        position["next_step"] = step["id"]
        position["blocked_reason"] = detail
        break
    else:
        position["current_step"] = "completed"
        position["next_step"] = None
    return position


def main() -> int:
    parser = argparse.ArgumentParser(description="journal-style state-machine runner.")
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--mode", choices=["full"], default="", help="Run mode. Formal journal-style tasks are full-depth only.")
    parser.add_argument("--status", action="store_true", help="Report current position only.")
    args = parser.parse_args()

    task_dir = args.task_dir.expanduser().resolve()

    try:
        native_required = production_required() or os.getenv("WENHENG_ALLOW_LEGACY_FLOW") != "1"
        wenheng_binding = validate_binding_receipt(task_dir, production=native_required)
    except WenhengNativeError as exc:
        print(json.dumps({
            "status": "NO_GO",
            "reason": str(exc),
            "required_startup": "scripts/journal-style-startup.py",
            "intake_request": "00-intake/wenheng-intake-request.json",
        }, ensure_ascii=False, indent=2))
        return 5

    # Fail-closed release integrity guard: refuse to run if published config or
    # state-machine scripts drift from config/release-manifest.json. This is the
    # core immutability fix: a task window can no longer edit workflow-states.json
    # or gate code to force progress.
    try:
        integrity = assert_release_integrity()
    except ReleaseIntegrityError as exc:
        record_integrity_failure(task_dir, "runner", exc)
        print(json.dumps(integrity_failure_payload(exc, "runner", task_dir),
                         ensure_ascii=False, indent=2))
        return 3

    # Controlled task-local override (gate_input path only, whitelisted steps).
    try:
        overrides = validate_task_adapter(load_task_adapter(task_dir), task_dir)
    except TaskAdapterError as exc:
        payload = adapter_failure_payload(exc, task_dir)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 4

    state = load_state(task_dir)
    run_mode = resolve_run_mode(state, args.mode)
    workflow = load_workflow_states()
    position = compute_position(task_dir, workflow, overrides, run_mode=run_mode)

    state.update({
        "schema": "journal_style_current_run_state_v1",
        "skill_id": "journal-style",
        "authoritative": True,
        "single_state_source": "current-run-state.json",
        "run_mode": run_mode,
        "demoted_mirrors": ["task-state.json", "wenheng-center-status.json"],
        "release_integrity": integrity,
        "wenheng_native": {
            "required": native_required,
            "validated": bool(wenheng_binding.get("native")),
            "wenheng_task_id": wenheng_binding.get("wenheng_task_id", ""),
            "production_evidence_allowed": bool(wenheng_binding.get("production_evidence_allowed")),
        },
        "applied_overrides": list(overrides.values()),
        "position": position,
        "current_step": position["current_step"],
        "next_step": position["next_step"],
        "blocked": bool(position["blocked_reason"]),
        "evaluated_at": now_iso(),
    })
    write_state(task_dir, state)
    write_state_mirrors(task_dir, state)

    print(json.dumps({
        "task_dir": str(task_dir),
        "run_mode": run_mode,
        "current_step": position["current_step"],
        "next_step": position["next_step"],
        "completed_count": len(position["completed"]),
        "skipped_by_mode": position["skipped_by_mode"],
        "blocked_reason": position["blocked_reason"],
        "applied_overrides": [o["step"] for o in overrides.values()],
        "wenheng_native_validated": bool(wenheng_binding.get("native")),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
