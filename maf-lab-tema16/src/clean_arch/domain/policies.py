from __future__ import annotations

from src.clean_arch.domain.incident import Incident


class IncidentPolicyError(Exception):
    pass


class IncidentPolicy:
    def validate(self, incident: Incident) -> None:
        if len(incident.summary) < 10:
            raise IncidentPolicyError("El resumen de la incidencia es demasiado corto.")

        if incident.affected_users < 1:
            raise IncidentPolicyError("affected_users debe ser mayor o igual que 1.")

        if len(incident.business_impact) < 5:
            raise IncidentPolicyError("Debe indicarse un impacto de negocio útil.")