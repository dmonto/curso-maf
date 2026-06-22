from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.state import SupportSessionMemory


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _memory_from_dict(data: dict[str, Any]) -> SupportSessionMemory:
    """
    Reconstruye la memoria desde JSON, filtrando campos desconocidos.

    Esto permite evolucionar el esquema de memoria sin romper registros
    antiguos guardados en la base local.
    """
    valid_fields = {field.name for field in fields(SupportSessionMemory)}
    filtered = {key: value for key, value in data.items() if key in valid_fields}

    if filtered.get("pasos_probados") is None:
        filtered["pasos_probados"] = []

    return SupportSessionMemory(**filtered)


class SQLiteSessionMemoryStore:
    """
    Store externo para memoria de sesión usando SQLite local.

    Clave lógica:

    user_id    = usuario o identificador funcional
    session_id = conversación o caso concreto

    Este diseño replica el patrón que usaríamos después con Azure Table Storage,
    Cosmos DB, PostgreSQL o cualquier store externo.
    """

    def __init__(
        self,
        db_path: str,
    ) -> None:
        if not db_path:
            raise ValueError("db_path no puede estar vacío")

        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    @classmethod
    def from_env(cls) -> "SQLiteSessionMemoryStore":
        db_path = os.getenv(
            "MAF_MEMORY_DB_PATH",
            "data/session_memory.sqlite3",
        )

        return cls(db_path=db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_memory (
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    memory_json TEXT NOT NULL,
                    updated_utc TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    PRIMARY KEY (user_id, session_id)
                )
                """
            )

    def load(
        self,
        user_id: str,
        session_id: str,
    ) -> SupportSessionMemory | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT memory_json
                FROM session_memory
                WHERE user_id = ? AND session_id = ?
                """,
                (user_id, session_id),
            ).fetchone()

        if row is None:
            return None

        data = json.loads(row["memory_json"])
        return _memory_from_dict(data)

    def save(
        self,
        user_id: str,
        session_id: str,
        memory: SupportSessionMemory,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO session_memory (
                    user_id,
                    session_id,
                    memory_json,
                    updated_utc,
                    schema_version
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, session_id)
                DO UPDATE SET
                    memory_json = excluded.memory_json,
                    updated_utc = excluded.updated_utc,
                    schema_version = excluded.schema_version
                """,
                (
                    user_id,
                    session_id,
                    memory.to_json(),
                    _utc_now(),
                    "1",
                ),
            )

    def delete(
        self,
        user_id: str,
        session_id: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM session_memory
                WHERE user_id = ? AND session_id = ?
                """,
                (user_id, session_id),
            )