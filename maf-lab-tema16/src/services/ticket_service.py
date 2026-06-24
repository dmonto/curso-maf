from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from src.legacy.sk_ticket_plugin import LegacyTicketPlugin


class ServiceName(StrEnum):
    VPN = "vpn"
    CORREO = "correo"
    TEAMS = "teams"
    ERP = "erp"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class TicketSearchResult:
    ticket_id: str
    service: str
    status: str
    summary: str


@dataclass(frozen=True)
class TicketDraft:
    draft_id: str
    service: str
    title: str
    description: str
    priority: str
    confirmation_required: bool


@dataclass(frozen=True)
class ToolEnvelope:
    success: bool
    operation: str
    data: dict[str, Any] | list[dict[str, Any]] | None
    message: str
    error_code: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


class TicketService:
    def __init__(self, legacy_plugin: LegacyTicketPlugin | None = None) -> None:
        self._legacy_plugin = legacy_plugin or LegacyTicketPlugin()

    def search_tickets(
        self,
        *,
        service: ServiceName,
        max_results: int = 3,
    ) -> ToolEnvelope:
        raw = self._legacy_plugin.execute(
            action="search",
            payload={
                "service": service.value,
                "max_results": max_results,
            },
        )

        payload = json.loads(raw)

        if not payload.get("ok"):
            return ToolEnvelope(
                success=False,
                operation="search_tickets",
                data=None,
                message="No se pudieron consultar tickets.",
                error_code="legacy_search_failed",
            )

        items = payload.get("items", [])[:max_results]

        results = [
            asdict(
                TicketSearchResult(
                    ticket_id=item["ticket_id"],
                    service=item["service"],
                    status=item["status"],
                    summary=item["summary"],
                )
            )
            for item in items
        ]

        return ToolEnvelope(
            success=True,
            operation="search_tickets",
            data=results,
            message=f"Se encontraron {len(results)} tickets relacionados.",
        )

    def prepare_ticket_draft(
        self,
        *,
        service: ServiceName,
        title: str,
        description: str,
        priority: TicketPriority,
    ) -> ToolEnvelope:
        draft = TicketDraft(
            draft_id=f"DRAFT-{service.value.upper()}-001",
            service=service.value,
            title=title,
            description=description,
            priority=priority.value,
            confirmation_required=True,
        )

        return ToolEnvelope(
            success=True,
            operation="prepare_ticket_draft",
            data=asdict(draft),
            message="Borrador preparado. Requiere confirmación antes de crear ticket real.",
        )

    def create_ticket_real(
        self,
        *,
        draft_id: str,
        confirmed_by_user: bool,
    ) -> ToolEnvelope:
        if not confirmed_by_user:
            return ToolEnvelope(
                success=False,
                operation="create_ticket_real",
                data=None,
                message="No se ha creado el ticket porque falta confirmación explícita.",
                error_code="confirmation_required",
            )

        raw = self._legacy_plugin.execute(
            action="create",
            payload={
                "draft_id": draft_id,
                "confirmed_by_user": confirmed_by_user,
            },
        )

        payload = json.loads(raw)

        if not payload.get("ok"):
            return ToolEnvelope(
                success=False,
                operation="create_ticket_real",
                data=None,
                message="No se pudo crear el ticket real.",
                error_code="legacy_create_failed",
            )

        return ToolEnvelope(
            success=True,
            operation="create_ticket_real",
            data={
                "ticket_id": payload["ticket_id"],
                "created_at_utc": payload["created_at_utc"],
            },
            message="Ticket real creado correctamente.",
        )