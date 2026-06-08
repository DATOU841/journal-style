#!/usr/bin/env python3
"""Validate public introduction source and boundary claims."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOC = ROOT / "docs" / "public-introduction.zh.md"
VERSION_FILE = ROOT / "VERSION"

PENDING_MARKER = "content_source: pending_wenheng_claude"
WENHENG_MARKERS = (
    "content_source: wenheng_claude",
    "生成来源：文衡 Claude",
    "生成来源: 文衡 Claude",
    "<!-- content_source: wenheng_claude -->",
    "<!-- 生成来源：文衡 Claude -->",
)

REQUIRED_SECTIONS = (
    "适用场景",
    "核心能力",
    "与其他 skill 的边界",
    "输出内容",
    "设计原则",
    "当前版本状态",
    "一句话说明",
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
    parser = argparse.ArgumentParser(description="Validate journal-style public introduction.")
    parser.add_argument("--file", type=Path, default=DEFAULT_DOC, help="Public introduction markdown file.")
    parser.add_argument(
        "--mode",
        choices=("auto", "pending", "final"),
        default="auto",
        help="pending accepts placeholder; final requires Wenheng Claude source marker and required sections.",
    )
    return parser.parse_args()


def fail(message: str) -> int:
    sys.stderr.write(f"public introduction validation failed: {message}\n")
    return 1


def has_wenheng_marker(text: str) -> bool:
    return any(marker in text for marker in WENHENG_MARKERS)


def validate_pending(text: str) -> int:
    if PENDING_MARKER not in text:
        return fail("pending file must include content_source: pending_wenheng_claude")
    if "本文件正文待文衡 Claude 生成" not in text:
        return fail("pending file must clearly state that body text is waiting for Wenheng Claude")
    return 0


def validate_final(text: str) -> int:
    if not has_wenheng_marker(text):
        return fail("final file must include a Wenheng Claude source marker")
    missing = [section for section in REQUIRED_SECTIONS if section not in text]
    if missing:
        return fail("final file is missing required sections: " + ", ".join(missing))
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if version not in text:
        return fail(f"final file must include current VERSION: {version}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            return fail(f"forbidden capability claim found: {phrase}")
    return 0


def main() -> int:
    args = parse_args()
    if not args.file.exists():
        return fail(f"file does not exist: {args.file}")
    text = args.file.read_text(encoding="utf-8")

    if args.mode == "pending":
        return validate_pending(text)
    if args.mode == "final":
        return validate_final(text)

    if PENDING_MARKER in text:
        return validate_pending(text)
    return validate_final(text)


if __name__ == "__main__":
    raise SystemExit(main())
