from __future__ import annotations

import asyncio

from src.agents.privacy_safe_agent import build_privacy_safe_agent
from src.security.sensitive_audit import write_sensitive_audit_event
from src.security.sensitive_data import sanitize_text


USER_ID = "ana@contoso.com"
SESSION_ID = "sensitive-data-lab-001"


async def main() -> None:
    agent = build_privacy_safe_agent()
    session = agent.create_session()

    print("Chat con protección de datos sensibles. Escribe 's' para salir.\n")

    while True:
        user_text = input("Tú> ").strip()

        if user_text.lower() == "s":
            break

        input_report = sanitize_text(user_text, block_critical=True)

        write_sensitive_audit_event(
            event_type="input_guard",
            user_id=USER_ID,
            session_id=SESSION_ID,
            report=input_report,
        )

        if input_report.blocked:
            print(
                "\nAgente> He detectado un posible secreto o credencial. "
                "No voy a enviarlo al modelo. Rota esa credencial si era real "
                "y vuelve a plantear la consulta sin incluir el secreto.\n"
            )
            continue

        result = await agent.run(input_report.sanitized_text, session=session)

        output_report = sanitize_text(str(result), block_critical=False)

        write_sensitive_audit_event(
            event_type="output_guard",
            user_id=USER_ID,
            session_id=SESSION_ID,
            report=output_report,
        )

        print(f"\nAgente> {output_report.sanitized_text}\n")


if __name__ == "__main__":
    asyncio.run(main())