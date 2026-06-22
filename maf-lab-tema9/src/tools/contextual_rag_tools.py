from __future__ import annotations

import json
from typing import Annotated, Any

from agent_framework import tool
from pydantic import Field

from src.retrieval.contextual_retriever import build_context_package


@tool(
    name="retrieve_contextual_support_knowledge",
    description=(
        "Recupera un paquete contextual desde la base documental interna de soporte. "
        "Usa esta tool cuando la pregunta dependa de procedimientos internos, criterios de prioridad, "
        "VPN, ERP, Teams, identidad, MFA o soporte técnico. "
        "Puede usar una consulta, resumen de conversación, estado del caso y dominio explícito."
    ),
)
def retrieve_contextual_support_knowledge(
    user_query: Annotated[
        str,
        Field(
            description="Pregunta o necesidad actual del usuario.",
            min_length=3,
        ),
    ],
    conversation_summary: Annotated[
        str | None,
        Field(
            description=(
                "Resumen breve de la conversación previa. "
                "Usa null si no existe contexto previo relevante."
            ),
        ),
    ] = None,
    case_state_json: Annotated[
        str | None,
        Field(
            description=(
                "Estado operativo del caso en formato JSON. "
                "Puede incluir servicio, sistema_operativo, sintoma, usuarios_afectados "
                "y pasos_probados. Usa null si no existe estado estructurado."
            ),
        ),
    ] = None,
    explicit_domain: Annotated[
        str | None,
        Field(
            description=(
                "Dominio documental opcional. Ejemplos: vpn, erp, teams, identity, support. "
                "Usa null si no estás seguro."
            ),
        ),
    ] = None,
) -> dict[str, Any]:
    case_state: dict[str, Any] | None = None

    if case_state_json:
        try:
            parsed = json.loads(case_state_json)

            if isinstance(parsed, dict):
                case_state = parsed
            else:
                return {
                    "valid": False,
                    "error": "case_state_json debe representar un objeto JSON.",
                }

        except json.JSONDecodeError as exc:
            return {
                "valid": False,
                "error": f"case_state_json no es JSON válido: {exc}",
            }

    package = build_context_package(
        user_query=user_query,
        conversation_summary=conversation_summary,
        case_state=case_state,
        explicit_domain=explicit_domain,
    )

    return {
        "valid": True,
        "package": package,
    }