
from __future__ import annotations

import json
from collections import Counter

from src.agents.support_agent_safe import build_support_agent
from src.queues.local_queue import LocalQueue
from src.queues.message import QueueMessage


class QueueWorker:
    def __init__(self, name: str, queue: LocalQueue) -> None:
        self.name = name
        self.queue = queue
        self.agent = build_support_agent()
        self.processed_message_ids: set[str] = set()
        self.stats: Counter[str] = Counter()

    async def run(self, max_messages: int) -> None:
        for _ in range(max_messages):
            message = await self.queue.receive()

            try:
                await self._process_message(message)
                await self.queue.complete(message)
                self.stats["completed"] += 1

            except ValueError as exc:
                await self.queue.dead_letter(message, reason=str(exc))
                self.stats["dead_letter"] += 1

            except Exception as exc:
                await self.queue.abandon(message, reason=str(exc))
                self.stats["retried"] += 1

    async def _process_message(self, message: QueueMessage) -> None:
        if message.message_id in self.processed_message_ids:
            print(f"[{self.name}] duplicado ignorado: {message.message_id}")
            self.stats["duplicates"] += 1
            return

        self.processed_message_ids.add(message.message_id)

        if message.message_type != "incident.triage.requested":
            raise ValueError(f"Tipo de mensaje no soportado: {message.message_type}")

        payload = message.payload

        if "service" not in payload:
            raise ValueError("Payload inválido: falta service")

        if payload.get("force_error") is True:
            raise RuntimeError("Error simulado para probar reintentos")

        prompt = self._build_prompt(message)

        print(f"\n[{self.name}] procesando {message.message_id}")
        result = await self.agent.run(prompt)

        print(f"[{self.name}] resultado del agente:")
        print(result)

    def _build_prompt(self, message: QueueMessage) -> str:
        payload_json = json.dumps(message.payload, indent=2, ensure_ascii=False)

        return f"""
Has recibido un mensaje desde una cola.

Metadatos:
- message_id: {message.message_id}
- message_type: {message.message_type}
- correlation_id: {message.correlation_id}
- delivery_count: {message.delivery_count}

Payload:
{payload_json}

Analiza la incidencia, estima prioridad operativa y prepara un borrador de respuesta.
No ejecutes acciones reales fuera del laboratorio.
"""