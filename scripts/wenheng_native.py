from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


STYLE_MEMORY_NOT_APPLICABLE = "journal-style 只做期刊画像和投稿匹配分析，不生成正式正文，G07 写作风格规则不适用。"
WENHENG_BINDING_RECEIPT = "00-intake/wenheng-native-binding.json"
WENHENG_INTAKE_REQUEST = "00-intake/wenheng-intake-request.json"
ALLOW_TOKENS = {"allow", "allowed", "approved"}
REJECT_TOKENS = {"forbidden", "blocked", "deny", "denied", "rejected", "disabled"}
DECISION_SAFE_FIELDS = ("target_skill", "target_channel", "task_type", "target_task_type", "channel", "channel_id", "decision", "status", "reason")


class WenhengNativeError(RuntimeError):
    """Raised when production/native Wenheng binding is missing or invalid."""


def add_wenheng_args(parser: Any) -> None:
    parser.add_argument("--wenheng-task-id", default=os.getenv("WENHENG_TASK_ID", ""))
    parser.add_argument("--wenheng-backend-url", default=os.getenv("WENHENG_BACKEND_URL", ""))


def production_required() -> bool:
    return os.getenv("WENHENG_PRODUCTION_MODE") == "1" or os.getenv("WENHENG_NATIVE_REQUIRED") == "1"


def write_binding_receipt(task_dir: Path, binding: dict[str, Any]) -> Path:
    path = Path(task_dir) / WENHENG_BINDING_RECEIPT
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "journal_style_wenheng_binding_receipt_v1",
        "binding": binding,
        "production_evidence_allowed": bool(binding.get("production_evidence_allowed")),
        "source": "journal-style-startup",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_binding_receipt(task_dir: Path) -> dict[str, Any]:
    path = Path(task_dir) / WENHENG_BINDING_RECEIPT
    if not path.is_file():
        raise WenhengNativeError(f"missing Wenheng native binding receipt: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise WenhengNativeError(f"invalid Wenheng native binding receipt JSON: {path}") from exc
    if payload.get("schema") != "journal_style_wenheng_binding_receipt_v1":
        raise WenhengNativeError("Wenheng native binding receipt schema mismatch")
    binding = payload.get("binding")
    if not isinstance(binding, dict):
        raise WenhengNativeError("Wenheng native binding receipt missing binding object")
    return binding


def validate_binding_receipt(task_dir: Path, *, production: bool | None = None) -> dict[str, Any]:
    production_mode = production_required() if production is None else production
    try:
        binding = load_binding_receipt(task_dir)
    except WenhengNativeError:
        if production_mode:
            raise
        return {}
    if not binding.get("native") or binding.get("binding_status") != "validated_by_b02_task_api":
        if production_mode:
            raise WenhengNativeError("Wenheng native binding receipt is not validated by B02 task API")
        return binding
    required_fields = [
        "wenheng_task_id",
        "task_folder",
        "target_skill",
        "h08_evidence_stub",
        "f06_channel_decision",
        "h08",
        "archive",
        "style_memory_not_applicable_reason",
    ]
    missing = [field for field in required_fields if not binding.get(field)]
    if missing:
        raise WenhengNativeError(f"Wenheng native binding receipt missing required fields: {', '.join(missing)}")
    if binding.get("task_type") != "journal_style" or binding.get("skill_id") != "journal_style":
        raise WenhengNativeError("Wenheng native binding receipt task_type/skill_id mismatch")
    if not binding.get("production_evidence_allowed"):
        raise WenhengNativeError("Wenheng native binding receipt does not allow production evidence")
    return binding


def build_intake_request(target_journal: str = "") -> dict[str, Any]:
    return {
        "schema": "journal_style_wenheng_intake_request_v1",
        "target_journal": target_journal,
        "task_type": "journal_style",
        "target_skill": "journal-style",
        "required_wenheng_fields": [
            "wenheng_task_id",
            "task_folder",
            "task_type=journal_style",
            "target_skill",
            "f06_routing_decision",
            "h08_evidence_stub",
        ],
        "allowed_action_without_binding": "intake_request_only",
        "production_evidence_allowed": False,
        "next_action": "Create or bind a Wenheng B02 journal_style task via /api/tasks, then rerun journal-style-startup.",
    }


def _task_folder(task: dict[str, Any]) -> str:
    return str(task.get("task_folder") or task.get("folder") or task.get("relative_task_folder") or "")


def _h08_evidence_stub(task: dict[str, Any]) -> Any:
    return (
        task.get("h08_evidence_stub")
        or (task.get("h08") or {}).get("evidence_stub")
        or task.get("evidence_stub")
        or task.get("evidence_path")
    )


def write_intake_request(task_dir: Path, target_journal: str = "") -> Path:
    path = Path(task_dir) / WENHENG_INTAKE_REQUEST
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_intake_request(target_journal), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _backend_read_key() -> str:
    return os.getenv("WENHENG_BACKEND_READ_API_KEY", "")


def _backend_write_key() -> str:
    return os.getenv("WENHENG_BACKEND_API_KEY", "")


def _routing(task: dict[str, Any]) -> dict[str, Any]:
    return task.get("routing") if isinstance(task.get("routing"), dict) else {}


def _extract_task(payload: dict[str, Any]) -> dict[str, Any]:
    task = payload.get("task") if isinstance(payload.get("task"), dict) else payload
    return task if isinstance(task, dict) else {}


def _safe_decision(item: dict[str, Any]) -> dict[str, Any]:
    return {key: item[key] for key in DECISION_SAFE_FIELDS if key in item and item[key] not in (None, "")}


def _decision_token(item: dict[str, Any]) -> str:
    return str(item.get("decision") or item.get("status") or "").strip().lower()


def _skill_aliases(skill_id: str) -> set[str]:
    return {skill_id, skill_id.replace("_", "-"), skill_id.replace("-", "_")}


def _decision_matches(item: dict[str, Any], *, task: dict[str, Any], skill_id: str, task_type: str) -> bool:
    routing = _routing(task)
    item_skill = str(item.get("target_skill") or routing.get("target_skill") or task.get("target_skill") or "").strip()
    if item_skill not in _skill_aliases(skill_id):
        return False
    item_task_type = str(item.get("task_type") or item.get("target_task_type") or routing.get("task_type") or task.get("task_type") or "").strip()
    if item_task_type and item_task_type != task_type:
        return False
    expected_channel = str(routing.get("target_channel") or task.get("target_channel") or task.get("channel") or "journal_style").strip()
    item_channel = str(item.get("target_channel") or item.get("channel") or item.get("channel_id") or expected_channel).strip()
    if expected_channel and item_channel and item_channel != expected_channel:
        return False
    return True


def _normalize_f06_channel_decision(task: dict[str, Any], *, skill_id: str, task_type: str) -> dict[str, Any]:
    routing = _routing(task)
    channel_decision = routing.get("channel_decision") if isinstance(routing.get("channel_decision"), dict) else {}
    decisions = channel_decision.get("decisions") if isinstance(channel_decision.get("decisions"), list) else []
    dict_decisions = [item for item in decisions if isinstance(item, dict)]
    if not dict_decisions:
        raise WenhengNativeError("F06 routing.channel_decision.decisions[] is missing; single-field F06 verdict is not native authority")
    matched = [item for item in dict_decisions if _decision_matches(item, task=task, skill_id=skill_id, task_type=task_type)]
    if not matched:
        raise WenhengNativeError("F06 channel decision has no matching decision for journal-style task")
    rejected = [item for item in matched if _decision_token(item) in REJECT_TOKENS]
    if rejected:
        raise WenhengNativeError(f"F06 channel decision blocks this task: {_safe_decision(rejected[0])}")
    allowed = [item for item in matched if _decision_token(item) in ALLOW_TOKENS]
    if not allowed:
        raise WenhengNativeError("F06 channel decision is not explicitly allowed for journal-style task")
    first = allowed[0]
    return {
        "verdict": "allowed",
        "source_path": "routing.channel_decision.decisions[]",
        "matched_decision": _safe_decision(first),
        "decisions_evaluated": len(dict_decisions),
        "skill_id": skill_id,
        "task_type": task_type,
        "target_channel": str(routing.get("target_channel") or task.get("target_channel") or first.get("channel_id") or "journal_style"),
    }


def verify_wenheng_native(args: Any, *, skill_id: str = "journal_style", task_type: str = "journal_style") -> dict[str, Any]:
    task_id = getattr(args, "wenheng_task_id", "") or os.getenv("WENHENG_TASK_ID", "")
    backend_url = (getattr(args, "wenheng_backend_url", "") or os.getenv("WENHENG_BACKEND_URL", "")).rstrip("/")
    read_api_key = _backend_read_key()
    write_api_key = _backend_write_key()
    allow_legacy = os.getenv("WENHENG_ALLOW_LEGACY_FLOW") == "1"
    required = os.getenv("WENHENG_PRODUCTION_MODE") == "1" or os.getenv("WENHENG_NATIVE_REQUIRED") == "1" or bool(task_id) or not allow_legacy
    if not required:
        return {
            "binding_status": "standalone_design_flow",
            "native": False,
            "skill_id": skill_id,
            "task_type": task_type,
            "note": "Legacy/offline design startup is explicitly allowed via WENHENG_ALLOW_LEGACY_FLOW=1, but it is not Wenheng native completion evidence.",
            "style_memory_not_applicable_reason": STYLE_MEMORY_NOT_APPLICABLE,
            "production_evidence_allowed": False,
        }
    if not task_id:
        raise WenhengNativeError(f"{skill_id} requires WENHENG_TASK_ID or --wenheng-task-id; set WENHENG_ALLOW_LEGACY_FLOW=1 only for standalone offline debugging")
    if not backend_url:
        raise WenhengNativeError("Wenheng native mode requires WENHENG_BACKEND_URL")
    if not read_api_key:
        raise WenhengNativeError("Wenheng native B02 read requires WENHENG_BACKEND_READ_API_KEY")
    if not write_api_key:
        raise WenhengNativeError("Wenheng native H08/C03 writeback requires WENHENG_BACKEND_API_KEY")
    task = _extract_task(_get_json(f"{backend_url}/api/tasks/{urllib.parse.quote(task_id)}", read_api_key))
    if not task:
        raise WenhengNativeError(f"B02 task validation failed for {task_id}: missing task payload")
    actual_type = task.get("task_type") or task.get("type")
    if actual_type and actual_type != task_type:
        raise WenhengNativeError(f"B02 task type mismatch: expected {task_type}, got {actual_type}")
    task_folder = _task_folder(task)
    routing = _routing(task)
    target_skill = str(routing.get("target_skill") or task.get("target_skill") or "")
    h08_evidence_stub = _h08_evidence_stub(task)
    missing_packet = []
    if not task_folder:
        missing_packet.append("task_folder")
    if not target_skill:
        missing_packet.append("target_skill")
    if not h08_evidence_stub:
        missing_packet.append("h08_evidence_stub")
    if missing_packet:
        raise WenhengNativeError(f"B02 task packet missing required field(s): {', '.join(missing_packet)}")
    channel_decision = _normalize_f06_channel_decision(task, skill_id=skill_id, task_type=task_type)
    learning_event = _record_learning_event(
        backend_url,
        write_api_key,
        {
            "source": "workflow_deviation",
            "task_id": task_id,
            "skill_id": skill_id,
            "severity": "P3",
            "symptom": "journal-style native startup validated B02/F06 and recorded G07 not-applicable usage.",
            "prevention_rule_candidate": "journal-style must bind B02/F06 before producing C03 handoff; legacy output cannot become production evidence.",
            "targets": ["B02_TIMELINE", "H08_ERROR_REVIEW", "G07_CANDIDATE", "DEV_ISSUE"],
            "metadata": {"runtime_contract": "wenheng-skill-runtime-contract-v2", "source": "journal-style-startup"},
        },
    )
    return {
        "binding_status": "validated_by_b02_task_api",
        "native": True,
        "skill_id": skill_id,
        "task_type": task_type,
        "wenheng_task_id": task_id,
        "task_folder": task_folder,
        "target_skill": target_skill,
        "source_run_id": task.get("source_run_id"),
        "f06_channel_decision": channel_decision,
        "h08_evidence_stub": h08_evidence_stub,
        "style_memory": {
            "source": "G07",
            "rules_applied": [],
            "rules_ignored": [],
            "conflicts": [],
            "not_applicable_reason": STYLE_MEMORY_NOT_APPLICABLE,
        },
        "style_memory_not_applicable_reason": STYLE_MEMORY_NOT_APPLICABLE,
        "h08": {"evidence_required": True, "error_review_required_on_failure": True},
        "archive": {"required": True},
        "learning_event_id": learning_event.get("event", {}).get("event_id") if learning_event else None,
        "production_evidence_allowed": True,
    }


def _get_json(url: str, api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "X-API-Key": api_key})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8", errors="replace")
            payload = json.loads(raw) if raw.strip() else {}
        except Exception:
            payload = {}
        code = payload.get("code") if isinstance(payload, dict) else None
        raise WenhengNativeError(f"B02 task validation read failed using WENHENG_BACKEND_READ_API_KEY: {exc.code}{f'/{code}' if code else ''}") from exc


def _record_learning_event(backend_url: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{backend_url}/api/h08/learning-events",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json", "X-API-Key": api_key},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        if os.getenv("WENHENG_LEARNING_EVENT_REQUIRED") == "1" or os.getenv("WENHENG_PRODUCTION_MODE") == "1":
            raise
        return None
