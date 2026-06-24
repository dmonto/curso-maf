from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, AsyncIterable


# ---------------------------------------------------------------------
# Helpers genéricos
# ---------------------------------------------------------------------

def _class_name(value: Any) -> str:
    return value.__class__.__name__ if value is not None else "None"


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _looks_like_object_repr(text: str) -> bool:
    return text.startswith("<") and " object at 0x" in text and text.endswith(">")


def _safe_text(value: Any, *, _depth: int = 0, _seen: set[int] | None = None) -> str:
    """
    Extrae texto de forma tolerante desde Message, ChatMessage, AgentResponse,
    AgentResponseUpdate, AgentExecutorResponse, eventos de workflow, listas, tuplas o dicts.

    La función evita devolver representaciones inútiles del tipo:
    <SomeObject object at 0x...>
    """
    if value is None:
        return ""

    if _seen is None:
        _seen = set()

    if _depth > 8:
        return ""

    value_id = id(value)
    if value_id in _seen:
        return ""
    _seen.add(value_id)

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (int, float, bool)):
        return str(value)

    if isinstance(value, dict):
        for key in (
            "text",
            "content",
            "message",
            "messages",
            "delta",
            "response",
            "agent_response",
            "output",
            "value",
        ):
            if key in value:
                text = _safe_text(value[key], _depth=_depth + 1, _seen=_seen)
                if text:
                    return text

        # Último recurso: imprimir claves simples del dict
        simple_items = []
        for key, item in value.items():
            if isinstance(item, (str, int, float, bool)):
                simple_items.append(f"{key}: {item}")
        return "\n".join(simple_items)

    if isinstance(value, (list, tuple)):
        parts: list[str] = []
        for item in value:
            text = _safe_text(item, _depth=_depth + 1, _seen=_seen)
            if text:
                parts.append(text)
        return "\n".join(parts)

    # Atributos habituales en MAF/OpenAI/Message/Response/Event
    for attr in (
        "text",
        "delta",
        "content",
        "message",
        "messages",
        "agent_response",
        "response",
        "output",
        "data",
        "value",
    ):
        attr_value = getattr(value, attr, None)
        if attr_value is None:
            continue

        text = _safe_text(attr_value, _depth=_depth + 1, _seen=_seen)
        if text:
            return text

    text = str(value).strip()
    if text and not _looks_like_object_repr(text):
        return text

    return ""


def _event_parts(event: Any) -> tuple[str, str | None, Any]:
    """
    Normaliza eventos que pueden venir como:
    - tuple: (event_type, executor_id, data)
    - WorkflowEvent: event.type / event.data
    - objetos internos con executor_id / data
    """
    if isinstance(event, tuple):
        if len(event) >= 3:
            return str(_enum_value(event[0])), event[1], event[2]
        if len(event) == 2:
            return str(_enum_value(event[0])), None, event[1]

    event_type = _enum_value(getattr(event, "type", None))
    if not event_type or event_type == "None":
        event_type = _enum_value(getattr(event, "event_type", _class_name(event)))

    executor_id = (
        getattr(event, "executor_id", None)
        or getattr(event, "source", None)
        or getattr(event, "sender", None)
    )

    data = getattr(event, "data", None)
    if data is None:
        data = getattr(event, "payload", None)
    if data is None:
        data = event

    return str(event_type), executor_id, data


def _extract_author(value: Any, fallback: str | None = None) -> str:
    """
    Intenta deducir qué agente produjo un fragmento.
    Funciona con eventos group_chat, AgentResponse, AgentResponseUpdate,
    AgentExecutorResponse y objetos similares.
    """
    if value is None:
        return fallback or "unknown"

    if isinstance(value, (list, tuple)):
        for item in reversed(value):
            author = _extract_author(item, fallback=None)
            if author != "unknown":
                return author
        return fallback or "unknown"

    for attr in (
        "author_name",
        "participant_name",
        "agent_name",
        "executor_id",
        "name",
        "sender",
        "source",
        "role",
    ):
        attr_value = getattr(value, attr, None)
        if attr_value:
            return str(attr_value)

    for nested_attr in ("agent_response", "response", "message", "data"):
        nested = getattr(value, nested_attr, None)
        if nested is not None and nested is not value:
            author = _extract_author(nested, fallback=None)
            if author != "unknown":
                return author

    return fallback or "unknown"


def _is_agent_update(value: Any) -> bool:
    name = _class_name(value)
    if "AgentResponseUpdate" in name:
        return True
    if "RunUpdate" in name:
        return True
    if hasattr(value, "delta"):
        return True
    return False


def _is_agent_response(value: Any) -> bool:
    name = _class_name(value)
    if name == "AgentResponse":
        return True
    if "AgentResponse" in name and "Update" not in name:
        return True
    if getattr(value, "agent_response", None) is not None:
        return True
    return False


def _format_ledger_item(item: Any) -> str:
    if item is None:
        return ""

    answer = getattr(item, "answer", None)
    reason = getattr(item, "reason", None)

    if reason is None:
        return str(answer)

    return f"{answer} — {reason}"


# ---------------------------------------------------------------------
# Modelo interno del renderer
# ---------------------------------------------------------------------

@dataclass
class AgentMessage:
    agent: str
    text: str
    kind: str
    event_index: int
    event_type: str
    data_class: str


@dataclass
class WorkflowRenderState:
    title: str = "Resultado"
    timeline: list[str] = field(default_factory=list)
    plans: list[str] = field(default_factory=list)
    ledgers: list[str] = field(default_factory=list)
    handoffs: list[str] = field(default_factory=list)
    requests: list[str] = field(default_factory=list)
    messages_by_agent: dict[str, list[AgentMessage]] = field(default_factory=dict)
    final_answer: str = ""
    event_count: int = 0

    # Para streaming token a token
    _live_last_agent: str | None = None

    def add_agent_message(self, message: AgentMessage) -> None:
        if not message.text:
            return

        self.messages_by_agent.setdefault(message.agent, []).append(message)

        # En modo no streaming, la respuesta final suele llegar como AgentResponse.
        # En modo streaming, los updates son parciales y no deberían pisar final_answer.
        if message.kind in {"response", "executor_response", "group_chat_response", "final_output"}:
            self.final_answer = message.text

    def ingest(self, event: Any, *, live: bool = False) -> None:
        self.event_count += 1
        index = self.event_count

        event_type, executor_id, data = _event_parts(event)
        data_class = _class_name(data)

        # Eventos típicos de lifecycle
        if event_type == "executor_invoked":
            self.timeline.append(f"{index:02d}. Invocado `{executor_id}`")
            return

        if event_type == "executor_completed":
            self.timeline.append(f"{index:02d}. Completado `{executor_id}`")
            for message in _extract_agent_messages(data, index, event_type, executor_id):
                self.add_agent_message(message)
                if live:
                    self._print_live_message(message)
            return

        # GroupChatBuilder suele emitir eventos de petición/respuesta por ronda
        if event_type == "group_chat":
            self._handle_group_chat_event(index, data, live=live)
            return

        # MagenticBuilder tiene eventos específicos del orquestador
        if event_type == "magentic_orchestrator":
            self._handle_magentic_orchestrator_event(data)
            return

        # HandoffBuilder puede exponer clases/eventos con "handoff" según versión
        if "handoff" in event_type.lower() or "Handoff" in data_class:
            self._handle_handoff_event(index, event_type, executor_id, data)
            for message in _extract_agent_messages(data, index, event_type, executor_id):
                self.add_agent_message(message)
                if live:
                    self._print_live_message(message)
            return

        # Eventos de pausa / human input / request info
        if "request" in event_type.lower() or "InputRequest" in data_class or "RequestInfo" in data_class:
            text = _safe_text(data)
            self.requests.append(
                f"### Solicitud de input\n"
                f"- Evento: `{event_type}`\n"
                f"- Executor: `{executor_id or '-'}`\n"
                f"- Detalle: {text or data_class}"
            )
            return

        # En streaming, muchos builders emiten la salida como event.type == "output"
        if event_type == "output":
            messages = _extract_agent_messages(data, index, event_type, executor_id)

            if messages:
                for message in messages:
                    self.add_agent_message(message)
                    if live:
                        self._print_live_message(message)
            else:
                text = _safe_text(data)
                if text:
                    self.final_answer = text
            return

        # Supersteps: útiles para depuración profunda, pero ruidosos para lectura normal
        if event_type in {"superstep_started", "superstep_completed"}:
            return

        # Último recurso
        self.timeline.append(f"{index:02d}. {event_type} | `{executor_id or '-'}` | {data_class}")

        for message in _extract_agent_messages(data, index, event_type, executor_id):
            self.add_agent_message(message)
            if live:
                self._print_live_message(message)

    def _handle_group_chat_event(self, index: int, data: Any, *, live: bool) -> None:
        data_class = _class_name(data)

        if data_class == "GroupChatRequestSentEvent":
            round_index = getattr(data, "round_index", "?")
            participant_name = getattr(data, "participant_name", "?")
            self.timeline.append(
                f"{index:02d}. Ronda {round_index}: petición enviada a `{participant_name}`"
            )
            return

        if data_class == "GroupChatResponseReceivedEvent":
            round_index = getattr(data, "round_index", "?")
            participant_name = getattr(data, "participant_name", "?")
            self.timeline.append(
                f"{index:02d}. Ronda {round_index}: respuesta recibida de `{participant_name}`"
            )

            text = _safe_text(
                getattr(data, "response", None)
                or getattr(data, "agent_response", None)
                or getattr(data, "message", None)
                or getattr(data, "content", None)
            )

            message = AgentMessage(
                agent=str(participant_name),
                text=text,
                kind="group_chat_response",
                event_index=index,
                event_type="group_chat",
                data_class=data_class,
            )
            self.add_agent_message(message)

            if live:
                self._print_live_message(message)

            return

        self.timeline.append(f"{index:02d}. Evento group_chat: {data_class}")

    def _handle_magentic_orchestrator_event(self, data: Any) -> None:
        event_type = _enum_value(getattr(data, "event_type", ""))
        content = getattr(data, "content", None)

        if event_type == "plan_created":
            plan_text = _safe_text(content)
            self.plans.append(
                "### Plan creado\n"
                f"{plan_text if plan_text else '(plan sin texto extraíble)'}"
            )
            return

        if event_type == "progress_ledger_updated":
            request_satisfied = getattr(content, "is_request_satisfied", None)
            in_loop = getattr(content, "is_in_loop", None)
            progress = getattr(content, "is_progress_being_made", None)
            next_speaker = getattr(content, "next_speaker", None)
            instruction = getattr(content, "instruction_or_question", None)

            self.ledgers.append(
                "### Ledger de progreso\n"
                f"- Solicitud satisfecha: {_format_ledger_item(request_satisfied)}\n"
                f"- En bucle: {_format_ledger_item(in_loop)}\n"
                f"- Hay progreso: {_format_ledger_item(progress)}\n"
                f"- Siguiente agente: {_format_ledger_item(next_speaker)}\n"
                f"- Instrucción: {_format_ledger_item(instruction)}"
            )
            return

        text = _safe_text(content)
        self.timeline.append(f"Orquestador Magentic: `{event_type}` — {text}")

    def _handle_handoff_event(
        self,
        index: int,
        event_type: str,
        executor_id: str | None,
        data: Any,
    ) -> None:
        data_class = _class_name(data)
        text = _safe_text(data)

        line = f"{index:02d}. Handoff | `{executor_id or '-'}` | {data_class}"
        if text:
            line += f" | {text}"

        self.handoffs.append(line)
        self.timeline.append(line)

    def _print_live_message(self, message: AgentMessage) -> None:
        if not message.text:
            return

        # Para updates token a token, imprimimos compacto.
        if message.kind == "update":
            if self._live_last_agent != message.agent:
                print(f"\n\n[{message.agent}] ", end="", flush=True)
                self._live_last_agent = message.agent
            print(message.text, end="", flush=True)
            return

        print(f"\n\n[{message.agent} | {message.kind}]\n{message.text}", flush=True)

    def render_markdown(self, *, include_timeline: bool = True, include_updates: bool = True) -> str:
        sections: list[str] = []

        sections.append(f"### {self.title}")

        if self.plans:
            sections.append("\n\n".join(self.plans))

        if include_timeline and self.timeline:
            sections.append("### Timeline")
            sections.append("\n".join(self.timeline))

        if self.handoffs:
            sections.append("### Handoffs")
            sections.append("\n".join(self.handoffs))

        if self.requests:
            sections.append("### Solicitudes de intervención")
            sections.append("\n\n".join(self.requests))

        if self.messages_by_agent:
            sections.append("### Mensajes intermedios por agente")
            sections.append(self._render_messages_by_agent(include_updates=include_updates))

        if self.ledgers:
            sections.append("### Decisiones del orquestador")
            sections.append("\n\n".join(self.ledgers))

        sections.append("### Respuesta final")
        sections.append(
            self.final_answer
            if self.final_answer
            else "(no se pudo extraer una respuesta final limpia)"
        )

        return "\n\n".join(sections)

    def _render_messages_by_agent(self, *, include_updates: bool) -> str:
        parts: list[str] = []

        for agent, messages in self.messages_by_agent.items():
            parts.append(f"#### {agent}")

            if include_updates:
                update_text = "".join(
                    message.text
                    for message in messages
                    if message.kind == "update"
                ).strip()

                if update_text:
                    parts.append("**Streaming parcial**")
                    parts.append(update_text)

            non_updates = [
                message
                for message in messages
                if include_updates or message.kind != "update"
            ]

            # Evita repetir el streaming parcial como cientos de líneas.
            non_updates = [
                message
                for message in non_updates
                if message.kind != "update"
            ]

            for pos, message in enumerate(non_updates, start=1):
                parts.append(
                    f"**{pos}. {message.kind}** "
                    f"`{message.event_type}` / `{message.data_class}`\n\n"
                    f"{message.text}"
                )

        return "\n\n".join(parts)


# ---------------------------------------------------------------------
# Extracción genérica de mensajes de agente
# ---------------------------------------------------------------------

def _extract_agent_messages(
    data: Any,
    event_index: int,
    event_type: str,
    default_agent: str | None = None,
) -> list[AgentMessage]:
    if data is None:
        return []

    if isinstance(data, (list, tuple)):
        messages: list[AgentMessage] = []
        for item in data:
            messages.extend(
                _extract_agent_messages(
                    item,
                    event_index=event_index,
                    event_type=event_type,
                    default_agent=default_agent,
                )
            )
        return messages

    data_class = _class_name(data)

    # AgentExecutorResponse suele envolver agent_response
    agent_response = getattr(data, "agent_response", None)
    if agent_response is not None:
        agent = _extract_author(agent_response, fallback=default_agent)
        text = _safe_text(agent_response)
        return [
            AgentMessage(
                agent=agent,
                text=text,
                kind="executor_response",
                event_index=event_index,
                event_type=event_type,
                data_class=data_class,
            )
        ]

    # AgentResponseUpdate en streaming
    if _is_agent_update(data):
        agent = _extract_author(data, fallback=default_agent)
        text = _safe_text(data)
        return [
            AgentMessage(
                agent=agent,
                text=text,
                kind="update",
                event_index=event_index,
                event_type=event_type,
                data_class=data_class,
            )
        ]

    # AgentResponse completa
    if _is_agent_response(data):
        agent = _extract_author(data, fallback=default_agent)
        text = _safe_text(data)
        return [
            AgentMessage(
                agent=agent,
                text=text,
                kind="response",
                event_index=event_index,
                event_type=event_type,
                data_class=data_class,
            )
        ]

    # Mensajes sueltos
    if data_class in {"Message", "ChatMessage", "AssistantMessage", "UserMessage"}:
        agent = _extract_author(data, fallback=default_agent)
        text = _safe_text(data)
        return [
            AgentMessage(
                agent=agent,
                text=text,
                kind="message",
                event_index=event_index,
                event_type=event_type,
                data_class=data_class,
            )
        ]

    # Eventos que tengan participant_name y algún contenido textual
    if hasattr(data, "participant_name"):
        agent = _extract_author(data, fallback=default_agent)
        text = _safe_text(data)
        if text:
            return [
                AgentMessage(
                    agent=agent,
                    text=text,
                    kind="participant_event",
                    event_index=event_index,
                    event_type=event_type,
                    data_class=data_class,
                )
            ]

    return []


# ---------------------------------------------------------------------
# API pública: renderizar resultados ya terminados
# ---------------------------------------------------------------------

def extract_workflow_events(result_or_events: Any) -> list[Any]:
    """
    Acepta:
    - result de workflow.run(...)
    - result.events
    - result.get_events()
    - result.get_outputs()
    - lista de eventos
    - un único evento/objeto
    """
    if result_or_events is None:
        return []

    if isinstance(result_or_events, list):
        return result_or_events

    events = getattr(result_or_events, "events", None)
    if events is not None:
        return list(events)

    if hasattr(result_or_events, "get_events"):
        maybe_events = result_or_events.get_events()
        if inspect.isawaitable(maybe_events):
            raise TypeError("get_events() es awaitable; usa la variante async correspondiente.")
        return list(maybe_events)

    if hasattr(result_or_events, "get_outputs"):
        outputs = result_or_events.get_outputs()
        if inspect.isawaitable(outputs):
            raise TypeError("get_outputs() es awaitable; usa la variante async correspondiente.")

        outputs = list(outputs)

        if len(outputs) == 1 and isinstance(outputs[0], list):
            return outputs[0]

        return outputs

    return [result_or_events]


def render_workflow_result(
    result_or_events: Any,
    *,
    title: str = "Resultado",
    include_timeline: bool = True,
    include_updates: bool = True,
) -> str:
    state = WorkflowRenderState(title=title)

    for event in extract_workflow_events(result_or_events):
        state.ingest(event, live=False)

    return state.render_markdown(
        include_timeline=include_timeline,
        include_updates=include_updates,
    )


def print_workflow_result(
    result_or_events: Any,
    *,
    title: str = "Resultado",
    include_timeline: bool = True,
    include_updates: bool = True,
) -> None:
    print(
        render_workflow_result(
            result_or_events,
            title=title,
            include_timeline=include_timeline,
            include_updates=include_updates,
        )
    )


# ---------------------------------------------------------------------
# API pública: ejecutar en streaming y mostrar mensajes intermedios
# ---------------------------------------------------------------------

async def render_workflow_stream(
    workflow: Any,
    user_input: Any,
    *,
    title: str = "Resultado streaming",
    include_timeline: bool = True,
    include_updates: bool = True,
    live: bool = True,
    **run_kwargs: Any,
) -> str:
    """
    Ejecuta workflow.run(..., stream=True), muestra mensajes intermedios
    mientras llegan y devuelve el Markdown final.

    Uso:
        markdown = await render_workflow_stream(workflow, prompt)
        print(markdown)
    """
    state = WorkflowRenderState(title=title)

    async for event in workflow.run(user_input, stream=True, **run_kwargs):
        state.ingest(event, live=live)

    if live:
        print("\n")

    return state.render_markdown(
        include_timeline=include_timeline,
        include_updates=include_updates,
    )


async def print_workflow_stream(
    workflow: Any,
    user_input: Any,
    *,
    title: str = "Resultado streaming",
    include_timeline: bool = True,
    include_updates: bool = True,
    live: bool = True,
    **run_kwargs: Any,
) -> None:
    markdown = await render_workflow_stream(
        workflow,
        user_input,
        title=title,
        include_timeline=include_timeline,
        include_updates=include_updates,
        live=live,
        **run_kwargs,
    )
    print(markdown)