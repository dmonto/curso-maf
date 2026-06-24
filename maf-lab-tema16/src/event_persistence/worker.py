from __future__ import annotations

import json
from typing import Any

from src.agents.support_agent_safe import build_support_agent
from src.event_persistence.store import EventStore


class PersistentEventWorker:
    def __init__(
        self,
        store: EventStore,
        max_attempts: int = 3,
    ) -> None:
        self.store = store
        self.max_attempts = max_attempts
        self.agent = build_support_agent()

    async def process_pending(self, max_events: int = 10) -> None:
        processed = 0

        while processed < max_events:
            event = self.store.fetch_next_received()

            if not event:
                print("[worker] no hay eventos pendientes")
                return

            try:
                result = await self._process_event(event)
                self.store.mark_processed(event["event_id"], result)

                print(
                    f"[worker] procesado {event['event_type']} "
                    f"{event['external_id']}"
                )

            except Exception as exc:
                self.store.mark_failed(
                    event_id=event["event_id"],
                    error=str(exc),
                    max_attempts=self.max_attempts,
                )

                print(
                    f"[worker] error en {event['event_type']} "
                    f"{event['external_id']}: {exc}"
                )

            processed += 1

    async def _process_event(self, event: dict[str, Any]) -> dict[str, Any]:
        payload = event["payload"]

        if event["event_type"] == "incident.created":
            self._validate_incident_payload(payload)
            prompt = self._build_incident_prompt(event)

        elif event["event_type"] == "document.uploaded":
            self._validate_document_payload(payload)
            prompt = self._build_document_prompt(event)

        else:
            raise ValueError(f"event_type no soportado: {event['event_type']}")

        agent_response = await self.agent.run(prompt)

        return {
            "event_id": event["event_id"],
            "event_type": event["event_type"],
            "correlation_id": event["correlation_id"],
            "agent_response": str(agent_response),
        }

    def _validate_incident_payload(self, payload: dict[str, Any]) -> None:
        required = {"service", "severity", "description"}

        missing = required - set(payload)

        if missing:
            raise ValueError(f"Payload de incidencia inválido. Faltan: {missing}")

    def _validate_document_payload(self, payload: dict[str, Any]) -> None:
        required = {"document_id", "file_name"}

        missing = required - set(payload)

        if missing:
            raise ValueError(f"Payload documental inválido. Faltan: {missing}")

    def _build_incident_prompt(self, event: dict[str, Any]) -> str:
        return f"""
Procesa este evento persistido de incidencia.

Metadatos:
- event_id: {event["event_id"]}
- source: {event["source"]}
- external_id: {event["external_id"]}
- correlation_id: {event["correlation_id"]}
- attempts: {event["attempts"]}

Payload:
{json.dumps(event["payload"], indent=2, ensure_ascii=False)}

Devuelve:
1. resumen operativo;
2. prioridad estimada;
3. posible causa;
4. siguiente acción recomendada;
5. si requiere revisión humana.

No ejecutes acciones reales fuera del laboratorio.
"""

    def _build_document_prompt(self, event: dict[str, Any]) -> str:
        return f"""
Procesa este evento persistido de subida documental.

Metadatos:
- event_id: {event["event_id"]}
- source: {event["source"]}
- external_id: {event["external_id"]}
- correlation_id: {event["correlation_id"]}
- attempts: {event["attempts"]}

Payload:
{json.dumps(event["payload"], indent=2, ensure_ascii=False)}

Devuelve:
1. tipo probable de documento;
2. sensibilidad estimada;
3. si podría indexarse para RAG;
4. riesgos antes de indexarlo;
5. siguiente acción recomendada.

No indexas documentos reales. Solo produces una recomendación.
"""