from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class JsonlEventPublisher:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/clean_arch_events.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def publish(self, event_type: str, payload: dict, correlation_id: str) -> None:
        event = {
            "event_id": f"evt-{uuid4().hex}",
            "event_type": event_type,
            "schema_version": 1,
            "correlation_id": correlation_id,
            "occurred_at_utc": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }

        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")