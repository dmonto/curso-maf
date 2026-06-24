from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.security.sensitive_data import SensitiveDataReport, summarize_matches


AUDIT_PATH = Path("logs/sensitive_data_audit.jsonl")


def write_sensitive_audit_event(
    *,
    event_type: str,
    user_id: str,
    session_id: str,
    report: SensitiveDataReport,
    extra: dict[str, Any] | None = None,
) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "session_id": session_id,
        "has_sensitive_data": report.has_sensitive_data,
        "highest_level": report.highest_level.value,
        "blocked": report.blocked,
        "reason": report.reason,
        "matches": summarize_matches(report.matches),
        "extra": extra or {},
    }

    with AUDIT_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")