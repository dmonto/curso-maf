from __future__ import annotations

from pathlib import Path
from typing import Any

from src.pipeline_governance.governance_model import (
    GateStatus,
    GovernanceFinding,
    PipelineGateResult,
)
from src.pipeline_governance.governance_loader import (
    load_agent_profile,
    load_compliance_report,
    load_evaluation_summary,
    load_governance_config,
    load_risk_report,
)


def _finding(
    *,
    check_id: str,
    title: str,
    status: GateStatus,
    severity: str,
    description: str,
    recommendation: str,
    metadata: dict[str, Any] | None = None,
) -> GovernanceFinding:
    return GovernanceFinding(
        check_id=check_id,
        title=title,
        status=status,
        severity=severity,
        description=description,
        recommendation=recommendation,
        metadata=metadata or {},
    )


def check_required_files(config: dict[str, Any]) -> list[GovernanceFinding]:
    findings: list[GovernanceFinding] = []

    for file_path in config.get("required_files", []):
        exists = Path(file_path).exists()

        findings.append(
            _finding(
                check_id="PIPE-FILE-001",
                title=f"Fichero requerido: {file_path}",
                status=GateStatus.PASS if exists else GateStatus.FAIL,
                severity="high" if not exists else "info",
                description=(
                    "El fichero requerido existe."
                    if exists
                    else "Falta un fichero requerido para evaluar el pipeline."
                ),
                recommendation=(
                    "Sin acción."
                    if exists
                    else f"Crea o genera el fichero antes de continuar: {file_path}"
                ),
                metadata={"file_path": file_path},
            )
        )

    return findings


def check_evaluation(
    *,
    environment_policy: dict[str, Any],
    governance_config: dict[str, Any],
    evaluation: dict[str, Any] | None,
) -> list[GovernanceFinding]:
    if not environment_policy.get("require_evaluation"):
        return [
            _finding(
                check_id="PIPE-EVAL-000",
                title="Evaluación no requerida",
                status=GateStatus.WARN,
                severity="low",
                description="Este entorno no exige evaluación automática.",
                recommendation="Mantén evaluación al menos en test y prod.",
            )
        ]

    if evaluation is None:
        return [
            _finding(
                check_id="PIPE-EVAL-001",
                title="Informe de evaluación ausente",
                status=GateStatus.FAIL,
                severity="high",
                description="No existe reports/evaluation_summary.json.",
                recommendation="Ejecuta la evaluación automática del agente antes del gate.",
            )
        ]

    minimum = governance_config.get("minimum_evaluation", {})
    min_cases = int(minimum.get("min_cases_run", 0))
    min_pass_rate = float(minimum.get("min_pass_rate", 0))

    cases_run = int(evaluation.get("cases_run", 0))
    pass_rate = float(evaluation.get("pass_rate", 0))

    findings: list[GovernanceFinding] = []

    findings.append(
        _finding(
            check_id="PIPE-EVAL-002",
            title="Número mínimo de casos de evaluación",
            status=GateStatus.PASS if cases_run >= min_cases else GateStatus.FAIL,
            severity="high" if cases_run < min_cases else "info",
            description=f"Casos ejecutados: {cases_run}. Mínimo requerido: {min_cases}.",
            recommendation=(
                "Sin acción."
                if cases_run >= min_cases
                else "Amplía el conjunto de evaluación antes de promover."
            ),
            metadata={"cases_run": cases_run, "min_cases_run": min_cases},
        )
    )

    findings.append(
        _finding(
            check_id="PIPE-EVAL-003",
            title="Tasa mínima de éxito",
            status=GateStatus.PASS if pass_rate >= min_pass_rate else GateStatus.FAIL,
            severity="high" if pass_rate < min_pass_rate else "info",
            description=f"Pass rate: {pass_rate:.2%}. Mínimo requerido: {min_pass_rate:.2%}.",
            recommendation=(
                "Sin acción."
                if pass_rate >= min_pass_rate
                else "Revisa regresiones de prompt, tools o recuperación RAG."
            ),
            metadata={"pass_rate": pass_rate, "min_pass_rate": min_pass_rate},
        )
    )

    return findings


def check_risk_report(
    *,
    environment_policy: dict[str, Any],
    risk_report: dict[str, Any] | None,
) -> list[GovernanceFinding]:
    if not environment_policy.get("require_risk_assessment"):
        return [
            _finding(
                check_id="PIPE-RISK-000",
                title="Evaluación de riesgos no obligatoria en este entorno",
                status=GateStatus.WARN,
                severity="low",
                description="El entorno actual permite continuar sin informe de riesgo.",
                recommendation="Exígelo para test y producción.",
            )
        ]

    if risk_report is None:
        return [
            _finding(
                check_id="PIPE-RISK-001",
                title="Informe de riesgos ausente",
                status=GateStatus.FAIL,
                severity="critical",
                description="No existe reports/agent_risk_assessment.json.",
                recommendation="Ejecuta check_agent_risk.py antes del gate de pipeline.",
            )
        ]

    highest = risk_report.get("highest_severity", "low")

    block_high = bool(environment_policy.get("block_on_high_risk"))
    block_critical = bool(environment_policy.get("block_on_critical_risk"))

    should_block = (
        highest == "critical" and block_critical
    ) or (
        highest == "high" and block_high
    )

    return [
        _finding(
            check_id="PIPE-RISK-002",
            title="Severidad máxima de riesgo",
            status=GateStatus.FAIL if should_block else GateStatus.PASS,
            severity=highest,
            description=f"Severidad máxima detectada: {highest}.",
            recommendation=(
                "Mitiga o acepta formalmente los riesgos antes de promover."
                if should_block
                else "Sin acción."
            ),
            metadata={"highest_severity": highest},
        )
    ]


def check_compliance_report(
    *,
    environment_policy: dict[str, Any],
    compliance_report: dict[str, Any] | None,
) -> list[GovernanceFinding]:
    if not environment_policy.get("require_compliance_report"):
        return [
            _finding(
                check_id="PIPE-CMP-000",
                title="Informe de cumplimiento no obligatorio en este entorno",
                status=GateStatus.WARN,
                severity="low",
                description="El entorno actual no exige informe de cumplimiento.",
                recommendation="Exígelo antes de pasar a test o prod.",
            )
        ]

    if compliance_report is None:
        return [
            _finding(
                check_id="PIPE-CMP-001",
                title="Informe de cumplimiento ausente",
                status=GateStatus.FAIL,
                severity="critical",
                description="No existe reports/compliance_report.json.",
                recommendation="Ejecuta check_compliance.py antes del gate de pipeline.",
            )
        ]

    blocking = compliance_report.get("blocking_findings", [])
    passed = bool(compliance_report.get("passed"))

    return [
        _finding(
            check_id="PIPE-CMP-002",
            title="Resultado de cumplimiento",
            status=GateStatus.PASS if passed else GateStatus.FAIL,
            severity="critical" if blocking else "high",
            description=f"Hallazgos bloqueantes: {len(blocking)}.",
            recommendation=(
                "Completa controles y evidencias pendientes."
                if not passed
                else "Sin acción."
            ),
            metadata={"blocking_findings": len(blocking)},
        )
    ]


def check_model_aliases(
    *,
    environment_policy: dict[str, Any],
    agent_profile: dict[str, Any] | None,
) -> list[GovernanceFinding]:
    if agent_profile is None:
        return [
            _finding(
                check_id="PIPE-MODEL-001",
                title="Perfil del agente ausente",
                status=GateStatus.FAIL,
                severity="high",
                description="No se puede comprobar el uso de modelos sin agent_risk_profile.json.",
                recommendation="Crea el perfil del agente antes de continuar.",
            )
        ]

    allowed = set(environment_policy.get("allowed_model_aliases", []))
    exposed = set(agent_profile.get("max_model_aliases_exposed", []))
    not_allowed = sorted(exposed - allowed)

    return [
        _finding(
            check_id="PIPE-MODEL-002",
            title="Alias de modelo permitidos por entorno",
            status=GateStatus.PASS if not not_allowed else GateStatus.FAIL,
            severity="high" if not_allowed else "info",
            description=(
                "Todos los alias expuestos están permitidos."
                if not not_allowed
                else f"Hay alias no permitidos para el entorno: {not_allowed}"
            ),
            recommendation=(
                "Sin acción."
                if not not_allowed
                else "Ajusta el model gateway o la política del entorno."
            ),
            metadata={
                "allowed_model_aliases": sorted(allowed),
                "exposed_model_aliases": sorted(exposed),
                "not_allowed": not_allowed,
            },
        )
    ]


def check_transcript_policy(
    *,
    environment_policy: dict[str, Any],
    agent_profile: dict[str, Any] | None,
) -> list[GovernanceFinding]:
    if agent_profile is None:
        return []

    stores_full_transcripts = bool(agent_profile.get("stores_full_transcripts"))
    allow_full_transcripts = bool(environment_policy.get("allow_full_transcripts"))

    blocked = stores_full_transcripts and not allow_full_transcripts

    return [
        _finding(
            check_id="PIPE-RET-001",
            title="Retención de transcripciones completas",
            status=GateStatus.FAIL if blocked else GateStatus.PASS,
            severity="high" if blocked else "info",
            description=(
                "El perfil no conserva transcripciones completas en este entorno."
                if not blocked
                else "El perfil conserva transcripciones completas, pero el entorno no lo permite."
            ),
            recommendation=(
                "Sin acción."
                if not blocked
                else "Desactiva transcripciones completas o limita su retención."
            ),
            metadata={
                "stores_full_transcripts": stores_full_transcripts,
                "allow_full_transcripts": allow_full_transcripts,
            },
        )
    ]


def run_pipeline_governance_gate(target_environment: str) -> PipelineGateResult:
    config = load_governance_config()
    environments = config["environments"]

    if target_environment not in environments:
        raise ValueError(
            f"Entorno no reconocido: {target_environment}. "
            f"Opciones: {', '.join(environments)}"
        )

    environment_policy = environments[target_environment]

    agent_profile = load_agent_profile()
    evaluation = load_evaluation_summary()
    risk_report = load_risk_report()
    compliance_report = load_compliance_report()

    findings: list[GovernanceFinding] = []
    findings.extend(check_required_files(config))
    findings.extend(
        check_evaluation(
            environment_policy=environment_policy,
            governance_config=config,
            evaluation=evaluation,
        )
    )
    findings.extend(
        check_risk_report(
            environment_policy=environment_policy,
            risk_report=risk_report,
        )
    )
    findings.extend(
        check_compliance_report(
            environment_policy=environment_policy,
            compliance_report=compliance_report,
        )
    )
    findings.extend(
        check_model_aliases(
            environment_policy=environment_policy,
            agent_profile=agent_profile,
        )
    )
    findings.extend(
        check_transcript_policy(
            environment_policy=environment_policy,
            agent_profile=agent_profile,
        )
    )

    status = GateStatus.FAIL if any(item.status == GateStatus.FAIL for item in findings) else GateStatus.PASS

    if status == GateStatus.PASS and any(item.status == GateStatus.WARN for item in findings):
        status = GateStatus.WARN

    return PipelineGateResult(
        pipeline_name=config["pipeline_name"],
        target_environment=target_environment,
        status=status,
        findings=findings,
    )