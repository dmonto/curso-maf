from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field


AUDIT_PATH = Path("logs/operations_assistant_audit.jsonl")
AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)


ServiceName = Literal["vpn", "teams", "correo", "erp", "api", "desconocido"]
Severity = Literal["low", "medium", "high", "critical"]
Impact = Literal["local", "partial", "global", "business_critical", "unknown"]
ActionRisk = Literal["safe", "requires_confirmation", "blocked"]


@dataclass(frozen=True)
class OperationClassification:
    service: str
    severity: str
    impact: str
    business_blocker: bool
    escalation_required: bool
    rationale: str


@dataclass(frozen=True)
class Runbook:
    service: str
    title: str
    first_checks: list[str]
    escalation_criteria: list[str]
    forbidden_actions: list[str]


@dataclass(frozen=True)
class ActionPlan:
    plan_id: str
    service: str
    severity: str
    impact: str
    risk: str
    recommended_steps: list[str]
    validation_steps: list[str]
    escalation_target: str
    requires_human_approval: bool


RUNBOOKS: dict[str, Runbook] = {
    "erp": Runbook(
        service="erp",
        title="Runbook ERP - Degradación o error en facturación",
        first_checks=[
            "Comprobar si hay alerta activa de infraestructura.",
            "Validar latencia de API y errores 5xx.",
            "Revisar si hubo despliegue reciente.",
            "Comprobar cola de integración y base de datos.",
        ],
        escalation_criteria=[
            "Afecta a varios usuarios o a un área completa.",
            "Bloquea facturación, cierre contable o logística.",
            "El error se mantiene más de 15 minutos.",
        ],
        forbidden_actions=[
            "No reiniciar base de datos sin aprobación.",
            "No revertir despliegue sin validar impacto.",
            "No cerrar la incidencia sin confirmación funcional.",
        ],
    ),
    "api": Runbook(
        service="api",
        title="Runbook API - Latencia o errores 5xx",
        first_checks=[
            "Validar tasa de errores por endpoint.",
            "Comparar latencia p95 con la línea base.",
            "Comprobar saturación de CPU, memoria y conexiones.",
            "Revisar dependencias externas.",
        ],
        escalation_criteria=[
            "Error rate superior al umbral durante más de 10 minutos.",
            "Afectación a clientes externos.",
            "Dependencia crítica no disponible.",
        ],
        forbidden_actions=[
            "No aumentar capacidad sin revisar coste.",
            "No desactivar validaciones de seguridad.",
        ],
    ),
    "teams": Runbook(
        service="teams",
        title="Runbook Teams - Degradación de colaboración",
        first_checks=[
            "Validar si afecta a un usuario, grupo o toda la organización.",
            "Comprobar conectividad y cliente web.",
            "Revisar incidencias conocidas.",
        ],
        escalation_criteria=[
            "Afecta a un departamento completo.",
            "Impide reuniones críticas.",
            "Hay múltiples reportes simultáneos.",
        ],
        forbidden_actions=[
            "No reinstalar masivamente clientes sin diagnóstico.",
        ],
    ),
}


def _audit(event: dict) -> None:
    payload = {
        "event_id": str(uuid.uuid4()),
        "ts": time.time(),
        **event,
    }

    with AUDIT_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _route_team(service: str) -> str:
    routing = {
        "erp": "business-apps",
        "api": "platform-engineering",
        "vpn": "networking",
        "teams": "collaboration",
        "correo": "messaging",
    }
    return routing.get(service, "operations")


@tool(
    name="classify_operational_signal",
    description=(
        "Clasifica una señal operativa según servicio, severidad, impacto y necesidad de escalado. "
        "Usar al inicio del análisis de una alerta o evento operativo."
    ),
)
def classify_operational_signal(
    service: Annotated[
        ServiceName,
        Field(description="Servicio afectado: vpn, teams, correo, erp, api o desconocido."),
    ],
    error_rate_percent: Annotated[
        float,
        Field(description="Porcentaje aproximado de errores observado.", ge=0, le=100),
    ],
    affected_users: Annotated[
        int,
        Field(description="Número aproximado de usuarios afectados.", ge=0),
    ],
    business_blocker: Annotated[
        bool,
        Field(description="True si bloquea un proceso crítico de negocio."),
    ],
) -> str:
    if business_blocker or error_rate_percent >= 30 or affected_users >= 100:
        severity: Severity = "critical"
    elif error_rate_percent >= 10 or affected_users >= 20:
        severity = "high"
    elif error_rate_percent >= 3 or affected_users >= 5:
        severity = "medium"
    else:
        severity = "low"

    if business_blocker:
        impact: Impact = "business_critical"
    elif affected_users >= 100:
        impact = "global"
    elif affected_users >= 5:
        impact = "partial"
    elif affected_users > 0:
        impact = "local"
    else:
        impact = "unknown"

    escalation_required = severity in ("high", "critical") or impact == "business_critical"

    classification = OperationClassification(
        service=service,
        severity=severity,
        impact=impact,
        business_blocker=business_blocker,
        escalation_required=escalation_required,
        rationale=(
            f"Severidad {severity} estimada por error_rate={error_rate_percent}% "
            f"y affected_users={affected_users}."
        ),
    )

    _audit(
        {
            "event_type": "signal.classified",
            "tool_name": "classify_operational_signal",
            "service": service,
            "severity": severity,
            "impact": impact,
            "escalation_required": escalation_required,
        }
    )

    return json.dumps(asdict(classification), ensure_ascii=False)


@tool(
    name="get_operations_runbook",
    description=(
        "Recupera el runbook operativo local para un servicio. "
        "Usar antes de recomendar pasos de actuación."
    ),
)
def get_operations_runbook(
    service: Annotated[
        ServiceName,
        Field(description="Servicio afectado: vpn, teams, correo, erp, api o desconocido."),
    ],
) -> str:
    runbook = RUNBOOKS.get(service)

    if runbook is None:
        result = {
            "service": service,
            "found": False,
            "message": "No hay runbook local para este servicio. Pedir más información o escalar a operaciones.",
        }
    else:
        result = {
            "found": True,
            **asdict(runbook),
        }

    _audit(
        {
            "event_type": "runbook.retrieved",
            "tool_name": "get_operations_runbook",
            "service": service,
            "found": result["found"],
        }
    )

    return json.dumps(result, ensure_ascii=False)


@tool(
    name="prepare_operations_action_plan",
    description=(
        "Prepara un plan de actuación operativo. No ejecuta acciones reales. "
        "Debe usarse después de clasificar la señal y consultar el runbook."
    ),
)
def prepare_operations_action_plan(
    service: Annotated[str, Field(description="Servicio afectado.")],
    severity: Annotated[Severity, Field(description="Severidad clasificada.")],
    impact: Annotated[Impact, Field(description="Impacto clasificado.")],
    symptoms: Annotated[str, Field(description="Síntomas observados.", min_length=10)],
    runbook_summary: Annotated[
        str,
        Field(description="Resumen del runbook aplicable o motivo por el que no existe."),
    ],
) -> str:
    requires_approval = severity in ("high", "critical") or impact == "business_critical"

    risk: ActionRisk = "requires_confirmation" if requires_approval else "safe"

    plan = ActionPlan(
        plan_id=f"ops-plan-{uuid.uuid4().hex[:8]}",
        service=service,
        severity=severity,
        impact=impact,
        risk=risk,
        recommended_steps=[
            "Confirmar alcance real de la afectación.",
            "Revisar métricas principales del servicio.",
            "Contrastar con cambios o despliegues recientes.",
            "Aplicar comprobaciones del runbook antes de ejecutar acciones.",
            "Escalar si se cumple algún criterio de severidad o impacto.",
        ],
        validation_steps=[
            "Comprobar reducción de errores.",
            "Validar recuperación con usuario o equipo afectado.",
            "Confirmar que no aparecen nuevas alertas relacionadas.",
        ],
        escalation_target=_route_team(service),
        requires_human_approval=requires_approval,
    )

    result = {
        **asdict(plan),
        "symptoms": symptoms,
        "runbook_summary": runbook_summary,
        "note": "Plan preparado como recomendación. No se ha ejecutado ninguna acción real.",
    }

    _audit(
        {
            "event_type": "action_plan.created",
            "tool_name": "prepare_operations_action_plan",
            "plan_id": plan.plan_id,
            "service": service,
            "severity": severity,
            "impact": impact,
            "risk": risk,
            "requires_human_approval": requires_approval,
        }
    )

    return json.dumps(result, ensure_ascii=False)


@tool(
    name="create_operations_handover",
    description=(
        "Genera un resumen de handover operativo para transferir contexto a otro turno o equipo."
    ),
)
def create_operations_handover(
    service: Annotated[str, Field(description="Servicio afectado.")],
    current_status: Annotated[str, Field(description="Estado actual del incidente.")],
    actions_done: Annotated[str, Field(description="Acciones realizadas o revisadas.")],
    pending_items: Annotated[str, Field(description="Pendientes relevantes.")],
    next_owner: Annotated[str, Field(description="Equipo o responsable siguiente.")],
) -> str:
    handover_id = f"handover-{uuid.uuid4().hex[:8]}"

    handover = {
        "handover_id": handover_id,
        "service": service,
        "current_status": current_status,
        "actions_done": actions_done,
        "pending_items": pending_items,
        "next_owner": next_owner,
        "requires_review": True,
    }

    _audit(
        {
            "event_type": "handover.created",
            "tool_name": "create_operations_handover",
            "handover_id": handover_id,
            "service": service,
            "next_owner": next_owner,
        }
    )

    return json.dumps(handover, ensure_ascii=False)