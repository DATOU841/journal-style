#!/usr/bin/env python3
"""Score a user manuscript against a calibrated journal-fit model.

The output is a fit report, not text polishing and not an acceptance prediction.
When no manuscript feature JSON is supplied, the script writes a pending-feature
report rather than inventing a score.
"""

from __future__ import annotations

import argparse
import json
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
DEFAULT_MODEL = "04-fit-evaluation/journal-fit-scoring-model.json"
DEFAULT_OUTPUT = "04-fit-evaluation/submission-fit-score.md"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_gate(gate: str, input_path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(RUN_STAGE_GATES), "--gate", gate, "--input", str(input_path)],
        capture_output=True,
        text=True,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"verdict": "NO_GO", "problems": ["gate did not return valid JSON", proc.stderr.strip()[:400]], "warnings": []}


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def band_value(band: dict, low_key: str, high_key: str, fallback_low: float, fallback_high: float) -> tuple[float, float, str]:
    try:
        low = float(band.get(low_key))
        high = float(band.get(high_key))
        return low, high, "journal_style_aggregation_bundle"
    except Exception:
        return fallback_low, fallback_high, "fallback"


def constraints_from_model(model: dict) -> dict:
    constraints = model.get("scoring_constraints") or {}
    return {
        "section": band_value(constraints.get("section_hierarchy") or {}, "section_min", "section_max", 3, 6),
        "keyword": band_value(constraints.get("abstract_keywords") or {}, "keyword_min", "keyword_max", 3, 6),
        "reference": band_value(constraints.get("reference_constraints") or {}, "reference_min", "reference_max", 15, 60),
        "raw": constraints,
    }


def outside(value, low: float, high: float) -> bool:
    try:
        current = float(value)
    except Exception:
        return False
    return current < low or current > high


def score_features(features: dict, model: dict) -> tuple[float, list[dict]]:
    section_count = float(features.get("section_count") or 0)
    keyword_count = float(features.get("keyword_count") or 0)
    reference_count = float(features.get("reference_count") or 0)
    has_notes = bool(features.get("has_notes"))
    has_abstract = bool(features.get("has_abstract", True))
    deductions: list[dict] = []
    constraints = constraints_from_model(model)
    section_low, section_high, section_source = constraints["section"]
    keyword_low, keyword_high, keyword_source = constraints["keyword"]
    reference_low, reference_high, reference_source = constraints["reference"]
    score = float((model.get("published_score_distribution") or {}).get("median") or 80)
    if section_count and outside(section_count, section_low, section_high):
        score -= 8
        deductions.append({
            "dimension": "format_convention",
            "deduction": 8,
            "reason": f"章节数量偏离目标期刊区间 {section_low:g}-{section_high:g}",
            "constraint_source": section_source,
        })
    if keyword_count and outside(keyword_count, keyword_low, keyword_high):
        score -= 5
        deductions.append({
            "dimension": "title_abstract",
            "deduction": 5,
            "reason": f"关键词数量偏离目标期刊区间 {keyword_low:g}-{keyword_high:g}",
            "constraint_source": keyword_source,
        })
    if reference_count and outside(reference_count, reference_low, reference_high):
        score -= 8
        deductions.append({
            "dimension": "reference_ecology",
            "deduction": 8,
            "reason": f"参考文献数量偏离目标期刊区间 {reference_low:g}-{reference_high:g}",
            "constraint_source": reference_source,
        })
    if not has_notes:
        score -= 3
        deductions.append({"dimension": "format_convention", "deduction": 3, "reason": "缺少注释体例特征，需人工核对"})
    if not has_abstract:
        score -= 5
        deductions.append({"dimension": "title_abstract", "deduction": 5, "reason": "缺少摘要特征，无法完成摘要适配判断"})
    return round(clamp(score), 1), deductions


def percentile(score: float, distribution: dict) -> str:
    if score < float(distribution.get("q1") or 0):
        return "below_q1"
    if score < float(distribution.get("median") or 0):
        return "q1_to_median"
    if score < float(distribution.get("q3") or 0):
        return "median_to_q3"
    return "above_q3"


def render_report(model: dict, features: dict | None, score: float | None, deductions: list[dict]) -> str:
    constraints = constraints_from_model(model)
    lines = [
        "# 投稿适配评分",
        "",
        "本报告基于 `journal_fit_scoring_model_v1` 的已刊样本回放校准结果生成；不是主编模拟，不预测录用概率。",
        "",
        f"- 目标期刊：{model.get('target_journal') or ''}",
        f"- 校准样本数：{(model.get('calibration') or {}).get('replay_sample_count')}",
        f"- 已刊样本区间：{json.dumps(model.get('published_score_distribution') or {}, ensure_ascii=False)}",
        f"- 评分约束来源：{(model.get('scoring_constraints') or {}).get('source') or 'fallback'}",
        f"- 目标期刊章节区间：{constraints['section'][0]:g}-{constraints['section'][1]:g}",
        f"- 目标期刊关键词区间：{constraints['keyword'][0]:g}-{constraints['keyword'][1]:g}",
        f"- 目标期刊参考文献区间：{constraints['reference'][0]:g}-{constraints['reference'][1]:g}",
        "",
    ]
    if features is None:
        lines.extend([
            "## 结论",
            "",
            "待补稿件结构化特征，暂不做用户稿件分位定位。",
            "",
            "## 需要补充",
            "",
            "- section_count",
            "- keyword_count",
            "- reference_count",
            "- has_notes",
            "- has_abstract",
        ])
        return "\n".join(lines) + "\n"
    dist = model.get("published_score_distribution") or {}
    lines.extend([
        "## 结论",
        "",
        f"- 用户稿适配分：{score}",
        f"- 相对已刊样本位置：{percentile(float(score or 0), dist)}",
        "",
        "## 维度扣分",
        "",
    ])
    if deductions:
        for item in deductions:
            source = item.get("constraint_source")
            source_text = f"，约束来源：{source}" if source else ""
            lines.append(f"- {item['dimension']}：-{item['deduction']}，{item['reason']}{source_text}")
    else:
        lines.append("- 未见结构化特征触发的主要扣分项。")
    lines.extend([
        "",
        "## 补强建议",
        "",
        "- 按目标期刊约束锁核对章节、关键词、注释和参考文献生态。",
        "- 缺失维度必须回到 journal-style 消费包或检索入库补材料，不在此处补写正文。",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score user manuscript features against a calibrated model.")
    parser.add_argument("--task-dir", type=Path, default=Path("."))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--manuscript-features", default="")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        assert_release_integrity()
    except ReleaseIntegrityError as exc:
        print(json.dumps(integrity_failure_payload(exc, "score_user_manuscript", args.task_dir), ensure_ascii=False, indent=2))
        return 3
    task_dir = args.task_dir.expanduser().resolve()
    model_path = (task_dir / args.model).resolve() if not Path(args.model).is_absolute() else Path(args.model).resolve()
    output_path = (task_dir / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output).resolve()
    if not model_path.exists():
        print(json.dumps({"ok": False, "reason": f"scoring model missing: {model_path}"}, ensure_ascii=False, indent=2))
        return 1
    gate = run_gate("submission-fit-ready", model_path)
    if gate.get("verdict") not in {"PASS", "DEGRADED"}:
        print(json.dumps({"ok": False, "reason": "calibrated model gate did not pass", "problems": gate.get("problems") or []}, ensure_ascii=False, indent=2))
        return 1
    model = load_json(model_path)
    features = None
    if args.manuscript_features:
        feature_path = (task_dir / args.manuscript_features).resolve() if not Path(args.manuscript_features).is_absolute() else Path(args.manuscript_features).resolve()
        if feature_path.exists():
            features = load_json(feature_path)
    if features is None:
        report = render_report(model, None, None, [])
    else:
        score, deductions = score_features(features, model)
        report = render_report(model, features, score, deductions)
    write_text(output_path, report)
    print(json.dumps({"ok": True, "output": str(output_path), "features_used": features is not None}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
