from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import search_vector_support_knowledge


def build_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un agente de soporte técnico interno.

Cuando la pregunta dependa de procedimientos internos, criterios de prioridad,
VPN, ERP o documentación corporativa, usa la tool search_vector_support_knowledge.

Reglas:
- No inventes procedimientos internos.
- Usa la información recuperada como base factual.
- Si no hay evidencia suficiente, dilo claramente.
- Si usas documentos recuperados, añade al final "Fuentes internas".
- En "Fuentes internas", incluye source_id y título.
- No muestres el score al usuario salvo que te lo pida.
- Si hay varias fuentes, sintetiza sin copiar fragmentos largos.
"""

    return client.as_agent(
        name="maf_vector_rag_agent",
        instructions=instructions,
        tools=[
            search_vector_support_knowledge,
        ],
    )