#!/usr/bin/env python3
"""Build a calibrated journal-fit scoring model from aggregation evidence."""

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
DEFAULT_INPUT = "03-analysis/fulltext-layer/journal-style-aggregation-bundle.json"
DEFAULT_PROFILES = "03-analysis/fulltext-layer/per-article-style-profiles.json"
DEFAULT_OUTPUT = "04-fit-evaluation/journal-fit-scoring-model.json"


DIMENSIONS = [
    ("format_convention", 15, "由格式体例聚合锁校准，衡量节级、摘要关键词、篇幅和注释体例适配。"),
    ("argument_style", 20, "由论证偏好画像校准，衡量问题提出、材料推进和结论收束适配。"),
    ("reference_ecology", 20, "由参考文献生态锁校准，衡量参考数量、近年文献和中外比例适配。"),
    ("title_abstract", 15, "由题名、摘要和关键词画像校准，衡量入口信息组织适配。"),
    ("material_method", 20, "由材料与方法画像校准，衡量核心材料类型和方法路径适配。"),
    ("risk_control", 10, "单列运营和证据风险扣分，不预测录用概率。"),
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
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"verdict": "NO_GO", "problems": ["gate did not return valid JSON", proc.stderr.strip()[:400]], "warnings": []}


def numbers(values) -> list[float]:
    out: list[float] = []
    for value in values:
        try:
            out.append(float(value))
        except Exception:
            pass
    return out


def score_distribution(scores: list[float]) -> dict:
    vals = sorted(numbers(scores))
    if not vals:
        raise ValueError("cannot build distribution without replay scores")
    median = statistics.median(vals)
    return {
        "sample_count": len(vals),
        "min": round(vals[0], 2),
        "q1": round(vals[len(vals) // 4], 2),
        "median": round(float(median), 2),
        "q3": round(vals[(len(vals) * 3) // 4], 2),
        "max": round(vals[-1], 2),
        "source": "replay_scores",
    }


def find_artifact(bundle: dict, name: str) -> dict:
    for artifact in bundle.get("artifacts") or []:
        if artifact.get("name") == name:
            return artifact
    return {}


def extract_constraints(bundle: dict) -> dict:
    pack_artifact = find_artifact(bundle, "journal-polish-consumption-pack")
    pack_payload = pack_artifact.get("payload") or {}
    constraints = pack_payload.get("constraints")
    if isinstance(constraints, dict) and constraints:
        return constraints
    lock_artifact = find_artifact(bundle, "journal-style-constraints-lock")
    lock_payload = lock_artifact.get("payload") or {}
    return lock_payload.get("constraints") or {}


def compact_constraints(constraints: dict) -> dict:
    return {
        "source": "journal_style_aggregation_bundle",
        "fallback_used": False,
        "section_hierarchy": constraints.get("section_hierarchy") or {},
        "abstract_keywords": constraints.get("abstract_keywords") or {},
        "reference_constraints": constraints.get("reference_constraints") or {},
        "notes_convention": constraints.get("notes_convention") or {},
    }


def add_band_deduction(deductions: list[dict], dimension: str, value, band: dict, low_key: str, high_key: str, label: str, weight: float) -> None:
    try:
        current = float(value)
        low = float(band.get(low_key))
        high = float(band.get(high_key))
    except Exception:
        return
    try:
        median = float(band.get("median"))
    except Exception:
        median = (low + high) / 2
    spread = max(high - low, 1.0)
    if current < low:
        deduction = min(weight, weight * (0.5 + (low - current) / spread))
    elif current > high:
        deduction = min(weight, weight * (0.5 + (current - high) / spread))
    else:
        deduction = min(weight * 0.5, weight * abs(current - median) / spread)
    if deduction > 0:
        deductions.append({
            "dimension": dimension,
            "deduction": round(deduction, 2),
            "reason": f"{label}相对目标期刊已刊样本中位数存在偏离",
            "value": current,
            "target_min": low,
            "target_max": high,
            "target_median": median,
            "constraint_source": "journal_style_aggregation_bundle",
        })


def feature_values(profile: dict) -> dict:
    dims = profile.get("dimensions") or {}
    return {
        "section_count": (dims.get("section_hierarchy") or {}).get("section_count"),
        "keyword_count": (dims.get("keywords_profile") or {}).get("count"),
        "reference_count": (dims.get("reference_profile") or {}).get("reference_count"),
        "has_notes": bool((dims.get("notes_profile") or {}).get("available", True)),
        "has_abstract": bool((dims.get("abstract_profile") or {}).get("has_abstract", True)),
        "material_types": dims.get("material_types") or [],
        "method_types": dims.get("method_types") or [],
        "argument_rhythm": (dims.get("argument_rhythm") or {}).get("type"),
    }


def replay_score(profile: dict, constraints: dict) -> dict:
    values = feature_values(profile)
    deductions: list[dict] = []
    add_band_deduction(deductions, "format_convention", values.get("section_count"), constraints.get("section_hierarchy") or {}, "section_min", "section_max", "章节数量", 12)
    add_band_deduction(deductions, "title_abstract", values.get("keyword_count"), constraints.get("abstract_keywords") or {}, "keyword_min", "keyword_max", "关键词数量", 8)
    add_band_deduction(deductions, "reference_ecology", values.get("reference_count"), constraints.get("reference_constraints") or {}, "reference_min", "reference_max", "参考文献数量", 12)
    if not values.get("has_notes"):
        deductions.append({"dimension": "format_convention", "deduction": 3, "reason": "已刊样本缺少可识别注释体例"})
    if not values.get("has_abstract"):
        deductions.append({"dimension": "title_abstract", "deduction": 5, "reason": "已刊样本缺少摘要特征"})
    if any(str(item).startswith("gap:") for item in values.get("material_types") or []):
        deductions.append({"dimension": "material_method", "deduction": 4, "reason": "材料类型缺少稳定锚点"})
    if any(str(item).startswith("gap:") for item in values.get("method_types") or []):
        deductions.append({"dimension": "material_method", "deduction": 4, "reason": "方法类型缺少稳定锚点"})
    if not values.get("argument_rhythm"):
        deductions.append({"dimension": "argument_style", "deduction": 4, "reason": "论证节奏缺少可识别特征"})
    score = max(0.0, 100.0 - sum(float(item.get("deduction") or 0) for item in deductions))
    return {
        "article_id": profile.get("article_id") or profile.get("source_article_id"),
        "score": round(score, 2),
        "feature_values": values,
        "deductions": deductions,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate journal-fit scoring model from published sample evidence.")
    parser.add_argument("--task-dir", type=Path, default=Path("."))
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--profiles", default=DEFAULT_PROFILES)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--rounds-completed", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        assert_release_integrity()
    except ReleaseIntegrityError as exc:
        print(json.dumps(integrity_failure_payload(exc, "calibrate_fit_scoring", args.task_dir), ensure_ascii=False, indent=2))
        return 3
    task_dir = args.task_dir.expanduser().resolve()
    input_path = (task_dir / args.input).resolve() if not Path(args.input).is_absolute() else Path(args.input).resolve()
    profiles_path = (task_dir / args.profiles).resolve() if not Path(args.profiles).is_absolute() else Path(args.profiles).resolve()
    output_path = (task_dir / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output).resolve()
    if not input_path.exists():
        print(json.dumps({"ok": False, "reason": f"aggregation bundle missing: {input_path}"}, ensure_ascii=False, indent=2))
        return 1
    if not profiles_path.exists():
        print(json.dumps({"ok": False, "reason": f"per-article profile batch missing: {profiles_path}"}, ensure_ascii=False, indent=2))
        return 1
    aggregation_verdict = run_gate("aggregation-threshold", input_path)
    if aggregation_verdict.get("verdict") not in {"PASS", "DEGRADED"}:
        print(json.dumps({
            "ok": False,
            "reason": "aggregation gate did not pass",
            "gate_verdict": aggregation_verdict.get("verdict"),
            "problems": aggregation_verdict.get("problems") or [],
        }, ensure_ascii=False, indent=2))
        return 1
    profile_verdict = run_gate("per-article-profile-complete", profiles_path)
    if profile_verdict.get("verdict") not in {"PASS", "DEGRADED"}:
        print(json.dumps({
            "ok": False,
            "reason": "per-article profile gate did not pass",
            "gate_verdict": profile_verdict.get("verdict"),
            "problems": profile_verdict.get("problems") or [],
        }, ensure_ascii=False, indent=2))
        return 1
    bundle = load_json(input_path)
    profile_batch = load_json(profiles_path)
    profiles = profile_batch.get("profiles") or []
    sample_count = len(profiles)
    if sample_count < 10:
        print(json.dumps({"ok": False, "reason": "published replay sample below 10"}, ensure_ascii=False, indent=2))
        return 1
    constraints = compact_constraints(extract_constraints(bundle))
    replay_scores = [replay_score(profile, constraints) for profile in profiles]
    distribution = score_distribution([item["score"] for item in replay_scores])
    model = {
        "schema": "journal_fit_scoring_model_v1",
        "target_journal": bundle.get("target_journal") or "",
        "model_name": "journal_fit_scoring_model_v1",
        "not_editor_simulation": True,
        "no_acceptance_prediction": True,
        "calibration": {
            "status": "calibrated",
            "rounds_completed": max(1, int(args.rounds_completed or 1)),
            "replay_sample_count": sample_count,
            "source": "per_article_profile_replay",
            "source_profiles": profiles_path.relative_to(task_dir).as_posix() if profiles_path.is_relative_to(task_dir) else str(profiles_path),
            "source_aggregation_bundle": input_path.relative_to(task_dir).as_posix() if input_path.is_relative_to(task_dir) else str(input_path),
        },
        "dimensions": [
            {"dimension": name, "weight": weight, "rationale": rationale}
            for name, weight, rationale in DIMENSIONS
        ],
        "scoring_constraints": constraints,
        "replay_scores": replay_scores,
        "published_score_distribution": distribution,
        "created_at": now_iso(),
        "_boundary": "This model is a journal-fit calibration aid, not editor simulation and not acceptance prediction.",
    }
    write_json(output_path, model)
    scoring_verdict = run_gate("scoring-replay-calibrated", output_path)
    ok = scoring_verdict.get("verdict") in {"PASS", "DEGRADED"}
    print(json.dumps({
        "ok": ok,
        "output": str(output_path),
        "aggregation_gate_verdict": aggregation_verdict.get("verdict"),
        "profile_gate_verdict": profile_verdict.get("verdict"),
        "scoring_gate_verdict": scoring_verdict.get("verdict"),
        "problems": scoring_verdict.get("problems") or [],
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
