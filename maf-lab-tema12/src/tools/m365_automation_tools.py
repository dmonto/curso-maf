from __future__ import annotations

from typing import Annotated

from agent_framework import tool
from pydantic import Field

from src.integrations.m365_automation_client import (
    M365AutomationClient,
    M365AutomationError,
)


@tool(
    name="crear_borrador_correo_m365",
    description=(
        "Crea o prepara un borrador de correo en Outlook mediante Microsoft Graph. "
        "Por defecto funciona en modo dry-run si M365_AUTOMATION_DRY_RUN=true. "
        "Úsala cuando el usuario quiera preparar una comunicación por email. "
        "No envía el correo."
    ),
)
def crear_borrador_correo_m365(
    to: Annotated[
        str,
        Field(description="Destinatarios separados por coma. Ejemplo: ana@empresa.com."),
    ],
    subject: Annotated[
        str,
        Field(description="Asunto del correo."),
    ],
    body: Annotated[
        str,
        Field(description="Cuerpo del correo."),
    ],
) -> dict:
    client = M365AutomationClient.from_env()

    try:
        result = client.create_mail_draft(
            to=to,
            subject=subject,
            body=body,
        )
        return result.model_dump()
    except M365AutomationError as exc:
        return {
            "ok": False,
            "dry_run": client.dry_run,
            "action": "create_mail_draft",
            "error": str(exc),
        }


@tool(
    name="crear_evento_calendario_m365",
    description=(
        "Crea o prepara un evento de calendario en Microsoft 365 mediante Graph. "
        "Por defecto funciona en modo dry-run si M365_AUTOMATION_DRY_RUN=true. "
        "Úsala cuando el usuario quiera agendar una reunión o seguimiento. "
        "Requiere título, inicio, fin y asistentes."
    ),
)
def crear_evento_calendario_m365(
    subject: Annotated[
        str,
        Field(description="Título de la reunión o evento."),
    ],
    start_datetime: Annotated[
        str,
        Field(description="Inicio en formato ISO local. Ejemplo: 2026-06-18T10:00:00."),
    ],
    end_datetime: Annotated[
        str,
        Field(description="Fin en formato ISO local. Ejemplo: 2026-06-18T10:30:00."),
    ],
    attendees: Annotated[
        str,
        Field(description="Asistentes separados por coma."),
    ],
    body: Annotated[
        str,
        Field(description="Descripción o agenda del evento."),
    ] = "",
    timezone: Annotated[
        str,
        Field(description="Zona horaria. Ejemplo: Europe/Madrid."),
    ] = "Europe/Madrid",
) -> dict:
    client = M365AutomationClient.from_env()

    try:
        result = client.create_calendar_event(
            subject=subject,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            attendees=attendees,
            body=body,
            timezone=timezone,
        )
        return result.model_dump()
    except M365AutomationError as exc:
        return {
            "ok": False,
            "dry_run": client.dry_run,
            "action": "create_calendar_event",
            "error": str(exc),
        }