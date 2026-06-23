from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import sys
from typing import Any

from src.observability.context import (
    get_agent_name,
    get_run_id,
    get_session_id,
)


RESERVED_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
}


SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_value(key: str, value: Any) -> Any:
    key_lower = key.lower()

    if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
        return "***REDACTED***"

    if isinstance(value, dict):
        return {k: _redact_value(k, v) for k, v in value.items()}

    if isinstance(value, list):
        return [_redact_value(key, item) for item in value]

    return value


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": _utc_now_iso(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": get_run_id(),
            "session_id": get_session_id(),
            "agent_name": get_agent_name(),
        }

        for key, value in record.__dict__.items():
            if key not in RESERVED_ATTRS and not key.startswith("_"):
                payload[key] = _redact_value(key, value)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_json_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Reducimos ruido de librerías externas durante el laboratorio.
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)