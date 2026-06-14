#!/usr/bin/env python3
"""Build config/release-manifest.json for journal-style.

The manifest freezes the bytes of load-bearing config and runner scripts. Runtime
entrypoints refuse to run when those bytes drift, so task windows cannot patch
workflow-states.json or gate code to force progress.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from journal_style_runtime import (
    CONFIG_DIR,
    MANIFEST_TRACKED_CONFIG,
    MANIFEST_TRACKED_SCRIPTS,
    RELEASE_MANIFEST_PATH,
    SKILL_ROOT,
    now_iso,
    sha256_file,
)


def git_head() -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(SKILL_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip()
    except Exception:
        return ""


def tracked_release_files() -> list[str]:
    return list(MANIFEST_TRACKED_CONFIG) + list(MANIFEST_TRACKED_SCRIPTS)


def tracked_files_clean_against_head() -> tuple[bool, str]:
    """Return whether load-bearing files are clean relative to HEAD.

    Used by the release runbook before re-signing. It prevents a task window from
    editing workflow/gate files and immediately re-blessing those bytes without a
    visible git commit.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(SKILL_ROOT), "diff", "--quiet", "HEAD", "--", *tracked_release_files()],
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        return False, f"git diff check failed: {exc}"
    if proc.returncode == 0:
        return True, ""
    if proc.returncode == 1:
        return False, "tracked config/scripts differ from HEAD; commit reviewed changes before re-signing release-manifest.json"
    return False, (proc.stderr or proc.stdout or f"git diff exited {proc.returncode}").strip()


def build_manifest() -> dict:
    version = (SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    head = git_head()
    config_sha = {rel: sha256_file(SKILL_ROOT / rel) for rel in MANIFEST_TRACKED_CONFIG}
    script_sha = {rel: sha256_file(SKILL_ROOT / rel) for rel in MANIFEST_TRACKED_SCRIPTS}
    return {
        "schema": "journal_style_release_manifest_v1",
        "release_id": f"journal-style@{version}+{head[:12] if head else 'bundle'}",
        "version": version,
        "manifest_generated_from_commit": head,
        "generated_at": now_iso(),
        "config_sha256": config_sha,
        "script_sha256": script_sha,
        "mode_policy": {
            "git": {
                "required": ["manifest present", "tracked config/script sha match manifest"],
                "note": "Commit hash is recorded as provenance, not used as a self-referential same-commit check.",
            },
            "bundle": {
                "required": ["manifest present", "tracked config/script sha match manifest"],
            },
        },
        "_rule": "Runtime detects post-release byte drift in manifest-tracked config/scripts and fails closed. Release re-signing must use --require-clean; task-level path adaptation must use task-adapter-manifest.json.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build journal-style release manifest.")
    parser.add_argument("--check", action="store_true", help="Do not write; exit non-zero if current manifest differs.")
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="Before writing, require manifest-tracked config/scripts to match HEAD. Use this in the release runbook.",
    )
    args = parser.parse_args()

    if args.require_clean:
        clean, detail = tracked_files_clean_against_head()
        if not clean:
            print(f"refusing to re-sign release manifest: {detail}", file=sys.stderr)
            return 2

    manifest = build_manifest()
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if args.check:
        if not RELEASE_MANIFEST_PATH.is_file():
            print("release-manifest.json missing", file=sys.stderr)
            return 1
        existing = json.loads(RELEASE_MANIFEST_PATH.read_text(encoding="utf-8"))
        # Compare only the content that pins integrity, NOT the volatile
        # generated_at timestamp (which would make --check always report stale).
        drift = []
        for field in ("version", "config_sha256", "script_sha256"):
            if existing.get(field) != manifest.get(field):
                drift.append(field)
        if drift:
            print(f"release-manifest.json is stale: {', '.join(drift)}", file=sys.stderr)
            return 1
        print("release-manifest.json is current")
        return 0
    RELEASE_MANIFEST_PATH.write_text(text, encoding="utf-8")
    print(json.dumps({
        "manifest": str(RELEASE_MANIFEST_PATH),
        "release_id": manifest["release_id"],
        "tracked_config": len(manifest["config_sha256"]),
        "tracked_scripts": len(manifest["script_sha256"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
