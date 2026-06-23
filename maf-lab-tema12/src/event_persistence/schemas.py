from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


EventStatus = Literal[
    "received",
    "processing",
    "processed",
    "failed",
    "dead_letter",
]


@dataclass(frozen=True)
class IncomingEvent:
    source: str
    external_id: str
    event_type: str
    payload: dict[str, Any]
    schema_version: str = "1.0"
    event_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()