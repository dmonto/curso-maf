from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator


SUPPORT_STATE_KEY = "support_state"


_current_support_state: ContextVar[dict[str, Any] | None] = ContextVar(
    "current_support_state",
    default=None,
)


def create_initial_support_state() -> dict[str, Any]:
    return {
        "turn_count": 0,
        "active_service": None,
        "active_priority": None,
        "last_service_status": None,
        "last_severity": None,
        "last_recommended_action": None,
        "last_sla_hours": None,
        "last_sla_deadline_utc": None,
        "draft_ticket_id": None,
        "draft_ticket_status": None,
        "last_action": None,
    }


def get_session_state_bag(session: Any) -> dict[str, Any]:
    state = getattr(session, "state", None)

    if state is None:
        raise RuntimeError(
            "La sesión no expone un diccionario 'state'. "
            "Revisa la versión del framework o el tipo de sesión utilizado."
        )

    if not isinstance(state, dict):
        raise RuntimeError(
            f"session.state debería ser dict, pero se recibió {type(state).__name__}."
        )

    return state


def get_support_state(session: Any) -> dict[str, Any]:
    state_bag = get_session_state_bag(session)

    if SUPPORT_STATE_KEY not in state_bag:
        state_bag[SUPPORT_STATE_KEY] = create_initial_support_state()

    return state_bag[SUPPORT_STATE_KEY]


def reset_support_state(session: Any) -> dict[str, Any]:
    state_bag = get_session_state_bag(session)
    state_bag[SUPPORT_STATE_KEY] = create_initial_support_state()
    return state_bag[SUPPORT_STATE_KEY]


def increment_turn_count(session: Any) -> None:
    support_state = get_support_state(session)
    support_state["turn_count"] = int(support_state.get("turn_count") or 0) + 1


def update_bound_support_state(**updates: Any) -> None:
    support_state = _current_support_state.get()

    if support_state is None:
        # Permitimos que la tool funcione aunque no esté enlazada a una sesión.
        return

    for key, value in updates.items():
        if value is not None:
            support_state[key] = value


@contextmanager
def bind_support_state(session: Any) -> Iterator[dict[str, Any]]:
    support_state = get_support_state(session)
    token = _current_support_state.set(support_state)

    try:
        yield support_state
    finally:
        _current_support_state.reset(token)


def summarize_support_state(session: Any) -> str:
    support_state = get_support_state(session)

    fields = [
        ("turn_count", "Turnos acumulados"),
        ("active_service", "Servicio activo"),
        ("active_priority", "Prioridad activa"),
        ("last_service_status", "Último estado de servicio"),
        ("last_severity", "Última severidad"),
        ("last_sla_hours", "Último SLA en horas"),
        ("last_sla_deadline_utc", "Última fecha límite SLA UTC"),
        ("draft_ticket_id", "Último borrador de ticket"),
        ("draft_ticket_status", "Estado del borrador"),
        ("last_action", "Última acción relevante"),
    ]

    lines: list[str] = []

    for key, label in fields:
        value = support_state.get(key)
        if value is not None:
            lines.append(f"- {label}: {value}")

    if not lines:
        return "No hay estado estructurado relevante todavía."

    return "\n".join(lines)


def enrich_prompt_with_state(user_input: str, session: Any) -> str:
    state_summary = summarize_support_state(session)

    return f"""Contexto interno de sesión, no mostrar literalmente al usuario:
{state_summary}

Solicitud actual del usuario:
{user_input}
"""