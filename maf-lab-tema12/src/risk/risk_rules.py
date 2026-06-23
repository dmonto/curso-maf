from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.risk.risk_model import RiskFinding, RiskStatus


def load_agent_risk_profile(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _has_all(profile: dict[str, Any], keys: list[str]) -> bool:
    return all(bool(profile.get(key)) for key in keys)


def evaluate_architecture_risks(profile: dict[str, Any]) -> list[RiskFinding]:
    findings: list[RiskFinding] = []

    if not profile.get("has_identity_context"):
        findings.append(
            RiskFinding(
                risk_id="ID-001",
                title="Identidad no confiable",
                category="identity",
                description=(
                    "El agente no recibe un contexto de identidad confiable. "
                    "Podría aceptar identidad declarada por el usuario en el prompt."
                ),
                impact=5,
                likelihood=3,
                controls_missing=["IdentityContext", "claims confiables", "session_id"],
                recommendation="Construir IdentityContext desde Entra ID, cabeceras firmadas o backend.",
            )
        )

    if profile.get("uses_rag"):
        filters = set(profile.get("rag_filters", []))
        required_filters = {"tenant_id", "groups", "classification"}
        missing = sorted(required_filters - filters)

        if missing:
            findings.append(
                RiskFinding(
                    risk_id="RAG-001",
                    title="RAG sin filtros suficientes",
                    category="rag",
                    description=(
                        "El agente usa recuperación documental, pero faltan filtros "
                        "de seguridad antes de inyectar contexto al modelo."
                    ),
                    impact=5,
                    likelihood=4,
                    controls_present=sorted(filters),
                    controls_missing=missing,
                    recommendation=(
                        "Aplicar filtros por tenant, grupo y clasificación antes de devolver chunks."
                    ),
                )
            )

    if profile.get("uses_tools") and profile.get("allows_real_actions"):
        required_approvals = set(profile.get("tool_approval_required_for", []))
        dangerous_actions = {"create_ticket", "send_email", "change_permissions"}
        missing = sorted(dangerous_actions - required_approvals)

        if missing:
            findings.append(
                RiskFinding(
                    risk_id="TOOL-001",
                    title="Acciones reales sin aprobación suficiente",
                    category="tools",
                    description=(
                        "El agente puede ejecutar acciones con efecto externo, "
                        "pero no todas tienen aprobación explícita."
                    ),
                    impact=5,
                    likelihood=3,
                    controls_present=sorted(required_approvals),
                    controls_missing=missing,
                    recommendation="Exigir aprobación humana o workflow controlado para acciones sensibles.",
                )
            )

    if profile.get("uses_memory") and profile.get("memory_mode") != "structured_state":
        findings.append(
            RiskFinding(
                risk_id="MEM-001",
                title="Memoria con exceso de contenido",
                category="memory",
                description=(
                    "La memoria no está configurada como estado estructurado. "
                    "Podría conservar conversaciones completas o PII innecesaria."
                ),
                impact=4,
                likelihood=3,
                controls_missing=["estado estructurado", "TTL", "sanitización previa"],
                recommendation="Guardar solo campos operativos necesarios y añadir expiración.",
            )
        )

    if not profile.get("has_sensitive_data_guard"):
        findings.append(
            RiskFinding(
                risk_id="DATA-001",
                title="Sin protección de datos sensibles",
                category="sensitive_data",
                description=(
                    "No hay guard explícito para detectar, redactar o bloquear PII y secretos."
                ),
                impact=5,
                likelihood=4,
                controls_missing=["input guard", "output guard", "tool output guard"],
                recommendation="Añadir sanitización en input, tool output, RAG y respuesta final.",
            )
        )

    if not profile.get("uses_model_gateway"):
        findings.append(
            RiskFinding(
                risk_id="MODEL-001",
                title="Modelo expuesto sin gateway",
                category="model_exposure",
                description=(
                    "La aplicación no centraliza la selección de modelo ni limita alias, "
                    "parámetros o exposición de detalles internos."
                ),
                impact=4,
                likelihood=4,
                controls_missing=["model gateway", "alias lógicos", "output shielding"],
                recommendation="Usar política de exposición y routing por alias lógico.",
            )
        )

    if profile.get("stores_full_transcripts"):
        findings.append(
            RiskFinding(
                risk_id="AUD-001",
                title="Transcripciones completas retenidas",
                category="audit",
                description=(
                    "Se almacenan conversaciones completas. Esto aumenta el riesgo de conservar PII, "
                    "secretos o información interna."
                ),
                impact=4,
                likelihood=3,
                controls_missing=["hash de input", "eventos estructurados", "retención corta"],
                recommendation="Sustituir por eventos estructurados y conservar transcripción solo si es imprescindible.",
            )
        )

    if not profile.get("has_audit_events"):
        findings.append(
            RiskFinding(
                risk_id="AUD-002",
                title="Auditoría insuficiente",
                category="audit",
                description=(
                    "No hay eventos de auditoría suficientes para reconstruir decisiones de tools, RAG o modelo."
                ),
                impact=4,
                likelihood=3,
                controls_missing=["run_id", "turn_id", "tool_call", "rag_retrieval"],
                recommendation="Registrar eventos estructurados con correlación por ejecución y turno.",
            )
        )

    if not profile.get("has_retention_policy"):
        findings.append(
            RiskFinding(
                risk_id="RET-001",
                title="Sin política de retención",
                category="retention",
                description=(
                    "No existe política centralizada para eliminar, compactar o archivar eventos y memoria."
                ),
                impact=4,
                likelihood=3,
                controls_missing=["retention_policies.json", "purge log", "TTL"],
                recommendation="Definir retención por tipo de dato y ejecutar revisiones periódicas.",
            )
        )

    if not findings:
        findings.append(
            RiskFinding(
                risk_id="OK-001",
                title="Sin riesgos críticos detectados por reglas básicas",
                category="summary",
                description=(
                    "El perfil declara controles mínimos para identidad, acceso, RAG, datos sensibles, "
                    "modelo, auditoría y retención."
                ),
                impact=1,
                likelihood=1,
                controls_present=[
                    "identity_context",
                    "access_policy",
                    "sensitive_data_guard",
                    "audit_events",
                    "retention_policy",
                    "model_gateway",
                ],
                recommendation="Revisar manualmente riesgos específicos del caso de uso.",
                status=RiskStatus.MITIGATED,
            )
        )

    return findings