from __future__ import annotations

import asyncio
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from time import perf_counter
from uuid import uuid4

from agent_framework import WorkflowBuilder, WorkflowContext, executor
from agent_framework.observability import enable_instrumentation
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from pydantic import BaseModel, Field
from typing_extensions import Never


WORKFLOW_NAME = "incident_observability_workflow"

logger = logging.getLogger("maf.workflow.observability")
tracer = trace.get_tracer("maf.workflow.observability")


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
    reported_by: str = Field(default="usuario.lab@contoso.com")
    users_affected: int | None = Field(default=None, ge=1)


class Finding(BaseModel):
    code: str
    severity: FindingSeverity
    step: str
    message: str
    field: str | None = None


class ObservableMessage(BaseModel):
    run_id: str
    original_description: str
    normalized_description: str | None = None
    reported_by: str
    users_affected: int | None
    service: ServiceName = ServiceName.UNKNOWN
    owner_team: str | None = None
    business_service: str | None = None
    priority: Priority | None = None
    priority_reason: str | None = None
    readiness: Readiness | None = None
    findings: list[Finding] = Field(default_factory=list)


class WorkflowOutput(BaseModel):
    run_id: str
    workflow_name: str
    title: str
    summary: str
    service: ServiceName
    priority: Priority | None
    readiness: Readiness
    owner_team: str | None
    business_service: str | None
    findings: list[Finding]
    elapsed_ms_by_step: dict[str, int]
    suggested_next_step: str
    sla_deadline_utc: str | None
    ready_for_real_action: bool = False


STEP_DURATIONS: dict[str, dict[str, int]] = {}


def configure_observability() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": "maf-course-workflows",
                "workflow.name": WORKFLOW_NAME,
            }
        )
    )

    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)

    # Activa la instrumentación propia de Agent Framework.
    # En laboratorio mantenemos datos sensibles desactivados.
    enable_instrumentation(enable_sensitive_data=False)


def log_event(event: str, **fields: object) -> None:
    payload = {
        "event": event,
        "ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **fields,
    }
    logger.info(json.dumps(payload, ensure_ascii=False))


@contextmanager
def observe_step(step: str, run_id: str, **attributes: object):
    start = perf_counter()

    with tracer.start_as_current_span(f"workflow.step.{step}") as span:
        span.set_attribute("workflow.name", WORKFLOW_NAME)
        span.set_attribute("workflow.run_id", run_id)
        span.set_attribute("workflow.step", step)

        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(str(key), str(value))

        log_event(
            "executor_started",
            run_id=run_id,
            workflow=WORKFLOW_NAME,
            executor=step,
            **attributes,
        )

        try:
            yield span

            elapsed_ms = int((perf_counter() - start) * 1000)
            STEP_DURATIONS.setdefault(run_id, {})[step] = elapsed_ms

            span.set_attribute("workflow.elapsed_ms", elapsed_ms)

            log_event(
                "executor_finished",
                run_id=run_id,
                workflow=WORKFLOW_NAME,
                executor=step,
                elapsed_ms=elapsed_ms,
                **attributes,
            )

        except Exception as exc:
            elapsed_ms = int((perf_counter() - start) * 1000)
            STEP_DURATIONS.setdefault(run_id, {})[step] = elapsed_ms

            span.record_exception(exc)
            span.set_attribute("workflow.elapsed_ms", elapsed_ms)
            span.set_attribute("workflow.error", True)
            span.set_attribute("workflow.error_type", type(exc).__name__)

            log_event(
                "executor_failed",
                run_id=run_id,
                workflow=WORKFLOW_NAME,
                executor=step,
                elapsed_ms=elapsed_ms,
                error_type=type(exc).__name__,
                error_message=str(exc),
                **attributes,
            )

            raise


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


def lookup_service_context(service: ServiceName) -> tuple[str | None, str | None]:
    catalog = {
        ServiceName.VPN: ("networking", "remote_access"),
        ServiceName.ERP: ("business_apps", "core_business_systems"),
        ServiceName.EMAIL: ("m365", "collaboration"),
        ServiceName.TEAMS: ("m365", "collaboration"),
    }

    return catalog.get(service, (None, None))


def classify_priority_rule(
    text: str,
    service: ServiceName,
    users_affected: int | None,
) -> tuple[Priority, str]:
    if "error 500" in text or "caído" in text or "caido" in text:
        if service == ServiceName.ERP and users_affected is not None and users_affected >= 5:
            return Priority.P1, "Error severo en ERP con varios usuarios afectados."
        return Priority.P2, "Error severo con impacto limitado o no confirmado."

    if "lento" in text or "intermitente" in text or "degradado" in text:
        return Priority.P2, "Servicio degradado o intermitente."

    if service == ServiceName.UNKNOWN:
        return Priority.P3, "No se ha identificado el servicio afectado."

    return Priority.P3, "Incidencia estándar sin señales claras de criticidad alta."


def calculate_sla_deadline(priority: Priority | None) -> str | None:
    if priority is None:
        return None

    hours = {
        Priority.P1: 2,
        Priority.P2: 8,
        Priority.P3: 24,
    }[priority]

    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat(timespec="seconds")


@executor(id="create_observable_context")
async def create_observable_context(
    message: IncidentInput,
    ctx: WorkflowContext[ObservableMessage],
) -> None:
    run_id = f"run-{uuid4()}"

    with observe_step(
        step="create_observable_context",
        run_id=run_id,
        reported_by=message.reported_by,
    ):
        await ctx.send_message(
            ObservableMessage(
                run_id=run_id,
                original_description=message.description,
                reported_by=message.reported_by,
                users_affected=message.users_affected,
            )
        )


@executor(id="normalize_incident")
async def normalize_incident(
    message: ObservableMessage,
    ctx: WorkflowContext[ObservableMessage],
) -> None:
    with observe_step(
        step="normalize_incident",
        run_id=message.run_id,
        users_affected=message.users_affected,
    ):
        normalized = message.original_description.strip().lower()
        service = detect_service(normalized)

        findings = list(message.findings)

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

        message.normalized_description = normalized
        message.service = service
        message.findings = findings

        log_event(
            "service_detected",
            run_id=message.run_id,
            workflow=WORKFLOW_NAME,
            service=service,
            findings_count=len(findings),
        )

        await ctx.send_message(message)


@executor(id="enrich_context")
async def enrich_context(
    message: ObservableMessage,
    ctx: WorkflowContext[ObservableMessage],
) -> None:
    with observe_step(
        step="enrich_context",
        run_id=message.run_id,
        service=message.service,
    ):
        owner_team, business_service = lookup_service_context(message.service)

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

        message.owner_team = owner_team
        message.business_service = business_service
        message.findings = findings

        log_event(
            "context_enriched",
            run_id=message.run_id,
            workflow=WORKFLOW_NAME,
            service=message.service,
            owner_team=owner_team,
            business_service=business_service,
        )

        await ctx.send_message(message)


@executor(id="classify_priority")
async def classify_priority(
    message: ObservableMessage,
    ctx: WorkflowContext[ObservableMessage],
) -> None:
    with observe_step(
        step="classify_priority",
        run_id=message.run_id,
        service=message.service,
        owner_team=message.owner_team,
    ):
        priority, reason = classify_priority_rule(
            text=message.normalized_description or "",
            service=message.service,
            users_affected=message.users_affected,
        )

        message.priority = priority
        message.priority_reason = reason

        if priority == Priority.P1:
            message.findings.append(
                Finding(
                    code="p1_requires_review",
                    severity=FindingSeverity.WARNING,
                    step="classify_priority",
                    field="priority",
                    message="Las incidencias P1 requieren revisión humana antes de acción real.",
                )
            )

        log_event(
            "priority_classified",
            run_id=message.run_id,
            workflow=WORKFLOW_NAME,
            service=message.service,
            priority=priority,
            reason=reason,
        )

        await ctx.send_message(message)


@executor(id="validate_readiness")
async def validate_readiness(
    message: ObservableMessage,
    ctx: WorkflowContext[ObservableMessage],
) -> None:
    with observe_step(
        step="validate_readiness",
        run_id=message.run_id,
        service=message.service,
        priority=message.priority,
    ):
        if message.users_affected is None:
            message.findings.append(
                Finding(
                    code="users_affected_missing",
                    severity=FindingSeverity.ERROR,
                    step="validate_readiness",
                    field="users_affected",
                    message="Falta indicar cuántos usuarios están afectados.",
                )
            )

        has_errors = any(f.severity == FindingSeverity.ERROR for f in message.findings)

        if has_errors:
            readiness = Readiness.NEEDS_MORE_DATA
        elif message.priority == Priority.P1:
            readiness = Readiness.NEEDS_REVIEW
        else:
            readiness = Readiness.READY

        message.readiness = readiness

        log_event(
            "readiness_validated",
            run_id=message.run_id,
            workflow=WORKFLOW_NAME,
            readiness=readiness,
            findings_count=len(message.findings),
        )

        await ctx.send_message(message)


@executor(id="compose_output")
async def compose_output(
    message: ObservableMessage,
    ctx: WorkflowContext[Never, WorkflowOutput],
) -> None:
    with observe_step(
        step="compose_output",
        run_id=message.run_id,
        service=message.service,
        priority=message.priority,
        readiness=message.readiness,
    ):
        if message.readiness == Readiness.READY:
            suggested_next_step = "Preparar borrador de ticket y revisar antes de integración real."
        elif message.readiness == Readiness.NEEDS_REVIEW:
            suggested_next_step = "Enviar a revisión humana antes de cualquier acción real."
        else:
            suggested_next_step = "Solicitar los datos pendientes antes de continuar."

        output = WorkflowOutput(
            run_id=message.run_id,
            workflow_name=WORKFLOW_NAME,
            title=f"Resultado observable para incidencia {message.service.value}",
            summary=(
                f"Servicio={message.service.value}; "
                f"Prioridad={message.priority}; "
                f"Readiness={message.readiness}; "
                f"Findings={len(message.findings)}"
            ),
            service=message.service,
            priority=message.priority,
            readiness=message.readiness or Readiness.NEEDS_MORE_DATA,
            owner_team=message.owner_team,
            business_service=message.business_service,
            findings=message.findings,
            elapsed_ms_by_step=STEP_DURATIONS.get(message.run_id, {}),
            suggested_next_step=suggested_next_step,
            sla_deadline_utc=calculate_sla_deadline(message.priority),
            ready_for_real_action=False,
        )

        log_event(
            "workflow_output_created",
            run_id=message.run_id,
            workflow=WORKFLOW_NAME,
            readiness=output.readiness,
            findings_count=len(output.findings),
            elapsed_ms_by_step=output.elapsed_ms_by_step,
        )

        await ctx.yield_output(output)


def build_incident_observability_workflow():
    workflow = (
        WorkflowBuilder(
            name=WORKFLOW_NAME,
            start_executor=create_observable_context,
        )
        .add_edge(create_observable_context, normalize_incident)
        .add_edge(normalize_incident, enrich_context)
        .add_edge(enrich_context, classify_priority)
        .add_edge(classify_priority, validate_readiness)
        .add_edge(validate_readiness, compose_output)
        .build()
    )

    return workflow


async def run_case(name: str, request: IncidentInput) -> None:
    workflow = build_incident_observability_workflow()

    start = perf_counter()

    log_event(
        "workflow_case_started",
        workflow=WORKFLOW_NAME,
        case=name,
    )

    events = await workflow.run(request)
    outputs = events.get_outputs()

    elapsed_ms = int((perf_counter() - start) * 1000)

    print(f"\n--- CASO: {name} ---")
    print(f"Tiempo total observado: {elapsed_ms} ms")

    for output in outputs:
        if isinstance(output, BaseModel):
            print(output.model_dump_json(indent=2))
        else:
            print(output)

    log_event(
        "workflow_case_finished",
        workflow=WORKFLOW_NAME,
        case=name,
        elapsed_ms=elapsed_ms,
    )


async def main() -> None:
    configure_observability()

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
        name="Datos incompletos",
        request=IncidentInput(
            description="No puedo acceder a una aplicación interna.",
            reported_by="lab3@contoso.com",
            users_affected=None,
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())