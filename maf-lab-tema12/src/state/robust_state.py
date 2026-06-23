from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


CaseStatus = Literal[
    "new",
    "collecting_info",
    "ready_for_draft",
    "draft_prepared",
    "blocked",
    "closed",
]

IssueSeverity = Literal["info", "warning", "error", "blocking"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class StateIssue:
    code: str
    severity: IssueSeverity
    message: str
    field: str | None = None


@dataclass
class StateValidationReport:
    issues: list[StateIssue] = field(default_factory=list)

    def add(
        self,
        code: str,
        severity: IssueSeverity,
        message: str,
        field: str | None = None,
    ) -> None:
        self.issues.append(
            StateIssue(
                code=code,
                severity=severity,
                message=message,
                field=field,
            )
        )

    @property
    def has_blocking(self) -> bool:
        return any(issue.severity == "blocking" for issue in self.issues)

    @property
    def has_errors(self) -> bool:
        return any(issue.severity in {"error", "blocking"} for issue in self.issues)

    def status(self) -> str:
        if self.has_blocking:
            return "blocking"
        if self.has_errors:
            return "error"
        if any(issue.severity == "warning" for issue in self.issues):
            return "warning"
        return "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status(),
            "issues": [asdict(issue) for issue in self.issues],
        }


@dataclass
class StateEvent:
    event_id: str
    event_type: str
    created_utc: str
    actor: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class SupportCaseState:
    user_id: str
    session_id: str
    status: CaseStatus = "new"

    memory: dict[str, Any] = field(default_factory=dict)
    rolling_summary: str = ""
    recent_turns: list[dict[str, Any]] = field(default_factory=list)

    flags: dict[str, Any] = field(default_factory=dict)
    draft: dict[str, Any] | None = None

    schema_version: str = "1"
    state_version: int = 0
    created_utc: str = field(default_factory=utc_now)
    updated_utc: str = field(default_factory=utc_now)

    last_validation_report: dict[str, Any] | None = None
    events: list[StateEvent] = field(default_factory=list)

    def add_event(
        self,
        event_type: str,
        actor: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            StateEvent(
                event_id=uuid4().hex,
                event_type=event_type,
                created_utc=utc_now(),
                actor=actor,
                payload=payload or {},
            )
        )

        # Evitamos que el estado crezca indefinidamente.
        self.events = self.events[-50:]

    def touch(self) -> None:
        self.state_version += 1
        self.updated_utc = utc_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "status": self.status,
            "memory": self.memory,
            "rolling_summary": self.rolling_summary,
            "recent_turns": self.recent_turns,
            "flags": self.flags,
            "draft": self.draft,
            "schema_version": self.schema_version,
            "state_version": self.state_version,
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
            "last_validation_report": self.last_validation_report,
            "events": [asdict(event) for event in self.events],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SupportCaseState":
        migrated = migrate_state_dict(data)

        events = [
            StateEvent(**event)
            for event in migrated.get("events", [])
            if isinstance(event, dict)
        ]

        return cls(
            user_id=migrated["user_id"],
            session_id=migrated["session_id"],
            status=migrated.get("status", "new"),
            memory=migrated.get("memory", {}),
            rolling_summary=migrated.get("rolling_summary", ""),
            recent_turns=migrated.get("recent_turns", []),
            flags=migrated.get("flags", {}),
            draft=migrated.get("draft"),
            schema_version=migrated.get("schema_version", "1"),
            state_version=int(migrated.get("state_version", 0)),
            created_utc=migrated.get("created_utc", utc_now()),
            updated_utc=migrated.get("updated_utc", utc_now()),
            last_validation_report=migrated.get("last_validation_report"),
            events=events,
        )


class InvalidStateTransition(RuntimeError):
    pass


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "new": {"collecting_info", "blocked"},
    "collecting_info": {"ready_for_draft", "blocked", "closed"},
    "ready_for_draft": {"draft_prepared", "blocked", "closed"},
    "draft_prepared": {"closed", "blocked"},
    "blocked": {"collecting_info", "closed"},
    "closed": {"collecting_info"},
}


def migrate_state_dict(data: dict[str, Any]) -> dict[str, Any]:
    """
    Migración mínima para laboratorio.

    Si en el futuro cambia el esquema, este es el punto donde convertimos
    estados antiguos a la versión actual.
    """
    schema_version = data.get("schema_version", "0")

    if schema_version == "1":
        return data

    if schema_version == "0":
        migrated = {
            "user_id": data["user_id"],
            "session_id": data["session_id"],
            "status": data.get("status", "new"),
            "memory": data.get("memory", {}),
            "rolling_summary": data.get("summary", ""),
            "recent_turns": data.get("recent_turns", []),
            "flags": data.get("flags", {}),
            "draft": data.get("draft"),
            "schema_version": "1",
            "state_version": int(data.get("state_version", 0)),
            "created_utc": data.get("created_utc", utc_now()),
            "updated_utc": data.get("updated_utc", utc_now()),
            "last_validation_report": data.get("last_validation_report"),
            "events": data.get("events", []),
        }
        return migrated

    raise ValueError(f"Versión de esquema no soportada: {schema_version}")


class SupportCaseStateMachine:
    """
    Máquina de estados del caso.

    El agente no cambia el estado directamente.
    La aplicación invoca comandos controlados sobre esta clase.
    """

    def validate(self, state: SupportCaseState) -> StateValidationReport:
        report = StateValidationReport()

        if not state.user_id:
            report.add(
                code="missing_user_id",
                severity="blocking",
                message="El estado no tiene user_id.",
                field="user_id",
            )

        if not state.session_id:
            report.add(
                code="missing_session_id",
                severity="blocking",
                message="El estado no tiene session_id.",
                field="session_id",
            )

        if state.status not in ALLOWED_TRANSITIONS:
            report.add(
                code="invalid_status",
                severity="blocking",
                message=f"Estado no reconocido: {state.status}",
                field="status",
            )

        priority = state.memory.get("prioridad")
        if priority and priority not in {"p1", "p2", "p3", "p4"}:
            report.add(
                code="invalid_priority",
                severity="error",
                message=f"Prioridad no válida: {priority}",
                field="memory.prioridad",
            )

        if state.status == "ready_for_draft":
            if not state.memory.get("servicio"):
                report.add(
                    code="missing_service_ready_for_draft",
                    severity="blocking",
                    message="No se puede preparar borrador sin servicio afectado.",
                    field="memory.servicio",
                )

            if state.memory.get("usuarios_afectados") is None:
                report.add(
                    code="missing_impact_ready_for_draft",
                    severity="warning",
                    message="Conviene conocer cuántos usuarios están afectados.",
                    field="memory.usuarios_afectados",
                )

        if state.status == "draft_prepared" and not state.draft:
            report.add(
                code="missing_draft",
                severity="blocking",
                message="El estado indica draft_prepared, pero no hay borrador.",
                field="draft",
            )

        if state.status == "closed":
            if state.flags.get("lock_active"):
                report.add(
                    code="closed_case_with_active_lock",
                    severity="warning",
                    message="El caso está cerrado pero conserva un lock activo.",
                    field="flags.lock_active",
                )

        state.last_validation_report = report.to_dict()
        return report

    def transition(
        self,
        state: SupportCaseState,
        target_status: CaseStatus,
        actor: str,
        reason: str,
    ) -> None:
        allowed = ALLOWED_TRANSITIONS.get(state.status, set())

        if target_status not in allowed:
            raise InvalidStateTransition(
                f"Transición no permitida: {state.status} → {target_status}"
            )

        previous = state.status
        state.status = target_status
        state.touch()
        state.add_event(
            event_type="state_transition",
            actor=actor,
            payload={
                "from": previous,
                "to": target_status,
                "reason": reason,
                "state_version": state.state_version,
            },
        )

        report = self.validate(state)

        if report.has_blocking:
            state.status = "blocked"
            state.touch()
            state.add_event(
                event_type="state_blocked",
                actor="system",
                payload={
                    "reason": "validation_failed_after_transition",
                    "report": report.to_dict(),
                },
            )

    def apply_user_message(
        self,
        state: SupportCaseState,
        user_text: str,
        actor: str = "user",
    ) -> None:
        if state.status == "closed":
            state.add_event(
                event_type="message_rejected",
                actor="system",
                payload={
                    "reason": "case_closed",
                    "message_preview": user_text[:200],
                },
            )
            return

        state.recent_turns.append(
            {
                "role": "user",
                "content": user_text[:1200],
                "created_utc": utc_now(),
            }
        )
        state.recent_turns = state.recent_turns[-12:]

        state.touch()
        state.add_event(
            event_type="user_message_applied",
            actor=actor,
            payload={
                "message_length": len(user_text),
                "state_version": state.state_version,
            },
        )

        if state.status == "new":
            self.transition(
                state=state,
                target_status="collecting_info",
                actor="system",
                reason="first_user_message_received",
            )

    def mark_ready_for_draft(self, state: SupportCaseState, actor: str) -> None:
        self.transition(
            state=state,
            target_status="ready_for_draft",
            actor=actor,
            reason="minimum_required_information_available",
        )

    def attach_draft(
        self,
        state: SupportCaseState,
        draft_preview: str,
        actor: str,
    ) -> None:
        if state.status != "ready_for_draft":
            raise InvalidStateTransition(
                f"No se puede preparar borrador desde estado {state.status}"
            )

        state.draft = {
            "draft_id": uuid4().hex,
            "preview": draft_preview[:2000],
            "created_utc": utc_now(),
        }

        self.transition(
            state=state,
            target_status="draft_prepared",
            actor=actor,
            reason="draft_attached",
        )

    def close(self, state: SupportCaseState, actor: str, reason: str) -> None:
        if state.status == "closed":
            state.add_event(
                event_type="close_ignored",
                actor=actor,
                payload={
                    "reason": "already_closed",
                },
            )
            return

        self.transition(
            state=state,
            target_status="closed",
            actor=actor,
            reason=reason,
        )

    def reopen(self, state: SupportCaseState, actor: str, reason: str) -> None:
        if state.status != "closed":
            state.add_event(
                event_type="reopen_ignored",
                actor=actor,
                payload={
                    "reason": "case_not_closed",
                    "current_status": state.status,
                },
            )
            return

        self.transition(
            state=state,
            target_status="collecting_info",
            actor=actor,
            reason=reason,
        )