from __future__ import annotations

import os
from enum import StrEnum
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


class ServiceName(StrEnum):
    VPN = "vpn"
    ERP = "erp"
    CORREO = "correo"
    TEAMS = "teams"


class TriageRequest(BaseModel):
    service: ServiceName
    summary: str = Field(min_length=10)
    affected_users: int = Field(ge=1)
    business_impact: str = Field(min_length=5)


class TriageResponse(BaseModel):
    correlation_id: str
    priority: str
    recommended_team: str
    requires_escalation: bool
    rationale: str


API_KEY = os.getenv("SUPPORT_SERVICE_API_KEY", "dev-support-key")

app = FastAPI(title="Support Triage Microservice")


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def decide_triage(payload: TriageRequest) -> tuple[str, str, bool, str]:
    impact = payload.business_impact.lower()

    if payload.affected_users >= 50:
        return (
            "p1",
            "major-incident-team",
            True,
            "Afecta a 50 o más usuarios.",
        )

    if payload.service == ServiceName.ERP and (
        "facturación" in impact or "clientes" in impact or "producción" in impact
    ):
        return (
            "p1",
            "business-apps-l2",
            True,
            "Incidencia crítica en ERP con impacto directo en negocio.",
        )

    if payload.affected_users >= 10:
        return (
            "p2",
            "service-desk-l2",
            True,
            "Afecta a un grupo relevante de usuarios.",
        )

    if payload.service == ServiceName.VPN:
        return (
            "p3",
            "network-support-l2",
            False,
            "Incidencia acotada de conectividad VPN.",
        )

    if payload.service in {ServiceName.CORREO, ServiceName.TEAMS}:
        return (
            "p3",
            "collaboration-support-l2",
            False,
            "Incidencia acotada en herramienta colaborativa.",
        )

    return (
        "p3",
        "service-desk-l1",
        False,
        "Incidencia de bajo impacto inicial.",
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/incidents/triage",
    response_model=TriageResponse,
    dependencies=[Depends(require_api_key)],
)
def triage_incident(
    payload: TriageRequest,
    x_correlation_id: str | None = Header(default=None, alias="x-correlation-id"),
) -> TriageResponse:
    correlation_id = x_correlation_id or f"corr-{uuid4().hex[:8]}"

    priority, team, escalation, rationale = decide_triage(payload)

    return TriageResponse(
        correlation_id=correlation_id,
        priority=priority,
        recommended_team=team,
        requires_escalation=escalation,
        rationale=rationale,
    )