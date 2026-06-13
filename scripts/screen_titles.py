#!/usr/bin/env python3
"""Build a title-only screening ledger for journal-style tasks.

This script only reads title metadata. It never deletes Zotero/PDF/RAG
receipts and never reads full text.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_EXCLUDE_TERMS = [
    "建筑",
    "景观",
    "产品",
    "工艺",
    "陶瓷",
    "瓷器",
    "服装",
    "家居",
    "电影",
    "漫画",
    "广告",
    "海报",
    "设计方法",
    "城镇化",
    "社区营造",
]
DEFAULT_KEEP_TERMS = [
    "艺术学",
    "艺术史",
    "艺术理论",
    "艺术教育",
    "美术史",
    "书法",
    "书论",
    "碑帖",
    "书画",
    "题跋",
    "文字",
    "图像",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create title-only screening ledger.")
    parser.add_argument("--input", required=True, help="CSV/JSON/JSONL title metadata.")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", default="")
    parser.add_argument("--topic-keywords", default="", help="Comma-separated topic keywords to keep.")
    parser.add_argument("--max-exclude-ratio", type=float, default=0.30)
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as fh:
            return [dict(row) for row in csv.DictReader(fh)]
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    for key in ["items", "rows", "titles", "records"]:
        if isinstance(data.get(key), list):
            return data[key]
    raise SystemExit(f"unsupported input JSON shape: {path}")


def text_of(row: dict[str, Any], *keys: str) -> str:
    return " ".join(str(row.get(key) or "") for key in keys)


def has_success_receipt(row: dict[str, Any]) -> bool:
    truthy = {"1", "true", "yes", "有", "ready", "success", "done", "ok"}
    for key in ["had_success_receipt", "pdf_ready", "rag_ready", "zotero_success", "receipt_status", "status"]:
        value = str(row.get(key) or "").strip().lower()
        if value in truthy:
            return True
    return bool(row.get("item_key") and str(row.get("pdf_status") or "").strip() in {"有", "ready", "success"})


def standalone_artwork_title(title: str) -> bool:
    stripped = title.strip()
    if not (stripped.startswith("《") and stripped.endswith("》")):
        return False
    inner = stripped[1:-1].strip()
    return bool(inner) and len(inner) <= 14 and not re.search(r"[：:———-]|论|研究|考|探|析|史|观|述", inner)


def classify(row: dict[str, Any], topic_terms: list[str]) -> tuple[bool, str, float]:
    title = str(row.get("title") or "").strip()
    haystack = text_of(row, "title", "abstract", "keywords", "column", "section")
    keep_terms = DEFAULT_KEEP_TERMS + topic_terms
    if any(term and term in haystack for term in keep_terms):
        return False, "kept_by_art_or_topic_term", 0.0
    if standalone_artwork_title(title):
        return True, "standalone_artwork_plate_title", 0.95
    matched_terms = [term for term in DEFAULT_EXCLUDE_TERMS if term in haystack]
    if matched_terms:
        return True, f"obvious_low_fit_domain:{','.join(matched_terms[:3])}", 0.75 + min(len(matched_terms), 3) * 0.05
    doc_type = str(row.get("doc_type") or row.get("type") or "")
    if any(term in doc_type for term in ["目录", "征稿", "启事", "书评", "会议"]):
        return True, "non_research_item", 0.9
    return False, "kept_by_default_conservative_screening", 0.0


def redacted_entry(row: dict[str, Any], reason: str, action: str, sequence: int) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "title": str(row.get("title") or ""),
        "partition": str(row.get("partition") or row.get("journal_issue") or ""),
        "section": str(row.get("section") or row.get("column") or ""),
        "reason": reason,
        "had_success_receipt": has_success_receipt(row),
        "action": action,
    }


def write_md(path: Path, payload: dict[str, Any]) -> None:
    counts = payload["counts"]
    lines = [
        "# Title Screening Ledger",
        "",
        f"- Original count: {counts['original_count']}",
        f"- Excluded count: {counts['excluded_count']}",
        f"- Kept count: {counts['kept_count']}",
        f"- Excluded with success receipt: {counts['excluded_with_success_receipt_count']}",
        "",
        "## Boundary",
        "",
        "Title-only screening. Existing Zotero/PDF/RAG receipts are never deleted.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    rows = load_rows(Path(args.input).expanduser())
    topic_terms = [item.strip() for item in args.topic_keywords.split(",") if item.strip()]
    max_excluded = math.floor(len(rows) * max(0.0, min(args.max_exclude_ratio, 0.5)))
    candidates: list[tuple[float, int, dict[str, Any], str]] = []
    kept_reason_by_index: dict[int, str] = {}
    for index, row in enumerate(rows):
        exclude, reason, score = classify(row, topic_terms)
        if exclude and not has_success_receipt(row):
            candidates.append((score, index, row, reason))
        else:
            kept_reason_by_index[index] = reason if not exclude else "kept_success_receipt_preserved"
    candidates.sort(key=lambda item: (-item[0], item[1]))
    excluded_indexes = {index for _, index, _, _ in candidates[:max_excluded]}
    reason_by_index = {index: reason for _, index, _, reason in candidates[:max_excluded]}

    excluded = []
    kept = []
    for index, row in enumerate(rows):
        if index in excluded_indexes:
            excluded.append(redacted_entry(row, reason_by_index[index], "exclude_from_analysis_only", len(excluded) + 1))
        else:
            kept.append(redacted_entry(row, kept_reason_by_index.get(index, "kept_by_ratio_limit_or_conservative_screening"), "keep_for_analysis", len(kept) + 1))

    payload = {
        "schema": "journal_style_title_screening_ledger_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "title_only",
        "policy": "Keep art studies/art education/art history/theory and topic-related records; exclude only obvious low-fit title metadata. Do not delete receipts/PDF/RAG.",
        "topic_keywords": topic_terms,
        "counts": {
            "original_count": len(rows),
            "excluded_count": len(excluded),
            "kept_count": len(kept),
            "max_exclude_ratio": args.max_exclude_ratio,
            "excluded_with_success_receipt_count": sum(1 for item in excluded if item["had_success_receipt"]),
        },
        "excluded_titles_redacted_metadata": excluded,
        "kept_titles_redacted_metadata": kept,
        "verdict": "PASS" if sum(1 for item in excluded if item["had_success_receipt"]) == 0 else "NO_GO",
        "redaction": "Only title/partition/section/reason/receipt boolean are written; no fulltext, PDF content, RAG chunks, vector data, Zotero DB, keys, tokens, or cookies.",
    }
    output_json = Path(args.output_json)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.output_md:
        write_md(Path(args.output_md), payload)
    print(json.dumps({"status": "ok", "output": str(output_json), "excluded": len(excluded), "kept": len(kept)}, ensure_ascii=False))
    return 0 if payload["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
