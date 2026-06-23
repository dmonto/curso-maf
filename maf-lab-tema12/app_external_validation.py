import asyncio

from src.agents.support_agent_val import build_support_agent


async def main() -> None:
    agent = build_support_agent()

    prompts = [
        "Consulta el ticket externo INC-1001.",
        "Consulta el ticket externo INC-1002.",
        "Consulta el ticket externo INC-1003.",
        "Consulta el ticket externo INC-9999.",
    ]

    for prompt in prompts:
        print(f"\nUsuario> {prompt}")
        result = await agent.run(prompt)
        print(f"Agente> {result}")


if __name__ == "__main__":
    asyncio.run(main())