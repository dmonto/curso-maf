from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any
from uuid import uuid4


class SupportService(StrEnum):
    VPN = "vpn"
    ERP = "erp"
    CORREO = "correo"
    TEAMS = "teams"


class TicketPriority(StrEnum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"


@dataclass(frozen=True)
class Incident:
    incident_id: str
    service: SupportService
    summary: str
    affected_users: int
    business_impact: str

    @staticmethod
    def create(
        service: SupportService,
        summary: str,
        affected_users: int,
        business_impact: str,
    ) -> "Incident":
        return Incident(
            incident_id=f"inc-{uuid4().hex[:10]}",
            service=service,
            summary=summary.strip(),
            affected_users=affected_users,
            business_impact=business_impact.strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["service"] = self.service.value
        return data


@dataclass(frozen=True)
class IncidentClassification:
    incident_id: str
    priority: TicketPriority
    recommended_team: str
    requires_escalation: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["priority"] = self.priority.value
        return data