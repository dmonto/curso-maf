import asyncio

from src.agents.support_agent_m365 import build_support_agent


async def main() -> None:
    agent = build_support_agent()

    prompts = [
        (
            "Prepara un borrador de correo para ana.garcia@empresa.local "
            "con asunto 'Seguimiento incidencia VPN'. "
            "Indica que queremos confirmar si la VPN sigue lenta después de reiniciar "
            "el cliente y validar MFA."
        ),
        (
            "Prepara una reunión de seguimiento el 18 de junio de 2026 "
            "de 10:00 a 10:30 con ana.garcia@empresa.local. "
            "Título: Seguimiento incidencia VPN. "
            "Agenda: revisar estado, validar pruebas realizadas y decidir próximos pasos."
        ),
    ]

    for prompt in prompts:
        print(f"\nUsuario> {prompt}")
        result = await agent.run(prompt)
        print(f"Agente> {result}")


if __name__ == "__main__":
    asyncio.run(main())