from __future__ import annotations

import time
from fastapi import FastAPI, HTTPException, Header


app = FastAPI(title="Unstable Ticket API")


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str, x_correlation_id: str | None = Header(default=None)) -> dict:
    ticket_id = ticket_id.upper()

    if ticket_id == "INC-1001":
        return {
            "ticket_id": "INC-1001",
            "service": "vpn",
            "summary": "VPN lenta desde casa",
            "priority": "p2",
            "status": "investigating",
            "correlation_id": x_correlation_id,
        }

    if ticket_id == "INC-404":
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    if ticket_id == "INC-403":
        raise HTTPException(status_code=403, detail="Permiso insuficiente")

    if ticket_id == "INC-429":
        raise HTTPException(status_code=429, detail="Rate limit")

    if ticket_id == "INC-500":
        raise HTTPException(status_code=500, detail="Error interno temporal")

    if ticket_id == "INC-SLOW":
        time.sleep(10)
        return {
            "ticket_id": "INC-SLOW",
            "service": "erp",
            "summary": "Respuesta tardía",
            "priority": "p3",
            "status": "open",
        }

    if ticket_id == "INC-BADJSON":
        return {
            "id": ticket_id,
            "estado": None,
            "priority": "urgente",
        }

    return {
        "ticket_id": ticket_id,
        "service": "soporte",
        "summary": "Ticket genérico",
        "priority": "p4",
        "status": "open",
    }