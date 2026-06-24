from __future__ import annotations

from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(title="Mock ITSM API")


class TicketCreateRequest(BaseModel):
    service: str = Field(min_length=2)
    summary: str = Field(min_length=5)
    priority: Literal["p1", "p2", "p3", "p4"]


class Ticket(BaseModel):
    ticket_id: str
    service: str
    summary: str
    priority: str
    status: str


TICKETS: dict[str, Ticket] = {
    "INC-1001": Ticket(
        ticket_id="INC-1001",
        service="vpn",
        summary="VPN lenta para varios usuarios remotos",
        priority="p2",
        status="investigating",
    )
}


def require_token(authorization: str | None) -> None:
    expected = "Bearer lab-token"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Token inválido o ausente")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/tickets/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: str, authorization: str | None = Header(default=None)) -> Ticket:
    require_token(authorization)

    ticket = TICKETS.get(ticket_id.upper())
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    return ticket


@app.post("/tickets", response_model=Ticket)
def create_ticket(
    request: TicketCreateRequest,
    authorization: str | None = Header(default=None),
) -> Ticket:
    require_token(authorization)

    ticket_id = f"INC-{str(uuid4())[:8].upper()}"
    ticket = Ticket(
        ticket_id=ticket_id,
        service=request.service.lower(),
        summary=request.summary,
        priority=request.priority,
        status="new",
    )
    TICKETS[ticket_id] = ticket

    return ticket