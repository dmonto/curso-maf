from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class WorkflowStep(StrEnum):
    START = "start"
    CLASSIFY = "classify"
    LOAD_STATE = "load_state"
    CHECK_MISSING_DATA = "check_missing_data"
    SEARCH_TICKETS = "search_tickets"
    PREPARE_DRAFT = "prepare_draft"
    ASK_CLARIFICATION = "ask_clarification"
    FINAL_RESPONSE = "final_response"
    ERROR = "error"


class IncidentCategory(StrEnum):
    VPN = "vpn"
    ERP = "erp"
    TEAMS = "teams"
    CORREO = "correo"
    GENERAL = "general"


class WorkflowStatus(StrEnum):
    RUNNING = "running"
    NEEDS_USER_INPUT = "needs_user_input"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowEvent:
    step: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class SupportWorkflowState:
    user_id: str
    session_id: str
    user_message: str

    status: str = WorkflowStatus.RUNNING.value
    current_step: str = WorkflowStep.START.value

    category: str | None = None
    service: str | None = None
    operating_system: str | None = None
    affected_users: int | None = None
    steps_tried: list[str] = field(default_factory=list)

    missing_fields: list[str] = field(default_factory=list)
    existing_tickets: list[dict[str, Any]] = field(default_factory=list)
    ticket_draft: dict[str, Any] | None = None

    final_response: str | None = None
    events: list[WorkflowEvent] = field(default_factory=list)

    def add_event(self, step: WorkflowStep, message: str, **data: Any) -> None:
        self.events.append(
            WorkflowEvent(
                step=step.value,
                message=message,
                data=data,
            )
        )
        self.current_step = step.value

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["events"] = [asdict(event) for event in self.events]
        return payload


def classify_incident(message: str) -> IncidentCategory:
    lower = message.lower()

    if "vpn" in lower:
        return IncidentCategory.VPN
    if "erp" in lower:
        return IncidentCategory.ERP
    if "teams" in lower:
        return IncidentCategory.TEAMS
    if "correo" in lower or "email" in lower or "outlook" in lower:
        return IncidentCategory.CORREO

    return IncidentCategory.GENERAL


def extract_basic_state(state: SupportWorkflowState) -> None:
    lower = state.user_message.lower()

    category = classify_incident(state.user_message)
    state.category = category.value

    if category != IncidentCategory.GENERAL:
        state.service = category.value

    if "windows 11" in lower:
        state.operating_system = "Windows 11"
    elif "windows" in lower:
        state.operating_system = "Windows"
    elif "mac" in lower or "macos" in lower:
        state.operating_system = "macOS"

    if "reiniciar" in lower or "reiniciado" in lower:
        state.steps_tried.append("reiniciar cliente")
    if "mfa" in lower:
        state.steps_tried.append("validar MFA")
    if "internet" in lower or "conexión" in lower:
        state.steps_tried.append("comprobar conexión")

    if "varios usuarios" in lower or "muchos usuarios" in lower:
        state.affected_users = 10
    elif "solo yo" in lower or "un usuario" in lower:
        state.affected_users = 1


def compute_missing_fields(state: SupportWorkflowState) -> list[str]:
    missing: list[str] = []

    if not state.service:
        missing.append("service")

    if state.service == IncidentCategory.VPN.value and not state.operating_system:
        missing.append("operating_system")

    if state.affected_users is None:
        missing.append("affected_users")

    return missing


def simulate_search_tickets(service: str) -> list[dict[str, Any]]:
    if service == "vpn":
        return [
            {
                "ticket_id": "INC-1001",
                "service": "vpn",
                "status": "open",
                "summary": "Incidencia intermitente de VPN para usuarios remotos.",
            }
        ]

    return []


def estimate_priority(state: SupportWorkflowState) -> str:
    if state.affected_users is not None and state.affected_users >= 10:
        return "high"

    if state.service in {"erp", "vpn"}:
        return "medium"

    return "low"


def prepare_ticket_draft(state: SupportWorkflowState) -> dict[str, Any]:
    priority = estimate_priority(state)

    return {
        "draft_id": f"DRAFT-{state.service.upper()}-001",
        "service": state.service,
        "title": f"Incidencia de acceso en {state.service}",
        "description": (
            f"Usuario reporta problema en {state.service}. "
            f"Sistema operativo: {state.operating_system}. "
            f"Pasos probados: {', '.join(state.steps_tried) or 'sin datos'}."
        ),
        "priority": priority,
        "confirmation_required": True,
    }


def build_clarification_response(state: SupportWorkflowState) -> str:
    questions: list[str] = []

    if "service" in state.missing_fields:
        questions.append("¿Qué servicio está afectado: VPN, ERP, Teams o correo?")

    if "operating_system" in state.missing_fields:
        questions.append("¿Desde qué sistema operativo estás intentando acceder?")

    if "affected_users" in state.missing_fields:
        questions.append("¿Te ocurre solo a ti o afecta a varios usuarios?")

    return "Necesito un dato más para continuar: " + " ".join(questions)


def build_final_response(state: SupportWorkflowState) -> str:
    lines: list[str] = []

    lines.append(f"He clasificado la incidencia como: {state.category}.")
    lines.append(f"Servicio afectado: {state.service}.")
    lines.append(f"Prioridad estimada: {estimate_priority(state)}.")

    if state.steps_tried:
        lines.append(f"Pasos ya probados: {', '.join(state.steps_tried)}.")

    if state.existing_tickets:
        lines.append("He encontrado tickets relacionados:")
        for ticket in state.existing_tickets:
            lines.append(f"- {ticket['ticket_id']}: {ticket['summary']}")

    if state.ticket_draft:
        lines.append(
            f"He preparado un borrador de ticket: {state.ticket_draft['draft_id']}."
        )
        lines.append("No se ha creado ningún ticket real sin confirmación explícita.")

    return "\n".join(lines)


def run_support_workflow(
    *,
    user_id: str,
    session_id: str,
    user_message: str,
) -> SupportWorkflowState:
    state = SupportWorkflowState(
        user_id=user_id,
        session_id=session_id,
        user_message=user_message,
    )

    try:
        state.add_event(WorkflowStep.START, "Workflow iniciado.")

        state.add_event(WorkflowStep.CLASSIFY, "Clasificando incidencia.")
        extract_basic_state(state)

        state.add_event(
            WorkflowStep.LOAD_STATE,
            "Estado operativo extraído.",
            category=state.category,
            service=state.service,
            operating_system=state.operating_system,
            affected_users=state.affected_users,
            steps_tried=state.steps_tried,
        )

        state.add_event(WorkflowStep.CHECK_MISSING_DATA, "Comprobando datos mínimos.")
        state.missing_fields = compute_missing_fields(state)

        if state.missing_fields:
            state.status = WorkflowStatus.NEEDS_USER_INPUT.value
            state.final_response = build_clarification_response(state)
            state.add_event(
                WorkflowStep.ASK_CLARIFICATION,
                "Faltan datos críticos.",
                missing_fields=state.missing_fields,
            )
            return state

        state.add_event(WorkflowStep.SEARCH_TICKETS, "Buscando tickets existentes.")
        state.existing_tickets = simulate_search_tickets(state.service or "")

        state.add_event(
            WorkflowStep.PREPARE_DRAFT,
            "Preparando borrador de ticket.",
        )
        state.ticket_draft = prepare_ticket_draft(state)

        state.final_response = build_final_response(state)
        state.status = WorkflowStatus.COMPLETED.value
        state.add_event(WorkflowStep.FINAL_RESPONSE, "Workflow completado.")

        return state

    except Exception as exc:
        state.status = WorkflowStatus.FAILED.value
        state.final_response = "No se pudo completar el workflow de soporte."
        state.add_event(
            WorkflowStep.ERROR,
            "Error no controlado en workflow.",
            error=str(exc),
        )
        return state


def workflow_state_to_json(state: SupportWorkflowState) -> str:
    return json.dumps(state.to_dict(), ensure_ascii=False, indent=2)