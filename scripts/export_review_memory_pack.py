#!/usr/bin/env python3
"""Export journal_review_memory_v1 from Obsidian review-workbench front matter."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from journal_style_runtime import (
    ReleaseIntegrityError,
    assert_release_integrity,
    integrity_failure_payload,
)

DEFAULT_VAULT_ROOT = Path("/Users/a13497/Documents/Obsidian/Codex Memory/期刊评审工作台")
DEFAULT_JOURNAL_DIR = Path("03-期刊适配")
DEFAULT_LESION_DIR = Path("02-高危病灶库")
COMPILER_VERSION = "journal_review_memory_compiler_v1"

FORBIDDEN_KEYS = {
    "source_excerpt",
    "citation_key",
    "rag_chunk",
    "fulltext",
    "pdf_text",
    "token",
    "api_key",
    "authorization",
}
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{20,}|X-Amz-Signature=)", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("front matter missing")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError("front matter closing marker missing")
    return text[4:end].strip(), text[end + 4 :]


def parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value == "":
        return ""
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value.startswith("[") or value.startswith("{"):
        for loader in (json.loads, ast.literal_eval):
            try:
                return loader(value)
            except Exception:
                pass
        if value.startswith("{") and value.endswith("}"):
            return parse_inline_mapping(value)
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def parse_inline_mapping(value: str) -> dict:
    body = value.strip()[1:-1].strip()
    if not body:
        return {}
    out: dict[str, Any] = {}
    for part in split_top_level(body):
        if ":" not in part:
            continue
        key, raw = part.split(":", 1)
        out[key.strip().strip('"').strip("'")] = parse_scalar(raw.strip())
    return out


def split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    start = 0
    for index, char in enumerate(text):
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char in "[{(":
            depth += 1
        elif char in "]})":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return [part for part in parts if part]


def parse_frontmatter(frontmatter: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    lines = frontmatter.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if not line.startswith(" ") and ":" in line:
            key, raw = line.split(":", 1)
            key = key.strip()
            raw = raw.strip()
            if raw:
                data[key] = parse_scalar(raw)
                i += 1
                continue
            items: list[Any] = []
            mapping: dict[str, Any] = {}
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("\t")):
                child = lines[i].strip()
                if child.startswith("- "):
                    items.append(parse_scalar(child[2:].strip()))
                elif ":" in child:
                    child_key, child_raw = child.split(":", 1)
                    mapping[child_key.strip()] = parse_scalar(child_raw.strip())
                i += 1
            data[key] = items if items else mapping
            continue
        i += 1
    return data


def ensure_list(value: Any) -> list:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def ensure_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def find_journal_note(vault_root: Path, journal: str, explicit: Path | None) -> Path:
    if explicit:
        return explicit
    journal_dir = vault_root / DEFAULT_JOURNAL_DIR
    candidates = sorted(journal_dir.glob("*.md"))
    for candidate in candidates:
        if journal in candidate.stem:
            return candidate
    raise FileNotFoundError(f"journal note not found for {journal}: {journal_dir}")


def load_note_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = read_text(path)
    front, _body = split_frontmatter(text)
    return parse_frontmatter(front), text


def consumers(value: Any, default: str) -> str:
    if isinstance(value, str) and value:
        return value
    return default


def normalize_pattern(entry: Any, source: str, index: int) -> dict | None:
    if not isinstance(entry, dict):
        return None
    pattern = str(entry.get("pattern") or "").strip()
    if not pattern:
        return None
    return {
        "id": str(entry.get("id") or f"ap-{index:04d}"),
        "pattern": pattern,
        "kind": str(entry.get("kind") or "lint"),
        "severity": str(entry.get("severity") or "P2"),
        "fix_hint": str(entry.get("fix_hint") or ""),
        "consumers": consumers(entry.get("consumers"), "both"),
        "promote_status": str(entry.get("promote_status") or "candidate"),
        "source_note": source,
    }


def load_avoid_patterns(vault_root: Path) -> list[dict]:
    lesion_dir = vault_root / DEFAULT_LESION_DIR
    patterns: list[dict] = []
    if not lesion_dir.exists():
        return patterns
    for note in sorted(lesion_dir.glob("*.md")):
        try:
            fm, _text = load_note_frontmatter(note)
        except Exception:
            continue
        problems = scan_forbidden(fm, f"frontmatter:{note.relative_to(vault_root).as_posix()}")
        if problems:
            raise ValueError("; ".join(problems))
        raw_patterns = fm.get("patterns") or fm.get("avoid_patterns") or []
        for raw in ensure_list(raw_patterns):
            pattern = normalize_pattern(raw, f"Obsidian:{note.relative_to(vault_root).as_posix()}", len(patterns) + 1)
            if pattern:
                patterns.append(pattern)
    return patterns


def build_pack(vault_root: Path, journal: str, journal_note: Path) -> dict:
    fm, note_text = load_note_frontmatter(journal_note)
    problems = scan_forbidden(fm, f"frontmatter:{journal_note.relative_to(vault_root).as_posix()}")
    if problems:
        raise ValueError("; ".join(problems))
    note_ref = f"Obsidian:{journal_note.relative_to(vault_root).as_posix()}" if journal_note.is_relative_to(vault_root) else str(journal_note)
    target = str(fm.get("target_journal") or journal).strip()
    if not target:
        raise ValueError("target_journal missing")
    length_band = ensure_dict(fm.get("length_band"))
    keyword_count = ensure_dict(fm.get("keyword_count"))
    pack = {
        "schema": "journal_review_memory_v1",
        "provenance": "human_review_memory",
        "source_evidence_scope": "human_review_memory",
        "not_evidence": True,
        "target_journal": target,
        "source_note": note_ref,
        "source_note_sha": sha256_text(note_text),
        "compiled_at": now_iso(),
        "compiler_version": COMPILER_VERSION,
        "avoid_patterns": load_avoid_patterns(vault_root),
        "style_hints": {
            "section_rhythm": ensure_list(fm.get("section_rhythm")),
            "intro_patterns": ensure_list(fm.get("intro_patterns")),
            "conclusion_patterns": ensure_list(fm.get("conclusion_patterns")),
            "most_avoided_tone": ensure_list(fm.get("most_avoided_tone")),
            "theory_density": str(fm.get("theory_density") or ""),
            "review_density": str(fm.get("review_density") or ""),
            "consumers": "zhengwen-xiezuo",
        },
        "format_specs": {
            "length_band": {
                "min": length_band.get("min"),
                "max": length_band.get("max"),
                "advisory_only": True,
                "source": "human_memory",
            },
            "abstract": str(fm.get("abstract") or ""),
            "keyword_count": {
                "min": keyword_count.get("min"),
                "max": keyword_count.get("max"),
            },
            "notes_convention": str(fm.get("notes_convention") or ""),
            "reference_convention": str(fm.get("reference_convention") or ""),
            "consumers": "wenzhang-runse",
        },
        "verified_fix_strategies": ensure_list(fm.get("verified_fix_strategies")),
        "abstract_conclusion_rules": {
            "abstract": ensure_list(fm.get("abstract_rules")),
            "conclusion": ensure_list(fm.get("conclusion_rules")),
            "consumers": "both",
        },
        "ai_tone_replacements": ensure_list(fm.get("ai_tone_replacements")),
        "review_memory_conflicts": [],
    }
    validate_pack(pack)
    return pack


def scan_forbidden(value: Any, path: str = "$") -> list[str]:
    problems: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in FORBIDDEN_KEYS:
                problems.append(f"forbidden key {path}.{key}")
            problems.extend(scan_forbidden(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            problems.extend(scan_forbidden(child, f"{path}[{index}]"))
    elif isinstance(value, str) and SECRET_RE.search(value):
        problems.append(f"forbidden secret-like value at {path}")
    return problems


def validate_pack(pack: dict) -> None:
    required = [
        "schema",
        "provenance",
        "source_evidence_scope",
        "not_evidence",
        "target_journal",
        "source_note",
        "source_note_sha",
        "compiled_at",
        "compiler_version",
        "avoid_patterns",
        "style_hints",
        "format_specs",
        "verified_fix_strategies",
        "abstract_conclusion_rules",
        "ai_tone_replacements",
        "review_memory_conflicts",
    ]
    missing = [key for key in required if key not in pack]
    if missing:
        raise ValueError("missing required fields: " + ", ".join(missing))
    if pack["schema"] != "journal_review_memory_v1":
        raise ValueError("schema must be journal_review_memory_v1")
    if pack["provenance"] != "human_review_memory" or pack["source_evidence_scope"] != "human_review_memory":
        raise ValueError("review memory pack must use human_review_memory provenance")
    if pack["not_evidence"] is not True:
        raise ValueError("review memory pack must set not_evidence=true")
    problems = scan_forbidden(pack)
    if problems:
        raise ValueError("; ".join(problems))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export journal_review_memory_v1 from Obsidian front matter.")
    parser.add_argument("--vault-root", type=Path, default=DEFAULT_VAULT_ROOT)
    parser.add_argument("--journal", required=True)
    parser.add_argument("--journal-note", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        assert_release_integrity()
    except ReleaseIntegrityError as exc:
        print(json.dumps(integrity_failure_payload(exc, "export_review_memory_pack", None), ensure_ascii=False, indent=2))
        return 3
    vault_root = args.vault_root.expanduser().resolve()
    try:
        journal_note = find_journal_note(vault_root, args.journal, args.journal_note.expanduser().resolve() if args.journal_note else None)
        pack = build_pack(vault_root, args.journal, journal_note)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(args.output), "target_journal": pack["target_journal"]}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "reason": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
