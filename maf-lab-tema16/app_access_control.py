import asyncio

from src.agents.support_agent_ac import build_support_agent


async def main() -> None:
    agent = build_support_agent()

    prompts = [
        "Consulta el ticket INC-1001.",
        "Cambia la prioridad del ticket INC-1001 a p1.",
        "Dame un resumen global de tickets.",
    ]

    for prompt in prompts:
        print(f"\nUsuario> {prompt}")
        result = await agent.run(prompt)
        print(f"Agente> {result}")


if __name__ == "__main__":
    asyncio.run(main())