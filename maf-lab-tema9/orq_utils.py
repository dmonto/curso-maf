import asyncio
from typing import Any

from src.agents.multiagent.collaborative_agents import (
    build_conflict_resolver,
    build_final_synthesizer,
    build_identity_agent,
    build_network_agent,
    build_security_reviewer,
    build_triage_agent,
)


def extract_outputs(result: object) -> list[object]:
    if hasattr(result, "get_outputs"):
        return list(result.get_outputs())

    if hasattr(result, "outputs"):
        return list(getattr(result, "outputs"))

    events = getattr(result, "events", None)
    if events is not None:
        return [
            event.data
            for event in events
            if getattr(event, "type", None) == "output"
        ]

    return [result]


def last_output_as_text(result: object) -> str:
    outputs = extract_outputs(result)

    if not outputs:
        return ""

    return str([o for o in outputs])


def agent_result_to_text(value: Any) -> str:
    """
    Extracción tolerante para respuestas de agentes dentro de agregadores.
    """
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    agent_run_response = getattr(value, "agent_run_response", None)
    if agent_run_response is not None:
        messages = getattr(agent_run_response, "messages", None)
        if messages:
            last_message = messages[-1]
            text = getattr(last_message, "text", None)
            if text:
                return str(text)

        text = getattr(agent_run_response, "text", None)
        if text:
            return str(text)

        return str(agent_run_response)

    messages = getattr(value, "messages", None)
    if messages:
        last_message = messages[-1]
        text = getattr(last_message, "text", None)
        if text:
            return str(text)

    text = getattr(value, "text", None)
    if text:
        return str(text)

    return str(value)