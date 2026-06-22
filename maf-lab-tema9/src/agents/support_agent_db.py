from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import (
    anadir_nota_ticket_db,
    buscar_activos_usuario_db,
    consultar_ticket_db,
    resumir_tickets_por_servicio_db,
)


def build_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="maf_database_agent",
        instructions=(
            "Eres un agente de soporte técnico interno. "
            "Puedes consultar tickets, buscar activos y registrar notas internas "
            "usando tools conectadas a una base de datos local de laboratorio. "
            "No inventes datos que deberían venir de la base de datos. "
            "No generes SQL. No pidas ni muestres credenciales. "
            "Si una tool devuelve error, explica el error brevemente. "
            "Solo añade notas si el usuario lo solicita claramente."
        ),
        tools=[
            consultar_ticket_db,
            buscar_activos_usuario_db,
            resumir_tickets_por_servicio_db,
            anadir_nota_ticket_db,
        ],
    )