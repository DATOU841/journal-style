#!/usr/bin/env python3
"""Validate journal-style Wenheng status JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ALLOWED_STATUS = {"pending", "partial", "complete", "failed"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
ALLOWED_ACTION = {
    "unknown",
    "submit",
    "revise_then_submit",
    "supplement_then_decide",
    "change_journal",
    "do_not_submit",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate wenheng-center-status.json.")
    parser.add_argument("--input", required=True, help="Path to wenheng-center-status.json")
    return parser.parse_args()


def check(required: bool, message: str, problems: list[str]) -> None:
    if not required:
        problems.append(message)


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    problems: list[str] = []

    check(data.get("schema") == "journal_style_wenheng_status_v1", "schema mismatch", problems)
    check(data.get("skill_id") == "journal-style", "skill_id mismatch", problems)
    check(data.get("journal", {}).get("identity_status") in ALLOWED_STATUS, "invalid journal.identity_status", problems)

    pipeline = data.get("pipeline_status", {})
    for key in ["official_check", "title_intake", "topic_library", "pdf_check", "rag_import", "analysis", "fit_evaluation"]:
        check(pipeline.get(key) in ALLOWED_STATUS, f"invalid pipeline_status.{key}", problems)

    metrics = data.get("metrics", {})
    check(metrics.get("confidence") in ALLOWED_CONFIDENCE, "invalid metrics.confidence", problems)

    decision = data.get("decision", {})
    check(decision.get("recommended_action") in ALLOWED_ACTION, "invalid decision.recommended_action", problems)

    required_top = ["schema", "skill_id", "journal", "input", "data_assets", "pipeline_status", "metrics", "decision", "handoff", "updated_at"]
    for key in required_top:
        check(key in data, f"missing top-level key: {key}", problems)

    result = {"ok": not problems, "problems": problems}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())

