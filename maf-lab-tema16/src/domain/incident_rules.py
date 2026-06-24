from __future__ import annotations


def classify_incident(
    service: str,
    affected_users: int,
    business_impact: str,
) -> dict:
    impact = business_impact.lower()

    if affected_users >= 50:
        return {
            "priority": "p1",
            "recommended_team": "major-incident-team",
            "requires_escalation": True,
            "reason": "Afecta a 50 o más usuarios.",
        }

    if service == "erp" and (
        "facturación" in impact
        or "clientes" in impact
        or "producción" in impact
    ):
        return {
            "priority": "p1",
            "recommended_team": "business-apps-l2",
            "requires_escalation": True,
            "reason": "Incidencia en ERP con impacto directo en negocio.",
        }

    if affected_users >= 10:
        return {
            "priority": "p2",
            "recommended_team": "service-desk-l2",
            "requires_escalation": True,
            "reason": "Afecta a un grupo relevante de usuarios.",
        }

    if service == "vpn":
        return {
            "priority": "p3",
            "recommended_team": "network-support-l2",
            "requires_escalation": False,
            "reason": "Incidencia acotada de conectividad VPN.",
        }

    if service in {"correo", "teams"}:
        return {
            "priority": "p3",
            "recommended_team": "collaboration-support-l2",
            "requires_escalation": False,
            "reason": "Incidencia acotada en herramientas colaborativas.",
        }

    return {
        "priority": "p3",
        "recommended_team": "service-desk-l1",
        "requires_escalation": False,
        "reason": "Incidencia de bajo impacto inicial.",
    }