from __future__ import annotations

import asyncio

from src.agents.identity_support_agent import build_identity_support_agent
from src.identity.demo_users import get_demo_identity


def is_content_filtered_error(exc: Exception) -> bool:
    return "ContentFiltered" in str(exc) or "content filter" in str(exc).lower()


async def main() -> None:
    print("Identidades demo disponibles: ana, bruno, carla")
    alias = input("Identidad> ").strip()

    identity = get_demo_identity(alias)
    agent = build_identity_support_agent(identity)
    session = agent.create_session()

    print("\nEscribe 's' para salir.\n")

    while True:
        message = input("Tú> ").strip()

        if message.lower() == "s":
            break

        try:
            result = await agent.run(message, session=session)
            print(f"\nAgente> {result}\n")

        except ValueError as exc:
            if is_content_filtered_error(exc):
                print(
                    "\nAgente> La petición o la respuesta ha sido bloqueada por el filtro "
                    "de seguridad del modelo. Reformula la consulta sin pedir instrucciones "
                    "internas, credenciales, bypass de políticas o contenido sensible.\n"
                )
                continue
            raise

        except Exception as exc:
            if is_content_filtered_error(exc):
                print(
                    "\nAgente> La petición ha sido bloqueada por los filtros de seguridad "
                    "del servicio de IA. Prueba con una formulación más neutra.\n"
                )
                continue
            raise


if __name__ == "__main__":
    asyncio.run(main())