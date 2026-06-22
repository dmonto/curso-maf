from __future__ import annotations

import asyncio
import json
from collections import Counter

from src.agents.support_agent_safe import build_support_agent
from src.realtime.event import RealtimeEvent
from src.realtime.window import EventWindow, build_windows_by_service


class RealtimeProcessor:
    def __init__(
        self,
        queue: asyncio.Queue[RealtimeEvent],
        window_seconds: float = 2.0,
    ) -> None:
        self.queue = queue
        self.window_seconds = window_seconds
        self.agent = build_support_agent()
        self.stats: Counter[str] = Counter()

    async def run(self) -> None:
        buffer: list[RealtimeEvent] = []

        while True:
            try:
                event = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=self.window_seconds,
                )

                if event.event_name == "end_of_stream":
                    await self._flush(buffer)
                    self.queue.task_done()
                    break

                buffer.append(event)
                self.queue.task_done()

            except asyncio.TimeoutError:
                await self._flush(buffer)
                buffer.clear()

    async def _flush(self, events: list[RealtimeEvent]) -> None:
        if not events:
            return

        windows = build_windows_by_service(events)

        for window in windows:
            if self._requires_agent(window):
                await self._process_with_agent(window)
                self.stats["agent_calls"] += 1
            else:
                print(
                    f"[filter] {window.service}: descartado "
                    f"({window.total_events} eventos, severidad {window.max_severity})"
                )
                self.stats["filtered"] += 1

    def _requires_agent(self, window: EventWindow) -> bool:
        if window.max_severity in {"high", "critical"}:
            return True

        if window.total_events >= 5:
            return True

        if window.affected_users >= 10:
            return True

        return False

    async def _process_with_agent(self, window: EventWindow) -> None:
        payload = {
            "service": window.service,
            "total_events": window.total_events,
            "max_severity": window.max_severity,
            "affected_users": window.affected_users,
            "events": [
                {
                    "event_id": event.event_id,
                    "event_name": event.event_name,
                    "severity": event.severity,
                    "message": event.message,
                    "affected_users": event.affected_users,
                    "created_at": event.created_at,
                }
                for event in window.events
            ],
        }

        prompt = f"""
Has recibido una ventana de eventos casi en tiempo real.

Payload:
{json.dumps(payload, indent=2, ensure_ascii=False)}

Analiza el patrón observado y devuelve:
1. resumen operativo;
2. severidad consolidada;
3. posible causa;
4. acción recomendada;
5. si conviene crear o preparar un ticket.

No ejecutes acciones reales fuera del laboratorio.
"""

        print(f"\n[agent] analizando ventana de {window.service}")
        result = await self.agent.run(prompt)
        print(result)