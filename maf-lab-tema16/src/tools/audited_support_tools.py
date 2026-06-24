from __future__ import annotations

import json
from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from src.audit.interaction_audit import (
    AuditContext,
    AuditEvent,
    AuditWriter,
    Timer,
    safe_len,
    sha256_text,
)
from src.security.sensitive_data import sanitize_text


def _safe_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_audited_support_tools(
    audit_context: AuditContext,
    audit_writer: AuditWriter,
    get_turn_id,
) -> list:
    """
    Construye tools que emiten eventos de auditoría.

    get_turn_id es una función simple que devuelve el turn_id activo.
    """

    @tool(
        name="retrieve_support_knowledge_audited",
        description=(
            "Recupera conocimiento interno simulado de soporte. "
            "Devuelve fuentes y contenido sanitizado."
        ),
    )
    def retrieve_support_knowledge_audited(
        query: Annotated[
            str,
            Field(description="Consulta de soporte que debe buscarse en la base interna."),
        ],
        domain: Annotated[
            Literal["vpn", "erp", "mfa", "teams", "password"],
            Field(description="Dominio documental principal."),
        ],
    ) -> str:
        sanitized_query_report = sanitize_text(query, block_critical=False)
        turn_id = get_turn_id()

        with Timer() as timer:
            # Base documental simulada para laboratorio.
            docs = {
                "vpn": {
                    "source_id": "vpn_windows_11.md",
                    "text": (
                        "Para incidencias VPN en Windows 11, revisar conectividad, "
                        "reiniciar cliente VPN, validar MFA y probar otra red."
                    ),
                },
                "erp": {
                    "source_id": "erp_outage.md",
                    "text": (
                        "Si el ERP devuelve error 500 para varios usuarios, comprobar "
                        "alerta activa y escalar a operaciones."
                    ),
                },
                "mfa": {
                    "source_id": "mfa_support.md",
                    "text": "Para problemas MFA, revisar método registrado y hora del dispositivo.",
                },
                "teams": {
                    "source_id": "teams_access.md",
                    "text": "Para Teams, revisar licencia, sesión, conectividad y estado del servicio.",
                },
                "password": {
                    "source_id": "password_reset.md",
                    "text": "La recuperación de contraseña requiere validación de identidad.",
                },
            }

            doc = docs[domain]
            output = _safe_json(
                {
                    "query": sanitized_query_report.sanitized_text,
                    "domain": domain,
                    "sources": [
                        {
                            "source_id": doc["source_id"],
                            "text": doc["text"],
                            "score": 1.0,
                        }
                    ],
                    "sanitized": sanitized_query_report.has_sensitive_data,
                }
            )

        output_report = sanitize_text(output, block_critical=False)

        audit_writer.write(
            AuditEvent(
                event_type="tool_call",
                component="tool",
                action="retrieve_support_knowledge_audited",
                context=audit_context,
                turn_id=turn_id,
                allowed=True,
                duration_ms=timer.duration_ms,
                input_hash=sha256_text(sanitized_query_report.sanitized_text),
                output_hash=sha256_text(output_report.sanitized_text),
                input_length=safe_len(sanitized_query_report.sanitized_text),
                output_length=safe_len(output_report.sanitized_text),
                metadata={
                    "domain": domain,
                    "sources": [doc["source_id"]],
                    "input_sanitized": sanitized_query_report.has_sensitive_data,
                    "output_sanitized": output_report.has_sensitive_data,
                },
            )
        )

        return output_report.sanitized_text

    @tool(
        name="prepare_ticket_draft_audited",
        description=(
            "Prepara un borrador de ticket de soporte. "
            "No crea tickets reales ni llama a sistemas externos."
        ),
    )
    def prepare_ticket_draft_audited(
        service: Annotated[
            Literal["vpn", "erp", "teams", "correo"],
            Field(description="Servicio afectado."),
        ],
        priority: Annotated[
            Literal["p1", "p2", "p3"],
            Field(description="Prioridad tentativa."),
        ],
        summary: Annotated[
            str,
            Field(description="Resumen breve de la incidencia."),
        ],
    ) -> str:
        sanitized_summary_report = sanitize_text(summary, block_critical=False)
        turn_id = get_turn_id()

        with Timer() as timer:
            output = _safe_json(
                {
                    "created": False,
                    "mode": "draft_only",
                    "ticket": {
                        "service": service,
                        "priority": priority,
                        "summary": sanitized_summary_report.sanitized_text,
                    },
                }
            )

        output_report = sanitize_text(output, block_critical=False)

        audit_writer.write(
            AuditEvent(
                event_type="tool_call",
                component="tool",
                action="prepare_ticket_draft_audited",
                context=audit_context,
                turn_id=turn_id,
                allowed=True,
                duration_ms=timer.duration_ms,
                input_hash=sha256_text(sanitized_summary_report.sanitized_text),
                output_hash=sha256_text(output_report.sanitized_text),
                input_length=safe_len(sanitized_summary_report.sanitized_text),
                output_length=safe_len(output_report.sanitized_text),
                metadata={
                    "service": service,
                    "priority": priority,
                    "created_real_ticket": False,
                    "input_sanitized": sanitized_summary_report.has_sensitive_data,
                    "output_sanitized": output_report.has_sensitive_data,
                },
            )
        )

        return output_report.sanitized_text

    return [
        retrieve_support_knowledge_audited,
        prepare_ticket_draft_audited,
    ]