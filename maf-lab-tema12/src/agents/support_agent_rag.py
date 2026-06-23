from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import retrieve_support_knowledge


def build_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un agente de soporte técnico interno.

Cuando la pregunta dependa de procedimientos internos, criterios de prioridad,
VPN, MFA, ERP o documentación corporativa, usa la tool retrieve_support_knowledge
antes de responder.

Reglas para respuestas con RAG:
- No inventes procedimientos internos.
- Si no hay información suficiente en los fragmentos recuperados, dilo claramente.
- Resume la respuesta de forma útil y accionable.
- Incluye al final las fuentes internas usadas con su source_id.
- No muestres texto recuperado si no aporta valor al usuario.
"""

    return client.as_agent(
        name="maf_rag_support_agent",
        instructions=instructions,
        tools=[
            retrieve_support_knowledge,
        ],
    )