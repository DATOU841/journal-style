#!/usr/bin/env python3
"""Build a safe, metadata-only manifest for jiansuo-ruku 0.2.11 sidecars.

The script never opens PDF files, Zotero DBs, RAG chunks, vectors, or full.md
body files. full_md_path is recorded only as a pointer.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from journal_style_runtime import load_field_policy, now_iso, sha256_file

SCHEMA = "journal_style_jiansuo_sidecar_manifest_v1"

SIDECAR_PATHS = {
    "zotero_reference_full_bibliography": "02-kb-builder/zotero-reference-full-bibliography.md",
    "fulltext_index": "025-rag-import/fulltext/fulltext-index.json",
    "mineru_job_ledger": "025-rag-import/mineru-job-ledger.jsonl",
    "downstream_consumption_manifest": "026-knowledge-workbench/downstream-consumption-manifest.json",
    "source_role_register": "026-knowledge-workbench/source-role-register.json",
    "rag_query_seed_pack": "026-knowledge-workbench/rag-query-seed-pack.json",
    "gap_ledger": "026-knowledge-workbench/gap-ledger.json",
}

MASTER_CANDIDATES = [
    "02-kb-builder/zotero-reference-master.md",
    "025-rag-import/zotero-reference-master.md",
    "zotero-reference-master.md",
]

FORBIDDEN_CONTENT_KEYS = {
    "full_md",
    "full_md_content",
    "full_md_text",
    "mu_fulltext",
    "fulltext_body",
    "rag_chunk",
    "chunk_text",
    "vector",
    "embedding",
    "embedding_raw",
    "paragraph",
    "sentence",
    "copyable_text",
    "正文",
    "full_zip_url",
}

ALLOWED_POINTER_KEYS = {"full_md_path"}

SECRET_PATTERNS = [
    re.compile(r"--api-key(?:=|\s+)[A-Za-z0-9_\-]{12,}", re.I),
    re.compile(r"ZOTERO_API_KEY=[A-Za-z0-9_\-]{12,}", re.I),
    re.compile(r"\b(token|cookie|secret|password|bearer)\b\s*[:=]\s*[A-Za-z0-9_\-]{12,}", re.I),
    re.compile(r"\bapi[_\-]?key\b\s*[:=]\s*[A-Za-z0-9_\-]{12,}", re.I),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build safe jiansuo-ruku sidecar manifest.")
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path; defaults to 00-intake/jiansuo-sidecar-manifest.json under task-dir.",
    )
    return parser.parse_args()


def relpath(task_dir: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(task_dir.resolve()).as_posix()
    except ValueError:
        return str(path)


def safe_load_json(path: Path, warnings: list[str], safety: dict[str, Any]) -> Any:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"{path}: invalid JSON: {exc}")
        return None
    safety["scanned_json_files"].append(str(path))
    scan_forbidden(data, f"${path.name}", safety)
    return data


def load_policy_forbidden_keys() -> set[str]:
    try:
        policy = load_field_policy()
    except Exception:
        policy = {}
    deny = (policy.get("credential_denylist") or {}) if isinstance(policy, dict) else {}
    keys = {str(key).lower() for key in deny.get("forbidden_keys_exact", [])}
    keys.update(FORBIDDEN_CONTENT_KEYS)
    return keys


def scan_text_for_secrets(text: str, label: str, safety: dict[str, Any]) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            safety["contains_secrets"] = True
            safety["problems"].append(f"{label}: secret-like value matched {pattern.pattern}")


def scan_forbidden(obj: Any, where: str, safety: dict[str, Any]) -> None:
    forbidden = safety["forbidden_keys"]
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_text = str(key)
            key_lc = key_text.lower()
            child = f"{where}.{key_text}"
            if key_lc in forbidden and key_lc not in ALLOWED_POINTER_KEYS:
                safety["problems"].append(f"{child}: forbidden sidecar key")
                if key_lc in {"chunk_text", "rag_chunk"}:
                    safety["contains_rag_chunks"] = True
                if key_lc in {"vector", "embedding", "embedding_raw"}:
                    safety["contains_vectors"] = True
                if key_lc in FORBIDDEN_CONTENT_KEYS - {"chunk_text", "rag_chunk", "vector", "embedding", "embedding_raw"}:
                    safety["contains_fulltext_body"] = True
            scan_forbidden(value, child, safety)
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            scan_forbidden(item, f"{where}[{index}]", safety)
    elif isinstance(obj, str):
        scan_text_for_secrets(obj, where, safety)


def artifact_status(task_dir: Path, name: str, rel: str) -> dict[str, Any]:
    path = task_dir / rel
    item = {
        "rel_path": rel,
        "exists": path.exists(),
        "is_dir": path.is_dir() if path.exists() else False,
    }
    if path.is_file():
        item.update({"sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    elif path.is_dir():
        item.update({"file_count": len([p for p in path.rglob("*") if p.is_file()])})
    item["name"] = name
    return item


def bibliography_entries(path: Path) -> list[str]:
    entries: list[str] = []
    if not path.is_file():
        return entries
    text = path.read_text(encoding="utf-8", errors="ignore")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("<!--"):
            continue
        line = re.sub(r"^[-*]\s+", "", line)
        line = re.sub(r"^\d+[.)、]\s*", "", line)
        if len(line) >= 6:
            entries.append(line[:200])
    return entries


def build_bibliography_scope(task_dir: Path, sidecars: dict[str, Any], safety: dict[str, Any]) -> dict[str, Any]:
    full_path = task_dir / SIDECAR_PATHS["zotero_reference_full_bibliography"]
    master_path = next((task_dir / rel for rel in MASTER_CANDIDATES if (task_dir / rel).is_file()), None)
    full_entries = bibliography_entries(full_path)
    master_entries = bibliography_entries(master_path) if master_path else []
    for index, entry in enumerate(full_entries[:200], 1):
        scan_text_for_secrets(entry, f"$zotero_reference_full_bibliography[{index}]", safety)
    for index, entry in enumerate(master_entries[:200], 1):
        scan_text_for_secrets(entry, f"$zotero_reference_master[{index}]", safety)
    full_titles = {entry for entry in full_entries}
    master_titles = {entry for entry in master_entries}
    missing_from_master = sorted(full_titles - master_titles)[:50]
    coverage = len(master_entries) / len(full_entries) if full_entries else None
    scope = {
        "full_bibliography": {
            "rel_path": SIDECAR_PATHS["zotero_reference_full_bibliography"],
            "exists": full_path.is_file(),
            "entry_count": len(full_entries),
        },
        "master_bibliography": {
            "rel_path": relpath(task_dir, master_path) if master_path else "",
            "exists": bool(master_path),
            "entry_count": len(master_entries),
            "source": "direct" if master_path else "absent",
        },
        "formal_coverage_rate": round(coverage, 4) if coverage is not None else None,
        "unmatched_full_entries_sample": missing_from_master,
        "evidence_layer": "metadata_only",
        "rule": "full bibliography is the task-wide candidate scope; master is the formal ingested scope when available.",
    }
    sidecars["bibliography_scope_coverage"] = {
        "exists": bool(full_entries or master_entries),
        "derived": True,
    }
    return scope


def summarize_downstream_manifest(task_dir: Path, safety: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    path = task_dir / SIDECAR_PATHS["downstream_consumption_manifest"]
    if not path.is_file():
        return {"exists": False, "declared_artifact_count": 0}
    data = safe_load_json(path, warnings, safety)
    records = list_records(data)
    declared = []
    for row in records:
        declared.append({
            "name": str(first_present(row, "name", "artifact", "id") or ""),
            "rel_path": str(first_present(row, "rel_path", "path") or ""),
            "sha256": str(first_present(row, "sha256", "checksum") or ""),
            "ready": bool(first_present(row, "ready", "available")),
        })
    return {
        "exists": True,
        "rel_path": SIDECAR_PATHS["downstream_consumption_manifest"],
        "sha256": sha256_file(path),
        "declared_artifact_count": len(records),
        "declared_artifacts": declared[:100],
        "rule": "Declaration is diagnostic only; journal-style still verifies real task-local files.",
    }


def list_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("sources", "items", "records", "rows", "entries", "gaps", "query_seeds", "seeds", "queries"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def first_present(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if row.get(key) not in (None, "", [], {}):
            return row.get(key)
    return None


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [str(value)] if str(value) else []


def summarize_source_roles(task_dir: Path, safety: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    path = task_dir / SIDECAR_PATHS["source_role_register"]
    if not path.is_file():
        return {"exists": False, "record_count": 0, "role_counts": {}, "tag_counts": {}, "sources": []}
    data = safe_load_json(path, warnings, safety)
    records = list_records(data)
    role_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    sources = []
    for row in records:
        roles = as_list(first_present(row, "consumption_role", "source_role", "role"))
        tags = as_list(row.get("bucket_tags")) + as_list(row.get("role_tags")) + roles
        for role in roles:
            role_counts[role] += 1
        for tag in tags:
            tag_counts[tag] += 1
        sources.append({
            "source_id": str(first_present(row, "source_id", "stable_id", "id") or ""),
            "stable_id": str(first_present(row, "stable_id", "source_id", "id") or ""),
            "title": str(row.get("title") or ""),
            "year": str(row.get("year") or ""),
            "journal": str(row.get("journal") or row.get("source") or ""),
            "roles": roles,
            "tags": tags,
            "priority": row.get("priority"),
            "gap_id": str(row.get("gap_id") or ""),
            "source_need": str(row.get("source_need") or ""),
        })
    return {
        "exists": True,
        "rel_path": SIDECAR_PATHS["source_role_register"],
        "sha256": sha256_file(path),
        "record_count": len(records),
        "role_counts": dict(sorted(role_counts.items())),
        "tag_counts": dict(sorted(tag_counts.items())),
        "sources": sources,
        "evidence_layer": "metadata_only",
    }


def summarize_rag_seed_pack(task_dir: Path, safety: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    path = task_dir / SIDECAR_PATHS["rag_query_seed_pack"]
    if not path.is_file():
        return {"exists": False, "seed_count": 0, "dimension_counts": {}, "query_intents": []}
    data = safe_load_json(path, warnings, safety)
    records = list_records(data)
    dimension_counts: Counter[str] = Counter()
    intents = []
    for row in records:
        dimension = str(first_present(row, "dimension_tag", "dimension", "topic", "category") or "unspecified")
        query = str(first_present(row, "query", "query_text", "intent", "query_intent") or "")
        seed_terms = as_list(first_present(row, "seed_terms", "terms", "keywords"))
        dimension_counts[dimension] += 1
        intents.append({
            "dimension_tag": dimension,
            "query_intent": query[:160],
            "seed_terms": seed_terms[:20],
            "source_id_refs": as_list(first_present(row, "source_id_refs", "source_ids", "source_id")),
            "gap_id_refs": as_list(first_present(row, "gap_id_refs", "gap_ids", "gap_id")),
        })
    return {
        "exists": True,
        "rel_path": SIDECAR_PATHS["rag_query_seed_pack"],
        "sha256": sha256_file(path),
        "seed_count": len(records),
        "dimension_counts": dict(sorted(dimension_counts.items())),
        "query_intents": intents,
        "executed": False,
    }


def summarize_gap_ledger(task_dir: Path, safety: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    path = task_dir / SIDECAR_PATHS["gap_ledger"]
    if not path.is_file():
        return {"exists": False, "gap_count": 0, "category_counts": {}, "severity_counts": {}}
    data = safe_load_json(path, warnings, safety)
    records = list_records(data)
    categories: Counter[str] = Counter()
    severities: Counter[str] = Counter()
    gaps = []
    for row in records:
        category = str(first_present(row, "category", "gap_type", "type") or "unspecified")
        severity = str(first_present(row, "severity", "priority") or "unspecified")
        categories[category] += 1
        severities[severity] += 1
        gaps.append({
            "gap_id": str(first_present(row, "gap_id", "id") or ""),
            "category": category,
            "severity": severity,
            "status": str(row.get("status") or ""),
            "source_need": str(row.get("source_need") or row.get("need") or ""),
        })
    return {
        "exists": True,
        "rel_path": SIDECAR_PATHS["gap_ledger"],
        "sha256": sha256_file(path),
        "gap_count": len(records),
        "category_counts": dict(sorted(categories.items())),
        "severity_counts": dict(sorted(severities.items())),
        "gaps": gaps,
    }


def summarize_fulltext_index(task_dir: Path, safety: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    path = task_dir / SIDECAR_PATHS["fulltext_index"]
    if not path.is_file():
        return {"exists": False, "item_count": 0, "items": []}
    data = safe_load_json(path, warnings, safety)
    records = list_records(data)
    items = []
    vectorized = 0
    available = 0
    for row in records:
        stable_id = str(first_present(row, "stable_id", "source_id", "id") or "")
        title = str(first_present(row, "title", "display_title") or "")
        full_md_path = str(row.get("full_md_path") or "")
        is_vectorized = bool(row.get("is_vectorized") or row.get("vectorized"))
        if is_vectorized:
            vectorized += 1
        if full_md_path and not row.get("fulltext_missing"):
            available += 1
        item = {
            "stable_id": stable_id,
            "source_id": str(first_present(row, "source_id", "stable_id", "id") or ""),
            "title": title,
            "sha256": str(first_present(row, "sha256", "fulltext_sha256") or ""),
            "is_vectorized": is_vectorized,
            "kb_id": str(row.get("kb_id") or ""),
            "fulltext_missing": bool(row.get("fulltext_missing")),
            "full_md_path": full_md_path,
        }
        manifest_path = task_dir / "025-rag-import" / "fulltext" / stable_id / "manifest.json" if stable_id else None
        if manifest_path and manifest_path.is_file():
            item["manifest_path"] = relpath(task_dir, manifest_path)
            item["manifest_sha256"] = sha256_file(manifest_path)
            manifest_data = safe_load_json(manifest_path, warnings, safety)
            if isinstance(manifest_data, dict):
                item["manifest_full_md_path"] = str(manifest_data.get("full_md_path") or full_md_path)
                item["manifest_title"] = str(first_present(manifest_data, "title", "display_title") or title)
        items.append(item)
        if full_md_path:
            safety["full_md_pointers_recorded"] += 1
    return {
        "exists": True,
        "rel_path": SIDECAR_PATHS["fulltext_index"],
        "sha256": sha256_file(path),
        "item_count": len(records),
        "vectorized_count": vectorized,
        "fulltext_available_count": available,
        "index_declares_rag_chunks": bool(isinstance(data, dict) and data.get("contains_rag_chunks")),
        "index_declares_vectors": bool(isinstance(data, dict) and data.get("contains_vectors")),
        "items": items,
        "rule": "full_md_path is a pointer only; full.md body is not opened by journal-style sidecar intake.",
    }


def summarize_mineru_ledger(task_dir: Path, safety: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    path = task_dir / SIDECAR_PATHS["mineru_job_ledger"]
    if not path.is_file():
        return {"exists": False, "row_count": 0, "event_counts": {}, "status_counts": {}}
    event_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    rows = 0
    with path.open(encoding="utf-8", errors="ignore") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            rows += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                warnings.append(f"{SIDECAR_PATHS['mineru_job_ledger']}:{line_no}: invalid JSONL row")
                continue
            scan_forbidden(row, f"$mineru_job_ledger[{line_no}]", safety)
            event_counts[str(first_present(row, "event", "phase", "action") or "unspecified")] += 1
            status_counts[str(first_present(row, "status", "state", "result") or "unspecified")] += 1
    return {
        "exists": True,
        "rel_path": SIDECAR_PATHS["mineru_job_ledger"],
        "sha256": sha256_file(path),
        "row_count": rows,
        "event_counts": dict(sorted(event_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
    }


def summarize_sources_dir(task_dir: Path) -> dict[str, Any]:
    sources_dir = task_dir / "026-knowledge-workbench" / "sources"
    if not sources_dir.is_dir():
        return {"exists": False, "file_count": 0, "files": []}
    files = []
    for path in sorted(sources_dir.glob("*.md")):
        files.append({
            "rel_path": relpath(task_dir, path),
            "size_bytes": path.stat().st_size,
            "content_read": False,
        })
    return {
        "exists": True,
        "rel_path": "026-knowledge-workbench/sources",
        "file_count": len(files),
        "files": files,
        "derived": True,
        "rule": "source markdown content is not parsed at sidecar intake.",
    }


def write_derived(task_dir: Path, manifest: dict[str, Any]) -> None:
    meta_dir = task_dir / "03-analysis" / "metadata-layer"
    meta_dir.mkdir(parents=True, exist_ok=True)
    if manifest["source_role_summary"].get("exists"):
        out = meta_dir / "source-role-ecology-summary.json"
        payload = {
            "schema": "journal_style_source_role_ecology_summary_v1",
            "created_at": manifest["created_at"],
            "source_manifest": "00-intake/jiansuo-sidecar-manifest.json",
            "source_role_summary": manifest["source_role_summary"],
            "evidence_layer": "metadata_only",
            "redaction": manifest["redaction"],
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if manifest["bibliography_scope"].get("full_bibliography", {}).get("exists") or manifest["bibliography_scope"].get("master_bibliography", {}).get("exists"):
        out = meta_dir / "bibliography-scope-coverage.json"
        payload = {
            "schema": "journal_style_bibliography_scope_coverage_v1",
            "created_at": manifest["created_at"],
            "source_manifest": "00-intake/jiansuo-sidecar-manifest.json",
            "bibliography_scope": manifest["bibliography_scope"],
            "evidence_layer": "metadata_only",
            "redaction": manifest["redaction"],
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    task_dir = args.task_dir.expanduser().resolve()
    output = args.output.expanduser().resolve() if args.output else task_dir / "00-intake" / "jiansuo-sidecar-manifest.json"
    warnings: list[str] = []
    safety: dict[str, Any] = {
        "forbidden_keys": load_policy_forbidden_keys(),
        "contains_fulltext_body": False,
        "contains_rag_chunks": False,
        "contains_vectors": False,
        "contains_secrets": False,
        "problems": [],
        "warnings": warnings,
        "scanned_json_files": [],
        "full_md_pointers_recorded": 0,
        "full_md_files_opened": 0,
    }

    sidecars = {name: artifact_status(task_dir, name, rel) for name, rel in SIDECAR_PATHS.items()}
    sidecars["knowledge_workbench_sources"] = summarize_sources_dir(task_dir)
    source_roles = summarize_source_roles(task_dir, safety, warnings)
    rag_seeds = summarize_rag_seed_pack(task_dir, safety, warnings)
    gaps = summarize_gap_ledger(task_dir, safety, warnings)
    fulltext_index = summarize_fulltext_index(task_dir, safety, warnings)
    mineru = summarize_mineru_ledger(task_dir, safety, warnings)
    downstream_manifest = summarize_downstream_manifest(task_dir, safety, warnings)
    bibliography = build_bibliography_scope(task_dir, sidecars, safety)

    safety_out = {key: value for key, value in safety.items() if key != "forbidden_keys"}
    safety_out["warnings"] = warnings
    manifest = {
        "schema": SCHEMA,
        "created_at": now_iso(),
        "task_dir": str(task_dir),
        "sidecars": sidecars,
        "available_sidecar_count": sum(1 for item in sidecars.values() if item.get("exists") and not item.get("derived")),
        "source_role_summary": source_roles,
        "rag_query_seed_summary": rag_seeds,
        "bibliography_scope": bibliography,
        "downstream_consumption_manifest": downstream_manifest,
        "fulltext_index": fulltext_index,
        "mineru_job_ledger": mineru,
        "gap_summary": gaps,
        "knowledge_workbench_sources": sidecars["knowledge_workbench_sources"],
        "safety": safety_out,
        "redaction": "safe metadata only; no full.md/PDF body, RAG chunks, vectors, Zotero DB, cookies, tokens, keys, or full_zip_url are copied.",
        "_rule": "This is an optional best-effort sidecar summary. Missing sidecars do not block journal-style main flow.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_derived(task_dir, manifest)
    print(json.dumps({
        "manifest_path": str(output),
        "available_sidecar_count": manifest["available_sidecar_count"],
        "safety_problem_count": len(safety_out["problems"]),
        "full_md_files_opened": safety_out["full_md_files_opened"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
