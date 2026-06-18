import asyncio
import logging
import os
from uuid import uuid4

from src.agents.support_agent import build_structured_support_agent
from src.audit import (
    AzureConversationAuditStore,
    ConversationAuditEvent,
    hash_text,
    redact_text,
)
from src.context import ContextEnricher
from src.security import MemorySecurityGuard
from src.state import SupportSessionMemory
from src.state.coherence import CoherenceController, build_blocking_response


logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def render_result(result: object) -> str:
    for attr in ("text", "content", "message"):
        value = getattr(result, attr, None)
        if value:
            return str(value)

    return str(result)


def audit(
    store: AzureConversationAuditStore,
    *,
    event_type: str,
    user_id: str,
    session_id: str,
    run_id: str,
    actor: str,
    action: str,
    outcome: str,
    severity: str = "info",
    text: str | None = None,
    payload: dict | None = None,
) -> None:
    event = ConversationAuditEvent(
        event_type=event_type,
        user_id=user_id,
        session_id=session_id,
        run_id=run_id,
        actor=actor,
        action=action,
        outcome=outcome,
        severity=severity,
        message_preview=redact_text(text) if text else None,
        content_hash=hash_text(text) if text else None,
        payload=payload or {},
    )

    store.record_event(event)


def build_prompt(
    user_text: str,
    memory: SupportSessionMemory,
    enriched_context: dict,
    coherence_report: dict,
    security_report: dict,
) -> str:
    return f"""
Eres un agente de soporte técnico de nivel 1.

Usa memoria, contexto enriquecido y reportes de control.
No inventes datos.
No solicites contraseñas, tokens ni códigos MFA.
No digas que has creado un ticket real. Como máximo puedes preparar un borrador.

MEMORIA:
{memory.to_model_context()}

CONTEXTO ENRIQUECIDO:
{enriched_context}

REPORTE DE COHERENCIA:
{coherence_report}

REPORTE DE SEGURIDAD DE MEMORIA:
{security_report}

MENSAJE ACTUAL:
{user_text}
""".strip()


async def main() -> None:
    user_id = os.getenv("MAF_USER_ID", "usuario-demo")

    session_id = input("Session ID [caso-auditado]: ").strip()
    if not session_id:
        session_id = "caso-auditado"

    audit_store = AzureConversationAuditStore.from_env()

    agent = build_structured_support_agent()
    memory = SupportSessionMemory()
    enricher = ContextEnricher()
    security_guard = MemorySecurityGuard()
    coherence = CoherenceController()

    distributed_metadata = {
        "status": "open",
        "turn_count": 0,
    }

    last_run_id = None

    audit(
        audit_store,
        event_type="conversation_started",
        user_id=user_id,
        session_id=session_id,
        run_id=uuid4().hex,
        actor="system",
        action="start_conversation",
        outcome="started",
        payload={
            "status": distributed_metadata["status"],
        },
    )

    print("\nChat con auditoría de conversaciones")
    print(f"user_id: {user_id}")
    print(f"session_id: {session_id}")
    print("Comandos:")
    print("  /auditoria       lista eventos de auditoría")
    print("  /memoria         muestra memoria")
    print("  /cerrar          marca el caso como cerrado")
    print("  /reabrir         reabre el caso")
    print("  /salir           termina\n")

    while True:
        user_text = input("Tú> ").strip()

        if not user_text:
            continue

        command = user_text.lower()
        run_id = uuid4().hex
        last_run_id = run_id

        if command == "/salir":
            audit(
                audit_store,
                event_type="conversation_finished",
                user_id=user_id,
                session_id=session_id,
                run_id=run_id,
                actor="system",
                action="finish_conversation",
                outcome="finished",
                payload={
                    "turn_count": distributed_metadata.get("turn_count", 0),
                    "status": distributed_metadata.get("status", "open"),
                },
            )
            print("Sesión finalizada.")
            break

        if command == "/auditoria":
            events = audit_store.list_events(
                user_id=user_id,
                session_id=session_id,
            )

            print("\n--- EVENTOS DE AUDITORÍA ---")
            for event in events:
                print(
                    f"{event['created_utc']} | "
                    f"{event['severity']} | "
                    f"{event['event_type']} | "
                    f"{event['action']} | "
                    f"{event['outcome']}"
                )
            print()
            continue

        if command == "/memoria":
            print("\n--- MEMORIA ---")
            print(memory.to_json())
            print()
            continue

        if command == "/cerrar":
            distributed_metadata["status"] = "closed"
            audit(
                audit_store,
                event_type="case_status_changed",
                user_id=user_id,
                session_id=session_id,
                run_id=run_id,
                actor="system",
                action="close_case",
                outcome="closed",
                payload=distributed_metadata,
            )
            print("Caso marcado como cerrado.\n")
            continue

        if command == "/reabrir":
            distributed_metadata["status"] = "open"
            audit(
                audit_store,
                event_type="case_status_changed",
                user_id=user_id,
                session_id=session_id,
                run_id=run_id,
                actor="system",
                action="reopen_case",
                outcome="open",
                payload=distributed_metadata,
            )
            print("Caso reabierto.\n")
            continue

        audit(
            audit_store,
            event_type="user_message_received",
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
            actor="user",
            action="send_message",
            outcome="received",
            text=user_text,
            payload={
                "message_length": len(user_text),
            },
        )

        memory.update_from_user_text(user_text)

        sanitized_memory, security_report = security_guard.sanitize_memory(
            memory.to_dict()
        )

        audit(
            audit_store,
            event_type="memory_security_checked",
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
            actor="system",
            action="sanitize_memory",
            outcome=security_report.sensitivity(),
            severity="warning" if security_report.sensitivity() != "low" else "info",
            payload=security_report.to_dict(),
        )

        memory = SupportSessionMemory(**sanitized_memory)

        enriched = enricher.enrich(
            user_id=user_id,
            user_text=user_text,
            memory_service=memory.servicio,
        )

        audit(
            audit_store,
            event_type="context_enriched",
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
            actor="system",
            action="enrich_context",
            outcome="enriched",
            payload=enriched.to_dict(),
        )

        coherence_report = coherence.validate(
            user_text=user_text,
            memory=memory.to_dict(),
            enriched_context=enriched.to_dict(),
            distributed_metadata=distributed_metadata,
        )

        audit(
            audit_store,
            event_type="coherence_checked",
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
            actor="system",
            action="validate_coherence",
            outcome=coherence_report.status(),
            severity=coherence_report.status(),
            payload=coherence_report.to_dict(),
        )

        if coherence_report.has_blocking:
            response = build_blocking_response(coherence_report)

            audit(
                audit_store,
                event_type="agent_response_generated",
                user_id=user_id,
                session_id=session_id,
                run_id=run_id,
                actor="agent",
                action="return_blocking_response",
                outcome="blocked",
                severity="blocking",
                text=response,
                payload={
                    "reason": "coherence_blocking",
                },
            )

            print("\nAgente>")
            print(response)
            print()
            continue

        prompt = build_prompt(
            user_text=user_text,
            memory=memory,
            enriched_context=enriched.to_dict(),
            coherence_report=coherence_report.to_dict(),
            security_report=security_report.to_dict(),
        )

        result = await agent.run(prompt)
        assistant_text = render_result(result)

        distributed_metadata["turn_count"] = int(
            distributed_metadata.get("turn_count", 0)
        ) + 1

        audit(
            audit_store,
            event_type="agent_response_generated",
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
            actor="agent",
            action="generate_response",
            outcome="completed",
            text=assistant_text,
            payload={
                "turn_count": distributed_metadata["turn_count"],
                "last_run_id": last_run_id,
            },
        )

        print("\nAgente>")
        print(assistant_text)
        print()


if __name__ == "__main__":
    asyncio.run(main())