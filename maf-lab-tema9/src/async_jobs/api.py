from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.async_jobs.store import JobStore
from src.async_jobs.worker import AsyncJobWorker


queue: asyncio.Queue[str] = asyncio.Queue()
store = JobStore()
worker = AsyncJobWorker(queue=queue, store=store)
worker_task: asyncio.Task | None = None


class CreateJobRequest(BaseModel):
    job_type: str = Field(
        description="Tipo de job. Valores: incident_analysis, document_review."
    )
    payload: dict[str, Any]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_task

    worker_task = asyncio.create_task(worker.run_forever())
    print("[api] worker asincrónico iniciado")

    yield

    if worker_task:
        worker_task.cancel()
        print("[api] worker asincrónico detenido")


app = FastAPI(
    title="MAF Async Jobs Lab",
    version="1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs", status_code=202)
async def create_job(request: CreateJobRequest) -> dict[str, Any]:
    if request.job_type not in {"incident_analysis", "document_review"}:
        raise HTTPException(status_code=400, detail="job_type no soportado")

    job = store.create_job(
        job_type=request.job_type,
        payload=request.payload,
    )

    await queue.put(job.job_id)

    return {
        "status": "accepted",
        "job_id": job.job_id,
        "job_status": job.status,
    }


@app.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    job = store.as_dict(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="job no encontrado")

    return job


@app.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict[str, Any]:
    job = store.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="job no encontrado")

    if job.status in {"succeeded", "failed"}:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede cancelar un job en estado {job.status}",
        )

    store.update_status(job_id, "cancelled")

    return {
        "job_id": job_id,
        "status": "cancelled",
    }


@app.get("/stats")
async def stats() -> dict[str, Any]:
    return {
        "queue_size": queue.qsize(),
    }