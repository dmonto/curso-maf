from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, Callable, TypeVar


T = TypeVar("T")


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    message: str,
    **fields: Any,
) -> None:
    logger.log(
        level,
        message,
        extra={
            "event": event,
            **fields,
        },
    )


class Timer:
    def __init__(self) -> None:
        self._start = perf_counter()

    def elapsed_ms(self) -> int:
        return int((perf_counter() - self._start) * 1000)


def safe_len(value: Any) -> int | None:
    try:
        return len(value)
    except Exception:
        return None