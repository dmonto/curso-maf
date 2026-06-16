import asyncio
import logging
import os
from dataclasses import fields
from typing import Any

from src.agents.support_agent import build_structured_support_agent
from src.security import MemorySecurityGuard
from src.state import SupportSessionMemory
from src.storage import AzureDistributedSessionStore


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


def build_prompt(
    user_text: str,
    memory: SupportSessionMemory,
    security_report: dict[str, Any] | None,
) -> str:
    return f"""
Eres un agente de soporte técnico de nivel 1.

La memoria persistente pasa por una capa de seguridad antes de guardarse.
No solicites contraseñas, tokens, códigos MFA ni secretos.
Si el usuario aporta un secreto, indícale que no debe compartirlo y continúa con una alternativa segura.
No digas que has creado un ticket real. Como máximo puedes preparar un borrador.

MEMORIA ACTUAL:
{memory.to_model_context()}

ÚLTIMO REPORTE DE SEGURIDAD DE MEMORIA:
{security_report or "Todavía no hay reporte."}

MENSAJE ACTUAL:
{user_text}
""".strip()


async def main() -> None:
    user_id = os.getenv("MAF_USER_ID", "usuario-demo")

    session_id = input("Session ID [caso-seguridad-memoria]: ").strip()
    if not session_id:
        session_id = "caso-seguridad-memoria"

    store = AzureDistributedSessionStore.from_env()
    guard = MemorySecurityGuard()

    loaded = store.load(user_id=user_id, session_id=session_id)

    if loaded:
        state = loaded.state
        etag = loaded.etag
        print("\nEstado recuperado desde almacenamiento distribuido.\n")
    else:
        loaded = store.create_empty(user_id=user_id, session_id=session_id)
        state = loaded.state
        etag = loaded.etag
        print("\nEstado nuevo creado.\n")

    memory = memory_from_dict(state.memory)

    agent = build_structured_support_agent()
    last_security_report: dict[str, Any] | None = state.metadata.get("last_memory_security_report")

    print("Chat con seguridad en memoria persistente")
    print("Comandos:")
    print("  /memoria     muestra memoria cargada")
    print("  /seguridad   muestra último reporte de seguridad")
    print("  /estado      muestra estado distribuido")
    print("  /reset       borra estado")
    print("  /salir       termina\n")

    while True:
        user_text = input("Tú> ").strip()

        if not user_text:
            continue

        command = user_text.lower()

        if command == "/salir":
            print("Sesión finalizada.")
            break

        if command == "/memoria":
            print("\n--- MEMORIA EN USO ---")
            print(memory.to_json())
            print()
            continue

        if command == "/seguridad":
            print("\n--- REPORTE DE SEGURIDAD ---")
            print(last_security_report or "Todavía no hay reporte.")
            print()
            continue

        if command == "/estado":
            print("\n--- ESTADO DISTRIBUIDO ---")
            print(state.to_json())
            print()
            continue

        if command == "/reset":
            store.delete(user_id=user_id, session_id=session_id)
            print("Estado eliminado.")
            break

        memory.update_from_user_text(user_text)

        # Simulación didáctica:
        # guardamos parte del mensaje del usuario como última acción recomendada
        # para demostrar que el sanitizador intercepta datos sensibles.
        if any(word in user_text.lower() for word in ["contraseña", "password", "token", "mfa"]):
            memory.ultima_accion_recomendada = user_text

        unsafe_memory_dict = memory.to_dict()

        sanitized_memory_dict, security_report = guard.sanitize_memory(unsafe_memory_dict)
        last_security_report = security_report.to_dict()

        state.memory = sanitized_memory_dict
        state.metadata["last_memory_security_report"] = last_security_report
        state.metadata["memory_sensitivity"] = security_report.sensitivity()

        etag = store.save(
            state=state,
            expected_etag=etag,
        )

        # Rehidratar memoria desde lo realmente persistido.
        # Así evitamos que la memoria local conserve algo que no se ha podido guardar.
        memory = memory_from_dict(sanitized_memory_dict)

        prompt = build_prompt(
            user_text=user_text,
            memory=memory,
            security_report=last_security_report,
        )

        result = await agent.run(prompt)
        assistant_text = render_result(result)

        print("\nAgente>")
        print(assistant_text)
        print()


if __name__ == "__main__":
    asyncio.run(main())