from __future__ import annotations

import asyncio

from src.event_persistence.store import EventStore
from src.event_persistence.worker import PersistentEventWorker


async def main() -> None:
    store = EventStore(db_path="event_store.db")

    changed = store.reset_failed_for_replay()
    print(f"Eventos preparados para replay: {changed}")

    worker = PersistentEventWorker(store=store, max_attempts=3)
    await worker.process_pending(max_events=10)


if __name__ == "__main__":
    asyncio.run(main())