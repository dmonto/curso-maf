from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import consultar_ticket_soporte, crear_ticket_soporte_lab


def build_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="maf_rest_api_agent",
        instructions=(
            "Eres un agente de soporte técnico interno. "
            "Puedes consultar y crear tickets en la API ITSM del laboratorio mediante tools. "
            "No inventes tickets. Si una tool devuelve error, explícalo de forma breve. "
            "Antes de crear tickets, comprueba que tienes servicio, resumen y prioridad. "
            "No cierres, borres ni modifiques tickets porque no tienes tools para ello."
        ),
        tools=[
            consultar_ticket_soporte,
            crear_ticket_soporte_lab,
        ],
    )