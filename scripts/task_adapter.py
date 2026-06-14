#!/usr/bin/env python3
"""Task-local adapter manifest validation for journal-style.

This is the only allowed compatibility path when an existing task stores a gate
input at a non-default location. It can only remap gate_input to a task-local
artifact. It cannot change workflow contract fields or gate logic.
"""

from __future__ import annotations

import json
from pathlib import Path

from journal_style_runtime import OVERRIDE_ALLOWED_STEPS, load_json, now_iso, sha256_artifact

ADAPTER_PATH = "00-intake/task-adapter-manifest.json"
STEP0_MANIFEST = "00-intake/material-intake-manifest.json"

ALLOWED_OVERRIDE_KEYS = {
    "step",
    "step_id",
    "field",
    "task_local_path",
    "input_path",
    "input_sha256",
    "reason",
    "h08_candidate",
    "registered_in_step0",
}

FORBIDDEN_OVERRIDE_KEYS = {
    "gate",
    "next",
    "threshold",
    "thresholds",
    "resume_skippable",
    "gate_logic",
    "verdict",
}


class TaskAdapterError(RuntimeError):
    def __init__(self, reason: str, details: dict | None = None):
        super().__init__(reason)
        self.reason = reason
        self.details = details or {}


def task_path(task_dir: Path, rel: str) -> Path:
    base = Path(task_dir).resolve()
    path = (base / rel).resolve()
    if path != base and base not in path.parents:
        raise TaskAdapterError("adapter path escapes task_dir", {"path": rel})
    return path


def load_task_adapter(task_dir: Path) -> dict | None:
    path = Path(task_dir) / ADAPTER_PATH
    if not path.is_file():
        return None
    return load_json(path)


def _registered_assets(task_dir: Path) -> dict:
    path = Path(task_dir) / STEP0_MANIFEST
    if not path.is_file():
        raise TaskAdapterError("step0 material intake manifest missing", {"path": STEP0_MANIFEST})
    manifest = load_json(path)
    assets = manifest.get("registered_assets") or {}
    if not isinstance(assets, dict):
        raise TaskAdapterError("step0 registered_assets is not an object", {"path": STEP0_MANIFEST})
    return assets


def _is_registered(assets: dict, rel: str, digest: str) -> bool:
    for asset in assets.values():
        if asset.get("rel_path") == rel and asset.get("sha256") == digest:
            return True
    return False


def validate_task_adapter(
    manifest: dict | None,
    task_dir: Path,
    allowed_steps: set[str] | None = None,
) -> dict[str, dict]:
    if manifest is None:
        return {}
    if manifest.get("schema") != "journal_style_task_adapter_v1":
        raise TaskAdapterError("unexpected task adapter schema", {"schema": manifest.get("schema")})
    allowed = allowed_steps or OVERRIDE_ALLOWED_STEPS
    overrides = manifest.get("overrides") or []
    if not isinstance(overrides, list):
        raise TaskAdapterError("adapter overrides must be a list")
    registered = _registered_assets(task_dir)
    normalized: dict[str, dict] = {}
    for index, override in enumerate(overrides):
        if not isinstance(override, dict):
            raise TaskAdapterError("adapter override must be an object", {"index": index})
        keys = set(override)
        illegal = sorted((keys - ALLOWED_OVERRIDE_KEYS) | (keys & FORBIDDEN_OVERRIDE_KEYS))
        if illegal:
            raise TaskAdapterError("adapter override contains forbidden fields", {"index": index, "fields": illegal})
        step = override.get("step") or override.get("step_id")
        if step not in allowed:
            raise TaskAdapterError("adapter override step is not whitelisted", {"index": index, "step": step})
        if override.get("field") != "gate_input":
            raise TaskAdapterError("adapter override may only set gate_input", {"index": index, "field": override.get("field")})
        rel = override.get("task_local_path") or override.get("input_path")
        if not rel:
            raise TaskAdapterError("adapter override missing task_local_path", {"index": index})
        path = task_path(task_dir, rel)
        if not path.exists():
            raise TaskAdapterError("adapter input artifact missing", {"index": index, "path": rel})
        expected = override.get("input_sha256")
        actual = sha256_artifact(path)
        if actual != expected:
            raise TaskAdapterError("adapter input sha mismatch", {"index": index, "path": rel, "expected": expected, "actual": actual})
        if override.get("registered_in_step0") is not True:
            raise TaskAdapterError("adapter override not declared registered_in_step0=true", {"index": index, "path": rel})
        if not _is_registered(registered, rel, actual):
            raise TaskAdapterError("adapter input is not registered in step0 manifest", {"index": index, "path": rel, "sha256": actual})
        normalized[step] = {
            "step": step,
            "field": "gate_input",
            "task_local_path": rel,
            "input_sha256": actual,
            "reason": override.get("reason", ""),
            "validated_at": now_iso(),
        }
    return normalized


def adapter_failure_payload(exc: TaskAdapterError, task_dir: Path) -> dict:
    return {
        "schema": "journal_style_task_adapter_failure_v1",
        "task_dir": str(Path(task_dir).resolve()),
        "reason": exc.reason,
        "details": exc.details,
        "created_at": now_iso(),
        "blocked": True,
    }
