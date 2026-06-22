from __future__ import annotations

from typing import Annotated

from agent_framework import tool
from pydantic import Field

from src.tools.support_logic import (
    IncidentInput,
    Priority,
    ServiceName,
    build_ticket_draft_payload,
    calculate_sla,
    classify_incident_risk,
    normalize_service_name,
)


@tool(
    name="normalize_service",
    description=(
        "Normaliza el nombre de un servicio corporativo a uno de los valores admitidos: "
        "vpn, correo, teams o erp. Úsala si el usuario usa nombres ambiguos o variantes."
    ),
)
def normalize_service(
    raw_service: Annotated[
        str,
        Field(min_length=2, max_length=80, description="Nombre del servicio escrito por el usuario."),
    ],
) -> dict:
    normalized = normalize_service_name(raw_service)

    if normalized is None:
        return {
            "valid": False,
            "raw_service": raw_service,
            "normalized_service": None,
            "allowed_services": ["vpn", "correo", "teams", "erp"],
        }

    return {
        "valid": True,
        "raw_service": raw_service,
        "normalized_service": normalized,
    }


@tool(
    name="calculate_sla_deadline",
    description=(
        "Calcula el SLA de una incidencia según prioridad p1, p2, p3 o p4. "
        "No crea tickets ni modifica sistemas externos."
    ),
)
def calculate_sla_deadline(
    priority: Annotated[
        Priority,
        Field(description="Prioridad de la incidencia: p1, p2, p3 o p4."),
    ],
) -> dict:
    return calculate_sla(priority)


@tool(
    name="classify_incident_risk",
    description=(
        "Clasifica el riesgo de una incidencia según servicio, prioridad, impacto "
        "y usuarios afectados. Úsala antes de recomendar escalado."
    ),
)
def classify_incident_risk_tool(
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
        Field(min_length=15, max_length=500, description="Impacto funcional o de negocio."),
    ],
    users_affected: Annotated[
        int,
        Field(ge=1, le=10000, description="Número estimado de usuarios afectados."),
    ],
) -> dict:
    incident = IncidentInput(
        service=service,
        priority=priority,
        summary=summary,
        impact=impact,
        users_affected=users_affected,
    )

    decision = classify_incident_risk(incident)

    return {
        "risk": decision.risk,
        "reason": decision.reason,
        "requires_human_validation": decision.requires_human_validation,
    }


@tool(
    name="draft_support_ticket",
    description=(
        "Prepara un borrador de ticket de soporte con validación interna, clasificación "
        "de riesgo y SLA. No crea tickets reales."
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
        Field(min_length=15, max_length=500, description="Impacto funcional o de negocio."),
    ],
    users_affected: Annotated[
        int,
        Field(ge=1, le=10000, description="Número estimado de usuarios afectados."),
    ],
) -> dict:
    incident = IncidentInput(
        service=service,
        priority=priority,
        summary=summary,
        impact=impact,
        users_affected=users_affected,
    )

    return build_ticket_draft_payload(incident)