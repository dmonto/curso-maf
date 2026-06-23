from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONTROL_FIELD_MAP = {
    "identity_context": "has_identity_context",
    "access_policy": "has_access_policy",
    "sensitive_data_guard": "has_sensitive_data_guard",
    "audit_events": "has_audit_events",
    "retention_policy": "has_retention_policy",
    "model_gateway": "uses_model_gateway",
    "risk_assessment": "has_risk_assessment"
}


def profile_has_control(profile: dict[str, Any], control: str) -> bool:
    if control == "rag_filters":
        filters = set(profile.get("rag_filters", []))
        return {"tenant_id", "groups", "classification"}.issubset(filters)

    field = CONTROL_FIELD_MAP.get(control)

    if field is None:
        return False

    return bool(profile.get(field))


def load_audit_events(paths: list[Path]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for path in paths:
        if not path.exists():
            continue

        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    events.append(json.loads(line))

    return events


def event_types_present(events: list[dict[str, Any]]) -> set[str]:
    present = {event.get("event_type") for event in events if event.get("event_type")}

    # Normalizamos algunos eventos equivalentes usados en laboratorios anteriores.
    if any(event.get("metadata", {}).get("has_sensitive_data") for event in events):
        present.add("sensitive_detection")

    if Path("logs/retention_purge_log.jsonl").exists():
        present.add("retention_purge")

    return present


def evidence_file_exists(path: str) -> bool:
    return Path(path).exists()