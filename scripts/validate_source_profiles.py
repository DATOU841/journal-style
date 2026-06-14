#!/usr/bin/env python3
"""P4: validate the source_profiles handoff contract.

Because the runner never re-runs CNKI/Zotero/PDF/RAG (D1), all trust in upstream
work rests on this contract. Beyond field/join completeness, provenance MUST
trace back to the Step0 material-intake manifest: the profiles file has to be
registered there and its current sha256 must match. Field-complete but
untraceable profiles are rejected (NO_GO).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from journal_style_runtime import (
    CONFIG_DIR,
    load_json,
    sha256_artifact,
)

SCHEMA_PATH = CONFIG_DIR / "source-profiles-schema.json"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate source_profiles handoff contract (P4).")
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path, help="source-profiles-bridge JSONL")
    parser.add_argument("--core-ledger", type=Path, default=None)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    task_dir = args.task_dir.expanduser().resolve()
    input_path = args.input.expanduser().resolve()
    schema = load_json(SCHEMA_PATH)
    problems: list[str] = []
    warnings: list[str] = []

    rows = load_jsonl(input_path) if input_path.exists() else []
    if not rows:
        problems.append(f"source_profiles empty or missing: {input_path}")

    # 1) required fields
    required = schema["row_required_fields"]
    recommended = schema["row_recommended_fields"]
    for row in rows:
        missing = [f for f in required if not row.get(f)]
        if missing:
            problems.append(f"line {row.get('_line_no')}: missing required fields: {', '.join(missing)}")

    # 2) recommended coverage = mean per-field presence (not "every field on every row").
    # A field that is legitimately sparse (e.g. doi) must not drag the whole score to 0.
    if rows:
        per_field = {
            f: sum(1 for r in rows if r.get(f) not in (None, "", [])) / len(rows)
            for f in recommended
        }
        rec_present = sum(per_field.values()) / len(recommended) if recommended else 1.0
        warn_below = schema["field_completeness"]["recommended_field_coverage_warn_below"]
        if rec_present < warn_below:
            low = sorted([f for f, c in per_field.items() if c < 0.5])
            warnings.append(
                f"recommended field mean coverage {rec_present:.2f} below {warn_below}"
                + (f"; sparse fields: {', '.join(low)}" if low else "")
            )

    # 3) core join completeness back to Step7 ledger.
    # The schema decides severity: a join that cannot be verified (missing ledger
    # or no usable join keys) is NO_GO per verdict_when_join_key_absent, not a
    # silent pass; a verifiable but low rate is DEGRADED per verdict_below_min.
    join_cfg = schema["join"]
    below_verdict = join_cfg.get("verdict_below_min", "DEGRADED")
    absent_verdict = join_cfg.get("verdict_when_join_key_absent", "NO_GO")

    def _emit(verdict_label: str, message: str) -> None:
        if verdict_label == "NO_GO":
            problems.append(message)
        else:
            warnings.append(message)

    core_rows = [r for r in rows if r.get("core_library_selected")]
    if core_rows:
        ledger_path = args.core_ledger or (task_dir / "02b-core-library/core-library-ledger.json")
        ledger_keys = set()
        if ledger_path.exists():
            ledger = load_json(ledger_path)
            for item in (ledger.get("selected") or ledger.get("items") or []):
                if item.get("record_id"):
                    ledger_keys.add(("record_id", item["record_id"]))
                if item.get("item_key"):
                    ledger_keys.add(("item_key", item["item_key"]))
                if item.get("title"):
                    ledger_keys.add(("title_year", item.get("title"), item.get("year")))
        else:
            _emit(absent_verdict, f"core ledger not found for join check: {ledger_path}")
        if not ledger_keys and ledger_path.exists():
            # ledger exists but yields no usable join key -> cannot verify provenance
            _emit(absent_verdict,
                  f"core ledger has no usable join key (record_id/item_key/title): {ledger_path}")
        if ledger_keys:
            joined = 0
            for r in core_rows:
                if (
                    ("record_id", r.get("record_id")) in ledger_keys
                    or ("item_key", r.get("item_key")) in ledger_keys
                    or ("title_year", r.get("title"), r.get("year")) in ledger_keys
                ):
                    joined += 1
            rate = joined / len(core_rows)
            if rate < join_cfg["core_join_completeness_min"]:
                _emit(below_verdict,
                      f"core join completeness {rate:.3f} below {join_cfg['core_join_completeness_min']} "
                      f"({joined}/{len(core_rows)})")

    # 4) provenance back-reference to Step0 manifest (the命门)
    prov = schema["provenance_back_reference"]
    manifest_path = task_dir / "00-intake/material-intake-manifest.json"
    if prov.get("require_registered_in_manifest"):
        if not manifest_path.exists():
            problems.append(f"Step0 manifest missing; cannot verify provenance: {manifest_path}")
        else:
            manifest = load_json(manifest_path)
            asset = (manifest.get("registered_assets") or {}).get(prov["manifest_asset_name"])
            if not asset:
                problems.append(
                    f"source_profiles not registered in Step0 manifest as "
                    f"'{prov['manifest_asset_name']}' (untraceable provenance -> NO_GO)"
                )
            elif prov.get("require_sha_match"):
                live_sha = sha256_artifact(input_path) if input_path.exists() else None
                if asset.get("sha256") != live_sha:
                    problems.append(
                        "source_profiles sha mismatch vs Step0 manifest "
                        "(file changed since registration -> NO_GO)"
                    )
    if prov.get("require_source_ref"):
        no_ref = [r.get("_line_no") for r in rows if not r.get("source_ref")]
        if no_ref:
            warnings.append(f"{len(no_ref)} rows lack source_ref provenance")

    verdict = "NO_GO" if problems else "DEGRADED" if warnings else "PASS"
    result = {
        "gate": "source-profiles-contract",
        "verdict": verdict,
        "problems": problems,
        "warnings": warnings,
        "details": {
            "row_count": len(rows),
            "core_selected_count": len(core_rows),
            "input": str(input_path),
        },
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).expanduser().write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if verdict in {"PASS", "DEGRADED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
