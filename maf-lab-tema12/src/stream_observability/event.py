from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4


Severity = Literal["low", "medium", "high", "critical"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class StreamEvent:
    service: str
    event_name: str
    severity: Severity
    message: str
    affected_users: int = 1
    source: str = "monitoring"
    event_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)