#!/usr/bin/env python3
"""Create a journal-style task skeleton and initial task-state.json."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DIRS = [
    "00-official",
    "01-title-intake",
    "02-topic-library",
    "025-rag-import",
    "03-analysis",
    "04-fit-evaluation",
    "05-handoff",
    "scripts",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a journal-style task skeleton.")
    parser.add_argument("--task-dir", required=True, help="Task directory to create.")
    parser.add_argument("--journal-name", required=True, help="Target journal name.")
    parser.add_argument("--task-id", default="", help="Optional task identifier.")
    parser.add_argument("--topic-keywords", default="", help="Comma-separated topic keywords.")
    parser.add_argument("--target-year-range", default="", help="Optional target year range.")
    parser.add_argument("--manuscript-path", default="", help="Optional manuscript path.")
    parser.add_argument("--submission-title", default="", help="Optional submission title.")
    parser.add_argument("--force", action="store_true", help="Overwrite task-state.json if present.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task_dir = Path(args.task_dir).expanduser().resolve()
    task_dir.mkdir(parents=True, exist_ok=True)

    for rel in DEFAULT_DIRS:
        (task_dir / rel).mkdir(parents=True, exist_ok=True)

    topic_keywords = [item.strip() for item in args.topic_keywords.split(",") if item.strip()]
    state_path = task_dir / "task-state.json"
    if state_path.exists() and not args.force:
        raise SystemExit(f"task-state.json already exists: {state_path}")

    payload = {
        "skill_id": "journal-style",
        "task_id": args.task_id,
        "journal_name": args.journal_name,
        "journal_identity_status": "pending",
        "title_intake_status": "pending",
        "zotero_status": "pending",
        "rag_status": "pending",
        "analysis_status": "pending",
        "fit_score": None,
        "recommended_action": "unknown",
        "handoff_targets": [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "submission_title": args.submission_title,
            "manuscript_path": args.manuscript_path,
            "topic_keywords": topic_keywords,
            "target_year_range": args.target_year_range,
        },
    }
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    wenheng_path = task_dir / "05-handoff" / "wenheng-center-status.json"
    if not wenheng_path.exists() or args.force:
        wenheng_payload = {
            "schema": "journal_style_wenheng_status_v1",
            "skill_id": "journal-style",
            "task_id": args.task_id,
            "task_name": args.journal_name,
            "journal": {
                "name": args.journal_name,
                "issn": "",
                "cn": "",
                "official_url": "",
                "submission_url": "",
                "identity_status": "pending",
            },
            "input": {
                "submission_title": args.submission_title,
                "submission_abstract_path": "",
                "manuscript_path": args.manuscript_path,
                "topic_keywords": topic_keywords,
                "target_year_range": args.target_year_range,
            },
            "data_assets": {
                "title_list_path": "",
                "topic_library_path": "",
                "zotero_collections": [],
                "kb_ids": [],
                "official_evidence_path": "",
            },
            "pipeline_status": {
                "official_check": "pending",
                "title_intake": "pending",
                "topic_library": "pending",
                "pdf_check": "pending",
                "rag_import": "pending",
                "analysis": "pending",
                "fit_evaluation": "pending",
            },
            "metrics": {
                "journal_title_count": 0,
                "topic_library_count": 0,
                "pdf_count": 0,
                "rag_doc_count": 0,
                "fit_score": None,
                "confidence": "low",
            },
            "decision": {
                "recommended_action": "unknown",
                "primary_risks": [],
                "required_fixes": [],
                "recommended_target_journals": [],
            },
            "handoff": {
                "to_jiansuo_ruku": "",
                "to_zhengwen_xiezuo": "",
                "to_article_polish": "",
                "to_reference_footnote": "",
            },
            "updated_at": payload["updated_at"],
        }
        wenheng_path.write_text(json.dumps(wenheng_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(task_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
