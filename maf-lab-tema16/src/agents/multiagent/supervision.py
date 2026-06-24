from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class SupervisionSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class SupervisionEventType(StrEnum):
    DELEGATION = "delegation"
    TOOL_CALL = "tool_call"
    STATE_UPDATE = "state_update"
    RECOMMENDATION = "recommendation"
    RISK_DETECTED = "risk_detected"
    CONFLICT_DETECTED = "conflict_detected"
    POLICY_CHECK = "policy_check"
    ERROR = "error"


@dataclass
class SupervisionEvent:
    run_id: str
    agent_name: str
    event_type: SupervisionEventType
    severity: SupervisionSeverity
    summary: str

    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    details: dict[str, Any] = field(default_factory=dict)
    requires_review: bool = False


@dataclass
class SupervisionDecision:
    run_id: str
    allowed_to_continue: bool
    decision: str
    reasons: list[str]
    required_actions: list[str]
    max_severity: SupervisionSeverity


class InMemorySupervisionStore:
    def __init__(self) -> None:
        self._events: list[SupervisionEvent] = []

    def record(self, event: SupervisionEvent) -> SupervisionEvent:
        self._events.append(event)
        return event

    def list_by_run_id(self, run_id: str) -> list[SupervisionEvent]:
        return [event for event in self._events if event.run_id == run_id]

    def to_json(self, run_id: str) -> str:
        events = self.list_by_run_id(run_id)
        return json.dumps(
            [asdict(event) for event in events],
            ensure_ascii=False,
            indent=2,
        )

    def evaluate_policies(self, run_id: str) -> SupervisionDecision:
        events = self.list_by_run_id(run_id)

        reasons: list[str] = []
        required_actions: list[str] = []
        allowed_to_continue = True

        severities = [event.severity for event in events]
        max_severity = (
            SupervisionSeverity.INFO
            if not severities
            else _max_severity(severities)
        )

        text_blob = " ".join(
            [
                event.summary.lower() + " " + json.dumps(event.details).lower()
                for event in events
            ]
        )

        security_consulted = any(
            event.agent_name == "security_specialist" for event in events
        )

        if "administrador" in text_blob or "admin" in text_blob:
            if not security_consulted:
                allowed_to_continue = False
                reasons.append(
                    "Se menciona acceso administrador, pero no consta revisión de seguridad."
                )
                required_actions.append("Consultar security_specialist antes de continuar.")

        if "borrar" in text_blob or "eliminar" in text_blob or "producción" in text_blob:
            allowed_to_continue = False
            reasons.append(
                "Se detecta posible acción irreversible o sobre producción."
            )
            required_actions.append("Solicitar aprobación humana explícita.")

        if any(event.requires_review for event in events):
            allowed_to_continue = False
            reasons.append("Hay eventos marcados como requires_review=True.")
            required_actions.append("Revisión manual o validación del coordinador.")

        if any(event.severity == SupervisionSeverity.CRITICAL for event in events):
            allowed_to_continue = False
            reasons.append("Existe al menos un evento crítico.")
            required_actions.append("Escalar antes de entregar respuesta final.")

        if not reasons:
            reasons.append("No se han detectado incumplimientos de política.")

        return SupervisionDecision(
            run_id=run_id,
            allowed_to_continue=allowed_to_continue,
            decision="continue" if allowed_to_continue else "blocked",
            reasons=reasons,
            required_actions=required_actions,
            max_severity=max_severity,
        )


def _max_severity(severities: list[SupervisionSeverity]) -> SupervisionSeverity:
    order = {
        SupervisionSeverity.INFO: 1,
        SupervisionSeverity.WARNING: 2,
        SupervisionSeverity.HIGH: 3,
        SupervisionSeverity.CRITICAL: 4,
    }

    return max(severities, key=lambda severity: order[severity])


SUPERVISION_STORE = InMemorySupervisionStore()


def event_to_json(event: SupervisionEvent) -> str:
    return json.dumps(asdict(event), ensure_ascii=False, indent=2)


def decision_to_json(decision: SupervisionDecision) -> str:
    return json.dumps(asdict(decision), ensure_ascii=False, indent=2)