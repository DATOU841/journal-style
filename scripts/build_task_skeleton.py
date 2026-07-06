#!/usr/bin/env python3
"""Create a journal-style task skeleton and initial task-state.json."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from wenheng_native import WenhengNativeError, production_required, validate_binding_receipt


DEFAULT_DIRS = [
    "00-intake",
    "00-official",
    "01-title-intake",
    "015-title-screening",
    "02-topic-library",
    "02b-core-library",
    "025-rag-import",
    "03-analysis",
    "03-analysis/metadata-layer",
    "03-analysis/fulltext-layer",
    "04-fit-evaluation",
    "05-handoff",
    "06-gates",
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
    parser.add_argument("--run-mode", choices=["full"], default="full", help="Formal task run mode. journal-style production tasks are full-depth only.")
    parser.add_argument("--force", action="store_true", help="Overwrite task-state.json if present.")
    parser.add_argument("--allow-legacy-debug", action="store_true", help="Allow skeleton creation without Wenheng binding for offline debugging only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task_dir = Path(args.task_dir).expanduser().resolve()
    task_dir.mkdir(parents=True, exist_ok=True)
    production = production_required() or not args.allow_legacy_debug
    try:
        binding = validate_binding_receipt(task_dir, production=production)
    except WenhengNativeError as exc:
        raise SystemExit(str(exc))

    for rel in DEFAULT_DIRS:
        (task_dir / rel).mkdir(parents=True, exist_ok=True)

    topic_keywords = [item.strip() for item in args.topic_keywords.split(",") if item.strip()]
    state_path = task_dir / "task-state.json"
    if state_path.exists() and not args.force:
        raise SystemExit(f"task-state.json already exists: {state_path}")

    payload = {
        "skill_id": "journal-style",
        "task_id": args.task_id,
        "wenheng_native": {
            "required": production,
            "validated": bool(binding.get("native")),
            "wenheng_task_id": binding.get("wenheng_task_id", ""),
            "production_evidence_allowed": bool(binding.get("production_evidence_allowed")),
        },
        "run_mode": args.run_mode,
        "requested_mode": args.run_mode,
        "journal_name": args.journal_name,
        "journal_identity_status": "pending",
        "title_intake_status": "pending",
        "zotero_status": "pending",
        "rag_status": "pending",
        "metadata_analysis_status": "pending",
        "fulltext_analysis_status": "pending",
        "overall_journal_style_status": "blocked",
        "completion_label": "METADATA_ONLY_NOT_FULLTEXT_READY",
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

    # Non-mirror init receipt: this is the artifact step01 "produces". task-state.json
    # is a runner-written read-only mirror, so it must NOT be step01's produced
    # artifact (otherwise the runner would auto-satisfy step01 with its own mirror).
    init_receipt = {
        "schema": "journal_style_task_init_v1",
        "skill_id": "journal-style",
        "task_id": args.task_id,
        "wenheng_native": payload["wenheng_native"],
        "run_mode": args.run_mode,
        "journal_name": args.journal_name,
        "input": payload["input"],
        "created_at": payload["updated_at"],
        "_rule": "Authored by build_task_skeleton at init; never a state mirror.",
    }
    (task_dir / "00-intake").mkdir(parents=True, exist_ok=True)
    (task_dir / "00-intake" / "task-init.json").write_text(
        json.dumps(init_receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    wenheng_path = task_dir / "05-handoff" / "wenheng-center-status.json"
    if not wenheng_path.exists() or args.force:
        wenheng_payload = {
            "schema": "journal_style_wenheng_status_v1",
            "skill_id": "journal-style",
            "task_id": args.task_id,
            "wenheng_native": payload["wenheng_native"],
            "style_memory_not_applicable_reason": binding.get("style_memory_not_applicable_reason", ""),
            "run_mode": args.run_mode,
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
                "title_screening": "pending",
                "topic_library": "pending",
                "zotero_pdf_rag": "pending",
                "metadata_analysis": "pending",
                "core_library_selection": "pending",
                "fulltext_analysis": "blocked",
                "submission_operations": "pending",
                "fit_evaluation": "pending",
                "overall_journal_style": "blocked",
            },
            "analysis_layers": {
                "metadata_layer_status": "pending",
                "fulltext_layer_status": "blocked",
                "completion_label": "METADATA_ONLY_NOT_FULLTEXT_READY",
                "fulltext_evidence": {
                    "core_library_count": 0,
                    "fulltext_sample_count": 0,
                    "rag_available_rate": 0.0,
                    "pdf_coverage_rate": 0.0,
                },
            },
            "metrics": {
                "journal_title_count": 0,
                "topic_library_count": 0,
                "pdf_count": 0,
                "rag_doc_count": 0,
                "fit_score": None,
                "sample_coverage_rate": 0.0,
                "data_quality_grade": "low",
                "evidence_strength": "weak",
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
