from __future__ import annotations

from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from src.clean_arch.application.use_cases import ReportIncidentCommand
from src.clean_arch.container import build_container
from src.clean_arch.domain.policies import IncidentPolicyError


@tool(
    name="report_and_classify_support_incident",
    description=(
        "Registra y clasifica una incidencia de soporte usando la capa de aplicación. "
        "Debe usarse cuando ya se conozcan servicio, resumen, usuarios afectados e impacto. "
        "No crea tickets reales."
    ),
)
def report_and_classify_support_incident(
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
    use_case = build_container().report_and_classify_incident_use_case()

    try:
        return use_case.execute(
            ReportIncidentCommand(
                service=service,
                summary=summary,
                affected_users=affected_users,
                business_impact=business_impact,
            )
        )

    except IncidentPolicyError as error:
        return {
            "error": "policy_validation_error",
            "message": str(error),
        }

    except ValueError as error:
        return {
            "error": "invalid_service",
            "message": str(error),
        }