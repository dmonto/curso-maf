from __future__ import annotations

from src.di.container import AppContainer, build_app_container
from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools.contract_tools import build_contract_report_tool


def build_contract_support_agent(container: AppContainer | None = None):
    settings = get_settings()
    app_container = container or build_app_container()

    client = create_chat_client(settings.default_chat_model)

    report_tool = build_contract_report_tool(app_container)

    instructions = """
Eres un agente de soporte técnico interno.

Tu responsabilidad:
- Entender incidencias de soporte.
- Pedir datos faltantes si falta servicio, resumen, usuarios afectados o impacto.
- Usar la tool report_incident_with_contracts cuando haya datos suficientes.
- Explicar la clasificación de forma clara.

Límites:
- No inventes prioridad.
- No calcules reglas de escalado manualmente.
- No digas que se ha creado un ticket real.
- Si la tool devuelve un error de contrato, explica qué dato falta o qué dato no es válido.
- Si la tool devuelve correlation_id, inclúyelo en la respuesta.
"""

    return client.as_agent(
        name="maf_contract_support_agent",
        instructions=instructions,
        tools=[
            report_tool,
        ],
    )