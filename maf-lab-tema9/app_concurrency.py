from __future__ import annotations

import asyncio
import json

from src.concurrency.producer import publish_support_jobs
from src.concurrency.processor import ConcurrentJobProcessor
from src.concurrency.schemas import SupportJob
from src.concurrency.state import ConcurrentStateStore


async def main() -> None:
    queue: asyncio.Queue[SupportJob] = asyncio.Queue(maxsize=20)
    state_store = ConcurrentStateStore()

    await publish_support_jobs(queue=queue, total_jobs=12)

    processor = ConcurrentJobProcessor(
        queue=queue,
        state_store=state_store,
        worker_count=4,
        max_concurrent_agent_calls=2,
        job_timeout_seconds=60,
    )

    await processor.run()

    snapshot = await state_store.snapshot()

    print("\nResumen de concurrencia:")
    print(json.dumps(snapshot, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())