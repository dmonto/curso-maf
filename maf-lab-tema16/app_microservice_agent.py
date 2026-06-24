from __future__ import annotations

import asyncio
import logging

from src.agents.support_microservice_agent import build_support_microservice_agent


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def render_result(result) -> str:
    for attr in ("text", "content", "message"):
        value = getattr(result, attr, None)
        if value:
            return str(value)

    return str(result)


async def main() -> None:
    agent = build_support_microservice_agent()

    prompt = """
Tenemos una incidencia en el ERP.
Desde hace 20 minutos, 35 usuarios de finanzas no pueden emitir facturas.
El impacto es bloqueo de facturación a clientes.
Clasifica la incidencia y dime a qué equipo debería ir.
"""

    result = await agent.run(prompt)

    print("\n--- RESPUESTA DEL AGENTE ---")
    print(render_result(result))


if __name__ == "__main__":
    asyncio.run(main())