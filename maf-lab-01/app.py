import asyncio
import logging

from src.agents.support_agent import build_support_agent


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main() -> None:
    agent = build_support_agent()

    prompt = (
        "Haz un diagnóstico rápido de mi configuración inicial. "
        "Indica tres cosas que debería comprobar antes de añadir tools."
    )

    result = await agent.run(prompt)

    print("\n--- RESPUESTA DEL AGENTE ---")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())