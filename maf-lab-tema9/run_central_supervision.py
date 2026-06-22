import asyncio
import logging

from src.agents.multiagent.supervised_coordinator import (
    build_supervised_coordinator,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main() -> None:
    agent = build_supervised_coordinator()

    prompt = (
        "Un proveedor externo necesita acceso administrador temporal al ERP "
        "para resolver una incidencia antes de una auditoría. "
        "No hay aprobación formal registrada, pero Finanzas dice que es urgente. "
        "Analiza el caso y dime qué se puede hacer."
    )

    result = await agent.run(prompt)

    print("\n--- RESPUESTA DEL COORDINADOR SUPERVISADO ---\n")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())