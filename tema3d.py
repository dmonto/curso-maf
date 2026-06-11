import asyncio
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass
from typing import Annotated, Literal

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential
from pydantic import Field


# ---------------------------------------------------------------------
# 1. Estado de interacción
# ---------------------------------------------------------------------

@dataclass
class InteractionState:
    session_id: str
    service: str | None = None
    description: str | None = None
    impact: str | None = None
    users_affected: int | None = None
    priority: str | None = None
    pending_action: str | None = None
    action_confirmed: bool = False
    action_rejected: bool = False
    ticket_draft_id: str | None = None
    phase: str = "waiting_input"


STATE = InteractionState(session_id=str(uuid.uuid4()))


# ---------------------------------------------------------------------
# 2. Utilidades
# ---------------------------------------------------------------------

def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")
    return value


def detect_sensitive_or_blocked_request(text: str) -> str | None:
    blocked_terms = [
        "borrar",
        "eliminar",
        "desactivar usuario",
        "cambiar permisos",
        "crear ticket real",
        "ejecuta powershell",
        "dame credenciales",
    ]

    normalized = text.lower()

    for term in blocked_terms:
        if term in normalized:
            return f"Petición bloqueada por política: '{term}'"

    return None


def update_state_from_user_message(text: str) -> None:
    """
    Parser didáctico para laboratorio.
    En producción, esta extracción puede hacerse con structured output,
    un workflow o una tool de extracción validada.
    """
    normalized = text.lower().strip()

    if not STATE.description and len(text) > 10:
        STATE.description = text

    if "vpn" in normalized:
        STATE.service = "vpn"
    elif "correo" in normalized or "outlook" in normalized or "email" in normalized:
        STATE.service = "correo"
    elif "teams" in normalized:
        STATE.service = "teams"
    elif "erp" in normalized:
        STATE.service = "erp"

    if "impacto alto" in normalized or "urgente" in normalized:
        STATE.impact = "alto"
    elif "impacto medio" in normalized:
        STATE.impact = "medio"
    elif "impacto bajo" in normalized or "no es urgente" in normalized:
        STATE.impact = "bajo"

    if "solo a mí" in normalized or "solo a mi" in normalized:
        STATE.users_affected = 1

    match = re.search(r"(\d+)\s+(usuarios|personas|compañeros|companeros)", normalized)
    if match:
        STATE.users_affected = int(match.group(1))

    if STATE.impact and STATE.users_affected is not None:
        if STATE.impact == "alto" or STATE.users_affected > 10:
            STATE.priority = "alta"
        elif STATE.impact == "medio" or STATE.users_affected > 1:
            STATE.priority = "media"
        else:
            STATE.priority = "baja"

    if STATE.pending_action:
        if normalized in {"si", "sí", "confirmo", "adelante", "ok", "hazlo"}:
            STATE.action_confirmed = True
            STATE.action_rejected = False
        elif normalized in {"no", "cancela", "cancelar", "no lo hagas"}:
            STATE.action_confirmed = False
            STATE.action_rejected = True


def missing_fields() -> list[str]:
    missing: list[str] = []

    if not STATE.service:
        missing.append("service")
    if not STATE.description:
        missing.append("description")
    if not STATE.impact:
        missing.append("impact")
    if STATE.users_affected is None:
        missing.append("users_affected")
    if not STATE.priority:
        missing.append("priority")

    return missing


def build_agent_input(user_message: str) -> str:
    """
    Inyectamos estado como contexto textual controlado para la demo.
    En una arquitectura más avanzada se usaría un context provider o un store de sesión.
    """
    return (
        "Estado actual de la interacción:\n"
        f"{json.dumps(asdict(STATE), ensure_ascii=False, indent=2)}\n\n"
        "Mensaje del usuario:\n"
        f"{user_message}"
    )


# ---------------------------------------------------------------------
# 3. Tools de interacción
# ---------------------------------------------------------------------

@tool(
    name="leer_estado_interaccion",
    description=(
        "Devuelve el estado actual de la interacción con el usuario, incluyendo datos "
        "recopilados, campos pendientes, acción pendiente y confirmación."
    ),
    approval_mode="never_require",
)
def leer_estado_interaccion() -> str:
    return json.dumps(
        {
            "state": asdict(STATE),
            "missing_fields": missing_fields(),
        },
        ensure_ascii=False,
    )


@tool(
    name="solicitar_confirmacion_borrador",
    description=(
        "Solicita confirmación al usuario antes de preparar un borrador de ticket. "
        "No prepara el borrador; solo deja la acción pendiente."
    ),
    approval_mode="never_require",
)
def solicitar_confirmacion_borrador() -> str:
    pending = missing_fields()

    if pending:
        return json.dumps(
            {
                "can_request_confirmation": False,
                "missing_fields": pending,
                "message": "No se puede solicitar confirmación porque faltan datos.",
            },
            ensure_ascii=False,
        )

    STATE.pending_action = "prepare_ticket_draft"
    STATE.phase = "waiting_confirmation"
    STATE.action_confirmed = False
    STATE.action_rejected = False

    return json.dumps(
        {
            "can_request_confirmation": True,
            "pending_action": STATE.pending_action,
            "confirmation_message": (
                "Tengo datos suficientes para preparar un borrador de ticket. "
                "No se creará ningún ticket real. ¿Confirmas que quieres preparar el borrador?"
            ),
            "summary": {
                "service": STATE.service,
                "description": STATE.description,
                "impact": STATE.impact,
                "users_affected": STATE.users_affected,
                "priority": STATE.priority,
            },
        },
        ensure_ascii=False,
    )


@tool(
    name="preparar_borrador_ticket",
    description=(
        "Prepara un borrador de ticket solo si el usuario ha confirmado explícitamente "
        "la acción pendiente. No crea tickets reales."
    ),
    approval_mode="never_require",
)
def preparar_borrador_ticket() -> str:
    pending = missing_fields()

    if pending:
        raise ValueError(f"No se puede preparar el borrador. Faltan datos: {pending}")

    if STATE.pending_action != "prepare_ticket_draft":
        raise ValueError("No hay ninguna acción de preparación de borrador pendiente.")

    if not STATE.action_confirmed:
        raise ValueError("El usuario todavía no ha confirmado la acción.")

    STATE.ticket_draft_id = f"DRAFT-{uuid.uuid4().hex[:8].upper()}"
    STATE.pending_action = None
    STATE.action_confirmed = False
    STATE.phase = "completed"

    return json.dumps(
        {
            "action": "ticket_draft_prepared",
            "ticket_draft_id": STATE.ticket_draft_id,
            "real_ticket_created": False,
            "service": STATE.service,
            "description": STATE.description,
            "impact": STATE.impact,
            "users_affected": STATE.users_affected,
            "priority": STATE.priority,
        },
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------
# 4. Construcción del agente
# ---------------------------------------------------------------------

def build_agent() -> Agent:
    client = FoundryChatClient(
        project_endpoint=require_env("AZURE_AI_PROJECT_ENDPOINT"),
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_CHAT", "gpt-4o"),
        credential=AzureCliCredential(),
    )

    return Agent(
        client=client,
        name="AgenteInteraccionUsuario",
        instructions=(
            "Eres un agente de soporte técnico de nivel 1. "
            "Tu prioridad es interactuar de forma clara, breve y segura. "
            "Debes revisar el estado antes de responder usando leer_estado_interaccion. "
            "Si faltan datos, pregunta solo por el dato pendiente más importante. "
            "No hagas listas largas de preguntas. "
            "Si hay datos suficientes, puedes usar solicitar_confirmacion_borrador. "
            "Solo puedes usar preparar_borrador_ticket si el usuario ha confirmado explícitamente. "
            "No digas nunca que has creado un ticket real. "
            "Si el usuario rechaza la acción, confirma que no se hará nada. "
            "Si la petición está fuera de alcance, responde de forma breve y segura."
        ),
        tools=[
            leer_estado_interaccion,
            solicitar_confirmacion_borrador,
            preparar_borrador_ticket,
        ],
    )


# ---------------------------------------------------------------------
# 5. Loop de interacción
# ---------------------------------------------------------------------

async def main() -> None:
    agent = build_agent()
    session = agent.create_session()

    print("Agente de soporte listo. Escribe 's' para salir.\n")
    print("Prueba sugerida:")
    print("1) No puedo acceder a la VPN desde casa.")
    print("2) Solo me pasa a mí y el impacto es bajo.")
    print("3) Prepara un borrador de ticket.")
    print("4) sí\n")

    while True:
        user_message = input("Usuario> ").strip()

        if user_message.lower() in {"s", "salir", "exit", "quit"}:
            print("Agente> Conversación finalizada.")
            break

        blocked_reason = detect_sensitive_or_blocked_request(user_message)
        if blocked_reason:
            STATE.phase = "blocked"
            print(
                "Agente> No puedo realizar esa acción. "
                "Puedo ayudarte a diagnosticar la incidencia o preparar un borrador controlado."
            )
            print(f"[Bloqueo interno] {blocked_reason}")
            continue

        update_state_from_user_message(user_message)

        if STATE.action_rejected:
            STATE.pending_action = None
            STATE.action_rejected = False
            STATE.phase = "understanding"
            print("Agente> De acuerdo. No prepararé el borrador. ¿Quieres continuar con el diagnóstico?")
            continue

        agent_input = build_agent_input(user_message)

        try:
            response = await agent.run(agent_input, session=session)

            print("\nAgente>")
            print(response)

            print("\n[Estado de interacción]")
            print(json.dumps(asdict(STATE), indent=2, ensure_ascii=False))
            print("-" * 80)

        except Exception as ex:
            print("\nAgente>")
            print(
                "No he podido completar este paso de forma segura. "
                "No se ha realizado ninguna acción real."
            )
            print(f"[Error interno controlado] {ex}")


if __name__ == "__main__":
    asyncio.run(main())