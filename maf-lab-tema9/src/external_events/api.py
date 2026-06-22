# src/external_events/api.py

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from src.external_events.normalizer import normalize_external_event
from src.external_events.schemas import CanonicalEvent
from src.external_events.security import validate_signature
from src.external_events.worker import ExternalEventWorker


queue: asyncio.Queue[CanonicalEvent] = asyncio.Queue()
worker = ExternalEventWorker(queue=queue)
worker_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_task

    worker_task = asyncio.create_task(worker.run_forever())
    print("[api] worker iniciado")

    yield

    if worker_task:
        worker_task.cancel()
        print("[api] worker detenido")


app = FastAPI(
    title="MAF External Events Lab",
    version="1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/stats")
async def stats() -> dict[str, Any]:
    return {
        "queue_size": queue.qsize(),
        "stats": dict(worker.stats),
    }


@app.post("/webhooks/external")
async def receive_external_event(
    request: Request,
    x_event_source: str = Header(...),
    x_signature: str | None = Header(default=None),
) -> dict[str, Any]:
    body = await request.body()

    if not validate_signature(body=body, received_signature=x_signature):
        raise HTTPException(status_code=401, detail="Firma inválida")

    try:
        raw_event = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"JSON inválido: {exc}")

    try:
        event = normalize_external_event(
            source=x_event_source,
            raw_event=raw_event,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await queue.put(event)

    return {
        "status": "accepted",
        "event_id": event.event_id,
        "source": event.source,
        "event_type": event.event_type,
        "correlation_id": event.correlation_id,
    }