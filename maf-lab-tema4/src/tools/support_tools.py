from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import uuid4

from agent_framework import tool
from pydantic import Field
import logging

from src.observability.events import Timer, log_event

logger = logging.getLogger("maf_lab.tools.support")

def _normalize_text(value: str) -> str:
    return value.strip().lower()



def _get_service_status_impl(service_name: str) -> dict[str, Any]:
    service_key = _normalize_text(service_name)

    services = {
        "vpn": {
            "status": "degradado",
            "severity": "medium",
            "message": "La VPN acepta conexiones, pero hay latencia elevada.",
            "recommended_action": "Pedir al usuario que pruebe reconexión y registrar incidencia si persiste.",
        },
        "correo": {
            "status": "operativo",
            "severity": "low",
            "message": "No hay incidencias activas en el servicio de correo.",
            "recommended_action": "Revisar cliente local, credenciales y conectividad del usuario.",
        },
        "sharepoint": {
            "status": "operativo",
            "severity": "low",
            "message": "SharePoint responde correctamente en las comprobaciones internas.",
            "recommended_action": "Validar permisos del usuario sobre el sitio o biblioteca concreta.",
        },
        "erp": {
            "status": "caido",
            "severity": "high",
            "message": "El ERP no responde en la comprobación simulada.",
            "recommended_action": "Escalar a operaciones y abrir ticket de prioridad alta.",
        },
    }

    result = services.get(service_key)

    if result is None:
        return {
            "found": False,
            "service": service_name,
            "known_services": sorted(services.keys()),
            "message": "Servicio no reconocido en el catálogo de laboratorio.",
        }

    return {
        "found": True,
        "service": service_key,
        **result,
    }


def _calculate_sla_deadline_impl(priority: str) -> dict[str, Any]:
    priority_key = _normalize_text(priority)

    sla_hours = {
        "p1": 4,
        "p2": 8,
        "p3": 24,
        "p4": 72,
    }

    if priority_key not in sla_hours:
        return {
            "valid": False,
            "priority": priority,
            "allowed_priorities": sorted(sla_hours.keys()),
            "message": "Prioridad no válida. Usa p1, p2, p3 o p4.",
        }

    now = datetime.now(timezone.utc)
    deadline = now + timedelta(hours=sla_hours[priority_key])

    return {
        "valid": True,
        "priority": priority_key,
        "sla_hours": sla_hours[priority_key],
        "created_at_utc": now.isoformat(),
        "deadline_utc": deadline.isoformat(),
    }


def _draft_support_ticket_impl(
    title: str,
    description: str,
    priority: str,
    affected_service: str,
) -> dict[str, Any]:
    title_clean = title.strip()
    description_clean = description.strip()
    priority_key = _normalize_text(priority)
    service_key = _normalize_text(affected_service)

    missing_fields: list[str] = []

    if len(title_clean) < 5:
        missing_fields.append("title")

    if len(description_clean) < 20:
        missing_fields.append("description")

    if priority_key not in {"p1", "p2", "p3", "p4"}:
        missing_fields.append("priority")

    if not service_key:
        missing_fields.append("affected_service")

    if missing_fields:
        return {
            "created": False,
            "message": "No se puede preparar el borrador porque faltan campos obligatorios o no son válidos.",
            "missing_or_invalid_fields": missing_fields,
        }

    return {
        "created": True,
        "draft_ticket_id": f"DRAFT-{uuid4().hex[:8].upper()}",
        "title": title_clean,
        "description": description_clean,
        "priority": priority_key,
        "affected_service": service_key,
        "status": "draft",
        "message": "Borrador de ticket preparado. No se ha enviado a ningún sistema externo.",
    }


@tool(approval_mode="never_require")
def get_service_status(
    service_name: Annotated[
        str,
        Field(
            description=(
                "Nombre del servicio que se quiere comprobar. "
                "Valores habituales: vpn, correo, sharepoint, erp."
            )
        ),
    ],
) -> dict[str, Any]:
    """
    Consulta el estado simulado de un servicio corporativo del laboratorio.
    No modifica ningún sistema externo.
    """
    timer = Timer()

    log_event(
        logger,
        logging.INFO,
        "tool.started",
        "Comienza tool get_service_status.",
        tool_name="get_service_status",
        service_name=service_name,
    )

    try:
        result = _get_service_status_impl(service_name)

        log_event(
            logger,
            logging.INFO,
            "tool.completed",
            "Finaliza tool get_service_status.",
            tool_name="get_service_status",
            duration_ms=timer.elapsed_ms(),
            success=True,
            found=result.get("found"),
            service=result.get("service"),
            status=result.get("status"),
        )

        return result

    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            "tool.failed",
            "Fallo en tool get_service_status.",
            tool_name="get_service_status",
            duration_ms=timer.elapsed_ms(),
            success=False,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        raise


@tool(approval_mode="never_require")
def calculate_sla_deadline(
    priority: Annotated[
        str,
        Field(
            description=(
                "Prioridad de la incidencia. Valores permitidos: p1, p2, p3, p4."
            )
        ),
    ],
) -> dict[str, Any]:
    """
    Calcula la fecha límite de atención según una prioridad de soporte.
    No modifica ningún sistema externo.
    """
    return _calculate_sla_deadline_impl(priority)


@tool(approval_mode="never_require")
def draft_support_ticket(
    title: Annotated[
        str,
        Field(description="Título breve del ticket de soporte."),
    ],
    description: Annotated[
        str,
        Field(description="Descripción completa del problema reportado por el usuario."),
    ],
    priority: Annotated[
        str,
        Field(description="Prioridad del ticket. Valores permitidos: p1, p2, p3, p4."),
    ],
    affected_service: Annotated[
        str,
        Field(description="Servicio afectado por la incidencia."),
    ],
) -> dict[str, Any]:
    """
    Prepara un borrador de ticket de soporte.
    No crea tickets reales ni llama a sistemas externos.
    """
    return _draft_support_ticket_impl(
        title=title,
        description=description,
        priority=priority,
        affected_service=affected_service,
    )