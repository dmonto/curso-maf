
from __future__ import annotations

import asyncio
import json

from src.agents.support_agent_safe import build_support_agent
from src.concurrency.schemas import SupportJob
from src.concurrency.state import ConcurrentStateStore


class ConcurrentJobProcessor:
    def __init__(
        self,
        queue: asyncio.Queue[SupportJob],
        state_store: ConcurrentStateStore,
        worker_count: int = 4,
        max_concurrent_agent_calls: int = 2,
        job_timeout_seconds: int = 60,
    ) -> None:
        self.queue = queue
        self.state_store = state_store
        self.worker_count = worker_count
        self.agent = build_support_agent()
        self.agent_semaphore = asyncio.Semaphore(max_concurrent_agent_calls)
        self.job_timeout_seconds = job_timeout_seconds
        self.processed_job_ids: set[str] = set()
        self.processed_lock = asyncio.Lock()

    async def run(self) -> None:
        workers = [
            asyncio.create_task(self._worker_loop(worker_id=index + 1))
            for index in range(self.worker_count)
        ]

        await self.queue.join()

        for worker in workers:
            worker.cancel()

        await asyncio.gather(*workers, return_exceptions=True)

    async def _worker_loop(self, worker_id: int) -> None:
        while True:
            job = await self.queue.get()

            try:
                await asyncio.wait_for(
                    self._process_job(worker_id=worker_id, job=job),
                    timeout=self.job_timeout_seconds,
                )
                await self.state_store.increment_stat("completed")

            except asyncio.TimeoutError:
                print(f"[worker-{worker_id}] timeout job={job.job_id}")
                await self.state_store.increment_stat("timeout")

            except Exception as exc:
                print(f"[worker-{worker_id}] error job={job.job_id}: {exc}")
                await self.state_store.increment_stat("errors")

            finally:
                self.queue.task_done()

    async def _process_job(self, worker_id: int, job: SupportJob) -> None:
        async with self.processed_lock:
            if job.job_id in self.processed_job_ids:
                print(f"[worker-{worker_id}] duplicado ignorado {job.job_id}")
                await self.state_store.increment_stat("duplicates")
                return

            self.processed_job_ids.add(job.job_id)

        print(
            f"[worker-{worker_id}] procesando job={job.job_id} "
            f"servicio={job.service}"
        )

        prompt = self._build_prompt(job)

        async with self.agent_semaphore:
            await self.state_store.increment_stat("agent_calls_started")
            result = await self.agent.run(prompt)
            await self.state_store.increment_stat("agent_calls_finished")

        summary = str(result)[:500]

        await self.state_store.update_service_state(
            service=job.service,
            priority=job.priority,
            affected_users=job.affected_users,
            summary=summary,
        )

        print(f"[worker-{worker_id}] completado job={job.job_id}")

    def _build_prompt(self, job: SupportJob) -> str:
        payload = {
            "job_id": job.job_id,
            "correlation_id": job.correlation_id,
            "service": job.service,
            "priority": job.priority,
            "description": job.description,
            "affected_users": job.affected_users,
            "payload": job.payload,
        }

        return f"""
Procesa esta incidencia en un sistema concurrente.

Payload:
{json.dumps(payload, indent=2, ensure_ascii=False)}

Devuelve:
1. resumen operativo;
2. severidad consolidada;
3. datos faltantes;
4. siguiente acción recomendada;
5. si requiere revisión humana.

No ejecutes acciones reales fuera del laboratorio.
"""