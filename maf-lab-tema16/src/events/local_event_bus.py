from __future__ import annotations

import json
from pathlib import Path

from src.events.envelope import EventEnvelope


class LocalEventBus:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/events.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def publish(self, event: EventEnvelope) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def read_all(self) -> list[EventEnvelope]:
        events: list[EventEnvelope] = []

        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue

                events.append(EventEnvelope.from_dict(json.loads(line)))

        return events

    def read_by_correlation_id(self, correlation_id: str) -> list[EventEnvelope]:
        return [
            event
            for event in self.read_all()
            if event.correlation_id == correlation_id
        ]