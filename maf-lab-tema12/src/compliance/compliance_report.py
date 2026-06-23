from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src.compliance.compliance_model import (
    ComplianceAssessment,
    ComplianceFinding,
    ComplianceRequirement,
    ComplianceStatus,
)
from src.compliance.evidence_checker import (
    event_types_present,
    evidence_file_exists,
    load_audit_events,
    profile_has_control,
)


def evaluate_compliance(
    *,
    framework: str,
    version: str,
    requirements: list[ComplianceRequirement],
    profile: dict,
) -> ComplianceAssessment:
    events = load_audit_events(
        [
            Path("logs/interaction_audit.jsonl"),
            Path("logs/sensitive_data_audit.jsonl"),
            Path("logs/model_exposure_audit.jsonl"),
        ]
    )

    present_event_types = event_types_present(events)

    findings: list[ComplianceFinding] = []

    for requirement in requirements:
        controls_present = [
            control
            for control in requirement.required_controls
            if profile_has_control(profile, control)
        ]

        controls_missing = [
            control
            for control in requirement.required_controls
            if control not in controls_present
        ]

        evidence_events_present = [
            event_type
            for event_type in requirement.required_evidence_events
            if event_type in present_event_types
        ]

        evidence_events_missing = [
            event_type
            for event_type in requirement.required_evidence_events
            if event_type not in evidence_events_present
        ]

        evidence_files_present = [
            file_path
            for file_path in requirement.required_evidence_files
            if evidence_file_exists(file_path)
        ]

        evidence_files_missing = [
            file_path
            for file_path in requirement.required_evidence_files
            if file_path not in evidence_files_present
        ]

        if not controls_missing and not evidence_events_missing and not evidence_files_missing:
            status = ComplianceStatus.PASS
        elif controls_present or evidence_events_present or evidence_files_present:
            status = ComplianceStatus.PARTIAL
        else:
            status = ComplianceStatus.FAIL

        if status == ComplianceStatus.PASS:
            recommendation = "Mantener control y evidencias en revisiones periódicas."
        else:
            recommendation = (
                "Completar controles pendientes y generar evidencias verificables "
                "antes de promover el agente a un entorno superior."
            )

        findings.append(
            ComplianceFinding(
                requirement_id=requirement.id,
                domain=requirement.domain,
                title=requirement.title,
                status=status,
                severity=requirement.severity_if_missing,
                controls_present=controls_present,
                controls_missing=controls_missing,
                evidence_events_present=evidence_events_present,
                evidence_events_missing=evidence_events_missing,
                evidence_files_present=evidence_files_present,
                evidence_files_missing=evidence_files_missing,
                recommendation=recommendation,
            )
        )

    return ComplianceAssessment(
        framework=framework,
        version=version,
        agent_name=profile.get("agent_name", "unknown_agent"),
        environment=profile.get("environment", "unknown"),
        findings=findings,
    )


def render_compliance_markdown(assessment: ComplianceAssessment) -> str:
    lines: list[str] = []

    lines.append(f"### Informe de cumplimiento: {assessment.agent_name}")
    lines.append("")
    lines.append(f"- Framework: `{assessment.framework}`")
    lines.append(f"- Versión: `{assessment.version}`")
    lines.append(f"- Entorno: `{assessment.environment}`")
    lines.append(f"- Resultado global: `{'PASS' if assessment.passed else 'REVIEW_REQUIRED'}`")
    lines.append(f"- Hallazgos bloqueantes: `{len(assessment.blocking_findings)}`")
    lines.append("")

    lines.append("| Requisito | Dominio | Estado | Severidad | Controles pendientes | Evidencias pendientes |")
    lines.append("|---|---|---|---|---|---|")

    for finding in assessment.findings:
        missing_controls = ", ".join(finding.controls_missing) or "-"
        missing_evidence = ", ".join(
            finding.evidence_events_missing + finding.evidence_files_missing
        ) or "-"

        lines.append(
            f"| {finding.requirement_id} | "
            f"{finding.domain} | "
            f"{finding.status.value} | "
            f"{finding.severity.value} | "
            f"{missing_controls} | "
            f"{missing_evidence} |"
        )

    lines.append("")
    lines.append("### Detalle")
    lines.append("")

    for finding in assessment.findings:
        lines.append(f"#### {finding.requirement_id} - {finding.title}")
        lines.append("")
        lines.append(f"- Estado: `{finding.status.value}`")
        lines.append(f"- Severidad si falta: `{finding.severity.value}`")
        lines.append(f"- Controles presentes: `{', '.join(finding.controls_present) or '-'}`")
        lines.append(f"- Controles pendientes: `{', '.join(finding.controls_missing) or '-'}`")
        lines.append(f"- Evidencias presentes: `{', '.join(finding.evidence_events_present + finding.evidence_files_present) or '-'}`")
        lines.append(f"- Evidencias pendientes: `{', '.join(finding.evidence_events_missing + finding.evidence_files_missing) or '-'}`")
        lines.append(f"- Recomendación: {finding.recommendation}")
        lines.append("")

    return "\n".join(lines)


def save_compliance_outputs(assessment: ComplianceAssessment) -> None:
    Path("reports").mkdir(parents=True, exist_ok=True)

    markdown = render_compliance_markdown(assessment)
    Path("reports/compliance_report.md").write_text(markdown, encoding="utf-8")

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        **asdict(assessment),
        "passed": assessment.passed,
        "blocking_findings": [asdict(item) for item in assessment.blocking_findings],
    }

    Path("reports/compliance_report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )