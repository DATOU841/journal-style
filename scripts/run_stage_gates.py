#!/usr/bin/env python3
"""Run journal-style stage gates on synthetic or task-local metadata files."""

from __future__ import annotations

import argparse
import json
import re
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
            "dimension-evidence",
        ],
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    handlers = {
        "completion-label": gate_completion_label,
        "secret-boundary": gate_secret_boundary,
        "jiansuo-handoff": gate_jiansuo_handoff,
        "abstract-metadata-ledger": gate_abstract_metadata_ledger,
        "core-library": gate_core_library,
        "fulltext-claims": gate_fulltext_claims,
        "material-intake": gate_material_intake,
        "dimension-evidence": gate_dimension_evidence,
    }
    gate_result = handlers[args.gate](input_path)
    text = json.dumps(gate_result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if gate_result["verdict"] in {PASS, DEGRADED} else 1


if __name__ == "__main__":
    raise SystemExit(main())
