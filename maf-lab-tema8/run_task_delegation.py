import asyncio
import logging

from src.agents.multiagent.delegator_agent import (
    build_task_delegation_coordinator,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main() -> None:
    agent = build_task_delegation_coordinator()

    prompt = (
        "Un usuario de Finanzas no puede conectarse a la VPN desde casa. "
        "El cliente VPN se queda validando MFA y después falla. "
        "Solo le ocurre a él. Necesita acceder al ERP para cierre contable esta tarde. "
        "Analiza el caso y dime qué harías."
    )

    result = await agent.run(prompt)

    print("\n--- RESPUESTA DEL COORDINADOR ---\n")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())