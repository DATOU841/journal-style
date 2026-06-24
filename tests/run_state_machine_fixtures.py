#!/usr/bin/env python3
"""P7: offline regression fixtures for the journal-style state machine.

Each fixture reproduces one of this round's real drift accidents and asserts the
new machine controls catch it. The MUST-FAIL guards exist because if they ever
pass, the moat is fake.

Moat redesign (this patch): the runner no longer trusts a stored gate verdict's
marker/sha. It RE-RUNS the gate logic over the live artifact at consume time. So
a forged verdict -- even one that copies the generator marker and carries a
correct sha over the artifact -- cannot let a bad artifact pass.

Covered:
- RC2: hand-written PASS gate over a bad artifact -> runner re-runs -> rejected
- RC2 hard: forged verdict that copies marker AND correct sha over a bad
  artifact -> runner re-runs the logic -> still rejected (marker-copy guard)
- P2: tampered artifact -> re-run catches it regardless of stored verdict
- RC5: runner stops fail-closed at first unsatisfied step, does not skip
- step00 unblock: a valid material-intake manifest passes its gate
- P4: source_profiles untraceable to Step0 manifest -> NO_GO
- P5: credential leak -> NO_GO; item_key not falsely flagged; public metadata ok
- P6: gateless step can never be resume-skipped; gate-fail prior-run rejected
- handoff ratio regression: missing pdf/rag ratios must not silently pass
- dimension-evidence: below-threshold dimension is downgraded, not silently passed
"""

from __future__ import annotations

import hashlib
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / "scripts"
PY = sys.executable

RESULTS = []


def run(args, **kw):
    return subprocess.run([PY, *args], capture_output=True, text=True, **kw)


def record(name, passed, detail=""):
    RESULTS.append({"fixture": name, "passed": bool(passed), "detail": detail})


def write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        path.write_text(obj, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_runner():
    sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module("journal_style_runner")


def make_core_ledger(n_selected=30, n_total=100):
    sel = [{"record_id": f"R{i}", "title": f"t{i}", "year": 2025, "selected": True,
            "scores": {"topic_similarity": 0.8}, "total": 0.8} for i in range(n_selected)]
    rej = [{"title": f"r{i}", "reason": "low relevance"} for i in range(n_total - n_selected)]
    return {"screened_count": n_total, "selected": sel, "rejected": rej}


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_mu_article(index: int) -> dict:
    fulltext = (
        f"题名：期刊体例样本{index}\n"
        "摘要：本文围绕材料、方法与论证结构展开分析。\n"
        "一、问题提出\n"
        "本文从研究史和材料缺口进入问题。\n"
        "二、材料与方法\n"
        "文章采用文献考辨、案例比较和图像分析方法。\n"
        "三、结论\n"
        "文章回到问题意识并收束判断。\n"
        "注释：[1] 出处说明。\n"
        "参考文献：[1] 示例文献。\n"
    )
    return {
        "article_id": f"A{index:02d}",
        "title": f"期刊体例样本{index}",
        "authors": [f"作者{index}"],
        "year": 2020 + index % 5,
        "column": "专题研究",
        "mu_fulltext": fulltext,
        "fulltext_sha256": text_sha(fulltext),
        "core_library_joined": True,
        "abstract": "本文围绕材料、方法与论证结构展开分析。",
        "keywords": ["材料", "方法", "论证"],
        "section_tree": [
            {"level": 1, "title": "问题提出", "order": 1},
            {"level": 1, "title": "材料与方法", "order": 2},
            {"level": 1, "title": "结论", "order": 3},
        ],
        "paragraph_sequence": [
            {"section_ref": "1", "order": 1, "char_count": 80},
            {"section_ref": "2", "order": 2, "char_count": 90},
            {"section_ref": "3", "order": 3, "char_count": 70},
        ],
        "notes": {"type": "footnote", "count": 1},
        "reference_list": [
            {"raw": "[1] 示例文献。", "year": 2020, "lang": "zh", "is_self_journal": False},
        ],
        "char_count_total": len(fulltext),
        "provenance": {
            "source_ledger": "06-gates/zotero-pdf-rag-handoff.json",
            "extraction_method": "MinerU",
            "mu_version": "mineru-fixture-1",
        },
    }


def make_mu_pack(count: int = 20) -> dict:
    return {
        "schema": "journal_style_mu_fulltext_core_pack_v1",
        "target_journal": "测试刊",
        "source_skill": "检索入库",
        "mu_processing_required": True,
        "mu_processor": "MinerU",
        "ordinary_rag_is_not_substitute": True,
        "articles": [make_mu_article(i) for i in range(1, count + 1)],
    }


def make_profile(article: dict) -> dict:
    dims = {
        "title_structure": {"pattern": "对象+问题"},
        "abstract_profile": {"char_count": len(article["abstract"])},
        "keywords_profile": {"count": len(article["keywords"])},
        "length_band": {"char_count_total": article["char_count_total"]},
        "paragraph_stats": {"paragraph_count": len(article["paragraph_sequence"])},
        "section_hierarchy": {"max_level": 1},
        "intro_pattern": {"type": "问题切入"},
        "material_types": ["文献", "图像"],
        "method_types": ["考辨", "比较"],
        "argument_rhythm": {"type": "问题-材料-结论"},
        "notes_profile": article["notes"],
        "reference_profile": {"reference_count": len(article["reference_list"])},
        "conclusion_pattern": {"type": "回应问题"},
    }
    return {
        "schema": "per_article_style_profile_v1",
        "article_id": article["article_id"],
        "source_article_id": article["article_id"],
        "dimensions": dims,
        "evidence_index": [{
            "article_id": article["article_id"],
            "evidence_path": f"articles/{article['article_id']}/section_tree",
            "provenance": article["provenance"],
        }],
        "downstream_constraints": [{"type": "section_count", "min": 3, "max": 5}],
    }


def make_profile_batch(pack: dict) -> dict:
    return {
        "schema": "journal_style_per_article_profile_batch_v1",
        "target_journal": pack["target_journal"],
        "source_pack": "03-analysis/fulltext-layer/mu-fulltext-core-pack.json",
        "ready_article_count": len(pack["articles"]),
        "profiles": [make_profile(article) for article in pack["articles"]],
    }


def make_aggregation(sample_count: int = 20) -> dict:
    evidence = [
        {"article_id": f"A{i:02d}", "evidence_path": f"per-article/A{i:02d}.json", "provenance": {"source": "fixture"}}
        for i in range(1, sample_count + 1)
    ]
    names = [
        ("journal-style-constraints-lock", "format_convention"),
        ("journal-format-convention-profile", "format_convention"),
        ("journal-argument-preference-profile", "argument_style"),
        ("journal-reference-ecology-lock", "reference_ecology"),
        ("journal-polish-consumption-pack", "downstream_consumption"),
    ]
    return {
        "schema": "journal_style_aggregation_bundle_v1",
        "target_journal": "测试刊",
        "sample_count": sample_count,
        "artifacts": [
            {
                "name": name,
                "dimension": dimension,
                "sample_count": sample_count,
                "coverage": 1.0,
                "confidence": "medium",
                "conclusion_strength": "stable",
                "degrade_label": "",
                "evidence_index": evidence,
            }
            for name, dimension in names
        ],
    }


def make_scoring(calibrated: bool = True) -> dict:
    replay_count = 20 if calibrated else 5
    replay_scores = [
        {"article_id": f"A{i:02d}", "score": 78 + (i % 5)}
        for i in range(1, replay_count + 1)
    ]
    scores = sorted(float(item["score"]) for item in replay_scores)
    distribution = {
        "sample_count": replay_count,
        "min": scores[0],
        "q1": scores[len(scores) // 4],
        "median": scores[len(scores) // 2] if len(scores) % 2 else (scores[len(scores) // 2 - 1] + scores[len(scores) // 2]) / 2,
        "q3": scores[(len(scores) * 3) // 4],
        "max": scores[-1],
        "source": "replay_scores",
    }
    return {
        "schema": "journal_fit_scoring_model_v1",
        "target_journal": "测试刊",
        "model_name": "journal_fit_scoring_model_v1",
        "not_editor_simulation": True,
        "no_acceptance_prediction": True,
        "calibration": {
            "status": "calibrated" if calibrated else "not_started",
            "rounds_completed": 1 if calibrated else 0,
            "replay_sample_count": replay_count,
            "source": "per_article_profile_replay",
        },
        "dimensions": [
            {"dimension": "format_convention", "weight": 15, "rationale": "由体例约束锁校准"},
            {"dimension": "reference_ecology", "weight": 15, "rationale": "由参考文献生态锁校准"},
        ],
        "scoring_constraints": {
            "source": "journal_style_aggregation_bundle",
            "section_hierarchy": {"section_min": 3, "section_max": 5, "median": 3},
            "abstract_keywords": {"keyword_min": 3, "keyword_max": 5, "median": 3},
            "reference_constraints": {"reference_min": 1, "reference_max": 1, "median": 1},
        },
        "replay_scores": replay_scores,
        "published_score_distribution": distribution,
    }


def make_consumption_pack(sample_count: int = 20) -> dict:
    return {
        "schema": "journal_style_profile_v1",
        "target_journal": "测试刊",
        "source_evidence_scope": "mu_fulltext_core_pack",
        "metadata_only": False,
        "sample_count": sample_count,
        "constraints": {"section_hierarchy": {"section_min": 3, "section_max": 5}},
        "gap_checklist": [],
        "evidence_index": [{
            "article_id": "A01",
            "evidence_path": "per-article/A01.json",
            "provenance": {"source": "fixture"},
        }],
    }


def make_metadata_ready_task(tmp: Path, name: str, mode: str = "standard") -> Path:
    task = tmp / name
    task.mkdir()
    write(task / "00-intake" / "material-intake-manifest.json", {
        "schema": "journal_style_material_intake_manifest_v1",
        "registered_assets": {"title_intake_csv": {"rel_path": "01-title-intake/journal-full-title-list.csv", "sha256": "fixture"}}
    })
    write(task / "00-intake" / "task-init.json", {"schema": "journal_style_task_init_v1"})
    write(task / "current-run-state.json", {"run_mode": mode, "requested_mode": mode})
    write(task / "00-official" / "journal-identity-confirmation.md", "identity confirmed\n")
    write(task / "00-official" / "journal-official-and-web-evidence.md", "official evidence\n")
    write(task / "01-title-intake" / "journal-full-title-list.xlsx", "fixture\n")
    write(task / "01-title-intake" / "journal-title-ingestion-log.md", "log\n")
    write(task / "015-title-screening" / "title-screening-ledger.json", {"kept": []})
    write(task / "06-gates" / "title-screening-gate.json", {"verdict": "PASS"})
    write(task / "02-topic-library" / "topic-special-library-plan.md", "plan\n")
    write(task / "02-topic-library" / "topic-related-title-list.xlsx", "fixture\n")
    write(task / "06-gates" / "zotero-pdf-rag-handoff.json", {
        "status": "success", "task_collection_binding": "live", "item_count": 10,
        "item_receipts": [{"title": f"t{i}"} for i in range(10)],
        "pdf_count": 6, "rag_doc_count": 5, "recall_test": {"sampled": 2, "passed": 2}
    })
    write(task / "02b-core-library" / "core-library-ledger.json", make_core_ledger())
    write(task / "02b-core-library" / "core-library-rejected.json", {"rejected": []})
    rows = []
    for index in range(1, 4):
        rows.append(json.dumps({"title": f"t{index}", "abstract": "摘要", "keywords": ["k"], "item_key": f"K{index}"}, ensure_ascii=False))
    write(task / "03-analysis" / "metadata-layer" / "abstract-metadata-ledger.jsonl", "\n".join(rows) + "\n")
    write(task / "05-handoff" / "wenheng-center-status.json", {
        "schema": "journal_style_wenheng_status_v1",
        "pipeline_status": {"metadata_analysis": "done", "fulltext_analysis": "blocked", "overall_journal_style": "blocked"},
        "analysis_layers": {
            "metadata_layer_status": "done",
            "fulltext_layer_status": "blocked",
            "completion_label": "METADATA_ONLY_NOT_FULLTEXT_READY",
            "fulltext_evidence": {"fulltext_sample_count": 0, "rag_available_rate": 0.0, "pdf_coverage_rate": 0.0}
        }
    })
    return task


def add_fulltext_ready_artifacts(task: Path, calibrated: bool = True) -> None:
    pack = make_mu_pack(20)
    write(task / "03-analysis" / "fulltext-layer" / "mu-fulltext-core-pack.json", pack)
    write(task / "03-analysis" / "fulltext-layer" / "per-article-style-profiles.json", make_profile_batch(pack))
    write(task / "03-analysis" / "fulltext-layer" / "journal-style-aggregation-bundle.json", make_aggregation(20))
    for rel in [
        "journal-rag-fulltext-pattern-report.md",
        "journal-method-material-report.md",
        "journal-argument-style-report.md",
        "journal-reference-ecology-report.md",
        "journal-reference-network-report.md",
    ]:
        write(task / "03-analysis" / "fulltext-layer" / rel, f"{rel} fixture\n")
    write(task / "04-fit-evaluation" / "journal-fit-scoring-model.json", make_scoring(calibrated=calibrated))
    write(task / "04-fit-evaluation" / "submission-fit-score.md", "score fixture\n")
    write(task / "05-handoff" / "journal-polish-consumption-pack.json", make_consumption_pack(20))
    write(task / "05-handoff" / "handoff-to-downstream-skills.md", "handoff fixture\n")
    write(task / "04-fit-evaluation" / "topic-suggestion-report.md", "topic fixture\n")
    write(task / "04-fit-evaluation" / "target-journal-decision.md", "decision fixture\n")


CORE_STEP = {
    "id": "step07_core_library",
    "produces": ["02b-core-library/core-library-ledger.json"],
    "gate": "core-library-selection",
}


def fx_forged_gate_over_bad_artifact(tmp: Path):
    """RC2: a hand-written PASS gate sitting on top of a BAD artifact must not
    help. The runner re-runs the gate logic and gets NO_GO."""
    task = tmp / "forged"; task.mkdir()
    art = task / "02b-core-library" / "core-library-ledger.json"
    write(art, make_core_ledger(n_selected=5))  # ratio 5/100 -> out of range -> NO_GO
    forged = task / "06-gates" / "core-library-selection.json"
    write(forged, {"gate": "core-library-selection", "verdict": "PASS"})  # hand-written
    runner = load_runner()
    ok, detail = runner.step_satisfied(task, CORE_STEP)
    record("forged_gate_over_bad_artifact_rejected (MUST-FAIL guard)", ok is False, detail)


def fx_marker_copy_forgery(tmp: Path):
    """RC2 hard: forged verdict copies the generator marker AND a correct sha
    over a BAD artifact. Trusting marker+sha would pass it; re-running the gate
    logic must still reject it."""
    task = tmp / "markercopy"; task.mkdir()
    art = task / "02b-core-library" / "core-library-ledger.json"
    write(art, make_core_ledger(n_selected=5))  # bad ratio
    runtime = importlib.import_module("journal_style_runtime")
    forged = task / "06-gates" / "core-library-selection.json"
    write(forged, {
        "gate": "core-library-selection",
        "verdict": "PASS",
        "_chain": {
            "generator": runtime.GENERATOR_MARKER,         # marker copied
            "input_path": str(art.resolve()),
            "input_sha256": sha256_file(art),              # correct sha over the bad artifact
        },
    })
    runner = load_runner()
    ok, detail = runner.step_satisfied(task, CORE_STEP)
    record("marker_copy_forgery_rejected (MUST-FAIL guard)", ok is False, detail)


def fx_tampered_artifact(tmp: Path):
    """P2: good artifact passes; tamper it to a bad state; re-run must catch it
    regardless of any stored verdict."""
    task = tmp / "tamper"; task.mkdir()
    art = task / "02b-core-library" / "core-library-ledger.json"
    write(art, make_core_ledger(n_selected=30))  # good
    runner = load_runner()
    ok_before, _ = runner.step_satisfied(task, CORE_STEP)
    write(art, make_core_ledger(n_selected=5))   # tampered -> bad ratio
    ok_after, detail = runner.step_satisfied(task, CORE_STEP)
    record("rerun_detects_tampered_artifact (MUST-FAIL guard)",
           ok_before is True and ok_after is False, detail)


def fx_runner_stops(tmp: Path):
    """RC5: runner blocks fail-closed at step00 on a fresh task, does not skip."""
    task = tmp / "fresh"; task.mkdir()
    proc = run([str(SCRIPTS / "journal_style_runner.py"), "--task-dir", str(task)])
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        out = {}
    record("runner_stops_at_step00", out.get("current_step") == "step00_material_intake",
           out.get("blocked_reason", ""))


def fx_metadata_mode_reaches_metadata_terminal(tmp: Path):
    """Metadata-only modes must not be blocked by the MinerU/mu fulltext gate."""
    task = make_metadata_ready_task(tmp, "metadata_ok", mode="standard")
    proc = run([str(SCRIPTS / "journal_style_runner.py"), "--task-dir", str(task)])
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        out = {}
    record("metadata_mode_reaches_metadata_terminal",
           out.get("current_step") == "completed" and "step07b_mu_fulltext_pack" in out.get("skipped_by_mode", []),
           proc.stdout[:120] + proc.stderr[:120])


def fx_full_mode_requires_mu_pack(tmp: Path):
    """Full mode must still stop at the MinerU/mu fulltext gate when the pack is missing."""
    task = make_metadata_ready_task(tmp, "full_needs_mu", mode="full")
    proc = run([str(SCRIPTS / "journal_style_runner.py"), "--task-dir", str(task)])
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        out = {}
    record("full_mode_requires_mu_pack",
           out.get("current_step") == "step07b_mu_fulltext_pack" and "mu-fulltext-core-pack.json" in out.get("blocked_reason", ""),
           proc.stdout[:120] + proc.stderr[:120])


def fx_full_mode_reaches_handoff_terminal(tmp: Path):
    """A fully satisfied full-mode chain must traverse mu -> per-article -> aggregation -> calibration -> fit -> handoff."""
    task = make_metadata_ready_task(tmp, "full_ok", mode="full")
    add_fulltext_ready_artifacts(task, calibrated=True)
    proc = run([str(SCRIPTS / "journal_style_runner.py"), "--task-dir", str(task)])
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        out = {}
    state = json.loads((task / "current-run-state.json").read_text(encoding="utf-8"))
    completed = (state.get("position") or {}).get("completed") or []
    required = {
        "step07b_mu_fulltext_pack",
        "step08b1_per_article_profile",
        "step08b_fulltext_layer",
        "step09b_scoring_calibration",
        "step09_fit",
        "step10_handoff",
    }
    record("full_mode_reaches_handoff_terminal",
           out.get("current_step") == "completed" and required.issubset(set(completed)),
           proc.stdout[:120] + proc.stderr[:120])


def fx_uncalibrated_model_blocks_before_fit(tmp: Path):
    """A draft score file cannot make step09_fit reachable when the model is uncalibrated."""
    task = make_metadata_ready_task(tmp, "full_uncalibrated", mode="full")
    add_fulltext_ready_artifacts(task, calibrated=False)
    proc = run([str(SCRIPTS / "journal_style_runner.py"), "--task-dir", str(task)])
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        out = {}
    state = json.loads((task / "current-run-state.json").read_text(encoding="utf-8"))
    completed = (state.get("position") or {}).get("completed") or []
    record("uncalibrated_model_blocks_before_fit",
           out.get("current_step") == "step09b_scoring_calibration" and "step09_fit" not in completed,
           proc.stdout[:120] + proc.stderr[:120])


def fx_material_intake_unblocks(tmp: Path):
    """step00 unblock: a valid manifest passes the material-intake gate."""
    task = tmp / "intake"; task.mkdir()
    # need at least one registered asset, so create one and build the manifest
    write(task / "01-title-intake" / "journal-full-title-list.csv", "title,year\nt,2025\n")
    proc = run([str(SCRIPTS / "build_material_intake_manifest.py"), "--task-dir", str(task)])
    manifest = task / "00-intake" / "material-intake-manifest.json"
    gate = run([str(SCRIPTS / "run_stage_gates.py"), "--gate", "material-intake", "--input", str(manifest)])
    try:
        v = json.loads(gate.stdout)
    except json.JSONDecodeError:
        v = {}
    record("material_intake_gate_passes_valid_manifest",
           manifest.exists() and v.get("verdict") in {"PASS", "DEGRADED"}, str(v.get("problems")))


def fx_p4_untraceable(tmp: Path):
    """P4: profiles not registered in Step0 manifest -> NO_GO."""
    task = tmp / "p4"; task.mkdir()
    prof = task / "03-analysis" / "fulltext-layer" / "source-profiles-bridge-v2.jsonl"
    rows = [{"title": "t", "authors": ["a"], "column": "c", "year": 2025,
             "item_key": "K1", "provenance_hash": "h", "record_id": "R1",
             "core_library_selected": True, "source_ref": {"x": 1}}]
    write(prof, "\n".join(json.dumps(r, ensure_ascii=False) for r in rows))
    write(task / "02b-core-library" / "core-library-ledger.json",
          {"screened_count": 1, "selected": [{"record_id": "R1", "item_key": "K1", "title": "t", "year": 2025, "selected": True}]})
    # NO manifest registration
    proc = run([str(SCRIPTS / "validate_source_profiles.py"), "--task-dir", str(task), "--input", str(prof)])
    try:
        v = json.loads(proc.stdout)
    except json.JSONDecodeError:
        v = {}
    record("p4_untraceable_no_go", v.get("verdict") == "NO_GO",
           (v.get("problems") or [""])[0])


def fx_p4_missing_ledger_no_go(tmp: Path):
    """P4 hardened: core rows present but core ledger missing -> NO_GO, not warn."""
    task = tmp / "p4ml"; task.mkdir()
    prof = task / "03-analysis" / "fulltext-layer" / "source-profiles-bridge-v2.jsonl"
    rows = [{"title": "t", "authors": ["a"], "column": "c", "year": 2025,
             "item_key": "K1", "provenance_hash": "h", "record_id": "R1",
             "core_library_selected": True, "source_ref": {"x": 1}}]
    write(prof, "\n".join(json.dumps(r, ensure_ascii=False) for r in rows))
    # register profiles in manifest so provenance passes, isolate the join check
    sha = sha256_file(prof)
    write(task / "00-intake" / "material-intake-manifest.json", {
        "schema": "journal_style_material_intake_manifest_v1",
        "registered_assets": {"source_profiles": {"rel_path": "x", "sha256": sha}},
    })
    # NO core ledger on disk
    proc = run([str(SCRIPTS / "validate_source_profiles.py"), "--task-dir", str(task), "--input", str(prof)])
    try:
        v = json.loads(proc.stdout)
    except json.JSONDecodeError:
        v = {}
    record("p4_missing_core_ledger_no_go", v.get("verdict") == "NO_GO",
           str(v.get("problems"))[:80])


def fx_p5_credential(tmp: Path):
    """P5: credential key -> NO_GO; item_key never falsely flagged."""
    task = tmp / "p5"; task.mkdir()
    prof = task / "p.jsonl"
    write(prof, json.dumps({"title": "t", "item_key": "K1", "api_key": "AKIA1234567890abcd"}, ensure_ascii=False))
    proc = run([str(SCRIPTS / "validate_field_policy.py"), "--input", str(prof)])
    try:
        v = json.loads(proc.stdout)
    except json.JSONDecodeError:
        v = {}
    no_go = v.get("verdict") == "NO_GO"
    flags = " ".join(v.get("problems", []))
    record("p5_credential_no_go_itemkey_safe",
           no_go and "api_key" in flags and "item_key" not in flags.replace("api_key", ""), flags[:80])


def fx_p5_public_ok(tmp: Path):
    """P5: rich public metadata (title/abstract/keywords) must PASS, not be blocked."""
    task = tmp / "p5ok"; task.mkdir()
    prof = task / "p.jsonl"
    write(prof, json.dumps({"title": "真实题名", "authors": ["作者"], "column": "栏目",
                            "abstract": "摘要原文", "keywords": ["k1", "k2"], "item_key": "K1"}, ensure_ascii=False))
    proc = run([str(SCRIPTS / "validate_field_policy.py"), "--input", str(prof)])
    try:
        v = json.loads(proc.stdout)
    except json.JSONDecodeError:
        v = {}
    record("p5_public_metadata_pass", v.get("verdict") == "PASS", str(v.get("problems")))


def fx_p6_gateless_never_skip(tmp: Path):
    """P6: a gateless step (step02_identity) can never be resume-skipped."""
    task = tmp / "p6g"; task.mkdir()
    rm = task / "resume-manifest.json"
    write(rm, {"satisfied_by_prior_run": ["step02_identity"]})
    proc = run([str(SCRIPTS / "journal_style_resume.py"), "--task-dir", str(task), "--resume-manifest", str(rm)])
    try:
        v = json.loads(proc.stdout)
    except json.JSONDecodeError:
        v = {}
    record("p6_gateless_step_never_skipped (MUST-FAIL guard)",
           "step02_identity" in v.get("rejected_must_execute", []),
           str(v.get("decisions"))[:80])


def fx_p6_gatefail_rejected(tmp: Path):
    """P6: a gated step whose prior-run artifact fails the gate is rejected."""
    task = tmp / "p6f"; task.mkdir()
    write(task / "02b-core-library" / "core-library-ledger.json", make_core_ledger(n_selected=5))
    rm = task / "resume-manifest.json"
    write(rm, {"satisfied_by_prior_run": ["step07_core_library"]})
    proc = run([str(SCRIPTS / "journal_style_resume.py"), "--task-dir", str(task), "--resume-manifest", str(rm)])
    try:
        v = json.loads(proc.stdout)
    except json.JSONDecodeError:
        v = {}
    record("p6_gatefail_prior_run_rejected", "step07_core_library" in v.get("rejected_must_execute", []),
           str(v.get("decisions"))[:80])


def fx_p6_gatepass_accepted(tmp: Path):
    """P6: a gated step whose prior-run artifact passes the gate is accepted."""
    task = tmp / "p6p"; task.mkdir()
    write(task / "02b-core-library" / "core-library-ledger.json", make_core_ledger(n_selected=30))
    rm = task / "resume-manifest.json"
    write(rm, {"satisfied_by_prior_run": ["step07_core_library"]})
    proc = run([str(SCRIPTS / "journal_style_resume.py"), "--task-dir", str(task), "--resume-manifest", str(rm)])
    try:
        v = json.loads(proc.stdout)
    except json.JSONDecodeError:
        v = {}
    record("p6_gatepass_prior_run_accepted", "step07_core_library" in v.get("accepted_satisfied", []),
           str(v.get("decisions"))[:80])


def fx_handoff_ratio(tmp: Path):
    """handoff ratio regression: success handoff missing pdf/rag ratios must not pass."""
    task = tmp / "ho"; task.mkdir()
    ho = task / "06-gates" / "zotero-pdf-rag-handoff.json"
    write(ho, {"status": "success", "item_count": 100,
               "item_receipts": [{"title": f"t{i}"} for i in range(90)],
               "pdf_count": 10, "rag_doc_count": 5,
               "recall_test": {"sampled": 5, "passed": 5}})
    proc = run([str(SCRIPTS / "run_stage_gates.py"), "--gate", "jiansuo-handoff", "--input", str(ho)])
    try:
        v = json.loads(proc.stdout)
    except json.JSONDecodeError:
        v = {}
    record("handoff_low_pdf_rag_ratio_no_go", v.get("verdict") == "NO_GO",
           str(v.get("problems"))[:80])


def fx_dimension_below_threshold(tmp: Path):
    """dimension-evidence: a dimension below its configured min must be
    downgraded (DEGRADED), not silently passed."""
    task = tmp / "dim"; task.mkdir()
    rep = task / "dimension-evidence.json"
    write(rep, {"dimensions": [
        {"dimension": "reference_network",
         "counts": {"min_source_articles": 5, "min_reference_records": 20}},
    ]})
    proc = run([str(SCRIPTS / "run_stage_gates.py"), "--gate", "dimension-evidence", "--input", str(rep)])
    try:
        v = json.loads(proc.stdout)
    except json.JSONDecodeError:
        v = {}
    record("dimension_below_threshold_degraded",
           v.get("verdict") == "DEGRADED" and bool(v.get("warnings")), str(v.get("warnings"))[:80])


# ---------------------------------------------------------------------------
# Immutability hotfix fixtures (0.1.9): release integrity + task-local override.
# Drift tests run against an ISOLATED copy of the skill so the real repo is
# never mutated. The copy gets its own release-manifest built over its bytes;
# we then mutate a tracked file in the copy and assert entrypoints fail closed.
# ---------------------------------------------------------------------------

TRACKED_CONFIG_REL = "config/workflow-states.json"
TRACKED_SCRIPT_REL = "scripts/gate_runner.py"


def _clone_skill(tmp: Path, name: str) -> Path:
    dst = tmp / name
    shutil.copytree(SKILL, dst, ignore=shutil.ignore_patterns(".git", ".codegraph", "__pycache__"))
    return dst


def _build_manifest(skill_copy: Path):
    return run([str(skill_copy / "scripts" / "build_release_manifest.py")])


def _runner(skill_copy: Path, task: Path):
    return run([str(skill_copy / "scripts" / "journal_style_runner.py"), "--task-dir", str(task)])


def _is_blocked(proc) -> bool:
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False
    return proc.returncode == 3 and bool(out.get("blocked"))


def fx_integrity_clean_runs(tmp: Path):
    """Baseline: a clean clone with a matching manifest runs (not integrity-blocked)."""
    skill = _clone_skill(tmp, "clean"); _build_manifest(skill)
    task = tmp / "clean_task"; task.mkdir()
    proc = _runner(skill, task)
    # fresh task: runner advances to step00, NOT blocked by integrity (rc != 3)
    record("integrity_clean_clone_runs", proc.returncode == 0, proc.stdout[:80] + proc.stderr[:80])


def fx_integrity_dirty_config_must_fail(tmp: Path):
    """Reproduce this round's accident: edit workflow-states.json after release."""
    skill = _clone_skill(tmp, "dirtycfg"); _build_manifest(skill)
    cfg = skill / TRACKED_CONFIG_REL
    data = json.loads(cfg.read_text(encoding="utf-8"))
    data["steps"][6]["gate_input"] = "025-rag-import/zotero-pdf-rag-handoff-input.json"  # the real drift
    cfg.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    task = tmp / "dirtycfg_task"; task.mkdir()
    record("integrity_dirty_config_must_fail (MUST-FAIL guard)", _is_blocked(_runner(skill, task)))


def fx_integrity_dirty_script_must_fail(tmp: Path):
    """Edit a tracked state-machine script after release -> fail closed."""
    skill = _clone_skill(tmp, "dirtyscript"); _build_manifest(skill)
    scr = skill / TRACKED_SCRIPT_REL
    scr.write_text(scr.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    task = tmp / "dirtyscript_task"; task.mkdir()
    record("integrity_dirty_script_must_fail (MUST-FAIL guard)", _is_blocked(_runner(skill, task)))


def fx_integrity_missing_manifest_must_fail(tmp: Path):
    """No release-manifest.json at all -> fail closed (never default-allow)."""
    skill = _clone_skill(tmp, "nomani")  # do NOT build manifest
    (skill / "config" / "release-manifest.json").unlink(missing_ok=True)
    task = tmp / "nomani_task"; task.mkdir()
    record("integrity_missing_manifest_must_fail (MUST-FAIL guard)", _is_blocked(_runner(skill, task)))


def fx_integrity_gate_side_door_must_fail(tmp: Path):
    """The run_stage_gates side door must also fail closed under drift."""
    skill = _clone_skill(tmp, "sidedoor"); _build_manifest(skill)
    scr = skill / TRACKED_SCRIPT_REL
    scr.write_text(scr.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    rep = tmp / "dim.json"
    write(rep, {"dimensions": [{"dimension": "title_style", "counts": {"min_titles": 80}}]})
    proc = run([str(skill / "scripts" / "run_stage_gates.py"), "--gate", "dimension-evidence", "--input", str(rep)])
    record("integrity_run_stage_gates_side_door_blocked (MUST-FAIL guard)", proc.returncode == 3)


def _adapter_task(tmp: Path, name: str, sha_ok: bool = True, registered: bool = True):
    """Build a task with step06 produced artifact relocated to a non-default path,
    a Step0 manifest registering it, and a task-adapter-manifest pointing to it."""
    task = tmp / name; task.mkdir()
    # custom location for the handoff artifact (the real-world reason for override)
    rel = "025-rag-import/zotero-pdf-rag-handoff-input.json"
    art = task / rel
    write(art, {"status": "success", "item_count": 10,
                "item_receipts": [{"title": f"t{i}"} for i in range(10)],
                "pdf_count": 8, "rag_doc_count": 8,
                "recall_test": {"sampled": 3, "passed": 3}})
    digest = sha256_file(art)
    # Step0 manifest registering the asset under its real sha
    write(task / "00-intake" / "material-intake-manifest.json", {
        "schema": "journal_style_material_intake_manifest_v1",
        "registered_assets": {
            "zotero_pdf_rag_handoff_custom": {"rel_path": rel, "sha256": digest if registered else "deadbeef"},
        },
    })
    write(task / "00-intake" / "task-adapter-manifest.json", {
        "schema": "journal_style_task_adapter_v1",
        "task_id": name,
        "overrides": [{
            "step": "step06_zotero_pdf_rag",
            "field": "gate_input",
            "task_local_path": rel,
            "input_sha256": digest if sha_ok else "deadbeef",
            "registered_in_step0": True,
            "reason": "existing task stores handoff at a non-default path",
        }],
    })
    return task


def fx_adapter_allowed_path_ok(tmp: Path):
    """Legal override: remap step06 gate_input to a registered, sha-bound path."""
    from task_adapter import load_task_adapter, validate_task_adapter
    task = _adapter_task(tmp, "adapter_ok")
    try:
        overrides = validate_task_adapter(load_task_adapter(task), task)
        ok = "step06_zotero_pdf_rag" in overrides
    except Exception as exc:  # noqa
        ok = False; overrides = str(exc)
    record("adapter_allowed_path_ok", ok, str(overrides)[:80])


def fx_adapter_illegal_field_must_fail(tmp: Path):
    """Override that tries to change a contract field (next) must be rejected."""
    from task_adapter import TaskAdapterError, load_task_adapter, validate_task_adapter
    task = _adapter_task(tmp, "adapter_illegal")
    mani = task / "00-intake" / "task-adapter-manifest.json"
    data = json.loads(mani.read_text(encoding="utf-8"))
    data["overrides"][0]["next"] = "step09_fit"  # contract field
    mani.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    try:
        validate_task_adapter(load_task_adapter(task), task)
        rejected = False
    except TaskAdapterError:
        rejected = True
    record("adapter_illegal_field_must_fail (MUST-FAIL guard)", rejected)


def fx_adapter_unregistered_must_fail(tmp: Path):
    """Override sha not matching the Step0-registered sha must be rejected."""
    from task_adapter import TaskAdapterError, load_task_adapter, validate_task_adapter
    task = _adapter_task(tmp, "adapter_unreg", registered=False)
    try:
        validate_task_adapter(load_task_adapter(task), task)
        rejected = False
    except TaskAdapterError:
        rejected = True
    record("adapter_unregistered_must_fail (MUST-FAIL guard)", rejected)


def fx_adapter_sha_mismatch_must_fail(tmp: Path):
    """Override input_sha256 not matching the live artifact must be rejected."""
    from task_adapter import TaskAdapterError, load_task_adapter, validate_task_adapter
    task = _adapter_task(tmp, "adapter_sha", sha_ok=False)
    try:
        validate_task_adapter(load_task_adapter(task), task)
        rejected = False
    except TaskAdapterError:
        rejected = True
    record("adapter_sha_mismatch_must_fail (MUST-FAIL guard)", rejected)


def fx_adapter_non_whitelisted_step_must_fail(tmp: Path):
    """Override for a non-whitelisted step (step10_handoff) must be rejected."""
    from task_adapter import TaskAdapterError, load_task_adapter, validate_task_adapter
    task = _adapter_task(tmp, "adapter_wl")
    mani = task / "00-intake" / "task-adapter-manifest.json"
    data = json.loads(mani.read_text(encoding="utf-8"))
    data["overrides"][0]["step"] = "step10_handoff"
    mani.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    try:
        validate_task_adapter(load_task_adapter(task), task)
        rejected = False
    except TaskAdapterError:
        rejected = True
    record("adapter_non_whitelisted_step_must_fail (MUST-FAIL guard)", rejected)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for fx in [fx_forged_gate_over_bad_artifact, fx_marker_copy_forgery, fx_tampered_artifact,
                   fx_runner_stops, fx_metadata_mode_reaches_metadata_terminal, fx_full_mode_requires_mu_pack,
                   fx_full_mode_reaches_handoff_terminal, fx_uncalibrated_model_blocks_before_fit,
                   fx_material_intake_unblocks, fx_p4_untraceable,
                   fx_p4_missing_ledger_no_go, fx_p5_credential, fx_p5_public_ok,
                   fx_p6_gateless_never_skip, fx_p6_gatefail_rejected, fx_p6_gatepass_accepted,
                   fx_handoff_ratio, fx_dimension_below_threshold,
                   fx_integrity_clean_runs, fx_integrity_dirty_config_must_fail,
                   fx_integrity_dirty_script_must_fail, fx_integrity_missing_manifest_must_fail,
                   fx_integrity_gate_side_door_must_fail,
                   fx_adapter_allowed_path_ok, fx_adapter_illegal_field_must_fail,
                   fx_adapter_unregistered_must_fail, fx_adapter_sha_mismatch_must_fail,
                   fx_adapter_non_whitelisted_step_must_fail]:
            try:
                fx(tmp)
            except Exception as exc:  # a fixture crash is a failure
                record(fx.__name__, False, f"crash: {exc}")
    passed = sum(1 for r in RESULTS if r["passed"])
    total = len(RESULTS)
    print(json.dumps({"ok": passed == total, "passed": passed, "total": total, "results": RESULTS},
                     ensure_ascii=False, indent=2))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
