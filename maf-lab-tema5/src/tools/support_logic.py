from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal


ServiceName = Literal["vpn", "correo", "teams", "erp"]
Priority = Literal["p1", "p2", "p3", "p4"]
RiskLevel = Literal["low", "medium", "high", "critical"]


@dataclass(frozen=True)
class IncidentInput:
    service: ServiceName
    priority: Priority
    summary: str
    impact: str
    users_affected: int


@dataclass(frozen=True)
class RiskDecision:
    risk: RiskLevel
    reason: str
    requires_human_validation: bool


SLA_HOURS: dict[Priority, int] = {
    "p1": 2,
    "p2": 8,
    "p3": 24,
    "p4": 72,
}


SERVICE_ALIASES: dict[str, ServiceName] = {
    "vpn": "vpn",
    "red privada virtual": "vpn",
    "correo": "correo",
    "email": "correo",
    "mail": "correo",
    "teams": "teams",
    "microsoft teams": "teams",
    "erp": "erp",
    "sistema de gestion": "erp",
}


def normalize_service_name(raw_service: str) -> ServiceName | None:
    normalized = raw_service.strip().lower()
    return SERVICE_ALIASES.get(normalized)


def calculate_sla(priority: Priority) -> dict:
    hours = SLA_HOURS[priority]
    deadline = datetime.now(timezone.utc) + timedelta(hours=hours)

    return {
        "priority": priority,
        "sla_hours": hours,
        "deadline_utc": deadline.isoformat(),
        "rule": f"SLA estándar para prioridad {priority}: {hours} horas.",
    }


def validate_incident_input(incident: IncidentInput) -> list[str]:
    errors: list[str] = []

    if len(incident.summary.strip()) < 10:
        errors.append("El resumen debe tener al menos 10 caracteres.")

    if len(incident.impact.strip()) < 15:
        errors.append("El impacto debe tener al menos 15 caracteres.")

    if incident.users_affected < 1:
        errors.append("Debe haber al menos un usuario afectado.")

    if incident.priority == "p1":
        if incident.users_affected < 10:
            errors.append("Una prioridad p1 requiere al menos 10 usuarios afectados.")
        if len(incident.impact.strip()) < 30:
            errors.append("Una prioridad p1 requiere una descripción de impacto más completa.")

    return errors


def classify_incident_risk(incident: IncidentInput) -> RiskDecision:
    validation_errors = validate_incident_input(incident)

    if validation_errors:
        return RiskDecision(
            risk="medium",
            reason="No se puede clasificar con precisión: " + "; ".join(validation_errors),
            requires_human_validation=True,
        )

    impact_lower = incident.impact.lower()

    if (
        incident.priority == "p1"
        or incident.users_affected > 50
        or (
            incident.service == "erp"
            and any(term in impact_lower for term in ["facturación", "facturacion", "pedidos", "financiero"])
        )
    ):
        return RiskDecision(
            risk="critical",
            reason="Incidencia crítica por prioridad, volumen de usuarios o impacto de negocio.",
            requires_human_validation=True,
        )

    if incident.priority == "p2" or incident.users_affected > 10:
        return RiskDecision(
            risk="high",
            reason="Incidencia de riesgo alto por prioridad p2 o más de 10 usuarios afectados.",
            requires_human_validation=False,
        )

    if incident.priority == "p3":
        return RiskDecision(
            risk="medium",
            reason="Incidencia de riesgo medio por prioridad p3.",
            requires_human_validation=False,
        )

    return RiskDecision(
        risk="low",
        reason="Incidencia de bajo riesgo por prioridad p4 o impacto limitado.",
        requires_human_validation=False,
    )


def build_ticket_draft_payload(incident: IncidentInput) -> dict:
    validation_errors = validate_incident_input(incident)

    if validation_errors:
        return {
            "created": False,
            "errors": validation_errors,
            "required_action": "Pedir los datos faltantes antes de preparar el borrador.",
        }

    risk = classify_incident_risk(incident)
    sla = calculate_sla(incident.priority)

    return {
        "created": True,
        "ticket_type": "draft",
        "service": incident.service,
        "priority": incident.priority,
        "summary": incident.summary,
        "impact": incident.impact,
        "users_affected": incident.users_affected,
        "risk": risk.risk,
        "risk_reason": risk.reason,
        "requires_human_validation": risk.requires_human_validation,
        "sla": sla,
        "external_effect": False,
    }