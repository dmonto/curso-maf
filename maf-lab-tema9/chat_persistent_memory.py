import asyncio
import logging
import os

from src.agents.support_agent import build_structured_support_agent
from src.state import SupportSessionMemory
from src.storage import AzureTableSessionMemoryStore


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


def build_prompt(user_text: str, memory: SupportSessionMemory) -> str:
    return f"""
Eres un agente de soporte técnico de nivel 1.

Tienes memoria persistente recuperada desde una base externa.
Usa esa memoria para mantener continuidad, pero no inventes datos.
Si falta información crítica, pregúntala.
No digas que has creado un ticket real. Como máximo puedes preparar un borrador.

MEMORIA PERSISTENTE ACTUAL:
{memory.to_model_context()}

MENSAJE ACTUAL DEL USUARIO:
{user_text}
""".strip()


async def main() -> None:
    user_id = os.getenv("MAF_USER_ID", "usuario-demo")

    session_id = input("Session ID [soporte-vpn-demo]: ").strip()
    if not session_id:
        session_id = "soporte-vpn-demo"

    store = AzureTableSessionMemoryStore.from_env()

    loaded_memory = store.load(
        user_id=user_id,
        session_id=session_id,
    )

    if loaded_memory:
        memory = loaded_memory
        print("\nMemoria recuperada desde Azure Table Storage.\n")
    else:
        memory = SupportSessionMemory()
        print("\nNo había memoria previa. Se crea una memoria nueva.\n")

    agent = build_structured_support_agent()
    session = agent.create_session()

    print("Chat de soporte con memoria persistente")
    print("Comandos:")
    print("  /memoria  muestra memoria actual")
    print("  /guardar  guarda memoria manualmente")
    print("  /reset    borra memoria persistida")
    print("  /salir    termina la sesión\n")

    while True:
        user_text = input("Tú> ").strip()

        if not user_text:
            continue

        command = user_text.lower()

        if command == "/salir":
            store.save(
                user_id=user_id,
                session_id=session_id,
                memory=memory,
            )
            print("Memoria guardada. Sesión finalizada.")
            break

        if command == "/memoria":
            print("\n--- MEMORIA ACTUAL ---")
            print(memory.to_json())
            print()
            continue

        if command == "/guardar":
            store.save(
                user_id=user_id,
                session_id=session_id,
                memory=memory,
            )
            print("Memoria guardada en Azure Table Storage.\n")
            continue

        if command == "/reset":
            store.delete(
                user_id=user_id,
                session_id=session_id,
            )
            memory = SupportSessionMemory()
            print("Memoria persistida eliminada y memoria local reiniciada.\n")
            continue

        memory.update_from_user_text(user_text)

        prompt = build_prompt(
            user_text=user_text,
            memory=memory,
        )

        result = await agent.run(
            prompt,
            session=session,
        )

        store.save(
            user_id=user_id,
            session_id=session_id,
            memory=memory,
        )

        print("\nAgente>")
        print(render_result(result))
        print()


if __name__ == "__main__":
    asyncio.run(main())