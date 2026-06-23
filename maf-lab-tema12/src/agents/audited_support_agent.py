from __future__ import annotations

from src.audit.interaction_audit import AuditContext, AuditWriter
from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools.audited_support_tools import build_audited_support_tools


def build_audited_support_agent(
    audit_context: AuditContext,
    audit_writer: AuditWriter,
    get_turn_id,
):
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    tools = build_audited_support_tools(
        audit_context=audit_context,
        audit_writer=audit_writer,
        get_turn_id=get_turn_id,
    )

    instructions = f"""
Eres un agente de soporte técnico interno con auditoría de interacciones.

Contexto operativo:
- user_id: {audit_context.user_id}
- tenant_id: {audit_context.tenant_id}
- session_id: {audit_context.session_id}
- run_id: {audit_context.run_id}
- prompt_version: {audit_context.prompt_version}
- model_alias: {audit_context.model_alias}

Reglas:
- No afirmes que has creado tickets reales.
- Usa tools cuando necesites conocimiento interno o preparar un borrador.
- No repitas datos sensibles si aparecen redactados.
- Si falta evidencia, dilo claramente.
- Mantén respuestas breves, trazables y orientadas a soporte.
"""

    return client.as_agent(
        name=audit_context.agent_name,
        instructions=instructions,
        tools=tools,
    )