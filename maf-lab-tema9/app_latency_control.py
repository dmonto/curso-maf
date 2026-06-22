from __future__ import annotations

import asyncio
import json

from src.latency_control.event import LatencyEvent
from src.latency_control.producer import produce_latency_events
from src.latency_control.processor import LatencyControlledProcessor
from src.latency_control.telemetry import LatencyTelemetry


async def monitor_queue(
    queue: asyncio.Queue[LatencyEvent],
    telemetry: LatencyTelemetry,
    interval_seconds: float = 1.0,
) -> None:
    while True:
        queue_size = queue.qsize()

        telemetry.log(
            "queue_observed",
            queue_size=queue_size,
        )

        if queue_size > 30:
            telemetry.log(
                "local_alert",
                alert_name="queue_backpressure",
                severity="warning",
                queue_size=queue_size,
            )

        await asyncio.sleep(interval_seconds)


async def main() -> None:
    telemetry = LatencyTelemetry()
    queue: asyncio.Queue[LatencyEvent] = asyncio.Queue(maxsize=100)

    producer_task = asyncio.create_task(
        produce_latency_events(
            queue=queue,
            telemetry=telemetry,
            total_events=60,
            delay_seconds=0.05,
        )
    )

    processor = LatencyControlledProcessor(
        queue=queue,
        telemetry=telemetry,
        window_seconds=2.0,
        max_concurrent_agent_calls=2,
    )

    processor_task = asyncio.create_task(processor.run())
    monitor_task = asyncio.create_task(monitor_queue(queue, telemetry))

    await producer_task
    await queue.join()
    await processor_task

    monitor_task.cancel()
    await asyncio.gather(monitor_task, return_exceptions=True)

    print("\nResumen de control de latencia:")
    print(json.dumps(telemetry.summary(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())