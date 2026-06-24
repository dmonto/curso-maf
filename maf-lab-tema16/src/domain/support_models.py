from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


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
class SupportTicketDraftRequest:
    service: SupportService
    summary: str
    affected_users: int
    business_impact: str


@dataclass(frozen=True)
class SupportTicketDraft:
    ticket_type: str
    service: SupportService
    priority: TicketPriority
    summary: str
    business_impact: str
    recommended_queue: str
    requires_human_review: bool