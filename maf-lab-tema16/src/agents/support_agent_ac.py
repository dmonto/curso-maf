from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import (
    cambiar_prioridad_ticket_con_acceso,
    consultar_ticket_con_acceso,
    resumen_global_tickets_con_acceso,
)


def build_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="maf_access_control_agent",
        instructions=(
            "Eres un agente interno de soporte con control de acceso aplicado en tools. "
            "No debes prometer acciones si la tool las deniega. "
            "No inventes permisos. "
            "Si una tool devuelve allowed=false, explica de forma breve que la acción "
            "no está permitida y muestra la razón devuelta. "
            "No pidas al usuario que indique su rol: el rol se obtiene del contexto autenticado. "
            "No intentes saltarte las políticas de autorización."
        ),
        tools=[
            consultar_ticket_con_acceso,
            cambiar_prioridad_ticket_con_acceso,
            resumen_global_tickets_con_acceso,
        ],
    )