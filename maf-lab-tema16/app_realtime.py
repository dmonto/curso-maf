from __future__ import annotations

import asyncio

from src.realtime.event import RealtimeEvent
from src.realtime.producer import produce_realtime_events
from src.realtime.processor import RealtimeProcessor


async def main() -> None:
    queue: asyncio.Queue[RealtimeEvent] = asyncio.Queue()

    producer_task = asyncio.create_task(
        produce_realtime_events(
            queue=queue,
            total_events=30,
            delay_seconds=0.2,
        )
    )

    processor = RealtimeProcessor(
        queue=queue,
        window_seconds=2.0,
    )

    processor_task = asyncio.create_task(processor.run())

    await producer_task
    await queue.join()
    await processor_task

    print("\nResumen:")
    for key, value in processor.stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())