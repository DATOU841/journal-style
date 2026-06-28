#!/usr/bin/env python3
"""Offline fixtures for journal_review_memory_v1 export.

All data is synthetic. These fixtures do not read real Obsidian notes, real
article bodies, RAG chunks, Zotero DBs, PDFs, servers, or model pools.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / "scripts"
PY = sys.executable

RESULTS: list[dict] = []


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([PY, *args], capture_output=True, text=True)


def record(name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append({"fixture": name, "passed": bool(passed), "detail": detail})


def write_note(path: Path, frontmatter: str, body: str = "# Body\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter.strip()}\n---\n\n{body}", encoding="utf-8")


def make_vault(root: Path) -> None:
    write_note(
        root / "03-期刊适配" / "测试刊-投稿要求.md",
        """
review_memory: true
target_journal: "测试刊"
length_band: {"min": 9000, "max": 14000}
abstract: "避免流程宣告，直接给研究判断。"
keyword_count: {"min": 3, "max": 5}
notes_convention: "脚注"
reference_convention: "GB/T 7714"
theory_density: "medium"
review_density: "low"
most_avoided_tone: ["流程腔", "功能宣告句"]
section_rhythm: ["问题-材料-判断"]
intro_patterns: ["对象切入"]
conclusion_patterns: ["回到问题意识"]
verified_fix_strategies: [{"id": "vf-0001", "problem": "功能宣告句", "fix_kind": "lint_fix", "strategy": "改为判断句", "consumers": "wenzhang-runse"}]
abstract_rules: ["摘要必须给出判断"]
conclusion_rules: ["结语避免重复摘要"]
ai_tone_replacements: [{"from": "本文旨在", "to": "改为研究判断"}]
""",
        body="SOURCE_EXCERPT_BODY_SHOULD_NOT_BE_READ\n",
    )
    write_note(
        root / "02-高危病灶库" / "AI腔替换策略.md",
        """
review_memory: lesion
patterns: [{"id": "ap-0001", "pattern": "本文旨在", "kind": "lint", "severity": "P0", "fix_hint": "改为直接判断句", "consumers": "both", "promote_status": "candidate"}]
""",
    )


def export_pack(vault: Path, output: Path, journal: str = "测试刊") -> subprocess.CompletedProcess[str]:
    return run([
        str(SCRIPTS / "export_review_memory_pack.py"),
        "--vault-root",
        str(vault),
        "--journal",
        journal,
        "--output",
        str(output),
    ])


def fixture_export_pack_is_advisory_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        vault = root / "vault"
        out = root / "pack.json"
        make_vault(vault)
        proc = export_pack(vault, out)
        if proc.returncode != 0 or not out.is_file():
            record("export_pack_is_advisory_only", False, proc.stdout + proc.stderr)
            return
        pack = json.loads(out.read_text(encoding="utf-8"))
        passed = (
            pack.get("schema") == "journal_review_memory_v1"
            and pack.get("provenance") == "human_review_memory"
            and pack.get("source_evidence_scope") == "human_review_memory"
            and pack.get("not_evidence") is True
            and pack.get("format_specs", {}).get("length_band", {}).get("advisory_only") is True
            and pack.get("avoid_patterns")
        )
        record("export_pack_is_advisory_only", passed, json.dumps(pack, ensure_ascii=False)[:500])


def fixture_frontmatter_only_body_not_exported() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        vault = root / "vault"
        out = root / "pack.json"
        make_vault(vault)
        proc = export_pack(vault, out)
        if proc.returncode != 0:
            record("frontmatter_only_body_not_exported", False, proc.stdout + proc.stderr)
            return
        text = out.read_text(encoding="utf-8")
        record(
            "frontmatter_only_body_not_exported",
            "SOURCE_EXCERPT_BODY_SHOULD_NOT_BE_READ" not in text and "source_excerpt" not in text,
            text[:500],
        )


def fixture_forbidden_evidence_field_blocks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        vault = root / "vault"
        make_vault(vault)
        write_note(
            vault / "02-高危病灶库" / "证据泄漏.md",
            """
review_memory: lesion
patterns: [{"id": "bad-0001", "pattern": "泄漏", "source_excerpt": "不得进入记忆包"}]
""",
        )
        proc = export_pack(vault, root / "pack.json")
        record(
            "forbidden_evidence_field_blocks",
            proc.returncode != 0 and "frontmatter" in proc.stdout and "source_excerpt" in proc.stdout,
            proc.stdout + proc.stderr,
        )


def fixture_secret_like_value_blocks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        vault = root / "vault"
        make_vault(vault)
        write_note(
            vault / "02-高危病灶库" / "密钥泄漏.md",
            """
review_memory: lesion
patterns: [{"id": "bad-0002", "pattern": "Bearer abcdefghijklmnopqrstuvwxyz123456"}]
""",
        )
        proc = export_pack(vault, root / "pack.json")
        record(
            "secret_like_value_blocks",
            proc.returncode != 0 and "secret-like" in proc.stdout,
            proc.stdout + proc.stderr,
        )


def fixture_missing_journal_note_fails_cleanly() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        vault = root / "vault"
        (vault / "03-期刊适配").mkdir(parents=True, exist_ok=True)
        proc = export_pack(vault, root / "pack.json", journal="不存在刊")
        record(
            "missing_journal_note_fails_cleanly",
            proc.returncode != 0 and "journal note not found" in proc.stdout,
            proc.stdout + proc.stderr,
        )


def main() -> int:
    fixtures = [
        fixture_export_pack_is_advisory_only,
        fixture_frontmatter_only_body_not_exported,
        fixture_forbidden_evidence_field_blocks,
        fixture_secret_like_value_blocks,
        fixture_missing_journal_note_fails_cleanly,
    ]
    for fixture in fixtures:
        try:
            fixture()
        except Exception as exc:
            record(fixture.__name__, False, repr(exc))
    failed = [item for item in RESULTS if not item["passed"]]
    print(json.dumps({"ok": not failed, "passed": len(RESULTS) - len(failed), "total": len(RESULTS), "results": RESULTS}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
