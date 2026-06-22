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


class Readiness(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    NEEDS_MORE_DATA = "needs_more_data"


class FindingSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class IncidentInput(BaseModel):
    description: str = Field(min_length=5)
    reported_by: str = Field(default="usuario.lab")
    users_affected: int | None = Field(default=None, ge=1)


class Finding(BaseModel):
    code: str
    severity: FindingSeverity
    step: str
    message: str
    field: str | None = None


class NormalizedIncident(BaseModel):
    original_description: str
    normalized_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    findings: list[Finding] = Field(default_factory=list)


class EnrichedIncident(BaseModel):
    original_description: str
    normalized_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    owner_team: str | None
    business_service: str | None
    is_business_critical: bool
    findings: list[Finding]


class ClassifiedIncident(BaseModel):
    original_description: str
    normalized_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    owner_team: str | None
    business_service: str | None
    is_business_critical: bool
    priority: Priority
    priority_reason: str
    findings: list[Finding]


class ValidatedIncident(BaseModel):
    original_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    owner_team: str | None
    business_service: str | None
    priority: Priority
    priority_reason: str
    readiness: Readiness
    findings: list[Finding]


class WorkflowOutput(BaseModel):
    title: str
    summary: str
    service: ServiceName
    priority: Priority
    readiness: Readiness
    owner_team: str | None
    business_service: str | None
    findings: list[Finding]
    suggested_next_step: str
    sla_deadline_utc: str | None
    ready_for_real_action: bool


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


def lookup_service_context(service: ServiceName) -> tuple[str | None, str | None, bool]:
    catalog = {
        ServiceName.VPN: ("networking", "remote_access", False),
        ServiceName.ERP: ("business_apps", "core_business_systems", True),
        ServiceName.EMAIL: ("m365", "collaboration", False),
        ServiceName.TEAMS: ("m365", "collaboration", False),
    }

    return catalog.get(service, (None, None, False))


def classify_priority_rule(
    text: str,
    service: ServiceName,
    users_affected: int | None,
    is_business_critical: bool,
) -> tuple[Priority, str]:
    if "error 500" in text or "caído" in text or "caido" in text:
        if is_business_critical and users_affected is not None and users_affected >= 5:
            return Priority.P1, "Servicio crítico con error severo y varios usuarios afectados."
        return Priority.P2, "Error severo con impacto limitado o no completamente confirmado."

    if "lento" in text or "intermitente" in text or "degradado" in text:
        return Priority.P2, "Servicio degradado o intermitente."

    if service == ServiceName.UNKNOWN:
        return Priority.P3, "No se ha identificado el servicio afectado."

    return Priority.P3, "Incidencia estándar sin señales claras de criticidad alta."


def calculate_sla_deadline(priority: Priority) -> str:
    hours = {
        Priority.P1: 2,
        Priority.P2: 8,
        Priority.P3: 24,
    }[priority]

    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat(timespec="seconds")


@executor(id="normalize_incident")
async def normalize_incident(
    message: IncidentInput,
    ctx: WorkflowContext[NormalizedIncident],
) -> None:
    normalized_text = message.description.strip().lower()
    service = detect_service(normalized_text)

    findings: list[Finding] = []

    if service == ServiceName.UNKNOWN:
        findings.append(
            Finding(
                code="service_not_detected",
                severity=FindingSeverity.ERROR,
                step="normalize_incident",
                field="service",
                message="No se ha podido identificar el servicio afectado.",
            )
        )

    await ctx.send_message(
        NormalizedIncident(
            original_description=message.description,
            normalized_description=normalized_text,
            service=service,
            reported_by=message.reported_by,
            users_affected=message.users_affected,
            findings=findings,
        )
    )


@executor(id="enrich_context")
async def enrich_context(
    message: NormalizedIncident,
    ctx: WorkflowContext[EnrichedIncident],
) -> None:
    owner_team, business_service, is_business_critical = lookup_service_context(message.service)
    findings = list(message.findings)

    if owner_team is None:
        findings.append(
            Finding(
                code="owner_team_not_found",
                severity=FindingSeverity.ERROR,
                step="enrich_context",
                field="owner_team",
                message="No se ha encontrado equipo responsable para el servicio.",
            )
        )

    await ctx.send_message(
        EnrichedIncident(
            original_description=message.original_description,
            normalized_description=message.normalized_description,
            service=message.service,
            reported_by=message.reported_by,
            users_affected=message.users_affected,
            owner_team=owner_team,
            business_service=business_service,
            is_business_critical=is_business_critical,
            findings=findings,
        )
    )


@executor(id="classify_priority")
async def classify_priority(
    message: EnrichedIncident,
    ctx: WorkflowContext[ClassifiedIncident],
) -> None:
    priority, reason = classify_priority_rule(
        text=message.normalized_description,
        service=message.service,
        users_affected=message.users_affected,
        is_business_critical=message.is_business_critical,
    )

    findings = list(message.findings)

    if priority == Priority.P1:
        findings.append(
            Finding(
                code="p1_requires_human_review",
                severity=FindingSeverity.WARNING,
                step="classify_priority",
                field="priority",
                message="Las incidencias P1 requieren revisión antes de cualquier acción real.",
            )
        )

    await ctx.send_message(
        ClassifiedIncident(
            original_description=message.original_description,
            normalized_description=message.normalized_description,
            service=message.service,
            reported_by=message.reported_by,
            users_affected=message.users_affected,
            owner_team=message.owner_team,
            business_service=message.business_service,
            is_business_critical=message.is_business_critical,
            priority=priority,
            priority_reason=reason,
            findings=findings,
        )
    )


@executor(id="validate_readiness")
async def validate_readiness(
    message: ClassifiedIncident,
    ctx: WorkflowContext[ValidatedIncident],
) -> None:
    findings = list(message.findings)

    if message.users_affected is None:
        findings.append(
            Finding(
                code="users_affected_missing",
                severity=FindingSeverity.ERROR,
                step="validate_readiness",
                field="users_affected",
                message="Falta indicar cuántos usuarios están afectados.",
            )
        )

    has_errors = any(f.severity == FindingSeverity.ERROR for f in findings)

    if has_errors:
        readiness = Readiness.NEEDS_MORE_DATA
    elif message.priority == Priority.P1:
        readiness = Readiness.NEEDS_REVIEW
    else:
        readiness = Readiness.READY

    await ctx.send_message(
        ValidatedIncident(
            original_description=message.original_description,
            service=message.service,
            reported_by=message.reported_by,
            users_affected=message.users_affected,
            owner_team=message.owner_team,
            business_service=message.business_service,
            priority=message.priority,
            priority_reason=message.priority_reason,
            readiness=readiness,
            findings=findings,
        )
    )


@executor(id="compose_operator_summary")
async def compose_operator_summary(
    message: ValidatedIncident,
    ctx: WorkflowContext[Never, WorkflowOutput],
) -> None:
    if message.readiness == Readiness.READY:
        suggested_next_step = (
            "Preparar borrador de ticket y revisarlo antes de integrarlo con el sistema ITSM."
        )
        ready_for_real_action = False
    elif message.readiness == Readiness.NEEDS_REVIEW:
        suggested_next_step = (
            "Enviar a revisión humana antes de ejecutar cualquier acción real."
        )
        ready_for_real_action = False
    else:
        suggested_next_step = (
            "Solicitar los datos pendientes antes de continuar el workflow."
        )
        ready_for_real_action = False

    output = WorkflowOutput(
        title=f"[{message.priority.upper()}] Evaluación secuencial de incidencia",
        summary=(
            f"Servicio: {message.service.value}. "
            f"Equipo responsable: {message.owner_team or 'pendiente'}. "
            f"Motivo de prioridad: {message.priority_reason}"
        ),
        service=message.service,
        priority=message.priority,
        readiness=message.readiness,
        owner_team=message.owner_team,
        business_service=message.business_service,
        findings=message.findings,
        suggested_next_step=suggested_next_step,
        sla_deadline_utc=calculate_sla_deadline(message.priority),
        ready_for_real_action=ready_for_real_action,
    )

    await ctx.yield_output(output)


def build_incident_sequential_workflow():
    workflow = (
        WorkflowBuilder(start_executor=normalize_incident)
        .add_chain(
            [
                normalize_incident,
                enrich_context,
                classify_priority,
                validate_readiness,
                compose_operator_summary,
            ]
        )
        .build()
    )

    return workflow

async def run_case(name: str, request: IncidentInput) -> None:
    workflow = build_incident_sequential_workflow()

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
        name="VPN lenta",
        request=IncidentInput(
            description="La VPN está lenta y afecta a 2 usuarios.",
            reported_by="lab1@contoso.com",
            users_affected=2,
        ),
    )

    await run_case(
        name="ERP crítico",
        request=IncidentInput(
            description="El ERP devuelve error 500 y afecta a 12 usuarios.",
            reported_by="lab2@contoso.com",
            users_affected=12,
        ),
    )

    await run_case(
        name="Servicio desconocido",
        request=IncidentInput(
            description="No puedo acceder a una aplicación interna.",
            reported_by="lab3@contoso.com",
            users_affected=1,
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())