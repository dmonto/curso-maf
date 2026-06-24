from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    event_type: str
    schema_version: int
    aggregate_id: str
    correlation_id: str
    causation_id: str | None
    occurred_at_utc: str
    payload: dict[str, Any]

    @staticmethod
    def create(
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        causation_id: str | None = None,
        schema_version: int = 1,
    ) -> "EventEnvelope":
        return EventEnvelope(
            event_id=f"evt-{uuid4().hex}",
            event_type=event_type,
            schema_version=schema_version,
            aggregate_id=aggregate_id,
            correlation_id=correlation_id or f"corr-{uuid4().hex[:10]}",
            causation_id=causation_id,
            occurred_at_utc=datetime.now(timezone.utc).isoformat(),
            payload=payload,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "EventEnvelope":
        return EventEnvelope(
            event_id=data["event_id"],
            event_type=data["event_type"],
            schema_version=int(data["schema_version"]),
            aggregate_id=data["aggregate_id"],
            correlation_id=data["correlation_id"],
            causation_id=data.get("causation_id"),
            occurred_at_utc=data["occurred_at_utc"],
            payload=dict(data["payload"]),
        )