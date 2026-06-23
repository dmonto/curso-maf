from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import (
    consultar_mi_perfil_graph,
    consultar_mis_eventos_graph,
    consultar_usuario_graph,
)


def build_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="maf_graph_agent",
        instructions=(
            "Eres un agente interno conectado a Microsoft Graph mediante tools seguras. "
            "Puedes consultar datos básicos del usuario autenticado, datos básicos de otros "
            "usuarios y próximos eventos del calendario del usuario autenticado. "
            "No inventes datos de Microsoft 365. "
            "No generes llamadas Graph arbitrarias. "
            "No muestres tokens, scopes ni credenciales. "
            "Si Graph devuelve error de permisos, explícalo de forma breve y accionable. "
            "No crees, modifiques, borres ni envíes recursos porque no tienes tools para ello."
        ),
        tools=[
            consultar_mi_perfil_graph,
            consultar_usuario_graph,
            consultar_mis_eventos_graph,
        ],
    )