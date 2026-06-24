from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class DatabaseIntegrationError(RuntimeError):
    pass


class TicketRecord(BaseModel):
    ticket_id: str
    service: str
    summary: str
    priority: str
    status: str
    owner_email: str


class AssetRecord(BaseModel):
    asset_id: str
    asset_type: str
    model: str
    owner_email: str
    status: str


class TicketNoteRecord(BaseModel):
    note_id: int
    ticket_id: str
    note: str
    created_by: str
    created_at: str


@dataclass(frozen=True)
class SupportDbRepository:
    db_path: Path

    @classmethod
    def from_env(cls) -> "SupportDbRepository":
        raw_path = os.getenv("SUPPORT_DB_PATH", "./support_lab.db")
        db_path = Path(raw_path)

        if not db_path.exists():
            raise RuntimeError(
                f"No existe la base de datos {db_path}. "
                "Ejecuta primero python create_support_db.py"
            )

        return cls(db_path=db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_ticket(self, ticket_id: str) -> TicketRecord | None:
        normalized_id = ticket_id.strip().upper()

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT ticket_id, service, summary, priority, status, owner_email
                FROM tickets
                WHERE ticket_id = ?
                """,
                (normalized_id,),
            ).fetchone()

        if not row:
            return None

        return TicketRecord(**dict(row))

    def find_assets_by_owner(self, owner_email: str) -> list[AssetRecord]:
        normalized_email = owner_email.strip().lower()

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT asset_id, asset_type, model, owner_email, status
                FROM assets
                WHERE lower(owner_email) = ?
                ORDER BY asset_type, asset_id
                """,
                (normalized_email,),
            ).fetchall()

        return [AssetRecord(**dict(row)) for row in rows]

    def summarize_tickets_by_service(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    service,
                    status,
                    priority,
                    COUNT(*) AS total
                FROM tickets
                GROUP BY service, status, priority
                ORDER BY service, priority
                """
            ).fetchall()

        return [dict(row) for row in rows]

    def add_ticket_note(
        self,
        ticket_id: str,
        note: str,
        created_by: str,
    ) -> TicketNoteRecord:
        normalized_id = ticket_id.strip().upper()
        clean_note = note.strip()
        clean_created_by = created_by.strip().lower()

        if len(clean_note) < 10:
            raise DatabaseIntegrationError(
                "La nota debe tener al menos 10 caracteres."
            )

        ticket = self.get_ticket(normalized_id)
        if not ticket:
            raise DatabaseIntegrationError(
                f"No existe el ticket {normalized_id}."
            )

        created_at = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO ticket_notes (
                    ticket_id, note, created_by, created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (normalized_id, clean_note, clean_created_by, created_at),
            )

            note_id = int(cursor.lastrowid)

            row = conn.execute(
                """
                SELECT note_id, ticket_id, note, created_by, created_at
                FROM ticket_notes
                WHERE note_id = ?
                """,
                (note_id,),
            ).fetchone()

        if not row:
            raise DatabaseIntegrationError("No se pudo recuperar la nota creada.")

        return TicketNoteRecord(**dict(row))