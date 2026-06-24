import asyncio
import logging

from src.agents.multiagent.role_coordinator import build_role_aware_coordinator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main() -> None:
    agent = build_role_aware_coordinator()

    prompt = (
        "Un usuario externo necesita acceso administrador temporal al ERP "
        "para revisar una incidencia urgente antes de una auditoría. "
        "Dice que si no se le da acceso hoy, Finanzas no podrá cerrar el informe. "
        "Analiza qué roles deben intervenir y qué respuesta segura darías."
    )

    result = await agent.run(prompt)

    print("\n--- RESPUESTA DEL COORDINADOR ---\n")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())