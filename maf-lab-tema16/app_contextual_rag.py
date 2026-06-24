import asyncio

from src.agents.support_agent_rag_context import build_support_agent


async def main() -> None:
    agent = build_support_agent()

    prompt = """
El usuario no puede acceder a la red privada corporativa desde Windows 11.
Tiene Internet, ya ha validado MFA y ha probado otra red.
Solo le pasa a él.

¿Qué debería revisar ahora soporte y qué prioridad tendría normalmente?
"""

    result = await agent.run(prompt)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())