from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from azure.core import MatchConditions
from azure.core.exceptions import ResourceExistsError, ResourceModifiedError, ResourceNotFoundError
from azure.data.tables import TableServiceClient, UpdateMode
from azure.identity import AzureCliCredential
from azure.storage.blob import BlobServiceClient, ContentSettings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_key(value: str) -> str:
    """
    Evita caracteres problemáticos en nombres de blob.
    No es una función de seguridad completa; solo normaliza claves para el laboratorio.
    """
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    return value.strip("-") or "unknown"


@dataclass
class DistributedSessionState:
    user_id: str
    session_id: str
    memory: dict[str, Any] = field(default_factory=dict)
    rolling_summary: str = ""
    recent_turns: list[dict[str, Any]] = field(default_factory=list)
    collapsed_tool_results: list[dict[str, Any]] = field(default_factory=list)
    last_enriched_context: dict[str, Any] | None = None
    last_truncation_report: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1"
    created_utc: str = field(default_factory=utc_now)
    updated_utc: str = field(default_factory=utc_now)

    def to_json(self) -> str:
        self.updated_utc = utc_now()
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "DistributedSessionState":
        data = json.loads(text)

        allowed = {
            "user_id",
            "session_id",
            "memory",
            "rolling_summary",
            "recent_turns",
            "collapsed_tool_results",
            "last_enriched_context",
            "last_truncation_report",
            "metadata",
            "schema_version",
            "created_utc",
            "updated_utc",
        }

        filtered = {
            key: value
            for key, value in data.items()
            if key in allowed
        }

        return cls(**filtered)


@dataclass(frozen=True)
class LoadedState:
    state: DistributedSessionState
    etag: str | None


class StateConflictError(RuntimeError):
    pass


class AzureDistributedSessionStore:
    """
    Store distribuido para estado de agentes.

    - Blob Storage guarda el snapshot completo.
    - Table Storage guarda índice y metadatos.
    - ETag permite detectar conflictos de escritura.
    """

    def __init__(
        self,
        storage_account: str,
        container_name: str,
        table_name: str,
    ) -> None:
        if not storage_account:
            raise ValueError("storage_account no puede estar vacío")

        self.storage_account = storage_account
        self.container_name = container_name
        self.table_name = table_name

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
    def from_env(cls) -> "AzureDistributedSessionStore":
        storage_account = os.getenv("AZURE_STORAGE_ACCOUNT")
        container_name = os.getenv("AZURE_BLOB_CONTAINER", "maf-state")
        table_name = os.getenv("AZURE_TABLE_NAME", "MafSessionIndex")

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

    def build_blob_name(self, user_id: str, session_id: str) -> str:
        return (
            f"sessions/{safe_key(user_id)}/"
            f"{safe_key(session_id)}/state.json"
        )

    def load(
        self,
        user_id: str,
        session_id: str,
    ) -> LoadedState | None:
        blob_name = self.build_blob_name(user_id, session_id)
        blob_client = self._container.get_blob_client(blob_name)

        try:
            downloader = blob_client.download_blob()
            text = downloader.readall().decode("utf-8")
            properties = blob_client.get_blob_properties()
        except ResourceNotFoundError:
            return None

        state = DistributedSessionState.from_json(text)

        return LoadedState(
            state=state,
            etag=properties.etag,
        )

    def create_empty(
        self,
        user_id: str,
        session_id: str,
    ) -> LoadedState:
        state = DistributedSessionState(
            user_id=user_id,
            session_id=session_id,
            memory={},
            rolling_summary="",
            recent_turns=[],
            collapsed_tool_results=[],
            metadata={
                "status": "open",
                "turn_count": 0,
            },
        )

        etag = self.save(
            state=state,
            expected_etag=None,
            allow_create=True,
        )

        return LoadedState(
            state=state,
            etag=etag,
        )

    def save(
        self,
        state: DistributedSessionState,
        expected_etag: str | None,
        allow_create: bool = False,
    ) -> str:
        """
        Guarda el snapshot.

        Si expected_etag tiene valor, solo guarda si el blob no ha cambiado
        desde que se cargó.

        Si otro proceso guardó antes, Azure devuelve ResourceModifiedError.
        """
        blob_name = self.build_blob_name(state.user_id, state.session_id)
        blob_client = self._container.get_blob_client(blob_name)

        payload = state.to_json().encode("utf-8")

        content_settings = ContentSettings(
            content_type="application/json; charset=utf-8"
        )

        try:
            if expected_etag:
                blob_client.upload_blob(
                    payload,
                    overwrite=True,
                    etag=expected_etag,
                    match_condition=MatchConditions.IfNotModified,
                    content_settings=content_settings,
                )
            else:
                blob_client.upload_blob(
                    payload,
                    overwrite=allow_create,
                    content_settings=content_settings,
                )
        except ResourceModifiedError as exc:
            raise StateConflictError(
                "El estado fue modificado por otra instancia antes de guardar."
            ) from exc
        except ResourceExistsError as exc:
            raise StateConflictError(
                "El estado ya existe. Carga la sesión antes de sobrescribir."
            ) from exc

        properties = blob_client.get_blob_properties()
        etag = properties.etag

        self._upsert_index(
            state=state,
            blob_name=blob_name,
            etag=etag,
        )

        return etag

    def _upsert_index(
        self,
        state: DistributedSessionState,
        blob_name: str,
        etag: str,
    ) -> None:
        entity = {
            "PartitionKey": state.user_id,
            "RowKey": state.session_id,
            "blob_name": blob_name,
            "blob_etag": etag,
            "schema_version": state.schema_version,
            "created_utc": state.created_utc,
            "updated_utc": state.updated_utc,
            "status": state.metadata.get("status", "open"),
            "turn_count": int(state.metadata.get("turn_count", 0)),
        }

        self._table.upsert_entity(
            entity=entity,
            mode=UpdateMode.REPLACE,
        )

    def delete(
        self,
        user_id: str,
        session_id: str,
    ) -> None:
        blob_name = self.build_blob_name(user_id, session_id)
        blob_client = self._container.get_blob_client(blob_name)

        try:
            blob_client.delete_blob()
        except ResourceNotFoundError:
            pass

        try:
            self._table.delete_entity(
                partition_key=user_id,
                row_key=session_id,
            )
        except ResourceNotFoundError:
            pass

    def list_sessions(
        self,
        user_id: str,
    ) -> list[dict[str, Any]]:
        query_filter = f"PartitionKey eq '{user_id}'"
        entities = self._table.query_entities(query_filter=query_filter)

        result: list[dict[str, Any]] = []

        for entity in entities:
            result.append(
                {
                    "session_id": entity["RowKey"],
                    "updated_utc": entity.get("updated_utc"),
                    "status": entity.get("status"),
                    "turn_count": entity.get("turn_count"),
                    "blob_name": entity.get("blob_name"),
                }
            )

        return sorted(
            result,
            key=lambda item: item.get("updated_utc") or "",
            reverse=True,
        )