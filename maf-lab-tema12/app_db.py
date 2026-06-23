import asyncio

from src.agents.support_agent_db import build_support_agent


async def main() -> None:
    agent = build_support_agent()

    prompts = [
        "Consulta el ticket INC-1001.",
        "¿Qué activos tiene asignados ana.garcia@empresa.local?",
        "Dame un resumen de tickets por servicio.",
        (
            "Añade una nota al ticket INC-1001 indicando que el usuario "
            "confirma que la lentitud continúa tras reiniciar el cliente VPN. "
            "Registrado por soporte.n1@empresa.local."
        ),
    ]

    for prompt in prompts:
        print(f"\nUsuario> {prompt}")
        result = await agent.run(prompt)
        print(f"Agente> {result}")


if __name__ == "__main__":
    asyncio.run(main())