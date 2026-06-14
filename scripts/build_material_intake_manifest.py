#!/usr/bin/env python3
"""P3: Step-0 material-intake manifest.

Register every available input asset once, up front, with its sha256, so later
steps can only consume registered assets and missing fields surface immediately
instead of at Step 8. Source-profiles provenance (P4) is later checked back
against this manifest.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from journal_style_runtime import now_iso, sha256_artifact

# Candidate assets the workflow may consume. Presence is recorded, absence is
# reported as a gap; nothing here triggers retrieval.
CANDIDATE_ASSETS = [
    ("title_intake", "01-title-intake/journal-full-title-list.xlsx"),
    ("title_intake_csv", "01-title-intake/journal-full-title-list.csv"),
    ("title_screening_ledger", "015-title-screening/title-screening-ledger.json"),
    ("topic_library", "02-topic-library/topic-related-title-list.xlsx"),
    ("core_library_ledger", "02b-core-library/core-library-ledger.json"),
    ("core_library_selected", "02b-core-library/core-library-selected.csv"),
    ("rag_import_handoff", "025-rag-import/rag-import-handoff.md"),
    ("zotero_pdf_rag_handoff", "06-gates/zotero-pdf-rag-handoff.json"),
    ("source_profiles", "03-analysis/fulltext-layer/source-profiles-bridge-v2.jsonl"),
    ("official_identity", "00-official/journal-identity-confirmation.md"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Step-0 material-intake manifest.")
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--extra-asset", action="append", default=[],
                        help="Extra asset as name=relpath; recorded if present.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task_dir = args.task_dir.expanduser().resolve()
    assets = list(CANDIDATE_ASSETS)
    for spec in args.extra_asset:
        if "=" in spec:
            name, rel = spec.split("=", 1)
            assets.append((name.strip(), rel.strip()))

    registered = {}
    gaps = []
    for name, rel in assets:
        path = task_dir / rel
        if path.exists():
            registered[name] = {
                "rel_path": rel,
                "abs_path": str(path),
                "sha256": sha256_artifact(path),
                "is_dir": path.is_dir(),
            }
        else:
            gaps.append({"asset": name, "rel_path": rel})

    manifest = {
        "schema": "journal_style_material_intake_manifest_v1",
        "task_dir": str(task_dir),
        "created_at": now_iso(),
        "registered_assets": registered,
        "registered_count": len(registered),
        "gaps": gaps,
        "gap_count": len(gaps),
        "_rule": "Later steps may only consume registered assets. source_profiles provenance must trace back here (P4).",
    }
    out_dir = task_dir / "00-intake"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "material-intake-manifest.json"
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest_path": str(out_path), "registered_count": len(registered), "gap_count": len(gaps)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
