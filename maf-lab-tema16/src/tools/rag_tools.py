from __future__ import annotations

from typing import Annotated, Any

from agent_framework import tool
from pydantic import Field

from src.rag.local_retriever import search_knowledge


@tool(
    name="retrieve_support_knowledge",
    description=(
        "Busca fragmentos relevantes en la base documental interna de soporte. "
        "Úsala cuando el usuario pregunte por procedimientos, criterios de prioridad, "
        "VPN, MFA, ERP o resolución de incidencias. "
        "Devuelve fuentes internas, puntuación de relevancia y fragmentos de texto."
    ),
)
def retrieve_support_knowledge(
    query: Annotated[
        str,
        Field(
            description=(
                "Consulta de búsqueda basada en la necesidad del usuario. "
                "Debe ser concreta e incluir el servicio, síntoma o procedimiento buscado."
            ),
            min_length=3,
        ),
    ],
    top_k: Annotated[
        int,
        Field(
            description="Número máximo de fragmentos a recuperar.",
            ge=1,
            le=5,
        ),
    ] = 3,
) -> dict[str, Any]:
    results = search_knowledge(query=query, top_k=top_k)

    return {
        "query": query,
        "results_count": len(results),
        "results": results,
    }