from __future__ import annotations

import asyncio
import random

from src.latency_control.event import LatencyEvent
from src.latency_control.telemetry import LatencyTelemetry


SERVICES = ["vpn", "erp", "correo", "teams"]


async def produce_latency_events(
    queue: asyncio.Queue[LatencyEvent],
    telemetry: LatencyTelemetry,
    total_events: int = 60,
    delay_seconds: float = 0.05,
) -> None:
    for index in range(total_events):
        if index % 11 == 0:
            event = LatencyEvent(
                service="erp",
                event_name="latency_spike",
                severity="critical",
                message="Pico de latencia en módulo de facturación",
                affected_users=random.randint(20, 60),
            )
        elif index % 4 == 0:
            event = LatencyEvent(
                service="vpn",
                event_name="connection_error",
                severity="high",
                message="Error de conexión remota",
                affected_users=random.randint(10, 30),
            )
        else:
            service = random.choice(SERVICES)
            event = LatencyEvent(
                service=service,
                event_name="health_signal",
                severity=random.choice(["low", "medium"]),
                message="Señal operativa de baja criticidad",
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
            severity=event.severity,
            queue_size=queue.qsize(),
        )

        await asyncio.sleep(delay_seconds)

    await queue.put(
        LatencyEvent(
            service="system",
            event_name="end_of_stream",
            severity="low",
            message="Fin del stream",
        )
    )