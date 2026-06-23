from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import httpx
from azure.identity import AzureCliCredential
from pydantic import BaseModel, Field


class M365AutomationError(RuntimeError):
    pass


class M365ActionResult(BaseModel):
    ok: bool
    dry_run: bool
    action: str
    graph_path: str
    payload: dict[str, Any]
    graph_response: dict[str, Any] | None = None
    error: str | None = None


def parse_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "si", "sí"}


def validate_email(address: str) -> str:
    clean = address.strip().lower()

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
        raise M365AutomationError(f"Correo no válido: {address}")

    return clean


def parse_recipients(raw: str) -> list[str]:
    recipients = [
        validate_email(item)
        for item in raw.replace(";", ",").split(",")
        if item.strip()
    ]

    if not recipients:
        raise M365AutomationError("Debes indicar al menos un destinatario.")

    return recipients


@dataclass(frozen=True)
class M365AutomationClient:
    base_url: str
    dry_run: bool
    default_timezone: str
    timeout_seconds: float = 10.0

    @classmethod
    def from_env(cls) -> "M365AutomationClient":
        return cls(
            base_url=os.getenv(
                "GRAPH_BASE_URL",
                "https://graph.microsoft.com/v1.0",
            ).rstrip("/"),
            dry_run=parse_bool(os.getenv("M365_AUTOMATION_DRY_RUN"), default=True),
            default_timezone=os.getenv("M365_DEFAULT_TIMEZONE", "Europe/Madrid"),
        )

    def _access_token(self) -> str:
        credential = AzureCliCredential()
        token = credential.get_token("https://graph.microsoft.com/.default")
        return token.token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = httpx.post(
                f"{self.base_url}{path}",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise M365AutomationError("Timeout llamando a Microsoft Graph.") from exc
        except httpx.RequestError as exc:
            raise M365AutomationError(f"Error de red llamando a Graph: {exc}") from exc

        if response.status_code == 401:
            raise M365AutomationError(
                "No autorizado. Revisa az login y los permisos de Graph."
            )

        if response.status_code == 403:
            raise M365AutomationError(
                "Permiso denegado. La identidad no tiene permisos suficientes."
            )

        if response.status_code == 429:
            raise M365AutomationError(
                "Graph ha limitado temporalmente las llamadas. Reintenta más tarde."
            )

        if response.status_code >= 400:
            raise M365AutomationError(
                f"Error HTTP {response.status_code}: {response.text}"
            )

        if not response.text:
            return {}

        return response.json()

    def create_mail_draft(
        self,
        to: str,
        subject: str,
        body: str,
    ) -> M365ActionResult:
        recipients = parse_recipients(to)

        if len(subject.strip()) < 3:
            raise M365AutomationError("El asunto debe tener al menos 3 caracteres.")

        if len(body.strip()) < 10:
            raise M365AutomationError("El cuerpo debe tener al menos 10 caracteres.")

        payload = {
            "subject": subject.strip(),
            "body": {
                "contentType": "Text",
                "content": body.strip(),
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": recipient,
                    }
                }
                for recipient in recipients
            ],
        }

        path = "/me/messages"

        if self.dry_run:
            return M365ActionResult(
                ok=True,
                dry_run=True,
                action="create_mail_draft",
                graph_path=path,
                payload=payload,
            )

        try:
            response = self._post(path, payload)
            return M365ActionResult(
                ok=True,
                dry_run=False,
                action="create_mail_draft",
                graph_path=path,
                payload=payload,
                graph_response=response,
            )
        except M365AutomationError as exc:
            return M365ActionResult(
                ok=False,
                dry_run=False,
                action="create_mail_draft",
                graph_path=path,
                payload=payload,
                error=str(exc),
            )

    def create_calendar_event(
        self,
        subject: str,
        start_datetime: str,
        end_datetime: str,
        attendees: str,
        body: str = "",
        timezone: str | None = None,
    ) -> M365ActionResult:
        clean_subject = subject.strip()
        if len(clean_subject) < 3:
            raise M365AutomationError("El título del evento debe tener al menos 3 caracteres.")

        attendee_list = parse_recipients(attendees)
        effective_timezone = timezone or self.default_timezone

        payload = {
            "subject": clean_subject,
            "body": {
                "contentType": "Text",
                "content": body.strip() or "Evento creado desde automatización MAF.",
            },
            "start": {
                "dateTime": start_datetime,
                "timeZone": effective_timezone,
            },
            "end": {
                "dateTime": end_datetime,
                "timeZone": effective_timezone,
            },
            "attendees": [
                {
                    "emailAddress": {
                        "address": attendee,
                    },
                    "type": "required",
                }
                for attendee in attendee_list
            ],
        }

        path = "/me/events"

        if self.dry_run:
            return M365ActionResult(
                ok=True,
                dry_run=True,
                action="create_calendar_event",
                graph_path=path,
                payload=payload,
            )

        try:
            response = self._post(path, payload)
            return M365ActionResult(
                ok=True,
                dry_run=False,
                action="create_calendar_event",
                graph_path=path,
                payload=payload,
                graph_response=response,
            )
        except M365AutomationError as exc:
            return M365ActionResult(
                ok=False,
                dry_run=False,
                action="create_calendar_event",
                graph_path=path,
                payload=payload,
                error=str(exc),
            )