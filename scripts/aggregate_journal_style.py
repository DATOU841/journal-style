#!/usr/bin/env python3
"""Aggregate per-article style profiles into downstream-consumable locks."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path

from journal_style_runtime import (
    ReleaseIntegrityError,
    assert_release_integrity,
    integrity_failure_payload,
    now_iso,
)

SCRIPTS_DIR = Path(__file__).resolve().parent
RUN_STAGE_GATES = SCRIPTS_DIR / "run_stage_gates.py"
DEFAULT_INPUT = "03-analysis/fulltext-layer/per-article-style-profiles.json"
DEFAULT_OUTPUT = "03-analysis/fulltext-layer/journal-style-aggregation-bundle.json"
DEFAULT_PENDING = "03-analysis/fulltext-layer/pending-materials.json"

REQUIRED_ARTIFACTS = [
    "journal-style-constraints-lock",
    "journal-format-convention-profile",
    "journal-argument-preference-profile",
    "journal-reference-ecology-lock",
    "journal-polish-consumption-pack",
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


def dist(values) -> dict:
    vals = sorted(numbers(values))
    if not vals:
        return {"min": None, "max": None, "median": None, "q1": None, "q3": None}
    mid = statistics.median(vals)
    return {
        "min": int(vals[0]) if vals[0].is_integer() else vals[0],
        "max": int(vals[-1]) if vals[-1].is_integer() else vals[-1],
        "median": int(mid) if float(mid).is_integer() else round(mid, 2),
        "q1": int(vals[len(vals) // 4]) if vals[len(vals) // 4].is_integer() else vals[len(vals) // 4],
        "q3": int(vals[(len(vals) * 3) // 4]) if vals[(len(vals) * 3) // 4].is_integer() else vals[(len(vals) * 3) // 4],
    }


def mode(values) -> str | None:
    vals = [str(value) for value in values if value not in (None, "", [], {})]
    if not vals:
        return None
    return Counter(vals).most_common(1)[0][0]


def flatten_evidence(profiles: list[dict]) -> list[dict]:
    evidence = []
    for profile in profiles:
        for entry in profile.get("evidence_index") or []:
            evidence.append(entry)
    return evidence


def conclusion_strength(sample_count: int) -> tuple[str, str, str]:
    if sample_count < 10:
        return "sample_observation", "low", "样本不足"
    if sample_count < 20:
        return "preliminary", "low", "10-19篇，仅初步偏好"
    return "stable", "medium", ""


def build_consumption_pack(target: str, sample_count: int, profiles: list[dict], evidence_index: list[dict]) -> dict:
    dims = [profile.get("dimensions") or {} for profile in profiles]
    length = dist((dim.get("length_band") or {}).get("char_count_total") for dim in dims)
    paragraphs = dist((dim.get("paragraph_stats") or {}).get("paragraph_count") for dim in dims)
    sections = dist((dim.get("section_hierarchy") or {}).get("section_count") for dim in dims)
    keywords = dist((dim.get("keywords_profile") or {}).get("count") for dim in dims)
    refs = dist((dim.get("reference_profile") or {}).get("reference_count") for dim in dims)
    notes = mode((dim.get("notes_profile") or {}).get("type") for dim in dims) or "unknown"
    title_patterns = sorted(set(
        str((dim.get("title_structure") or {}).get("pattern"))
        for dim in dims
        if (dim.get("title_structure") or {}).get("pattern")
    ))
    rhythms = sorted(set(
        str((dim.get("argument_rhythm") or {}).get("type"))
        for dim in dims
        if (dim.get("argument_rhythm") or {}).get("type")
    ))
    strength, confidence, degrade = conclusion_strength(sample_count)
    return {
        "schema": "journal_style_profile_v1",
        "target_journal": target,
        "source_evidence_scope": "mu_fulltext_core_pack",
        "metadata_only": False,
        "completion_label": "FULLTEXT_READY",
        "fulltext_layer_status": "done",
        "sample_count": sample_count,
        "confidence": confidence,
        "conclusion_strength": strength,
        "degrade_label": degrade,
        "constraints": {
            "length_band": {
                "min": length["min"],
                "max": length["max"],
                "median": length["median"],
                "advisory_only": True,
                "source": "reference_only",
            },
            "paragraph_band": {"min": paragraphs["min"], "max": paragraphs["max"], "median": paragraphs["median"]},
            "section_hierarchy": {"section_min": sections["min"], "section_max": sections["max"], "median": sections["median"]},
            "abstract_keywords": {"keyword_min": keywords["min"], "keyword_max": keywords["max"], "median": keywords["median"]},
            "notes_convention": {"type": notes},
            "reference_constraints": {"reference_min": refs["min"], "reference_max": refs["max"], "median": refs["median"]},
            "title_style": {"patterns": title_patterns},
            "argument_rhythm": {"preferred": rhythms},
        },
        "gap_checklist": [] if sample_count >= 10 else ["MinerU/mu ready articles below 10"],
        "evidence_index": evidence_index,
    }


def artifact(name: str, dimension: str, sample_count: int, payload: dict, evidence_index: list[dict]) -> dict:
    strength, confidence, degrade = conclusion_strength(sample_count)
    if dimension in {"argument_style", "reference_ecology"} and sample_count < 30 and confidence == "high":
        confidence = "medium"
    return {
        "name": name,
        "dimension": dimension,
        "sample_count": sample_count,
        "coverage": 1.0 if sample_count else 0.0,
        "confidence": confidence,
        "conclusion_strength": strength,
        "degrade_label": degrade,
        "payload": payload,
        "evidence_index": evidence_index,
    }


def build_bundle(batch: dict) -> dict:
    profiles = batch.get("profiles") or []
    sample_count = len(profiles)
    target = batch.get("target_journal") or ""
    evidence_index = flatten_evidence(profiles)
    consumption_pack = build_consumption_pack(target, sample_count, profiles, evidence_index)
    constraints = consumption_pack["constraints"]
    artifacts = [
        artifact("journal-style-constraints-lock", "format_convention", sample_count, {"constraints": constraints}, evidence_index),
        artifact("journal-format-convention-profile", "format_convention", sample_count, {
            "length_band": constraints["length_band"],
            "paragraph_band": constraints["paragraph_band"],
            "section_hierarchy": constraints["section_hierarchy"],
            "abstract_keywords": constraints["abstract_keywords"],
            "notes_convention": constraints["notes_convention"],
        }, evidence_index),
        artifact("journal-argument-preference-profile", "argument_style", sample_count, {
            "argument_rhythm": constraints["argument_rhythm"],
            "title_style": constraints["title_style"],
        }, evidence_index),
        artifact("journal-reference-ecology-lock", "reference_ecology", sample_count, {
            "reference_constraints": constraints["reference_constraints"],
        }, evidence_index),
        artifact("journal-polish-consumption-pack", "downstream_consumption", sample_count, consumption_pack, evidence_index),
    ]
    return {
        "schema": "journal_style_aggregation_bundle_v1",
        "target_journal": target,
        "source_profiles": batch.get("source_pack"),
        "sample_count": sample_count,
        "artifacts": artifacts,
        "created_at": now_iso(),
    }


def write_pending(path: Path, input_path: Path, verdict: dict) -> None:
    write_json(path, {
        "schema": "journal_style_pending_materials_v1",
        "reason": "per-article-profile-complete gate did not pass; aggregation was not generated",
        "source_profiles": str(input_path),
        "gate_verdict": verdict.get("verdict"),
        "problems": verdict.get("problems") or [],
        "warnings": verdict.get("warnings") or [],
        "created_at": now_iso(),
    })


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate per-article profiles into journal-style locks.")
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
        print(json.dumps(integrity_failure_payload(exc, "aggregate_journal_style", args.task_dir), ensure_ascii=False, indent=2))
        return 3
    task_dir = args.task_dir.expanduser().resolve()
    input_path = (task_dir / args.input).resolve() if not Path(args.input).is_absolute() else Path(args.input).resolve()
    output_path = (task_dir / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output).resolve()
    pending_path = (task_dir / args.pending_output).resolve() if not Path(args.pending_output).is_absolute() else Path(args.pending_output).resolve()
    if not input_path.exists():
        verdict = {"verdict": "NO_GO", "problems": [f"input profiles missing: {input_path}"], "warnings": []}
        write_pending(pending_path, input_path, verdict)
        print(json.dumps({"ok": False, "pending": str(pending_path), "reason": verdict["problems"][0]}, ensure_ascii=False, indent=2))
        return 1
    profile_verdict = run_gate("per-article-profile-complete", input_path)
    if profile_verdict.get("verdict") not in {"PASS", "DEGRADED"}:
        write_pending(pending_path, input_path, profile_verdict)
        print(json.dumps({"ok": False, "pending": str(pending_path), "gate_verdict": profile_verdict.get("verdict")}, ensure_ascii=False, indent=2))
        return 1
    bundle = build_bundle(load_json(input_path))
    write_json(output_path, bundle)
    aggregation_verdict = run_gate("aggregation-threshold", output_path)
    ok = aggregation_verdict.get("verdict") in {"PASS", "DEGRADED"}
    print(json.dumps({
        "ok": ok,
        "output": str(output_path),
        "artifact_count": len(bundle.get("artifacts") or []),
        "profile_gate_verdict": profile_verdict.get("verdict"),
        "aggregation_gate_verdict": aggregation_verdict.get("verdict"),
        "problems": aggregation_verdict.get("problems") or [],
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
