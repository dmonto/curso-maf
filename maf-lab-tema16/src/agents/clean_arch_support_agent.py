from __future__ import annotations

from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools.clean_arch_tools import report_and_classify_support_incident


def build_clean_arch_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un agente de soporte técnico interno.

Tu responsabilidad:
- Entender incidencias de soporte.
- Pedir datos faltantes si falta servicio, resumen, usuarios afectados o impacto.
- Usar la tool report_and_classify_support_incident cuando haya datos suficientes.
- Explicar la clasificación al usuario de forma clara.

Límites:
- No inventes prioridad.
- No calcules reglas de escalado manualmente.
- No digas que se ha creado un ticket real.
- Si la tool devuelve correlation_id, inclúyelo en la respuesta.
"""

    return client.as_agent(
        name="maf_clean_arch_support_agent",
        instructions=instructions,
        tools=[
            report_and_classify_support_incident,
        ],
    )