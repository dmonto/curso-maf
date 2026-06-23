from __future__ import annotations

import asyncio

from src.agents.audited_support_agent import build_audited_support_agent
from src.audit.interaction_audit import (
    AuditContext,
    AuditEvent,
    AuditWriter,
    Timer,
    new_run_id,
    new_turn_id,
    safe_len,
    sha256_text,
)
from src.security.sensitive_data import sanitize_text


class TurnState:
    def __init__(self) -> None:
        self.turn_id = "turn-0000"

    def set(self, turn_id: str) -> None:
        self.turn_id = turn_id

    def get(self) -> str:
        return self.turn_id


async def main() -> None:
    audit_writer = AuditWriter()
    run_id = new_run_id()
    turn_state = TurnState()

    audit_context = AuditContext(
        user_id="ana@contoso.com",
        tenant_id="contoso",
        session_id="session-audit-lab-001",
        run_id=run_id,
        agent_name="audited_support_agent",
        prompt_version="support_prompt_v1",
        model_alias="chat_default",
    )

    agent = build_audited_support_agent(
        audit_context=audit_context,
        audit_writer=audit_writer,
        get_turn_id=turn_state.get,
    )

    session = agent.create_session()

    audit_writer.write(
        AuditEvent(
            event_type="session_started",
            component="application",
            action="start_session",
            context=audit_context,
            turn_id="turn-0000",
            allowed=True,
            metadata={
                "channel": "cli",
                "environment": "local_lab",
            },
        )
    )

    print("Agente auditado. Escribe 's' para salir.\n")

    turn_index = 1

    while True:
        raw_input = input("Tú> ").strip()

        if raw_input.lower() == "s":
            break

        turn_id = new_turn_id(turn_index)
        turn_state.set(turn_id)
        turn_index += 1

        input_report = sanitize_text(raw_input, block_critical=True)

        audit_writer.write(
            AuditEvent(
                event_type="user_message_received",
                component="input_guard",
                action="sanitize_user_input",
                context=audit_context,
                turn_id=turn_id,
                allowed=not input_report.blocked,
                input_hash=sha256_text(input_report.sanitized_text),
                input_length=safe_len(input_report.sanitized_text),
                metadata={
                    "has_sensitive_data": input_report.has_sensitive_data,
                    "highest_level": input_report.highest_level.value,
                    "blocked": input_report.blocked,
                    "match_kinds": [match.kind for match in input_report.matches],
                },
            )
        )

        if input_report.blocked:
            print(
                "\nAgente> He detectado un posible secreto o credencial. "
                "No voy a enviarlo al modelo. El evento ha quedado auditado.\n"
            )
            continue

        try:
            with Timer() as timer:
                result = await agent.run(input_report.sanitized_text, session=session)

            output_report = sanitize_text(str(result), block_critical=False)

            audit_writer.write(
                AuditEvent(
                    event_type="assistant_response_generated",
                    component="agent",
                    action="agent_run",
                    context=audit_context,
                    turn_id=turn_id,
                    allowed=True,
                    duration_ms=timer.duration_ms,
                    input_hash=sha256_text(input_report.sanitized_text),
                    output_hash=sha256_text(output_report.sanitized_text),
                    input_length=safe_len(input_report.sanitized_text),
                    output_length=safe_len(output_report.sanitized_text),
                    metadata={
                        "output_sanitized": output_report.has_sensitive_data,
                    },
                )
            )

            print(f"\nAgente> {output_report.sanitized_text}\n")

        except Exception as exc:
            audit_writer.write(
                AuditEvent(
                    event_type="agent_error",
                    component="agent",
                    action="agent_run",
                    context=audit_context,
                    turn_id=turn_id,
                    allowed=False,
                    error_type=type(exc).__name__,
                    error_message=str(exc)[:500],
                )
            )
            raise

    audit_writer.write(
        AuditEvent(
            event_type="session_finished",
            component="application",
            action="finish_session",
            context=audit_context,
            turn_id=turn_state.get(),
            allowed=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())