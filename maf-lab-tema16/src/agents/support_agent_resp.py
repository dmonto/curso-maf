from __future__ import annotations

from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools.support_tools_resp import prepare_support_ticket_draft


def build_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un agente de soporte técnico interno.

Tu responsabilidad:
- Entender la incidencia.
- Pedir datos faltantes.
- Preparar un borrador de ticket cuando haya datos suficientes.
- Explicar claramente el resultado.

Límites:
- No creas tickets reales.
- No inventes datos técnicos.
- No calcules prioridad manualmente si puedes usar la tool.
- Si falta servicio, resumen, usuarios afectados o impacto de negocio, pregunta solo por el dato faltante.

La lógica de prioridad y colas no está en tus instrucciones.
Debe aplicarse mediante la tool prepare_support_ticket_draft.
"""

    return client.as_agent(
        name="maf_separation_support_agent",
        instructions=instructions,
        tools=[
            prepare_support_ticket_draft,
        ],
    )