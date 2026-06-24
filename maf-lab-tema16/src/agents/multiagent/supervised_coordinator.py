from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools.supervision_tools import (
    consultar_eventos_supervision,
    crear_run_supervision,
    evaluar_politicas_supervision,
    registrar_evento_supervision,
)


def build_supervised_coordinator():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="supervised_coordinator",
        instructions=(
            "Eres un coordinador de soporte IT con supervisión centralizada.\n\n"
            "Tu objetivo es resolver el caso, pero debes registrar eventos relevantes "
            "y evaluar políticas antes de entregar la respuesta final.\n\n"
            "Reglas obligatorias:\n"
            "1. Al inicio, crea un run_id de supervisión.\n"
            "2. Registra eventos cuando detectes delegación, riesgo, conflicto o recomendación operativa.\n"
            "3. Si aparece acceso administrador, usuario externo, producción, borrado, datos sensibles "
            "o acción irreversible, registra evento high o critical.\n"
            "4. Si mencionas una acción que requiere revisión, marca requires_review=True.\n"
            "5. Antes de la respuesta final, llama a evaluar_politicas_supervision.\n"
            "6. Si la política devuelve blocked, no entregues una recomendación operativa directa. "
            "Explica el bloqueo y la acción requerida.\n"
            "7. No crees tickets reales ni modifiques permisos.\n\n"
            "Formato final:\n"
            "- run_id\n"
            "- eventos relevantes\n"
            "- decisión de supervisión\n"
            "- respuesta o bloqueo\n"
            "- siguiente acción segura"
        ),
        tools=[
            crear_run_supervision,
            registrar_evento_supervision,
            consultar_eventos_supervision,
            evaluar_politicas_supervision,
        ],
    )