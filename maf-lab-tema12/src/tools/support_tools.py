from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Literal
from uuid import uuid4

from agent_framework import tool
from pydantic import Field


Priority = Literal["p1", "p2", "p3", "p4"]


SERVICE_STATUS = {
    "vpn": {
        "status": "degraded",
        "severity": "medium",
        "recommended_action": "Preparar borrador de incidencia si el problema persiste.",
    },
    "erp": {
        "status": "operational",
        "severity": "none",
        "recommended_action": "No abrir incidencia salvo que haya síntomas adicionales.",
    },
    "correo": {
        "status": "operational",
        "severity": "none",
        "recommended_action": "Validar cliente local si el problema afecta a un único usuario.",
    },
}


SLA_HOURS = {
    "p1": 2,
    "p2": 8,
    "p3": 24,
    "p4": 72,
}


def _normalize(value: str) -> str:
    return value.strip().lower()


def _get_service_status_impl(service_name: str) -> dict[str, Any]:
    service = _normalize(service_name)

    if not service:
        return {
            "ok": False,
            "code": "invalid_service",
            "error": "El nombre del servicio no puede estar vacío.",
            "external_side_effect": False,
        }

    status = SERVICE_STATUS.get(service)

    if status is None:
        return {
            "ok": True,
            "service": service,
            "status": "unknown",
            "severity": "low",
            "recommended_action": "Pedir más información o validar el servicio afectado.",
            "external_side_effect": False,
        }

    return {
        "ok": True,
        "service": service,
        "status": status["status"],
        "severity": status["severity"],
        "recommended_action": status["recommended_action"],
        "external_side_effect": False,
    }


@tool(
    name="get_service_status",
    description=(
        "Consulta el estado simulado de un servicio corporativo del laboratorio. "
        "Úsala cuando el usuario pregunte si un servicio está caído, degradado u operativo. "
        "No modifica sistemas externos."
    ),
)
def get_service_status(
    service_name: Annotated[
        str,
        Field(description="Servicio corporativo. Ejemplos: vpn, erp, correo."),
    ],
) -> dict[str, Any]:
    return _get_service_status_impl(service_name)


def _calculate_sla_deadline_impl(priority: str) -> dict[str, Any]:
    normalized_priority = _normalize(priority)

    if normalized_priority not in SLA_HOURS:
        return {
            "ok": False,
            "code": "invalid_priority",
            "error": "Prioridad inválida. Usa p1, p2, p3 o p4.",
            "external_side_effect": False,
        }

    sla_hours = SLA_HOURS[normalized_priority]
    deadline = datetime.now(timezone.utc) + timedelta(hours=sla_hours)

    return {
        "ok": True,
        "priority": normalized_priority,
        "sla_hours": sla_hours,
        "deadline_utc": deadline.isoformat(),
        "external_side_effect": False,
    }


@tool(
    name="calculate_sla_deadline",
    description=(
        "Calcula la fecha límite de atención según prioridad p1, p2, p3 o p4. "
        "No crea tickets ni modifica sistemas externos."
    ),
)
def calculate_sla_deadline(
    priority: Annotated[
        str,
        Field(description="Prioridad de la incidencia. Valores válidos: p1, p2, p3, p4."),
    ],
) -> dict[str, Any]:
    return _calculate_sla_deadline_impl(priority)


def _draft_support_ticket_impl(
    service_name: str,
    summary: str,
    priority: str,
) -> dict[str, Any]:
    service = _normalize(service_name)
    normalized_priority = _normalize(priority)
    clean_summary = summary.strip()

    if not service:
        return {
            "ok": False,
            "code": "invalid_service",
            "error": "El servicio no puede estar vacío.",
            "external_side_effect": False,
        }

    if not clean_summary:
        return {
            "ok": False,
            "code": "invalid_summary",
            "error": "El resumen del ticket no puede estar vacío.",
            "external_side_effect": False,
        }

    if normalized_priority not in SLA_HOURS:
        return {
            "ok": False,
            "code": "invalid_priority",
            "error": "Prioridad inválida. Usa p1, p2, p3 o p4.",
            "external_side_effect": False,
        }

    return {
        "ok": True,
        "ticket_draft_id": f"DRAFT-{uuid4().hex[:8].upper()}",
        "service": service,
        "summary": clean_summary,
        "priority": normalized_priority,
        "external_side_effect": False,
        "requires_confirmation": True,
        "message": "Borrador preparado. No se ha creado ningún ticket real.",
    }


@tool(
    name="draft_support_ticket",
    description=(
        "Prepara un borrador de ticket de soporte. "
        "No crea tickets reales en sistemas externos. "
        "Debe usarse cuando haya servicio, resumen y prioridad."
    ),
)
def draft_support_ticket(
    service_name: Annotated[
        str,
        Field(description="Servicio afectado. Ejemplos: vpn, erp, correo."),
    ],
    summary: Annotated[
        str,
        Field(description="Resumen breve de la incidencia."),
    ],
    priority: Annotated[
        str,
        Field(description="Prioridad. Valores válidos: p1, p2, p3, p4."),
    ],
) -> dict[str, Any]:
    return _draft_support_ticket_impl(service_name, summary, priority)