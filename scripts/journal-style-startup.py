#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from wenheng_native import add_wenheng_args, verify_wenheng_native


def main() -> int:
    parser = argparse.ArgumentParser(description="Wenheng native startup gate for journal-style.")
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--target-journal", default="")
    parser.add_argument("--compact", action="store_true")
    add_wenheng_args(parser)
    args = parser.parse_args()
    binding = verify_wenheng_native(args)
    args.task_dir.mkdir(parents=True, exist_ok=True)
    handoff = {
        "schema": "journal_style_c03_handoff_v1",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "target_journal": args.target_journal,
        "wenheng_native_binding": binding,
        "source_skill": "journal-style",
        "source_fields_policy": "task_id/source_run_id/evidence_path/source_skill are derived by Wenheng backend and must not be user supplied",
        "style_memory_not_applicable_reason": binding.get("style_memory_not_applicable_reason"),
        "allowed_c03_adjustments": ["priority", "submission_stage", "tags", "next_action", "match_status"],
        "production_evidence_allowed": bool(binding.get("production_evidence_allowed")),
    }
    output = args.task_dir / "c03-journal-profile-handoff.json"
    output.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload = {"status": "ok", "handoff_path": str(output), "wenheng_native_binding": binding} if args.compact else handoff
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
