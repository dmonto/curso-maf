
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone

from src.agents.support_agent_safe import build_support_agent
from src.latency_control.event import LatencyEvent
from src.latency_control.policy import LatencyPolicy, policy_for_event
from src.latency_control.telemetry import LatencyTelemetry, Stopwatch


class LatencyControlledProcessor:
    def __init__(
        self,
        queue: asyncio.Queue[LatencyEvent],
        telemetry: LatencyTelemetry,
        window_seconds: float = 2.0,
        max_concurrent_agent_calls: int = 2,
    ) -> None:
        self.queue = queue
        self.telemetry = telemetry
        self.window_seconds = window_seconds
        self.agent = build_support_agent()
        self.agent_semaphore = asyncio.Semaphore(max_concurrent_agent_calls)

    async def run(self) -> None:
        buffer: list[LatencyEvent] = []

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

                queue_lag_ms = self._queue_lag_ms(event)

                self.telemetry.observe(
                    "queue_lag_ms",
                    queue_lag_ms,
                    service=event.service,
                    severity=event.severity,
                )

                self.telemetry.log(
                    "event_dequeued",
                    event_id=event.event_id,
                    correlation_id=event.correlation_id,
                    service=event.service,
                    severity=event.severity,
                    queue_lag_ms=round(queue_lag_ms, 2),
                    queue_size=self.queue.qsize(),
                )

                buffer.append(event)
                self.queue.task_done()

            except asyncio.TimeoutError:
                await self._flush(buffer)
                buffer.clear()

    async def _flush(self, events: list[LatencyEvent]) -> None:
        if not events:
            return

        grouped: dict[str, list[LatencyEvent]] = defaultdict(list)

        for event in events:
            grouped[event.service].append(event)

        for service, service_events in grouped.items():
            await self._process_service_window(service, service_events)

    async def _process_service_window(
        self,
        service: str,
        events: list[LatencyEvent],
    ) -> None:
        stopwatch = Stopwatch()
        max_severity = self._max_severity(events)
        oldest_event = min(events, key=lambda event: event.created_at)
        queue_lag_ms = self._queue_lag_ms(oldest_event)
        policy = policy_for_event(max_severity, queue_lag_ms)

        self.telemetry.log(
            "latency_policy_selected",
            service=service,
            severity=max_severity,
            event_count=len(events),
            queue_lag_ms=round(queue_lag_ms, 2),
            mode=policy.mode,
            agent_timeout_ms=policy.agent_timeout_ms,
            max_prompt_events=policy.max_prompt_events,
            allow_tools=policy.allow_tools,
        )

        if policy.mode == "fallback":
            result = self._fallback_result(service, events, reason="latency_budget_exceeded")
            self._record_result(service, policy, stopwatch.elapsed_ms(), result)
            return

        prompt = self._build_prompt(service, events, policy)

        try:
            async with self.agent_semaphore:
                self.telemetry.increment(
                    "agent_calls_started_total",
                    service=service,
                    mode=policy.mode,
                )

                agent_stopwatch = Stopwatch()

                result = await asyncio.wait_for(
                    self.agent.run(prompt),
                    timeout=policy.agent_timeout_ms / 1000,
                )

                agent_latency_ms = agent_stopwatch.elapsed_ms()

                self.telemetry.observe(
                    "agent_latency_ms",
                    agent_latency_ms,
                    service=service,
                    mode=policy.mode,
                )

                self.telemetry.increment(
                    "agent_calls_finished_total",
                    service=service,
                    mode=policy.mode,
                    status="success",
                )

            self._record_result(
                service=service,
                policy=policy,
                total_latency_ms=stopwatch.elapsed_ms(),
                result={
                    "type": "agent_result",
                    "content": str(result)[:800],
                },
            )

        except asyncio.TimeoutError:
            self.telemetry.increment(
                "agent_calls_finished_total",
                service=service,
                mode=policy.mode,
                status="timeout",
            )

            result = self._fallback_result(service, events, reason="agent_timeout")

            self._record_result(
                service=service,
                policy=policy,
                total_latency_ms=stopwatch.elapsed_ms(),
                result=result,
            )

        except Exception as exc:
            self.telemetry.increment(
                "agent_calls_finished_total",
                service=service,
                mode=policy.mode,
                status="error",
            )

            result = self._fallback_result(service, events, reason=str(exc))

            self._record_result(
                service=service,
                policy=policy,
                total_latency_ms=stopwatch.elapsed_ms(),
                result=result,
            )

    def _build_prompt(
        self,
        service: str,
        events: list[LatencyEvent],
        policy: LatencyPolicy,
    ) -> str:
        compact_events = events[: policy.max_prompt_events]

        payload = {
            "service": service,
            "event_count": len(events),
            "events_in_prompt": len(compact_events),
            "max_severity": self._max_severity(events),
            "affected_users": sum(event.affected_users for event in events),
            "latency_mode": policy.mode,
            "allow_tools": policy.allow_tools,
            "events": [
                {
                    "event_id": event.event_id,
                    "event_name": event.event_name,
                    "severity": event.severity,
                    "message": event.message,
                    "affected_users": event.affected_users,
                    "created_at": event.created_at.isoformat(),
                }
                for event in compact_events
            ],
        }

        return f"""
Analiza esta ventana de eventos con control estricto de latencia.

Payload:
{json.dumps(payload, indent=2, ensure_ascii=False)}

Instrucciones:
- Devuelve una respuesta breve y accionable.
- No ejecutes acciones reales fuera del laboratorio.
- Si allow_tools=false, no propongas depender de comprobaciones externas lentas.
- Prioriza diagnóstico operativo, severidad consolidada y siguiente acción.

Formato esperado:
1. resumen;
2. severidad consolidada;
3. causa probable;
4. acción recomendada;
5. requiere revisión humana.
"""

    def _fallback_result(
        self,
        service: str,
        events: list[LatencyEvent],
        reason: str,
    ) -> dict:
        max_severity = self._max_severity(events)
        affected_users = sum(event.affected_users for event in events)

        requires_human_review = max_severity in {"high", "critical"} or affected_users >= 30

        return {
            "type": "fallback_result",
            "reason": reason,
            "service": service,
            "event_count": len(events),
            "max_severity": max_severity,
            "affected_users": affected_users,
            "summary": (
                f"Resultado preliminar generado por reglas. "
                f"Servicio={service}, severidad={max_severity}, "
                f"usuarios_afectados={affected_users}."
            ),
            "recommended_action": (
                "Enviar a revisión humana."
                if requires_human_review
                else "Registrar y continuar observando."
            ),
            "requires_human_review": requires_human_review,
        }

    def _record_result(
        self,
        service: str,
        policy: LatencyPolicy,
        total_latency_ms: float,
        result: dict,
    ) -> None:
        self.telemetry.observe(
            "total_processing_latency_ms",
            total_latency_ms,
            service=service,
            mode=policy.mode,
        )

        self.telemetry.increment(
            "results_total",
            service=service,
            mode=policy.mode,
            result_type=result["type"],
        )

        self.telemetry.log(
            "processing_result",
            service=service,
            mode=policy.mode,
            total_latency_ms=round(total_latency_ms, 2),
            result=result,
        )

    def _max_severity(self, events: list[LatencyEvent]) -> str:
        order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return max(events, key=lambda event: order[event.severity]).severity

    def _queue_lag_ms(self, event: LatencyEvent) -> float:
        now = datetime.now(timezone.utc)
        return (now - event.created_at).total_seconds() * 1000