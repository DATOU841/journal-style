#!/usr/bin/env python3
"""Run local smoke tests with synthetic metadata only."""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run journal-style smoke tests.")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary files and print their path.")
    return parser.parse_args()


def write_csv(path: Path, rows: list[dict]) -> None:
    headers = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def run(cmd: list[str], cwd: Path) -> None:
    completed = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        raise SystemExit(completed.returncode)


def build_title_rows() -> list[dict]:
    rows = []
    for index in range(1, 13):
        year = 2021 + (index % 4)
        rows.append({
            "title": f"清代碑帖传播机制研究{index}",
            "year": year,
            "column": "专题研究" if index % 3 else "书学史",
            "author": f"作者{index % 5}；合作者{index % 3}",
            "author_titles": "教授；硕士研究生" if index % 2 else "副教授；博士研究生",
            "author_stages": "导师；硕士生" if index % 2 else "教师；博士生",
            "author_degrees": "博士；硕士" if index % 2 else "博士；博士",
            "institution": f"机构{index % 4}；合作机构{index % 2}",
            "corresponding_author": f"作者{index % 5}" if index % 4 == 0 else "",
            "fund": "国家社科基金项目" if index % 3 == 0 else "省社科项目" if index % 3 == 1 else "",
            "advisor_student_relation": "公开作者简介标注导师指导关系" if index == 1 else "",
            "abstract": "围绕碑帖材料、传播路径与书学接受展开分析。",
            "keywords": "碑帖；传播；书学史",
            "pdf_status": "有" if index % 2 else "无",
        })
    return rows


def build_reference_rows() -> list[dict]:
    rows = []
    for article_index in range(1, 7):
        for ref_index in range(1, 6):
            rows.append({
                "article_id": f"A{article_index}",
                "ref_author": f"被引作者{ref_index % 4}",
                "ref_title": f"碑帖文献研究{ref_index % 5}",
                "ref_year": 2018 + (ref_index % 6),
                "ref_source": "书法研究" if ref_index % 2 else "文艺研究",
                "ref_type": "期刊" if ref_index % 2 else "著作",
                "language": "中文",
                "is_self_journal": "是" if ref_index == 1 else "否",
            })
    return rows


def main() -> int:
    args = parse_args()
    work_dir = Path(tempfile.mkdtemp(prefix="journal-style-smoke-"))
    try:
        title_csv = work_dir / "titles.csv"
        refs_csv = work_dir / "references.csv"
        write_csv(title_csv, build_title_rows())
        write_csv(refs_csv, build_reference_rows())

        commands = [
            [sys.executable, str(SCRIPTS / "analyze_title_corpus.py"), "--input", str(title_csv), "--output-json", "title.json", "--output-md", "title.md"],
            [sys.executable, str(SCRIPTS / "analyze_column_structure.py"), "--title-list", str(title_csv), "--output-json", "column.json", "--output-md", "column.md"],
            [sys.executable, str(SCRIPTS / "analyze_author_institution_network.py"), "--input", str(title_csv), "--output-json", "author-network.json", "--output-md", "author-network.md"],
            [sys.executable, str(SCRIPTS / "analyze_author_profile_and_byline.py"), "--input", str(title_csv), "--output-json", "author-profile.json", "--output-md", "author-profile.md"],
            [sys.executable, str(SCRIPTS / "analyze_reference_ecology.py"), "--input", str(refs_csv), "--output-json", "ref-ecology.json", "--output-md", "ref-ecology.md"],
            [sys.executable, str(SCRIPTS / "analyze_reference_network.py"), "--input", str(refs_csv), "--output-json", "ref-network.json", "--output-md", "ref-network.md"],
            [
                sys.executable,
                str(SCRIPTS / "generate_quantitative_report.py"),
                "--title-list",
                str(title_csv),
                "--expected-title-count",
                "20",
                "--expected-years",
                "2021,2022,2023,2024",
                "--output-json",
                "quant.json",
                "--output-md",
                "quant.md",
            ],
            [
                sys.executable,
                str(SCRIPTS / "generate_topic_suggestions.py"),
                "--title-list",
                str(title_csv),
                "--user-keywords",
                "碑帖,传播",
                "--output-json",
                "topic.json",
                "--output",
                "topic.md",
            ],
        ]
        for command in commands:
            run(command, work_dir)
        if args.keep_temp:
            print(f"smoke tests passed: {work_dir}")
        else:
            print("smoke tests passed")
        return 0
    finally:
        if not args.keep_temp:
            shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
