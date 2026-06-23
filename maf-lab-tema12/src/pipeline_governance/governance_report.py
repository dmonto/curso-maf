from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src.pipeline_governance.governance_model import PipelineGateResult


def render_gate_markdown(result: PipelineGateResult) -> str:
    lines: list[str] = []

    lines.append(f"### Gate de gobierno de pipeline: {result.pipeline_name}")
    lines.append("")
    lines.append(f"- Entorno objetivo: `{result.target_environment}`")
    lines.append(f"- Estado: `{result.status.value}`")
    lines.append(f"- Checks ejecutados: `{len(result.findings)}`")
    lines.append(f"- Bloqueantes: `{len(result.blocking_findings)}`")
    lines.append("")

    lines.append("| Check | Estado | Severidad | Título | Recomendación |")
    lines.append("|---|---|---|---|---|")

    for finding in result.findings:
        lines.append(
            f"| {finding.check_id} | "
            f"{finding.status.value} | "
            f"{finding.severity} | "
            f"{finding.title} | "
            f"{finding.recommendation} |"
        )

    lines.append("")
    lines.append("### Detalle de checks")
    lines.append("")

    for finding in result.findings:
        lines.append(f"#### {finding.check_id} - {finding.title}")
        lines.append("")
        lines.append(f"- Estado: `{finding.status.value}`")
        lines.append(f"- Severidad: `{finding.severity}`")
        lines.append(f"- Descripción: {finding.description}")
        lines.append(f"- Recomendación: {finding.recommendation}")
        if finding.metadata:
            lines.append("")
            lines.append("Metadata:")
            lines.append("```json")
            lines.append(json.dumps(finding.metadata, ensure_ascii=False, indent=2))
            lines.append("```")
        lines.append("")

    return "\n".join(lines)


def save_gate_outputs(result: PipelineGateResult) -> None:
    Path("reports").mkdir(parents=True, exist_ok=True)

    markdown = render_gate_markdown(result)
    Path("reports/pipeline_governance_report.md").write_text(markdown, encoding="utf-8")

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        **asdict(result),
        "passed": result.passed,
        "blocking_findings": [asdict(item) for item in result.blocking_findings],
    }

    Path("reports/pipeline_governance_report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )