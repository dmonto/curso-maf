import asyncio

from src.agents.support_agent_int import build_support_agent


async def main() -> None:
    agent = build_support_agent()

    prompts = [
        "Consulta el estado del ticket INC-1001.",
        (
            "Crea un ticket p2 para el servicio VPN. "
            "Resumen: Usuario no puede conectar desde casa usando Windows 11."
        ),
    ]

    for prompt in prompts:
        print(f"\nUsuario> {prompt}")
        result = await agent.run(prompt)
        print(f"Agente> {result}")


if __name__ == "__main__":
    asyncio.run(main())