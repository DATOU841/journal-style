#!/usr/bin/env python3
"""P6: resume / re-run compatibility mode.

A resume-manifest declares which steps a prior run already satisfied (e.g. the
CNKI/Zotero/PDF/RAG download+ingest already happened and should not be re-run).
But "declared satisfied" is never trusted on its word:

- A step may be marked satisfied ONLY if it has a governing gate AND that gate
  passes now with a valid sha chain over the live prior-run artifacts.
- Steps with no gate (identity, title intake, fit scoring, etc.) can NEVER be
  resume-skipped (P6 ironclad rule); they must be executed in order.

This closes the RC1 (skip) / RC2 (fake closure) reopening that a naive
"declare and skip" resume would create.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from journal_style_runtime import (
    GATE_ID_MAP,
    load_json,
    load_state,
    load_workflow_states,
    now_iso,
    resolve_gate_input,
    write_state,
)

SCRIPTS_DIR = Path(__file__).resolve().parent
GATE_RUNNER = SCRIPTS_DIR / "gate_runner.py"

def step_index(workflow: dict) -> dict:
    return {s["id"]: s for s in workflow["steps"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="journal-style resume compatibility mode (P6).")
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--resume-manifest", required=True, type=Path)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    task_dir = args.task_dir.expanduser().resolve()
    workflow = load_workflow_states()
    steps = step_index(workflow)
    manifest = load_json(args.resume_manifest)

    declared = manifest.get("satisfied_by_prior_run", [])
    decisions = []
    accepted = []
    rejected = []

    for step_id in declared:
        step = steps.get(step_id)
        if not step:
            decisions.append({"step": step_id, "decision": "reject", "reason": "unknown step id"})
            rejected.append(step_id)
            continue
        gate = step.get("gate")
        # P6 ironclad: no gate -> never skippable
        if not gate or not step.get("resume_skippable", False):
            decisions.append({
                "step": step_id, "decision": "reject",
                "reason": "step has no governing gate or is not resume_skippable; must be executed",
            })
            rejected.append(step_id)
            continue
        gate_id = GATE_ID_MAP.get(gate)
        gate_input = resolve_gate_input(task_dir, step)
        if not gate_id or gate_input is None or not gate_input.exists():
            decisions.append({
                "step": step_id, "decision": "reject",
                "reason": f"prior-run artifact for gate '{gate}' missing: {gate_input}",
            })
            rejected.append(step_id)
            continue
        # run the gate now over the live prior-run artifact (sha-chained)
        verdict_path = task_dir / "06-gates" / f"resume-{gate}.json"
        proc = subprocess.run(
            [sys.executable, str(GATE_RUNNER), "--gate", gate_id, "--input", str(gate_input),
             "--task-dir", str(task_dir), "--output", str(verdict_path)],
            capture_output=True, text=True,
        )
        try:
            verdict = json.loads(proc.stdout)
        except json.JSONDecodeError:
            verdict = {"verdict": "NO_GO", "problems": [proc.stderr.strip()[:200]]}
        if verdict.get("verdict") in {"PASS", "DEGRADED"}:
            decisions.append({
                "step": step_id, "decision": "satisfied_by_prior_run",
                "gate": gate, "verdict": verdict.get("verdict"),
                "verdict_path": str(verdict_path),
            })
            accepted.append(step_id)
        else:
            decisions.append({
                "step": step_id, "decision": "reject",
                "reason": f"prior-run gate '{gate}' did not pass: {verdict.get('verdict')}",
                "problems": verdict.get("problems", []),
            })
            rejected.append(step_id)

    result = {
        "schema": "journal_style_resume_decision_v1",
        "task_dir": str(task_dir),
        "evaluated_at": now_iso(),
        "declared_count": len(declared),
        "accepted_satisfied": accepted,
        "rejected_must_execute": rejected,
        "decisions": decisions,
        "_rule": "satisfied requires a passing sha-chained gate over live prior-run artifacts; gateless steps never skip.",
    }

    # record into authoritative state (mirror only the resume decision; runner stays source of position)
    state = load_state(task_dir)
    state.setdefault("resume", {})
    state["resume"] = {
        "accepted_satisfied": accepted,
        "rejected_must_execute": rejected,
        "evaluated_at": result["evaluated_at"],
    }
    write_state(task_dir, state)

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).expanduser().write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if not rejected else 2


if __name__ == "__main__":
    raise SystemExit(main())
