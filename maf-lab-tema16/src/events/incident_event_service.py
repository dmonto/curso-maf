from __future__ import annotations

from uuid import uuid4

from src.events.envelope import EventEnvelope
from src.events.local_event_bus import LocalEventBus


VALID_SERVICES = {"vpn", "erp", "correo", "teams"}


class IncidentEventError(Exception):
    pass


class IncidentEventService:
    def __init__(self, event_bus: LocalEventBus | None = None) -> None:
        self.event_bus = event_bus or LocalEventBus()

    def report_incident(
        self,
        service: str,
        summary: str,
        affected_users: int,
        business_impact: str,
    ) -> dict:
        if service not in VALID_SERVICES:
            raise IncidentEventError(f"Servicio no soportado: {service}")

        if len(summary.strip()) < 10:
            raise IncidentEventError("El resumen de la incidencia es demasiado corto.")

        if affected_users < 1:
            raise IncidentEventError("affected_users debe ser mayor o igual que 1.")

        if len(business_impact.strip()) < 5:
            raise IncidentEventError("Debe indicarse el impacto de negocio.")

        incident_id = f"inc-{uuid4().hex[:10]}"

        event = EventEnvelope.create(
            event_type="support.incident.reported.v1",
            aggregate_id=incident_id,
            payload={
                "incident_id": incident_id,
                "service": service,
                "summary": summary.strip(),
                "affected_users": affected_users,
                "business_impact": business_impact.strip(),
            },
        )

        self.event_bus.publish(event)

        return {
            "accepted": True,
            "incident_id": incident_id,
            "event_id": event.event_id,
            "correlation_id": event.correlation_id,
            "message": "Incidencia aceptada para procesamiento asíncrono.",
        }