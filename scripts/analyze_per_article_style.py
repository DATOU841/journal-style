#!/usr/bin/env python3
"""Generate per-article journal-style profiles from a MinerU/mu fulltext pack.

This script is deliberately local and offline. It accepts only an upstream
MinerU/mu complete fulltext core pack, validates that pack with the existing
gate, and then emits per-article structural profiles. It does not fetch PDFs,
run MinerU, query RAG, or write paper prose.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path

from journal_style_runtime import (
    ReleaseIntegrityError,
    assert_release_integrity,
    integrity_failure_payload,
    now_iso,
)

SCRIPTS_DIR = Path(__file__).resolve().parent
RUN_STAGE_GATES = SCRIPTS_DIR / "run_stage_gates.py"
DEFAULT_INPUT = "03-analysis/fulltext-layer/mu-fulltext-core-pack.json"
DEFAULT_OUTPUT = "03-analysis/fulltext-layer/per-article-style-profiles.json"
DEFAULT_PENDING = "03-analysis/fulltext-layer/pending-materials.json"


REQUIRED_DIMS = [
    "title_structure",
    "abstract_profile",
    "keywords_profile",
    "length_band",
    "paragraph_stats",
    "section_hierarchy",
    "intro_pattern",
    "material_types",
    "method_types",
    "argument_rhythm",
    "notes_profile",
    "reference_profile",
    "conclusion_pattern",
]


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_gate(gate: str, input_path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(RUN_STAGE_GATES), "--gate", gate, "--input", str(input_path)],
        capture_output=True,
        text=True,
    )
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "gate": gate,
            "verdict": "NO_GO",
            "problems": ["gate did not return valid JSON", proc.stderr.strip()[:400]],
            "warnings": [],
        }
    return verdict


def is_ready_article(article: dict) -> bool:
    required = [
        "article_id",
        "title",
        "authors",
        "year",
        "column",
        "mu_fulltext",
        "fulltext_sha256",
        "provenance",
        "core_library_joined",
        "section_tree",
        "paragraph_sequence",
        "reference_list",
    ]
    if any(article.get(field) in (None, "", [], {}) for field in required):
        return False
    if article.get("core_library_joined") is not True:
        return False
    provenance = article.get("provenance") or {}
    return all(provenance.get(field) for field in ("source_ledger", "extraction_method", "mu_version"))


def evidence(article: dict, dimension: str, source_field: str) -> dict:
    article_id = str(article.get("article_id"))
    return {
        "article_id": article_id,
        "dimension": dimension,
        "evidence_path": f"articles/{article_id}/{source_field}",
        "provenance": article.get("provenance") or {},
    }


def title_structure(title: str) -> dict:
    has_subtitle = "：" in title or ":" in title or "——" in title
    return {
        "char_count": len(title),
        "has_subtitle": has_subtitle,
        "pattern": "主副标题" if has_subtitle else "单标题",
    }


def section_profile(section_tree: list[dict]) -> dict:
    levels = [int(item.get("level") or 1) for item in section_tree if isinstance(item, dict)]
    subsection_count = sum(int(item.get("subsection_count") or 0) for item in section_tree if isinstance(item, dict))
    return {
        "section_count": len([item for item in section_tree if isinstance(item, dict) and int(item.get("level") or 1) == 1]),
        "max_level": max(levels) if levels else 0,
        "has_subsections": any(level > 1 for level in levels) or subsection_count > 0,
        "subsection_count": subsection_count,
    }


def paragraph_profile(paragraphs: list[dict]) -> dict:
    counts = [int(item.get("char_count") or 0) for item in paragraphs if isinstance(item, dict)]
    counts = [count for count in counts if count > 0]
    return {
        "paragraph_count": len(paragraphs),
        "avg_char_count": round(statistics.mean(counts), 2) if counts else 0,
        "median_char_count": round(statistics.median(counts), 2) if counts else 0,
    }


def notes_profile(notes) -> dict:
    if isinstance(notes, dict):
        return {
            "type": notes.get("type") or "unknown",
            "count": int(notes.get("count") or 0),
            "content_types": notes.get("content_types") or [],
            "available": True,
        }
    return {"type": "unknown", "count": 0, "content_types": [], "available": False}


def reference_profile(refs: list[dict], article: dict) -> dict:
    total = len(refs)
    zh = sum(1 for ref in refs if str(ref.get("lang") or "").lower() in {"zh", "cn", "chinese"})
    foreign = sum(1 for ref in refs if str(ref.get("lang") or "").lower() not in {"", "zh", "cn", "chinese"})
    year = int(article.get("year") or 0) if str(article.get("year") or "").isdigit() else 0
    recent = 0
    self_journal = 0
    for ref in refs:
        try:
            ref_year = int(ref.get("year"))
        except Exception:
            ref_year = 0
        if year and ref_year and year - ref_year <= 5:
            recent += 1
        if ref.get("is_self_journal") is True:
            self_journal += 1
    return {
        "reference_count": total,
        "zh_count": zh,
        "foreign_count": foreign,
        "recent_5y_count": recent,
        "self_journal_count": self_journal,
        "foreign_ratio": round(foreign / total, 4) if total else 0,
        "recent_5y_ratio": round(recent / total, 4) if total else 0,
    }


def infer_intro_pattern(article: dict) -> dict:
    headings = " ".join(str(item.get("title") or "") for item in article.get("section_tree") or [])
    if "问题" in headings:
        pattern = "问题意识切入"
    elif "引言" in headings or "绪论" in headings:
        pattern = "引言综述切入"
    else:
        pattern = "章节开端切入"
    return {"type": pattern, "evidence_required": True}


def infer_material_types(article: dict) -> list[str]:
    text = str(article.get("mu_fulltext") or "")
    candidates = {
        "档案": ["档案", "文书"],
        "图像": ["图像", "图版", "作品"],
        "文献": ["文献", "史料", "著作"],
        "碑帖": ["碑", "帖"],
        "访谈": ["访谈", "口述"],
    }
    found = [label for label, needles in candidates.items() if any(needle in text for needle in needles)]
    return found or ["gap:未见稳定材料类型锚点"]


def infer_method_types(article: dict) -> list[str]:
    text = str(article.get("mu_fulltext") or "")
    candidates = {
        "考辨": ["考辨", "考证"],
        "比较": ["比较", "对比"],
        "个案研究": ["个案"],
        "图像分析": ["图像分析", "图像"],
        "量化统计": ["统计", "计量"],
    }
    found = [label for label, needles in candidates.items() if any(needle in text for needle in needles)]
    return found or ["gap:未见稳定方法类型锚点"]


def infer_argument_rhythm(article: dict) -> dict:
    sections = section_profile(article.get("section_tree") or {})
    if sections.get("section_count", 0) >= 3:
        rhythm = "问题-材料-分析-结论"
    else:
        rhythm = "短节结构"
    return {"type": rhythm, "section_count": sections.get("section_count", 0)}


def infer_conclusion_pattern(article: dict) -> dict:
    headings = [str(item.get("title") or "") for item in article.get("section_tree") or []]
    has_conclusion = any("结" in heading or "余论" in heading for heading in headings)
    return {"type": "显性结论节" if has_conclusion else "末节收束", "has_explicit_conclusion": has_conclusion}


def profile_article(article: dict) -> dict:
    abstract = str(article.get("abstract") or "")
    keywords = article.get("keywords") or []
    section_tree = article.get("section_tree") or []
    paragraphs = article.get("paragraph_sequence") or []
    refs = article.get("reference_list") or []
    dimensions = {
        "title_structure": title_structure(str(article.get("title") or "")),
        "abstract_profile": {"char_count": len(abstract), "has_abstract": bool(abstract)},
        "keywords_profile": {"count": len(keywords), "keywords": keywords},
        "length_band": {"char_count_total": int(article.get("char_count_total") or len(str(article.get("mu_fulltext") or "")))},
        "paragraph_stats": paragraph_profile(paragraphs),
        "section_hierarchy": section_profile(section_tree),
        "intro_pattern": infer_intro_pattern(article),
        "material_types": infer_material_types(article),
        "method_types": infer_method_types(article),
        "argument_rhythm": infer_argument_rhythm(article),
        "notes_profile": notes_profile(article.get("notes")),
        "reference_profile": reference_profile(refs, article),
        "conclusion_pattern": infer_conclusion_pattern(article),
    }
    evidence_index = [
        evidence(article, "title_structure", "title"),
        evidence(article, "abstract_profile", "abstract"),
        evidence(article, "keywords_profile", "keywords"),
        evidence(article, "length_band", "mu_fulltext"),
        evidence(article, "paragraph_stats", "paragraph_sequence"),
        evidence(article, "section_hierarchy", "section_tree"),
        evidence(article, "intro_pattern", "section_tree"),
        evidence(article, "material_types", "mu_fulltext"),
        evidence(article, "method_types", "mu_fulltext"),
        evidence(article, "argument_rhythm", "section_tree"),
        evidence(article, "notes_profile", "notes"),
        evidence(article, "reference_profile", "reference_list"),
        evidence(article, "conclusion_pattern", "section_tree"),
    ]
    section = dimensions["section_hierarchy"]
    refs_profile = dimensions["reference_profile"]
    downstream_constraints = [
        {
            "type": "section_count_observation",
            "min": section["section_count"],
            "max": section["section_count"],
            "evidence_path": evidence(article, "section_hierarchy", "section_tree")["evidence_path"],
        },
        {
            "type": "keyword_count_observation",
            "min": len(keywords),
            "max": len(keywords),
            "evidence_path": evidence(article, "keywords_profile", "keywords")["evidence_path"],
        },
        {
            "type": "reference_count_observation",
            "min": refs_profile["reference_count"],
            "max": refs_profile["reference_count"],
            "evidence_path": evidence(article, "reference_profile", "reference_list")["evidence_path"],
        },
    ]
    missing_dims = [dim for dim in REQUIRED_DIMS if dim not in dimensions]
    return {
        "schema": "per_article_style_profile_v1",
        "article_id": str(article.get("article_id")),
        "source_article_id": str(article.get("article_id")),
        "title": article.get("title"),
        "year": article.get("year"),
        "column": article.get("column"),
        "dimensions": dimensions,
        "dimension_gaps": missing_dims,
        "evidence_index": evidence_index,
        "downstream_constraints": downstream_constraints,
    }


def write_pending(path: Path, input_path: Path, verdict: dict) -> None:
    payload = {
        "schema": "journal_style_pending_materials_v1",
        "reason": "mu-fulltext-pack gate did not pass; per-article profiles were not generated",
        "source_pack": str(input_path),
        "gate_verdict": verdict.get("verdict"),
        "problems": verdict.get("problems") or [],
        "warnings": verdict.get("warnings") or [],
        "created_at": now_iso(),
    }
    write_json(path, payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate per-article style profiles from a MinerU/mu pack.")
    parser.add_argument("--task-dir", type=Path, default=Path("."))
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--pending-output", default=DEFAULT_PENDING)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        assert_release_integrity()
    except ReleaseIntegrityError as exc:
        print(json.dumps(integrity_failure_payload(exc, "analyze_per_article_style", args.task_dir), ensure_ascii=False, indent=2))
        return 3

    task_dir = args.task_dir.expanduser().resolve()
    input_path = (task_dir / args.input).resolve() if not Path(args.input).is_absolute() else Path(args.input).resolve()
    output_path = (task_dir / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output).resolve()
    pending_path = (task_dir / args.pending_output).resolve() if not Path(args.pending_output).is_absolute() else Path(args.pending_output).resolve()
    if not input_path.exists():
        verdict = {"verdict": "NO_GO", "problems": [f"input pack missing: {input_path}"], "warnings": []}
        write_pending(pending_path, input_path, verdict)
        print(json.dumps({"ok": False, "output": None, "pending": str(pending_path), "reason": verdict["problems"][0]}, ensure_ascii=False, indent=2))
        return 1
    verdict = run_gate("mu-fulltext-pack", input_path)
    if verdict.get("verdict") not in {"PASS", "DEGRADED"}:
        write_pending(pending_path, input_path, verdict)
        print(json.dumps({"ok": False, "output": None, "pending": str(pending_path), "gate_verdict": verdict.get("verdict")}, ensure_ascii=False, indent=2))
        return 1

    pack = load_json(input_path)
    ready_articles = [article for article in pack.get("articles") or [] if is_ready_article(article)]
    profiles = [profile_article(article) for article in ready_articles]
    payload = {
        "schema": "journal_style_per_article_profile_batch_v1",
        "target_journal": pack.get("target_journal"),
        "source_pack": input_path.relative_to(task_dir).as_posix() if input_path.is_relative_to(task_dir) else str(input_path),
        "source_gate_verdict": verdict.get("verdict"),
        "ready_article_count": len(ready_articles),
        "profiles": profiles,
        "created_at": now_iso(),
        "_boundary": "Generated from an upstream MinerU/mu fulltext pack only; no CNKI/WoS/Zotero/PDF/RAG operation was performed.",
    }
    write_json(output_path, payload)
    profile_verdict = run_gate("per-article-profile-complete", output_path)
    ok = profile_verdict.get("verdict") in {"PASS", "DEGRADED"}
    print(json.dumps({
        "ok": ok,
        "output": str(output_path),
        "profile_count": len(profiles),
        "source_gate_verdict": verdict.get("verdict"),
        "profile_gate_verdict": profile_verdict.get("verdict"),
        "problems": profile_verdict.get("problems") or [],
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
