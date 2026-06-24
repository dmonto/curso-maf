import asyncio
import logging

from src.agents.multiagent.state_coordinator import build_state_aware_coordinator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main() -> None:
    agent = build_state_aware_coordinator()

    prompt = (
        "Un usuario de Finanzas no puede acceder al ERP desde casa. "
        "La VPN conecta correctamente, pero el ERP muestra 'acceso denegado'. "
        "No crees ticket real. Registra el caso, identifica datos pendientes "
        "y deja una siguiente acción segura."
    )

    result = await agent.run(prompt)

    print("\n--- RESPUESTA DEL COORDINADOR ---\n")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())