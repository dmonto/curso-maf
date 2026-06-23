from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class RoleSpec:
    name: str
    purpose: str
    domain: str
    allowed_tasks: list[str]
    forbidden_tasks: list[str]
    allowed_tools: list[str]
    escalation_targets: list[str]
    max_risk_level: RiskLevel
    output_contract: list[str]


def build_role_catalog() -> dict[str, RoleSpec]:
    return {
        "support_coordinator": RoleSpec(
            name="support_coordinator",
            purpose="Coordinar diagnóstico, delegación y respuesta final.",
            domain="soporte IT general",
            allowed_tasks=[
                "interpretar petición",
                "seleccionar especialistas",
                "sintetizar resultados",
                "pedir aclaraciones",
            ],
            forbidden_tasks=[
                "modificar sistemas",
                "conceder permisos",
                "crear tickets reales sin aprobación",
            ],
            allowed_tools=[
                "delegar_por_rol",
                "consultar_catalogo_roles",
            ],
            escalation_targets=[
                "security_specialist",
                "human_operator",
            ],
            max_risk_level=RiskLevel.MEDIUM,
            output_contract=[
                "roles_consultados",
                "resultado_por_rol",
                "datos_pendientes",
                "siguiente_accion",
            ],
        ),
        "network_specialist": RoleSpec(
            name="network_specialist",
            purpose="Analizar problemas de conectividad, VPN, DNS y latencia.",
            domain="red y conectividad",
            allowed_tasks=[
                "diagnosticar conectividad",
                "proponer comprobaciones de red",
                "identificar datos técnicos faltantes",
            ],
            forbidden_tasks=[
                "cambiar configuración de red",
                "reiniciar servicios reales",
                "crear tickets reales",
            ],
            allowed_tools=[],
            escalation_targets=[
                "support_coordinator",
                "security_specialist",
            ],
            max_risk_level=RiskLevel.LOW,
            output_contract=[
                "diagnostico_red",
                "evidencias",
                "datos_faltantes",
                "siguiente_comprobacion",
            ],
        ),
        "identity_specialist": RoleSpec(
            name="identity_specialist",
            purpose="Analizar problemas de MFA, login, permisos y grupos.",
            domain="identidad y acceso",
            allowed_tasks=[
                "analizar hipótesis de autenticación",
                "identificar datos faltantes",
                "recomendar validaciones de permisos",
            ],
            forbidden_tasks=[
                "conceder permisos",
                "desbloquear cuentas",
                "solicitar contraseñas",
                "aprobar acceso privilegiado",
            ],
            allowed_tools=[],
            escalation_targets=[
                "security_specialist",
                "human_operator",
            ],
            max_risk_level=RiskLevel.MEDIUM,
            output_contract=[
                "hipotesis_identidad",
                "riesgo",
                "datos_faltantes",
                "siguiente_comprobacion",
            ],
        ),
        "itsm_specialist": RoleSpec(
            name="itsm_specialist",
            purpose="Preparar prioridad, resumen y datos mínimos de incidencia.",
            domain="gestión de incidencias",
            allowed_tasks=[
                "proponer prioridad",
                "preparar resumen de ticket",
                "listar datos mínimos",
            ],
            forbidden_tasks=[
                "crear ticket real sin aprobación",
                "prometer resolución",
                "asignar permisos",
            ],
            allowed_tools=[],
            escalation_targets=[
                "support_coordinator",
                "human_operator",
            ],
            max_risk_level=RiskLevel.MEDIUM,
            output_contract=[
                "prioridad_sugerida",
                "resumen_ticket",
                "datos_minimos",
                "justificacion",
            ],
        ),
        "security_specialist": RoleSpec(
            name="security_specialist",
            purpose="Evaluar riesgos, restricciones y necesidad de aprobación.",
            domain="seguridad y control de acceso",
            allowed_tasks=[
                "evaluar riesgo",
                "detectar acción sensible",
                "recomendar aprobación",
                "bloquear recomendación insegura",
            ],
            forbidden_tasks=[
                "aprobar por cuenta propia",
                "conceder permisos",
                "ejecutar cambios",
            ],
            allowed_tools=[],
            escalation_targets=[
                "human_operator",
            ],
            max_risk_level=RiskLevel.CRITICAL,
            output_contract=[
                "riesgo_detectado",
                "severidad",
                "restriccion",
                "accion_segura",
            ],
        ),
    }


def get_role(role_name: str) -> RoleSpec:
    catalog = build_role_catalog()

    if role_name not in catalog:
        valid_roles = ", ".join(catalog.keys())
        raise ValueError(f"Rol no registrado: {role_name}. Roles válidos: {valid_roles}")

    return catalog[role_name]


def render_role_catalog() -> str:
    catalog = build_role_catalog()
    lines = []

    for role in catalog.values():
        lines.append(f"ROL: {role.name}")
        lines.append(f"Propósito: {role.purpose}")
        lines.append(f"Dominio: {role.domain}")
        lines.append(f"Riesgo máximo: {role.max_risk_level}")
        lines.append(f"Puede: {', '.join(role.allowed_tasks)}")
        lines.append(f"No puede: {', '.join(role.forbidden_tasks)}")
        lines.append(f"Escala a: {', '.join(role.escalation_targets)}")
        lines.append("")

    return "\n".join(lines)