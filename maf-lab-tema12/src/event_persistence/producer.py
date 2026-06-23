from __future__ import annotations

from src.event_persistence.schemas import IncomingEvent
from src.event_persistence.store import EventStore


def publish_demo_events(store: EventStore) -> None:
    events = [
        IncomingEvent(
            source="monitoring",
            external_id="alert-1001",
            event_type="incident.created",
            payload={
                "service": "vpn",
                "severity": "high",
                "description": "Usuarios no pueden conectar desde remoto",
                "affected_users": 25,
            },
        ),
        IncomingEvent(
            source="monitoring",
            external_id="alert-1002",
            event_type="incident.created",
            payload={
                "service": "erp",
                "severity": "medium",
                "description": "Lentitud intermitente en facturación",
                "affected_users": 8,
            },
        ),
        IncomingEvent(
            source="sharepoint",
            external_id="doc-event-2001",
            event_type="document.uploaded",
            payload={
                "document_id": "DOC-1001",
                "file_name": "manual_vpn_windows.pdf",
                "department": "IT",
                "classification_hint": "soporte",
            },
        ),
        IncomingEvent(
            source="monitoring",
            external_id="alert-invalid-3001",
            event_type="incident.created",
            payload={
                "severity": "high",
                "description": "Evento inválido para probar dead-letter",
            },
        ),
    ]

    for event in events:
        inserted = store.append_event(event)

        if inserted:
            print(f"[producer] persistido {event.event_type} {event.external_id}")
        else:
            print(f"[producer] duplicado ignorado {event.source}:{event.external_id}")

    duplicate = events[0]
    inserted = store.append_event(duplicate)

    if not inserted:
        print(f"[producer] duplicado detectado correctamente: {duplicate.external_id}")