from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.data.tables import TableServiceClient, UpdateMode
from azure.identity import AzureCliCredential
from azure.storage.blob import BlobServiceClient, ContentSettings


AuditActor = Literal["user", "agent", "system", "tool"]
AuditSeverity = Literal["info", "warning", "error", "blocking"]


EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"\b(?:\+34\s?)?(?:6|7|8|9)\d{8}\b"
)

SECRET_PATTERN = re.compile(
    r"(?i)\b(password|contraseña|passwd|api[_-]?key|secret|token|bearer|connection string)\b"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_key(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    return value.strip("-") or "unknown"


def redact_text(text: str, max_chars: int = 800) -> str:
    """
    Redacta texto antes de guardarlo como evidencia visible.

    Para auditoría básica guardamos preview redactada y hash.
    No guardamos secretos completos.
    """
    if SECRET_PATTERN.search(text):
        return "[CONTENIDO_SENSIBLE_REDACTADO]"

    redacted = EMAIL_PATTERN.sub("[EMAIL_REDACTADO]", text)
    redacted = PHONE_PATTERN.sub("[TELEFONO_REDACTADO]", redacted)

    if len(redacted) > max_chars:
        return redacted[:max_chars].rstrip() + "\n...[preview_truncada]"

    return redacted


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class ConversationAuditEvent:
    event_type: str
    user_id: str
    session_id: str
    run_id: str
    actor: AuditActor
    action: str
    outcome: str
    severity: AuditSeverity = "info"
    message_preview: str | None = None
    content_hash: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    created_utc: str = field(default_factory=utc_now)
    event_id: str = field(default_factory=lambda: uuid4().hex)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str)


class AzureConversationAuditStore:
    """
    Store de auditoría append-only simplificado.

    - Cada evento se guarda como un blob JSON independiente.
    - Una tabla mantiene el índice consultable por user_id/session_id.
    """

    def __init__(
        self,
        storage_account: str,
        container_name: str,
        table_name: str,
    ) -> None:
        if not storage_account:
            raise ValueError("storage_account no puede estar vacío")

        credential = AzureCliCredential()

        blob_endpoint = f"https://{storage_account}.blob.core.windows.net"
        table_endpoint = f"https://{storage_account}.table.core.windows.net"

        self._blob_service = BlobServiceClient(
            account_url=blob_endpoint,
            credential=credential,
        )

        self._table_service = TableServiceClient(
            endpoint=table_endpoint,
            credential=credential,
        )

        self._container = self._blob_service.get_container_client(container_name)

        try:
            self._container.create_container()
        except ResourceExistsError:
            pass

        self._table_service.create_table_if_not_exists(table_name)
        self._table = self._table_service.get_table_client(table_name)

    @classmethod
    def from_env(cls) -> "AzureConversationAuditStore":
        storage_account = os.getenv("AZURE_STORAGE_ACCOUNT")
        container_name = os.getenv("AZURE_AUDIT_CONTAINER", "maf-audit")
        table_name = os.getenv("AZURE_AUDIT_TABLE", "MafConversationAudit")

        if not storage_account:
            raise RuntimeError(
                "Falta AZURE_STORAGE_ACCOUNT. "
                "Ejemplo: $env:AZURE_STORAGE_ACCOUNT='cursoiastorage'"
            )

        return cls(
            storage_account=storage_account,
            container_name=container_name,
            table_name=table_name,
        )

    def record_event(self, event: ConversationAuditEvent) -> str:
        blob_name = self._build_blob_name(event)

        blob_client = self._container.get_blob_client(blob_name)
        payload = event.to_json().encode("utf-8")

        blob_client.upload_blob(
            payload,
            overwrite=False,
            content_settings=ContentSettings(
                content_type="application/json; charset=utf-8"
            ),
        )

        self._table.upsert_entity(
            entity={
                "PartitionKey": self._partition_key(event.user_id, event.session_id),
                "RowKey": self._row_key(event),
                "event_id": event.event_id,
                "event_type": event.event_type,
                "actor": event.actor,
                "action": event.action,
                "outcome": event.outcome,
                "severity": event.severity,
                "created_utc": event.created_utc,
                "run_id": event.run_id,
                "user_id": event.user_id,
                "session_id": event.session_id,
                "blob_name": blob_name,
            },
            mode=UpdateMode.REPLACE,
        )

        return event.event_id

    def list_events(
        self,
        user_id: str,
        session_id: str,
    ) -> list[dict[str, Any]]:
        partition_key = self._partition_key(user_id, session_id)
        query_filter = f"PartitionKey eq '{partition_key}'"

        rows = []

        for entity in self._table.query_entities(query_filter=query_filter):
            rows.append(
                {
                    "event_id": entity.get("event_id"),
                    "event_type": entity.get("event_type"),
                    "actor": entity.get("actor"),
                    "action": entity.get("action"),
                    "outcome": entity.get("outcome"),
                    "severity": entity.get("severity"),
                    "created_utc": entity.get("created_utc"),
                    "run_id": entity.get("run_id"),
                    "blob_name": entity.get("blob_name"),
                }
            )

        return sorted(rows, key=lambda item: item.get("created_utc") or "")

    def read_event_payload(
        self,
        blob_name: str,
    ) -> dict[str, Any]:
        blob_client = self._container.get_blob_client(blob_name)

        try:
            data = blob_client.download_blob().readall()
        except ResourceNotFoundError as exc:
            raise RuntimeError(f"No existe el evento de auditoría: {blob_name}") from exc

        return json.loads(data.decode("utf-8"))

    def _build_blob_name(self, event: ConversationAuditEvent) -> str:
        timestamp = event.created_utc.replace(":", "-")
        return (
            f"audit/{safe_key(event.user_id)}/"
            f"{safe_key(event.session_id)}/"
            f"{timestamp}_{safe_key(event.event_type)}_{event.event_id}.json"
        )

    def _partition_key(self, user_id: str, session_id: str) -> str:
        return f"{safe_key(user_id)}__{safe_key(session_id)}"

    def _row_key(self, event: ConversationAuditEvent) -> str:
        timestamp = event.created_utc.replace(":", "-")
        return f"{timestamp}_{event.event_id}"