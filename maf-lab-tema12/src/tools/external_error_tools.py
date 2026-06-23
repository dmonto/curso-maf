from __future__ import annotations

from typing import Annotated

from agent_framework import tool
from pydantic import Field

from src.integrations.unstable_ticket_client import UnstableTicketClient


@tool(
    name="consultar_ticket_con_gestion_errores",
    description=(
        "Consulta un ticket en una API externa inestable aplicando timeout, "
        "reintentos y clasificación de errores. Úsala cuando el usuario pregunte "
        "por el estado de un ticket externo. No modifica datos."
    ),
)
def consultar_ticket_con_gestion_errores(
    ticket_id: Annotated[
        str,
        Field(description="Identificador del ticket. Ejemplos: INC-1001, INC-500, INC-404."),
    ],
) -> dict:
    client = UnstableTicketClient.from_env()
    result = client.get_ticket(ticket_id)

    payload = result.model_dump(mode="json")

    if not payload["ok"]:
        # No devolvemos technical_message al usuario final como texto principal.
        # Sí lo dejamos estructurado para diagnóstico controlado.
        return {
            "ok": False,
            "error_kind": payload["error_kind"],
            "retryable": payload["retryable"],
            "user_message": payload["user_message"],
            "correlation_id": payload["correlation_id"],
            "attempts": payload["attempts"],
        }

    return payload