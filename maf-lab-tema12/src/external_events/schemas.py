
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class CanonicalEvent:
    source: str
    event_type: str
    payload: dict[str, Any]
    external_id: str
    event_id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: str = "1.0"
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    received_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )