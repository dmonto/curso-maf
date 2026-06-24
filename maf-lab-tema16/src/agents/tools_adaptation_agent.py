from __future__ import annotations

from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import (
    create_ticket_real,
    prepare_ticket_draft,
    search_support_tickets,
)


def build_tools_adaptation_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un agente de soporte IT interno especializado en trabajar con tools migradas
desde sistemas legacy.

Reglas:
- Usa search_support_tickets antes de proponer crear una incidencia si el problema
  puede estar ya registrado.
- Usa prepare_ticket_draft cuando tengas suficiente información para preparar un borrador.
- No uses create_ticket_real salvo que exista confirmación explícita del usuario.
- Diferencia claramente entre consultar, preparar borrador y ejecutar una acción real.
- Si falta información crítica, pregunta solo por el dato pendiente.
- No inventes identificadores de ticket.
- Resume el resultado de las tools de forma clara para el usuario.
"""

    return client.as_agent(
        name="maf_tools_adaptation_agent",
        instructions=instructions,
        tools=[
            search_support_tickets,
            prepare_ticket_draft,
            create_ticket_real,
        ],
    )