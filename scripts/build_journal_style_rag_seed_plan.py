#!/usr/bin/env python3
"""Build a planning-only RAG query seed plan for journal-style.

This script does not call RAG, vector stores, servers, or retrieval APIs. It
only reshapes safe query seeds from jiansuo-ruku sidecars into journal-style
analysis dimensions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from journal_style_runtime import now_iso

DIMENSION_FALLBACK_QUERIES = [
    ("title_style", "题名结构 主副标题 研究对象 问题意识"),
    ("abstract_keywords", "摘要结构 关键词 数量 研究对象 方法"),
    ("format_convention", "章节层级 注释 参考文献 格式体例"),
    ("material_method", "材料类型 方法偏好 档案 图像 文献 考辨"),
    ("argument_style", "引言 问题提出 论证节奏 结论方式"),
    ("reference_ecology", "参考文献 中外比例 近年文献 期刊内互引"),
    ("submission_operations", "投稿须知 字数 注释 参考文献 格式"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build journal-style RAG query seed plan.")
    parser.add_argument("--task-dir", type=Path, default=None)
    parser.add_argument("--sidecar-manifest", type=Path, default=None)
    parser.add_argument("--rag-query-seed-pack", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def records_from(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("query_intents", "query_seeds", "seeds", "queries", "items", "records"):
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


def first_present(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if row.get(key) not in (None, "", [], {}):
            return row.get(key)
    return None


def normalize_seed(row: dict[str, Any], index: int, source: str) -> dict[str, Any]:
    dimension = str(first_present(row, "dimension_tag", "dimension", "topic", "category") or "unspecified")
    query = str(first_present(row, "query_intent", "query", "query_text", "intent") or "")
    seed_terms = as_list(first_present(row, "seed_terms", "terms", "keywords"))
    if not seed_terms and query:
        seed_terms = [part for part in query.replace("，", " ").replace(",", " ").split() if part][:12]
    return {
        "id": f"seed-{index:03d}",
        "dimension_tag": dimension,
        "query_intent": query or " ".join(seed_terms),
        "seed_terms": seed_terms[:30],
        "source_id_refs": as_list(first_present(row, "source_id_refs", "source_ids", "source_id")),
        "gap_id_refs": as_list(first_present(row, "gap_id_refs", "gap_ids", "gap_id")),
        "seed_source": source,
        "confidence": "planning_only",
        "executed": False,
    }


def seeds_from_manifest(path: Path) -> tuple[list[dict[str, Any]], str]:
    data = load_json(path)
    summary = data.get("rag_query_seed_summary") if isinstance(data, dict) else None
    if isinstance(summary, dict) and summary.get("query_intents"):
        return records_from(summary), "jiansuo_sidecar_manifest"
    return [], "jiansuo_sidecar_manifest"


def seeds_from_pack(path: Path) -> tuple[list[dict[str, Any]], str]:
    return records_from(load_json(path)), "rag_query_seed_pack"


def fallback_seeds() -> list[dict[str, Any]]:
    return [
        {
            "dimension_tag": dimension,
            "query_intent": query,
            "seed_terms": query.split(),
            "source_id_refs": [],
            "gap_id_refs": [],
        }
        for dimension, query in DIMENSION_FALLBACK_QUERIES
    ]


def main() -> int:
    args = parse_args()
    task_dir = args.task_dir.expanduser().resolve() if args.task_dir else None
    output = args.output
    if output is None:
        if not task_dir:
            raise SystemExit("--output is required when --task-dir is not supplied")
        output = task_dir / "02-topic-library" / "journal-style-rag-query-seed-plan.json"
    output = output.expanduser().resolve()

    source = "fallback"
    raw_seeds: list[dict[str, Any]] = []
    warnings: list[str] = []
    if args.rag_query_seed_pack and args.rag_query_seed_pack.expanduser().is_file():
        raw_seeds, source = seeds_from_pack(args.rag_query_seed_pack.expanduser().resolve())
    elif args.sidecar_manifest and args.sidecar_manifest.expanduser().is_file():
        raw_seeds, source = seeds_from_manifest(args.sidecar_manifest.expanduser().resolve())
    elif task_dir:
        manifest = task_dir / "00-intake" / "jiansuo-sidecar-manifest.json"
        seed_pack = task_dir / "026-knowledge-workbench" / "rag-query-seed-pack.json"
        if seed_pack.is_file():
            raw_seeds, source = seeds_from_pack(seed_pack)
        elif manifest.is_file():
            raw_seeds, source = seeds_from_manifest(manifest)

    if not raw_seeds:
        warnings.append("sidecar query seeds absent; generated low-confidence planning fallback")
        raw_seeds = fallback_seeds()
        source = "fallback"

    seeds = [normalize_seed(row, index, source) for index, row in enumerate(raw_seeds, 1)]
    payload = {
        "schema": "journal_style_rag_query_seed_plan_v1",
        "created_at": now_iso(),
        "seed_source": source,
        "executed": False,
        "execution_scope": "planning_only_no_rag_call",
        "seed_count": len(seeds),
        "query_intents": seeds,
        "warnings": warnings,
        "redaction": "No RAG chunks, vectors, full.md body, PDF text, Zotero DB, cookies, tokens, or keys are read or written.",
        "_rule": "This plan only states what journal-style would query later; retrieval remains upstream-controlled.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "seed_count": len(seeds), "executed": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
