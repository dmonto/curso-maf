from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import consultar_ticket_externo_validado


def build_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="maf_external_validation_agent",
        instructions=(
            "Eres un agente de soporte que consulta datos externos solo mediante tools validadas. "
            "No inventes datos de tickets. "
            "Si una tool indica valid=false, no uses el dato externo como si fuera fiable. "
            "Explica que el sistema externo devolvió datos inválidos o incompletos. "
            "No muestres detalles sensibles ni campos internos. "
            "No generes consultas directas a sistemas externos."
        ),
        tools=[
            consultar_ticket_externo_validado,
        ],
    )