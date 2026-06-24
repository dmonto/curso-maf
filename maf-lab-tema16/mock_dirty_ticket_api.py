from __future__ import annotations

from fastapi import FastAPI, HTTPException


app = FastAPI(title="Dirty Ticket API")


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> dict:
    ticket_id = ticket_id.upper()

    if ticket_id == "INC-1001":
        return {
            "ticket_id": "INC-1001",
            "service": "vpn",
            "summary": "VPN lenta desde casa",
            "priority": "p2",
            "status": "investigating",
            "owner_email": "ana.garcia@empresa.local",
            "updated_at": "2026-06-18T10:15:00Z",
        }

    if ticket_id == "INC-1002":
        return {
            "ticket_id": "INC-1002",
            "service": "erp",
            "summary": "Error 500 al validar pedidos",
            "priority": "URGENTE",
            "status": "en proceso",
            "owner_email": "carlos.lopez@empresa.local",
            "updated_at": "18/06/2026 10:15",
        }

    if ticket_id == "INC-1003":
        return {
            "id": "INC-1003",
            "service": "correo",
            "summary": None,
            "priority": "p3",
            "status": "open",
            "owner_email": "usuario-sin-email-valido",
            "internal_debug": {
                "connection_string": "Server=sql;User=admin;Password=secret",
                "token": "Bearer abc123",
            },
        }

    if ticket_id == "INC-9999":
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    return {
        "ticket_id": ticket_id,
        "service": "unknown",
        "summary": "Ticket generado por sistema externo",
        "priority": "p4",
        "status": "open",
        "owner_email": "soporte@empresa.local",
        "updated_at": "2026-06-18T11:00:00Z",
        "extra_field": "Este campo no debe llegar al agente",
    }