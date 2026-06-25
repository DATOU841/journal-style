#!/usr/bin/env python3
"""Run journal-style stage gates on synthetic or task-local metadata files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path


PASS = "PASS"
DEGRADED = "DEGRADED"
NO_GO = "NO_GO"

COMPLETION_LABELS = {
    "METADATA_ONLY_NOT_FULLTEXT_READY",
    "FULLTEXT_PARTIAL",
    "FULLTEXT_READY",
}
READY_STATUS = {"done", "complete"}

# Fallbacks used only if config/field-policy.json cannot be loaded. The real
# source of truth is config/field-policy.json (RC2: no second hardcoded copy).
_FALLBACK_FORBIDDEN_KEYS = {
    "fulltext", "全文", "pdf_path", "absolute_pdf_path", "rag_chunk",
    "chunk_text", "vector", "cookie", "token", "api_key", "secret",
}
_FALLBACK_SECRET_PATTERNS = [
    r"--api-key(?:=|\s+)[A-Za-z0-9_\-]{12,}",
    r"ZOTERO_API_KEY=[A-Za-z0-9_\-]{12,}",
    r"\b(token|cookie|secret|password|bearer)\b\s*[:=]\s*[A-Za-z0-9_\-]{12,}",
]


# --- Single source of truth (P2/RC2): thresholds come from config/stage-gates.json ---
def _load_cfg():
    try:
        from journal_style_runtime import load_stage_gates, load_field_policy
        return load_stage_gates(), load_field_policy()
    except Exception:
        return {}, {}

_STAGE_GATES, _FIELD_POLICY = _load_cfg()
_GATES = _STAGE_GATES.get("gates", {})
_DIM = _STAGE_GATES.get("dimension_thresholds", {})

# Credential policy: load from field-policy.json, fall back to local constants.
_DENY = _FIELD_POLICY.get("credential_denylist", {}) if isinstance(_FIELD_POLICY, dict) else {}
FORBIDDEN_METADATA_KEYS = {
    str(k).lower() for k in _DENY.get("forbidden_keys_exact", _FALLBACK_FORBIDDEN_KEYS)
}
SECRET_PATTERNS = [
    re.compile(p, re.I) for p in _DENY.get("value_patterns", _FALLBACK_SECRET_PATTERNS)
]


def _cfg(path, default):
    """Dotted lookup into the stage-gates config with a fallback default."""
    cur = _STAGE_GATES
    for key in path.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


SIDECAR_ALLOWED_POINTER_KEYS = {
    str(key).lower()
    for key in _cfg("gates.jiansuo-sidecar-safety.allowed_pointer_fields", ["full_md_path"])
}
SIDECAR_FORBIDDEN_CONTENT_KEYS = {
    str(key).lower()
    for key in _cfg("gates.jiansuo-sidecar-safety.forbidden_content_keys", [])
}
SIDECAR_FORBIDDEN_KEYS = (FORBIDDEN_METADATA_KEYS | SIDECAR_FORBIDDEN_CONTENT_KEYS) - SIDECAR_ALLOWED_POINTER_KEYS

# FULLTEXT_READY thresholds
FT_SAMPLE_MIN = _cfg("gates.no-metadata-only-completion.fulltext_ready_requires.fulltext_sample_count_min", 20)
FT_RAG_MIN = _cfg("gates.no-metadata-only-completion.fulltext_ready_requires.rag_available_rate_min", 0.5)
FT_PDF_MIN = _cfg("gates.no-metadata-only-completion.fulltext_ready_requires.pdf_coverage_rate_min", 0.2)
# core library ratio
CORE_RATIO_MIN = _cfg("gates.core-library-selection.ratio_min", 0.25)
CORE_RATIO_MAX = _cfg("gates.core-library-selection.ratio_max", 0.40)
# handoff thresholds
HANDOFF_RECEIPT_MIN = _cfg("gates.zotero-pdf-rag-handoff.success_thresholds.receipt_coverage_of_item_count_min", 0.8)
HANDOFF_PDF_MIN = _cfg("gates.zotero-pdf-rag-handoff.success_thresholds.pdf_count_over_item_count_min", 0.5)
HANDOFF_RAG_MIN = _cfg("gates.zotero-pdf-rag-handoff.success_thresholds.rag_doc_over_pdf_count_min", 0.8)
# fulltext-claims thresholds
CLAIM_SAMPLE_OBS_MIN = _cfg("gates.no-fulltext-claim-without-rag.sample_observation_min", 10)
CLAIM_STABLE_MIN = _cfg("gates.no-fulltext-claim-without-rag.stable_style_claim_min", 20)
CLAIM_RAG_MIN = _cfg("gates.no-fulltext-claim-without-rag.rag_available_rate_min", 0.5)
# abstract coverage warn
ABSTRACT_WARN_BELOW = _cfg("gates.abstract-metadata-ledger.abstract_coverage_warn_below", 0.5)
MU_READY_MIN = _cfg("gates.mu-fulltext-pack.ready_article_min", 10)
MU_STABLE_MIN = _cfg("gates.mu-fulltext-pack.stable_article_min", 20)
ARG_REF_HIGH_MIN = _cfg("gates.mu-fulltext-pack.argument_reference_stable_min", 30)
PROFILE_REQUIRED_DIMS = _cfg("gates.per-article-profile-complete.required_dimensions", [])
AGG_PRELIM_MIN = _cfg("gates.aggregation-threshold.preliminary_min", 10)
AGG_STABLE_MIN = _cfg("gates.aggregation-threshold.stable_min", 20)
AGG_ARG_REF_HIGH_MIN = _cfg("gates.aggregation-threshold.argument_reference_high_min", 30)
AGG_REQUIRED_ARTIFACTS = _cfg("gates.aggregation-threshold.required_named_artifacts", [])
SCORING_ROUNDS_MIN = _cfg("gates.scoring-replay-calibrated.minimum_rounds_completed", 1)
SCORING_REPLAY_MIN = _cfg("gates.scoring-replay-calibrated.minimum_replay_sample_count", 10)


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{path}:{line_no}: invalid JSONL") from exc
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def scoring_distribution(scores: list[float]) -> dict:
    vals = sorted(float(score) for score in scores)
    if not vals:
        return {}
    return {
        "sample_count": len(vals),
        "min": round(vals[0], 2),
        "q1": round(vals[len(vals) // 4], 2),
        "median": round(float(statistics.median(vals)), 2),
        "q3": round(vals[(len(vals) * 3) // 4], 2),
        "max": round(vals[-1], 2),
    }


def same_number(left, right) -> bool:
    try:
        return abs(float(left) - float(right)) <= 0.01
    except Exception:
        return False


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def result(gate: str, verdict: str, problems: list[str], warnings: list[str], details: dict) -> dict:
    return {
        "gate": gate,
        "verdict": verdict,
        "problems": problems,
        "warnings": warnings,
        "details": details,
        "no_claims": {
            "metadata_only_completed": False,
            "fulltext_ready_without_rag": False,
            "journal_style_completed_without_fulltext": False,
        },
    }


def gate_completion_label(path: Path) -> dict:
    data = load_json(path)
    problems: list[str] = []
    warnings: list[str] = []
    pipeline = data.get("pipeline_status", {})
    layers = data.get("analysis_layers", {})
    label = layers.get("completion_label") or data.get("completion_label")
    fulltext_status = layers.get("fulltext_layer_status") or pipeline.get("fulltext_analysis")
    metadata_status = layers.get("metadata_layer_status") or pipeline.get("metadata_analysis")
    overall = pipeline.get("overall_journal_style") or pipeline.get("analysis")
    evidence = layers.get("fulltext_evidence", {})
    fulltext_count = int(evidence.get("fulltext_sample_count") or evidence.get("core_library_count") or 0)
    rag_rate = as_float(evidence.get("rag_available_rate"))
    pdf_rate = as_float(evidence.get("pdf_coverage_rate"))

    if label and label not in COMPLETION_LABELS:
        problems.append(f"invalid completion_label: {label}")
    if overall in READY_STATUS and fulltext_status not in READY_STATUS:
        problems.append("overall_journal_style/analysis cannot be done while fulltext layer is not done")
    if metadata_status in READY_STATUS and fulltext_status not in READY_STATUS and overall in READY_STATUS:
        problems.append("metadata-only analysis was promoted to overall completion")
    if label == "FULLTEXT_READY":
        if fulltext_status not in READY_STATUS:
            problems.append("FULLTEXT_READY requires fulltext_layer_status=done")
        if fulltext_count < FT_SAMPLE_MIN:
            problems.append(f"FULLTEXT_READY requires at least {FT_SAMPLE_MIN} fulltext samples")
        if rag_rate < FT_RAG_MIN:
            problems.append(f"FULLTEXT_READY requires rag_available_rate >= {FT_RAG_MIN}")
        if pdf_rate < FT_PDF_MIN:
            problems.append(f"FULLTEXT_READY requires pdf_coverage_rate >= {FT_PDF_MIN}")
    if not label:
        warnings.append("completion_label missing; legacy status accepted but should be upgraded")

    verdict = NO_GO if problems else PASS
    return result(
        "no-metadata-only-completion",
        verdict,
        problems,
        warnings,
        {
            "completion_label": label,
            "metadata_layer_status": metadata_status,
            "fulltext_layer_status": fulltext_status,
            "overall_journal_style": overall,
            "fulltext_sample_count": fulltext_count,
            "rag_available_rate": rag_rate,
            "pdf_coverage_rate": pdf_rate,
        },
    )


def gate_secret_boundary(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    problems = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            problems.append(f"secret-like process argument or evidence value matched: {pattern.pattern}")
    return result(
        "secret-boundary",
        NO_GO if problems else PASS,
        problems,
        [],
        {"input": str(path), "secret_pattern_hits": len(problems)},
    )


def _scan_sidecar_safety(obj, where: str, problems: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_text = str(key)
            key_lc = key_text.lower()
            child = f"{where}.{key_text}"
            if key_lc in SIDECAR_FORBIDDEN_KEYS and not re.search(r"(?:^|\.)[^.]+_counts$", where):
                problems.append(f"{child}: forbidden sidecar key")
            _scan_sidecar_safety(value, child, problems)
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            _scan_sidecar_safety(item, f"{where}[{index}]", problems)
    elif isinstance(obj, str):
        for pattern in SECRET_PATTERNS:
            if pattern.search(obj):
                problems.append(f"{where}: secret-like value matched {pattern.pattern}")
                break


def gate_jiansuo_sidecar_safety(path: Path) -> dict:
    problems: list[str] = []
    warnings: list[str] = []
    details = {
        "input": str(path),
        "missing_sidecar_is_pass": bool(_cfg("gates.jiansuo-sidecar-safety.missing_sidecar_is_pass", True)),
        "allowed_pointer_fields": sorted(SIDECAR_ALLOWED_POINTER_KEYS),
    }
    if not path.exists():
        warnings.append("jiansuo sidecar manifest absent; optional enhancement skipped")
        return result("jiansuo-sidecar-safety", PASS, problems, warnings, details)
    data = load_json(path)
    _scan_sidecar_safety(data, "$", problems)
    safety = data.get("safety") if isinstance(data, dict) else {}
    if isinstance(safety, dict):
        for problem in safety.get("problems") or []:
            problems.append(f"manifest safety problem: {problem}")
        for key in ("contains_fulltext_body", "contains_rag_chunks", "contains_vectors", "contains_secrets"):
            if safety.get(key):
                problems.append(f"manifest safety flag true: {key}")
        details.update({
            "manifest_safety_problem_count": len(safety.get("problems") or []),
            "full_md_files_opened": int(safety.get("full_md_files_opened") or 0),
            "full_md_pointers_recorded": int(safety.get("full_md_pointers_recorded") or 0),
        })
    if isinstance(data, dict) and data.get("schema") != "journal_style_jiansuo_sidecar_manifest_v1":
        warnings.append(f"unexpected sidecar manifest schema: {data.get('schema')}")
    details["problem_count"] = len(problems)
    return result(
        "jiansuo-sidecar-safety",
        NO_GO if problems else PASS,
        problems,
        warnings,
        details,
    )


def gate_jiansuo_handoff(path: Path) -> dict:
    data = load_json(path)
    problems: list[str] = []
    warnings: list[str] = []
    status = data.get("status")
    receipts = data.get("item_receipts") or []
    item_count = int(data.get("item_count") or 0)
    pdf_count = int(data.get("pdf_count") or 0)
    rag_count = int(data.get("rag_doc_count") or 0)
    recall = data.get("recall_test") or {}

    if data.get("task_collection_binding") == "missing":
        problems.append("task_collection_binding is missing")
    if not receipts:
        problems.append("missing item-level receipts")
    receipt_titles = {row.get("title") for row in receipts if row.get("title")}
    if item_count and len(receipt_titles) < min(item_count, len(receipts)):
        warnings.append("item_count and unique receipt titles differ; check duplicates")
    if status == "success":
        if item_count <= 0 or len(receipts) < max(1, int(item_count * HANDOFF_RECEIPT_MIN)):
            problems.append("success handoff requires item receipts for at least 80% of item_count")
        if data.get("include_pdf", True) and item_count and pdf_count / item_count < HANDOFF_PDF_MIN:
            problems.append("success handoff requires pdf_count/item_count >= 0.5")
        if data.get("include_rag", True) and pdf_count and rag_count / pdf_count < HANDOFF_RAG_MIN:
            problems.append("success handoff requires rag_doc_count/pdf_count >= 0.8")
        if data.get("acceptance", {}).get("require_recall_test", True):
            if int(recall.get("sampled") or 0) <= 0 or int(recall.get("passed") or 0) <= 0:
                problems.append("success handoff requires recall_test sampled/passed > 0")
    elif status == "partial":
        warnings.append("partial handoff can only support degraded analysis")
    elif status == "failed":
        problems.append("handoff status failed")
    else:
        problems.append(f"invalid handoff status: {status}")

    verdict = NO_GO if problems else DEGRADED if status == "partial" or warnings else PASS
    return result(
        "zotero-pdf-rag-handoff",
        verdict,
        problems,
        warnings,
        {
            "status": status,
            "item_count": item_count,
            "receipt_count": len(receipts),
            "pdf_count": pdf_count,
            "rag_doc_count": rag_count,
            "recall_test": recall,
        },
    )


def gate_abstract_metadata_ledger(path: Path) -> dict:
    rows = load_jsonl(path)
    problems: list[str] = []
    warnings: list[str] = []
    abstract_count = 0
    keyword_count = 0
    for row in rows:
        forbidden = sorted(FORBIDDEN_METADATA_KEYS.intersection({str(key).lower() for key in row}))
        if forbidden:
            problems.append(f"line {row.get('_line_no')}: forbidden metadata keys: {', '.join(forbidden)}")
        if row.get("abstract"):
            abstract_count += 1
        if row.get("keywords"):
            keyword_count += 1
    total = len(rows)
    abstract_rate = abstract_count / total if total else 0
    keyword_rate = keyword_count / total if total else 0
    if total == 0:
        problems.append("abstract metadata ledger is empty")
    if abstract_rate < ABSTRACT_WARN_BELOW:
        warnings.append("abstract coverage below 50%; trend and method claims must be downgraded")
    verdict = NO_GO if problems else DEGRADED if warnings else PASS
    return result(
        "abstract-metadata-ledger",
        verdict,
        problems,
        warnings,
        {"record_count": total, "abstract_rate": round(abstract_rate, 4), "keyword_rate": round(keyword_rate, 4)},
    )


def gate_core_library(path: Path) -> dict:
    data = load_json(path)
    problems: list[str] = []
    warnings: list[str] = []
    total = int(data.get("screened_count") or data.get("kept_count") or 0)
    selected = data.get("selected") or data.get("items") or []
    rejected = data.get("rejected") or []
    selected_count = len([item for item in selected if item.get("selected", True)])
    ratio = selected_count / total if total else 0
    if total <= 0:
        problems.append("missing screened_count/kept_count")
    if ratio < CORE_RATIO_MIN or ratio > CORE_RATIO_MAX:
        problems.append(f"core library ratio out of 25%-40% range: {ratio:.4f}")
    for item in selected:
        scores = item.get("scores") or {}
        if not scores or "total" not in item and "total" not in scores:
            problems.append(f"selected item missing score detail: {item.get('title')}")
            break
    missing_reason = [item.get("title") for item in rejected if not item.get("reason")]
    if missing_reason:
        problems.append(f"rejected items missing reason: {len(missing_reason)}")
    if not rejected:
        warnings.append("rejected ledger missing or empty")
    return result(
        "core-library-selection",
        NO_GO if problems else DEGRADED if warnings else PASS,
        problems,
        warnings,
        {"screened_count": total, "selected_count": selected_count, "ratio": round(ratio, 4), "rejected_count": len(rejected)},
    )


def gate_fulltext_claims(path: Path) -> dict:
    data = load_json(path)
    problems: list[str] = []
    warnings: list[str] = []
    claims = data.get("claims") or []
    stats = data.get("sample") or data
    sample_count = int(stats.get("fulltext_sample_count") or stats.get("record_count") or 0)
    rag_rate = as_float((data.get("coverage") or {}).get("rag_available_rate", data.get("rag_available_rate", 0.0)))
    for claim in claims:
        if claim.get("evidence_layer") == "fulltext":
            provenance = claim.get("provenance") or claim.get("source_item_keys") or claim.get("rag_doc_ids")
            if not provenance:
                problems.append(f"fulltext claim lacks provenance: {claim.get('claim_id') or claim.get('text')}")
    if sample_count < CLAIM_SAMPLE_OBS_MIN:
        warnings.append("fulltext sample below 10; only sample observations are allowed")
    elif sample_count < CLAIM_STABLE_MIN:
        warnings.append("fulltext sample below 20; stable journal-wide style claims are not allowed")
    if rag_rate < CLAIM_RAG_MIN:
        warnings.append("rag_available_rate below threshold; argument/reference ecology claims must be downgraded")
    verdict = NO_GO if problems else DEGRADED if warnings else PASS
    return result(
        "no-fulltext-claim-without-rag",
        verdict,
        problems,
        warnings,
        {"claim_count": len(claims), "fulltext_sample_count": sample_count, "rag_available_rate": rag_rate},
    )


def gate_material_intake(path: Path) -> dict:
    """Step-0 manifest gate: the manifest must be well-formed, register at least
    one asset, and carry per-asset sha256 so later provenance back-references
    (P4) have something to bind to. This unblocks step00 in the runner."""
    data = load_json(path)
    problems: list[str] = []
    warnings: list[str] = []
    schema = data.get("schema")
    registered = data.get("registered_assets") or {}
    gaps = data.get("gaps") or []
    if schema != "journal_style_material_intake_manifest_v1":
        problems.append(f"unexpected manifest schema: {schema}")
    if not isinstance(registered, dict) or not registered:
        problems.append("manifest registers no assets")
    for name, asset in (registered.items() if isinstance(registered, dict) else []):
        if not asset.get("sha256"):
            problems.append(f"registered asset '{name}' missing sha256")
        if not asset.get("rel_path"):
            problems.append(f"registered asset '{name}' missing rel_path")
    if gaps:
        warnings.append(f"{len(gaps)} candidate assets absent at intake (recorded as gaps)")
    verdict = NO_GO if problems else DEGRADED if warnings else PASS
    return result(
        "material-intake",
        verdict,
        problems,
        warnings,
        {"registered_count": len(registered) if isinstance(registered, dict) else 0,
         "gap_count": len(gaps)},
    )


def gate_dimension_evidence(path: Path) -> dict:
    """Consume dimension_thresholds from stage-gates.json (RC: make them load-
    bearing, not decorative). Each analysis dimension declares its id and
    evidence counts; the gate downgrades or fails by the configured thresholds
    instead of relying on prose."""
    data = load_json(path)
    problems: list[str] = []
    warnings: list[str] = []
    dims = data.get("dimensions") or data.get("dimension_evidence") or []
    if not dims:
        problems.append("no dimension evidence declared")
    checked = 0
    degraded_dims: list[str] = []
    for entry in dims:
        dim_id = entry.get("dimension") or entry.get("id")
        thresholds = _DIM.get(dim_id) if dim_id else None
        if not dim_id:
            problems.append("dimension entry missing 'dimension' id")
            continue
        if not thresholds:
            warnings.append(f"dimension '{dim_id}' has no configured threshold; not validated")
            continue
        checked += 1
        counts = entry.get("counts") or {}
        numeric_thresholds = {
            k: v for k, v in thresholds.items()
            if not k.startswith("_") and not k.endswith("_label")
            and isinstance(v, (int, float)) and not isinstance(v, bool)
        }
        if numeric_thresholds and not counts:
            problems.append(f"dimension '{dim_id}' declares no evidence counts")
        below = []
        for key, bound in numeric_thresholds.items():
            observed = counts.get(key)
            if observed is None:
                # Only thresholds the report chose to declare are evaluated; an
                # undeclared metric is a coverage warning, not a hard NO_GO.
                warnings.append(f"dimension '{dim_id}' did not declare count '{key}'")
                continue
            is_max = key.endswith("_max")
            if is_max and as_float(observed) > float(bound):
                below.append(f"{key}={observed}>{bound}")
            elif not is_max and as_float(observed) < float(bound):
                below.append(f"{key}={observed}<{bound}")
        if below:
            degraded_dims.append(dim_id)
            warnings.append(f"dimension '{dim_id}' below threshold: {', '.join(below)}; claim must be downgraded")
    verdict = NO_GO if problems else DEGRADED if warnings else PASS
    return result(
        "dimension-evidence",
        verdict,
        problems,
        warnings,
        {"dimensions_checked": checked, "degraded_dimensions": degraded_dims},
    )


def gate_mu_fulltext_pack(path: Path) -> dict:
    """Validate a MinerU/mu complete-text core pack.

    MinerU/mu is the upstream PDF-to-text processing route. This gate only
    accepts the complete text pack handed off by upstream work; it does not
    retrieve PDFs, run MinerU, or query RAG.
    """
    data = load_json(path)
    problems: list[str] = []
    warnings: list[str] = []
    if data.get("schema") != "journal_style_mu_fulltext_core_pack_v1":
        problems.append(f"unexpected schema: {data.get('schema')}")
    if data.get("mu_processing_required") is not True:
        problems.append("mu_processing_required must be true")
    processor = str(data.get("mu_processor") or "")
    if processor and processor.lower() not in {"mineru", "mu"}:
        problems.append(f"unexpected mu_processor: {processor}")
    if data.get("ordinary_rag_is_not_substitute") is not True:
        warnings.append("ordinary_rag_is_not_substitute should be true")

    required = _cfg("gates.mu-fulltext-pack.required_article_fields", [])
    required_structure_fields = _cfg("gates.mu-fulltext-pack.required_structure_fields", [])
    recommended_structure_fields = _cfg(
        "gates.mu-fulltext-pack.recommended_structure_fields",
        _cfg("gates.mu-fulltext-pack.structure_fields", []),
    )
    articles = data.get("articles") or []
    ready = 0
    ready_article_ids: list[str] = []
    required_structure_coverage = {field: 0 for field in required_structure_fields}
    recommended_structure_coverage = {field: 0 for field in recommended_structure_fields}
    for index, article in enumerate(articles, 1):
        missing = [field for field in required if article.get(field) in (None, "", [], {})]
        if missing:
            problems.append(f"article {index}: missing required fields: {', '.join(missing)}")
            continue
        missing_structure = [
            field for field in required_structure_fields
            if article.get(field) in (None, "", [], {})
        ]
        if missing_structure:
            problems.append(
                f"article {article.get('article_id')}: missing required full-mode structure fields: "
                f"{', '.join(missing_structure)}"
            )
            continue
        if article.get("core_library_joined") is not True:
            problems.append(f"article {article.get('article_id')}: not joined back to core library")
            continue
        provenance = article.get("provenance") or {}
        for field in ("source_ledger", "extraction_method", "mu_version"):
            if not provenance.get(field):
                problems.append(f"article {article.get('article_id')}: provenance missing {field}")
        fulltext = str(article.get("mu_fulltext") or "")
        if article.get("fulltext_sha256") != sha256_text(fulltext):
            problems.append(f"article {article.get('article_id')}: fulltext_sha256 mismatch")
            continue
        ready += 1
        ready_article_ids.append(str(article.get("article_id")))
        for field in required_structure_fields:
            if article.get(field) not in (None, "", [], {}):
                required_structure_coverage[field] += 1
        for field in recommended_structure_fields:
            if article.get(field) not in (None, "", [], {}):
                recommended_structure_coverage[field] += 1

    if ready < MU_READY_MIN:
        problems.append(f"MinerU/mu fulltext ready articles {ready} below minimum {MU_READY_MIN}")
    elif ready < MU_STABLE_MIN:
        warnings.append(f"MinerU/mu fulltext ready articles {ready} only support preliminary preferences")
    for field, count in recommended_structure_coverage.items():
        rate = count / ready if ready else 0
        if ready and rate < 0.8:
            warnings.append(f"recommended structure field '{field}' coverage {rate:.2f} below 0.80")

    return result(
        "mu-fulltext-pack",
        NO_GO if problems else DEGRADED if warnings else PASS,
        problems,
        warnings,
        {
            "article_count": len(articles),
            "ready_article_count": ready,
            "ready_article_ids": ready_article_ids,
            "stable_article_min": MU_STABLE_MIN,
            "argument_reference_high_min": ARG_REF_HIGH_MIN,
            "required_structure_coverage": {
                field: round(count / ready, 4) if ready else 0
                for field, count in required_structure_coverage.items()
            },
            "recommended_structure_coverage": {
                field: round(count / ready, 4) if ready else 0
                for field, count in recommended_structure_coverage.items()
            },
        },
    )


def _direct_text_keys(obj) -> list[str]:
    bad_keys = {
        "paragraph",
        "sentence",
        "draft_text",
        "rewritten_text",
        "copyable_text",
        "正文",
    }
    hits: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in bad_keys:
                hits.append(str(key))
            hits.extend(_direct_text_keys(value))
    elif isinstance(obj, list):
        for item in obj:
            hits.extend(_direct_text_keys(item))
    return hits


def _load_mu_pack_for_profile_batch(path: Path, data: dict) -> dict | None:
    source_pack = data.get("source_pack") or data.get("source_mu_pack")
    if not source_pack:
        return None
    candidate = Path(source_pack)
    if not candidate.is_absolute():
        candidate = (path.parent / candidate).resolve()
        if not candidate.exists():
            parents = list(path.parents)
            for parent in parents:
                maybe = parent / source_pack
                if maybe.exists():
                    candidate = maybe.resolve()
                    break
    if not candidate.exists():
        return None
    try:
        return load_json(candidate)
    except Exception:
        return None


def _ready_articles_from_mu_pack(pack: dict | None) -> tuple[set[str], int]:
    if not pack:
        return set(), 0
    ready_ids: set[str] = set()
    required = _cfg("gates.mu-fulltext-pack.required_article_fields", [])
    required_structure_fields = _cfg("gates.mu-fulltext-pack.required_structure_fields", [])
    for article in pack.get("articles") or []:
        if any(article.get(field) in (None, "", [], {}) for field in required):
            continue
        if any(article.get(field) in (None, "", [], {}) for field in required_structure_fields):
            continue
        if article.get("core_library_joined") is not True:
            continue
        fulltext = str(article.get("mu_fulltext") or "")
        if article.get("fulltext_sha256") != sha256_text(fulltext):
            continue
        provenance = article.get("provenance") or {}
        if any(not provenance.get(field) for field in ("source_ledger", "extraction_method", "mu_version")):
            continue
        ready_ids.add(str(article.get("article_id")))
    return ready_ids, len(ready_ids)


def gate_per_article_profile_complete(path: Path) -> dict:
    data = load_json(path)
    problems: list[str] = []
    warnings: list[str] = []
    if data.get("schema") != "journal_style_per_article_profile_batch_v1":
        problems.append(f"unexpected schema: {data.get('schema')}")
    profiles = data.get("profiles") or []
    mu_pack = _load_mu_pack_for_profile_batch(path, data)
    mu_ready_ids, mu_ready_count = _ready_articles_from_mu_pack(mu_pack)
    self_reported_count = int(data.get("ready_article_count") or data.get("source_ready_article_count") or 0)
    expected_count = mu_ready_count or self_reported_count or len(profiles)
    if (data.get("source_pack") or data.get("source_mu_pack")) and mu_pack is None:
        problems.append("source_pack declared but MinerU/mu pack could not be loaded")
    if mu_ready_count and self_reported_count and self_reported_count < mu_ready_count:
        problems.append(
            f"ready_article_count self-report {self_reported_count} below mu pack ready count {mu_ready_count}"
        )
    if not profiles:
        problems.append("no per-article profiles")
    if expected_count and len(profiles) < expected_count:
        problems.append(f"per-article profile count {len(profiles)} below ready article count {expected_count}")
    seen = set()
    for profile in profiles:
        article_id = profile.get("article_id")
        if not article_id:
            problems.append("profile missing article_id")
            continue
        if article_id in seen:
            problems.append(f"duplicate profile article_id: {article_id}")
        seen.add(article_id)
        if mu_ready_ids and article_id not in mu_ready_ids:
            problems.append(f"profile {article_id}: article_id not found in mu ready articles")
        if profile.get("schema") != "per_article_style_profile_v1":
            problems.append(f"profile {article_id}: schema mismatch")
        dims = profile.get("dimensions") or {}
        missing_dims = [dim for dim in PROFILE_REQUIRED_DIMS if dim not in dims]
        if missing_dims:
            problems.append(f"profile {article_id}: missing dimensions: {', '.join(missing_dims)}")
        evidence = profile.get("evidence_index") or []
        if not evidence:
            problems.append(f"profile {article_id}: evidence_index missing")
        for entry in evidence:
            if not entry.get("article_id") or not entry.get("evidence_path") or not entry.get("provenance"):
                problems.append(f"profile {article_id}: evidence entry lacks article_id/evidence_path/provenance")
                break
        hits = _direct_text_keys(profile.get("downstream_constraints") or [])
        if hits:
            problems.append(f"profile {article_id}: downstream constraints include direct reusable text keys: {', '.join(sorted(set(hits)))}")
    return result(
        "per-article-profile-complete",
        NO_GO if problems else DEGRADED if warnings else PASS,
        problems,
        warnings,
        {
            "profile_count": len(profiles),
            "expected_count": expected_count,
            "mu_ready_article_count": mu_ready_count,
            "self_reported_ready_article_count": self_reported_count,
        },
    )


def gate_aggregation_threshold(path: Path) -> dict:
    data = load_json(path)
    problems: list[str] = []
    warnings: list[str] = []
    if data.get("schema") != "journal_style_aggregation_bundle_v1":
        problems.append(f"unexpected schema: {data.get('schema')}")
    bundle_sample = int(data.get("sample_count") or 0)
    artifacts = data.get("artifacts") or []
    if not artifacts:
        problems.append("aggregation bundle has no artifacts")
    artifact_names = {artifact.get("name") for artifact in artifacts}
    missing_artifacts = [name for name in AGG_REQUIRED_ARTIFACTS if name not in artifact_names]
    if missing_artifacts:
        problems.append(f"aggregation bundle missing required artifacts: {', '.join(missing_artifacts)}")
    for artifact in artifacts:
        name = artifact.get("name") or "<unnamed>"
        dimension = str(artifact.get("dimension") or "")
        sample_count = int(artifact.get("sample_count") or bundle_sample or 0)
        conclusion = artifact.get("conclusion_strength")
        confidence = artifact.get("confidence")
        evidence = artifact.get("evidence_index") or []
        for field in ("sample_count", "coverage", "confidence", "degrade_label", "evidence_index"):
            if field not in artifact:
                problems.append(f"artifact {name}: missing {field}")
        if not evidence:
            problems.append(f"artifact {name}: evidence_index empty")
        if sample_count < AGG_PRELIM_MIN and conclusion != "sample_observation":
            problems.append(f"artifact {name}: sample_count {sample_count} below {AGG_PRELIM_MIN}; only sample_observation allowed")
        if sample_count < AGG_STABLE_MIN and conclusion == "stable":
            problems.append(f"artifact {name}: stable conclusion requires sample_count >= {AGG_STABLE_MIN}")
        if dimension in {"argument_style", "reference_ecology", "reference_network"} and sample_count < AGG_ARG_REF_HIGH_MIN and confidence == "high":
            problems.append(f"artifact {name}: high-confidence {dimension} requires sample_count >= {AGG_ARG_REF_HIGH_MIN}")
        if sample_count < AGG_STABLE_MIN and not artifact.get("degrade_label"):
            warnings.append(f"artifact {name}: low sample count should carry a degrade_label")
    return result(
        "aggregation-threshold",
        NO_GO if problems else DEGRADED if warnings else PASS,
        problems,
        warnings,
        {"bundle_sample_count": bundle_sample, "artifact_count": len(artifacts)},
    )


def gate_provenance_required(path: Path) -> dict:
    data = load_json(path)
    problems: list[str] = []
    warnings: list[str] = []
    evidence = data.get("evidence_index") or []
    if not evidence:
        problems.append("evidence_index missing or empty")
    for index, entry in enumerate(evidence, 1):
        if not (entry.get("article_id") or entry.get("source_article_id")):
            problems.append(f"evidence {index}: missing article_id/source_article_id")
        if not (entry.get("evidence_path") or entry.get("source_path")):
            problems.append(f"evidence {index}: missing evidence_path/source_path")
        if not entry.get("provenance"):
            problems.append(f"evidence {index}: missing provenance")
    if data.get("schema") == "journal_style_profile_v1":
        if data.get("metadata_only") is True and data.get("source_evidence_scope") == "mu_fulltext_core_pack":
            problems.append("metadata_only cannot be true when source_evidence_scope is mu_fulltext_core_pack")
        if data.get("source_evidence_scope") != "mu_fulltext_core_pack":
            warnings.append("profile is not backed by a MinerU/mu fulltext core pack; downstream fulltext style use must be degraded")
    return result(
        "provenance-required",
        NO_GO if problems else DEGRADED if warnings else PASS,
        problems,
        warnings,
        {"evidence_count": len(evidence), "schema": data.get("schema")},
    )


def gate_scoring_replay_calibrated(path: Path) -> dict:
    data = load_json(path)
    problems: list[str] = []
    warnings: list[str] = []
    if data.get("schema") != "journal_fit_scoring_model_v1":
        problems.append(f"unexpected schema: {data.get('schema')}")
    if data.get("not_editor_simulation") is not True:
        problems.append("scoring model must declare not_editor_simulation=true")
    if data.get("no_acceptance_prediction") is not True:
        problems.append("scoring model must declare no_acceptance_prediction=true")
    calibration = data.get("calibration") or {}
    rounds = int(calibration.get("rounds_completed") or 0)
    replay_count = int(calibration.get("replay_sample_count") or 0)
    if calibration.get("status") != "calibrated":
        problems.append("calibration.status must be calibrated")
    if calibration.get("source") != "per_article_profile_replay":
        problems.append("calibration.source must be per_article_profile_replay")
    if rounds < SCORING_ROUNDS_MIN:
        problems.append(f"calibration rounds {rounds} below minimum {SCORING_ROUNDS_MIN}")
    if replay_count < SCORING_REPLAY_MIN:
        problems.append(f"replay_sample_count {replay_count} below minimum {SCORING_REPLAY_MIN}")
    constraints = data.get("scoring_constraints") or {}
    if constraints.get("source") != "journal_style_aggregation_bundle":
        problems.append("scoring_constraints.source must be journal_style_aggregation_bundle")
    for group, keys in (
        ("section_hierarchy", ("section_min", "section_max")),
        ("abstract_keywords", ("keyword_min", "keyword_max")),
        ("reference_constraints", ("reference_min", "reference_max")),
    ):
        block = constraints.get(group) or {}
        for key in keys:
            if block.get(key) is None:
                problems.append(f"scoring_constraints.{group} missing {key}")
                break
    replay_scores = data.get("replay_scores") or []
    if len(replay_scores) < SCORING_REPLAY_MIN:
        problems.append("replay_scores below minimum")
    if replay_count and len(replay_scores) != replay_count:
        problems.append("replay_scores count must match calibration.replay_sample_count")
    replay_values: list[float] = []
    for index, item in enumerate(replay_scores, 1):
        if not item.get("article_id"):
            problems.append(f"replay score {index}: missing article_id")
            break
        if item.get("score") is None:
            problems.append(f"replay score {index}: missing score")
            break
        replay_values.append(float(item.get("score")))
    distribution = data.get("published_score_distribution") or {}
    if int(distribution.get("sample_count") or 0) < SCORING_REPLAY_MIN:
        problems.append("published_score_distribution sample_count below minimum")
    if int(distribution.get("sample_count") or 0) != len(replay_scores):
        problems.append("published_score_distribution sample_count must match replay_scores count")
    if distribution.get("source") != "replay_scores":
        problems.append("published_score_distribution.source must be replay_scores")
    for field in ("min", "q1", "median", "q3", "max"):
        if distribution.get(field) is None:
            problems.append(f"published_score_distribution missing {field}")
    if replay_values:
        expected = scoring_distribution(replay_values)
        for field in ("min", "q1", "median", "q3", "max"):
            if distribution.get(field) is not None and not same_number(distribution.get(field), expected.get(field)):
                problems.append(f"published_score_distribution {field} does not match replay_scores")
                break
    dimensions = data.get("dimensions") or []
    if not dimensions:
        problems.append("scoring dimensions missing")
    for dimension in dimensions:
        if not dimension.get("dimension") or dimension.get("weight") is None:
            problems.append("scoring dimension missing dimension/weight")
            break
        if not dimension.get("rationale"):
            problems.append(f"scoring dimension {dimension.get('dimension')}: missing rationale")
            break
    return result(
        "scoring-replay-calibrated",
        NO_GO if problems else DEGRADED if warnings else PASS,
        problems,
        warnings,
        {"rounds_completed": rounds, "replay_sample_count": replay_count},
    )


def gate_submission_fit_ready(path: Path) -> dict:
    data = load_json(path)
    scoring_verdict = gate_scoring_replay_calibrated(path)
    problems = list(scoring_verdict.get("problems") or [])
    warnings = list(scoring_verdict.get("warnings") or [])
    if data.get("schema") != "journal_fit_scoring_model_v1":
        problems.append("submission fit requires journal-fit-scoring-model.json as gate input")
    return result(
        "submission-fit-ready",
        NO_GO if problems else DEGRADED if warnings else PASS,
        problems,
        warnings,
        {"model_gate": scoring_verdict.get("verdict")},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run journal-style stage gates.")
    parser.add_argument(
        "--gate",
        required=True,
        choices=[
            "completion-label",
            "secret-boundary",
            "jiansuo-handoff",
            "abstract-metadata-ledger",
            "core-library",
            "fulltext-claims",
            "material-intake",
            "jiansuo-sidecar-safety",
            "dimension-evidence",
            "mu-fulltext-pack",
            "per-article-profile-complete",
            "aggregation-threshold",
            "provenance-required",
            "scoring-replay-calibrated",
            "submission-fit-ready",
        ],
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    # Fail-closed release integrity guard: close the side door of running gate
    # logic directly from a drifted run_stage_gates.py / config. Mirrors the
    # guard in gate_runner so neither path can be bypassed.
    try:
        from journal_style_runtime import (
            ReleaseIntegrityError,
            assert_release_integrity,
            integrity_failure_payload,
        )
        assert_release_integrity()
    except ReleaseIntegrityError as exc:
        print(json.dumps(integrity_failure_payload(exc, "run_stage_gates"),
                         ensure_ascii=False, indent=2))
        return 3
    except ImportError:
        # runtime helper unavailable: cannot prove integrity -> fail closed.
        print(json.dumps({"verdict": "NO_GO",
                          "problems": ["release integrity helper unavailable"]},
                         ensure_ascii=False))
        return 3

    input_path = Path(args.input).expanduser().resolve()
    handlers = {
        "completion-label": gate_completion_label,
        "secret-boundary": gate_secret_boundary,
        "jiansuo-handoff": gate_jiansuo_handoff,
        "abstract-metadata-ledger": gate_abstract_metadata_ledger,
        "core-library": gate_core_library,
        "fulltext-claims": gate_fulltext_claims,
        "material-intake": gate_material_intake,
        "jiansuo-sidecar-safety": gate_jiansuo_sidecar_safety,
        "dimension-evidence": gate_dimension_evidence,
        "mu-fulltext-pack": gate_mu_fulltext_pack,
        "per-article-profile-complete": gate_per_article_profile_complete,
        "aggregation-threshold": gate_aggregation_threshold,
        "provenance-required": gate_provenance_required,
        "scoring-replay-calibrated": gate_scoring_replay_calibrated,
        "submission-fit-ready": gate_submission_fit_ready,
    }
    gate_result = handlers[args.gate](input_path)
    text = json.dumps(gate_result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if gate_result["verdict"] in {PASS, DEGRADED} else 1


if __name__ == "__main__":
    raise SystemExit(main())
