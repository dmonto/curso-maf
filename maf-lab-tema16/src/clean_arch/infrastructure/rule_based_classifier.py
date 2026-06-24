from __future__ import annotations

from src.clean_arch.domain.incident import (
    Incident,
    IncidentClassification,
    SupportService,
    TicketPriority,
)


class RuleBasedIncidentClassifier:
    def classify(self, incident: Incident) -> IncidentClassification:
        impact = incident.business_impact.lower()

        if incident.affected_users >= 50:
            return IncidentClassification(
                incident_id=incident.incident_id,
                priority=TicketPriority.P1,
                recommended_team="major-incident-team",
                requires_escalation=True,
                reason="Afecta a 50 o más usuarios.",
            )

        if incident.service == SupportService.ERP and (
            "facturación" in impact
            or "clientes" in impact
            or "producción" in impact
        ):
            return IncidentClassification(
                incident_id=incident.incident_id,
                priority=TicketPriority.P1,
                recommended_team="business-apps-l2",
                requires_escalation=True,
                reason="Incidencia en ERP con impacto directo en negocio.",
            )

        if incident.affected_users >= 10:
            return IncidentClassification(
                incident_id=incident.incident_id,
                priority=TicketPriority.P2,
                recommended_team="service-desk-l2",
                requires_escalation=True,
                reason="Afecta a un grupo relevante de usuarios.",
            )

        if incident.service == SupportService.VPN:
            return IncidentClassification(
                incident_id=incident.incident_id,
                priority=TicketPriority.P3,
                recommended_team="network-support-l2",
                requires_escalation=False,
                reason="Incidencia acotada de conectividad VPN.",
            )

        if incident.service in {SupportService.CORREO, SupportService.TEAMS}:
            return IncidentClassification(
                incident_id=incident.incident_id,
                priority=TicketPriority.P3,
                recommended_team="collaboration-support-l2",
                requires_escalation=False,
                reason="Incidencia acotada en herramientas colaborativas.",
            )

        return IncidentClassification(
            incident_id=incident.incident_id,
            priority=TicketPriority.P3,
            recommended_team="service-desk-l1",
            requires_escalation=False,
            reason="Incidencia de bajo impacto inicial.",
        )