#!/usr/bin/env python3
"""Shared runtime helpers for the journal-style state-machine runner and gates.

Single source of truth for:
- loading machine-readable config (stage-gates.json, field-policy.json, workflow-states.json)
- sha256 over real on-disk artifacts (P2 sha chain)
- the authoritative state file current-run-state.json (RC0 single state source)

Read-only mirrors (task-state.json, wenheng-center-status.json) are never read for
stage position; they are written from the authoritative state, not the reverse.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = SKILL_ROOT / "config"

STAGE_GATES_PATH = CONFIG_DIR / "stage-gates.json"
FIELD_POLICY_PATH = CONFIG_DIR / "field-policy.json"
WORKFLOW_STATES_PATH = CONFIG_DIR / "workflow-states.json"

AUTHORITATIVE_STATE_FILE = "current-run-state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def load_stage_gates() -> dict:
    return load_json(STAGE_GATES_PATH)


def load_field_policy() -> dict:
    return load_json(FIELD_POLICY_PATH)


def load_workflow_states() -> dict:
    return load_json(WORKFLOW_STATES_PATH)


def sha256_file(path: Path) -> str:
    """sha256 of a real on-disk file. Raises if missing (P2: never sign a phantom)."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"cannot sha256 missing artifact: {p}")
    h = hashlib.sha256()
    with p.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_dir(path: Path) -> str:
    """Stable sha256 over a directory's file contents (sorted relative paths)."""
    p = Path(path)
    if not p.is_dir():
        raise FileNotFoundError(f"cannot sha256 missing directory: {p}")
    h = hashlib.sha256()
    for child in sorted(p.rglob("*")):
        if child.is_file():
            rel = child.relative_to(p).as_posix()
            h.update(rel.encode("utf-8"))
            h.update(sha256_file(child).encode("utf-8"))
    return h.hexdigest()


def sha256_artifact(path: Path) -> str:
    p = Path(path)
    if p.is_dir():
        return sha256_dir(p)
    return sha256_file(p)


def load_state(task_dir: Path) -> dict:
    state_path = Path(task_dir) / AUTHORITATIVE_STATE_FILE
    if not state_path.is_file():
        return {}
    return load_json(state_path)


def write_state(task_dir: Path, state: dict) -> Path:
    state["updated_at"] = now_iso()
    state_path = Path(task_dir) / AUTHORITATIVE_STATE_FILE
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return state_path


# P2: marker proving a gate JSON was produced by gate_runner, not hand-written.
# This is an auxiliary signal only; the real moat is the sha chain (gate.artifact_sha
# must equal the freshly computed sha of the on-disk artifact at consume time).
GENERATOR_MARKER = "journal-style-gate-runner/v1"


# Single source of truth for the workflow gate name -> run_stage_gates.py gate id
# mapping. Shared by the runner and the resume tool so the two cannot drift.
GATE_ID_MAP = {
    "material-intake": "material-intake",
    "zotero-pdf-rag-handoff": "jiansuo-handoff",
    "core-library-selection": "core-library",
    "abstract-metadata-ledger": "abstract-metadata-ledger",
    "no-fulltext-claim-without-rag": "fulltext-claims",
    "no-metadata-only-completion": "completion-label",
}


def resolve_gate_input(task_dir, step):
    """Resolve the concrete artifact a step's gate must judge.

    Priority: explicit step['gate_input'] -> first produced .json/.jsonl ->
    first required input. Returns a Path or None.
    """
    task_dir = Path(task_dir)
    gi = step.get("gate_input")
    if gi:
        return task_dir / gi
    for rel in step.get("produces", []):
        if rel.endswith(".json") or rel.endswith(".jsonl"):
            return task_dir / rel
    for rel in step.get("requires_inputs", []):
        if rel.endswith(".json") or rel.endswith(".jsonl"):
            return task_dir / rel
    return None


def write_state_mirrors(task_dir: Path, state: dict) -> list[Path]:
    """Write read-only mirrors derived FROM the authoritative state.

    task-state.json and wenheng-center-status.json are mirrors only. They are
    written from current-run-state.json, never read for stage position. This is
    the RC0 single-state-source guarantee made concrete.
    """
    task_dir = Path(task_dir)
    written: list[Path] = []
    mirror_note = {
        "_mirror_of": AUTHORITATIVE_STATE_FILE,
        "_authoritative": False,
        "_rule": "Read-only mirror derived from current-run-state.json. Do not edit; do not use for stage position.",
        "current_step": state.get("current_step"),
        "next_step": state.get("next_step"),
        "completion_label": state.get("completion_label"),
        "blocked": state.get("blocked"),
        "updated_at": state.get("updated_at"),
    }
    for name in ("task-state.json", "05-handoff/wenheng-center-status.json"):
        path = task_dir / name
        if not path.parent.exists():
            continue
        existing = {}
        if path.is_file():
            try:
                existing = load_json(path)
            except Exception:
                existing = {}
        existing.update(mirror_note)
        path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written
