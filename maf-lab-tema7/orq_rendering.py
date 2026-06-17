from typing import Any


def _class_name(value: Any) -> str:
    return value.__class__.__name__


def _enum_value(value: Any) -> str:
    return getattr(value, "value", str(value))


def _safe_text(value: Any) -> str:
    """
    Extrae texto de forma tolerante desde Message, AgentResponse u otros objetos.
    Evita mostrar solo '<object at 0x...>' cuando hay contenido útil.
    """
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    for attr in ("text", "content"):
        attr_value = getattr(value, attr, None)

        if isinstance(attr_value, str) and attr_value.strip():
            return attr_value.strip()

        if isinstance(attr_value, list):
            parts: list[str] = []
            for item in attr_value:
                item_text = _safe_text(item)
                if item_text:
                    parts.append(item_text)
            if parts:
                return "\n".join(parts)

    message = getattr(value, "message", None)
    if message is not None:
        text = _safe_text(message)
        if text:
            return text

    messages = getattr(value, "messages", None)
    if messages:
        parts = [_safe_text(message) for message in messages]
        parts = [part for part in parts if part]
        if parts:
            return "\n".join(parts)

    agent_response = getattr(value, "agent_response", None)
    if agent_response is not None:
        text = _safe_text(agent_response)
        if text:
            return text

    return str(value)


def _event_parts(event: Any) -> tuple[str, str | None, Any]:
    """
    Normaliza eventos que pueden venir como:
    - tupla: (event_type, executor_id, data)
    - objeto con atributos type / executor_id / data
    """
    if isinstance(event, tuple) and len(event) >= 3:
        return str(event[0]), event[1], event[2]

    event_type = getattr(event, "type", _class_name(event))
    executor_id = getattr(event, "executor_id", None)
    data = getattr(event, "data", event)

    return str(event_type), executor_id, data


def extract_magentic_events(result_or_events: Any) -> list[Any]:
    """
    Acepta:
    - result de workflow.run(...)
    - result.events
    - result.get_outputs()
    - lista de eventos
    """
    if isinstance(result_or_events, list):
        return result_or_events

    events = getattr(result_or_events, "events", None)
    if events is not None:
        return list(events)

    if hasattr(result_or_events, "get_events"):
        return list(result_or_events.get_events())

    if hasattr(result_or_events, "get_outputs"):
        outputs = list(result_or_events.get_outputs())

        if len(outputs) == 1 and isinstance(outputs[0], list):
            return outputs[0]

        return outputs

    return [result_or_events]


def _format_ledger_item(item: Any) -> str:
    if item is None:
        return ""

    answer = getattr(item, "answer", None)
    reason = getattr(item, "reason", None)

    if reason is None:
        return str(answer)

    return f"{answer} — {reason}"


def _format_magentic_orchestrator_event(data: Any) -> list[str]:
    lines: list[str] = []

    event_type = _enum_value(getattr(data, "event_type", ""))
    content = getattr(data, "content", None)

    if event_type == "plan_created":
        plan_text = _safe_text(content)
        lines.append("### Plan creado")
        lines.append(plan_text if plan_text else "(plan sin texto extraíble)")
        return lines

    if event_type == "progress_ledger_updated":
        lines.append("### Ledger de progreso")

        request_satisfied = getattr(content, "is_request_satisfied", None)
        in_loop = getattr(content, "is_in_loop", None)
        progress = getattr(content, "is_progress_being_made", None)
        next_speaker = getattr(content, "next_speaker", None)
        instruction = getattr(content, "instruction_or_question", None)

        lines.append(f"- Solicitud satisfecha: {_format_ledger_item(request_satisfied)}")
        lines.append(f"- En bucle: {_format_ledger_item(in_loop)}")
        lines.append(f"- Hay progreso: {_format_ledger_item(progress)}")
        lines.append(f"- Siguiente agente: {_format_ledger_item(next_speaker)}")
        lines.append(f"- Instrucción: {_format_ledger_item(instruction)}")

        return lines

    lines.append(f"### Evento Magentic: {event_type}")
    lines.append(_safe_text(content))

    return lines


def _extract_agent_response_text(data: Any) -> str:
    """
    Busca una respuesta de agente dentro de estructuras típicas:
    - AgentResponse
    - AgentExecutorResponse
    - list[AgentExecutorResponse, AgentResponse]
    """
    if data is None:
        return ""

    if _class_name(data) == "AgentResponse":
        return _safe_text(data)

    agent_response = getattr(data, "agent_response", None)
    if agent_response is not None:
        return _safe_text(agent_response)

    if isinstance(data, list):
        for item in reversed(data):
            text = _extract_agent_response_text(item)
            if text:
                return text

    if isinstance(data, tuple):
        for item in reversed(data):
            text = _extract_agent_response_text(item)
            if text:
                return text

    return ""


def render_magentic_result(result_or_events: Any) -> str:
    events = extract_magentic_events(result_or_events)

    timeline: list[str] = []
    ledgers: list[str] = []
    plans: list[str] = []
    final_answer = ""

    for index, event in enumerate(events, start=1):
        event_type, executor_id, data = _event_parts(event)
        data_class = _class_name(data)

        if event_type == "executor_invoked":
            timeline.append(f"{index:02d}. Invocado `{executor_id}`")

        elif event_type == "executor_completed":
            timeline.append(f"{index:02d}. Completado `{executor_id}`")

            response_text = _extract_agent_response_text(data)
            if response_text:
                final_answer = response_text

        elif event_type == "group_chat":
            if data_class == "GroupChatRequestSentEvent":
                round_index = getattr(data, "round_index", "?")
                participant_name = getattr(data, "participant_name", "?")
                timeline.append(
                    f"{index:02d}. Ronda {round_index}: petición enviada a `{participant_name}`"
                )

            elif data_class == "GroupChatResponseReceivedEvent":
                round_index = getattr(data, "round_index", "?")
                participant_name = getattr(data, "participant_name", "?")
                timeline.append(
                    f"{index:02d}. Ronda {round_index}: respuesta recibida de `{participant_name}`"
                )

            else:
                timeline.append(f"{index:02d}. Evento group_chat: {data_class}")

        elif event_type == "magentic_orchestrator":
            formatted = _format_magentic_orchestrator_event(data)
            joined = "\n".join(formatted)

            if "Plan creado" in joined:
                plans.append(joined)
            elif "Ledger de progreso" in joined:
                ledgers.append(joined)
            else:
                timeline.append(f"{index:02d}. Orquestador: {data_class}")

        elif event_type in {"superstep_started", "superstep_completed"}:
            # Ruido útil para depuración, pero normalmente no hace falta mostrarlo.
            continue

        else:
            timeline.append(f"{index:02d}. {event_type} | {executor_id or '-'} | {data_class}")

    sections: list[str] = []

    sections.append("# Resultado MagenticBuilder")

    if plans:
        sections.append("\n".join(plans))

    if timeline:
        sections.append("### Timeline")
        sections.append("\n".join(timeline))

    if ledgers:
        sections.append("### Decisiones del orquestador")
        sections.append("\n\n".join(ledgers))

    sections.append("### Respuesta final")
    sections.append(final_answer if final_answer else "(no se pudo extraer una respuesta final limpia)")

    return "\n\n".join(sections)


def print_magentic_result(result_or_events: Any) -> None:
    print(render_magentic_result(result_or_events))