from __future__ import annotations

from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from src.clean_arch.application.use_cases import ReportIncidentCommand
from src.contracts.registry import ContractValidationError, validate_payload
from src.di.container import AppContainer


def build_contract_report_tool(container: AppContainer):
    @tool(
        name="report_incident_with_contracts",
        description=(
            "Registra y clasifica una incidencia validando primero el contrato "
            "support.report_incident.request.v1. No crea tickets reales."
        ),
    )
    def report_incident_with_contracts(
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
        raw_payload = {
            "service": service,
            "summary": summary,
            "affected_users": affected_users,
            "business_impact": business_impact,
        }

        try:
            validated = validate_payload(
                contract_name="support.report_incident.request",
                schema_version=1,
                payload=raw_payload,
            )
        except ContractValidationError as error:
            return {
                "error": "contract_validation_error",
                "contract_name": error.contract_name,
                "schema_version": error.schema_version,
                "details": error.errors,
            }

        use_case = container.create_scope().report_and_classify_incident_use_case()

        result = use_case.execute(
            ReportIncidentCommand(
                service=validated.service,
                summary=validated.summary,
                affected_users=validated.affected_users,
                business_impact=validated.business_impact,
            )
        )

        return result

    return report_incident_with_contracts