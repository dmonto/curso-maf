from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing_extensions import Never

from agent_framework import WorkflowBuilder, WorkflowContext, executor
from pydantic import BaseModel, Field


class ServiceName(StrEnum):
    VPN = "vpn"
    ERP = "erp"
    EMAIL = "email"
    TEAMS = "teams"
    UNKNOWN = "unknown"


class Priority(StrEnum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"


class OutputAction(StrEnum):
    DRAFT_TICKET = "draft_ticket"
    REQUEST_MORE_DATA = "request_more_data"


class IncidentInput(BaseModel):
    description: str = Field(min_length=5)
    reported_by: str = Field(default="usuario.lab")
    users_affected: int | None = Field(default=None, ge=1)


class NormalizedIncident(BaseModel):
    original_description: str
    normalized_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None


class ClassifiedIncident(BaseModel):
    original_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    priority: Priority
    reason: str


class ValidatedIncident(BaseModel):
    original_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    priority: Priority
    reason: str
    missing_fields: list[str]
    is_ready_for_ticket: bool


class WorkflowOutput(BaseModel):
    action: OutputAction
    title: str
    message: str
    priority: Priority | None = None
    service: ServiceName | None = None
    missing_fields: list[str] = Field(default_factory=list)
    sla_deadline_utc: str | None = None
    ready_for_creation: bool = False


def detect_service(text: str) -> ServiceName:
    if "vpn" in text:
        return ServiceName.VPN
    if "erp" in text or "sap" in text:
        return ServiceName.ERP
    if "correo" in text or "email" in text or "outlook" in text:
        return ServiceName.EMAIL
    if "teams" in text:
        return ServiceName.TEAMS
    return ServiceName.UNKNOWN


def calculate_priority(
    service: ServiceName,
    text: str,
    users_affected: int | None,
) -> tuple[Priority, str]:
    if "error 500" in text or "caído" in text or "caido" in text:
        if users_affected is not None and users_affected >= 5:
            return Priority.P1, "Error severo con impacto en varios usuarios."
        return Priority.P2, "Error severo con impacto no confirmado o limitado."

    if "lento" in text or "intermitente" in text or "degradado" in text:
        return Priority.P2, "Servicio degradado o intermitente."

    if service == ServiceName.UNKNOWN:
        return Priority.P3, "No se ha identificado el servicio afectado."

    return Priority.P3, "Incidencia estándar sin señales de criticidad alta."


def calculate_sla_deadline(priority: Priority) -> str:
    hours_by_priority = {
        Priority.P1: 2,
        Priority.P2: 8,
        Priority.P3: 24,
    }

    deadline = datetime.now(timezone.utc) + timedelta(hours=hours_by_priority[priority])
    return deadline.isoformat(timespec="seconds")


def is_ready_for_ticket(message: ValidatedIncident) -> bool:
    return message.is_ready_for_ticket


def needs_more_data(message: ValidatedIncident) -> bool:
    return not message.is_ready_for_ticket


@executor(id="normalize_incident")
async def normalize_incident(
    message: IncidentInput,
    ctx: WorkflowContext[NormalizedIncident],
) -> None:
    normalized_text = message.description.strip().lower()

    await ctx.send_message(
        NormalizedIncident(
            original_description=message.description,
            normalized_description=normalized_text,
            service=detect_service(normalized_text),
            reported_by=message.reported_by,
            users_affected=message.users_affected,
        )
    )


@executor(id="classify_priority")
async def classify_priority(
    message: NormalizedIncident,
    ctx: WorkflowContext[ClassifiedIncident],
) -> None:
    priority, reason = calculate_priority(
        service=message.service,
        text=message.normalized_description,
        users_affected=message.users_affected,
    )

    await ctx.send_message(
        ClassifiedIncident(
            original_description=message.original_description,
            service=message.service,
            reported_by=message.reported_by,
            users_affected=message.users_affected,
            priority=priority,
            reason=reason,
        )
    )


@executor(id="validate_required_data")
async def validate_required_data(
    message: ClassifiedIncident,
    ctx: WorkflowContext[ValidatedIncident],
) -> None:
    missing_fields: list[str] = []

    if message.service == ServiceName.UNKNOWN:
        missing_fields.append("service")

    if message.users_affected is None:
        missing_fields.append("users_affected")

    await ctx.send_message(
        ValidatedIncident(
            original_description=message.original_description,
            service=message.service,
            reported_by=message.reported_by,
            users_affected=message.users_affected,
            priority=message.priority,
            reason=message.reason,
            missing_fields=missing_fields,
            is_ready_for_ticket=len(missing_fields) == 0,
        )
    )


@executor(id="draft_ticket")
async def draft_ticket(
    message: ValidatedIncident,
    ctx: WorkflowContext[Never, WorkflowOutput],
) -> None:
    service_label = message.service.value.upper()

    await ctx.yield_output(
        WorkflowOutput(
            action=OutputAction.DRAFT_TICKET,
            title=f"[{message.priority.upper()}] Incidencia en {service_label}",
            message=(
                f"Se ha preparado un borrador de ticket para {service_label}. "
                f"Motivo de prioridad: {message.reason}"
            ),
            priority=message.priority,
            service=message.service,
            missing_fields=[],
            sla_deadline_utc=calculate_sla_deadline(message.priority),
            ready_for_creation=True,
        )
    )


@executor(id="request_missing_data")
async def request_missing_data(
    message: ValidatedIncident,
    ctx: WorkflowContext[Never, WorkflowOutput],
) -> None:
    await ctx.yield_output(
        WorkflowOutput(
            action=OutputAction.REQUEST_MORE_DATA,
            title="Faltan datos para continuar",
            message=(
                "No se puede preparar todavía el borrador del ticket. "
                "Completa los campos pendientes antes de continuar."
            ),
            priority=message.priority,
            service=message.service,
            missing_fields=message.missing_fields,
            ready_for_creation=False,
        )
    )


def build_incident_conditional_workflow():
    workflow = (
        WorkflowBuilder(start_executor=normalize_incident)
        .add_edge(normalize_incident, classify_priority)
        .add_edge(classify_priority, validate_required_data)
        .add_edge(
            validate_required_data,
            draft_ticket,
            condition=is_ready_for_ticket,
        )
        .add_edge(
            validate_required_data,
            request_missing_data,
            condition=needs_more_data,
        )
        .build()
    )

    return workflow


async def run_case(name: str, request: IncidentInput) -> None:
    workflow = build_incident_conditional_workflow()

    events = await workflow.run(request)
    outputs = events.get_outputs()

    print(f"\n--- CASO: {name} ---")
    for output in outputs:
        if isinstance(output, BaseModel):
            print(output.model_dump_json(indent=2))
        else:
            print(output)


async def main() -> None:
    await run_case(
        name="Incidencia completa",
        request=IncidentInput(
            description="El ERP devuelve error 500 y afecta a 12 usuarios.",
            reported_by="ana.soporte@contoso.com",
            users_affected=12,
        ),
    )

    await run_case(
        name="Incidencia incompleta",
        request=IncidentInput(
            description="No puedo acceder a una aplicación interna.",
            reported_by="luis.usuario@contoso.com",
            users_affected=None,
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())