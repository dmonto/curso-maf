from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone

from src.agents.support_agent_safe import build_support_agent
from src.stream_observability.event import StreamEvent
from src.stream_observability.telemetry import Telemetry


class ObservableStreamProcessor:
    def __init__(
        self,
        queue: asyncio.Queue[StreamEvent],
        telemetry: Telemetry,
        window_seconds: float = 2.0,
        max_concurrent_agent_calls: int = 2,
    ) -> None:
        self.queue = queue
        self.telemetry = telemetry
        self.window_seconds = window_seconds
        self.agent = build_support_agent()
        self.agent_semaphore = asyncio.Semaphore(max_concurrent_agent_calls)

    async def run(self) -> None:
        buffer: list[StreamEvent] = []

        while True:
            try:
                event = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=self.window_seconds,
                )

                if event.event_name == "end_of_stream":
                    await self._flush(buffer)
                    buffer.clear()
                    self.queue.task_done()
                    break

                lag_ms = self._lag_ms(event)

                self.telemetry.observe_latency(
                    "event_lag_ms",
                    lag_ms,
                    service=event.service,
                    severity=event.severity,
                )

                self.telemetry.log(
                    "event_dequeued",
                    event_id=event.event_id,
                    correlation_id=event.correlation_id,
                    service=event.service,
                    severity=event.severity,
                    lag_ms=round(lag_ms, 2),
                    queue_size=self.queue.qsize(),
                )

                buffer.append(event)
                self.queue.task_done()

            except asyncio.TimeoutError:
                await self._flush(buffer)
                buffer.clear()

    async def _flush(self, events: list[StreamEvent]) -> None:
        if not events:
            return

        self.telemetry.increment("windows_flushed_total")

        grouped: dict[str, list[StreamEvent]] = defaultdict(list)

        for event in events:
            grouped[event.service].append(event)

        self.telemetry.log(
            "window_flushed",
            total_events=len(events),
            services=list(grouped.keys()),
        )

        for service, service_events in grouped.items():
            if self._requires_agent(service_events):
                await self._process_window_with_agent(service, service_events)
            else:
                self.telemetry.increment(
                    "events_filtered_total",
                    value=len(service_events),
                    service=service,
                )

                self.telemetry.log(
                    "window_filtered",
                    service=service,
                    event_count=len(service_events),
                    reason="low_priority_or_low_impact",
                )

    def _requires_agent(self, events: list[StreamEvent]) -> bool:
        severities = {event.severity for event in events}
        affected_users = sum(event.affected_users for event in events)
        latency_spikes = sum(
            1 for event in events if event.event_name == "latency_spike"
        )

        if "critical" in severities or "high" in severities:
            return True

        if affected_users >= 30:
            return True

        if latency_spikes >= 3:
            return True

        if len(events) >= 8:
            return True

        return False

    async def _process_window_with_agent(
        self,
        service: str,
        events: list[StreamEvent],
    ) -> None:
        correlation_id = events[0].correlation_id

        payload = {
            "service": service,
            "event_count": len(events),
            "affected_users": sum(event.affected_users for event in events),
            "max_severity": self._max_severity(events),
            "events": [
                {
                    "event_id": event.event_id,
                    "event_name": event.event_name,
                    "severity": event.severity,
                    "message": event.message,
                    "affected_users": event.affected_users,
                    "created_at": event.created_at.isoformat(),
                }
                for event in events
            ],
        }

        prompt = f"""
Analiza esta ventana de eventos observada en streaming.

Payload:
{json.dumps(payload, indent=2, ensure_ascii=False)}

Devuelve:
1. resumen operativo;
2. severidad consolidada;
3. posible causa;
4. siguiente acción recomendada;
5. si requiere revisión humana.

No ejecutes acciones reales fuera del laboratorio.
"""

        self.telemetry.increment(
            "agent_calls_total",
            service=service,
            severity=payload["max_severity"],
        )

        self.telemetry.log(
            "agent_call_queued",
            correlation_id=correlation_id,
            service=service,
            event_count=len(events),
            max_severity=payload["max_severity"],
        )

        async with self.agent_semaphore:
            try:
                with self.telemetry.span(
                    "agent_call",
                    correlation_id=correlation_id,
                    service=service,
                    event_count=len(events),
                ):
                    result = await self.agent.run(prompt)

                self.telemetry.increment(
                    "agent_results_total",
                    service=service,
                    status="success",
                )

                self.telemetry.log(
                    "agent_result",
                    correlation_id=correlation_id,
                    service=service,
                    result_preview=str(result)[:500],
                )

            except Exception as exc:
                self.telemetry.increment(
                    "agent_results_total",
                    service=service,
                    status="error",
                )

                self.telemetry.log(
                    "agent_error",
                    correlation_id=correlation_id,
                    service=service,
                    error=str(exc),
                )

    def _max_severity(self, events: list[StreamEvent]) -> str:
        order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return max(events, key=lambda event: order[event.severity]).severity

    def _lag_ms(self, event: StreamEvent) -> float:
        now = datetime.now(timezone.utc)
        return (now - event.created_at).total_seconds() * 1000