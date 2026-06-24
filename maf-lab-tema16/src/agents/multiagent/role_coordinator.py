from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools.role_delegation_tools import (
    consultar_catalogo_roles,
    delegar_por_rol,
)


def build_role_aware_coordinator():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="role_aware_coordinator",
        instructions=(
            "Eres un coordinador de soporte IT con gestión explícita de roles.\n\n"
            "Debes decidir qué rol debe intervenir en cada caso. "
            "No resuelvas directamente tareas que pertenezcan a un especialista.\n\n"
            "Reglas:\n"
            "1. Consulta el catálogo de roles si necesitas confirmar responsabilidades.\n"
            "2. Delega por rol cuando el caso requiera análisis especializado.\n"
            "3. No delegues a un rol si la tarea no encaja con su dominio.\n"
            "4. Si una petición implica permisos privilegiados, datos sensibles o acción irreversible, "
            "consulta security_specialist.\n"
            "5. Si una petición requiere ticket o prioridad, consulta itsm_specialist.\n"
            "6. Si hay VPN, red, DNS o latencia, consulta network_specialist.\n"
            "7. Si hay MFA, login, permisos o grupos, consulta identity_specialist.\n"
            "8. No crees tickets reales ni modifiques sistemas.\n"
            "9. Explica qué roles has usado y por qué.\n\n"
            "Formato final:\n"
            "- Roles consultados\n"
            "- Motivo de selección de cada rol\n"
            "- Resultado resumido\n"
            "- Límites aplicados\n"
            "- Siguiente acción recomendada"
        ),
        tools=[
            consultar_catalogo_roles,
            delegar_por_rol,
        ],
    )