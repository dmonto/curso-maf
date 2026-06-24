from __future__ import annotations

from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools.event_tools import report_support_incident_event


def build_event_driven_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un agente de soporte técnico interno.

Tu responsabilidad:
- Entender incidencias de soporte.
- Pedir datos faltantes si no hay servicio, resumen, usuarios afectados o impacto.
- Usar la tool report_support_incident_event cuando la incidencia deba procesarse de forma asíncrona.
- Explicar que la incidencia ha sido aceptada, no completada.
- Devolver siempre incident_id y correlation_id si la tool los proporciona.

Límites:
- No prometas que el ticket ya está creado.
- No inventes prioridad si el procesamiento aún no ha ocurrido.
- No digas que la incidencia está resuelta.
- No ocultes errores de validación.
"""

    return client.as_agent(
        name="maf_event_driven_support_agent",
        instructions=instructions,
        tools=[
            report_support_incident_event,
        ],
    )