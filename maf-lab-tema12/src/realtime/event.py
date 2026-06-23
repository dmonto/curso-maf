# src/realtime/event.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4


Severity = Literal["low", "medium", "high", "critical"]


@dataclass(frozen=True)
class RealtimeEvent:
    service: str
    event_name: str
    severity: Severity
    message: str
    affected_users: int = 1
    source: str = "monitoring"
    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )