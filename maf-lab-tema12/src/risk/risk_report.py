from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src.risk.risk_model import RiskAssessment, RiskFinding


def render_markdown_report(assessment: RiskAssessment) -> str:
    lines: list[str] = []

    lines.append(f"### Informe de evaluación de riesgos: {assessment.agent_name}")
    lines.append("")
    lines.append(f"- Entorno: `{assessment.environment}`")
    lines.append(f"- Severidad máxima: `{assessment.highest_severity}`")
    lines.append(f"- Score total: `{assessment.total_score}`")
    lines.append(f"- Hallazgos: `{len(assessment.findings)}`")
    lines.append("")

    lines.append("| ID | Categoría | Riesgo | Impacto | Prob. | Score | Severidad | Estado |")
    lines.append("|---|---|---|---:|---:|---:|---|---|")

    for finding in sorted(assessment.findings, key=lambda item: item.score, reverse=True):
        lines.append(
            "| "
            f"{finding.risk_id} | "
            f"{finding.category} | "
            f"{finding.title} | "
            f"{finding.impact} | "
            f"{finding.likelihood} | "
            f"{finding.score} | "
            f"{finding.severity} | "
            f"{finding.status} |"
        )

    lines.append("")
    lines.append("### Detalle de hallazgos")
    lines.append("")

    for finding in sorted(assessment.findings, key=lambda item: item.score, reverse=True):
        lines.append(f"#### {finding.risk_id} - {finding.title}")
        lines.append("")
        lines.append(f"Categoría: `{finding.category}`")
        lines.append("")
        lines.append(f"Descripción: {finding.description}")
        lines.append("")
        lines.append(f"Impacto: `{finding.impact}`")
        lines.append("")
        lines.append(f"Probabilidad: `{finding.likelihood}`")
        lines.append("")
        lines.append(f"Score: `{finding.score}`")
        lines.append("")
        lines.append(f"Severidad: `{finding.severity}`")
        lines.append("")
        if finding.controls_present:
            lines.append("Controles presentes:")
            for control in finding.controls_present:
                lines.append(f"- {control}")
            lines.append("")
        if finding.controls_missing:
            lines.append("Controles pendientes:")
            for control in finding.controls_missing:
                lines.append(f"- {control}")
            lines.append("")
        lines.append(f"Recomendación: {finding.recommendation}")
        lines.append("")

    return "\n".join(lines)


def save_assessment_json(assessment: RiskAssessment, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "agent_name": assessment.agent_name,
        "environment": assessment.environment,
        "highest_severity": assessment.highest_severity.value,
        "total_score": assessment.total_score,
        "findings": [asdict(finding) for finding in assessment.findings],
    }

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_markdown_report(content: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")