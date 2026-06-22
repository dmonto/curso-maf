import asyncio

from src.agents.support_agent_safe import build_support_agent


async def main() -> None:
    agent = build_support_agent()

    prompts = [
        "Consulta el ticket externo INC-1001.",
        "Consulta el ticket externo INC-404.",
        "Consulta el ticket externo INC-500.",
        "Consulta el ticket externo INC-SLOW.",
        "Consulta el ticket externo INC-BADJSON.",
    ]

    for prompt in prompts:
        print(f"\nUsuario> {prompt}")
        result = await agent.run(prompt)
        print(f"Agente> {result}")


if __name__ == "__main__":
    asyncio.run(main())