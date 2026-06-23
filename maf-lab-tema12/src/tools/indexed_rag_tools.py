from __future__ import annotations

from typing import Annotated, Any

from agent_framework import tool
from pydantic import Field

from src.rag.indexed_search import search_indexed_documents


@tool(
    name="search_indexed_support_documents",
    description=(
        "Busca información en el índice documental interno de soporte. "
        "Úsala cuando el usuario pregunte por procedimientos, incidencias, VPN, ERP, MFA "
        "o criterios de prioridad. Devuelve chunks ya indexados con fuente, dominio y score."
    ),
)
def search_indexed_support_documents(
    query: Annotated[
        str,
        Field(
            description=(
                "Consulta concreta para buscar en el índice documental. "
                "Debe incluir servicio, síntoma o procedimiento buscado."
            ),
            min_length=3,
        ),
    ],
    domain: Annotated[
        str | None,
        Field(
            description=(
                "Filtro opcional por dominio documental. "
                "Ejemplos: vpn, erp, support. Si no se conoce, usar null."
            ),
        ),
    ] = None,
    top_k: Annotated[
        int,
        Field(
            description="Número máximo de chunks a recuperar.",
            ge=1,
            le=5,
        ),
    ] = 3,
) -> dict[str, Any]:
    results = search_indexed_documents(
        query=query,
        domain=domain,
        top_k=top_k,
    )

    return {
        "query": query,
        "domain": domain,
        "results_count": len(results),
        "results": results,
    }