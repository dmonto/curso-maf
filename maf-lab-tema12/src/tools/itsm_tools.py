from __future__ import annotations

from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from src.integrations.itsm_client import ItsmClient, ItsmIntegrationError


@tool(
    name="consultar_ticket_soporte",
    description=(
        "Consulta un ticket de soporte en la API ITSM del laboratorio. "
        "Úsala cuando el usuario pregunte por el estado, prioridad, servicio "
        "o resumen de una incidencia existente. No modifica sistemas externos."
    ),
)
def consultar_ticket_soporte(
    ticket_id: Annotated[
        str,
        Field(description="Identificador del ticket. Ejemplo: INC-1001."),
    ],
) -> dict:
    client = ItsmClient.from_env()

    try:
        ticket = client.get_ticket(ticket_id)
        return {
            "ok": True,
            "ticket": ticket.model_dump(),
        }
    except ItsmIntegrationError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "ticket_id": ticket_id,
        }


@tool(
    name="crear_ticket_soporte_lab",
    description=(
        "Crea un ticket de soporte en la API ITSM del laboratorio. "
        "Úsala solo cuando el usuario haya pedido claramente crear una incidencia. "
        "No debe usarse para borrar, cerrar ni modificar tickets existentes."
    ),
)
def crear_ticket_soporte_lab(
    service: Annotated[
        str,
        Field(description="Servicio afectado. Ejemplos: vpn, correo, erp, teams."),
    ],
    summary: Annotated[
        str,
        Field(description="Resumen breve y concreto de la incidencia."),
    ],
    priority: Annotated[
        Literal["p1", "p2", "p3", "p4"],
        Field(description="Prioridad de la incidencia. Valores permitidos: p1, p2, p3, p4."),
    ],
) -> dict:
    client = ItsmClient.from_env()

    try:
        ticket = client.create_ticket(
            service=service,
            summary=summary,
            priority=priority,
        )
        return {
            "ok": True,
            "created": True,
            "ticket": ticket.model_dump(),
        }
    except ItsmIntegrationError as exc:
        return {
            "ok": False,
            "created": False,
            "error": str(exc),
        }