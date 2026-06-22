from __future__ import annotations

import asyncio
import json

from src.event_persistence.producer import publish_demo_events
from src.event_persistence.store import EventStore
from src.event_persistence.worker import PersistentEventWorker


def print_event_summary(store: EventStore) -> None:
    events = store.list_events()

    print("\nResumen del Event Store:")

    for event in events:
        print(
            json.dumps(
                {
                    "event_id": event["event_id"],
                    "source": event["source"],
                    "external_id": event["external_id"],
                    "event_type": event["event_type"],
                    "status": event["status"],
                    "attempts": event["attempts"],
                    "error": event["error"],
                    "has_result": event["result"] is not None,
                },
                indent=2,
                ensure_ascii=False,
            )
        )


async def main() -> None:
    store = EventStore(db_path="event_store.db")

    publish_demo_events(store)

    worker = PersistentEventWorker(
        store=store,
        max_attempts=2,
    )

    await worker.process_pending(max_events=10)

    print_event_summary(store)


if __name__ == "__main__":
    asyncio.run(main())