from __future__ import annotations

import logging
from typing import Any

from src.observability.events import Timer, log_event
from src.state.session_state import (
    bind_support_state,
    enrich_prompt_with_state,
    increment_turn_count,
)


logger = logging.getLogger("maf_lab.agent_runner")


async def run_agent_with_basic_state(
    *,
    agent: Any,
    user_input: str,
    session: Any,
) -> Any:
    timer = Timer()

    increment_turn_count(session)

    enriched_prompt = enrich_prompt_with_state(
        user_input=user_input,
        session=session,
    )

    with bind_support_state(session):
        log_event(
            logger,
            logging.INFO,
            "agent.state_run.started",
            "Comienza ejecución del agente con estado básico.",
            prompt_length=len(user_input),
            enriched_prompt_length=len(enriched_prompt),
        )

        try:
            result = await agent.run(enriched_prompt, session=session)

            log_event(
                logger,
                logging.INFO,
                "agent.state_run.completed",
                "Finaliza ejecución del agente con estado básico.",
                duration_ms=timer.elapsed_ms(),
                success=True,
                response_length=len(str(result)),
            )

            return result

        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "agent.state_run.failed",
                "Fallo en ejecución del agente con estado básico.",
                duration_ms=timer.elapsed_ms(),
                success=False,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise