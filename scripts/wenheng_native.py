from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


STYLE_MEMORY_NOT_APPLICABLE = "journal-style 只做期刊画像和投稿匹配分析，不生成正式正文，G07 写作风格规则不适用。"


def add_wenheng_args(parser: Any) -> None:
    parser.add_argument("--wenheng-task-id", default=os.getenv("WENHENG_TASK_ID", ""))
    parser.add_argument("--wenheng-backend-url", default=os.getenv("WENHENG_BACKEND_URL", ""))


def verify_wenheng_native(args: Any, *, skill_id: str = "journal_style", task_type: str = "journal_style") -> dict[str, Any]:
    task_id = getattr(args, "wenheng_task_id", "") or os.getenv("WENHENG_TASK_ID", "")
    backend_url = (getattr(args, "wenheng_backend_url", "") or os.getenv("WENHENG_BACKEND_URL", "")).rstrip("/")
    api_key = os.getenv("WENHENG_BACKEND_API_KEY", "")
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
        raise RuntimeError(f"{skill_id} requires WENHENG_TASK_ID or --wenheng-task-id; set WENHENG_ALLOW_LEGACY_FLOW=1 only for standalone offline debugging")
    if not backend_url or not api_key:
        raise RuntimeError("Wenheng native mode requires WENHENG_BACKEND_URL and WENHENG_BACKEND_API_KEY")
    task = _get_json(f"{backend_url}/api/tasks/{urllib.parse.quote(task_id)}", api_key).get("task")
    if not task:
        raise RuntimeError(f"B02 task validation failed for {task_id}: missing task payload")
    actual_type = task.get("task_type") or task.get("type")
    if actual_type and actual_type != task_type:
        raise RuntimeError(f"B02 task type mismatch: expected {task_type}, got {actual_type}")
    channel_decision = task.get("routing_decision", {}).get("channel_decision") or task.get("routing", {}).get("channel_decision") or task.get("channel_decision") or {}
    verdict = str(channel_decision.get("verdict") or channel_decision.get("decision") or "").lower()
    if not verdict:
        raise RuntimeError("F06 final verdict is missing; journal-style native runtime must fail closed before analysis or C03 handoff")
    if verdict in {"forbidden", "blocked", "deny", "denied"}:
        raise RuntimeError(f"F06 channel decision blocks this task: {channel_decision.get('reason') or channel_decision}")
    learning_event = _record_learning_event(
        backend_url,
        api_key,
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
        "f06_channel_decision": channel_decision,
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
        raise RuntimeError(f"B02 task validation failed: {exc.code}") from exc


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
