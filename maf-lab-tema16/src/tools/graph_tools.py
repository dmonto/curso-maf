from __future__ import annotations

from typing import Annotated

from agent_framework import tool
from pydantic import Field

from src.integrations.graph_client import GraphClient, GraphIntegrationError


@tool(
    name="consultar_mi_perfil_graph",
    description=(
        "Consulta el perfil básico del usuario autenticado en Microsoft Graph. "
        "Úsala cuando el usuario pregunte quién es, con qué cuenta está autenticado "
        "o qué datos básicos tiene su perfil. No modifica datos."
    ),
)
def consultar_mi_perfil_graph() -> dict:
    client = GraphClient.from_env()

    try:
        user = client.get_me()
        return {
            "ok": True,
            "user": user.model_dump(),
        }
    except GraphIntegrationError as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


@tool(
    name="consultar_usuario_graph",
    description=(
        "Consulta datos básicos de un usuario por UPN en Microsoft Graph. "
        "Úsala solo cuando el usuario proporcione una dirección corporativa concreta. "
        "No devuelve datos sensibles ni modifica datos."
    ),
)
def consultar_usuario_graph(
    upn: Annotated[
        str,
        Field(description="UPN o correo corporativo del usuario. Ejemplo: ana@empresa.com."),
    ],
) -> dict:
    client = GraphClient.from_env()

    try:
        user = client.get_user_by_upn(upn)
        return {
            "ok": True,
            "user": user.model_dump(),
        }
    except GraphIntegrationError as exc:
        return {
            "ok": False,
            "upn": upn,
            "error": str(exc),
        }


@tool(
    name="consultar_mis_eventos_graph",
    description=(
        "Consulta próximos eventos del calendario del usuario autenticado mediante Graph. "
        "Úsala cuando el usuario pregunte por su agenda o próximos eventos. "
        "Limita la consulta a un máximo de 30 días y 25 eventos. No crea ni modifica eventos."
    ),
)
def consultar_mis_eventos_graph(
    days: Annotated[
        int,
        Field(description="Número de días hacia adelante. Mínimo 1, máximo 30."),
    ] = 7,
    limit: Annotated[
        int,
        Field(description="Número máximo de eventos. Mínimo 1, máximo 25."),
    ] = 10,
) -> dict:
    client = GraphClient.from_env()

    try:
        events = client.get_my_upcoming_events(days=days, limit=limit)
        return {
            "ok": True,
            "count": len(events),
            "events": [event.model_dump() for event in events],
        }
    except GraphIntegrationError as exc:
        return {
            "ok": False,
            "error": str(exc),
        }