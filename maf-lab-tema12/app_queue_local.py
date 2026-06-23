
from __future__ import annotations

import asyncio

from src.queues.local_queue import LocalQueue
from src.queues.message import QueueMessage
from src.queues.worker import QueueWorker


async def publish_messages(queue: LocalQueue) -> None:
    messages = [
        QueueMessage(
            message_type="incident.triage.requested",
            payload={
                "service": "vpn",
                "severity": "high",
                "description": "Usuarios no pueden conectar desde remoto",
                "affected_users": 25,
            },
        ),
        QueueMessage(
            message_type="incident.triage.requested",
            payload={
                "service": "erp",
                "severity": "medium",
                "description": "Lentitud en facturación",
                "affected_users": 8,
            },
        ),
        QueueMessage(
            message_type="incident.triage.requested",
            payload={
                "severity": "low",
                "description": "Mensaje inválido porque no tiene service",
            },
        ),
        QueueMessage(
            message_type="incident.triage.requested",
            payload={
                "service": "correo",
                "severity": "high",
                "description": "Error simulado para probar retry",
                "force_error": True,
            },
        ),
    ]

    for message in messages:
        await queue.send(message)
        print(f"[producer] publicado {message.message_type} {message.message_id}")


async def main() -> None:
    queue = LocalQueue(max_delivery_count=2)

    await publish_messages(queue)

    worker = QueueWorker(name="worker-1", queue=queue)

    # Hay 4 mensajes iniciales. Uno fallará y se reintentará.
    await worker.run(max_messages=5)

    print("\nResumen:")
    print(worker.stats)

    print("\nDead-letter:")
    for record in queue.dead_letter_records:
        print(
            {
                "message_id": record.message.message_id,
                "message_type": record.message.message_type,
                "delivery_count": record.message.delivery_count,
                "reason": record.reason,
            }
        )


if __name__ == "__main__":
    asyncio.run(main())