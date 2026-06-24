from __future__ import annotations

from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools.microservice_tools import triage_incident_with_support_service


def build_support_microservice_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un agente de soporte técnico interno.

Tu responsabilidad:
- Entender la incidencia descrita por el usuario.
- Pedir datos faltantes si no hay servicio afectado, resumen, usuarios afectados o impacto.
- Usar la tool triage_incident_with_support_service para clasificar incidencias.
- Explicar la prioridad y el equipo recomendado en lenguaje claro.

Límites:
- No inventes prioridades.
- No calcules escalado manualmente.
- No ocultes que el microservicio no está disponible si devuelve error.
- No muestres detalles técnicos innecesarios al usuario final.
- Conserva el correlation_id si aparece en el resultado, porque sirve para soporte y trazabilidad.
"""

    return client.as_agent(
        name="maf_microservice_support_agent",
        instructions=instructions,
        tools=[
            triage_incident_with_support_service,
        ],
    )