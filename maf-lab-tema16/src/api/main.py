from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.agents.support_agent_models import build_support_agent
from src.settings import get_settings


logger = logging.getLogger("maf.container.api")

app = FastAPI(
    title="MAF Support Agent API",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=2,
        max_length=4000,
        description="Mensaje del usuario para el agente.",
    )
    session_id: str | None = Field(
        default=None,
        max_length=100,
        description="Identificador de sesión conversacional.",
    )


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


@app.on_event("startup")
async def startup() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    settings = get_settings()

    app.state.settings = settings
    app.state.agent = build_support_agent()
    app.state.sessions = {}

    logger.info(
        "agent_api_started app_env=%s auth_mode=%s default_model=%s",
        settings.app_env,
        settings.azure_auth_mode,
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
    started = time.perf_counter()

    session_id = request.session_id or uuid.uuid4().hex

    try:
        session = app.state.sessions.get(session_id)

        if session is None:
            session = app.state.agent.create_session()
            app.state.sessions[session_id] = session

        logger.info(
            "agent_run_started run_id=%s session_id=%s message_length=%s",
            run_id,
            session_id,
            len(request.message),
        )

        result = await app.state.agent.run(
            request.message,
            session=session,
        )

        duration_ms = int((time.perf_counter() - started) * 1000)
        answer = render_agent_result(result)

        logger.info(
            "agent_run_completed run_id=%s session_id=%s duration_ms=%s",
            run_id,
            session_id,
            duration_ms,
        )

        return ChatResponse(
            session_id=session_id,
            answer=answer,
            duration_ms=duration_ms,
            run_id=run_id,
        )

    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)

        logger.exception(
            "agent_run_failed run_id=%s session_id=%s duration_ms=%s error=%s",
            run_id,
            session_id,
            duration_ms,
            type(exc).__name__,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "No he podido completar la ejecución del agente de forma segura.",
                "run_id": run_id,
            },
        ) from exc