from __future__ import annotations

import json
from typing import Annotated, Any

from agent_framework import tool
from pydantic import Field

from src.security.access_policy import user_context_from_dict
from src.vector.azure_ai_search_store import vector_search


@tool(
    name="secure_search_support_knowledge",
    description=(
        "Busca conocimiento interno aplicando filtros de seguridad por usuario, tenant y grupos. "
        "Úsala para consultar documentación interna de soporte, procedimientos o criterios. "
        "Nunca debe devolver documentos para los que el usuario no tenga permiso."
    ),
)
def secure_search_support_knowledge(
    query: Annotated[
        str,
        Field(
            description="Consulta semántica sobre la documentación interna.",
            min_length=3,
        ),
    ],
    user_context_json: Annotated[
        str,
        Field(
            description=(
                "Contexto de usuario autenticado en JSON. "
                "Debe incluir user_id, tenant_id y groups. "
                "En producción este valor debe venir del backend, no del mensaje libre del usuario."
            ),
            min_length=3,
        ),
    ],
    domain: Annotated[
        str | None,
        Field(
            description="Dominio documental opcional: vpn, erp, support, hr, identity, teams.",
        ),
    ] = None,
    top_k: Annotated[
        int,
        Field(
            description="Número máximo de chunks permitidos a recuperar.",
            ge=1,
            le=5,
        ),
    ] = 3,
) -> dict[str, Any]:
    try:
        payload = json.loads(user_context_json)
        user_context = user_context_from_dict(payload)

    except Exception as exc:
        return {
            "valid": False,
            "error": f"Contexto de usuario inválido. Acceso denegado. Detalle: {exc}",
            "results": [],
        }

    results = vector_search(
        query=query,
        user_context=user_context,
        domain=domain,
        top_k=top_k,
        hybrid=True,
    )

    return {
        "valid": True,
        "user_id": user_context.user_id,
        "tenant_id": user_context.tenant_id,
        "groups": user_context.groups,
        "domain": domain,
        "results_count": len(results),
        "results": results,
    }