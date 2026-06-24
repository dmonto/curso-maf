from __future__ import annotations

import asyncio
import logging

from src.agents.contract_support_agent import build_contract_support_agent
from src.di.container import build_app_container


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
    container = build_app_container()
    agent = build_contract_support_agent(container)

    prompt = """
Tenemos una incidencia en el ERP.
35 usuarios de finanzas no pueden emitir facturas.
El impacto es bloqueo de facturación a clientes.
Registra y clasifica la incidencia.
"""

    result = await agent.run(prompt)

    print("\n--- RESPUESTA DEL AGENTE ---")
    print(render_result(result))


if __name__ == "__main__":
    asyncio.run(main())