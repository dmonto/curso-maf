from __future__ import annotations

from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from src.events.incident_event_service import (
    IncidentEventError,
    IncidentEventService,
)


@tool(
    name="report_support_incident_event",
    description=(
        "Registra una incidencia de soporte para procesamiento asíncrono. "
        "Publica un evento support.incident.reported.v1. "
        "No clasifica la incidencia inmediatamente y no crea tickets reales."
    ),
)
def report_support_incident_event(
    service: Annotated[
        Literal["vpn", "erp", "correo", "teams"],
        Field(description="Servicio afectado por la incidencia."),
    ],
    summary: Annotated[
        str,
        Field(description="Resumen concreto de la incidencia.", min_length=10),
    ],
    affected_users: Annotated[
        int,
        Field(description="Número estimado de usuarios afectados.", ge=1),
    ],
    business_impact: Annotated[
        str,
        Field(description="Impacto operativo o de negocio.", min_length=5),
    ],
) -> dict:
    try:
        return IncidentEventService().report_incident(
            service=service,
            summary=summary,
            affected_users=affected_users,
            business_impact=business_impact,
        )
    except IncidentEventError as error:
        return {
            "accepted": False,
            "error": "incident_event_validation_error",
            "message": str(error),
        }