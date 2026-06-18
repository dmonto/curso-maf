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


class ValidationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class OutputAction(StrEnum):
    DRAFT_TICKET = "draft_ticket"
    REQUEST_MORE_DATA = "request_more_data"
    MANUAL_REVIEW = "manual_review"


class IncidentInput(BaseModel):
    description: str = Field(min_length=5)
    reported_by: str = Field(default="usuario.lab")
    users_affected: int | None = Field(default=None, ge=1)


class ValidationFinding(BaseModel):
    code: str
    severity: ValidationSeverity
    step: str
    message: str
    field: str | None = None


class NormalizedIncident(BaseModel):
    original_description: str
    normalized_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    findings: list[ValidationFinding] = Field(default_factory=list)


class InputValidatedIncident(BaseModel):
    original_description: str
    normalized_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    findings: list[ValidationFinding]
    can_continue: bool
    needs_more_data: bool


class EnrichedIncident(BaseModel):
    original_description: str
    normalized_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    owner_team: str | None
    business_service: str | None
    is_business_critical: bool
    findings: list[ValidationFinding]


class ContextValidatedIncident(BaseModel):
    original_description: str
    normalized_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    owner_team: str | None
    business_service: str | None
    is_business_critical: bool
    findings: list[ValidationFinding]
    can_continue: bool
    requires_manual_review: bool


class ClassifiedIncident(BaseModel):
    original_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    owner_team: str | None
    business_service: str | None
    priority: Priority
    reason: str
    findings: list[ValidationFinding]


class ActionValidatedIncident(BaseModel):
    original_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    owner_team: str | None
    business_service: str | None
    priority: Priority
    reason: str
    findings: list[ValidationFinding]
    can_draft_ticket: bool
    requires_manual_review: bool
    needs_more_data: bool


class WorkflowOutput(BaseModel):
    action: OutputAction
    title: str
    message: str
    service: ServiceName | None = None
    priority: Priority | None = None
    owner_team: str | None = None
    business_service: str | None = None
    findings: list[ValidationFinding] = Field(default_factory=list)
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


def lookup_service_context(service: ServiceName) -> tuple[str | None, str | None, bool]:
    service_catalog = {
        ServiceName.VPN: ("networking", "remote_access", False),
        ServiceName.ERP: ("business_apps", "core_business_systems", True),
        ServiceName.EMAIL: ("m365", "collaboration", False),
        ServiceName.TEAMS: ("m365", "collaboration", False),
    }

    return service_catalog.get(service, (None, None, False))


def calculate_priority(
    text: str,
    service: ServiceName,
    users_affected: int | None,
    is_business_critical: bool,
) -> tuple[Priority, str]:
    if "error 500" in text or "caído" in text or "caido" in text:
        if is_business_critical and users_affected is not None and users_affected >= 5:
            return Priority.P1, "Error severo en servicio crítico con varios usuarios afectados."
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


def has_blocking_input_error(message: InputValidatedIncident) -> bool:
    return message.needs_more_data


def can_continue_after_input_validation(message: InputValidatedIncident) -> bool:
    return message.can_continue


def requires_manual_review_after_context(message: ContextValidatedIncident) -> bool:
    return message.requires_manual_review


def can_continue_after_context_validation(message: ContextValidatedIncident) -> bool:
    return message.can_continue and not message.requires_manual_review


def needs_more_data_after_action_validation(message: ActionValidatedIncident) -> bool:
    return message.needs_more_data


def requires_manual_review_after_action_validation(message: ActionValidatedIncident) -> bool:
    return message.requires_manual_review


def can_draft_after_action_validation(message: ActionValidatedIncident) -> bool:
    return message.can_draft_ticket


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


@executor(id="validate_input")
async def validate_input(
    message: NormalizedIncident,
    ctx: WorkflowContext[InputValidatedIncident],
) -> None:
    findings = list(message.findings)

    if message.service == ServiceName.UNKNOWN:
        findings.append(
            ValidationFinding(
                code="service_not_identified",
                severity=ValidationSeverity.ERROR,
                step="validate_input",
                field="service",
                message="No se ha identificado el servicio afectado.",
            )
        )

    if message.users_affected is None:
        findings.append(
            ValidationFinding(
                code="users_affected_missing",
                severity=ValidationSeverity.ERROR,
                step="validate_input",
                field="users_affected",
                message="Falta indicar cuántos usuarios están afectados.",
            )
        )

    needs_more_data = any(f.severity == ValidationSeverity.ERROR for f in findings)

    await ctx.send_message(
        InputValidatedIncident(
            original_description=message.original_description,
            normalized_description=message.normalized_description,
            service=message.service,
            reported_by=message.reported_by,
            users_affected=message.users_affected,
            findings=findings,
            can_continue=not needs_more_data,
            needs_more_data=needs_more_data,
        )
    )


@executor(id="enrich_context")
async def enrich_context(
    message: InputValidatedIncident,
    ctx: WorkflowContext[EnrichedIncident],
) -> None:
    owner_team, business_service, is_business_critical = lookup_service_context(message.service)

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
            findings=message.findings,
        )
    )


@executor(id="validate_context")
async def validate_context(
    message: EnrichedIncident,
    ctx: WorkflowContext[ContextValidatedIncident],
) -> None:
    findings = list(message.findings)

    if message.owner_team is None:
        findings.append(
            ValidationFinding(
                code="owner_team_missing",
                severity=ValidationSeverity.CRITICAL,
                step="validate_context",
                field="owner_team",
                message="No se ha encontrado equipo responsable para el servicio.",
            )
        )

    if message.is_business_critical and message.users_affected is not None and message.users_affected >= 10:
        findings.append(
            ValidationFinding(
                code="critical_business_impact",
                severity=ValidationSeverity.WARNING,
                step="validate_context",
                field="users_affected",
                message="El servicio es crítico y hay impacto en 10 o más usuarios.",
            )
        )

    requires_manual_review = any(f.severity == ValidationSeverity.CRITICAL for f in findings)

    await ctx.send_message(
        ContextValidatedIncident(
            original_description=message.original_description,
            normalized_description=message.normalized_description,
            service=message.service,
            reported_by=message.reported_by,
            users_affected=message.users_affected,
            owner_team=message.owner_team,
            business_service=message.business_service,
            is_business_critical=message.is_business_critical,
            findings=findings,
            can_continue=not requires_manual_review,
            requires_manual_review=requires_manual_review,
        )
    )


@executor(id="classify_priority")
async def classify_priority(
    message: ContextValidatedIncident,
    ctx: WorkflowContext[ClassifiedIncident],
) -> None:
    priority, reason = calculate_priority(
        text=message.normalized_description,
        service=message.service,
        users_affected=message.users_affected,
        is_business_critical=message.is_business_critical,
    )

    await ctx.send_message(
        ClassifiedIncident(
            original_description=message.original_description,
            service=message.service,
            reported_by=message.reported_by,
            users_affected=message.users_affected,
            owner_team=message.owner_team,
            business_service=message.business_service,
            priority=priority,
            reason=reason,
            findings=message.findings,
        )
    )


@executor(id="validate_action_readiness")
async def validate_action_readiness(
    message: ClassifiedIncident,
    ctx: WorkflowContext[ActionValidatedIncident],
) -> None:
    findings = list(message.findings)

    needs_more_data = False
    requires_manual_review = False

    if message.priority == Priority.P1:
        requires_manual_review = True
        findings.append(
            ValidationFinding(
                code="p1_requires_review",
                severity=ValidationSeverity.WARNING,
                step="validate_action_readiness",
                field="priority",
                message="Las incidencias P1 requieren revisión antes de cualquier acción real.",
            )
        )

    if message.owner_team is None:
        requires_manual_review = True
        findings.append(
            ValidationFinding(
                code="cannot_route_without_owner",
                severity=ValidationSeverity.CRITICAL,
                step="validate_action_readiness",
                field="owner_team",
                message="No se puede enrutar la incidencia sin equipo responsable.",
            )
        )

    if message.users_affected is None:
        needs_more_data = True
        findings.append(
            ValidationFinding(
                code="cannot_draft_without_impact",
                severity=ValidationSeverity.ERROR,
                step="validate_action_readiness",
                field="users_affected",
                message="No se puede preparar un borrador operativo sin impacto definido.",
            )
        )

    can_draft_ticket = not needs_more_data and not requires_manual_review

    await ctx.send_message(
        ActionValidatedIncident(
            original_description=message.original_description,
            service=message.service,
            reported_by=message.reported_by,
            users_affected=message.users_affected,
            owner_team=message.owner_team,
            business_service=message.business_service,
            priority=message.priority,
            reason=message.reason,
            findings=findings,
            can_draft_ticket=can_draft_ticket,
            requires_manual_review=requires_manual_review,
            needs_more_data=needs_more_data,
        )
    )


@executor(id="draft_ticket")
async def draft_ticket(
    message: ActionValidatedIncident,
    ctx: WorkflowContext[Never, WorkflowOutput],
) -> None:
    await ctx.yield_output(
        WorkflowOutput(
            action=OutputAction.DRAFT_TICKET,
            title=f"[{message.priority.upper()}] Incidencia en {message.service.value.upper()}",
            message=(
                "Se ha preparado un borrador de ticket porque las validaciones "
                "intermedias permiten continuar sin revisión adicional."
            ),
            service=message.service,
            priority=message.priority,
            owner_team=message.owner_team,
            business_service=message.business_service,
            findings=message.findings,
            sla_deadline_utc=calculate_sla_deadline(message.priority),
            ready_for_creation=False,
        )
    )


@executor(id="request_missing_data")
async def request_missing_data(
    message: InputValidatedIncident | ActionValidatedIncident,
    ctx: WorkflowContext[Never, WorkflowOutput],
) -> None:
    missing_fields = sorted(
        {
            finding.field
            for finding in message.findings
            if finding.field is not None and finding.severity == ValidationSeverity.ERROR
        }
    )

    await ctx.yield_output(
        WorkflowOutput(
            action=OutputAction.REQUEST_MORE_DATA,
            title="Faltan datos para continuar",
            message="El workflow se ha detenido en una validación intermedia.",
            service=message.service,
            findings=message.findings,
            missing_fields=missing_fields,
            ready_for_creation=False,
        )
    )


@executor(id="manual_review")
async def manual_review(
    message: ContextValidatedIncident | ActionValidatedIncident,
    ctx: WorkflowContext[Never, WorkflowOutput],
) -> None:
    await ctx.yield_output(
        WorkflowOutput(
            action=OutputAction.MANUAL_REVIEW,
            title="Revisión manual requerida",
            message=(
                "El workflow ha detectado condiciones que no deben avanzar "
                "automáticamente. Revisa los findings antes de continuar."
            ),
            service=message.service,
            priority=getattr(message, "priority", None),
            owner_team=message.owner_team,
            business_service=message.business_service,
            findings=message.findings,
            ready_for_creation=False,
        )
    )


def build_incident_validation_workflow():
    workflow = (
        WorkflowBuilder(start_executor=normalize_incident)
        .add_edge(normalize_incident, validate_input)
        .add_edge(
            validate_input,
            request_missing_data,
            condition=has_blocking_input_error,
        )
        .add_edge(
            validate_input,
            enrich_context,
            condition=can_continue_after_input_validation,
        )
        .add_edge(enrich_context, validate_context)
        .add_edge(
            validate_context,
            manual_review,
            condition=requires_manual_review_after_context,
        )
        .add_edge(
            validate_context,
            classify_priority,
            condition=can_continue_after_context_validation,
        )
        .add_edge(classify_priority, validate_action_readiness)
        .add_edge(
            validate_action_readiness,
            request_missing_data,
            condition=needs_more_data_after_action_validation,
        )
        .add_edge(
            validate_action_readiness,
            manual_review,
            condition=requires_manual_review_after_action_validation,
        )
        .add_edge(
            validate_action_readiness,
            draft_ticket,
            condition=can_draft_after_action_validation,
        )
        .build()
    )

    return workflow


async def run_case(name: str, request: IncidentInput) -> None:
    workflow = build_incident_validation_workflow()

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
        name="Incidencia estándar completa",
        request=IncidentInput(
            description="La VPN está lenta y afecta a 2 usuarios.",
            reported_by="lab1@contoso.com",
            users_affected=2,
        ),
    )

    await run_case(
        name="Servicio desconocido",
        request=IncidentInput(
            description="No puedo acceder a una aplicación interna.",
            reported_by="lab2@contoso.com",
            users_affected=1,
        ),
    )

    await run_case(
        name="Falta impacto",
        request=IncidentInput(
            description="El ERP devuelve error 500.",
            reported_by="lab3@contoso.com",
            users_affected=None,
        ),
    )

    await run_case(
        name="P1 requiere revisión",
        request=IncidentInput(
            description="El ERP devuelve error 500 y afecta a 12 usuarios.",
            reported_by="lab4@contoso.com",
            users_affected=12,
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())