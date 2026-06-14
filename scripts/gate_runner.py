#!/usr/bin/env python3
"""P2: gate-runner with sha chain.

Gates may only be produced here, never hand-written. The verdict embeds the
sha256 of the real on-disk artifact it judged, plus a generator marker. The
runner re-checks gate.input_sha == current artifact sha before consuming a
gate, so a stale/forged artifact cannot pass behind a previously-good verdict.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from journal_style_runtime import (
    GENERATOR_MARKER,
    ReleaseIntegrityError,
    assert_release_integrity,
    integrity_failure_payload,
    now_iso,
    record_integrity_failure,
    sha256_artifact,
)

SCRIPTS_DIR = Path(__file__).resolve().parent
RUN_STAGE_GATES = SCRIPTS_DIR / "run_stage_gates.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a journal-style gate and emit a sha-chained verdict.")
    parser.add_argument("--gate", required=True)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--output", default="", help="Where to write the gate verdict JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Fail-closed release integrity guard: a gate verdict produced by a drifted
    # gate_runner / run_stage_gates must never be trusted. Refuse to emit one.
    try:
        assert_release_integrity()
    except ReleaseIntegrityError as exc:
        record_integrity_failure(args.task_dir, "gate_runner", exc)
        print(json.dumps(integrity_failure_payload(exc, "gate_runner", args.task_dir),
                         ensure_ascii=False, indent=2))
        return 3

    input_path = args.input.expanduser().resolve()
    if not input_path.exists():
        verdict = {
            "gate": args.gate,
            "verdict": "NO_GO",
            "problems": [f"gate input missing: {input_path}"],
            "warnings": [],
            "details": {},
        }
    else:
        proc = subprocess.run(
            [sys.executable, str(RUN_STAGE_GATES), "--gate", args.gate, "--input", str(input_path)],
            capture_output=True, text=True,
        )
        try:
            verdict = json.loads(proc.stdout)
        except json.JSONDecodeError:
            verdict = {
                "gate": args.gate,
                "verdict": "NO_GO",
                "problems": ["gate logic did not return valid JSON", proc.stderr.strip()[:400]],
                "warnings": [],
                "details": {},
            }

    # sha chain: bind the verdict to the exact bytes judged.
    input_sha = sha256_artifact(input_path) if input_path.exists() else None
    verdict["_chain"] = {
        "generator": GENERATOR_MARKER,
        "produced_at": now_iso(),
        "input_path": str(input_path),
        "input_sha256": input_sha,
        "_rule": "runner must re-verify input_sha256 against the live artifact before consuming this verdict; hand-written gates lack a valid generator+sha and are rejected.",
    }

    text = json.dumps(verdict, ensure_ascii=False, indent=2)
    if args.output:
        out_path = Path(args.output).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if verdict.get("verdict") in {"PASS", "DEGRADED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
