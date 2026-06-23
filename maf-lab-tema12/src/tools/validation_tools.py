from __future__ import annotations

from typing import Annotated

from agent_framework import tool
from pydantic import Field

from src.integrations.external_ticket_client import (
    ExternalDataValidationError,
    ExternalTicketClient,
    ExternalTicketError,
)


@tool(
    name="consultar_ticket_externo_validado",
    description=(
        "Consulta un ticket en una API externa y valida estrictamente la respuesta "
        "antes de entregarla al agente. Úsala cuando el usuario pregunte por un ticket "
        "de soporte externo. No modifica datos."
    ),
)
def consultar_ticket_externo_validado(
    ticket_id: Annotated[
        str,
        Field(description="Identificador del ticket externo. Ejemplo: INC-1001."),
    ],
) -> dict:
    client = ExternalTicketClient.from_env()

    try:
        ticket = client.get_validated_ticket(ticket_id)
        return {
            "ok": True,
            "valid": True,
            "ticket": ticket.model_dump(mode="json"),
        }

    except ExternalDataValidationError as exc:
        return {
            "ok": False,
            "valid": False,
            "error_type": "validation_error",
            "message": str(exc),
            "safe_response": (
                "El sistema externo respondió, pero los datos no cumplen "
                "el contrato esperado."
            ),
        }

    except ExternalTicketError as exc:
        return {
            "ok": False,
            "valid": False,
            "error_type": "external_system_error",
            "message": str(exc),
        }