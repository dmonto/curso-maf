from __future__ import annotations

import asyncio

from src.agents.tools_adaptation_agent import build_tools_adaptation_agent


def render_response(response: object) -> str:
    for attr in ("text", "content", "message"):
        value = getattr(response, attr, None)
        if value:
            return str(value)

    value = getattr(response, "value", None)
    if value:
        return str(value)

    return str(response)


async def main() -> None:
    agent = build_tools_adaptation_agent()

    prompt = """
No puedo acceder a la VPN desde Windows 11.
Ya he probado reiniciar el cliente VPN y tengo conexión a Internet.
¿Puedes revisar si hay algo abierto y preparar un ticket si hace falta?
"""

    response = await agent.run(prompt)
    print(render_response(response))


if __name__ == "__main__":
    asyncio.run(main())