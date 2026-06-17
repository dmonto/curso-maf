import asyncio
import logging

from src.agents.support_agent import build_structured_support_agent
from src.state import SupportSessionMemory


logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def render_result(result: object) -> str:
    """
    Pequeño adaptador para imprimir el resultado de forma robusta
    aunque el objeto devuelto por el runtime cambie ligeramente.
    """
    for attr in ("text", "content", "message"):
        value = getattr(result, attr, None)
        if value:
            return str(value)

    return str(result)


def build_prompt(user_text: str, memory: SupportSessionMemory) -> str:
    return f"""
Eres un agente de soporte técnico de nivel 1.

Usa la memoria de sesión para mantener continuidad, pero no inventes datos.
Si falta información crítica, pregúntala.
No digas que has creado un ticket real. Como máximo puedes preparar un borrador.

MEMORIA DE SESIÓN ACTUAL:
{memory.to_model_context()}

MENSAJE ACTUAL DEL USUARIO:
{user_text}
""".strip()


async def main() -> None:
    agent = build_structured_support_agent()
    session = agent.create_session()
    memory = SupportSessionMemory()

    print("\nChat de soporte con memoria en sesión")
    print("Comandos:")
    print("  /memoria  muestra la memoria estructurada")
    print("  /salir    termina la sesión\n")

    while True:
        user_text = input("Tú> ").strip()

        if not user_text:
            continue

        if user_text.lower() == "/salir":
            print("Sesión finalizada.")
            break

        if user_text.lower() == "/memoria":
            print("\n--- MEMORIA DE SESIÓN ---")
            print(memory.to_json())
            print()
            continue

        memory.update_from_user_text(user_text)

        prompt = build_prompt(user_text=user_text, memory=memory)
        result = await agent.run(prompt, session=session)

        print("\nAgente>")
        print(render_result(result))
        print()


if __name__ == "__main__":
    asyncio.run(main())