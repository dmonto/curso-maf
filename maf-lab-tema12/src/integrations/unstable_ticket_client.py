from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Literal
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError


ErrorKind = Literal[
    "timeout",
    "network",
    "unauthorized",
    "forbidden",
    "not_found",
    "rate_limited",
    "conflict",
    "external_server_error",
    "invalid_response",
    "unknown",
]


class SafeTicket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(pattern=r"^INC-[A-Z0-9]+$")
    service: str
    summary: str
    priority: Literal["p1", "p2", "p3", "p4"]
    status: Literal["open", "investigating", "monitoring", "closed"]


class ExternalError(BaseModel):
    ok: bool = False
    error_kind: ErrorKind
    retryable: bool
    user_message: str
    technical_message: str
    correlation_id: str
    attempts: int


class ExternalSuccess(BaseModel):
    ok: bool = True
    ticket: SafeTicket
    correlation_id: str
    attempts: int


ExternalResult = ExternalSuccess | ExternalError


def classify_http_error(status_code: int) -> tuple[ErrorKind, bool, str]:
    if status_code == 401:
        return "unauthorized", False, "La autenticación contra el sistema externo no es válida."

    if status_code == 403:
        return "forbidden", False, "No hay permisos suficientes para consultar el recurso."

    if status_code == 404:
        return "not_found", False, "No se encontró el recurso solicitado."

    if status_code == 409:
        return "conflict", False, "El recurso está en conflicto o ha cambiado."

    if status_code == 429:
        return "rate_limited", True, "El sistema externo está limitando temporalmente las llamadas."

    if status_code in {500, 502, 503, 504}:
        return "external_server_error", True, "El sistema externo ha devuelto un error temporal."

    return "unknown", False, f"El sistema externo devolvió HTTP {status_code}."


@dataclass(frozen=True)
class UnstableTicketClient:
    base_url: str
    timeout_seconds: float = 2.0
    max_attempts: int = 3
    backoff_seconds: float = 0.5

    @classmethod
    def from_env(cls) -> "UnstableTicketClient":
        base_url = os.getenv("UNSTABLE_API_BASE_URL")
        if not base_url:
            raise RuntimeError("Falta UNSTABLE_API_BASE_URL en .env")

        return cls(base_url=base_url.rstrip("/"))

    def get_ticket(self, ticket_id: str) -> ExternalResult:
        correlation_id = str(uuid4())
        clean_id = ticket_id.strip().upper()

        last_error: ExternalError | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                response = httpx.get(
                    f"{self.base_url}/tickets/{clean_id}",
                    headers={"x-correlation-id": correlation_id},
                    timeout=self.timeout_seconds,
                )

                if response.status_code >= 400:
                    error_kind, retryable, user_message = classify_http_error(
                        response.status_code
                    )

                    last_error = ExternalError(
                        error_kind=error_kind,
                        retryable=retryable,
                        user_message=user_message,
                        technical_message=f"HTTP {response.status_code}: {response.text}",
                        correlation_id=correlation_id,
                        attempts=attempt,
                    )

                    if retryable and attempt < self.max_attempts:
                        time.sleep(self.backoff_seconds * attempt)
                        continue

                    return last_error

                try:
                    ticket = SafeTicket.model_validate(response.json())
                except ValidationError as exc:
                    return ExternalError(
                        error_kind="invalid_response",
                        retryable=False,
                        user_message=(
                            "El sistema externo respondió, pero los datos no cumplen "
                            "el contrato esperado."
                        ),
                        technical_message=str(exc.errors()),
                        correlation_id=correlation_id,
                        attempts=attempt,
                    )

                return ExternalSuccess(
                    ticket=ticket,
                    correlation_id=correlation_id,
                    attempts=attempt,
                )

            except httpx.TimeoutException as exc:
                last_error = ExternalError(
                    error_kind="timeout",
                    retryable=True,
                    user_message="El sistema externo no respondió dentro del tiempo máximo.",
                    technical_message=str(exc),
                    correlation_id=correlation_id,
                    attempts=attempt,
                )

                if attempt < self.max_attempts:
                    time.sleep(self.backoff_seconds * attempt)
                    continue

                return last_error

            except httpx.RequestError as exc:
                last_error = ExternalError(
                    error_kind="network",
                    retryable=True,
                    user_message="No se pudo conectar con el sistema externo.",
                    technical_message=str(exc),
                    correlation_id=correlation_id,
                    attempts=attempt,
                )

                if attempt < self.max_attempts:
                    time.sleep(self.backoff_seconds * attempt)
                    continue

                return last_error

        return last_error or ExternalError(
            error_kind="unknown",
            retryable=False,
            user_message="Error externo desconocido.",
            technical_message="No se obtuvo resultado.",
            correlation_id=correlation_id,
            attempts=self.max_attempts,
        )