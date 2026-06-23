# src/realtime/producer.py

from __future__ import annotations

import asyncio
import random

from src.realtime.event import RealtimeEvent


SERVICES = ["vpn", "erp", "correo", "teams"]


async def produce_realtime_events(
    queue: asyncio.Queue[RealtimeEvent],
    total_events: int = 30,
    delay_seconds: float = 0.2,
) -> None:
    for index in range(total_events):
        service = random.choice(SERVICES)

        if service == "vpn" and index % 3 == 0:
            event = RealtimeEvent(
                service="vpn",
                event_name="connection_error",
                severity="high",
                message="Error de conexión remota",
                affected_users=random.randint(5, 20),
            )
        else:
            event = RealtimeEvent(
                service=service,
                event_name="health_signal",
                severity=random.choice(["low", "medium"]),
                message="Señal operativa sin impacto crítico",
                affected_users=random.randint(1, 3),
            )

        await queue.put(event)
        print(f"[producer] {event.service} {event.severity} {event.event_id}")

        await asyncio.sleep(delay_seconds)

    await queue.put(
        RealtimeEvent(
            service="system",
            event_name="end_of_stream",
            severity="low",
            message="Fin del stream de laboratorio",
        )
    )