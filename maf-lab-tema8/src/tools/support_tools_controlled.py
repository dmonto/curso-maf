from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import uuid4

from agent_framework import tool
from pydantic import Field


ServiceName = Literal["vpn", "correo", "teams", "erp"]
Priority = Literal["p1", "p2", "p3", "p4"]


_SERVICE_STATUS = {
    "vpn": {
        "status": "degradado",
        "severity": "medium",
        "detail": "Latencia elevada en conexiones remotas.",
    },
    "correo": {
        "status": "operativo",
        "severity": "low",
        "detail": "No hay incidencias activas.",
    },
    "teams": {
        "status": "operativo",
        "severity": "low",
        "detail": "Servicio funcionando correctamente.",
    },
    "erp": {
        "status": "intermitente",
        "severity": "high",
        "detail": "Errores esporádicos de autenticación.",
    },
}


_SLA_HOURS = {
    "p1": 2,
    "p2": 8,
    "p3": 24,
    "p4": 72,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_p1(priority: Priority, users_affected: int, impact: str) -> dict | None:
    if priority != "p1":
        return None

    if users_affected < 10:
        return {
            "valid": False,
            "error": (
                "No se acepta prioridad p1 con menos de 10 usuarios afectados "
                "sin validación humana."
            ),
            "required_action": "Pedir más información o escalar a validación humana.",
        }

    if len(impact.strip()) < 20:
        return {
            "valid": False,
            "error": "La prioridad p1 requiere una descripción de impacto más concreta.",
            "required_action": "Pedir impacto de negocio, usuarios afectados y servicio.",
        }

    return None


@tool(
    name="get_service_status",
    description=(
        "Consulta el estado simulado de un servicio corporativo del laboratorio. "
        "Úsala cuando el usuario pregunte si VPN, correo, Teams o ERP están caídos, "
        "degradados o con errores. No modifica sistemas externos."
    ),
)
def get_service_status(
    service: Annotated[
        ServiceName,
        Field(description="Servicio corporativo: vpn, correo, teams o erp."),
    ],
) -> dict:
    status = _SERVICE_STATUS[service]

    return {
        "tool": "get_service_status",
        "service": service,
        "status": status["status"],
        "severity": status["severity"],
        "detail": status["detail"],
        "external_effect": False,
    }


@tool(
    name="calculate_sla_deadline",
    description=(
        "Calcula la fecha límite de atención según prioridad p1, p2, p3 o p4. "
        "No crea tickets ni modifica sistemas."
    ),
)
def calculate_sla_deadline(
    priority: Annotated[
        Priority,
        Field(description="Prioridad de la incidencia: p1, p2, p3 o p4."),
    ],
) -> dict:
    hours = _SLA_HOURS[priority]
    deadline = _utc_now() + timedelta(hours=hours)

    return {
        "tool": "calculate_sla_deadline",
        "priority": priority,
        "sla_hours": hours,
        "deadline_utc": deadline.isoformat(),
        "external_effect": False,
    }


@tool(
    name="draft_support_ticket",
    description=(
        "Prepara un borrador de ticket de soporte. No crea tickets reales. "
        "Úsala solo cuando haya servicio, resumen, prioridad, impacto y usuarios afectados."
    ),
)
def draft_support_ticket(
    service: Annotated[
        ServiceName,
        Field(description="Servicio afectado: vpn, correo, teams o erp."),
    ],
    priority: Annotated[
        Priority,
        Field(description="Prioridad propuesta: p1, p2, p3 o p4."),
    ],
    summary: Annotated[
        str,
        Field(min_length=10, max_length=200, description="Resumen breve de la incidencia."),
    ],
    impact: Annotated[
        str,
        Field(min_length=10, max_length=500, description="Impacto descrito por el usuario."),
    ],
    users_affected: Annotated[
        int,
        Field(ge=1, le=10000, description="Número estimado de usuarios afectados."),
    ],
) -> dict:
    p1_error = _validate_p1(priority, users_affected, impact)
    if p1_error:
        return {
            "tool": "draft_support_ticket",
            "created": False,
            "external_effect": False,
            **p1_error,
        }

    ticket_id = f"DRAFT-{uuid4().hex[:8].upper()}"

    return {
        "tool": "draft_support_ticket",
        "created": True,
        "ticket_type": "draft",
        "ticket_id": ticket_id,
        "service": service,
        "priority": priority,
        "summary": summary,
        "impact": impact,
        "users_affected": users_affected,
        "external_effect": False,
        "message": "Borrador preparado. No se ha creado ningún ticket real.",
    }


@tool(
    name="request_ticket_creation",
    description=(
        "Solicita la creación real de un ticket a partir de un borrador validado. "
        "Esta tool representa una acción con efecto externo y requiere aprobación."
    ),
    approval_mode="always_require",
)
def request_ticket_creation(
    draft_ticket_id: Annotated[
        str,
        Field(min_length=6, description="Identificador del borrador de ticket."),
    ],
    justification: Annotated[
        str,
        Field(min_length=20, description="Justificación para crear el ticket real."),
    ],
) -> dict:
    return {
        "tool": "request_ticket_creation",
        "created": True,
        "ticket_id": f"REAL-{uuid4().hex[:8].upper()}",
        "source_draft": draft_ticket_id,
        "justification": justification,
        "external_effect": True,
    }