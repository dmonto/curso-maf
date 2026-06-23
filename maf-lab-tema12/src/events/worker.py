from __future__ import annotations

import asyncio
import json
from typing import Any

from src.agents.support_agent_safe import build_support_agent
from src.events.schemas import EventEnvelope


class EventWorker:
    def __init__(self) -> None:
        self.agent = build_support_agent()
        self.processed_event_ids: set[str] = set()

    async def process_event(self, event: EventEnvelope) -> None:
        if event.event_id in self.processed_event_ids:
            print(f"[worker] evento duplicado ignorado: {event.event_id}")
            return

        self.processed_event_ids.add(event.event_id)

        if event.event_type == "incident.created":
            prompt = self._build_incident_prompt(event)
        elif event.event_type == "ticket.updated":
            prompt = self._build_ticket_prompt(event)
        else:
            print(f"[worker] tipo de evento no soportado: {event.event_type}")
            return

        print(f"\n[worker] procesando {event.event_type}")
        result = await self.agent.run(prompt)
        print("[agent-result]")
        print(result)

    async def run(
        self,
        queue: asyncio.Queue[EventEnvelope],
        stop_after: int | None = None,
    ) -> None:
        processed = 0

        while True:
            event = await queue.get()

            try:
                await self.process_event(event)
            except Exception as exc:
                print(f"[worker] error procesando evento {event.event_id}: {exc}")
            finally:
                queue.task_done()
                processed += 1

            if stop_after is not None and processed >= stop_after:
                break

    def _build_incident_prompt(self, event: EventEnvelope) -> str:
        payload = json.dumps(event.payload, ensure_ascii=False, indent=2)

        return f"""
Has recibido un evento de tipo incident.created.

Metadatos:
- event_id: {event.event_id}
- source: {event.source}
- correlation_id: {event.correlation_id}

Payload:
{payload}

Analiza la incidencia, comprueba el estado del servicio si procede,
estima una prioridad operativa y prepara un borrador de ticket.
No ejecutes acciones reales fuera del laboratorio.
"""

    def _build_ticket_prompt(self, event: EventEnvelope) -> str:
        payload = json.dumps(event.payload, ensure_ascii=False, indent=2)

        return f"""
Has recibido un evento de tipo ticket.updated.

Metadatos:
- event_id: {event.event_id}
- source: {event.source}
- correlation_id: {event.correlation_id}

Payload:
{payload}

Resume el estado del ticket y propone la siguiente acción recomendada.
No cierres el ticket ni envíes comunicaciones reales.
"""