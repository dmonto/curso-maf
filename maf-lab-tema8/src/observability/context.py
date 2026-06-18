from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4


_current_run_id: ContextVar[str | None] = ContextVar("run_id", default=None)
_current_session_id: ContextVar[str | None] = ContextVar("session_id", default=None)
_current_agent_name: ContextVar[str | None] = ContextVar("agent_name", default=None)


def new_run_id() -> str:
    return uuid4().hex


def set_run_context(
    *,
    run_id: str | None = None,
    session_id: str | None = None,
    agent_name: str | None = None,
) -> None:
    if run_id is not None:
        _current_run_id.set(run_id)

    if session_id is not None:
        _current_session_id.set(session_id)

    if agent_name is not None:
        _current_agent_name.set(agent_name)


def get_run_id() -> str | None:
    return _current_run_id.get()


def get_session_id() -> str | None:
    return _current_session_id.get()


def get_agent_name() -> str | None:
    return _current_agent_name.get()