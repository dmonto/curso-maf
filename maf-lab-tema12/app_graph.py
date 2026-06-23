import asyncio

from src.agents.support_agent_graph import build_support_agent


async def main() -> None:
    agent = build_support_agent()

    prompts = [
        "¿Con qué usuario estoy autenticado?",
        "Consulta mis próximos eventos de los próximos 7 días, máximo 5.",
    ]

    for prompt in prompts:
        print(f"\nUsuario> {prompt}")
        result = await agent.run(prompt)
        print(f"Agente> {result}")


if __name__ == "__main__":
    asyncio.run(main())