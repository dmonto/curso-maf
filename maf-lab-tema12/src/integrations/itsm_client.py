from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError


class ItsmIntegrationError(RuntimeError):
    pass


class TicketDto(BaseModel):
    ticket_id: str
    service: str
    summary: str
    priority: str
    status: str


class TicketCreateDto(BaseModel):
    service: str = Field(min_length=2)
    summary: str = Field(min_length=5)
    priority: Literal["p1", "p2", "p3", "p4"]


@dataclass(frozen=True)
class ItsmClient:
    base_url: str
    token: str
    timeout_seconds: float = 5.0

    @classmethod
    def from_env(cls) -> "ItsmClient":
        base_url = os.getenv("ITSM_API_BASE_URL")
        token = os.getenv("ITSM_API_TOKEN")

        if not base_url:
            raise RuntimeError("Falta ITSM_API_BASE_URL en .env")

        if not token:
            raise RuntimeError("Falta ITSM_API_TOKEN en .env")

        return cls(base_url=base_url.rstrip("/"), token=token)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get_ticket(self, ticket_id: str) -> TicketDto:
        url = f"{self.base_url}/tickets/{ticket_id.upper()}"

        try:
            response = httpx.get(
                url,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ItsmIntegrationError("Timeout consultando el sistema ITSM") from exc
        except httpx.RequestError as exc:
            raise ItsmIntegrationError(f"Error de red consultando ITSM: {exc}") from exc

        if response.status_code == 404:
            raise ItsmIntegrationError(f"No existe el ticket {ticket_id}")

        if response.status_code == 401:
            raise ItsmIntegrationError("No autorizado contra la API ITSM")

        if response.status_code >= 400:
            raise ItsmIntegrationError(
                f"Error HTTP {response.status_code} consultando ITSM"
            )

        try:
            return TicketDto.model_validate(response.json())
        except ValidationError as exc:
            raise ItsmIntegrationError("La respuesta de ITSM no tiene el formato esperado") from exc

    def create_ticket(
        self,
        service: str,
        summary: str,
        priority: Literal["p1", "p2", "p3", "p4"],
    ) -> TicketDto:
        payload = TicketCreateDto(
            service=service,
            summary=summary,
            priority=priority,
        )

        try:
            response = httpx.post(
                f"{self.base_url}/tickets",
                headers=self._headers(),
                json=payload.model_dump(),
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ItsmIntegrationError("Timeout creando ticket en ITSM") from exc
        except httpx.RequestError as exc:
            raise ItsmIntegrationError(f"Error de red creando ticket en ITSM: {exc}") from exc

        if response.status_code == 401:
            raise ItsmIntegrationError("No autorizado contra la API ITSM")

        if response.status_code >= 400:
            raise ItsmIntegrationError(
                f"Error HTTP {response.status_code} creando ticket en ITSM: {response.text}"
            )

        try:
            return TicketDto.model_validate(response.json())
        except ValidationError as exc:
            raise ItsmIntegrationError("La respuesta de creación no tiene el formato esperado") from exc