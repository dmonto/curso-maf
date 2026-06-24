from __future__ import annotations

import json
import os
from dataclasses import fields
from datetime import datetime, timezone
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableServiceClient, UpdateMode
from azure.identity import AzureCliCredential

from src.state import SupportSessionMemory


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _memory_from_dict(data: dict[str, Any]) -> SupportSessionMemory:
    """
    Reconstruye la memoria desde JSON, filtrando campos desconocidos.

    Esto permite evolucionar el esquema de memoria sin romper todos los
    registros antiguos guardados en la tabla.
    """
    valid_fields = {field.name for field in fields(SupportSessionMemory)}
    filtered = {key: value for key, value in data.items() if key in valid_fields}

    if filtered.get("pasos_probados") is None:
        filtered["pasos_probados"] = []

    return SupportSessionMemory(**filtered)


class AzureTableSessionMemoryStore:
    """
    Store externo para memoria de sesión usando Azure Table Storage.

    PartitionKey = user_id
    RowKey       = session_id

    Este diseño permite recuperar rápidamente la memoria de una sesión
    concreta de un usuario concreto.
    """

    def __init__(
        self,
        storage_account: str,
        table_name: str,
    ) -> None:
        if not storage_account:
            raise ValueError("storage_account no puede estar vacío")

        if not table_name:
            raise ValueError("table_name no puede estar vacío")

        endpoint = f"https://{storage_account}.table.core.windows.net"

        credential = AzureCliCredential(
            tenant_id=os.getenv("AZURE_TENANT_ID")
        )

        service_client = TableServiceClient(
            endpoint=endpoint,
            credential=credential,
        )

        service_client.create_table_if_not_exists(table_name)
        self._table_client = service_client.get_table_client(table_name)

    @classmethod
    def from_env(cls) -> "AzureTableSessionMemoryStore":
        storage_account = os.getenv("AZURE_STORAGE_ACCOUNT")
        table_name = os.getenv("AZURE_TABLE_NAME", "MafSessionMemory")

        if not storage_account:
            raise RuntimeError(
                "Falta AZURE_STORAGE_ACCOUNT. "
                "Ejemplo: $env:AZURE_STORAGE_ACCOUNT='cursoiastorage'"
            )

        return cls(
            storage_account=storage_account,
            table_name=table_name,
        )

    def load(
        self,
        user_id: str,
        session_id: str,
    ) -> SupportSessionMemory | None:
        try:
            entity = self._table_client.get_entity(
                partition_key=user_id,
                row_key=session_id,
            )
        except ResourceNotFoundError:
            return None

        memory_json = entity.get("memory_json")

        if not memory_json:
            return None

        data = json.loads(memory_json)
        return _memory_from_dict(data)

    def save(
        self,
        user_id: str,
        session_id: str,
        memory: SupportSessionMemory,
    ) -> None:
        entity = {
            "PartitionKey": user_id,
            "RowKey": session_id,
            "memory_json": memory.to_json(),
            "updated_utc": _utc_now(),
            "schema_version": "1",
        }

        self._table_client.upsert_entity(
            entity=entity,
            mode=UpdateMode.REPLACE,
        )

    def delete(
        self,
        user_id: str,
        session_id: str,
    ) -> None:
        try:
            self._table_client.delete_entity(
                partition_key=user_id,
                row_key=session_id,
            )
        except ResourceNotFoundError:
            return