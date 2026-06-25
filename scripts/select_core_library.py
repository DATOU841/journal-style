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
    parser.add_argument("--sidecar-manifest", default="", help="Optional 0.2.11 sidecar manifest for role/fulltext tags.")
    parser.add_argument("--source-role-register", default="", help="Optional raw source-role-register.json.")
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


def normalized(value: Any) -> str:
    return "".join(str(value or "").lower().split())


def list_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("sources", "items", "records", "rows", "entries"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [str(value)] if str(value) else []


def load_json_if_present(path_text: str) -> Any:
    if not path_text:
        return None
    path = Path(path_text).expanduser()
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_sidecar_context(sidecar_manifest: str, source_role_register: str) -> dict[str, Any]:
    context: dict[str, Any] = {
        "roles_by_title": {},
        "roles_by_id": {},
        "fulltext_titles": set(),
        "fulltext_ids": set(),
        "active": False,
        "sources": [],
    }
    manifest = load_json_if_present(sidecar_manifest)
    if isinstance(manifest, dict):
        summary = manifest.get("source_role_summary") or {}
        for row in summary.get("sources") or []:
            add_role_record(context, row)
        fulltext_index = manifest.get("fulltext_index") or {}
        for item in fulltext_index.get("items") or []:
            if item.get("fulltext_missing"):
                continue
            title_key = normalized(item.get("title") or item.get("manifest_title"))
            if title_key:
                context["fulltext_titles"].add(title_key)
            for key in ("stable_id", "source_id"):
                ident = normalized(item.get(key))
                if ident:
                    context["fulltext_ids"].add(ident)
    raw_register = load_json_if_present(source_role_register)
    for row in list_records(raw_register):
        add_role_record(context, row)
    context["active"] = bool(context["roles_by_title"] or context["roles_by_id"] or context["fulltext_titles"] or context["fulltext_ids"])
    return context


def add_role_record(context: dict[str, Any], row: dict[str, Any]) -> None:
    roles = as_list(row.get("roles") or row.get("consumption_role") or row.get("source_role") or row.get("role"))
    tags = as_list(row.get("tags")) + as_list(row.get("bucket_tags")) + as_list(row.get("role_tags")) + roles
    record = {
        "source_id": str(row.get("source_id") or ""),
        "stable_id": str(row.get("stable_id") or row.get("source_id") or ""),
        "title": str(row.get("title") or ""),
        "roles": roles,
        "tags": sorted(set(tags)),
        "priority": row.get("priority"),
        "gap_id": str(row.get("gap_id") or ""),
        "source_need": str(row.get("source_need") or ""),
    }
    if record["title"]:
        context["roles_by_title"][normalized(record["title"])] = record
    for key in ("source_id", "stable_id"):
        ident = normalized(record.get(key))
        if ident:
            context["roles_by_id"][ident] = record
    context["sources"].append(record)


def sidecar_match(row: dict[str, Any], context: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    title_key = normalized(row.get("title"))
    ids = [normalized(row.get(key)) for key in ("item_key", "source_id", "stable_id", "record_id")]
    record = context["roles_by_title"].get(title_key)
    if record is None:
        record = next((context["roles_by_id"].get(ident) for ident in ids if ident in context["roles_by_id"]), None)
    fulltext_available = title_key in context["fulltext_titles"] or any(ident in context["fulltext_ids"] for ident in ids)
    return record, fulltext_available


def apply_sidecar_context(
    row: dict[str, Any],
    scores: dict[str, float],
    tags: list[str],
    context: dict[str, Any],
) -> tuple[dict[str, float], list[str], dict[str, Any] | None]:
    if not context.get("active"):
        return scores, tags, None
    record, fulltext_available = sidecar_match(row, context)
    evidence: dict[str, Any] = {}
    sidecar_tags: set[str] = set()
    boost = 0.0
    if record:
        role_tags = set(as_list(record.get("tags")) + as_list(record.get("roles")))
        sidecar_tags.update(f"source_role:{tag}" for tag in sorted(role_tags) if tag)
        if role_tags.intersection({"same_journal", "same_column", "same_topic", "target_journal_ecosystem"}):
            boost += 0.03
        evidence = {
            "source_id": record.get("source_id"),
            "stable_id": record.get("stable_id"),
            "roles": record.get("roles") or [],
            "tags": record.get("tags") or [],
            "gap_id": record.get("gap_id") or "",
            "source_need": record.get("source_need") or "",
        }
    if fulltext_available:
        boost += 0.02
        sidecar_tags.add("sidecar_fulltext_index_available")
    if not evidence and not fulltext_available:
        return scores, tags, None
    updated_scores = dict(scores)
    if boost:
        updated_scores["sidecar_role_boost"] = round(boost, 4)
        updated_scores["total"] = round(bounded(float(updated_scores["total"]) + boost), 4)
    updated_tags = list(tags)
    for tag in sorted(sidecar_tags):
        if tag not in updated_tags:
            updated_tags.append(tag)
    evidence["fulltext_index_available"] = fulltext_available
    evidence["sidecar_role_boost"] = round(boost, 4)
    evidence["evidence_layer"] = "metadata_only"
    return updated_scores, updated_tags, evidence


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
    sidecar_context = load_sidecar_context(args.sidecar_manifest, args.source_role_register)

    scored = []
    for index, row in enumerate(rows):
        scores, tags = score_row(row, topic_terms, years, sections)
        scores, tags, sidecar_evidence = apply_sidecar_context(row, scores, tags, sidecar_context)
        scored.append((scores["total"], index, row, scores, tags, sidecar_evidence))
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected_rows = scored[:selected_count]
    rejected_rows = scored[selected_count:]

    selected = []
    for rank, (_, _, row, scores, tags, sidecar_evidence) in enumerate(selected_rows, 1):
        entry = redacted(row)
        entry.update({"rank": rank, "selected": True, "scores": scores, "total": scores["total"], "coverage_tags": tags})
        if sidecar_evidence:
            entry["source_role_tags"] = [tag for tag in tags if tag.startswith("source_role:")]
            entry["sidecar_role_evidence"] = sidecar_evidence
        selected.append(entry)
    rejected = []
    for _, _, row, scores, tags, sidecar_evidence in rejected_rows:
        entry = redacted(row)
        if scores["fulltext_availability"] < 0.5 and scores["topic_similarity"] >= 0.8:
            reason = "pending_fulltext_only_candidate"
        else:
            reason = "below_core_library_threshold"
        entry.update({"selected": False, "scores": scores, "total": scores["total"], "reason": reason})
        if sidecar_evidence:
            entry["coverage_tags"] = tags
            entry["source_role_tags"] = [tag for tag in tags if tag.startswith("source_role:")]
            entry["sidecar_role_evidence"] = sidecar_evidence
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
        "sidecar_context": {
            "active": bool(sidecar_context.get("active")),
            "source": "best_effort_optional",
            "rule": "source-role sidecar only adds metadata tags and small boosts; it does not change the 25%-40% core-library gate or create fulltext style evidence.",
        },
        "redaction": "Only metadata scores and redacted identifiers are written; no fulltext, PDF content, RAG chunks, vector data, Zotero DB, keys, tokens, or cookies.",
    }
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.output_md:
        write_md(Path(args.output_md), payload)
    print(json.dumps({"status": "ok", "output": str(output_json), "selected": len(selected), "ratio": ratio}, ensure_ascii=False))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
