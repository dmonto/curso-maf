from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from src.realtime.event import RealtimeEvent


@dataclass(frozen=True)
class EventWindow:
    service: str
    events: list[RealtimeEvent]

    @property
    def total_events(self) -> int:
        return len(self.events)

    @property
    def max_severity(self) -> str:
        order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return max(self.events, key=lambda event: order[event.severity]).severity

    @property
    def affected_users(self) -> int:
        return sum(event.affected_users for event in self.events)


def build_windows_by_service(events: Iterable[RealtimeEvent]) -> list[EventWindow]:
    grouped: dict[str, list[RealtimeEvent]] = defaultdict(list)

    for event in events:
        grouped[event.service].append(event)

    return [
        EventWindow(service=service, events=service_events)
        for service, service_events in grouped.items()
    ]