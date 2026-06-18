from __future__ import annotations

import json
from typing import Annotated, Any

from agent_framework import tool
from pydantic import Field

from src.security.permission_policy import UserAccessContext
from src.vector.azure_ai_search_store import vector_search


def _parse_user_context(user_context_json: str) -> UserAccessContext:
    payload = json.loads(user_context_json)

    return UserAccessContext(
        user_id=payload["user_id"],
        tenant_id=payload["tenant_id"],
        groups=payload.get("groups", []),
    )


@tool(
    name="search_documents_with_permissions",
    description=(
        "Busca documentación interna aplicando control de permisos por tenant, usuario y grupos. "
        "Debe usarse siempre que se consulte documentación corporativa. "
        "No devuelve documentos no autorizados."
    ),
)
def search_documents_with_permissions(
    query: Annotated[
        str,
        Field(
            description="Consulta semántica o híbrida sobre la documentación interna.",
            min_length=3,
        ),
    ],
    user_context_json: Annotated[
        str,
        Field(
            description=(
                "Contexto del usuario autenticado en JSON. "
                "Debe venir del backend de la aplicación. "
                "Debe incluir user_id, tenant_id y groups."
            ),
            min_length=3,
        ),
    ],
    domain: Annotated[
        str | None,
        Field(description="Dominio documental opcional: vpn, erp, hr, support, identity, teams."),
    ] = None,
    top_k: Annotated[
        int,
        Field(description="Número máximo de chunks a recuperar.", ge=1, le=5),
    ] = 3,
) -> dict[str, Any]:
    try:
        user = _parse_user_context(user_context_json)
    except Exception as exc:
        return {
            "valid": False,
            "error": f"Contexto de usuario inválido. Acceso denegado: {exc}",
            "results": [],
        }

    results = vector_search(
        query=query,
        user=user,
        domain=domain,
        top_k=top_k,
        hybrid=True,
    )

    return {
        "valid": True,
        "user_id": user.user_id,
        "tenant_id": user.tenant_id,
        "domain": domain,
        "results_count": len(results),
        "results": results,
    }