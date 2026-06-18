import asyncio
import logging

from src.agents.multiagent.coordinator_agent import build_support_coordinator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main() -> None:
    agent = build_support_coordinator()

    prompt = (
        "Un usuario de Finanzas no puede conectarse a la VPN desde casa. "
        "Dice que el cliente VPN se queda validando MFA y luego falla. "
        "Solo le ocurre a él, pero necesita acceder al ERP para cierre contable. "
        "Analiza el caso y dime qué harías."
    )

    result = await agent.run(prompt)
    print("\n--- RESPUESTA DEL COORDINADOR ---\n")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())