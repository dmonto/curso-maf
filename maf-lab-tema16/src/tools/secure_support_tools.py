from __future__ import annotations

import json
from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from src.security.access_policy import UserAccessContext, authorize


KNOWLEDGE_BASE = [
    {
        "tenant_id": "contoso",
        "area": "vpn",
        "classification": "internal",
        "title": "Guía de diagnóstico VPN",
        "content": "Revisar MFA, red local, cliente VPN y estado del servicio.",
    },
    {
        "tenant_id": "contoso",
        "area": "correo",
        "classification": "internal",
        "title": "Incidencias frecuentes de correo",
        "content": "Validar Outlook, conectividad, cuota y estado de Exchange.",
    },
    {
        "tenant_id": "contoso",
        "area": "seguridad",
        "classification": "restricted",
        "title": "Procedimiento de cuentas comprometidas",
        "content": "Requiere equipo de seguridad o soporte avanzado.",
    },
    {
        "tenant_id": "contoso",
        "area": "facturacion",
        "classification": "confidential",
        "title": "Validación de facturas corporativas",
        "content": "Revisar estado de factura, centro de coste y aprobación.",
    },
]


def _safe_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_secure_support_tools(user_context: UserAccessContext) -> list:
    """
    Crea un catálogo de tools adaptado al usuario autenticado.

    Además de no exponer ciertas tools, cada tool vuelve a validar permisos internamente.
    """

    @tool(
        name="search_internal_knowledge",
        description=(
            "Busca documentación interna del laboratorio por área. "
            "Úsala para responder preguntas de soporte técnico cuando necesites grounding. "
            "Respeta tenant, área permitida y clasificación del documento."
        ),
    )
    def search_internal_knowledge(
        area: Annotated[
            Literal["vpn", "correo", "seguridad", "facturacion"],
            Field(description="Área documental que se quiere consultar."),
        ],
        query: Annotated[
            str,
            Field(description="Consulta del usuario resumida en pocas palabras."),
        ],
    ) -> str:
        decision = authorize(
            user_context,
            action="knowledge.search",
            area=area,
            classification="internal",
            tenant_id=user_context.tenant_id,
        )

        if not decision.allowed:
            return _safe_json(
                {
                    "allowed": False,
                    "reason": decision.reason,
                    "documents": [],
                }
            )

        results = []

        for doc in KNOWLEDGE_BASE:
            if doc["tenant_id"] != user_context.tenant_id:
                continue

            if doc["area"] != area:
                continue

            doc_decision = authorize(
                user_context,
                action="knowledge.search",
                area=doc["area"],
                classification=doc["classification"],
                tenant_id=doc["tenant_id"],
            )

            if doc_decision.allowed:
                results.append(
                    {
                        "title": doc["title"],
                        "area": doc["area"],
                        "classification": doc["classification"],
                        "content": doc["content"],
                    }
                )

        return _safe_json(
            {
                "allowed": True,
                "area": area,
                "query": query,
                "documents": results,
            }
        )

    @tool(
        name="prepare_incident_draft",
        description=(
            "Prepara un borrador de incidencia de soporte. "
            "No crea tickets reales ni modifica sistemas externos."
        ),
    )
    def prepare_incident_draft(
        service: Annotated[
            Literal["vpn", "correo", "teams", "erp"],
            Field(description="Servicio afectado por la incidencia."),
        ],
        priority: Annotated[
            Literal["p1", "p2", "p3"],
            Field(description="Prioridad tentativa del borrador."),
        ],
        description: Annotated[
            str,
            Field(description="Descripción breve de la incidencia."),
        ],
    ) -> str:
        decision = authorize(
            user_context,
            action="incident.draft",
            area=service if service in user_context.allowed_areas else None,
            classification="internal",
            tenant_id=user_context.tenant_id,
        )

        if not decision.allowed:
            return _safe_json(
                {
                    "allowed": False,
                    "created": False,
                    "reason": decision.reason,
                }
            )

        return _safe_json(
            {
                "allowed": True,
                "created": False,
                "draft": {
                    "tenant_id": user_context.tenant_id,
                    "requested_by": user_context.user_id,
                    "service": service,
                    "priority": priority,
                    "description": description,
                    "status": "draft_only",
                },
            }
        )

    @tool(
        name="get_user_security_summary",
        description=(
            "Consulta un resumen restringido de seguridad de una cuenta de usuario. "
            "Solo debe estar disponible para soporte avanzado o seguridad."
        ),
    )
    def get_user_security_summary(
        user_email: Annotated[
            str,
            Field(description="Correo corporativo del usuario que se quiere revisar."),
        ],
    ) -> str:
        decision = authorize(
            user_context,
            action="identity.read_restricted",
            area="seguridad",
            classification="restricted",
            tenant_id=user_context.tenant_id,
        )

        if not decision.allowed:
            return _safe_json(
                {
                    "allowed": False,
                    "reason": decision.reason,
                    "security_summary": None,
                }
            )

        return _safe_json(
            {
                "allowed": True,
                "security_summary": {
                    "user_email": user_email,
                    "mfa_enabled": True,
                    "recent_risk": "low",
                    "note": "Datos simulados para laboratorio.",
                },
            }
        )

    tools = [
        search_internal_knowledge,
        prepare_incident_draft,
    ]

    admin_decision = authorize(
        user_context,
        action="identity.read_restricted",
        area="seguridad",
        classification="restricted",
        tenant_id=user_context.tenant_id,
    )

    if admin_decision.allowed:
        tools.append(get_user_security_summary)

    return tools