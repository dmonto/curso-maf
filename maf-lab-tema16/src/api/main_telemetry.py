from __future__ import annotations

import hashlib
import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.agents.support_agent_models import build_support_agent
from src.observability.telemetry import (
    agent_duration_histogram,
    agent_errors_counter,
    agent_runs_counter,
    configure_telemetry,
    tracer,
)
from src.settings import get_settings


logger = logging.getLogger("maf.production.api")

app = FastAPI(
    title="MAF Support Agent API",
    version="1.2.0",
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
    session_id: str | None = Field(default=None, max_length=100)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    duration_ms: int
    run_id: str


def render_agent_result(result: Any) -> str:
    for attribute in ("text", "content", "message"):
        value = getattr(result, attribute, None)

        if value:
            return str(value)

    return str(result)


def hash_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


@app.on_event("startup")
async def startup() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    configure_telemetry()

    settings = get_settings()

    app.state.settings = settings
    app.state.agent = build_support_agent()
    app.state.sessions = {}

    logger.info(
        "agent_api_started app_env=%s default_model=%s",
        settings.app_env,
        settings.default_chat_model,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    settings = app.state.settings

    return {
        "status": "ok",
        "app_env": settings.app_env,
        "default_model": settings.default_chat_model,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    run_id = uuid.uuid4().hex
    session_id = request.session_id or uuid.uuid4().hex
    session_hash = hash_identifier(session_id)

    started = time.perf_counter()

    attributes = {
        "agent.name": "maf-support-agent",
        "agent.run_id": run_id,
        "agent.session_hash": session_hash,
        "agent.model_alias": app.state.settings.default_chat_model,
        "agent.message_length": len(request.message),
    }

    with tracer.start_as_current_span(
        "maf.agent.chat",
        attributes=attributes,
    ) as span:
        agent_runs_counter.add(
            1,
            attributes={
                "agent.name": "maf-support-agent",
                "model.alias": app.state.settings.default_chat_model,
            },
        )

        try:
            session = app.state.sessions.get(session_id)

            if session is None:
                session = app.state.agent.create_session()
                app.state.sessions[session_id] = session
                span.set_attribute("agent.session_created", True)
            else:
                span.set_attribute("agent.session_created", False)

            logger.info(
                "agent_run_started run_id=%s session_hash=%s model_alias=%s",
                run_id,
                session_hash,
                app.state.settings.default_chat_model,
            )

            result = await app.state.agent.run(
                request.message,
                session=session,
            )

            duration_ms = int((time.perf_counter() - started) * 1000)

            span.set_attribute("agent.duration_ms", duration_ms)
            span.set_attribute("agent.status", "success")

            agent_duration_histogram.record(
                duration_ms,
                attributes={
                    "agent.name": "maf-support-agent",
                    "model.alias": app.state.settings.default_chat_model,
                    "status": "success",
                },
            )

            logger.info(
                "agent_run_completed run_id=%s session_hash=%s duration_ms=%s",
                run_id,
                session_hash,
                duration_ms,
            )

            return ChatResponse(
                session_id=session_id,
                answer=render_agent_result(result),
                duration_ms=duration_ms,
                run_id=run_id,
            )

        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)

            span.set_attribute("agent.duration_ms", duration_ms)
            span.set_attribute("agent.status", "error")
            span.set_attribute("agent.error_type", type(exc).__name__)
            span.record_exception(exc)

            agent_errors_counter.add(
                1,
                attributes={
                    "agent.name": "maf-support-agent",
                    "error.type": type(exc).__name__,
                },
            )

            agent_duration_histogram.record(
                duration_ms,
                attributes={
                    "agent.name": "maf-support-agent",
                    "status": "error",
                },
            )

            logger.exception(
                "agent_run_failed run_id=%s session_hash=%s duration_ms=%s error=%s",
                run_id,
                session_hash,
                duration_ms,
                type(exc).__name__,
            )

            raise HTTPException(
                status_code=500,
                detail={
                    "message": "No he podido completar la ejecución del agente.",
                    "run_id": run_id,
                },
            ) from exc