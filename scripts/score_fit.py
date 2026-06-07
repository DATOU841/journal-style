#!/usr/bin/env python3
"""Compute journal fit score from section scores."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


WEIGHTS = {
    "topic_fit": 20,
    "material_fit": 15,
    "method_argument_fit": 15,
    "title_abstract_fit": 10,
    "reference_ecology_fit": 15,
    "format_fit": 10,
    "trend_newness_fit": 10,
    "risk_deduction": 5,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score journal submission fit.")
    parser.add_argument("--input", help="JSON file with section scores.")
    parser.add_argument("--evidence", help="Optional JSON file with evidence index.")
    parser.add_argument("--output", help="Optional output JSON path.")
    return parser.parse_args()


def normalize(value: float, weight: int) -> float:
    if weight == 0:
        return 0.0
    return max(0.0, min(10.0, value)) / 10.0 * weight


def main() -> int:
    args = parse_args()
    if args.input:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    else:
        data = json.load(sys.stdin)

    evidence = data.get("evidence", {})
    if args.evidence:
        evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))

    scores = {}
    total = 0.0
    risk_deduction = 0.0
    for key, weight in WEIGHTS.items():
        raw = float(data.get(key, 0))
        if key == "risk_deduction":
            raw = max(0.0, min(5.0, raw))
            risk_deduction = raw
            scaled = 0.0
        else:
            scaled = normalize(raw, weight)
        scores[key] = round(raw, 2)
        total += scaled

    total += 5.0 - risk_deduction
    total = max(0.0, min(100.0, total))
    result = {"total": round(total, 1), "scores": scores, "weights": WEIGHTS, "evidence": evidence}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
