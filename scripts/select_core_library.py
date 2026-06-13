#!/usr/bin/env python3
"""Select a 25%-40% core library from screened journal metadata."""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select core library for fulltext journal-style analysis.")
    parser.add_argument("--input", required=True, help="CSV/JSON/JSONL screened metadata.")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", default="")
    parser.add_argument("--topic-keywords", default="")
    parser.add_argument("--target-ratio", type=float, default=0.30)
    parser.add_argument("--min-ratio", type=float, default=0.25)
    parser.add_argument("--max-ratio", type=float, default=0.40)
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
    for key in ["kept_titles_redacted_metadata", "items", "rows", "records", "titles"]:
        if isinstance(data.get(key), list):
            return data[key]
    raise SystemExit(f"unsupported input JSON shape: {path}")


def text_of(row: dict[str, Any], *keys: str) -> str:
    return " ".join(str(row.get(key) or "") for key in keys)


def truthy(row: dict[str, Any], *keys: str) -> bool:
    yes = {"1", "true", "yes", "有", "ready", "success", "done", "ok"}
    return any(str(row.get(key) or "").strip().lower() in yes for key in keys)


def bounded(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_row(row: dict[str, Any], topic_terms: list[str], years: set[str], sections: set[str]) -> tuple[dict[str, float], list[str]]:
    haystack = text_of(row, "title", "abstract", "keywords", "section", "column", "material_type", "method_type")
    tags: list[str] = []
    topic_hits = sum(1 for term in topic_terms if term and term in haystack)
    topic_score = 1.0 if topic_hits else 0.35 if any(term in haystack for term in ["书法", "书论", "碑帖", "书画", "艺术史", "美术史"]) else 0.15
    if topic_hits:
        tags.append("topic_keyword_match")
    section_text = text_of(row, "section", "column")
    column_score = 0.8 if any(term in section_text for term in ["专题", "古代", "理论", "书", "美术史"]) else 0.45
    material_text = text_of(row, "material_type", "method_type", "abstract", "keywords")
    method_score = 0.8 if any(term in material_text for term in ["文献", "图像", "碑帖", "档案", "考辨", "比较", "文本"]) else 0.4
    theory_score = 0.85 if any(term in haystack for term in ["理论", "美学", "观念", "艺术史", "书论", "接受"]) else 0.35
    fulltext_score = 1.0 if truthy(row, "pdf_ready", "rag_ready", "ready_for_import") or row.get("item_key") else 0.25
    if fulltext_score >= 1.0:
        tags.append("fulltext_or_receipt_ready")
    year = str(row.get("year") or "")
    section = str(row.get("section") or row.get("column") or "")
    representation_score = 0.55
    if year and year in years:
        representation_score += 0.2
    if section and section in sections:
        representation_score += 0.2
    scores = {
        "topic_similarity": bounded(topic_score),
        "column_similarity": bounded(column_score),
        "material_method_similarity": bounded(method_score),
        "theory_art_history_relevance": bounded(theory_score),
        "fulltext_availability": bounded(fulltext_score),
        "year_column_representation": bounded(representation_score),
    }
    weights = {
        "topic_similarity": 0.25,
        "column_similarity": 0.15,
        "material_method_similarity": 0.15,
        "theory_art_history_relevance": 0.15,
        "fulltext_availability": 0.15,
        "year_column_representation": 0.15,
    }
    scores["total"] = round(sum(scores[key] * weights[key] for key in weights), 4)
    return scores, tags


def redacted(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": str(row.get("title") or ""),
        "item_key": str(row.get("item_key") or ""),
        "year": str(row.get("year") or ""),
        "section": str(row.get("section") or row.get("column") or ""),
    }


def write_md(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Core Library Selection",
        "",
        f"- Screened count: {payload['screened_count']}",
        f"- Selected count: {len(payload['selected'])}",
        f"- Ratio: {payload['ratio']}",
        f"- Verdict: {payload['verdict']}",
        "",
        "Core library is selected by multi-factor metadata scoring, not by PDF availability alone.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    rows = load_rows(Path(args.input).expanduser())
    topic_terms = [item.strip() for item in args.topic_keywords.split(",") if item.strip()]
    total = len(rows)
    if total == 0:
        raise SystemExit("empty screened metadata")
    target_ratio = max(args.min_ratio, min(args.target_ratio, args.max_ratio))
    selected_count = max(1, math.ceil(total * target_ratio))
    min_count = math.ceil(total * args.min_ratio)
    max_count = math.floor(total * args.max_ratio)
    selected_count = max(min_count, min(selected_count, max_count))
    years = {str(row.get("year") or "") for row in rows if row.get("year")}
    sections = {str(row.get("section") or row.get("column") or "") for row in rows if row.get("section") or row.get("column")}

    scored = []
    for index, row in enumerate(rows):
        scores, tags = score_row(row, topic_terms, years, sections)
        scored.append((scores["total"], index, row, scores, tags))
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected_rows = scored[:selected_count]
    rejected_rows = scored[selected_count:]

    selected = []
    for rank, (_, _, row, scores, tags) in enumerate(selected_rows, 1):
        entry = redacted(row)
        entry.update({"rank": rank, "selected": True, "scores": scores, "total": scores["total"], "coverage_tags": tags})
        selected.append(entry)
    rejected = []
    for _, _, row, scores, _ in rejected_rows:
        entry = redacted(row)
        if scores["fulltext_availability"] < 0.5 and scores["topic_similarity"] >= 0.8:
            reason = "pending_fulltext_only_candidate"
        else:
            reason = "below_core_library_threshold"
        entry.update({"selected": False, "scores": scores, "total": scores["total"], "reason": reason})
        rejected.append(entry)

    ratio = round(len(selected) / total, 4)
    verdict = "PASS" if args.min_ratio <= ratio <= args.max_ratio and all(item.get("reason") for item in rejected) else "NO_GO"
    payload = {
        "schema": "journal_style_core_library_ledger_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "screened_count": total,
        "target_ratio": target_ratio,
        "ratio": ratio,
        "selected": selected,
        "rejected": rejected,
        "verdict": verdict,
        "redaction": "Only metadata scores and redacted identifiers are written; no fulltext, PDF content, RAG chunks, vector data, Zotero DB, keys, tokens, or cookies.",
    }
    output_json = Path(args.output_json)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.output_md:
        write_md(Path(args.output_md), payload)
    print(json.dumps({"status": "ok", "output": str(output_json), "selected": len(selected), "ratio": ratio}, ensure_ascii=False))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
