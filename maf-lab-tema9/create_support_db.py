from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("support_lab.db")


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE tickets (
                ticket_id TEXT PRIMARY KEY,
                service TEXT NOT NULL,
                summary TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                owner_email TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE assets (
                asset_id TEXT PRIMARY KEY,
                asset_type TEXT NOT NULL,
                model TEXT NOT NULL,
                owner_email TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE ticket_notes (
                note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL,
                note TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(ticket_id) REFERENCES tickets(ticket_id)
            )
        """)

        conn.executemany(
            """
            INSERT INTO tickets (
                ticket_id, service, summary, priority, status, owner_email
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "INC-1001",
                    "vpn",
                    "VPN lenta para usuario remoto",
                    "p2",
                    "investigating",
                    "ana.garcia@empresa.local",
                ),
                (
                    "INC-1002",
                    "erp",
                    "Error 500 al validar pedidos",
                    "p1",
                    "open",
                    "carlos.lopez@empresa.local",
                ),
                (
                    "INC-1003",
                    "correo",
                    "Retraso intermitente en recepción de correo",
                    "p3",
                    "monitoring",
                    "ana.garcia@empresa.local",
                ),
            ],
        )

        conn.executemany(
            """
            INSERT INTO assets (
                asset_id, asset_type, model, owner_email, status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    "LAP-001",
                    "laptop",
                    "Surface Laptop 6",
                    "ana.garcia@empresa.local",
                    "active",
                ),
                (
                    "MOB-101",
                    "mobile",
                    "iPhone 15",
                    "ana.garcia@empresa.local",
                    "active",
                ),
                (
                    "LAP-002",
                    "laptop",
                    "ThinkPad T14",
                    "carlos.lopez@empresa.local",
                    "active",
                ),
            ],
        )

    print(f"Base de datos creada en {DB_PATH.resolve()}")


if __name__ == "__main__":
    main()