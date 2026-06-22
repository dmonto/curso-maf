import asyncio

from src.agents.support_agent_rag import build_support_agent


async def main() -> None:
    agent = build_support_agent()

    prompt = """
Un usuario dice que no puede acceder a la VPN desde Windows 11.
Ya ha comprobado que tiene Internet, pero no sabe qué pasos seguir.
Responde usando el procedimiento interno si lo encuentras.
"""

    result = await agent.run(prompt)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())