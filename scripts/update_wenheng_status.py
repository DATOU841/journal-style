#!/usr/bin/env python3
"""Incrementally update journal-style Wenheng status JSON."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update wenheng-center-status.json incrementally.")
    parser.add_argument("--status-file", required=True, help="Path to wenheng-center-status.json")
    parser.add_argument("--update", required=True, help="JSON object of dotted-path updates.")
    parser.add_argument("--history-file", help="Optional JSONL history path.")
    return parser.parse_args()


def set_dotted(data: dict, dotted: str, value) -> None:
    parts = dotted.split(".")
    current = data
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def main() -> int:
    args = parse_args()
    path = Path(args.status_file)
    data = json.loads(path.read_text(encoding="utf-8"))
    before = deepcopy(data)
    updates = json.loads(args.update)
    if not isinstance(updates, dict):
        raise SystemExit("--update must be a JSON object")

    for dotted, value in updates.items():
        set_dotted(data, dotted, value)

    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    changed = {"updated_at": data["updated_at"], "updates": updates}
    if args.history_file:
        history_path = Path(args.history_file)
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text("", encoding="utf-8") if not history_path.exists() else None
        with history_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(changed, ensure_ascii=False) + "\n")

    print(json.dumps({"ok": True, "changed": changed}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

