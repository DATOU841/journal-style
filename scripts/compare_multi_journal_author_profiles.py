#!/usr/bin/env python3
"""Compare author profile statistics across multiple journals."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare multi-journal author profile statistics.")
    parser.add_argument("--inputs", nargs="+", required=True, help="Pairs like JournalName=path/to/statistics.json")
    parser.add_argument("--output-json", default="multi-journal-author-profile-comparison-statistics.json")
    parser.add_argument("--output-md", default="multi-journal-author-profile-comparison-report.md")
    return parser.parse_args()


def load_input(pair: str) -> dict:
    if "=" not in pair:
        raise SystemExit(f"Invalid input pair, expected JournalName=path: {pair}")
    name, path_text = pair.split("=", 1)
    path = Path(path_text)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["journal_name"] = name.strip() or data.get("journal_name") or path.stem
    data["_source_path"] = str(path)
    return data


def value(data: dict, key: str, default=0):
    item = data.get(key, default)
    return default if item is None else item


def top_distribution(distribution: dict, limit: int = 5) -> list[dict]:
    return [
        {"name": key, "count": count}
        for key, count in sorted(distribution.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]


def evidence_strength(items: list[dict]) -> str:
    if len(items) < 2:
        return "weak"
    if all(value(item, "record_count") >= 50 and value(item, "evidence_strength", "weak") in {"medium", "strong"} for item in items):
        return "strong"
    if all(value(item, "record_count") >= 20 for item in items):
        return "medium"
    return "weak"


def main() -> int:
    args = parse_args()
    journals = [load_input(pair) for pair in args.inputs]
    warnings = []
    if len(journals) < 2:
        warnings.append("少于 2 个期刊，不得生成对比结论。")
    for item in journals:
        name = item["journal_name"]
        if value(item, "record_count") < 50:
            warnings.append(f"{name} 样本低于 50 条，对比只能作为样本观察。")
        if value(item, "author_title_coverage_rate") < 0.5:
            warnings.append(f"{name} 职称字段覆盖率低于 50%，不得比较作者职称结构强差异。")
        if value(item, "author_stage_or_degree_coverage_rate") < 0.5:
            warnings.append(f"{name} 学位/身份字段覆盖率低于 50%，不得比较学生作者参与度强差异。")
        if value(item, "fund_field_coverage_rate") < 0.5:
            warnings.append(f"{name} 基金字段覆盖率低于 50%，不得比较基金支撑强差异。")

    comparison_rows = []
    for item in journals:
        comparison_rows.append({
            "journal_name": item["journal_name"],
            "source_path": item.get("_source_path", ""),
            "record_count": value(item, "record_count"),
            "author_title_coverage_rate": value(item, "author_title_coverage_rate"),
            "author_stage_or_degree_coverage_rate": value(item, "author_stage_or_degree_coverage_rate"),
            "fund_field_coverage_rate": value(item, "fund_field_coverage_rate"),
            "student_author_record_ratio": value(item, "student_author_record_ratio"),
            "senior_first_student_second_ratio": value(item, "senior_first_student_second_ratio"),
            "senior_first_master_second_ratio": value(item, "senior_first_master_second_ratio"),
            "senior_first_phd_second_ratio": value(item, "senior_first_phd_second_ratio"),
            "funded_record_ratio": value(item, "funded_record_ratio"),
            "first_author_title_top": top_distribution(value(item, "first_author_title_distribution", {}), 5),
            "second_author_stage_top": top_distribution(value(item, "second_author_stage_distribution", {}), 5),
            "fund_level_top": top_distribution(value(item, "fund_level_distribution", {}), 5),
            "evidence_strength": value(item, "evidence_strength", "weak"),
        })

    highest_student = sorted(comparison_rows, key=lambda row: row["student_author_record_ratio"], reverse=True)[:3]
    highest_funded = sorted(comparison_rows, key=lambda row: row["funded_record_ratio"], reverse=True)[:3]
    strength = evidence_strength(journals)
    stats = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "journal_count": len(journals),
        "comparison_rows": comparison_rows,
        "highest_student_author_ratio": highest_student,
        "highest_funded_record_ratio": highest_funded,
        "evidence_strength": strength,
        "warnings": warnings,
    }

    lines = [
        "# 多期刊作者身份对比报告",
        "",
        f"- 对比期刊数：{len(journals)}",
        f"- 证据强度：{strength}",
        "",
        "## 降级提示",
    ]
    lines.extend([f"- {item}" for item in warnings] or ["- 暂无阻断性降级提示。"])
    lines.extend(["", "## 核心指标对比"])
    for row in comparison_rows:
        lines.extend([
            f"### {row['journal_name']}",
            f"- 样本数：{row['record_count']}",
            f"- 职称覆盖率：{row['author_title_coverage_rate']}",
            f"- 学位/身份覆盖率：{row['author_stage_or_degree_coverage_rate']}",
            f"- 基金字段覆盖率：{row['fund_field_coverage_rate']}",
            f"- 学生作者参与比例：{row['student_author_record_ratio']}",
            f"- 高年资一作 + 学生二作线索比例：{row['senior_first_student_second_ratio']}",
            f"- 高年资一作 + 硕士二作线索比例：{row['senior_first_master_second_ratio']}",
            f"- 高年资一作 + 博士二作线索比例：{row['senior_first_phd_second_ratio']}",
            f"- 基金论文比例：{row['funded_record_ratio']}",
            "- 第一作者职称高频：" + "；".join([f"{entry['name']}({entry['count']})" for entry in row["first_author_title_top"]]),
            "- 第二作者身份高频：" + "；".join([f"{entry['name']}({entry['count']})" for entry in row["second_author_stage_top"]]),
            "- 基金层级高频：" + "；".join([f"{entry['name']}({entry['count']})" for entry in row["fund_level_top"]]),
            "",
        ])
    lines.extend(["## 相对提示"])
    lines.append("- 学生作者参与比例排序靠前：" + "；".join([row["journal_name"] for row in highest_student]) if highest_student else "- 学生作者参与比例排序靠前：无")
    lines.append("- 基金论文比例排序靠前：" + "；".join([row["journal_name"] for row in highest_funded]) if highest_funded else "- 基金论文比例排序靠前：无")
    lines.extend([
        "",
        "## 不得推断项",
        "- 不得从作者身份对比推断录用倾向、私人关系或投稿捷径。",
        "- 对比结果只用于改投判断和补证据提示，不替代投稿匹配评分。",
    ])

    Path(args.output_json).write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.output_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
