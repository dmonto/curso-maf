from __future__ import annotations

from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from src.integrations.support_microservice_client import (
    SupportMicroserviceError,
    build_support_microservice_client,
)


@tool(
    name="triage_incident_with_support_service",
    description=(
        "Consulta el microservicio corporativo de soporte para clasificar una incidencia. "
        "Devuelve prioridad, equipo recomendado, si requiere escalado y razón de la decisión. "
        "Debe usarse cuando el usuario describa una incidencia y haya datos suficientes."
    ),
)
def triage_incident_with_support_service(
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
    client = build_support_microservice_client()

    try:
        return client.triage_incident(
            service=service,
            summary=summary,
            affected_users=affected_users,
            business_impact=business_impact,
        )

    except SupportMicroserviceError as error:
        return {
            "error": "support_microservice_unavailable",
            "message": str(error),
        }