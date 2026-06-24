from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class SourceFramework(StrEnum):
    SEMANTIC_KERNEL = "semantic_kernel"
    AUTOGEN = "autogen"


class LegacyMemoryKind(StrEnum):
    CHAT_HISTORY = "chat_history"
    SEMANTIC_MEMORY = "semantic_memory"
    GROUPCHAT_MESSAGE = "groupchat_message"
    SCRATCHPAD = "scratchpad"
    STATE = "state"
    UNKNOWN = "unknown"


class MemoryTarget(StrEnum):
    SESSION_STATE = "session_state"
    LONG_TERM_MEMORY = "long_term_memory"
    KNOWLEDGE = "knowledge"
    AUDIT_LOG = "audit_log"
    DISCARD = "discard"
    MANUAL_REVIEW = "manual_review"


@dataclass(frozen=True)
class LegacyMemoryRecord:
    record_id: str
    source_framework: str
    kind: str
    user_id: str
    session_id: str | None
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class MigratedMemoryRecord:
    source_record_id: str
    user_id: str
    session_id: str | None
    target: str
    key: str
    value: dict[str, Any]
    redacted: bool
    reason: str


SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(password|contraseña)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[a-z0-9\._\-]+"),
]


def load_legacy_records(path: Path) -> list[LegacyMemoryRecord]:
    raw_records = json.loads(path.read_text(encoding="utf-8"))

    return [
        LegacyMemoryRecord(
            record_id=item["record_id"],
            source_framework=item["source_framework"],
            kind=item.get("kind", "unknown"),
            user_id=item["user_id"],
            session_id=item.get("session_id"),
            text=item.get("text", ""),
            metadata=item.get("metadata", {}),
        )
        for item in raw_records
    ]


def redact_sensitive_text(text: str) -> tuple[str, bool]:
    redacted = False
    clean_text = text

    for pattern in SENSITIVE_PATTERNS:
        new_text = pattern.sub("[REDACTED_SECRET]", clean_text)
        if new_text != clean_text:
            redacted = True
            clean_text = new_text

    return clean_text, redacted


def classify_target(record: LegacyMemoryRecord, clean_text: str, redacted: bool) -> tuple[MemoryTarget, str]:
    text = clean_text.lower()
    kind = record.kind

    if redacted:
        return MemoryTarget.MANUAL_REVIEW, "Contiene datos sensibles redactados; requiere revisión antes de persistir."

    if kind == LegacyMemoryKind.SCRATCHPAD.value:
        return MemoryTarget.DISCARD, "Scratchpad interno: no debe migrarse como memoria del agente."

    if kind == LegacyMemoryKind.GROUPCHAT_MESSAGE.value:
        return MemoryTarget.AUDIT_LOG, "Mensaje entre agentes: útil como evidencia, no como memoria de usuario."

    if kind == LegacyMemoryKind.SEMANTIC_MEMORY.value:
        if "procedimiento" in text or "manual" in text or "documentación" in text:
            return MemoryTarget.KNOWLEDGE, "Parece conocimiento documental; debe ir a RAG o knowledge base."
        return MemoryTarget.LONG_TERM_MEMORY, "Parece preferencia o hecho estable de usuario."

    if kind == LegacyMemoryKind.CHAT_HISTORY.value:
        if "ticket" in text or "vpn" in text or "erp" in text or "prioridad" in text:
            return MemoryTarget.SESSION_STATE, "Historial con datos operativos del caso; convertir a estado de sesión."
        return MemoryTarget.MANUAL_REVIEW, "Historial conversacional sin destino claro."

    if kind == LegacyMemoryKind.STATE.value:
        return MemoryTarget.SESSION_STATE, "Estado legacy explícito."

    return MemoryTarget.MANUAL_REVIEW, "Tipo de memoria no reconocido."


def extract_state_fields(text: str, metadata: dict[str, Any]) -> dict[str, Any]:
    lower = text.lower()

    service = metadata.get("service")
    if not service:
        for candidate in ["vpn", "erp", "correo", "teams"]:
            if candidate in lower:
                service = candidate
                break

    steps_tried: list[str] = []
    if "reinicia" in lower or "reiniciar" in lower:
        steps_tried.append("reiniciar cliente")
    if "mfa" in lower:
        steps_tried.append("validar MFA")
    if "windows 11" in lower:
        operating_system = "Windows 11"
    else:
        operating_system = None

    return {
        "service": service,
        "operating_system": operating_system,
        "steps_tried": steps_tried,
        "ticket_requested": "ticket" in lower,
    }


def migrate_record(record: LegacyMemoryRecord) -> MigratedMemoryRecord:
    clean_text, redacted = redact_sensitive_text(record.text)
    target, reason = classify_target(record, clean_text, redacted)

    if target == MemoryTarget.SESSION_STATE:
        value = extract_state_fields(clean_text, record.metadata)
        key = f"case_state:{record.session_id or 'unknown'}"

    elif target == MemoryTarget.LONG_TERM_MEMORY:
        value = {
            "summary": clean_text,
            "source": record.source_framework,
        }
        key = "user_profile"

    elif target == MemoryTarget.AUDIT_LOG:
        value = {
            "event_summary": clean_text,
            "participants": record.metadata.get("participants", []),
            "source": record.source_framework,
        }
        key = f"audit:{record.record_id}"

    elif target == MemoryTarget.KNOWLEDGE:
        value = {
            "content": clean_text,
            "source": record.source_framework,
        }
        key = f"knowledge:{record.record_id}"

    elif target == MemoryTarget.DISCARD:
        value = {
            "discarded_text_preview": clean_text[:120],
        }
        key = f"discard:{record.record_id}"

    else:
        value = {
            "text": clean_text,
            "source": record.source_framework,
        }
        key = f"review:{record.record_id}"

    return MigratedMemoryRecord(
        source_record_id=record.record_id,
        user_id=record.user_id,
        session_id=record.session_id,
        target=target.value,
        key=key,
        value=value,
        redacted=redacted,
        reason=reason,
    )


def migrate_legacy_memory(path: Path) -> list[MigratedMemoryRecord]:
    records = load_legacy_records(path)
    return [migrate_record(record) for record in records]


def write_migration_report(records: list[MigratedMemoryRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(record) for record in records]
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )