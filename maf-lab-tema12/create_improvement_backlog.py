from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPORTS_DIR = Path("reports")
IMPROVEMENTS_DIR = Path("improvements")

ANALYSIS_REPORT = REPORTS_DIR / "analysis_report.json"
QUALITY_REPORT = REPORTS_DIR / "quality_metrics_report.json"
REGRESSION_REPORT = REPORTS_DIR / "regression_report.json"
DRIFT_REPORT = REPORTS_DIR / "drift_report.json"
MODEL_COMPARISON_REPORT = REPORTS_DIR / "model_comparison_report.json"

BACKLOG_JSON = IMPROVEMENTS_DIR / "improvement_backlog.json"
BACKLOG_MD = IMPROVEMENTS_DIR / "improvement_backlog.md"


@dataclass
class ImprovementItem:
    id: str
    title: str
    source: str
    owner: str
    severity: str
    hypothesis: str
    proposed_change: str
    acceptance_criteria: list[str]
    impact: int
    frequency: int
    effort: int
    priority_score: float
    status: str = "proposed"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def calculate_priority(
    severity: str,
    impact: int,
    frequency: int,
    effort: int,
) -> float:
    severity_weight = {
        "critical": 5,
        "warning": 3,
        "info": 1,
    }.get(severity, 1)

    effort = max(effort, 1)

    return round((impact * severity_weight * frequency) / effort, 2)


def owner_for_finding(source: str, title: str, detail: str) -> str:
    text = f"{source} {title} {detail}".lower()

    if "tool" in text:
        return "tools"

    if "safety" in text or "sensible" in text or "seguridad" in text:
        return "prompt/security"

    if "groundedness" in text or "grounding" in text:
        return "rag/context"

    if "regression" in text or "regresión" in text:
        return "release-owner"

    if "drift" in text:
        return "ops"

    if "modelo" in text or "model" in text:
        return "architecture"

    return "agent-owner"


def build_item_from_finding(index: int, finding: dict[str, Any]) -> ImprovementItem:
    source = finding.get("source", "unknown")
    severity = finding.get("severity", "info")
    title = finding.get("title", "Finding sin título")
    detail = finding.get("detail", "")

    owner = owner_for_finding(source, title, detail)

    if severity == "critical":
        impact = 5
        effort = 2
    elif severity == "warning":
        impact = 3
        effort = 2
    else:
        impact = 1
        effort = 1

    frequency = 3

    hypothesis = (
        f"Si corregimos el problema detectado en {source}, "
        "mejorará la calidad del agente sin introducir regresiones críticas."
    )

    proposed_change = finding.get("recommendation", "Revisar el finding y definir cambio técnico.")

    acceptance_criteria = [
        "La suite offline pasa correctamente.",
        "La evaluación online no introduce fallos críticos.",
        "No aparece regresión crítica frente a baseline.",
    ]

    if "safety" in f"{title} {detail}".lower():
        acceptance_criteria.append("safety.avg >= 0.95.")

    if "groundedness" in f"{title} {detail}".lower():
        acceptance_criteria.append("groundedness.avg >= 0.85.")

    if "tool" in f"{title} {detail}".lower():
        acceptance_criteria.append("check_tool_validation.py pasa al 100%.")

    priority_score = calculate_priority(
        severity=severity,
        impact=impact,
        frequency=frequency,
        effort=effort,
    )

    return ImprovementItem(
        id=f"IMP-{index:03d}",
        title=title,
        source=source,
        owner=owner,
        severity=severity,
        hypothesis=hypothesis,
        proposed_change=proposed_change,
        acceptance_criteria=acceptance_criteria,
        impact=impact,
        frequency=frequency,
        effort=effort,
        priority_score=priority_score,
    )


def add_quality_specific_items(
    quality_report: dict[str, Any] | None,
    items: list[ImprovementItem],
) -> None:
    if not quality_report:
        return

    metric_summary = quality_report.get("metric_summary", {})

    metric_rules = [
        {
            "metric": "completeness",
            "threshold": 0.85,
            "title": "Mejorar completitud de respuestas",
            "owner": "prompt",
            "change": "Añadir checklist mínimo de respuesta para incidencias de soporte.",
        },
        {
            "metric": "conciseness",
            "threshold": 0.85,
            "title": "Reducir longitud de respuestas",
            "owner": "prompt",
            "change": "Limitar respuestas a pasos accionables y evitar explicación redundante.",
        },
        {
            "metric": "tool_accuracy",
            "threshold": 0.85,
            "title": "Mejorar precisión en uso de tools",
            "owner": "tools",
            "change": "Revisar nombres, descripciones y señales esperadas de tools.",
        },
    ]

    for rule in metric_rules:
        metric_data = metric_summary.get(rule["metric"])

        if not metric_data:
            continue

        avg = float(metric_data.get("avg", 1.0))

        if avg >= rule["threshold"]:
            continue

        severity = "warning"
        impact = 3
        frequency = 3
        effort = 2

        items.append(
            ImprovementItem(
                id=f"IMP-{len(items) + 1:03d}",
                title=rule["title"],
                source="quality_metrics",
                owner=rule["owner"],
                severity=severity,
                hypothesis=(
                    f"La métrica {rule['metric']} está en {avg}. "
                    f"Si ajustamos la capa {rule['owner']}, debería superar {rule['threshold']}."
                ),
                proposed_change=rule["change"],
                acceptance_criteria=[
                    f"{rule['metric']}.avg >= {rule['threshold']}.",
                    "average_quality_score >= 0.80.",
                    "Sin regresiones críticas.",
                ],
                impact=impact,
                frequency=frequency,
                effort=effort,
                priority_score=calculate_priority(severity, impact, frequency, effort),
            )
        )


def add_model_routing_item(
    model_report: dict[str, Any] | None,
    items: list[ImprovementItem],
) -> None:
    if not model_report:
        return

    recommended_model = model_report.get("recommended_model")

    if not recommended_model:
        return

    ranking = model_report.get("ranking", [])

    if not ranking:
        return

    top_model = ranking[0].get("model_alias")

    if top_model != recommended_model:
        return

    items.append(
        ImprovementItem(
            id=f"IMP-{len(items) + 1:03d}",
            title="Revisar routing de modelos según benchmark",
            source="model_comparison",
            owner="architecture",
            severity="info",
            hypothesis=(
                f"El benchmark recomienda {recommended_model}. "
                "Usar routing por tipo de tarea puede mejorar coste, latencia o calidad."
            ),
            proposed_change=(
                "Documentar qué modelo usar para consulta simple, borrador de ticket, "
                "acción sensible y fallback."
            ),
            acceptance_criteria=[
                "README actualizado con tabla de routing.",
                "check_model_comparison.py ejecutado sin fallos críticos.",
                "No hay regresiones tras aplicar el cambio.",
            ],
            impact=2,
            frequency=2,
            effort=2,
            priority_score=calculate_priority("info", 2, 2, 2),
        )
    )


def render_markdown(items: list[ImprovementItem]) -> str:
    lines: list[str] = []

    lines.append("### Backlog de mejora continua")
    lines.append("")
    lines.append("| ID | Prioridad | Severidad | Owner | Mejora | Estado |")
    lines.append("|---|---:|---|---|---|---|")

    for item in sorted(items, key=lambda x: x.priority_score, reverse=True):
        lines.append(
            f"| {item.id} | {item.priority_score} | `{item.severity}` | "
            f"`{item.owner}` | {item.title} | `{item.status}` |"
        )

    lines.append("")
    lines.append("### Detalle de mejoras")
    lines.append("")

    for item in sorted(items, key=lambda x: x.priority_score, reverse=True):
        lines.append(f"#### {item.id} · {item.title}")
        lines.append("")
        lines.append(f"**Owner:** `{item.owner}`  ")
        lines.append(f"**Fuente:** `{item.source}`  ")
        lines.append(f"**Severidad:** `{item.severity}`  ")
        lines.append(f"**Prioridad:** `{item.priority_score}`")
        lines.append("")
        lines.append(f"**Hipótesis:** {item.hypothesis}")
        lines.append("")
        lines.append(f"**Cambio propuesto:** {item.proposed_change}")
        lines.append("")
        lines.append("**Criterios de aceptación:**")
        for criterion in item.acceptance_criteria:
            lines.append(f"- {criterion}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    IMPROVEMENTS_DIR.mkdir(exist_ok=True)

    analysis_report = load_json(ANALYSIS_REPORT)
    quality_report = load_json(QUALITY_REPORT)
    model_report = load_json(MODEL_COMPARISON_REPORT)

    items: list[ImprovementItem] = []

    if analysis_report:
        findings = analysis_report.get("findings", [])

        for index, finding in enumerate(findings, start=1):
            if finding.get("severity") in {"critical", "warning"}:
                items.append(build_item_from_finding(index, finding))

    add_quality_specific_items(quality_report, items)
    add_model_routing_item(model_report, items)

    items = sorted(items, key=lambda x: x.priority_score, reverse=True)

    backlog = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_items": len(items),
        "items": [asdict(item) for item in items],
    }

    BACKLOG_JSON.write_text(
        json.dumps(backlog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    BACKLOG_MD.write_text(
        render_markdown(items),
        encoding="utf-8",
    )

    print("--- IMPROVEMENT BACKLOG ---")
    print(f"Items: {len(items)}")
    print(f"JSON: {BACKLOG_JSON}")
    print(f"Markdown: {BACKLOG_MD}")

    for item in items:
        print(f"{item.id} | priority={item.priority_score} | {item.title}")


if __name__ == "__main__":
    main()