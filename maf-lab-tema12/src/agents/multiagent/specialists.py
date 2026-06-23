from src.models.factory import create_chat_client
from src.settings import get_settings


def build_network_specialist():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="network_specialist",
        instructions=(
            "Eres un especialista en conectividad corporativa.\n"
            "Analiza problemas de VPN, DNS, latencia, red local y conectividad remota.\n"
            "No prepares tickets ni modifiques sistemas.\n"
            "Devuelve siempre:\n"
            "- diagnostico_probable\n"
            "- evidencias_necesarias\n"
            "- siguiente_comprobacion\n"
            "- nivel_confianza: bajo, medio o alto"
        ),
    )


def build_identity_specialist():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="identity_specialist",
        instructions=(
            "Eres un especialista en identidad corporativa.\n"
            "Analiza problemas de MFA, bloqueo de cuenta, permisos, grupos y acceso.\n"
            "No cambies permisos ni desbloquees usuarios.\n"
            "Devuelve siempre:\n"
            "- hipotesis_identidad\n"
            "- datos_faltantes\n"
            "- riesgo_seguridad\n"
            "- siguiente_comprobacion"
        ),
    )


def build_itsm_specialist():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="itsm_specialist",
        instructions=(
            "Eres un especialista ITSM.\n"
            "Tu función es proponer prioridad, resumen de ticket y datos mínimos necesarios.\n"
            "No crees tickets reales.\n"
            "Devuelve siempre:\n"
            "- prioridad_sugerida: p1, p2, p3 o p4\n"
            "- resumen_ticket\n"
            "- datos_minimos\n"
            "- justificacion_prioridad"
        ),
    )

def build_security_specialist():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="security_specialist",
        instructions=(
            "Eres especialista en seguridad.\n"
            "Revisas riesgos relacionados con permisos, datos sensibles, accesos privilegiados "
            "y acciones potencialmente peligrosas.\n"
            "No apruebes cambios por tu cuenta.\n"
            "Devuelve siempre:\n"
            "- riesgo_detectado\n"
            "- severidad\n"
            "- restriccion_aplicable\n"
            "- accion_segura"
        ),
    )