from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, field_validator


class ExternalDataValidationError(RuntimeError):
    pass


class ExternalTicketError(RuntimeError):
    pass


Priority = Literal["p1", "p2", "p3", "p4"]
TicketStatus = Literal["open", "investigating", "monitoring", "closed"]


STATUS_ALIASES = {
    "abierto": "open",
    "open": "open",
    "en proceso": "investigating",
    "investigating": "investigating",
    "monitoring": "monitoring",
    "cerrado": "closed",
    "closed": "closed",
}


PRIORITY_ALIASES = {
    "p1": "p1",
    "p2": "p2",
    "p3": "p3",
    "p4": "p4",
    "alta": "p1",
    "media": "p2",
    "baja": "p4",
}


class SafeTicketDto(BaseModel):
    """
    DTO interno seguro.
    Solo contiene campos que el agente puede recibir.
    """

    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(pattern=r"^INC-\d{4,}$")
    service: str = Field(min_length=2, max_length=40)
    summary: str = Field(min_length=5, max_length=300)
    priority: Priority
    status: TicketStatus
    owner_email: EmailStr
    updated_at: datetime | None = None
    source: str = "dirty-ticket-api"

    @field_validator("service")
    @classmethod
    def normalize_service(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("summary")
    @classmethod
    def clean_summary(cls, value: str) -> str:
        clean = " ".join(value.strip().split())
        if "password" in clean.lower() or "token" in clean.lower():
            raise ValueError("El resumen contiene posibles secretos.")
        return clean

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value: Any) -> Any:
        if isinstance(value, str):
            normalized = PRIORITY_ALIASES.get(value.strip().lower())
            if normalized:
                return normalized
        return value

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> Any:
        if isinstance(value, str):
            normalized = STATUS_ALIASES.get(value.strip().lower())
            if normalized:
                return normalized
        return value


@dataclass(frozen=True)
class ExternalTicketClient:
    base_url: str
    timeout_seconds: float = 5.0

    @classmethod
    def from_env(cls) -> "ExternalTicketClient":
        base_url = os.getenv("DIRTY_TICKET_API_BASE_URL")
        if not base_url:
            raise RuntimeError("Falta DIRTY_TICKET_API_BASE_URL en .env")

        return cls(base_url=base_url.rstrip("/"))

    def _fetch_raw_ticket(self, ticket_id: str) -> dict[str, Any]:
        clean_id = ticket_id.strip().upper()

        try:
            response = httpx.get(
                f"{self.base_url}/tickets/{clean_id}",
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ExternalTicketError("Timeout consultando API externa.") from exc
        except httpx.RequestError as exc:
            raise ExternalTicketError(f"Error de red consultando API externa: {exc}") from exc

        if response.status_code == 404:
            raise ExternalTicketError(f"No existe el ticket {clean_id}.")

        if response.status_code >= 400:
            raise ExternalTicketError(
                f"Error HTTP {response.status_code} consultando API externa."
            )

        return response.json()

    def get_validated_ticket(self, ticket_id: str) -> SafeTicketDto:
        raw = self._fetch_raw_ticket(ticket_id)

        allowed_payload = {
            "ticket_id": raw.get("ticket_id"),
            "service": raw.get("service"),
            "summary": raw.get("summary"),
            "priority": raw.get("priority"),
            "status": raw.get("status"),
            "owner_email": raw.get("owner_email"),
            "updated_at": raw.get("updated_at"),
            "source": "dirty-ticket-api",
        }

        try:
            return SafeTicketDto.model_validate(allowed_payload)
        except ValidationError as exc:
            raise ExternalDataValidationError(
                f"La API externa devolvió datos no válidos para {ticket_id}: {exc.errors()}"
            ) from exc