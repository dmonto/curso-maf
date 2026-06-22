from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


JobStatus = Literal[
    "queued",
    "running",
    "waiting_approval",
    "succeeded",
    "failed",
    "cancelled",
]


@dataclass
class AsyncJob:
    job_type: str
    payload: dict[str, Any]
    job_id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = "queued"
    result: dict[str, Any] | None = None
    error: str | None = None
    attempts: int = 0
    max_attempts: int = 3
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()