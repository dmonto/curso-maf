# src/events/producer.py

from __future__ import annotations

import asyncio

from src.events.schemas import EventEnvelope


async def publish_demo_events(queue: asyncio.Queue[EventEnvelope]) -> None:
    events = [
        EventEnvelope(
            event_type="incident.created",
            source="monitoring",
            payload={
                "service": "vpn",
                "severity": "high",
                "description": "Aumento de errores de conexión desde remoto",
                "affected_users": 25,
            },
        ),
        EventEnvelope(
            event_type="incident.created",
            source="monitoring",
            payload={
                "service": "erp",
                "severity": "medium",
                "description": "Lentitud intermitente en consultas de facturación",
                "affected_users": 8,
            },
        ),
        EventEnvelope(
            event_type="ticket.updated",
            source="itsm",
            payload={
                "ticket_id": "TCK-1042",
                "status": "waiting_user",
                "description": "Usuario pendiente de confirmar si MFA funciona",
            },
        ),
    ]

    for event in events:
        await queue.put(event)
        print(f"[producer] publicado {event.event_type} {event.event_id}")