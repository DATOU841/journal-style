#!/usr/bin/env python3
"""Build a journal-style MinerU/mu core pack from jiansuo-ruku fulltext sidecars.

This tool is a handoff normalizer. It reads only already-produced fulltext
sidecars from 检索入库: fulltext-index.json, per-item manifest.json, and the
corresponding non-empty full.md. It does not call CNKI, Zotero, PDF tooling,
MinerU, RAG, vector stores, or Wenheng backend APIs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from journal_style_runtime import now_iso

SCHEMA = "journal_style_mu_fulltext_core_pack_v1"
DEFAULT_OUTPUT = "03-analysis/fulltext-layer/mu-fulltext-core-pack.json"
DEFAULT_STRUCTURE_SUMMARY_OUTPUT = "03-analysis/fulltext-layer/mu-fulltext-structure-summary.json"
REQUIRED_STRUCTURE = ("section_tree", "paragraph_sequence", "reference_list")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build mu-fulltext-core-pack.json from fulltext sidecars.")
    parser.add_argument("--task-dir", type=Path, default=None)
    parser.add_argument("--sidecar-dir", type=Path, default=None, help="Path to 025-rag-import/fulltext.")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--structure-summary-output", type=Path, default=None)
    parser.add_argument("--target-journal", default="江汉论坛")
    parser.add_argument("--source-skill", default="检索入库")
    parser.add_argument("--min-ready", type=int, default=10)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def load_json_any(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def first_present(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in re.split(r"[;；,，、]", text) if part.strip()]


def normalize_authors(value: Any) -> list[str]:
    authors = normalize_list(value)
    if len(authors) == 1:
        compact = authors[0]
        if re.fullmatch(r"[\u4e00-\u9fff]{4,12}", compact):
            # Common CNKI OCR pattern: two-character Chinese names are joined.
            pairs = [compact[i:i + 2] for i in range(0, len(compact), 2)]
            if all(len(item) == 2 for item in pairs):
                return pairs
    return authors


def sidecar_id(row: dict[str, Any]) -> str:
    return str(first_present(row, "stable_id", "source_id", "paper_id", "zotero_key", "id") or "")


def record_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("items", "records", "papers", "sources"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def load_metadata_records(task_dir: Path, sidecar_dir: Path) -> list[dict[str, Any]]:
    candidates = [
        sidecar_dir.parent.parent / "025-import-queue.json",
        sidecar_dir.parent.parent / "cnki-stage2-queue.json",
        sidecar_dir.parent.parent / "stage2-import-readiness.json",
        task_dir / "025-import-queue.json",
        task_dir / "cnki-stage2-queue.json",
    ]
    candidates.extend(sorted(task_dir.glob("tmp/cnki/*/025-import-queue.json")))
    candidates.extend(sorted(task_dir.glob("tmp/cnki/*/cnki-stage2-queue.json")))
    records: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()
    for path in candidates:
        path = path.resolve()
        if path in seen_paths or not path.is_file():
            continue
        seen_paths.add(path)
        try:
            for row in record_list(load_json_any(path)):
                row = dict(row)
                row["_metadata_source_path"] = str(path)
                records.append(row)
        except Exception:
            continue
    return records


def normalize_key(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "", str(value or "")).lower()


def build_metadata_lookup(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in records:
        keys = [
            row.get("item_key"),
            row.get("paper_id"),
            row.get("zotero_key"),
            row.get("source_id"),
            row.get("id"),
            row.get("title"),
        ]
        for key in keys:
            norm = normalize_key(key)
            if norm and norm not in lookup:
                lookup[norm] = row
    return lookup


def match_metadata(row: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        row.get("paper_id"),
        row.get("source_id"),
        row.get("zotero_key"),
        row.get("stable_id"),
        row.get("title"),
        row.get("display_title"),
    ]
    for candidate in candidates:
        norm = normalize_key(candidate)
        if norm in lookup:
            return lookup[norm]
        for key, value in lookup.items():
            if norm and (norm.startswith(key) or key.startswith(norm)):
                return value
    return {}


def resolve_task_dir(args: argparse.Namespace, output: Path | None) -> Path:
    if args.task_dir:
        return args.task_dir.expanduser().resolve()
    if output and output.parent.as_posix().endswith("03-analysis/fulltext-layer"):
        return output.parent.parent.parent.resolve()
    return Path.cwd().resolve()


def resolve_sidecar_dir(task_dir: Path, args: argparse.Namespace) -> Path:
    if args.sidecar_dir:
        return args.sidecar_dir.expanduser().resolve()
    return task_dir / "025-rag-import" / "fulltext"


def resolve_full_md_path(sidecar_dir: Path, pointer: str, stable_id: str) -> Path:
    candidates: list[Path] = []
    if pointer:
        raw = Path(pointer)
        if raw.is_absolute():
            candidates.append(raw)
        else:
            parts = raw.parts
            if "fulltext" in parts:
                idx = parts.index("fulltext")
                candidates.append(sidecar_dir.joinpath(*parts[idx + 1:]))
            candidates.append(sidecar_dir / raw)
            candidates.append(sidecar_dir.parent.parent / raw)
    if stable_id:
        candidates.append(sidecar_dir / stable_id / "full.md")
    for path in candidates:
        if path.is_file():
            return path.resolve()
    return candidates[0].resolve() if candidates else (sidecar_dir / stable_id / "full.md").resolve()


def load_sidecar_manifest(sidecar_dir: Path, row: dict[str, Any]) -> dict[str, Any]:
    stable_id = sidecar_id(row)
    if not stable_id:
        return {}
    path = sidecar_dir / stable_id / "manifest.json"
    if not path.is_file():
        return {}
    try:
        return load_json(path)
    except Exception:
        return {}


def normalize_section_tree(value: Any, title: str) -> list[dict[str, Any]]:
    if isinstance(value, list) and value:
        out = []
        for index, item in enumerate(value, 1):
            if isinstance(item, dict):
                out.append({
                    "index": item.get("index") or index,
                    "title": str(first_present(item, "title", "heading", "name") or title or f"section-{index}"),
                    "level": int(item.get("level") or 1),
                    "subsection_count": int(item.get("subsection_count") or 0),
                })
        if out:
            return out
    return [{"index": 1, "title": title or "正文", "level": 1, "subsection_count": 0}]


def normalize_paragraph_sequence(value: Any, text: str, title: str) -> list[dict[str, Any]]:
    if isinstance(value, list) and value:
        out = []
        for index, item in enumerate(value, 1):
            if isinstance(item, dict):
                char_count = int(item.get("char_count") or 0)
                out.append({
                    "index": item.get("index") or index,
                    "heading": str(first_present(item, "heading", "section", "title") or title or ""),
                    "char_count": char_count,
                    "sha256": str(item.get("sha256") or ""),
                })
        if out:
            return out
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    return [
        {
            "index": index,
            "heading": title or "",
            "char_count": len(paragraph),
            "sha256": sha256_text(paragraph),
        }
        for index, paragraph in enumerate(paragraphs, 1)
    ]


def normalize_reference_list(value: Any, fulltext: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    if isinstance(value, list):
        for index, item in enumerate(value, 1):
            if isinstance(item, dict):
                raw = str(first_present(item, "raw", "text", "reference", "title") or "").strip()
                if not raw and item:
                    raw = " ".join(str(v).strip() for v in item.values() if str(v).strip())[:300]
                if raw:
                    refs.append({
                        "index": item.get("index") or index,
                        "raw": raw,
                        "year": item.get("year"),
                        "lang": item.get("lang") or infer_lang(raw),
                        "is_self_journal": bool(item.get("is_self_journal")),
                        "source": item.get("source") or "sidecar_manifest",
                    })
            elif str(item).strip():
                raw = str(item).strip()
                refs.append({"index": index, "raw": raw, "year": extract_year(raw), "lang": infer_lang(raw), "is_self_journal": False, "source": "sidecar_manifest"})
    if refs:
        return refs
    return derive_references_from_tail(fulltext)


def infer_lang(raw: str) -> str:
    return "en" if re.search(r"[A-Za-z]{4,}", raw) and not re.search(r"[\u4e00-\u9fff]", raw) else "zh"


def extract_year(raw: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", raw)
    return int(match.group(0)) if match else None


def derive_references_from_tail(fulltext: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in fulltext.splitlines() if line.strip()]
    tail = lines[-80:]
    refs = []
    for line in tail:
        if line.startswith("#"):
            continue
        if line.startswith("作者简介") or line.startswith("(责任编辑") or line.startswith("（责任编辑"):
            continue
        has_bibliographic_marker = bool(re.search(r"《[^》]{2,}》|出版社|第\d+期|University Press|Press,|\d{4}年", line))
        has_note_prefix = bool(re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩0-9]+", line))
        if len(line) >= 8 and (has_bibliographic_marker or has_note_prefix):
            refs.append({
                "index": len(refs) + 1,
                "raw": line,
                "year": extract_year(line),
                "lang": infer_lang(line),
                "is_self_journal": "江汉论坛" in line,
                "source": "derived_from_full_md_tail",
            })
    return refs


def extract_front_matter(fulltext: str) -> dict[str, Any]:
    lines = [line.strip() for line in fulltext.splitlines() if line.strip()]
    title = lines[0].lstrip("#").strip() if lines else ""
    author = lines[1] if len(lines) > 1 and not lines[1].startswith("摘要") else ""
    abstract = ""
    keywords: list[str] = []
    for line in lines[:12]:
        if line.startswith("摘要"):
            abstract = re.sub(r"^摘要[:：]?", "", line).strip()
        if line.startswith("关键词"):
            keywords = normalize_list(re.sub(r"^关键词[:：]?", "", line).strip())
    return {"title": title, "authors": normalize_authors(author), "abstract": abstract, "keywords": keywords}


def build_article(sidecar_dir: Path, row: dict[str, Any], metadata_lookup: dict[str, dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    manifest = load_sidecar_manifest(sidecar_dir, row)
    metadata = match_metadata({**row, **manifest}, metadata_lookup)
    merged = {**metadata, **row, **manifest}
    stable_id = sidecar_id(merged)
    full_md_path = resolve_full_md_path(sidecar_dir, str(merged.get("full_md_path") or ""), stable_id)
    detail = {"article_id": stable_id, "full_md_path": str(full_md_path), "ready": False, "problems": []}
    if not full_md_path.is_file():
        detail["problems"].append("full.md missing")
        return None, detail
    fulltext = full_md_path.read_text(encoding="utf-8", errors="ignore")
    if not fulltext.strip():
        detail["problems"].append("full.md empty")
        return None, detail
    front = extract_front_matter(fulltext)
    title = str(first_present(merged, "title", "display_title") or front["title"] or stable_id)
    authors = normalize_authors(first_present(merged, "authors", "author", "creator", "creators") or front["authors"])
    section_tree = normalize_section_tree(merged.get("section_tree"), title)
    paragraphs = normalize_paragraph_sequence(merged.get("paragraph_sequence"), fulltext, title)
    refs = normalize_reference_list(merged.get("reference_list"), fulltext)
    missing = []
    if not section_tree:
        missing.append("section_tree")
    if not paragraphs:
        missing.append("paragraph_sequence")
    if not refs:
        missing.append("reference_list")
    if missing:
        detail["problems"].append("missing required structure: " + ", ".join(missing))
        return None, detail
    article = {
        "article_id": stable_id,
        "title": title,
        "authors": authors or normalize_authors(metadata.get("author")) or ["未识别"],
        "year": first_present(merged, "year", "publish_year") or "",
        "column": first_present(merged, "column", "section", "partition") or "艺术美学相关",
        "mu_fulltext": fulltext,
        "fulltext_sha256": sha256_text(fulltext),
        "core_library_joined": True,
        "abstract": str(first_present(merged, "abstract") or front["abstract"] or ""),
        "keywords": normalize_list(first_present(merged, "keywords") or front["keywords"]),
        "section_tree": section_tree,
        "paragraph_sequence": paragraphs,
        "notes": {
            "type": "inline_or_tail_notes",
            "count": len(re.findall(r"[①②③④⑤⑥⑦⑧⑨⑩]", fulltext)),
            "content_types": ["citation", "bibliographic_note"],
        },
        "reference_list": refs,
        "page_range": first_present(merged, "page_range", "pages"),
        "char_count_total": len(fulltext),
        "provenance": {
            "source_ledger": "025-rag-import/fulltext/fulltext-index.json",
            "source_manifest": f"025-rag-import/fulltext/{stable_id}/manifest.json",
            "source_full_md": str(merged.get("full_md_path") or ""),
            "metadata_source": str(metadata.get("_metadata_source_path") or ""),
            "extraction_method": "MinerU",
            "mu_version": str(first_present(merged, "parser_version", "model_version", "parse_mode") or "pipeline"),
        },
    }
    detail["ready"] = True
    detail["reference_count"] = len(refs)
    detail["structure_counts"] = {
        "section_tree": len(section_tree),
        "paragraph_sequence": len(paragraphs),
        "reference_list": len(refs),
    }
    detail["reference_sources"] = sorted({str(item.get("source") or "") for item in refs if isinstance(item, dict) and item.get("source")})
    detail["fulltext_sha256"] = article["fulltext_sha256"]
    detail["title"] = title
    return article, detail


def build_structure_summary(output: Path, payload: dict[str, Any], details: list[dict[str, Any]]) -> dict[str, Any]:
    articles = []
    for detail in details:
        if not detail.get("ready"):
            continue
        counts = detail.get("structure_counts") or {}
        articles.append({
            "article_id": detail.get("article_id"),
            "title": detail.get("title") or "",
            "ready": True,
            "structure_counts": {
                "section_tree": int(counts.get("section_tree") or 0),
                "paragraph_sequence": int(counts.get("paragraph_sequence") or 0),
                "reference_list": int(counts.get("reference_list") or 0),
            },
            "reference_sources": detail.get("reference_sources") or [],
            "fulltext_sha256": detail.get("fulltext_sha256") or "",
        })
    return {
        "schema": "journal_style_mu_fulltext_structure_summary_v1",
        "source_pack": str(output),
        "source_sidecar_dir": payload.get("source_sidecar_dir") or "",
        "created_at": payload.get("created_at") or now_iso(),
        "article_count": len(articles),
        "rule": "Structure counts only. This file intentionally excludes mu_fulltext body, paragraph text, RAG chunks, vectors, and secrets.",
        "articles": articles,
    }


def main() -> int:
    args = parse_args()
    output = args.output.expanduser().resolve() if args.output else None
    task_dir = resolve_task_dir(args, output)
    sidecar_dir = resolve_sidecar_dir(task_dir, args)
    output = output if output else task_dir / DEFAULT_OUTPUT
    structure_summary_output = (
        args.structure_summary_output.expanduser().resolve()
        if args.structure_summary_output
        else task_dir / DEFAULT_STRUCTURE_SUMMARY_OUTPUT
    )
    index_path = sidecar_dir / "fulltext-index.json"
    if not index_path.is_file():
        raise SystemExit(f"fulltext-index.json missing: {index_path}")
    index = load_json(index_path)
    records = index.get("items") or []
    metadata_records = load_metadata_records(task_dir, sidecar_dir)
    metadata_lookup = build_metadata_lookup(metadata_records)
    articles = []
    details = []
    for row in records:
        if not isinstance(row, dict):
            continue
        article, detail = build_article(sidecar_dir, row, metadata_lookup)
        details.append(detail)
        if article:
            articles.append(article)
    payload = {
        "schema": SCHEMA,
        "target_journal": args.target_journal,
        "source_skill": args.source_skill,
        "mu_processing_required": True,
        "mu_processor": "MinerU",
        "ordinary_rag_is_not_substitute": True,
        "full_mode_required_structure_fields": list(REQUIRED_STRUCTURE),
        "source_sidecar_dir": str(sidecar_dir),
        "source_index": str(index_path),
        "created_at": now_iso(),
        "articles": articles,
        "build_summary": {
            "source_item_count": len(records),
            "metadata_record_count": len(metadata_records),
            "ready_article_count": len(articles),
            "min_ready": args.min_ready,
            "not_ready": [item for item in details if not item.get("ready")],
            "rule": "Only existing jiansuo-ruku fulltext sidecars were consumed; no retrieval, PDF parsing, MinerU run, RAG query, vector read, or backend write was performed.",
        },
    }
    write_json(output, payload)
    write_json(structure_summary_output, build_structure_summary(output, payload, details))
    ok = len(articles) >= args.min_ready
    print(json.dumps({
        "ok": ok,
        "output": str(output),
        "structure_summary_output": str(structure_summary_output),
        "source_item_count": len(records),
        "ready_article_count": len(articles),
        "not_ready_count": len(records) - len(articles),
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
