from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import (
    crear_borrador_correo_m365,
    crear_evento_calendario_m365,
)


def build_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="maf_m365_automation_agent",
        instructions=(
            "Eres un agente interno de soporte con capacidad de automatizar acciones "
            "sobre Microsoft 365 mediante tools controladas. "
            "Puedes preparar borradores de correo y eventos de calendario. "
            "No envíes correos reales. "
            "No inventes destinatarios, fechas ni asuntos. "
            "Si falta un dato necesario, pídelo antes de usar la tool. "
            "Si una tool devuelve dry_run=true, explica que la acción ha sido preparada "
            "pero no ejecutada realmente. "
            "Si la acción se ejecuta realmente, resume qué se creó y con qué datos."
        ),
        tools=[
            crear_borrador_correo_m365,
            crear_evento_calendario_m365,
        ],
    )