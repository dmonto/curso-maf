from __future__ import annotations

from typing import Annotated, Any

from agent_framework import tool
from pydantic import Field

from src.vector.azure_ai_search_store import vector_search


@tool(
    name="search_vector_support_knowledge",
    description=(
        "Busca conocimiento interno de soporte en una base vectorial de Azure AI Search. "
        "Úsala cuando el usuario pregunte por procedimientos, incidencias, prioridad, VPN, ERP, "
        "MFA, acceso, errores o soporte técnico. "
        "Devuelve chunks con fuente, dominio, score y texto recuperado."
    ),
)
def search_vector_support_knowledge(
    query: Annotated[
        str,
        Field(
            description=(
                "Consulta semántica basada en la necesidad del usuario. "
                "Debe incluir síntoma, servicio afectado o procedimiento buscado."
            ),
            min_length=3,
        ),
    ],
    domain: Annotated[
        str | None,
        Field(
            description=(
                "Filtro opcional por dominio. Ejemplos: vpn, erp, support. "
                "Usa null si no estás seguro."
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
    hybrid: Annotated[
        bool,
        Field(
            description=(
                "Si true, combina búsqueda textual y vectorial. "
                "Si false, usa solo búsqueda vectorial."
            ),
        ),
    ] = True,
) -> dict[str, Any]:
    results = vector_search(
        query=query,
        domain=domain,
        top_k=top_k,
        hybrid=hybrid,
    )

    return {
        "query": query,
        "domain": domain,
        "hybrid": hybrid,
        "results_count": len(results),
        "results": results,
    }