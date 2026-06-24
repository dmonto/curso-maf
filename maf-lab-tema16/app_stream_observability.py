# 

from __future__ import annotations

import asyncio
import json

from src.stream_observability.event import StreamEvent
from src.stream_observability.producer import produce_events
from src.stream_observability.processor import ObservableStreamProcessor
from src.stream_observability.telemetry import Telemetry


async def monitor_queue(
    queue: asyncio.Queue[StreamEvent],
    telemetry: Telemetry,
    interval_seconds: float = 1.0,
) -> None:
    while True:
        telemetry.log(
            "queue_observed",
            queue_size=queue.qsize(),
        )

        telemetry.observe_latency(
            "queue_size_observed",
            float(queue.qsize()),
        )

        await asyncio.sleep(interval_seconds)


async def main() -> None:
    telemetry = Telemetry()
    queue: asyncio.Queue[StreamEvent] = asyncio.Queue(maxsize=100)

    producer_task = asyncio.create_task(
        produce_events(
            queue=queue,
            telemetry=telemetry,
            total_events=40,
            delay_seconds=0.1,
        )
    )

    processor = ObservableStreamProcessor(
        queue=queue,
        telemetry=telemetry,
        window_seconds=2.0,
        max_concurrent_agent_calls=2,
    )

    processor_task = asyncio.create_task(processor.run())
    monitor_task = asyncio.create_task(
        monitor_queue(queue=queue, telemetry=telemetry)
    )

    await producer_task
    await queue.join()
    await processor_task

    monitor_task.cancel()
    await asyncio.gather(monitor_task, return_exceptions=True)

    print("\nResumen de observabilidad:")
    print(json.dumps(telemetry.summary(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())