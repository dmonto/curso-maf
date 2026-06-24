from __future__ import annotations

from src.di.container import AppContainer, build_app_container
from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools.di_clean_arch_tools import build_report_and_classify_tool


def build_di_support_agent(container: AppContainer | None = None):
    settings = get_settings()
    app_container = container or build_app_container()

    client = create_chat_client(settings.default_chat_model)

    report_tool = build_report_and_classify_tool(app_container)

    instructions = """
Eres un agente de soporte técnico interno.

Tu responsabilidad:
- Entender incidencias de soporte.
- Pedir datos faltantes si falta servicio, resumen, usuarios afectados o impacto.
- Usar la tool report_and_classify_support_incident_di cuando haya datos suficientes.
- Explicar la clasificación de forma clara.

Límites:
- No inventes prioridad.
- No calcules reglas de escalado manualmente.
- No digas que se ha creado un ticket real.
- Si la tool devuelve correlation_id, inclúyelo en la respuesta.
"""

    return client.as_agent(
        name="maf_di_support_agent",
        instructions=instructions,
        tools=[
            report_tool,
        ],
    )