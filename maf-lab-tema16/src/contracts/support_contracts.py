from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


class ReportIncidentRequestV1(ContractBase):
    service: Literal["vpn", "erp", "correo", "teams"] = Field(
        description="Servicio afectado por la incidencia."
    )
    summary: str = Field(
        min_length=10,
        description="Resumen concreto de la incidencia.",
    )
    affected_users: int = Field(
        ge=1,
        description="Número estimado de usuarios afectados.",
    )
    business_impact: str = Field(
        min_length=5,
        description="Impacto operativo o de negocio.",
    )


class IncidentReportedEventV1(ContractBase):
    incident_id: str = Field(
        pattern=r"^inc-[a-zA-Z0-9]+",
        description="Identificador interno de incidencia.",
    )
    service: Literal["vpn", "erp", "correo", "teams"]
    summary: str = Field(min_length=10)
    affected_users: int = Field(ge=1)
    business_impact: str = Field(min_length=5)


class IncidentClassificationV1(ContractBase):
    incident_id: str = Field(pattern=r"^inc-[a-zA-Z0-9]+")
    priority: Literal["p1", "p2", "p3"]
    recommended_team: str = Field(min_length=3)
    requires_escalation: bool
    reason: str = Field(min_length=5)


class ReportIncidentResultV1(ContractBase):
    correlation_id: str = Field(pattern=r"^corr-[a-zA-Z0-9]+")
    incident: IncidentReportedEventV1
    classification: IncidentClassificationV1


class ContractErrorV1(ContractBase):
    error: str
    message: str
    contract_name: str | None = None
    schema_version: int | None = None