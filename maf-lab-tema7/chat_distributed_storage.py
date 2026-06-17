import asyncio
import logging
import os
from dataclasses import fields
from typing import Any

from src.agents.support_agent import build_structured_support_agent
from src.state import SupportSessionMemory
from src.storage import AzureDistributedSessionStore, DistributedSessionState, StateConflictError


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


def memory_from_dict(data: dict[str, Any]) -> SupportSessionMemory:
    valid_fields = {field.name for field in fields(SupportSessionMemory)}
    filtered = {
        key: value
        for key, value in data.items()
        if key in valid_fields
    }

    if filtered.get("pasos_probados") is None:
        filtered["pasos_probados"] = []

    return SupportSessionMemory(**filtered)


def append_recent_turn(
    state: DistributedSessionState,
    role: str,
    content: str,
    max_turns: int = 10,
) -> None:
    state.recent_turns.append(
        {
            "role": role,
            "content": content[:1200],
        }
    )

    if len(state.recent_turns) > max_turns:
        state.recent_turns = state.recent_turns[-max_turns:]


def build_prompt(
    user_text: str,
    state: DistributedSessionState,
    memory: SupportSessionMemory,
) -> str:
    return f"""
Eres un agente de soporte técnico de nivel 1.

Estás usando estado distribuido compartido entre posibles instancias.
Usa la memoria y los últimos turnos para mantener continuidad.
No inventes datos.
No digas que has creado un ticket real; como máximo puedes preparar un borrador.

ESTADO DISTRIBUIDO:
- user_id: {state.user_id}
- session_id: {state.session_id}
- status: {state.metadata.get("status", "open")}
- turn_count: {state.metadata.get("turn_count", 0)}

MEMORIA ESTRUCTURADA:
{memory.to_model_context()}

RESUMEN ACUMULADO:
{state.rolling_summary or "No hay resumen acumulado."}

ÚLTIMOS TURNOS:
{state.recent_turns}

MENSAJE ACTUAL:
{user_text}
""".strip()


async def main() -> None:
    user_id = os.getenv("MAF_USER_ID", "usuario-demo")

    session_id = input("Session ID [caso-vpn-distribuido]: ").strip()
    if not session_id:
        session_id = "caso-vpn-distribuido"

    store = AzureDistributedSessionStore.from_env()

    loaded = store.load(
        user_id=user_id,
        session_id=session_id,
    )

    if loaded:
        state = loaded.state
        etag = loaded.etag
        print("\nEstado distribuido recuperado desde Azure Blob Storage.\n")
    else:
        loaded = store.create_empty(
            user_id=user_id,
            session_id=session_id,
        )
        state = loaded.state
        etag = loaded.etag
        print("\nNo existía estado. Se ha creado un snapshot nuevo.\n")

    memory = memory_from_dict(state.memory)

    agent = build_structured_support_agent()

    print("Chat con almacenamiento distribuido")
    print(f"user_id: {user_id}")
    print(f"session_id: {session_id}")
    print("Comandos:")
    print("  /memoria    muestra memoria estructurada")
    print("  /estado     muestra metadatos del estado distribuido")
    print("  /sesiones   lista sesiones del usuario")
    print("  /cerrar     marca el caso como cerrado")
    print("  /reabrir    marca el caso como abierto")
    print("  /reset      elimina estado distribuido")
    print("  /salir      termina\n")

    while True:
        user_text = input("Tú> ").strip()

        if not user_text:
            continue

        command = user_text.lower()

        if command == "/salir":
            print("Sesión finalizada.")
            break

        if command == "/memoria":
            print("\n--- MEMORIA ---")
            print(memory.to_json())
            print()
            continue

        if command == "/estado":
            print("\n--- ESTADO DISTRIBUIDO ---")
            print(state.to_json())
            print(f"\nETag actual: {etag}")
            print()
            continue

        if command == "/sesiones":
            print("\n--- SESIONES ---")
            for item in store.list_sessions(user_id):
                print(item)
            print()
            continue

        if command == "/reset":
            store.delete(
                user_id=user_id,
                session_id=session_id,
            )
            print("Estado distribuido eliminado.")
            break

        if command == "/cerrar":
            state.metadata["status"] = "closed"
            try:
                etag = store.save(
                    state=state,
                    expected_etag=etag,
                )
                print("Caso marcado como cerrado.\n")
            except StateConflictError as exc:
                print(f"Conflicto al guardar: {exc}\n")
            continue

        if command == "/reabrir":
            state.metadata["status"] = "open"
            try:
                etag = store.save(
                    state=state,
                    expected_etag=etag,
                )
                print("Caso reabierto.\n")
            except StateConflictError as exc:
                print(f"Conflicto al guardar: {exc}\n")
            continue

        if state.metadata.get("status") == "closed":
            print(
                "\nEste caso figura como cerrado. "
                "Usa /reabrir para continuar o crea una nueva sesión.\n"
            )
            continue

        memory.update_from_user_text(user_text)
        state.memory = memory.to_dict()

        turn_count = int(state.metadata.get("turn_count", 0)) + 1
        state.metadata["turn_count"] = turn_count
        state.metadata["last_user_message"] = user_text[:300]

        append_recent_turn(
            state=state,
            role="user",
            content=user_text,
        )

        prompt = build_prompt(
            user_text=user_text,
            state=state,
            memory=memory,
        )

        result = await agent.run(prompt)
        assistant_text = render_result(result)

        append_recent_turn(
            state=state,
            role="assistant",
            content=assistant_text,
        )

        try:
            etag = store.save(
                state=state,
                expected_etag=etag,
            )
        except StateConflictError as exc:
            print("\nNo se ha podido guardar el estado.")
            print(f"Motivo: {exc}")
            print("Recarga la sesión para evitar sobrescribir cambios de otra instancia.\n")
            continue

        print("\nAgente>")
        print(assistant_text)
        print()


if __name__ == "__main__":
    asyncio.run(main())