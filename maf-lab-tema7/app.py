import asyncio
import logging

from src.agents.support_agent import build_support_agent
from src.observability.context import new_run_id, set_run_context
from src.observability.events import Timer, log_event
from src.observability.logging_config import configure_json_logging


logger = logging.getLogger("maf_lab.run_once")


async def main() -> None:
    configure_json_logging(logging.INFO)

    agent_name = "maf_tools_agent"
    run_id = new_run_id()
    session_id = "single-run"

    set_run_context(
        run_id=run_id,
        session_id=session_id,
        agent_name=agent_name,
    )

    log_event(
        logger,
        logging.INFO,
        "app.started",
        "Arranca ejecución básica de una petición.",
    )

    agent = build_support_agent()

    prompt = (
        "Tengo un usuario que indica que la VPN conecta, pero va muy lenta. "
        "Comprueba el estado del servicio, calcula un SLA p2 y prepara un borrador "
        "de ticket con la información disponible."
    )

    timer = Timer()

    try:
        log_event(
            logger,
            logging.INFO,
            "agent.run.started",
            "Comienza ejecución del agente.",
            prompt_length=len(prompt),
        )

        result = await agent.run(prompt)

        log_event(
            logger,
            logging.INFO,
            "agent.run.completed",
            "Finaliza ejecución del agente.",
            duration_ms=timer.elapsed_ms(),
            success=True,
            response_length=len(str(result)),
        )

        print("\n--- RESPUESTA DEL AGENTE ---\n")
        print(result)

    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            "agent.run.failed",
            "Fallo durante la ejecución del agente.",
            duration_ms=timer.elapsed_ms(),
            success=False,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        raise

    finally:
        log_event(
            logger,
            logging.INFO,
            "app.completed",
            "Termina ejecución básica.",
        )


if __name__ == "__main__":
    asyncio.run(main())