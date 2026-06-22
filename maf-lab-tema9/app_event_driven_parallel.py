

from __future__ import annotations

import asyncio

from src.events.producer import publish_demo_events
from src.events.schemas import EventEnvelope
from src.events.worker import EventWorker


async def main() -> None:
    queue: asyncio.Queue[EventEnvelope] = asyncio.Queue()

    await publish_demo_events(queue)

    workers = [
        EventWorker(),
        EventWorker(),
    ]

    tasks = [
        asyncio.create_task(worker.run(queue, stop_after=2))
        for worker in workers
    ]

    await asyncio.gather(*tasks)
    await queue.join()


if __name__ == "__main__":
    asyncio.run(main())