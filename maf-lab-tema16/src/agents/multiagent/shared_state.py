from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class ChangeEntry:
    version: int
    updated_by: str
    updated_at_utc: str
    changes: dict[str, Any]
    reason: str


@dataclass
class SharedCaseState:
    case_id: str
    service: str | None = None
    user_area: str | None = None
    symptom: str | None = None
    location: str | None = None
    vpn_connected: bool | None = None
    error_message: str | None = None

    network_findings: list[str] = field(default_factory=list)
    identity_findings: list[str] = field(default_factory=list)
    security_constraints: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    itsm_findings: list[str] = field(default_factory=list)

    pending_data: list[str] = field(default_factory=list)
    priority_suggestion: str | None = None
    next_action: str | None = None
    case_status: str = "open"

    version: int = 1
    change_history: list[ChangeEntry] = field(default_factory=list)


ROLE_ALLOWED_FIELDS: dict[str, set[str]] = {
    "support_coordinator": {
        "service",
        "user_area",
        "symptom",
        "location",
        "error_message",
        "pending_data",
        "next_action",
        "case_status",
    },
    "network_specialist": {
        "vpn_connected",
        "network_findings",
        "pending_data",
    },
    "identity_specialist": {
        "identity_findings",
        "pending_data",
    },
    "security_specialist": {
        "security_constraints",
        "risk_flags",
        "pending_data",
    },
    "itsm_specialist": {
        "itsm_findings",
        "priority_suggestion",
        "pending_data",
    },
}


class StateConflictError(Exception):
    pass


class StatePermissionError(Exception):
    pass


class InMemorySharedStateStore:
    def __init__(self) -> None:
        self._cases: dict[str, SharedCaseState] = {}

    def create_case(self, initial_data: dict[str, Any] | None = None) -> SharedCaseState:
        case_id = str(uuid4())
        state = SharedCaseState(case_id=case_id)

        if initial_data:
            for key, value in initial_data.items():
                if hasattr(state, key):
                    setattr(state, key, value)

        self._cases[case_id] = state
        return deepcopy(state)

    def get_case(self, case_id: str) -> SharedCaseState:
        if case_id not in self._cases:
            raise KeyError(f"No existe el caso {case_id}")

        return deepcopy(self._cases[case_id])

    def update_case(
        self,
        *,
        case_id: str,
        role: str,
        expected_version: int,
        changes: dict[str, Any],
        reason: str,
    ) -> SharedCaseState:
        if case_id not in self._cases:
            raise KeyError(f"No existe el caso {case_id}")

        state = self._cases[case_id]

        if state.version != expected_version:
            raise StateConflictError(
                f"Conflicto de versión. Versión actual={state.version}, "
                f"versión esperada={expected_version}"
            )

        allowed_fields = ROLE_ALLOWED_FIELDS.get(role)

        if allowed_fields is None:
            raise StatePermissionError(f"Rol no reconocido: {role}")

        forbidden = set(changes.keys()) - allowed_fields

        if forbidden:
            raise StatePermissionError(
                f"El rol {role} no puede modificar estos campos: {sorted(forbidden)}"
            )

        applied_changes: dict[str, Any] = {}

        for key, value in changes.items():
            if not hasattr(state, key):
                raise ValueError(f"Campo de estado no válido: {key}")

            current_value = getattr(state, key)

            if isinstance(current_value, list):
                if isinstance(value, list):
                    current_value.extend(value)
                else:
                    current_value.append(value)

                applied_changes[key] = value
            else:
                setattr(state, key, value)
                applied_changes[key] = value

        state.version += 1
        state.change_history.append(
            ChangeEntry(
                version=state.version,
                updated_by=role,
                updated_at_utc=datetime.now(timezone.utc).isoformat(),
                changes=applied_changes,
                reason=reason,
            )
        )

        return deepcopy(state)


STATE_STORE = InMemorySharedStateStore()


def state_to_json(state: SharedCaseState) -> str:
    return json.dumps(asdict(state), ensure_ascii=False, indent=2)