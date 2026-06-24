from __future__ import annotations

import asyncio
import random

from src.stream_observability.event import StreamEvent
from src.stream_observability.telemetry import Telemetry


SERVICES = ["vpn", "erp", "correo", "teams"]


async def produce_events(
    queue: asyncio.Queue[StreamEvent],
    telemetry: Telemetry,
    total_events: int = 40,
    delay_seconds: float = 0.1,
) -> None:
    for index in range(total_events):
        if index % 5 == 0:
            event = StreamEvent(
                service="vpn",
                event_name="connection_error",
                severity="high",
                message="Error de conexión remota",
                affected_users=random.randint(10, 40),
            )
        elif index % 13 == 0:
            event = StreamEvent(
                service="erp",
                event_name="latency_spike",
                severity="critical",
                message="Pico de latencia en facturación",
                affected_users=random.randint(20, 60),
            )
        else:
            service = random.choice(SERVICES)
            event = StreamEvent(
                service=service,
                event_name="health_signal",
                severity=random.choice(["low", "medium"]),
                message="Señal operativa sin impacto crítico",
                affected_users=random.randint(1, 5),
            )

        await queue.put(event)

        telemetry.increment(
            "events_received_total",
            service=event.service,
            severity=event.severity,
        )

        telemetry.log(
            "event_received",
            event_id=event.event_id,
            correlation_id=event.correlation_id,
            service=event.service,
            stream_event_name=event.event_name,
            severity=event.severity,
            queue_size=queue.qsize(),
        )

        await asyncio.sleep(delay_seconds)

    await queue.put(
        StreamEvent(
            service="system",
            event_name="end_of_stream",
            severity="low",
            message="Fin del stream",
        )
    )