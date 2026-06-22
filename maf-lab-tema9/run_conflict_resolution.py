import asyncio
import logging

from src.agents.multiagent.conflictor_agent import (
    build_conflict_aware_coordinator,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main() -> None:
    agent = build_conflict_aware_coordinator()

    prompt = (
        "Un usuario de Finanzas no puede acceder al ERP desde casa. "
        "Dice que la VPN conecta correctamente, pero al abrir el ERP aparece acceso denegado. "
        "Necesita entrar hoy por cierre contable. "
        "Analiza el caso, detecta si hay conflicto entre posibles causas y dime el siguiente paso."
    )

    result = await agent.run(prompt)

    print("\n--- RESPUESTA DEL COORDINADOR ---\n")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())