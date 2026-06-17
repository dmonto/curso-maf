import asyncio
import logging
import os
from typing import Any

from src.agents.support_agent import build_structured_support_agent
from src.state import SupportSessionMemory
from src.state.robust_state import (
    InvalidStateTransition,
    SupportCaseState,
    SupportCaseStateMachine,
)


logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def render_result(result: object) -> str:
    for attr in ("text", "content", "message"):
        value = getattr(result, attr, None)
        if value:
            return str(value)

    return str(result)


def build_prompt(
    user_text: str,
    state: SupportCaseState,
    memory: SupportSessionMemory,
) -> str:
    return f"""
Eres un agente de soporte técnico de nivel 1.

El estado del caso está controlado por una máquina de estados.
No afirmes acciones que no estén reflejadas en el estado.
No digas que has creado un ticket real.
Si el estado está blocked o closed, explica el bloqueo y pide el siguiente paso seguro.

ESTADO DEL CASO:
{state.to_json()}

MEMORIA OPERATIVA:
{memory.to_model_context()}

MENSAJE ACTUAL:
{user_text}
""".strip()


def state_from_memory(
    state: SupportCaseState,
    memory: SupportSessionMemory,
) -> None:
    state.memory = memory.to_dict()


def can_mark_ready(memory: SupportSessionMemory) -> bool:
    return bool(memory.servicio and memory.ubicacion and memory.sistema_operativo)


async def main() -> None:
    user_id = os.getenv("MAF_USER_ID", "usuario-demo")

    session_id = input("Session ID [caso-estado-robusto]: ").strip()
    if not session_id:
        session_id = "caso-estado-robusto"

    agent = build_structured_support_agent()
    machine = SupportCaseStateMachine()

    state = SupportCaseState(
        user_id=user_id,
        session_id=session_id,
    )

    memory = SupportSessionMemory()

    print("\nChat con diseño robusto de estado")
    print(f"user_id: {user_id}")
    print(f"session_id: {session_id}")
    print("Comandos:")
    print("  /estado       muestra estado completo")
    print("  /validar      valida invariantes")
    print("  /ready        intenta pasar a ready_for_draft")
    print("  /borrador     adjunta un borrador simulado")
    print("  /cerrar       cierra el caso")
    print("  /reabrir      reabre el caso")
    print("  /salir        termina\n")

    while True:
        user_text = input("Tú> ").strip()

        if not user_text:
            continue

        command = user_text.lower()

        if command == "/salir":
            print("Sesión finalizada.")
            break

        if command == "/estado":
            print("\n--- ESTADO ---")
            print(state.to_json())
            print()
            continue

        if command == "/validar":
            report = machine.validate(state)
            print("\n--- VALIDACIÓN ---")
            print(report.to_dict())
            print()
            continue

        if command == "/cerrar":
            try:
                machine.close(
                    state=state,
                    actor="user",
                    reason="manual_close",
                )
                print("Caso cerrado.\n")
            except InvalidStateTransition as exc:
                print(f"No se puede cerrar: {exc}\n")
            continue

        if command == "/reabrir":
            try:
                machine.reopen(
                    state=state,
                    actor="user",
                    reason="manual_reopen",
                )
                print("Caso reabierto.\n")
            except InvalidStateTransition as exc:
                print(f"No se puede reabrir: {exc}\n")
            continue

        if command == "/ready":
            state_from_memory(state, memory)

            if not can_mark_ready(memory):
                print(
                    "Todavía no hay datos mínimos. "
                    "Necesito servicio, ubicación y sistema operativo.\n"
                )
                continue

            try:
                machine.mark_ready_for_draft(
                    state=state,
                    actor="user",
                )
                print("Estado cambiado a ready_for_draft.\n")
            except InvalidStateTransition as exc:
                print(f"No se puede cambiar de estado: {exc}\n")
            continue

        if command == "/borrador":
            try:
                machine.attach_draft(
                    state=state,
                    actor="user",
                    draft_preview=(
                        "Borrador de ticket: incidencia de acceso VPN "
                        "con datos recopilados en la sesión."
                    ),
                )
                print("Borrador adjuntado y estado cambiado a draft_prepared.\n")
            except InvalidStateTransition as exc:
                print(f"No se puede adjuntar borrador: {exc}\n")
            continue

        if state.status == "closed":
            print(
                "\nEste caso está cerrado. Usa /reabrir antes de continuar "
                "o crea una nueva sesión.\n"
            )
            continue

        memory.update_from_user_text(user_text)
        state_from_memory(state, memory)

        machine.apply_user_message(
            state=state,
            user_text=user_text,
        )

        validation = machine.validate(state)

        prompt = build_prompt(
            user_text=user_text,
            state=state,
            memory=memory,
        )

        result = await agent.run(prompt)
        assistant_text = render_result(result)

        state.recent_turns.append(
            {
                "role": "assistant",
                "content": assistant_text[:1200],
            }
        )
        state.recent_turns = state.recent_turns[-12:]
        state.touch()
        state.add_event(
            event_type="assistant_response_recorded",
            actor="agent",
            payload={
                "response_length": len(assistant_text),
                "validation_status": validation.status(),
            },
        )

        print("\nAgente>")
        print(assistant_text)
        print()


if __name__ == "__main__":
    asyncio.run(main())