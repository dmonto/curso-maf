from __future__ import annotations

import asyncio

from src.agents.exposure_controlled_agent import build_exposure_controlled_agent
from src.identity.demo_users import get_demo_identity
from src.security.model_exposure import decide_model_exposure, shield_model_output
from src.security.sensitive_data import sanitize_text

from dotenv import load_dotenv

load_dotenv()

async def main() -> None:
    print("Identidades demo disponibles: ana, bruno, carla")
    alias = input("Identidad> ").strip()

    identity = get_demo_identity(alias)

    requested_model_alias = input(
        "Modelo lógico solicitado [chat_fast/chat_default/chat_quality] "
        "(deja vacío para automático)> "
    ).strip() or None

    print("\nEscribe 's' para salir.\n")

    agent = None
    session = None
    active_model_alias = None

    while True:
        raw_text = input("Tú> ").strip()

        if raw_text.lower() == "s":
            break

        input_report = sanitize_text(raw_text, block_critical=True)

        if input_report.blocked:
            print(
                "\nAgente> He detectado un posible secreto o credencial. "
                "No voy a enviarlo al modelo.\n"
            )
            continue

        decision = decide_model_exposure(
            identity=identity,
            user_text=input_report.sanitized_text,
            requested_model_alias=requested_model_alias,
            environment="local",
        )

        if not decision.allowed:
            print(f"\nAgente> {decision.safe_message}\n")
            continue

        if agent is None or active_model_alias != decision.model_alias:
            active_model_alias = decision.model_alias
            agent = build_exposure_controlled_agent(
                identity=identity,
                model_alias=active_model_alias,
            )
            session = agent.create_session()

        result = await agent.run(input_report.sanitized_text, session=session)
        safe_output = shield_model_output(str(result))

        print(f"\nAgente> {safe_output}\n")


if __name__ == "__main__":
    asyncio.run(main())