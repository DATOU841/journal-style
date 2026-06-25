#!/usr/bin/env python3
"""Offline fixtures for jiansuo-ruku 0.2.11 sidecar adaptation.

All data is synthetic. The fixtures do not call CNKI/WoS/Zotero/PDF/MinerU/RAG,
servers, vector stores, or real Wenheng tasks.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / "scripts"
PY = sys.executable

RESULTS: list[dict] = []


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([PY, *args], capture_output=True, text=True)


def record(name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append({"fixture": name, "passed": bool(passed), "detail": detail})


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def make_safe_sidecars(task: Path) -> None:
    write_json(task / "025-rag-import" / "fulltext" / "A1" / "manifest.json", {
        "stable_id": "A1",
        "title": "碑帖传播研究",
        "full_md_path": "025-rag-import/fulltext/A1/full.md",
        "sha256": "sha-fixture",
        "is_vectorized": True,
    })
    write_json(task / "025-rag-import" / "fulltext" / "fulltext-index.json", {
        "contains_rag_chunks": False,
        "contains_vectors": False,
        "items": [
            {
                "stable_id": "A1",
                "source_id": "A1",
                "title": "碑帖传播研究",
                "full_md_path": "025-rag-import/fulltext/A1/full.md",
                "sha256": "sha-fixture",
                "is_vectorized": True,
            }
        ],
    })
    (task / "025-rag-import" / "fulltext" / "A1" / "full.md").write_text(
        "SENTINEL_SHOULD_NOT_APPEAR_IN_MANIFEST\n",
        encoding="utf-8",
    )
    write_json(task / "026-knowledge-workbench" / "source-role-register.json", {
        "sources": [
            {
                "source_id": "A1",
                "stable_id": "A1",
                "title": "碑帖传播研究",
                "year": 2024,
                "journal": "测试刊",
                "consumption_role": "same_journal",
                "bucket_tags": ["target_journal_ecosystem", "same_topic"],
            }
        ]
    })
    write_json(task / "026-knowledge-workbench" / "rag-query-seed-pack.json", {
        "query_seeds": [
            {
                "dimension_tag": "title_style",
                "query": "题名结构 主副标题",
                "seed_terms": ["题名", "主副标题"],
                "source_id_refs": ["A1"],
            }
        ]
    })
    write_json(task / "026-knowledge-workbench" / "gap-ledger.json", {
        "gaps": [
            {"gap_id": "G1", "category": "fulltext", "severity": "medium", "source_need": "补全文样本"}
        ]
    })
    write_json(task / "026-knowledge-workbench" / "downstream-consumption-manifest.json", {
        "items": [
            {"name": "source-role-register", "rel_path": "026-knowledge-workbench/source-role-register.json", "ready": True}
        ]
    })
    (task / "026-knowledge-workbench" / "sources").mkdir(parents=True, exist_ok=True)
    (task / "026-knowledge-workbench" / "sources" / "A1.md").write_text(
        "SENTINEL_SOURCE_CARD_SHOULD_NOT_APPEAR\n",
        encoding="utf-8",
    )
    (task / "02-kb-builder").mkdir(parents=True, exist_ok=True)
    (task / "02-kb-builder" / "zotero-reference-full-bibliography.md").write_text(
        "- 碑帖传播研究. 2024.\n- 书学史材料研究. 2023.\n- 图像与书法. 2022.\n",
        encoding="utf-8",
    )
    (task / "02-kb-builder" / "zotero-reference-master.md").write_text(
        "- 碑帖传播研究. 2024.\n- 图像与书法. 2022.\n",
        encoding="utf-8",
    )


def gate_sidecar(path: Path) -> tuple[dict, subprocess.CompletedProcess[str]]:
    proc = run([str(SCRIPTS / "run_stage_gates.py"), "--gate", "jiansuo-sidecar-safety", "--input", str(path)])
    try:
        return json.loads(proc.stdout), proc
    except json.JSONDecodeError:
        return {}, proc


def fx_missing_sidecar_pass(tmp: Path) -> None:
    verdict, proc = gate_sidecar(tmp / "missing" / "00-intake" / "jiansuo-sidecar-manifest.json")
    record(
        "missing_sidecar_pass",
        proc.returncode == 0 and verdict.get("verdict") == "PASS",
        proc.stdout[:200] + proc.stderr[:200],
    )


def fx_safe_manifest_no_fullmd_read(tmp: Path) -> None:
    task = tmp / "safe"
    make_safe_sidecars(task)
    proc = run([str(SCRIPTS / "build_jiansuo_sidecar_manifest.py"), "--task-dir", str(task)])
    manifest_path = task / "00-intake" / "jiansuo-sidecar-manifest.json"
    text = manifest_path.read_text(encoding="utf-8") if manifest_path.exists() else ""
    data = read_json(manifest_path) if manifest_path.exists() else {}
    verdict, gate_proc = gate_sidecar(manifest_path)
    record(
        "safe_manifest_no_fullmd_read",
        proc.returncode == 0
        and "SENTINEL_SHOULD_NOT_APPEAR_IN_MANIFEST" not in text
        and "SENTINEL_SOURCE_CARD_SHOULD_NOT_APPEAR" not in text
        and (data.get("safety") or {}).get("full_md_files_opened") == 0
        and data.get("fulltext_index", {}).get("item_count") == 1
        and verdict.get("verdict") == "PASS"
        and gate_proc.returncode == 0,
        proc.stdout[:160] + proc.stderr[:160] + gate_proc.stderr[:160],
    )


def fx_leakage_must_fail(tmp: Path) -> None:
    task = tmp / "leak"
    write_json(task / "026-knowledge-workbench" / "source-role-register.json", {
        "sources": [
            {
                "source_id": "B1",
                "title": "泄漏样本",
                "chunk_text": "this should be blocked",
                "token": "abcdef1234567890",
            }
        ]
    })
    proc = run([str(SCRIPTS / "build_jiansuo_sidecar_manifest.py"), "--task-dir", str(task)])
    manifest_path = task / "00-intake" / "jiansuo-sidecar-manifest.json"
    verdict, gate_proc = gate_sidecar(manifest_path)
    record(
        "leakage_must_fail",
        proc.returncode == 0
        and gate_proc.returncode == 1
        and verdict.get("verdict") == "NO_GO"
        and verdict.get("problems"),
        gate_proc.stdout[:300] + gate_proc.stderr[:160],
    )


def fx_seed_plan_no_rag(tmp: Path) -> None:
    task = tmp / "seed-plan"
    make_safe_sidecars(task)
    run([str(SCRIPTS / "build_jiansuo_sidecar_manifest.py"), "--task-dir", str(task)])
    proc = run([str(SCRIPTS / "build_journal_style_rag_seed_plan.py"), "--task-dir", str(task)])
    plan = read_json(task / "02-topic-library" / "journal-style-rag-query-seed-plan.json")
    record(
        "seed_plan_no_rag",
        proc.returncode == 0
        and plan.get("executed") is False
        and plan.get("execution_scope") == "planning_only_no_rag_call"
        and plan.get("seed_count") == 1,
        proc.stdout[:160] + proc.stderr[:160],
    )


def fx_core_library_role_boost(tmp: Path) -> None:
    task = tmp / "core-role"
    make_safe_sidecars(task)
    run([str(SCRIPTS / "build_jiansuo_sidecar_manifest.py"), "--task-dir", str(task)])
    input_csv = task / "screened.csv"
    with input_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["title", "item_key", "year", "section", "abstract", "keywords"])
        writer.writeheader()
        writer.writerow({"title": "碑帖传播研究", "item_key": "A1", "year": "2024", "section": "专题", "abstract": "碑帖 书学史", "keywords": "碑帖"})
        writer.writerow({"title": "展览评论", "item_key": "B2", "year": "2023", "section": "评论", "abstract": "展览", "keywords": "展览"})
        writer.writerow({"title": "建筑景观研究", "item_key": "B3", "year": "2022", "section": "景观", "abstract": "景观", "keywords": "景观"})
        writer.writerow({"title": "设计教育观察", "item_key": "B4", "year": "2021", "section": "教育", "abstract": "教育", "keywords": "教育"})
    out = task / "02b-core-library" / "core-library-ledger.json"
    proc = run([
        str(SCRIPTS / "select_core_library.py"),
        "--input", str(input_csv),
        "--output-json", str(out),
        "--target-ratio", "0.25",
        "--topic-keywords", "碑帖",
        "--sidecar-manifest", str(task / "00-intake" / "jiansuo-sidecar-manifest.json"),
    ])
    payload = read_json(out) if out.exists() else {}
    selected = (payload.get("selected") or [{}])[0]
    record(
        "core_library_role_boost",
        proc.returncode == 0
        and payload.get("verdict") == "PASS"
        and payload.get("ratio") == 0.25
        and payload.get("sidecar_context", {}).get("active") is True
        and selected.get("title") == "碑帖传播研究"
        and selected.get("source_role_tags")
        and selected.get("sidecar_role_evidence", {}).get("sidecar_role_boost", 0) > 0,
        proc.stdout[:200] + proc.stderr[:200],
    )


def fx_bibliography_scope_counts(tmp: Path) -> None:
    task = tmp / "bibliography"
    make_safe_sidecars(task)
    proc = run([str(SCRIPTS / "build_jiansuo_sidecar_manifest.py"), "--task-dir", str(task)])
    manifest = read_json(task / "00-intake" / "jiansuo-sidecar-manifest.json")
    scope = manifest.get("bibliography_scope") or {}
    derived = read_json(task / "03-analysis" / "metadata-layer" / "bibliography-scope-coverage.json")
    record(
        "bibliography_scope_counts",
        proc.returncode == 0
        and scope.get("full_bibliography", {}).get("entry_count") == 3
        and scope.get("master_bibliography", {}).get("entry_count") == 2
        and scope.get("formal_coverage_rate") == 0.6667
        and derived.get("schema") == "journal_style_bibliography_scope_coverage_v1",
        proc.stdout[:160] + proc.stderr[:160],
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for fx in [
            fx_missing_sidecar_pass,
            fx_safe_manifest_no_fullmd_read,
            fx_leakage_must_fail,
            fx_seed_plan_no_rag,
            fx_core_library_role_boost,
            fx_bibliography_scope_counts,
        ]:
            try:
                fx(tmp)
            except Exception as exc:  # noqa: BLE001
                record(fx.__name__, False, f"crash: {exc}")
    passed = sum(1 for item in RESULTS if item["passed"])
    total = len(RESULTS)
    print(json.dumps({"ok": passed == total, "passed": passed, "total": total, "results": RESULTS}, ensure_ascii=False, indent=2))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
