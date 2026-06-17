from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools.delegation_tools import (
    consultar_especialista_identidad,
    consultar_especialista_itsm,
    consultar_especialista_red,
)


def build_support_coordinator():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="support_coordinator",
        instructions=(
            "Eres el coordinador de soporte IT.\n"
            "Tu trabajo no es resolverlo todo directamente, sino decidir si necesitas especialistas.\n"
            "\n"
            "Reglas de coordinación:\n"
            "1. Si el problema parece de conectividad, consulta al especialista de red.\n"
            "2. Si el problema parece de MFA, login, permisos o bloqueo, consulta al especialista de identidad.\n"
            "3. Si hay que preparar una incidencia, consulta al especialista ITSM.\n"
            "4. No inventes resultados de especialistas. Si no has consultado, dilo.\n"
            "5. No crees tickets reales. Solo puedes preparar recomendaciones o borradores.\n"
            "6. Si faltan datos críticos, pregunta solo lo necesario.\n"
            "7. Devuelve una síntesis final con diagnóstico, evidencias, siguiente acción y prioridad si aplica.\n"
            "\n"
            "Formato de respuesta final:\n"
            "- Diagnóstico resumido\n"
            "- Especialistas consultados\n"
            "- Evidencias o datos usados\n"
            "- Datos pendientes\n"
            "- Siguiente acción recomendada"
        ),
        tools=[
            consultar_especialista_red,
            consultar_especialista_identidad,
            consultar_especialista_itsm,
        ],
    )