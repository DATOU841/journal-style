#!/usr/bin/env python3
"""Run local smoke tests with synthetic metadata only."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SKILL = ROOT


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


def run_expect_fail(cmd: list[str], cwd: Path) -> None:
    completed = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    if completed.returncode == 0:
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        raise SystemExit("expected command to fail")


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
            "material_type": "碑帖；档案" if index % 2 else "图像；文献汇编",
            "method_type": "考辨；比较" if index % 2 else "个案；图像分析",
            "advisor_student_relation": "公开作者简介标注导师指导关系" if index == 1 else "",
            "abstract": "围绕碑帖材料、传播路径与书学接受展开分析。",
            "keywords": "碑帖；传播；书学史",
            "pdf_status": "有" if index % 2 else "无",
        })
    return rows


def build_peer_title_rows() -> list[dict]:
    rows = []
    for index in range(1, 13):
        rows.append({
            "title": f"近现代书法教育专题研究{index}",
            "year": 2021 + (index % 4),
            "column": "教育研究" if index % 2 else "理论研究",
            "author": f"邻刊作者{index % 6}；邻刊合作者{index % 4}",
            "author_titles": "讲师；博士研究生" if index % 2 else "教授；硕士研究生",
            "author_stages": "教师；博士生" if index % 2 else "导师；硕士生",
            "author_degrees": "博士；博士" if index % 2 else "博士；硕士",
            "institution": f"邻刊机构{index % 5}；邻刊合作机构{index % 3}",
            "corresponding_author": f"邻刊作者{index % 6}" if index % 5 == 0 else "",
            "fund": "校级项目" if index % 4 == 0 else "省社科项目" if index % 4 == 1 else "",
            "material_type": "教育案例；访谈" if index % 2 else "文献汇编；统计",
            "method_type": "田野；文本分析" if index % 2 else "计量；比较",
            "advisor_student_relation": "",
            "abstract": "围绕书法教育、课程建设与传播路径展开分析。",
            "keywords": "书法教育；课程；传播",
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


def build_operations_rows() -> list[dict]:
    return [
        {
            "source_type": "official",
            "source_title": "投稿须知",
            "source_url": "https://example.org/journal/submit",
            "review_cycle_days": "60",
            "fee_policy": "不收审稿费，录用后按页收取版面费",
            "page_charge": "按页",
            "submission_system": "官方投稿系统",
            "reputation_polarity": "neutral",
            "reputation_note": "官网说明审稿周期约两个月。",
        },
        {
            "source_type": "third_party",
            "source_title": "作者经验统计",
            "source_url": "https://example.org/third-party",
            "first_decision_days": "75",
            "acceptance_days": "180",
            "publication_lag_days": "120",
            "reputation_polarity": "mixed",
            "reputation_note": "第三方经验样本显示等待时间差异较大。",
        },
        {
            "source_type": "forum",
            "source_title": "投稿经验帖",
            "source_url": "https://example.org/forum",
            "review_cycle_days": "150",
            "reputation_polarity": "negative",
            "reputation_note": "个别作者反馈等待较长，需核验。",
            "warning_flag": "是",
        },
    ]


def build_fulltext_rows() -> list[dict]:
    rows = []
    for index in range(1, 9):
        rows.append({
            "article_id": f"FT{index}",
            "title": f"碑帖材料与书学传播研究{index}",
            "year": 2021 + (index % 4),
            "column": "专题研究" if index % 2 else "书学史",
            "abstract": "本文围绕碑帖材料、传播路径与书学接受展开讨论。",
            "keywords": "碑帖；传播；书学史；材料",
            "fulltext": (
                f"摘要：本文围绕碑帖材料、传播路径与书学接受展开讨论。关键词：碑帖；传播；书学史\n"
                "一、问题的提出\n"
                "本文使用档案、碑帖、图像材料，结合比较和考辨方法展开分析。\n"
                "二、材料与方法\n"
                "材料包括馆藏档案、拓本和图版。方法包括个案研究、图像分析和文本分析。\n"
                "三、结论\n"
                "表1 材料来源统计。图1 传播路径图。注：样本为示例。\n"
                "[1] 示例参考文献。\n"
                f"收稿日期：2024-01-{index + 10:02d} 录用日期：2024-03-{index + 10:02d} 刊发日期：2024-06-{index + 10:02d}\n"
            ),
        })
    return rows


def build_review_memory_fixture(root: Path) -> tuple[Path, Path]:
    journal_dir = root / "03-期刊适配"
    lesion_dir = root / "02-高危病灶库"
    journal_dir.mkdir(parents=True, exist_ok=True)
    lesion_dir.mkdir(parents=True, exist_ok=True)
    journal_note = journal_dir / "测试刊-投稿要求.md"
    lesion_note = lesion_dir / "AI腔替换策略.md"
    journal_note.write_text(
        """---
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
ai_tone_replacements: [{"from": "本文旨在", "to": "可直接改为研究判断"}]
---

# 测试刊投稿要求
""",
        encoding="utf-8",
    )
    lesion_note.write_text(
        """---
review_memory: lesion
patterns: [{"id": "ap-0001", "pattern": "本文旨在", "kind": "lint", "severity": "P0", "fix_hint": "改为直接判断句", "consumers": "both", "promote_status": "candidate"}]
---

# AI腔替换策略
""",
        encoding="utf-8",
    )
    return journal_note, lesion_note


def main() -> int:
    args = parse_args()
    work_dir = Path(tempfile.mkdtemp(prefix="journal-style-smoke-"))
    try:
        title_csv = work_dir / "titles.csv"
        peer_title_csv = work_dir / "peer-titles.csv"
        refs_csv = work_dir / "references.csv"
        operations_csv = work_dir / "operations.csv"
        fulltext_csv = work_dir / "fulltext.csv"
        review_memory_root = work_dir / "review-memory-vault"
        review_memory_output = work_dir / "journal-review-memory-pack.json"
        write_csv(title_csv, build_title_rows())
        write_csv(peer_title_csv, build_peer_title_rows())
        write_csv(refs_csv, build_reference_rows())
        write_csv(operations_csv, build_operations_rows())
        write_csv(fulltext_csv, build_fulltext_rows())
        build_review_memory_fixture(review_memory_root)

        status_ok = work_dir / "wenheng-ok.json"
        status_bad = work_dir / "wenheng-bad.json"
        status_base = {
            "schema": "journal_style_wenheng_status_v1",
            "skill_id": "journal-style",
            "task_id": "TASK-SMOKE",
            "task_name": "测试刊",
            "journal": {"name": "测试刊", "identity_status": "pending"},
            "input": {},
            "data_assets": {},
            "pipeline_status": {
                "official_check": "pending",
                "title_intake": "pending",
                "title_screening": "pending",
                "topic_library": "pending",
                "zotero_pdf_rag": "pending",
                "metadata_analysis": "done",
                "core_library_selection": "pending",
                "fulltext_analysis": "blocked",
                "submission_operations": "pending",
                "fit_evaluation": "pending",
                "overall_journal_style": "blocked",
            },
            "analysis_layers": {
                "metadata_layer_status": "done",
                "fulltext_layer_status": "blocked",
                "completion_label": "METADATA_ONLY_NOT_FULLTEXT_READY",
                "fulltext_evidence": {
                    "core_library_count": 0,
                    "fulltext_sample_count": 0,
                    "rag_available_rate": 0.0,
                    "pdf_coverage_rate": 0.0,
                },
            },
            "metrics": {"confidence": "low", "data_quality_grade": "low", "evidence_strength": "weak", "sample_coverage_rate": 0.0},
            "decision": {"recommended_action": "unknown"},
            "handoff": {},
            "updated_at": "2026-01-01T00:00:00Z",
        }
        status_ok.write_text(json.dumps(status_base, ensure_ascii=False, indent=2), encoding="utf-8")
        bad_payload = json.loads(json.dumps(status_base))
        bad_payload["pipeline_status"]["overall_journal_style"] = "done"
        status_bad.write_text(json.dumps(bad_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        status_legacy_bad = work_dir / "wenheng-legacy-bad.json"
        legacy_bad_payload = json.loads(json.dumps(status_base))
        legacy_bad_payload.pop("analysis_layers")
        legacy_bad_payload["pipeline_status"] = {
            "official_check": "done",
            "title_intake": "done",
            "topic_library": "done",
            "pdf_check": "pending",
            "rag_import": "pending",
            "analysis": "done",
            "fit_evaluation": "pending",
        }
        status_legacy_bad.write_text(json.dumps(legacy_bad_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        handoff_ok = work_dir / "handoff-ok.json"
        handoff_bad = work_dir / "handoff-bad.json"
        receipts = [
            {"item_key": f"K{i}", "title": f"T{i}", "in_collection": True, "pdf_ready": i <= 6, "rag_indexed": i <= 5, "recall_ok": i <= 3}
            for i in range(1, 9)
        ]
        handoff_ok.write_text(json.dumps({
            "status": "success",
            "request_type": "journal_corpus",
            "task_collection_binding": "live",
            "item_count": 8,
            "pdf_count": 6,
            "rag_doc_count": 5,
            "include_pdf": True,
            "include_rag": True,
            "item_receipts": receipts,
            "recall_test": {"sampled": 3, "passed": 3},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        handoff_bad.write_text(json.dumps({
            "status": "success",
            "task_collection_binding": "missing",
            "item_count": 8,
            "pdf_count": 0,
            "rag_doc_count": 0,
            "item_receipts": [],
            "recall_test": {"sampled": 0, "passed": 0},
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        abstract_ok = work_dir / "abstract-ok.jsonl"
        abstract_bad = work_dir / "abstract-bad.jsonl"
        abstract_ok.write_text("\n".join(json.dumps({"title": f"T{i}", "abstract": "摘要", "keywords": ["艺术史"], "item_key": f"K{i}", "pdf_ready": True}, ensure_ascii=False) for i in range(1, 5)) + "\n", encoding="utf-8")
        abstract_bad.write_text(json.dumps({"title": "T1", "fulltext": "不应出现全文", "api_key": "SECRETSECRETSECRET"}, ensure_ascii=False) + "\n", encoding="utf-8")

        core_ok = work_dir / "core-ok.json"
        core_bad = work_dir / "core-bad.json"
        core_ok.write_text(json.dumps({
            "screened_count": 20,
            "selected": [{"title": f"T{i}", "selected": True, "scores": {"topic": 0.8, "total": 0.8}, "total": 0.8} for i in range(1, 7)],
            "rejected": [{"title": f"R{i}", "reason": "below_threshold"} for i in range(1, 15)],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        core_bad.write_text(json.dumps({
            "screened_count": 20,
            "selected": [{"title": f"T{i}", "selected": True, "scores": {"topic": 0.8}, "total": 0.8} for i in range(1, 12)],
            "rejected": [{"title": "R1"}],
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        fulltext_ok = work_dir / "fulltext-claims-ok.json"
        fulltext_bad = work_dir / "fulltext-claims-bad.json"
        fulltext_ok.write_text(json.dumps({
            "sample": {"fulltext_sample_count": 22},
            "coverage": {"rag_available_rate": 0.6},
            "claims": [{"claim_id": "C1", "evidence_layer": "fulltext", "provenance": [{"source_item_keys": ["K1"], "rag_doc_ids": ["R1"]}]}],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        fulltext_bad.write_text(json.dumps({
            "sample": {"fulltext_sample_count": 8},
            "coverage": {"rag_available_rate": 0.0},
            "claims": [{"claim_id": "C1", "evidence_layer": "fulltext", "text": "无来源全文结论"}],
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        secret_bad = work_dir / "secret-bad.txt"
        secret_bad.write_text("python script.py --api-key=SECRETSECRETSECRET\n", encoding="utf-8")

        commands = [
            [sys.executable, str(SCRIPTS / "validate_public_introduction.py")],
            [sys.executable, str(SCRIPTS / "validate_readme.py")],
            [
                sys.executable,
                str(SCRIPTS / "screen_titles.py"),
                "--input",
                str(title_csv),
                "--topic-keywords",
                "碑帖,传播",
                "--output-json",
                "title-screening.json",
                "--output-md",
                "title-screening.md",
            ],
            [
                sys.executable,
                str(SCRIPTS / "select_core_library.py"),
                "--input",
                str(title_csv),
                "--topic-keywords",
                "碑帖,传播",
                "--output-json",
                "core-library-generated.json",
                "--output-md",
                "core-library-generated.md",
            ],
            [sys.executable, str(SCRIPTS / "analyze_title_corpus.py"), "--input", str(title_csv), "--output-json", "title.json", "--output-md", "title.md"],
            [sys.executable, str(SCRIPTS / "analyze_column_structure.py"), "--title-list", str(title_csv), "--output-json", "column.json", "--output-md", "column.md"],
            [sys.executable, str(SCRIPTS / "analyze_journal_submission_operations.py"), "--input", str(operations_csv), "--output-json", "operations.json", "--output-md", "operations.md"],
            [sys.executable, str(SCRIPTS / "analyze_fulltext_article_patterns.py"), "--input", str(fulltext_csv), "--output-json", "fulltext-pattern.json", "--output-md", "fulltext-pattern.md"],
            [sys.executable, str(SCRIPTS / "analyze_funding_topic_association.py"), "--input", str(title_csv), "--user-keywords", "碑帖,传播", "--output-json", "funding-topic.json", "--output-md", "funding-topic.md"],
            [sys.executable, str(SCRIPTS / "analyze_author_institution_network.py"), "--input", str(title_csv), "--output-json", "author-network.json", "--output-md", "author-network.md"],
            [sys.executable, str(SCRIPTS / "analyze_author_profile_and_byline.py"), "--input", str(title_csv), "--output-json", "author-profile.json", "--output-md", "author-profile.md"],
            [sys.executable, str(SCRIPTS / "analyze_author_profile_and_byline.py"), "--input", str(peer_title_csv), "--output-json", "peer-author-profile.json", "--output-md", "peer-author-profile.md"],
            [sys.executable, str(SCRIPTS / "compare_multi_journal_author_profiles.py"), "--inputs", "目标刊=author-profile.json", "邻近刊=peer-author-profile.json", "--output-json", "multi-author-profile.json", "--output-md", "multi-author-profile.md"],
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
            [sys.executable, str(SCRIPTS / "validate_wenheng_status.py"), "--input", str(status_ok)],
            [sys.executable, str(SCRIPTS / "run_stage_gates.py"), "--gate", "completion-label", "--input", str(status_ok)],
            [sys.executable, str(SCRIPTS / "run_stage_gates.py"), "--gate", "jiansuo-handoff", "--input", str(handoff_ok)],
            [sys.executable, str(SCRIPTS / "run_stage_gates.py"), "--gate", "abstract-metadata-ledger", "--input", str(abstract_ok)],
            [sys.executable, str(SCRIPTS / "run_stage_gates.py"), "--gate", "core-library", "--input", str(core_ok)],
            [sys.executable, str(SCRIPTS / "run_stage_gates.py"), "--gate", "fulltext-claims", "--input", str(fulltext_ok)],
            [
                sys.executable,
                str(SCRIPTS / "export_review_memory_pack.py"),
                "--vault-root",
                str(review_memory_root),
                "--journal",
                "测试刊",
                "--output",
                str(review_memory_output),
            ],
            [sys.executable, str(SKILL / "tests" / "run_review_memory_fixtures.py")],
        ]
        for command in commands:
            run(command, work_dir)
        review_memory_pack = json.loads(review_memory_output.read_text(encoding="utf-8"))
        assert review_memory_pack["schema"] == "journal_review_memory_v1"
        assert review_memory_pack["provenance"] == "human_review_memory"
        assert review_memory_pack["not_evidence"] is True
        assert review_memory_pack["format_specs"]["length_band"]["advisory_only"] is True
        assert not any("source_excerpt" in json.dumps(item, ensure_ascii=False) for item in review_memory_pack.get("avoid_patterns", []))
        assert review_memory_pack["source_note"].startswith("Obsidian:")
        fail_commands = [
            [sys.executable, str(SCRIPTS / "validate_wenheng_status.py"), "--input", str(status_bad)],
            [sys.executable, str(SCRIPTS / "validate_wenheng_status.py"), "--input", str(status_legacy_bad)],
            [sys.executable, str(SCRIPTS / "run_stage_gates.py"), "--gate", "completion-label", "--input", str(status_bad)],
            [sys.executable, str(SCRIPTS / "run_stage_gates.py"), "--gate", "jiansuo-handoff", "--input", str(handoff_bad)],
            [sys.executable, str(SCRIPTS / "run_stage_gates.py"), "--gate", "abstract-metadata-ledger", "--input", str(abstract_bad)],
            [sys.executable, str(SCRIPTS / "run_stage_gates.py"), "--gate", "core-library", "--input", str(core_bad)],
            [sys.executable, str(SCRIPTS / "run_stage_gates.py"), "--gate", "fulltext-claims", "--input", str(fulltext_bad)],
            [sys.executable, str(SCRIPTS / "run_stage_gates.py"), "--gate", "secret-boundary", "--input", str(secret_bad)],
        ]
        for command in fail_commands:
            run_expect_fail(command, work_dir)
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
