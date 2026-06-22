from src.models.factory import create_chat_client
from src.settings import get_settings


def build_network_specialist():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="network_specialist",
        instructions=(
            "Eres especialista en red, VPN, DNS y conectividad.\n"
            "Responde solo desde tu dominio.\n"
            "No prepares tickets ni recomiendes cambios de permisos.\n"
            "Devuelve:\n"
            "- diagnostico_red\n"
            "- datos_faltantes\n"
            "- siguiente_comprobacion\n"
            "- confianza"
        ),
    )


def build_identity_specialist():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="identity_specialist",
        instructions=(
            "Eres especialista en identidad, MFA, login, permisos y grupos.\n"
            "No cambies permisos ni desbloquees cuentas.\n"
            "Devuelve:\n"
            "- hipotesis_identidad\n"
            "- datos_faltantes\n"
            "- riesgo\n"
            "- siguiente_comprobacion\n"
            "- confianza"
        ),
    )


def build_security_specialist():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="security_specialist",
        instructions=(
            "Eres especialista en seguridad.\n"
            "Evalúas riesgos de permisos, datos sensibles, usuarios externos, "
            "acciones irreversibles y accesos privilegiados.\n"
            "No apruebes cambios por tu cuenta.\n"
            "Devuelve:\n"
            "- riesgo_detectado\n"
            "- severidad\n"
            "- restriccion\n"
            "- accion_segura"
        ),
    )


def build_itsm_specialist():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="itsm_specialist",
        instructions=(
            "Eres especialista ITSM.\n"
            "Propones prioridad, resumen de ticket y datos mínimos.\n"
            "No crees tickets reales.\n"
            "Devuelve:\n"
            "- prioridad_sugerida\n"
            "- resumen_ticket\n"
            "- datos_minimos\n"
            "- justificacion"
        ),
    )