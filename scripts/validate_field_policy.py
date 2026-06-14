#!/usr/bin/env python3
"""P5: two-way field-policy validation over a JSONL profiles / ledger file.

Direction A (credential leak): forbidden field names (exact, lowercased) or
value-bearing regexes -> NO_GO.
Direction B (over-redaction, this round's RC4): public metadata fields redacted
to placeholders -> non-blocking warning only (per user directive: only
credentials block; public metadata is never intercepted).

The 'key' substring is intentionally NOT a forbidden key, so item_key /
item_key_hash are never falsely flagged.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from journal_style_runtime import load_field_policy


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
    parser = argparse.ArgumentParser(description="Two-way field-policy validation (P5).")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    policy = load_field_policy()
    allow = policy["public_metadata_allowlist"]
    deny = policy["credential_denylist"]
    over = allow.get("over_redaction_check", {})

    forbidden_keys = {k.lower() for k in deny["forbidden_keys_exact"]}
    value_patterns = [re.compile(p, re.I) for p in deny["value_patterns"]]
    placeholder_patterns = [re.compile(p) for p in over.get("placeholder_patterns", [])]
    allow_fields = allow["fields"]

    input_path = args.input.expanduser().resolve()
    rows = load_jsonl(input_path) if input_path.exists() else []
    problems: list[str] = []
    warnings: list[str] = []

    if not rows:
        problems.append(f"input empty or missing: {input_path}")

    for row in rows:
        line = row.get("_line_no")
        # Direction A: forbidden field names
        present_forbidden = sorted(forbidden_keys.intersection({str(k).lower() for k in row}))
        if present_forbidden:
            problems.append(f"line {line}: forbidden credential field(s): {', '.join(present_forbidden)}")
        # Direction A: value-bearing secret patterns in serialized row
        serialized = json.dumps(row, ensure_ascii=False)
        for pat in value_patterns:
            if pat.search(serialized):
                problems.append(f"line {line}: credential-like value matched: {pat.pattern}")
                break
        # Direction B: over-redaction of public metadata.
        # Per user directive: only credentials block; public metadata is never
        # intercepted. Over-redaction stays as a non-blocking warning so the
        # signal is kept (RC4) without failing the gate.
        if over.get("enabled"):
            for field in allow_fields:
                val = row.get(field)
                if isinstance(val, str) and any(p.search(val) for p in placeholder_patterns):
                    warnings.append(
                        f"line {line}: public metadata field '{field}' looks redacted to placeholder "
                        f"'{val[:24]}' (non-blocking notice)"
                    )

    verdict = "NO_GO" if problems else "DEGRADED" if warnings else "PASS"
    result = {
        "gate": "field-policy",
        "verdict": verdict,
        "problems": problems,
        "warnings": warnings,
        "details": {"row_count": len(rows), "input": str(input_path)},
        "_two_way": {
            "credential_leak_checked": True,
            "over_redaction_checked": bool(over.get("enabled")),
        },
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).expanduser().write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if verdict in {"PASS", "DEGRADED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
