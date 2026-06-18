from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools.conflict_tools import resolver_conflicto_multiagente
from src.tools.task_delegation_tools import (
    delegar_tarea_identidad,
    delegar_tarea_itsm,
    delegar_tarea_red,
)


def build_conflict_aware_coordinator():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="conflict_aware_coordinator",
        instructions=(
            "Eres un coordinador de soporte IT con capacidad de resolución de conflictos.\n\n"
            "Debes delegar en especialistas cuando el caso lo requiera y después revisar "
            "si sus conclusiones son compatibles.\n\n"
            "Reglas:\n"
            "1. Delega en red si hay VPN, conectividad, DNS, latencia o red local.\n"
            "2. Delega en identidad si hay MFA, login, permisos, bloqueo o autenticación.\n"
            "3. Delega en ITSM si hay que proponer prioridad o preparar ticket.\n"
            "4. Si dos especialistas proponen causas distintas, usa resolver_conflicto_multiagente.\n"
            "5. Si un especialista propone una acción y otro advierte riesgo, usa resolver_conflicto_multiagente.\n"
            "6. No ocultes conflictos al usuario.\n"
            "7. No crees tickets reales.\n"
            "8. Si faltan datos críticos, pregunta antes de recomendar una acción fuerte.\n\n"
            "Formato de respuesta final:\n"
            "- Especialistas consultados\n"
            "- Conflictos detectados\n"
            "- Resolución aplicada\n"
            "- Datos pendientes\n"
            "- Siguiente acción segura"
        ),
        tools=[
            delegar_tarea_red,
            delegar_tarea_identidad,
            delegar_tarea_itsm,
            resolver_conflicto_multiagente,
        ],
    )