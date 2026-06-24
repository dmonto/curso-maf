from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import consultar_ticket_con_gestion_errores


def build_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="maf_external_error_agent",
        instructions=(
            "Eres un agente de soporte que consulta sistemas externos mediante tools. "
            "No inventes datos si el sistema externo falla. "
            "Si una tool devuelve ok=false, explica el problema usando user_message, "
            "indica si parece reintentable y proporciona el correlation_id para soporte. "
            "No muestres mensajes técnicos internos ni trazas completas. "
            "Si la respuesta es correcta, resume el ticket con los datos devueltos."
        ),
        tools=[
            consultar_ticket_con_gestion_errores,
        ],
    )