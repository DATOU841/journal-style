#!/usr/bin/env python3
"""Validate README source and public boundary claims."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_README = ROOT / "README.md"
VERSION_FILE = ROOT / "VERSION"

WENHENG_MARKERS = (
    "content_source: wenheng_claude",
    "生成来源：文衡 Claude",
    "生成来源: 文衡 Claude",
    "<!-- content_source: wenheng_claude -->",
    "<!-- 生成来源：文衡 Claude -->",
)

REQUIRED_SECTIONS = (
    "公开介绍",
    "它解决什么问题",
    "当前能力",
    "边界",
    "开发验证",
    "发布纪律",
)

FORBIDDEN_PHRASES = (
    "写论文正文",
    "撰写论文正文",
    "生成论文正文",
    "润色正文",
    "模仿期刊语气",
    "直接下载",
    "直接导入 RAG",
    "直接检索 CNKI",
    "保证录用",
    "确保录用",
    "录用概率",
    "发表概率",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate journal-style README.")
    parser.add_argument("--file", type=Path, default=DEFAULT_README, help="README markdown file.")
    return parser.parse_args()


def fail(message: str) -> int:
    sys.stderr.write(f"README validation failed: {message}\n")
    return 1


def main() -> int:
    args = parse_args()
    if not args.file.exists():
        return fail(f"file does not exist: {args.file}")

    text = args.file.read_text(encoding="utf-8")
    if not any(marker in text for marker in WENHENG_MARKERS):
        return fail("README must include a Wenheng Claude source marker")
    if "<!-- skill_name: journal-style -->" not in text:
        return fail("README must include skill_name marker")

    missing = [section for section in REQUIRED_SECTIONS if section not in text]
    if missing:
        return fail("README is missing required sections: " + ", ".join(missing))

    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if version not in text:
        return fail(f"README must include current VERSION: {version}")
    if f"<!-- version: {version} -->" not in text:
        return fail(f"README must include version marker: {version}")

    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            return fail(f"forbidden capability claim found: {phrase}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
