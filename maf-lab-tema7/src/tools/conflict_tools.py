from typing import Annotated

from agent_framework import tool
from pydantic import Field

from src.agents.multiagent.conflict_resolution import build_conflict_resolver


@tool(
    name="resolver_conflicto_multiagente",
    description=(
        "Analiza resultados de varios especialistas y resuelve conflictos entre diagnósticos, "
        "prioridades, riesgos o acciones recomendadas. No ejecuta acciones reales."
    ),
)
async def resolver_conflicto_multiagente(
    resultados_especialistas: Annotated[
        str,
        Field(
            description=(
                "Resultados de especialistas en texto estructurado. "
                "Debe incluir especialista, conclusión, evidencias, confianza y acción propuesta si existe."
            ),
            min_length=30,
        ),
    ],
    criterio_resolucion: Annotated[
        str,
        Field(
            description=(
                "Criterio que debe aplicar el resolutor. "
                "Ejemplo: priorizar seguridad, pedir datos faltantes o evitar acciones irreversibles."
            ),
            min_length=10,
        ),
    ] = (
        "Aplicar evidencias primero, después confianza, después precedencia por riesgo. "
        "No recomendar acciones irreversibles sin validación."
    ),
) -> str:
    resolver = build_conflict_resolver()

    prompt = (
        "Analiza los siguientes resultados de especialistas y resuelve posibles conflictos.\n\n"
        f"RESULTADOS:\n{resultados_especialistas}\n\n"
        f"CRITERIO DE RESOLUCIÓN:\n{criterio_resolucion}\n"
    )

    result = await resolver.run(prompt)
    return str(result)