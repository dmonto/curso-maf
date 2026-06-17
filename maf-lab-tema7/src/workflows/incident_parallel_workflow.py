from __future__ import annotations

import asyncio
from enum import StrEnum
from time import perf_counter
from typing_extensions import Never

from agent_framework import WorkflowBuilder, WorkflowContext, executor
from pydantic import BaseModel, Field


class ServiceName(StrEnum):
    VPN = "vpn"
    ERP = "erp"
    EMAIL = "email"
    TEAMS = "teams"
    UNKNOWN = "unknown"


class AssessmentSource(StrEnum):
    SERVICE_IMPACT = "service_impact"
    SECURITY_RISK = "security_risk"
    BUSINESS_PRIORITY = "business_priority"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendedAction(StrEnum):
    REQUEST_MORE_DATA = "request_more_data"
    CREATE_DRAFT = "create_draft"
    ESCALATE_TO_ON_CALL = "escalate_to_on_call"
    MANUAL_REVIEW = "manual_review"


class IncidentInput(BaseModel):
    description: str = Field(min_length=5)
    reported_by: str = Field(default="usuario.lab")
    users_affected: int | None = Field(default=None, ge=1)


class ParallelContext(BaseModel):
    original_description: str
    normalized_description: str
    service: ServiceName
    reported_by: str
    users_affected: int | None


class ParallelAssessment(BaseModel):
    source: AssessmentSource
    severity: Severity
    score: int = Field(ge=0, le=100)
    finding: str
    recommended_action: RecommendedAction
    elapsed_ms: int


class WorkflowOutput(BaseModel):
    title: str
    service: ServiceName
    global_severity: Severity
    global_score: int
    recommended_action: RecommendedAction
    summary: str
    assessments: list[ParallelAssessment]
    ready_for_real_action: bool = False


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


def severity_from_score(score: int) -> Severity:
    if score >= 85:
        return Severity.CRITICAL
    if score >= 65:
        return Severity.HIGH
    if score >= 35:
        return Severity.MEDIUM
    return Severity.LOW


def action_from_global_score(score: int, service: ServiceName) -> RecommendedAction:
    if service == ServiceName.UNKNOWN:
        return RecommendedAction.REQUEST_MORE_DATA
    if score >= 85:
        return RecommendedAction.ESCALATE_TO_ON_CALL
    if score >= 65:
        return RecommendedAction.MANUAL_REVIEW
    return RecommendedAction.CREATE_DRAFT


@executor(id="prepare_parallel_context")
async def prepare_parallel_context(
    message: IncidentInput,
    ctx: WorkflowContext[ParallelContext],
) -> None:
    normalized = message.description.strip().lower()

    await ctx.send_message(
        ParallelContext(
            original_description=message.description,
            normalized_description=normalized,
            service=detect_service(normalized),
            reported_by=message.reported_by,
            users_affected=message.users_affected,
        )
    )


@executor(id="assess_service_impact")
async def assess_service_impact(
    message: ParallelContext,
    ctx: WorkflowContext[ParallelAssessment],
) -> None:
    start = perf_counter()

    # Simula una consulta lenta a inventario, CMDB o monitorización.
    await asyncio.sleep(0.8)

    score = 20
    finding = "Impacto técnico bajo."

    if message.service == ServiceName.ERP:
        score += 40
        finding = "El servicio ERP es crítico para procesos de negocio."

    if "error 500" in message.normalized_description or "caído" in message.normalized_description:
        score += 35
        finding = "Hay señales de caída o error severo del servicio."

    if message.users_affected is not None and message.users_affected >= 10:
        score += 20
        finding = "El número de usuarios afectados eleva el impacto técnico."

    score = min(score, 100)

    await ctx.send_message(
        ParallelAssessment(
            source=AssessmentSource.SERVICE_IMPACT,
            severity=severity_from_score(score),
            score=score,
            finding=finding,
            recommended_action=(
                RecommendedAction.ESCALATE_TO_ON_CALL
                if score >= 85
                else RecommendedAction.CREATE_DRAFT
            ),
            elapsed_ms=int((perf_counter() - start) * 1000),
        )
    )


@executor(id="assess_security_risk")
async def assess_security_risk(
    message: ParallelContext,
    ctx: WorkflowContext[ParallelAssessment],
) -> None:
    start = perf_counter()

    # Simula una validación contra señales de seguridad o reglas de política.
    await asyncio.sleep(1.1)

    score = 15
    finding = "No hay señales claras de riesgo de seguridad."

    sensitive_terms = ["password", "contraseña", "permiso", "acceso", "token", "secreto"]

    if any(term in message.normalized_description for term in sensitive_terms):
        score += 60
        finding = "La descripción contiene señales relacionadas con credenciales, permisos o accesos."

    if message.service == ServiceName.VPN:
        score += 15
        finding = "La VPN tiene implicaciones de acceso remoto."

    score = min(score, 100)

    await ctx.send_message(
        ParallelAssessment(
            source=AssessmentSource.SECURITY_RISK,
            severity=severity_from_score(score),
            score=score,
            finding=finding,
            recommended_action=(
                RecommendedAction.MANUAL_REVIEW
                if score >= 65
                else RecommendedAction.CREATE_DRAFT
            ),
            elapsed_ms=int((perf_counter() - start) * 1000),
        )
    )


@executor(id="assess_business_priority")
async def assess_business_priority(
    message: ParallelContext,
    ctx: WorkflowContext[ParallelAssessment],
) -> None:
    start = perf_counter()

    # Simula evaluación de criticidad de negocio.
    await asyncio.sleep(0.6)

    score = 20
    finding = "Prioridad de negocio estándar."

    if message.service == ServiceName.ERP:
        score += 45
        finding = "ERP soporta procesos centrales de negocio."

    if message.users_affected is not None:
        if message.users_affected >= 20:
            score += 35
            finding = "El impacto de negocio es alto por volumen de usuarios afectados."
        elif message.users_affected >= 5:
            score += 20
            finding = "El impacto de negocio es moderado por usuarios afectados."

    if message.service == ServiceName.UNKNOWN:
        score = 30
        finding = "No se puede evaluar bien la prioridad de negocio sin servicio identificado."

    score = min(score, 100)

    await ctx.send_message(
        ParallelAssessment(
            source=AssessmentSource.BUSINESS_PRIORITY,
            severity=severity_from_score(score),
            score=score,
            finding=finding,
            recommended_action=(
                RecommendedAction.ESCALATE_TO_ON_CALL
                if score >= 85
                else RecommendedAction.CREATE_DRAFT
            ),
            elapsed_ms=int((perf_counter() - start) * 1000),
        )
    )


@executor(id="aggregate_assessments")
async def aggregate_assessments(
    message: list[ParallelAssessment],
    ctx: WorkflowContext[Never, WorkflowOutput],
) -> None:
    if not message:
        await ctx.yield_output(
            WorkflowOutput(
                title="No hay evaluaciones disponibles",
                service=ServiceName.UNKNOWN,
                global_severity=Severity.LOW,
                global_score=0,
                recommended_action=RecommendedAction.MANUAL_REVIEW,
                summary="El agregador no recibió resultados de las ramas paralelas.",
                assessments=[],
            )
        )
        return

    assessments = sorted(message, key=lambda item: item.source.value)

    global_score = max(item.score for item in assessments)
    global_severity = severity_from_score(global_score)

    service = ServiceName.UNKNOWN
    # En este ejemplo las ramas no devuelven service para mantener el output parcial simple.
    # Inferimos acción global a partir de score. En producción conviene propagar service explícitamente.
    if any(item.source == AssessmentSource.SERVICE_IMPACT and item.score >= 65 for item in assessments):
        service = ServiceName.ERP

    recommended_action = action_from_global_score(global_score, service)

    reasons = " | ".join(
        f"{item.source.value}: {item.finding}"
        for item in assessments
    )

    await ctx.yield_output(
        WorkflowOutput(
            title=f"Evaluación paralela completada: severidad {global_severity.value}",
            service=service,
            global_severity=global_severity,
            global_score=global_score,
            recommended_action=recommended_action,
            summary=(
                "Se han agregado las evaluaciones técnica, de seguridad y de negocio. "
                f"Motivos principales: {reasons}"
            ),
            assessments=assessments,
            ready_for_real_action=False,
        )
    )


def build_incident_parallel_workflow():
    workflow = (
        WorkflowBuilder(start_executor=prepare_parallel_context)
        .add_fan_out_edges(
            prepare_parallel_context,
            [
                assess_service_impact,
                assess_security_risk,
                assess_business_priority,
            ],
        )
        .add_fan_in_edges(
            [
                assess_service_impact,
                assess_security_risk,
                assess_business_priority,
            ],
            aggregate_assessments,
        )
        .build()
    )

    return workflow


async def run_case(name: str, request: IncidentInput) -> None:
    workflow = build_incident_parallel_workflow()

    start = perf_counter()
    events = await workflow.run(request)
    elapsed_ms = int((perf_counter() - start) * 1000)

    outputs = events.get_outputs()

    print(f"\n--- CASO: {name} ---")
    print(f"Tiempo total workflow: {elapsed_ms} ms")

    for output in outputs:
        if isinstance(output, BaseModel):
            print(output.model_dump_json(indent=2))
        else:
            print(output)


async def main() -> None:
    await run_case(
        name="ERP crítico",
        request=IncidentInput(
            description="El ERP devuelve error 500 y afecta a 25 usuarios.",
            reported_by="lab1@contoso.com",
            users_affected=25,
        ),
    )

    await run_case(
        name="VPN con riesgo de acceso",
        request=IncidentInput(
            description="La VPN está intermitente y hay problemas de acceso con contraseña.",
            reported_by="lab2@contoso.com",
            users_affected=3,
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