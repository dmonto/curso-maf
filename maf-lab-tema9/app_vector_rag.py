import asyncio

from src.agents.support_agent_rag_embed import build_support_agent


async def main() -> None:
    agent = build_support_agent()

    prompt = """
Un usuario dice que no puede entrar a la red privada corporativa desde Windows 11.
Tiene Internet y solo le pasa a él.
¿Qué debería revisar soporte y qué prioridad tendría normalmente?
"""

    result = await agent.run(prompt)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())