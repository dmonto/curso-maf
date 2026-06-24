from __future__ import annotations

import asyncio
from typing import Any

from src.agents.internal_process_agent import build_internal_process_agent


def render_result(result: Any) -> str:
    if isinstance(result, str):
        return result

    for attr in ("text", "content", "message"):
        value = getattr(result, attr, None)
        if value:
            return str(value)

    return str(result)


async def main() -> None:
    agent = build_internal_process_agent()

    prompts = [
        """
Necesito comprar una licencia anual de DataViz Pro para el equipo de marketing.
Coste estimado: 1.200 euros al año.
Justificación: la necesitamos para preparar cuadros de mando de campañas y reducir trabajo manual.
Responsable presupuestario: Laura Gómez.
No tratará datos personales, solo métricas agregadas.
Es urgente porque el proyecto empieza el lunes.
""",
        """
Quiero comprar una herramienta nueva para el equipo.
Creo que cuesta poco, pero no sé cuánto.
""",
        """
Necesito acceso de administrador al ERP para hacer unos cambios rápidos.
""",
    ]

    for index, prompt in enumerate(prompts, start=1):
        print(f"\n\n--- CASO {index} ---")
        print(prompt.strip())

        result = await agent.run(prompt)

        print("\n--- RESPUESTA DEL AGENTE ---")
        print(render_result(result))


if __name__ == "__main__":
    asyncio.run(main())