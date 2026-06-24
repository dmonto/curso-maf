from __future__ import annotations

from typing import Any


def classify_audit_event(event: dict[str, Any]) -> str:
    """
    Clasifica un evento de auditoría en una política de retención.

    La clasificación se basa en metadatos estructurados, no en texto libre.
    """

    event_type = event.get("event_type")
    component = event.get("component")
    action = event.get("action")
    metadata = event.get("metadata") or {}

    if metadata.get("blocked") and "api_key_like" in metadata.get("match_kinds", []):
        return "secret_value"

    if event_type in {"sensitive_action_requested", "sensitive_action_approved"}:
        return "sensitive_action"

    if event_type in {"tool_call", "rag_retrieval", "assistant_response_generated"}:
        return "interaction_audit"

    if event_type in {"user_message_received"}:
        if metadata.get("has_sensitive_data"):
            return "sensitive_detection"
        return "interaction_audit"

    if event_type in {"agent_error"}:
        return "technical_log"

    if component in {"application", "input_guard", "output_guard"}:
        return "interaction_audit"

    if action in {"debug", "health_check"}:
        return "technical_log"

    return "interaction_audit"