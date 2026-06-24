#!/usr/bin/env python3
"""Offline fixtures for downstream-consumable journal-style contracts.

These tests use synthetic data only. They verify the Phase 1 contracts and
gates for MinerU/mu fulltext packs, per-article profiles, aggregation locks,
downstream provenance, and calibrated scoring.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / "scripts"
PY = sys.executable

RESULTS: list[dict] = []


def run(args: list[str]):
    return subprocess.run([PY, *args], capture_output=True, text=True)


def record(name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append({"fixture": name, "passed": bool(passed), "detail": detail})


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_article(index: int) -> dict:
    fulltext = (
        f"题名：碑帖传播研究{index}\n"
        "摘要：本文围绕碑帖材料、传播路径与书学接受展开分析。\n"
        "一、问题提出\n"
        "本文基于档案、碑帖和图像材料提出问题。\n"
        "二、材料与方法\n"
        "文章采用考辨、比较和个案研究方法。\n"
        "三、结论\n"
        "文章回到问题意识并收束判断。\n"
        "注释：[1] 文献出处说明。\n"
        "参考文献：[1] 示例文献。\n"
    )
    return {
        "article_id": f"A{index:02d}",
        "title": f"碑帖传播研究{index}",
        "authors": [f"作者{index}"],
        "year": 2020 + index % 4,
        "column": "专题研究",
        "mu_fulltext": fulltext,
        "fulltext_sha256": text_sha(fulltext),
        "core_library_joined": True,
        "abstract": "本文围绕碑帖材料、传播路径与书学接受展开分析。",
        "keywords": ["碑帖", "传播", "书学史"],
        "section_tree": [
            {"level": 1, "title": "问题提出", "order": 1, "has_subsections": False, "subsection_count": 0},
            {"level": 1, "title": "材料与方法", "order": 2, "has_subsections": False, "subsection_count": 0},
            {"level": 1, "title": "结论", "order": 3, "has_subsections": False, "subsection_count": 0}
        ],
        "paragraph_sequence": [
            {"section_ref": "1", "order": 1, "char_count": 80},
            {"section_ref": "2", "order": 2, "char_count": 90},
            {"section_ref": "3", "order": 3, "char_count": 70}
        ],
        "notes": {"type": "footnote", "count": 1, "content_types": ["出处说明"]},
        "reference_list": [
            {"raw": "[1] 示例文献。", "year": 2020, "lang": "zh", "is_self_journal": False}
        ],
        "figures_tables": {"figure_count": 0, "table_count": 0, "plate_clues": []},
        "page_range": "1-10",
        "char_count_total": len(fulltext),
        "provenance": {
            "source_ledger": "06-gates/zotero-pdf-rag-handoff.json",
            "extraction_method": "MinerU",
            "mu_version": "mineru-fixture-1"
        }
    }


def make_pack(count: int) -> dict:
    return {
        "schema": "journal_style_mu_fulltext_core_pack_v1",
        "target_journal": "测试刊",
        "source_skill": "检索入库",
        "mu_processing_required": True,
        "mu_processor": "MinerU",
        "ordinary_rag_is_not_substitute": True,
        "articles": [make_article(i) for i in range(1, count + 1)]
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
        "material_types": ["碑帖", "档案", "图像"],
        "method_types": ["考辨", "比较"],
        "argument_rhythm": {"type": "问题-材料-结论"},
        "notes_profile": article["notes"],
        "reference_profile": {"reference_count": len(article["reference_list"])},
        "conclusion_pattern": {"type": "回应问题"}
    }
    return {
        "schema": "per_article_style_profile_v1",
        "article_id": article["article_id"],
        "source_article_id": article["article_id"],
        "dimensions": dims,
        "evidence_index": [
            {
                "article_id": article["article_id"],
                "evidence_path": f"articles/{article['article_id']}/section_tree",
                "provenance": article["provenance"]
            }
        ],
        "downstream_constraints": [
            {"type": "section_count", "min": 3, "max": 5}
        ]
    }


def make_profile_batch(pack: dict, count: int | None = None) -> dict:
    articles = pack["articles"] if count is None else pack["articles"][:count]
    return {
        "schema": "journal_style_per_article_profile_batch_v1",
        "target_journal": pack["target_journal"],
        "source_pack": "03-analysis/fulltext-layer/mu-fulltext-core-pack.json",
        "ready_article_count": len(pack["articles"]),
        "profiles": [make_profile(article) for article in articles]
    }


def make_aggregation(sample_count: int, conclusion: str = "stable", confidence: str = "medium") -> dict:
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
                "confidence": confidence,
                "conclusion_strength": conclusion,
                "degrade_label": "" if conclusion == "stable" else "样本不足",
                "evidence_index": evidence
            }
            for name, dimension in names
        ]
    }


def make_consumption_pack(sample_count: int) -> dict:
    return {
        "schema": "journal_style_profile_v1",
        "target_journal": "测试刊",
        "source_evidence_scope": "mu_fulltext_core_pack",
        "metadata_only": False,
        "sample_count": sample_count,
        "confidence": "medium",
        "conclusion_strength": "stable",
        "degrade_label": "",
        "constraints": {
            "length_band": {"min": 10000, "max": 16000, "advisory_only": True, "source": "reference_only"},
            "paragraph_band": {"min": 30, "max": 60},
            "section_hierarchy": {"section_min": 3, "section_max": 5},
            "abstract_keywords": {"keyword_min": 3, "keyword_max": 5},
            "notes_convention": {"type": "footnote"},
            "reference_constraints": {"reference_min": 20, "reference_max": 45},
            "title_style": {"patterns": ["对象+问题"]},
            "argument_rhythm": {"preferred": "问题-材料-结论"}
        },
        "gap_checklist": [],
        "evidence_index": [
            {"article_id": "A01", "evidence_path": "per-article/A01.json", "provenance": {"source": "fixture"}}
        ]
    }


def make_scoring(rounds: int = 1, replay_count: int = 10) -> dict:
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
            "status": "calibrated",
            "rounds_completed": rounds,
            "replay_sample_count": replay_count,
            "source": "per_article_profile_replay"
        },
        "dimensions": [
            {"dimension": "format_convention", "weight": 15, "rationale": "由体例约束锁校准"},
            {"dimension": "reference_ecology", "weight": 15, "rationale": "由参考文献生态锁校准"}
        ],
        "scoring_constraints": {
            "source": "journal_style_aggregation_bundle",
            "section_hierarchy": {"section_min": 3, "section_max": 5, "median": 3},
            "abstract_keywords": {"keyword_min": 3, "keyword_max": 5, "median": 3},
            "reference_constraints": {"reference_min": 1, "reference_max": 1, "median": 1}
        },
        "replay_scores": replay_scores,
        "published_score_distribution": distribution
    }


def gate(tmp: Path, name: str, payload: dict, filename: str | None = None):
    path = tmp / (filename or f"{name}.json")
    write_json(path, payload)
    proc = run([str(SCRIPTS / "run_stage_gates.py"), "--gate", name, "--input", str(path)])
    try:
        return json.loads(proc.stdout), proc
    except json.JSONDecodeError:
        return {}, proc


def fx_mu_pack_pass(tmp: Path):
    verdict, proc = gate(tmp, "mu-fulltext-pack", make_pack(10))
    record("mu_pack_10_preliminary_degraded", verdict.get("verdict") == "DEGRADED", proc.stdout[:120])


def fx_mu_pack_low_no_go(tmp: Path):
    verdict, proc = gate(tmp, "mu-fulltext-pack", make_pack(9))
    record("mu_pack_below_10_no_go", verdict.get("verdict") == "NO_GO", proc.stdout[:120])


def fx_mu_pack_sha_no_go(tmp: Path):
    pack = make_pack(10)
    pack["articles"][0]["fulltext_sha256"] = "0" * 64
    verdict, proc = gate(tmp, "mu-fulltext-pack", pack)
    record("mu_pack_sha_mismatch_no_go", verdict.get("verdict") == "NO_GO", proc.stdout[:120])


def fx_per_article_complete_pass(tmp: Path):
    task = tmp / "per-article-complete"
    pack = make_pack(10)
    write_json(task / "03-analysis" / "fulltext-layer" / "mu-fulltext-core-pack.json", pack)
    verdict, proc = gate(
        task / "03-analysis" / "fulltext-layer",
        "per-article-profile-complete",
        make_profile_batch(pack),
        filename="per-article-style-profiles.json",
    )
    record("per_article_profiles_complete_pass", verdict.get("verdict") == "PASS", proc.stdout[:120])


def fx_per_article_missing_no_go(tmp: Path):
    task = tmp / "per-article-missing"
    pack = make_pack(10)
    write_json(task / "03-analysis" / "fulltext-layer" / "mu-fulltext-core-pack.json", pack)
    verdict, proc = gate(
        task / "03-analysis" / "fulltext-layer",
        "per-article-profile-complete",
        make_profile_batch(pack, count=9),
        filename="per-article-style-profiles.json",
    )
    record("per_article_missing_profile_no_go", verdict.get("verdict") == "NO_GO", proc.stdout[:120])


def fx_per_article_mu_ready_count_authoritative_no_go(tmp: Path):
    task = tmp / "mu-ready-authoritative"
    pack_path = task / "03-analysis" / "fulltext-layer" / "mu-fulltext-core-pack.json"
    pack = make_pack(30)
    write_json(pack_path, pack)
    batch = make_profile_batch(pack, count=12)
    batch["ready_article_count"] = 12
    verdict, proc = gate(
        task / "03-analysis" / "fulltext-layer",
        "per-article-profile-complete",
        batch,
        filename="per-article-style-profiles.json",
    )
    problems = " ".join(verdict.get("problems") or [])
    record(
        "per_article_mu_ready_count_authoritative_no_go",
        verdict.get("verdict") == "NO_GO" and "mu pack ready count 30" in problems,
        proc.stdout[:160],
    )


def fx_per_article_direct_text_no_go(tmp: Path):
    task = tmp / "per-article-direct-text"
    pack = make_pack(10)
    write_json(task / "03-analysis" / "fulltext-layer" / "mu-fulltext-core-pack.json", pack)
    batch = make_profile_batch(pack)
    batch["profiles"][0]["downstream_constraints"].append({"正文": "这是一段不应进入下游约束的可复用正文。"})
    verdict, proc = gate(
        task / "03-analysis" / "fulltext-layer",
        "per-article-profile-complete",
        batch,
        filename="per-article-style-profiles.json",
    )
    record("per_article_direct_text_no_go", verdict.get("verdict") == "NO_GO", proc.stdout[:120])


def fx_analyze_per_article_style_generates_profiles(tmp: Path):
    task = tmp / "generate-profiles"
    pack = make_pack(10)
    write_json(task / "03-analysis" / "fulltext-layer" / "mu-fulltext-core-pack.json", pack)
    proc = run([str(SCRIPTS / "analyze_per_article_style.py"), "--task-dir", str(task)])
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        out = {}
    output = task / "03-analysis" / "fulltext-layer" / "per-article-style-profiles.json"
    record(
        "analyze_per_article_style_generates_profiles",
        proc.returncode == 0 and out.get("profile_gate_verdict") == "PASS" and output.exists(),
        proc.stdout[:160] + proc.stderr[:160],
    )


def fx_analyze_per_article_style_pending_on_bad_pack(tmp: Path):
    task = tmp / "generate-pending"
    pack = make_pack(9)
    write_json(task / "03-analysis" / "fulltext-layer" / "mu-fulltext-core-pack.json", pack)
    proc = run([str(SCRIPTS / "analyze_per_article_style.py"), "--task-dir", str(task)])
    pending = task / "03-analysis" / "fulltext-layer" / "pending-materials.json"
    output = task / "03-analysis" / "fulltext-layer" / "per-article-style-profiles.json"
    record(
        "analyze_per_article_style_pending_on_bad_pack",
        proc.returncode == 1 and pending.exists() and not output.exists(),
        proc.stdout[:160] + proc.stderr[:160],
    )


def fx_aggregation_stable_pass(tmp: Path):
    verdict, proc = gate(tmp, "aggregation-threshold", make_aggregation(20))
    record("aggregation_20_stable_pass", verdict.get("verdict") == "PASS", proc.stdout[:120])


def fx_aggregation_missing_named_artifact_no_go(tmp: Path):
    bundle = make_aggregation(20)
    bundle["artifacts"] = bundle["artifacts"][:-1]
    verdict, proc = gate(tmp, "aggregation-threshold", bundle)
    record("aggregation_missing_named_artifact_no_go", verdict.get("verdict") == "NO_GO", proc.stdout[:160])


def fx_aggregation_under_10_stable_no_go(tmp: Path):
    verdict, proc = gate(tmp, "aggregation-threshold", make_aggregation(9))
    record("aggregation_under_10_stable_no_go", verdict.get("verdict") == "NO_GO", proc.stdout[:120])


def fx_aggregate_journal_style_generates_named_bundle(tmp: Path):
    task = tmp / "aggregate-bundle"
    pack = make_pack(20)
    write_json(task / "03-analysis" / "fulltext-layer" / "mu-fulltext-core-pack.json", pack)
    profile_proc = run([str(SCRIPTS / "analyze_per_article_style.py"), "--task-dir", str(task)])
    proc = run([str(SCRIPTS / "aggregate_journal_style.py"), "--task-dir", str(task)])
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        out = {}
    bundle_path = task / "03-analysis" / "fulltext-layer" / "journal-style-aggregation-bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8")) if bundle_path.exists() else {}
    names = {artifact.get("name") for artifact in bundle.get("artifacts") or []}
    required = {
        "journal-style-constraints-lock",
        "journal-format-convention-profile",
        "journal-argument-preference-profile",
        "journal-reference-ecology-lock",
        "journal-polish-consumption-pack",
    }
    record(
        "aggregate_journal_style_generates_named_bundle",
        profile_proc.returncode == 0 and proc.returncode == 0 and out.get("aggregation_gate_verdict") == "PASS" and required.issubset(names),
        proc.stdout[:160] + proc.stderr[:160],
    )


def fx_export_polish_consumption_pack(tmp: Path):
    task = tmp / "export-consumption"
    pack = make_pack(20)
    write_json(task / "03-analysis" / "fulltext-layer" / "mu-fulltext-core-pack.json", pack)
    profile_proc = run([str(SCRIPTS / "analyze_per_article_style.py"), "--task-dir", str(task)])
    aggregate_proc = run([str(SCRIPTS / "aggregate_journal_style.py"), "--task-dir", str(task)])
    proc = run([str(SCRIPTS / "export_polish_consumption_pack.py"), "--task-dir", str(task)])
    output = task / "05-handoff" / "journal-polish-consumption-pack.json"
    data = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    length = ((data.get("constraints") or {}).get("length_band") or {})
    record(
        "export_polish_consumption_pack",
        profile_proc.returncode == 0
        and aggregate_proc.returncode == 0
        and proc.returncode == 0
        and data.get("confidence")
        and data.get("conclusion_strength")
        and length.get("advisory_only") is True,
        proc.stdout[:160] + proc.stderr[:160],
    )


def fx_provenance_pass(tmp: Path):
    verdict, proc = gate(tmp, "provenance-required", make_consumption_pack(20))
    record("provenance_required_pack_pass", verdict.get("verdict") == "PASS", proc.stdout[:120])


def fx_provenance_missing_no_go(tmp: Path):
    pack = make_consumption_pack(20)
    pack["evidence_index"] = []
    verdict, proc = gate(tmp, "provenance-required", pack)
    record("provenance_missing_no_go", verdict.get("verdict") == "NO_GO", proc.stdout[:120])


def fx_provenance_metadata_conflict_no_go(tmp: Path):
    pack = make_consumption_pack(20)
    pack["metadata_only"] = True
    verdict, proc = gate(tmp, "provenance-required", pack)
    record("provenance_metadata_conflict_no_go", verdict.get("verdict") == "NO_GO", proc.stdout[:120])


def fx_scoring_calibrated_pass(tmp: Path):
    verdict, proc = gate(tmp, "scoring-replay-calibrated", make_scoring())
    record("scoring_replay_calibrated_pass", verdict.get("verdict") == "PASS", proc.stdout[:120])


def fx_scoring_uncalibrated_no_go(tmp: Path):
    model = make_scoring(rounds=0, replay_count=5)
    model["calibration"]["status"] = "not_started"
    verdict, proc = gate(tmp, "scoring-replay-calibrated", model)
    record("scoring_uncalibrated_no_go", verdict.get("verdict") == "NO_GO", proc.stdout[:120])


def fx_scoring_missing_rationale_no_go(tmp: Path):
    model = make_scoring()
    model["dimensions"][0].pop("rationale", None)
    verdict, proc = gate(tmp, "scoring-replay-calibrated", model)
    record("scoring_missing_rationale_no_go", verdict.get("verdict") == "NO_GO", proc.stdout[:160])


def fx_scoring_constant_distribution_no_go(tmp: Path):
    model = make_scoring()
    model["published_score_distribution"].update({"min": 70, "q1": 78, "median": 84, "q3": 90, "max": 96})
    verdict, proc = gate(tmp, "scoring-replay-calibrated", model)
    problems = " ".join(verdict.get("problems") or [])
    record(
        "scoring_constant_distribution_no_go",
        verdict.get("verdict") == "NO_GO" and "does not match replay_scores" in problems,
        proc.stdout[:160],
    )


def fx_calibrate_and_score_user_manuscript(tmp: Path):
    task = tmp / "calibrate-score"
    pack = make_pack(20)
    write_json(task / "03-analysis" / "fulltext-layer" / "mu-fulltext-core-pack.json", pack)
    profile_proc = run([str(SCRIPTS / "analyze_per_article_style.py"), "--task-dir", str(task)])
    aggregate_proc = run([str(SCRIPTS / "aggregate_journal_style.py"), "--task-dir", str(task)])
    calibrate_proc = run([str(SCRIPTS / "calibrate_fit_scoring.py"), "--task-dir", str(task)])
    write_json(task / "00-intake" / "manuscript-features.json", {
        "section_count": 7,
        "keyword_count": 4,
        "reference_count": 20,
        "has_notes": True,
        "has_abstract": True,
    })
    score_proc = run([
        str(SCRIPTS / "score_user_manuscript.py"),
        "--task-dir", str(task),
        "--manuscript-features", "00-intake/manuscript-features.json",
    ])
    report = task / "04-fit-evaluation" / "submission-fit-score.md"
    text = report.read_text(encoding="utf-8") if report.exists() else ""
    model_path = task / "04-fit-evaluation" / "journal-fit-scoring-model.json"
    model = json.loads(model_path.read_text(encoding="utf-8")) if model_path.exists() else {}
    distribution = model.get("published_score_distribution") or {}
    replay_scores = model.get("replay_scores") or []
    replay_values = sorted(float(item.get("score")) for item in replay_scores)
    record(
        "calibrate_and_score_user_manuscript",
        profile_proc.returncode == 0
        and aggregate_proc.returncode == 0
        and calibrate_proc.returncode == 0
        and score_proc.returncode == 0
        and distribution.get("source") == "replay_scores"
        and distribution.get("min") == replay_values[0]
        and distribution.get("max") == replay_values[-1]
        and (model.get("calibration") or {}).get("source") == "per_article_profile_replay"
        and (model.get("scoring_constraints") or {}).get("source") == "journal_style_aggregation_bundle"
        and "不是主编模拟" in text
        and "不预测录用概率" in text
        and "用户稿适配分" in text,
        score_proc.stdout[:160] + score_proc.stderr[:160],
    )


def fx_score_user_uses_journal_band(tmp: Path):
    task = tmp / "journal-band-score"
    model = make_scoring(replay_count=10)
    model["scoring_constraints"]["section_hierarchy"] = {"section_min": 4, "section_max": 4, "median": 4}
    model["scoring_constraints"]["abstract_keywords"] = {"keyword_min": 3, "keyword_max": 5, "median": 4}
    model["scoring_constraints"]["reference_constraints"] = {"reference_min": 22, "reference_max": 22, "median": 22}
    write_json(task / "04-fit-evaluation" / "journal-fit-scoring-model.json", model)
    write_json(task / "00-intake" / "manuscript-features.json", {
        "section_count": 3,
        "keyword_count": 4,
        "reference_count": 20,
        "has_notes": True,
        "has_abstract": True,
    })
    proc = run([
        str(SCRIPTS / "score_user_manuscript.py"),
        "--task-dir", str(task),
        "--manuscript-features", "00-intake/manuscript-features.json",
    ])
    report = task / "04-fit-evaluation" / "submission-fit-score.md"
    text = report.read_text(encoding="utf-8") if report.exists() else ""
    record(
        "score_user_uses_journal_band",
        proc.returncode == 0
        and "目标期刊章节区间：4-4" in text
        and "目标期刊参考文献区间：22-22" in text
        and "章节数量偏离目标期刊区间 4-4" in text
        and "参考文献数量偏离目标期刊区间 22-22" in text
        and "约束来源：journal_style_aggregation_bundle" in text,
        proc.stdout[:160] + proc.stderr[:160],
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for fx in [
            fx_mu_pack_pass,
            fx_mu_pack_low_no_go,
            fx_mu_pack_sha_no_go,
            fx_per_article_complete_pass,
            fx_per_article_missing_no_go,
            fx_per_article_mu_ready_count_authoritative_no_go,
            fx_per_article_direct_text_no_go,
            fx_analyze_per_article_style_generates_profiles,
            fx_analyze_per_article_style_pending_on_bad_pack,
            fx_aggregation_stable_pass,
            fx_aggregation_missing_named_artifact_no_go,
            fx_aggregation_under_10_stable_no_go,
            fx_aggregate_journal_style_generates_named_bundle,
            fx_export_polish_consumption_pack,
            fx_provenance_pass,
            fx_provenance_missing_no_go,
            fx_provenance_metadata_conflict_no_go,
            fx_scoring_calibrated_pass,
            fx_scoring_uncalibrated_no_go,
            fx_scoring_missing_rationale_no_go,
            fx_scoring_constant_distribution_no_go,
            fx_calibrate_and_score_user_manuscript,
            fx_score_user_uses_journal_band,
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
