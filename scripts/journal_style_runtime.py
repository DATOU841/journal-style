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
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = SKILL_ROOT / "config"

STAGE_GATES_PATH = CONFIG_DIR / "stage-gates.json"
FIELD_POLICY_PATH = CONFIG_DIR / "field-policy.json"
WORKFLOW_STATES_PATH = CONFIG_DIR / "workflow-states.json"
RELEASE_MANIFEST_PATH = CONFIG_DIR / "release-manifest.json"

AUTHORITATIVE_STATE_FILE = "current-run-state.json"

MANIFEST_TRACKED_CONFIG = [
    "config/workflow-states.json",
    "config/stage-gates.json",
    "config/field-policy.json",
    "config/source-profiles-schema.json",
    "config/mu-fulltext-pack-schema.json",
    "config/per-article-profile-schema.json",
    "config/aggregation-schema.json",
    "config/journal-polish-consumption-pack-schema.json",
    "config/scoring-model-schema.json",
]

MANIFEST_TRACKED_SCRIPTS = [
    "scripts/journal_style_runner.py",
    "scripts/gate_runner.py",
    "scripts/journal_style_resume.py",
    "scripts/journal_style_runtime.py",
    "scripts/wenheng_native.py",
    "scripts/journal-style-startup.py",
    "scripts/build_task_skeleton.py",
    "scripts/run_stage_gates.py",
    "scripts/task_adapter.py",
    "scripts/analyze_per_article_style.py",
    "scripts/aggregate_journal_style.py",
    "scripts/export_polish_consumption_pack.py",
    "scripts/calibrate_fit_scoring.py",
    "scripts/score_user_manuscript.py",
    "scripts/build_jiansuo_sidecar_manifest.py",
    "scripts/build_journal_style_rag_seed_plan.py",
]

OVERRIDE_ALLOWED_STEPS = {
    "step06_zotero_pdf_rag",
    "step08a_metadata_layer",
}


class ReleaseIntegrityError(RuntimeError):
    """Raised when the skill release files no longer match the manifest."""

    def __init__(self, reason: str, details: dict | None = None):
        super().__init__(reason)
        self.reason = reason
        self.details = details or {}


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


def skill_rel(path: Path) -> str:
    return Path(path).resolve().relative_to(SKILL_ROOT).as_posix()


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


def detect_runtime_mode() -> str:
    """Return git when this skill is running from a checkout, else bundle."""
    if (SKILL_ROOT / ".git").exists():
        try:
            subprocess.run(
                ["git", "-C", str(SKILL_ROOT), "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                check=True,
            )
            return "git"
        except Exception:
            pass
    return "bundle"


def git_head() -> str:
    proc = subprocess.run(
        ["git", "-C", str(SKILL_ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _manifest_expected_sha(manifest: dict, rel: str) -> str | None:
    if rel.startswith("config/"):
        return (manifest.get("config_sha256") or {}).get(rel)
    return (manifest.get("script_sha256") or {}).get(rel)


def assert_release_integrity(mode: str | None = None) -> dict:
    """Fail closed if published config/script files drift from the manifest.

    The manifest is the release-time trust anchor. We intentionally do not
    require a same-commit self-match inside the manifest: committing the manifest
    changes the commit hash. Git mode records HEAD for evidence; bundle mode uses
    the same sha checks without requiring .git.
    """
    runtime_mode = mode or detect_runtime_mode()
    if not RELEASE_MANIFEST_PATH.is_file():
        raise ReleaseIntegrityError(
            "release manifest missing",
            {"path": str(RELEASE_MANIFEST_PATH), "mode": runtime_mode},
        )
    manifest = load_json(RELEASE_MANIFEST_PATH)
    tracked = list(MANIFEST_TRACKED_CONFIG) + list(MANIFEST_TRACKED_SCRIPTS)
    missing: list[str] = []
    mismatches: list[dict] = []
    for rel in tracked:
        expected = _manifest_expected_sha(manifest, rel)
        path = SKILL_ROOT / rel
        if not expected:
            missing.append(rel)
            continue
        if not path.is_file():
            mismatches.append({"path": rel, "reason": "missing file", "expected": expected, "actual": None})
            continue
        actual = sha256_file(path)
        if actual != expected:
            mismatches.append({"path": rel, "reason": "sha mismatch", "expected": expected, "actual": actual})
    if missing or mismatches:
        raise ReleaseIntegrityError(
            "release integrity mismatch",
            {"mode": runtime_mode, "missing_manifest_entries": missing, "mismatches": mismatches},
        )
    summary = {
        "schema": "journal_style_release_integrity_v1",
        "mode": runtime_mode,
        "manifest": str(RELEASE_MANIFEST_PATH),
        "manifest_release_id": manifest.get("release_id"),
        "manifest_version": manifest.get("version"),
        "manifest_generated_from_commit": manifest.get("manifest_generated_from_commit"),
        "current_git_head": git_head() if runtime_mode == "git" else None,
        "tracked_count": len(tracked),
        "matched": True,
        "verified_at": now_iso(),
        "_rule": "config/script bytes must match config/release-manifest.json before any runner/gate/resume logic executes.",
    }
    return summary


def integrity_failure_payload(exc: ReleaseIntegrityError, entrypoint: str, task_dir: Path | None = None) -> dict:
    return {
        "schema": "journal_style_integrity_failure_v1",
        "entrypoint": entrypoint,
        "task_dir": str(task_dir) if task_dir else None,
        "reason": exc.reason,
        "details": exc.details,
        "created_at": now_iso(),
        "blocked": True,
        "_rule": "Skill config/scripts are immutable at execution time; task-local adaptation must use task-adapter-manifest.json.",
    }


def record_integrity_failure(task_dir: Path | None, entrypoint: str, exc: ReleaseIntegrityError) -> Path | None:
    if task_dir is None:
        return None
    task_dir = Path(task_dir)
    payload = integrity_failure_payload(exc, entrypoint, task_dir)
    out_dir = task_dir / "06-gates" / "h08"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"integrity-failure-{entrypoint}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        state = load_state(task_dir)
        state.setdefault("integrity_failures", [])
        state["integrity_failures"].append(payload)
        state["blocked"] = True
        state["blocked_reason"] = exc.reason
        write_state(task_dir, state)
        return out_path
    except Exception:
        return None


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
    "mu-fulltext-pack": "mu-fulltext-pack",
    "per-article-profile-complete": "per-article-profile-complete",
    "aggregation-threshold": "aggregation-threshold",
    "provenance-required": "provenance-required",
    "scoring-replay-calibrated": "scoring-replay-calibrated",
    "submission-fit-ready": "submission-fit-ready",
    "jiansuo-sidecar-safety": "jiansuo-sidecar-safety",
}


def _safe_task_path(task_dir: Path, rel: str) -> Path:
    base = Path(task_dir).resolve()
    path = (base / rel).resolve()
    if path != base and base not in path.parents:
        raise ValueError(f"task-local path escapes task_dir: {rel}")
    return path


def resolve_gate_input(task_dir, step, overrides=None):
    """Resolve the concrete artifact a step's gate must judge.

    Priority: validated task-local override -> explicit step['gate_input'] ->
    first produced .json/.jsonl -> first required input. Returns a Path or None.
    """
    task_dir = Path(task_dir)
    step_id = step.get("id")
    if overrides and step_id in overrides:
        override = overrides[step_id]
        rel = override.get("task_local_path") or override.get("input_path")
        if rel:
            return _safe_task_path(task_dir, rel)
    gi = step.get("gate_input")
    if gi:
        return _safe_task_path(task_dir, gi)
    for rel in step.get("produces", []):
        if rel.endswith(".json") or rel.endswith(".jsonl"):
            return _safe_task_path(task_dir, rel)
    for rel in step.get("requires_inputs", []):
        if rel.endswith(".json") or rel.endswith(".jsonl"):
            return _safe_task_path(task_dir, rel)
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
