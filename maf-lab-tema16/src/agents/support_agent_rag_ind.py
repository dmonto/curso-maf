from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import search_indexed_support_documents


def build_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un agente de soporte técnico interno.

Cuando la pregunta dependa de procedimientos internos, criterios de prioridad,
VPN, ERP o documentación corporativa, usa la tool search_indexed_support_documents.

Reglas:
- No inventes procedimientos internos.
- Responde solo con la información recuperada o indica que no hay evidencia suficiente.
- Si usas documentos recuperados, incluye al final una sección "Fuentes internas".
- En "Fuentes internas", muestra source_id y título.
- No muestres scores al usuario salvo que te lo pidan.
- Si la información recuperada es parcial, dilo claramente.
"""

    return client.as_agent(
        name="maf_indexed_rag_agent",
        instructions=instructions,
        tools=[
            search_indexed_support_documents,
        ],
    )