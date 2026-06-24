from __future__ import annotations

import json
from pathlib import Path

from src.domain.incident_rules import classify_incident
from src.events.envelope import EventEnvelope
from src.events.local_event_bus import LocalEventBus


PROCESSED_PATH = Path("data/processed_event_ids.txt")


class EventWorker:
    def __init__(self) -> None:
        self.event_bus = LocalEventBus()
        PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROCESSED_PATH.touch(exist_ok=True)

    def load_processed_ids(self) -> set[str]:
        return {
            line.strip()
            for line in PROCESSED_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    def mark_processed(self, event_id: str) -> None:
        with PROCESSED_PATH.open("a", encoding="utf-8") as file:
            file.write(event_id + "\n")

    def run_once(self) -> None:
        processed_ids = self.load_processed_ids()
        events = self.event_bus.read_all()

        for event in events:
            if event.event_id in processed_ids:
                continue

            if event.event_type == "support.incident.reported.v1":
                self.handle_incident_reported(event)
                self.mark_processed(event.event_id)

    def handle_incident_reported(self, event: EventEnvelope) -> None:
        payload = event.payload

        classification = classify_incident(
            service=payload["service"],
            affected_users=int(payload["affected_users"]),
            business_impact=payload["business_impact"],
        )

        classified_event = EventEnvelope.create(
            event_type="support.incident.classified.v1",
            aggregate_id=event.aggregate_id,
            correlation_id=event.correlation_id,
            causation_id=event.event_id,
            payload={
                "incident_id": payload["incident_id"],
                "service": payload["service"],
                "summary": payload["summary"],
                "affected_users": payload["affected_users"],
                "business_impact": payload["business_impact"],
                **classification,
            },
        )

        self.event_bus.publish(classified_event)

        print(
            json.dumps(
                {
                    "processed_event_id": event.event_id,
                    "new_event_id": classified_event.event_id,
                    "correlation_id": classified_event.correlation_id,
                    "event_type": classified_event.event_type,
                    "priority": classification["priority"],
                    "recommended_team": classification["recommended_team"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    EventWorker().run_once()