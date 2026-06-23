from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


AUDIT_LOG_PATH = Path("logs/interaction_audit.jsonl")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def safe_len(value: str | None) -> int:
    return len(value or "")


@dataclass(frozen=True)
class AuditContext:
    user_id: str
    tenant_id: str
    session_id: str
    run_id: str
    agent_name: str
    prompt_version: str
    model_alias: str


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    component: str
    action: str
    context: AuditContext
    turn_id: str
    timestamp_utc: str = field(default_factory=utc_now)
    allowed: bool | None = None
    duration_ms: int | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    input_length: int | None = None
    output_length: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AuditWriter:
    def __init__(self, path: Path = AUDIT_LOG_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: AuditEvent) -> None:
        record = asdict(event)

        # Aplana contexto para facilitar consultas posteriores.
        context = record.pop("context")
        record.update(context)

        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def new_run_id() -> str:
    return f"run-{uuid4().hex[:12]}"


def new_turn_id(index: int) -> str:
    return f"turn-{index:04d}"


class Timer:
    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.end = time.perf_counter()

    @property
    def duration_ms(self) -> int:
        return int((self.end - self.start) * 1000)