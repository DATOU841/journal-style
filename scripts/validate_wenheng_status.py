#!/usr/bin/env python3
"""Validate journal-style Wenheng status JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ALLOWED_STATUS = {"pending", "partial", "complete", "done", "failed", "blocked", "metadata_only"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
ALLOWED_DATA_QUALITY = {"low", "medium", "high"}
ALLOWED_EVIDENCE_STRENGTH = {"weak", "medium", "strong"}
ALLOWED_ACTION = {
    "unknown",
    "submit",
    "revise_then_submit",
    "supplement_then_decide",
    "change_journal",
    "do_not_submit",
}
ALLOWED_COMPLETION_LABEL = {"METADATA_ONLY_NOT_FULLTEXT_READY", "FULLTEXT_PARTIAL", "FULLTEXT_READY"}
READY_STATUS = {"complete", "done"}


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
    legacy_keys = ["official_check", "title_intake", "topic_library", "pdf_check", "rag_import", "analysis", "fit_evaluation"]
    split_keys = [
        "official_check",
        "title_intake",
        "title_screening",
        "topic_library",
        "zotero_pdf_rag",
        "metadata_analysis",
        "core_library_selection",
        "fulltext_analysis",
        "submission_operations",
        "fit_evaluation",
        "overall_journal_style",
    ]
    keys_to_check = split_keys if any(key in pipeline for key in split_keys) else legacy_keys
    for key in keys_to_check:
        if key in pipeline:
            check(pipeline.get(key) in ALLOWED_STATUS, f"invalid pipeline_status.{key}", problems)

    layers = data.get("analysis_layers", {})
    legacy_analysis_status = pipeline.get("analysis")
    if not layers and legacy_analysis_status in READY_STATUS:
        problems.append("legacy pipeline_status.analysis completion requires analysis_layers fulltext evidence")
    if layers:
        completion_label = layers.get("completion_label")
        check(completion_label in ALLOWED_COMPLETION_LABEL, "invalid analysis_layers.completion_label", problems)
        fulltext_status = layers.get("fulltext_layer_status") or pipeline.get("fulltext_analysis")
        metadata_status = layers.get("metadata_layer_status") or pipeline.get("metadata_analysis")
        overall = pipeline.get("overall_journal_style") or pipeline.get("analysis")
        evidence = layers.get("fulltext_evidence", {})
        try:
            fulltext_sample_count = int(evidence.get("fulltext_sample_count") or 0)
        except Exception:
            fulltext_sample_count = 0
        try:
            rag_available_rate = float(evidence.get("rag_available_rate") or 0)
        except Exception:
            rag_available_rate = 0.0
        try:
            pdf_coverage_rate = float(evidence.get("pdf_coverage_rate") or 0)
        except Exception:
            pdf_coverage_rate = 0.0
        if overall in READY_STATUS and fulltext_status not in READY_STATUS:
            problems.append("overall journal-style completion requires fulltext layer completion")
        if metadata_status in READY_STATUS and fulltext_status not in READY_STATUS and overall in READY_STATUS:
            problems.append("metadata-only analysis cannot be promoted to overall completion")
        if completion_label == "FULLTEXT_READY":
            check(fulltext_status in READY_STATUS, "FULLTEXT_READY requires fulltext_layer_status done/complete", problems)
            check(fulltext_sample_count >= 20, "FULLTEXT_READY requires at least 20 fulltext samples", problems)
            check(rag_available_rate >= 0.5, "FULLTEXT_READY requires rag_available_rate >= 0.5", problems)
            check(pdf_coverage_rate >= 0.2, "FULLTEXT_READY requires pdf_coverage_rate >= 0.2", problems)

    metrics = data.get("metrics", {})
    check(metrics.get("confidence") in ALLOWED_CONFIDENCE, "invalid metrics.confidence", problems)
    if "data_quality_grade" in metrics:
        check(metrics.get("data_quality_grade") in ALLOWED_DATA_QUALITY, "invalid metrics.data_quality_grade", problems)
    if "evidence_strength" in metrics:
        check(metrics.get("evidence_strength") in ALLOWED_EVIDENCE_STRENGTH, "invalid metrics.evidence_strength", problems)
    if "sample_coverage_rate" in metrics:
        try:
            sample_coverage_rate = float(metrics.get("sample_coverage_rate"))
            check(0.0 <= sample_coverage_rate <= 1.0, "metrics.sample_coverage_rate out of range", problems)
        except Exception:
            check(False, "invalid metrics.sample_coverage_rate", problems)

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
