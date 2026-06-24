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
    DEGRADED_DRAFT = "degraded_draft"
    SAFE_FAILURE = "safe_failure"


class ErrorKind(StrEnum):
    NONE = "none"
    VALIDATION = "validation"
    TRANSIENT_EXTERNAL = "transient_external"
    AUTHORIZATION = "authorization"
    POLICY = "policy"
    UNEXPECTED = "unexpected"


class IncidentInput(BaseModel):
    description: str = Field(min_length=5)
    reported_by: str = Field(default="usuario.lab")
    users_affected: int | None = Field(default=None, ge=1)


class StepError(BaseModel):
    kind: ErrorKind
    code: str
    step: str
    user_message: str
    retryable: bool = False
    technical_detail: str | None = None


class NormalizedIncident(BaseModel):
    original_description: str
    normalized_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None


class EnrichedIncident(BaseModel):
    original_description: str
    normalized_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    external_status: str | None = None
    degraded: bool = False
    error: StepError | None = None


class ClassifiedIncident(BaseModel):
    original_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    external_status: str | None
    degraded: bool
    priority: Priority
    reason: str
    error: StepError | None = None


class ValidatedIncident(BaseModel):
    original_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None
    external_status: str | None
    degraded: bool
    priority: Priority
    reason: str
    missing_fields: list[str]
    is_ready_for_ticket: bool
    error: StepError | None = None


class WorkflowOutput(BaseModel):
    action: OutputAction
    title: str
    message: str
    priority: Priority | None = None
    service: ServiceName | None = None
    missing_fields: list[str] = Field(default_factory=list)
    errors: list[StepError] = Field(default_factory=list)
    sla_deadline_utc: str | None = None
    ready_for_creation: bool = False


class ExternalTimeoutError(Exception):
    pass


class ExternalAuthorizationError(Exception):
    pass


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


def simulate_external_status_lookup(service: ServiceName, text: str) -> str:
    """
    Simula una consulta a un sistema externo.

    Reglas de laboratorio:
    - Si el texto contiene 'timeout', simulamos caída temporal.
    - Si el texto contiene '403', simulamos falta de permisos.
    - En otro caso, devolvemos un estado operativo simulado.
    """
    if "timeout" in text:
        raise ExternalTimeoutError("El sistema externo no respondió dentro del tiempo límite.")

    if "403" in text:
        raise ExternalAuthorizationError("El usuario no tiene permisos para consultar el sistema externo.")

    status_by_service = {
        ServiceName.VPN: "degraded",
        ServiceName.ERP: "major_outage",
        ServiceName.EMAIL: "operational",
        ServiceName.TEAMS: "operational",
        ServiceName.UNKNOWN: "unknown",
    }

    return status_by_service[service]


def calculate_priority(
    service: ServiceName,
    text: str,
    users_affected: int | None,
    external_status: str | None,
    degraded: bool,
) -> tuple[Priority, str]:
    if external_status == "major_outage":
        return Priority.P1, "El sistema externo indica caída mayor del servicio."

    if "error 500" in text or "caído" in text or "caido" in text:
        if users_affected is not None and users_affected >= 5:
            return Priority.P1, "Error severo con impacto en varios usuarios."
        return Priority.P2, "Error severo con impacto no confirmado o limitado."

    if external_status == "degraded":
        return Priority.P2, "El sistema externo indica servicio degradado."

    if degraded:
        return Priority.P2, "No se pudo consultar el estado externo; se mantiene prioridad conservadora."

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


def has_authorization_error(message: EnrichedIncident) -> bool:
    return message.error is not None and message.error.kind == ErrorKind.AUTHORIZATION


def can_continue_after_enrichment(message: EnrichedIncident) -> bool:
    return not has_authorization_error(message)


def needs_more_data(message: ValidatedIncident) -> bool:
    return not message.is_ready_for_ticket


def can_draft_ticket(message: ValidatedIncident) -> bool:
    return message.is_ready_for_ticket and not message.degraded


def can_draft_degraded(message: ValidatedIncident) -> bool:
    return message.is_ready_for_ticket and message.degraded


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


@executor(id="enrich_with_external_status")
async def enrich_with_external_status(
    message: NormalizedIncident,
    ctx: WorkflowContext[EnrichedIncident],
) -> None:
    try:
        external_status = simulate_external_status_lookup(
            service=message.service,
            text=message.normalized_description,
        )

        await ctx.send_message(
            EnrichedIncident(
                original_description=message.original_description,
                normalized_description=message.normalized_description,
                service=message.service,
                reported_by=message.reported_by,
                users_affected=message.users_affected,
                external_status=external_status,
                degraded=False,
                error=None,
            )
        )

    except ExternalTimeoutError as exc:
        await ctx.send_message(
            EnrichedIncident(
                original_description=message.original_description,
                normalized_description=message.normalized_description,
                service=message.service,
                reported_by=message.reported_by,
                users_affected=message.users_affected,
                external_status=None,
                degraded=True,
                error=StepError(
                    kind=ErrorKind.TRANSIENT_EXTERNAL,
                    code="external_status_timeout",
                    step="enrich_with_external_status",
                    user_message=(
                        "No se pudo consultar el estado externo del servicio. "
                        "El flujo continuará con información parcial."
                    ),
                    retryable=True,
                    technical_detail=str(exc),
                ),
            )
        )

    except ExternalAuthorizationError as exc:
        await ctx.send_message(
            EnrichedIncident(
                original_description=message.original_description,
                normalized_description=message.normalized_description,
                service=message.service,
                reported_by=message.reported_by,
                users_affected=message.users_affected,
                external_status=None,
                degraded=False,
                error=StepError(
                    kind=ErrorKind.AUTHORIZATION,
                    code="external_status_forbidden",
                    step="enrich_with_external_status",
                    user_message=(
                        "No hay permisos para consultar el sistema externo. "
                        "No se continuará con una acción automática."
                    ),
                    retryable=False,
                    technical_detail=str(exc),
                ),
            )
        )


@executor(id="classify_priority")
async def classify_priority(
    message: EnrichedIncident,
    ctx: WorkflowContext[ClassifiedIncident],
) -> None:
    priority, reason = calculate_priority(
        service=message.service,
        text=message.normalized_description,
        users_affected=message.users_affected,
        external_status=message.external_status,
        degraded=message.degraded,
    )

    await ctx.send_message(
        ClassifiedIncident(
            original_description=message.original_description,
            service=message.service,
            reported_by=message.reported_by,
            users_affected=message.users_affected,
            external_status=message.external_status,
            degraded=message.degraded,
            priority=priority,
            reason=reason,
            error=message.error,
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
            external_status=message.external_status,
            degraded=message.degraded,
            priority=message.priority,
            reason=message.reason,
            missing_fields=missing_fields,
            is_ready_for_ticket=len(missing_fields) == 0,
            error=message.error,
        )
    )


@executor(id="draft_ticket")
async def draft_ticket(
    message: ValidatedIncident,
    ctx: WorkflowContext[Never, WorkflowOutput],
) -> None:
    await ctx.yield_output(
        WorkflowOutput(
            action=OutputAction.DRAFT_TICKET,
            title=f"[{message.priority.upper()}] Incidencia en {message.service.value.upper()}",
            message=(
                "Se ha preparado un borrador de ticket con información completa. "
                f"Motivo de prioridad: {message.reason}"
            ),
            priority=message.priority,
            service=message.service,
            sla_deadline_utc=calculate_sla_deadline(message.priority),
            ready_for_creation=True,
        )
    )


@executor(id="draft_degraded_ticket")
async def draft_degraded_ticket(
    message: ValidatedIncident,
    ctx: WorkflowContext[Never, WorkflowOutput],
) -> None:
    errors = [message.error] if message.error else []

    await ctx.yield_output(
        WorkflowOutput(
            action=OutputAction.DEGRADED_DRAFT,
            title=f"[{message.priority.upper()}] Borrador degradado en {message.service.value.upper()}",
            message=(
                "Se ha preparado un borrador con información parcial. "
                "No debe convertirse en ticket real sin revisión, porque falló una consulta externa."
            ),
            priority=message.priority,
            service=message.service,
            errors=errors,
            sla_deadline_utc=calculate_sla_deadline(message.priority),
            ready_for_creation=False,
        )
    )


@executor(id="request_missing_data")
async def request_missing_data(
    message: ValidatedIncident,
    ctx: WorkflowContext[Never, WorkflowOutput],
) -> None:
    errors = [message.error] if message.error else []

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
            errors=errors,
            ready_for_creation=False,
        )
    )


@executor(id="safe_failure")
async def safe_failure(
    message: EnrichedIncident,
    ctx: WorkflowContext[Never, WorkflowOutput],
) -> None:
    errors = [message.error] if message.error else []

    await ctx.yield_output(
        WorkflowOutput(
            action=OutputAction.SAFE_FAILURE,
            title="Ejecución detenida de forma segura",
            message=(
                "El workflow se ha detenido porque falta autorización para consultar "
                "un sistema necesario. No se ha creado ni preparado ninguna acción automática."
            ),
            service=message.service,
            errors=errors,
            ready_for_creation=False,
        )
    )


def build_incident_error_workflow():
    workflow = (
        WorkflowBuilder(start_executor=normalize_incident)
        .add_edge(normalize_incident, enrich_with_external_status)
        .add_edge(
            enrich_with_external_status,
            safe_failure,
            condition=has_authorization_error,
        )
        .add_edge(
            enrich_with_external_status,
            classify_priority,
            condition=can_continue_after_enrichment,
        )
        .add_edge(classify_priority, validate_required_data)
        .add_edge(
            validate_required_data,
            request_missing_data,
            condition=needs_more_data,
        )
        .add_edge(
            validate_required_data,
            draft_ticket,
            condition=can_draft_ticket,
        )
        .add_edge(
            validate_required_data,
            draft_degraded_ticket,
            condition=can_draft_degraded,
        )
        .build()
    )

    return workflow


async def run_case(name: str, request: IncidentInput) -> None:
    workflow = build_incident_error_workflow()

    print(f"\n--- CASO: {name} ---")

    try:
        events = await workflow.run(request)
        outputs = events.get_outputs()

        for output in outputs:
            if isinstance(output, BaseModel):
                print(output.model_dump_json(indent=2))
            else:
                print(output)

    except Exception as exc:
        # Capa final de seguridad ante errores no controlados.
        # En producción aquí registraríamos run_id, stack trace y contexto técnico.
        safe_output = WorkflowOutput(
            action=OutputAction.SAFE_FAILURE,
            title="Error inesperado",
            message=(
                "El workflow ha fallado de forma inesperada. "
                "No se ha ejecutado ninguna acción real."
            ),
            errors=[
                StepError(
                    kind=ErrorKind.UNEXPECTED,
                    code="unexpected_workflow_error",
                    step="workflow.run",
                    user_message="Se produjo un error inesperado durante la ejecución.",
                    retryable=False,
                    technical_detail=str(exc),
                )
            ],
            ready_for_creation=False,
        )

        print(safe_output.model_dump_json(indent=2))


async def main() -> None:
    await run_case(
        name="Consulta externa correcta",
        request=IncidentInput(
            description="El ERP devuelve error 500 y afecta a 12 usuarios.",
            reported_by="ana.soporte@contoso.com",
            users_affected=12,
        ),
    )

    await run_case(
        name="Timeout externo recuperable",
        request=IncidentInput(
            description="La VPN está lenta timeout y afecta a 2 usuarios.",
            reported_by="luis.usuario@contoso.com",
            users_affected=2,
        ),
    )

    await run_case(
        name="Error de autorización no recuperable",
        request=IncidentInput(
            description="El ERP devuelve 403 al consultar estado externo.",
            reported_by="marta.operaciones@contoso.com",
            users_affected=5,
        ),
    )

    await run_case(
        name="Faltan datos obligatorios",
        request=IncidentInput(
            description="No puedo acceder a una aplicación interna.",
            reported_by="carlos.usuario@contoso.com",
            users_affected=None,
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())