# src/external_events/worker.py

from __future__ import annotations

import asyncio
import json
from collections import Counter

from src.agents.support_agent_safe import build_support_agent
from src.external_events.schemas import CanonicalEvent


class ExternalEventWorker:
    def __init__(self, queue: asyncio.Queue[CanonicalEvent]) -> None:
        self.queue = queue
        self.agent = build_support_agent()
        self.processed_external_ids: set[str] = set()
        self.stats: Counter[str] = Counter()

    async def run_forever(self) -> None:
        while True:
            event = await self.queue.get()

            try:
                await self.process_event(event)
            except Exception as exc:
                print(f"[worker] error procesando {event.event_id}: {exc}")
                self.stats["errors"] += 1
            finally:
                self.queue.task_done()

    async def process_event(self, event: CanonicalEvent) -> None:
        dedupe_key = f"{event.source}:{event.external_id}"

        if dedupe_key in self.processed_external_ids:
            print(f"[worker] duplicado ignorado: {dedupe_key}")
            self.stats["duplicates"] += 1
            return

        self.processed_external_ids.add(dedupe_key)
        self.stats[event.event_type] += 1

        if event.event_type == "alert.created":
            prompt = self._build_alert_prompt(event)
        elif event.event_type == "document.uploaded":
            prompt = self._build_document_prompt(event)
        else:
            print(f"[worker] evento sin handler: {event.event_type}")
            self.stats["unsupported"] += 1
            return

        print(f"\n[worker] reaccionando a {event.event_type} desde {event.source}")
        result = await self.agent.run(prompt)

        print("[agent-result]")
        print(result)

    def _build_alert_prompt(self, event: CanonicalEvent) -> str:
        return f"""
Has recibido un evento externo de monitorización.

Metadatos:
- event_id interno: {event.event_id}
- external_id: {event.external_id}
- source: {event.source}
- event_type: {event.event_type}
- correlation_id: {event.correlation_id}

Payload:
{json.dumps(event.payload, ensure_ascii=False, indent=2)}

Reacciona al evento:
1. resume el problema;
2. estima impacto operativo;
3. indica si conviene preparar ticket;
4. recomienda siguiente acción;
5. identifica si requiere revisión humana.

No ejecutes acciones reales fuera del laboratorio.
"""

    def _build_document_prompt(self, event: CanonicalEvent) -> str:
        return f"""
Has recibido un evento externo de subida de documento.

Metadatos:
- event_id interno: {event.event_id}
- external_id: {event.external_id}
- source: {event.source}
- event_type: {event.event_type}
- correlation_id: {event.correlation_id}

Payload:
{json.dumps(event.payload, ensure_ascii=False, indent=2)}

Reacciona al evento:
1. clasifica el tipo probable de documento;
2. estima sensibilidad;
3. indica si podría indexarse para RAG;
4. enumera riesgos antes de indexarlo;
5. recomienda siguiente acción.

No indexas documentos reales. Solo produces una recomendación.
"""