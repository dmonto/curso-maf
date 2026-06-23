from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class UserRecord(BaseModel):
    upn: str
    display_name: str
    role: str
    department: str


class TicketRecord(BaseModel):
    ticket_id: str
    service: str
    summary: str
    priority: str
    status: str
    owner_upn: str
    department: str


@dataclass(frozen=True)
class AccessLabRepository:
    db_path: Path

    @classmethod
    def from_env(cls) -> "AccessLabRepository":
        raw_path = os.getenv("ACCESS_LAB_DB_PATH", "./access_lab.db")
        db_path = Path(raw_path)

        if not db_path.exists():
            raise RuntimeError(
                f"No existe {db_path}. Ejecuta primero create_access_lab_db.py"
            )

        return cls(db_path=db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_user(self, upn: str) -> UserRecord | None:
        clean_upn = upn.strip().lower()

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT upn, display_name, role, department
                FROM users
                WHERE lower(upn) = ?
                """,
                (clean_upn,),
            ).fetchone()

        return UserRecord(**dict(row)) if row else None

    def get_ticket(self, ticket_id: str) -> TicketRecord | None:
        clean_id = ticket_id.strip().upper()

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT ticket_id, service, summary, priority, status, owner_upn, department
                FROM tickets
                WHERE ticket_id = ?
                """,
                (clean_id,),
            ).fetchone()

        return TicketRecord(**dict(row)) if row else None

    def update_ticket_priority(self, ticket_id: str, priority: str) -> TicketRecord:
        clean_id = ticket_id.strip().upper()
        clean_priority = priority.strip().lower()

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tickets
                SET priority = ?
                WHERE ticket_id = ?
                """,
                (clean_priority, clean_id),
            )

        ticket = self.get_ticket(clean_id)
        if not ticket:
            raise RuntimeError(f"No existe el ticket {clean_id}")

        return ticket

    def summarize_tickets(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT department, service, priority, status, COUNT(*) AS total
                FROM tickets
                GROUP BY department, service, priority, status
                ORDER BY department, service
                """
            ).fetchall()

        return [dict(row) for row in rows]

    def write_audit(
        self,
        requester_upn: str,
        action: str,
        resource_id: str | None,
        allowed: bool,
        reason: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_log (
                    requester_upn, action, resource_id, allowed, reason
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    requester_upn.strip().lower(),
                    action,
                    resource_id,
                    1 if allowed else 0,
                    reason,
                ),
            )