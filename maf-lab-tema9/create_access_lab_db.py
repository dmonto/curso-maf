from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("access_lab.db")


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE users (
                upn TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE tickets (
                ticket_id TEXT PRIMARY KEY,
                service TEXT NOT NULL,
                summary TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                owner_upn TEXT NOT NULL,
                department TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_upn TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_id TEXT,
                allowed INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.executemany(
            """
            INSERT INTO users (upn, display_name, role, department)
            VALUES (?, ?, ?, ?)
            """,
            [
                ("ana.garcia@empresa.local", "Ana García", "employee", "IT"),
                ("soporte.n1@empresa.local", "Soporte N1", "support_l1", "IT"),
                ("soporte.n2@empresa.local", "Soporte N2", "support_l2", "IT"),
                ("manager.it@empresa.local", "Manager IT", "manager", "IT"),
                ("ventas.user@empresa.local", "Usuario Ventas", "employee", "Sales"),
            ],
        )

        conn.executemany(
            """
            INSERT INTO tickets (
                ticket_id, service, summary, priority, status, owner_upn, department
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "INC-1001",
                    "vpn",
                    "VPN lenta desde casa",
                    "p2",
                    "investigating",
                    "ana.garcia@empresa.local",
                    "IT",
                ),
                (
                    "INC-2001",
                    "crm",
                    "Error al abrir oportunidad comercial",
                    "p3",
                    "open",
                    "ventas.user@empresa.local",
                    "Sales",
                ),
            ],
        )

    print(f"Base de datos creada en {DB_PATH.resolve()}")


if __name__ == "__main__":
    main()