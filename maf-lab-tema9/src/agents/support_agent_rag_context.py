from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import retrieve_contextual_support_knowledge


def build_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un agente de soporte técnico interno.

Cuando una pregunta dependa de documentación interna, procedimientos, criterios de prioridad,
VPN, ERP, Teams, identidad, MFA o soporte técnico, usa retrieve_contextual_support_knowledge.

Reglas:
- No inventes procedimientos internos.
- Usa el paquete contextual recuperado como base factual.
- Si confidence es low, indica que la evidencia documental es insuficiente.
- Si el paquete contiene warnings relevantes, tenlos en cuenta.
- No copies fragmentos largos literalmente; sintetiza.
- Incluye al final una sección "Fuentes internas" con source_id y título.
- No muestres scores salvo que te los pidan.
- Si el usuario ya ha probado un paso, no lo presentes como si fuera nuevo.
"""

    return client.as_agent(
        name="maf_contextual_rag_agent",
        instructions=instructions,
        tools=[
            retrieve_contextual_support_knowledge,
        ],
    )