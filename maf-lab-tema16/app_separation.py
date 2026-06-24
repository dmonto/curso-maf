from __future__ import annotations

import asyncio
import logging

from src.agents.support_agent_resp import build_support_agent


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main() -> None:
    agent = build_support_agent()

    prompt = """
Tenemos una incidencia en el ERP.
Desde hace 20 minutos, 35 usuarios de finanzas no pueden emitir facturas.
El impacto es bloqueo de facturación a clientes.
Prepara un borrador de ticket.
"""

    result = await agent.run(prompt)

    print("\n--- RESPUESTA DEL AGENTE ---")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())