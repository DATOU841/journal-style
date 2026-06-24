#!/usr/bin/env python3
"""Export journal_style_profile_v1 from the aggregation bundle for article polish."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from journal_style_runtime import (
    ReleaseIntegrityError,
    assert_release_integrity,
    integrity_failure_payload,
)

SCRIPTS_DIR = Path(__file__).resolve().parent
RUN_STAGE_GATES = SCRIPTS_DIR / "run_stage_gates.py"
DEFAULT_INPUT = "03-analysis/fulltext-layer/journal-style-aggregation-bundle.json"
DEFAULT_OUTPUT = "05-handoff/journal-polish-consumption-pack.json"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_gate(gate: str, input_path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(RUN_STAGE_GATES), "--gate", gate, "--input", str(input_path)],
        capture_output=True,
        text=True,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"verdict": "NO_GO", "problems": ["gate did not return valid JSON", proc.stderr.strip()[:400]], "warnings": []}


def find_consumption_pack(bundle: dict) -> dict | None:
    for artifact in bundle.get("artifacts") or []:
        if artifact.get("name") == "journal-polish-consumption-pack":
            payload = artifact.get("payload")
            if isinstance(payload, dict):
                return payload
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export journal-polish-consumption-pack.json from aggregation bundle.")
    parser.add_argument("--task-dir", type=Path, default=Path("."))
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        assert_release_integrity()
    except ReleaseIntegrityError as exc:
        print(json.dumps(integrity_failure_payload(exc, "export_polish_consumption_pack", args.task_dir), ensure_ascii=False, indent=2))
        return 3
    task_dir = args.task_dir.expanduser().resolve()
    input_path = (task_dir / args.input).resolve() if not Path(args.input).is_absolute() else Path(args.input).resolve()
    output_path = (task_dir / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output).resolve()
    if not input_path.exists():
        print(json.dumps({"ok": False, "reason": f"aggregation bundle missing: {input_path}"}, ensure_ascii=False, indent=2))
        return 1
    aggregation_verdict = run_gate("aggregation-threshold", input_path)
    if aggregation_verdict.get("verdict") not in {"PASS", "DEGRADED"}:
        print(json.dumps({
            "ok": False,
            "reason": "aggregation gate did not pass",
            "gate_verdict": aggregation_verdict.get("verdict"),
            "problems": aggregation_verdict.get("problems") or [],
        }, ensure_ascii=False, indent=2))
        return 1
    pack = find_consumption_pack(load_json(input_path))
    if not pack:
        print(json.dumps({"ok": False, "reason": "journal-polish-consumption-pack artifact payload missing"}, ensure_ascii=False, indent=2))
        return 1
    write_json(output_path, pack)
    provenance_verdict = run_gate("provenance-required", output_path)
    ok = provenance_verdict.get("verdict") in {"PASS", "DEGRADED"}
    print(json.dumps({
        "ok": ok,
        "output": str(output_path),
        "aggregation_gate_verdict": aggregation_verdict.get("verdict"),
        "provenance_gate_verdict": provenance_verdict.get("verdict"),
        "problems": provenance_verdict.get("problems") or [],
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
