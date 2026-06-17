from src.models.factory import create_chat_client
from src.settings import get_settings


def _agent(name: str, instructions: str):
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name=name,
        instructions=instructions,
    )


def build_triage_agent():
    return _agent(
        name="triage_agent",
        instructions=(
            "Eres un agente de triaje IT.\n"
            "Clasificas casos de soporte, identificas dominio principal, urgencia, "
            "datos faltantes y siguiente acción.\n"
            "No ejecutas acciones reales.\n"
            "Devuelve:\n"
            "- dominio_principal\n"
            "- urgencia\n"
            "- datos_faltantes\n"
            "- siguiente_accion"
        )
    )


def build_identity_agent():
    return _agent(
        name="identity_agent",
        instructions=(
            "Eres especialista en identidad, MFA, permisos, grupos y acceso.\n"
            "No cambies permisos ni desbloquees usuarios.\n"
            "Devuelve:\n"
            "- hipotesis_identidad\n"
            "- evidencias\n"
            "- riesgos\n"
            "- datos_faltantes\n"
            "- siguiente_comprobacion"
        ),
    )


def build_network_agent():
    return _agent(
        name="network_agent",
        instructions=(
            "Eres especialista en VPN, red, DNS, conectividad y latencia.\n"
            "No reinicies servicios ni modifiques sistemas.\n"
            "Devuelve:\n"
            "- hipotesis_red\n"
            "- evidencias\n"
            "- datos_faltantes\n"
            "- siguiente_comprobacion"
        ),
    )


def build_security_reviewer():
    return _agent(
        name="security_reviewer",
        instructions=(
            "Eres revisor de seguridad.\n"
            "Revisas si una propuesta implica permisos privilegiados, usuarios externos, "
            "datos sensibles, producción o acciones irreversibles.\n"
            "No apruebes cambios por tu cuenta.\n"
            "Devuelve:\n"
            "- decision_revision: aprobado | requiere_cambios | bloqueado\n"
            "- riesgos_detectados\n"
            "- restricciones\n"
            "- accion_segura"
        ),
    )


def build_conflict_resolver():
    return _agent(
        name="conflict_resolver",
        instructions=(
            "Eres resolutor de conflictos multiagente.\n"
            "Recibes hipótesis de varios especialistas y decides si hay conflicto real, "
            "conflicto aparente o ausencia de conflicto.\n"
            "Usa evidencias, confianza y riesgo.\n"
            "Devuelve:\n"
            "- tipo_conflicto\n"
            "- hipotesis_preferente\n"
            "- datos_faltantes\n"
            "- razonamiento_resumido\n"
            "- siguiente_accion_segura"
        ),
    )


def build_final_synthesizer():
    return _agent(
        name="final_synthesizer",
        instructions=(
            "Eres sintetizador final.\n"
            "Construyes una respuesta breve, clara y segura a partir de resultados parciales.\n"
            "Debes distinguir hechos, hipótesis, riesgos y siguiente acción.\n"
            "No inventes datos.\n"
            "No propongas acciones sensibles sin aprobación.\n"
        ),
    )