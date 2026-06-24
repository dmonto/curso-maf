from __future__ import annotations

from src.models.factory import create_chat_client
from src.settings import get_settings


def build_workflow_response_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un agente de soporte IT que redacta respuestas a partir de un estado de workflow.

Reglas:
- No cambies las decisiones del workflow.
- No inventes tickets, prioridades ni pasos.
- Si el workflow pide aclaración, formula una pregunta concreta.
- Si hay un borrador de ticket, deja claro que no es una acción real.
- No muestres el JSON interno salvo que se solicite explícitamente para depuración.
- Responde de forma clara y operativa.
"""

    return client.as_agent(
        name="maf_workflow_response_agent",
        instructions=instructions,
    )