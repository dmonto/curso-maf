from __future__ import annotations

import asyncio
from dataclasses import dataclass

from src.queues.message import QueueMessage


@dataclass
class DeadLetterRecord:
    message: QueueMessage
    reason: str


class LocalQueue:
    def __init__(self, max_delivery_count: int = 3) -> None:
        self._queue: asyncio.Queue[QueueMessage] = asyncio.Queue()
        self._dead_letter: list[DeadLetterRecord] = []
        self._max_delivery_count = max_delivery_count

    async def send(self, message: QueueMessage) -> None:
        await self._queue.put(message)

    async def receive(self) -> QueueMessage:
        message = await self._queue.get()
        message.delivery_count += 1
        return message

    async def complete(self, message: QueueMessage) -> None:
        self._queue.task_done()

    async def abandon(self, message: QueueMessage, reason: str) -> None:
        self._queue.task_done()

        if message.delivery_count >= self._max_delivery_count:
            self._dead_letter.append(
                DeadLetterRecord(message=message, reason=reason)
            )
            return

        await self._queue.put(message)

    async def dead_letter(self, message: QueueMessage, reason: str) -> None:
        self._queue.task_done()
        self._dead_letter.append(
            DeadLetterRecord(message=message, reason=reason)
        )

    async def join(self) -> None:
        await self._queue.join()

    @property
    def dead_letter_records(self) -> list[DeadLetterRecord]:
        return self._dead_letter