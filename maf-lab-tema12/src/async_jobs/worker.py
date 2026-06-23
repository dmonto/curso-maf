from __future__ import annotations

import asyncio
import json
from typing import Any

from src.agents.support_agent_safe import build_support_agent
from src.async_jobs.schemas import AsyncJob
from src.async_jobs.store import JobStore


class AsyncJobWorker:
    def __init__(
        self,
        queue: asyncio.Queue[str],
        store: JobStore,
        max_concurrent_agent_calls: int = 2,
    ) -> None:
        self.queue = queue
        self.store = store
        self.agent = build_support_agent()
        self.semaphore = asyncio.Semaphore(max_concurrent_agent_calls)

    async def run_forever(self) -> None:
        while True:
            job_id = await self.queue.get()

            try:
                await self.process_job(job_id)
            finally:
                self.queue.task_done()

    async def process_job(self, job_id: str) -> None:
        job = self.store.get_job(job_id)

        if not job:
            print(f"[worker] job no encontrado: {job_id}")
            return

        if job.status == "cancelled":
            print(f"[worker] job cancelado, no se procesa: {job_id}")
            return

        attempts = self.store.increment_attempts(job_id)
        self.store.update_status(job_id, "running")

        try:
            async with self.semaphore:
                result = await asyncio.wait_for(
                    self._execute_agent_job(job),
                    timeout=60,
                )

            self.store.update_status(
                job_id=job_id,
                status="succeeded",
                result=result,
            )

            print(f"[worker] job completado: {job_id}")

        except Exception as exc:
            if attempts < job.max_attempts:
                print(f"[worker] error recuperable en {job_id}: {exc}")
                self.store.update_status(
                    job_id=job_id,
                    status="queued",
                    error=str(exc),
                )
                await self.queue.put(job_id)
            else:
                print(f"[worker] job fallido definitivamente: {job_id}")
                self.store.update_status(
                    job_id=job_id,
                    status="failed",
                    error=str(exc),
                )

    async def _execute_agent_job(self, job: AsyncJob) -> dict[str, Any]:
        if job.job_type == "incident_analysis":
            prompt = self._build_incident_prompt(job)
        elif job.job_type == "document_review":
            prompt = self._build_document_prompt(job)
        else:
            raise ValueError(f"job_type no soportado: {job.job_type}")

        response = await self.agent.run(prompt)

        return {
            "job_type": job.job_type,
            "agent_response": str(response),
        }

    def _build_incident_prompt(self, job: AsyncJob) -> str:
        return f"""
Procesa este job asincrónico de análisis de incidencia.

job_id: {job.job_id}
attempts: {job.attempts}

Payload:
{json.dumps(job.payload, indent=2, ensure_ascii=False)}

Devuelve:
1. resumen operativo;
2. prioridad estimada;
3. datos faltantes;
4. siguiente acción recomendada;
5. si requiere revisión humana.

No ejecutes acciones reales fuera del laboratorio.
"""

    def _build_document_prompt(self, job: AsyncJob) -> str:
        return f"""
Procesa este job asincrónico de revisión documental.

job_id: {job.job_id}
attempts: {job.attempts}

Payload:
{json.dumps(job.payload, indent=2, ensure_ascii=False)}

Devuelve:
1. tipo probable de documento;
2. sensibilidad estimada;
3. si podría indexarse para RAG;
4. riesgos previos;
5. siguiente acción recomendada.

No indexas documentos reales. Solo produces una recomendación.
"""