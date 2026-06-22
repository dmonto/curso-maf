from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.event_persistence.schemas import EventStatus, IncomingEvent, utc_now


class EventStore:
    def __init__(self, db_path: str = "event_store.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source, external_id)
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_status
                ON events(status)
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_type
                ON events(event_type)
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_correlation
                ON events(correlation_id)
                """
            )

    def append_event(self, event: IncomingEvent) -> bool:
        now = utc_now()

        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO events (
                        event_id,
                        source,
                        external_id,
                        event_type,
                        schema_version,
                        correlation_id,
                        status,
                        payload_json,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.source,
                        event.external_id,
                        event.event_type,
                        event.schema_version,
                        event.correlation_id,
                        "received",
                        json.dumps(event.payload, ensure_ascii=False),
                        now,
                        now,
                    ),
                )

            return True

        except sqlite3.IntegrityError:
            return False

    def fetch_next_received(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM events
                WHERE status IN ('received', 'failed')
                ORDER BY created_at ASC
                LIMIT 1
                """
            ).fetchone()

            if not row:
                return None

            event_id = row["event_id"]

            conn.execute(
                """
                UPDATE events
                SET status = ?, attempts = attempts + 1, updated_at = ?
                WHERE event_id = ?
                """,
                ("processing", utc_now(), event_id),
            )

            updated = conn.execute(
                """
                SELECT *
                FROM events
                WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()

            return self._row_to_dict(updated)

    def mark_processed(self, event_id: str, result: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE events
                SET status = ?, result_json = ?, error = NULL, updated_at = ?
                WHERE event_id = ?
                """,
                (
                    "processed",
                    json.dumps(result, ensure_ascii=False),
                    utc_now(),
                    event_id,
                ),
            )

    def mark_failed(
        self,
        event_id: str,
        error: str,
        max_attempts: int = 3,
    ) -> None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT attempts
                FROM events
                WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()

            attempts = int(row["attempts"]) if row else 0
            next_status: EventStatus = (
                "dead_letter" if attempts >= max_attempts else "failed"
            )

            conn.execute(
                """
                UPDATE events
                SET status = ?, error = ?, updated_at = ?
                WHERE event_id = ?
                """,
                (next_status, error, utc_now(), event_id),
            )

    def list_events(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM events
                ORDER BY created_at ASC
                """
            ).fetchall()

            return [self._row_to_dict(row) for row in rows]

    def reset_failed_for_replay(self) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE events
                SET status = ?, error = NULL, updated_at = ?
                WHERE status IN ('failed', 'dead_letter')
                """,
                ("received", utc_now()),
            )

            return cursor.rowcount

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["payload"] = json.loads(data.pop("payload_json"))

        result_json = data.pop("result_json")
        data["result"] = json.loads(result_json) if result_json else None

        return data