import asyncio
import logging
from uuid import uuid4

from src.agents.support_agent import build_support_agent
from src.observability.context import new_run_id, set_run_context
from src.observability.events import Timer, log_event
from src.observability.logging_config import configure_json_logging


logger = logging.getLogger("maf_lab.chat_cli")


WELCOME = """
Agente de soporte MAF
Comandos:
  s      salir
  reset  reiniciar conversación
"""


async def chat_loop() -> None:
    configure_json_logging(logging.INFO)

    agent_name = "maf_tools_agent"
    agent = build_support_agent()

    session = agent.create_session()
    session_id = f"cli-{uuid4().hex[:8]}"

    set_run_context(
        session_id=session_id,
        agent_name=agent_name,
    )

    log_event(
        logger,
        logging.INFO,
        "chat.started",
        "Comienza conversación CLI.",
    )

    print(WELCOME)

    while True:
        user_input = input("\nTú: ").strip()

        if not user_input:
            continue

        if user_input.lower() in {"s", "salir", "exit", "quit"}:
            log_event(
                logger,
                logging.INFO,
                "chat.completed",
                "Finaliza conversación CLI por petición del usuario.",
            )
            print("\nCerrando conversación.")
            break

        if user_input.lower() == "reset":
            session = agent.create_session()
            session_id = f"cli-{uuid4().hex[:8]}"

            set_run_context(
                session_id=session_id,
                agent_name=agent_name,
            )

            log_event(
                logger,
                logging.INFO,
                "chat.session_reset",
                "Sesión reiniciada.",
            )

            print("\nConversación reiniciada.")
            continue

        run_id = new_run_id()

        set_run_context(
            run_id=run_id,
            session_id=session_id,
            agent_name=agent_name,
        )

        timer = Timer()

        try:
            log_event(
                logger,
                logging.INFO,
                "agent.run.started",
                "Comienza turno de conversación.",
                prompt_length=len(user_input),
            )

            result = await agent.run(user_input, session=session)

            log_event(
                logger,
                logging.INFO,
                "agent.run.completed",
                "Finaliza turno de conversación.",
                duration_ms=timer.elapsed_ms(),
                success=True,
                response_length=len(str(result)),
            )

            print("\nAgente:")
            print(result)

        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "agent.run.failed",
                "Fallo durante turno de conversación.",
                duration_ms=timer.elapsed_ms(),
                success=False,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

            print("\nERROR EN LA EJECUCIÓN")
            print(type(exc).__name__)
            print(exc)


if __name__ == "__main__":
    asyncio.run(chat_loop())