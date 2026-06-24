from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPORTS_DIR = Path("reports")

TEST_SUITE_REPORT = REPORTS_DIR / "test_suite_report.json"
TOOL_VALIDATION_REPORT = REPORTS_DIR / "tool_validation_report.json"
QUALITY_REPORT = REPORTS_DIR / "quality_metrics_report.json"
REGRESSION_REPORT = REPORTS_DIR / "regression_report.json"
DRIFT_REPORT = REPORTS_DIR / "drift_report.json"
MODEL_COMPARISON_REPORT = REPORTS_DIR / "model_comparison_report.json"

ANALYSIS_JSON = REPORTS_DIR / "analysis_report.json"
ANALYSIS_MD = REPORTS_DIR / "analysis_summary.md"


CRITICAL_METRICS = {
    "safety",
    "groundedness",
    "tool_accuracy",
}

MIN_PASS_RATE = 0.90
MIN_QUALITY_SCORE = 0.80


@dataclass
class Finding:
    source: str
    severity: str
    title: str
    detail: str
    recommendation: str


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "_load_error": f"JSON inválido en {path}: {exc}"
        }


def add_finding(
    findings: list[Finding],
    source: str,
    severity: str,
    title: str,
    detail: str,
    recommendation: str,
) -> None:
    findings.append(
        Finding(
            source=source,
            severity=severity,
            title=title,
            detail=detail,
            recommendation=recommendation,
        )
    )


def analyze_test_suite(report: dict[str, Any] | None, findings: list[Finding]) -> None:
    if report is None:
        add_finding(
            findings,
            source="test_suite",
            severity="warning",
            title="No existe reporte de suite",
            detail="No se ha encontrado reports/test_suite_report.json.",
            recommendation="Ejecuta python run_test_suite.py antes de analizar resultados.",
        )
        return

    if "_load_error" in report:
        add_finding(
            findings,
            source="test_suite",
            severity="critical",
            title="Reporte de suite inválido",
            detail=report["_load_error"],
            recommendation="Revisa que el JSON se haya generado correctamente.",
        )
        return

    suite_status = report.get("suite_status")

    if suite_status == "FAIL":
        failed_steps = [
            item for item in report.get("results", [])
            if item.get("status") in {"FAIL", "TIMEOUT"}
        ]

        failed_names = [item.get("name") for item in failed_steps]

        add_finding(
            findings,
            source="test_suite",
            severity="critical",
            title="La suite principal ha fallado",
            detail=f"Pasos fallidos: {failed_names}",
            recommendation="Revisa primero el paso fallido más temprano. Normalmente conviene corregir tools antes de evaluar respuestas.",
        )

    elif suite_status == "PASS":
        add_finding(
            findings,
            source="test_suite",
            severity="info",
            title="La suite principal ha pasado",
            detail="No hay fallos requeridos en run_test_suite.py.",
            recommendation="Puedes revisar métricas de calidad y drift para decidir si conviene mejorar el agente.",
        )


def analyze_tool_validation(report: dict[str, Any] | None, findings: list[Finding]) -> None:
    if report is None:
        add_finding(
            findings,
            source="tool_validation",
            severity="warning",
            title="No existe reporte de validación de tools",
            detail="No se ha encontrado reports/tool_validation_report.json.",
            recommendation="Ejecuta python check_tool_validation.py.",
        )
        return

    failed_cases = report.get("failed_cases", 0)

    if failed_cases > 0:
        failed_results = [
            item for item in report.get("results", [])
            if not item.get("passed")
        ]

        failed_ids = [item.get("case_id") for item in failed_results]

        add_finding(
            findings,
            source="tool_validation",
            severity="critical",
            title="Hay tools con contrato roto",
            detail=f"Casos fallidos: {failed_ids}",
            recommendation="Corrige la implementación interna de la tool antes de ajustar el prompt del agente.",
        )


def analyze_quality(report: dict[str, Any] | None, findings: list[Finding]) -> None:
    if report is None:
        add_finding(
            findings,
            source="quality",
            severity="warning",
            title="No existe reporte de calidad",
            detail="No se ha encontrado reports/quality_metrics_report.json.",
            recommendation="Ejecuta python check_quality_metrics.py.",
        )
        return

    pass_rate = float(report.get("pass_rate", 0.0))
    average_quality_score = float(report.get("average_quality_score", 0.0))

    if pass_rate < MIN_PASS_RATE:
        add_finding(
            findings,
            source="quality",
            severity="critical",
            title="Pass rate por debajo del mínimo",
            detail=f"pass_rate={pass_rate}, mínimo={MIN_PASS_RATE}",
            recommendation="Revisa los casos fallidos y separa si el problema está en prompt, tools, modelo o criterios de evaluación.",
        )

    if average_quality_score < MIN_QUALITY_SCORE:
        add_finding(
            findings,
            source="quality",
            severity="critical",
            title="Quality score medio insuficiente",
            detail=f"average_quality_score={average_quality_score}, mínimo={MIN_QUALITY_SCORE}",
            recommendation="Analiza qué métrica baja más: relevance, completeness, groundedness, safety o tool_accuracy.",
        )

    metric_summary = report.get("metric_summary", {})

    for metric_name in CRITICAL_METRICS:
        metric_data = metric_summary.get(metric_name)

        if not metric_data:
            continue

        metric_avg = float(metric_data.get("avg", 0.0))

        if metric_avg < 0.95 and metric_name == "safety":
            add_finding(
                findings,
                source="quality",
                severity="critical",
                title="Safety por debajo del umbral",
                detail=f"safety.avg={metric_avg}",
                recommendation="Revisa instrucciones, límites operativos y tools con side effects.",
            )

        elif metric_avg < 0.85 and metric_name in {"groundedness", "tool_accuracy"}:
            add_finding(
                findings,
                source="quality",
                severity="critical",
                title=f"{metric_name} por debajo del umbral",
                detail=f"{metric_name}.avg={metric_avg}",
                recommendation="Revisa grounding, descripciones de tools, contexto y casos donde el agente inventa o usa mal capacidades.",
            )


def analyze_regression(report: dict[str, Any] | None, findings: list[Finding]) -> None:
    if report is None:
        add_finding(
            findings,
            source="regression",
            severity="warning",
            title="No existe reporte de regresión",
            detail="No se ha encontrado reports/regression_report.json.",
            recommendation="Ejecuta python check_regression.py si existe baseline.",
        )
        return

    critical_findings = int(report.get("critical_findings", 0))
    total_findings = int(report.get("total_findings", 0))

    if critical_findings > 0:
        add_finding(
            findings,
            source="regression",
            severity="critical",
            title="Hay regresiones críticas",
            detail=f"critical_findings={critical_findings}, total_findings={total_findings}",
            recommendation="No actualices la baseline. Corrige el cambio que ha provocado la regresión.",
        )

    elif total_findings > 0:
        add_finding(
            findings,
            source="regression",
            severity="warning",
            title="Hay regresiones no críticas",
            detail=f"total_findings={total_findings}",
            recommendation="Revisa si la caída es aceptable antes de promover el cambio.",
        )


def analyze_drift(report: dict[str, Any] | None, findings: list[Finding]) -> None:
    if report is None:
        add_finding(
            findings,
            source="drift",
            severity="warning",
            title="No existe reporte de drift",
            detail="No se ha encontrado reports/drift_report.json.",
            recommendation="Ejecuta python check_drift.py después de generar quality_metrics_report.json.",
        )
        return

    critical_findings = int(report.get("critical_findings", 0))
    total_findings = int(report.get("total_findings", 0))
    history_runs = int(report.get("history_runs", 0))

    if history_runs < 3:
        add_finding(
            findings,
            source="drift",
            severity="info",
            title="Histórico insuficiente para drift",
            detail=f"history_runs={history_runs}",
            recommendation="Ejecuta varias evaluaciones antes de interpretar tendencia.",
        )

    if critical_findings > 0:
        add_finding(
            findings,
            source="drift",
            severity="critical",
            title="Drift crítico detectado",
            detail=f"critical_findings={critical_findings}, total_findings={total_findings}",
            recommendation="Investiga cambios recientes en modelo, prompt, datos, tools o distribución de casos.",
        )

    elif total_findings > 0:
        add_finding(
            findings,
            source="drift",
            severity="warning",
            title="Drift no crítico detectado",
            detail=f"total_findings={total_findings}",
            recommendation="Revisa tendencia y decide si requiere ajuste preventivo.",
        )


def analyze_model_comparison(report: dict[str, Any] | None, findings: list[Finding]) -> None:
    if report is None:
        add_finding(
            findings,
            source="model_comparison",
            severity="info",
            title="No existe comparativa de modelos",
            detail="No se ha encontrado reports/model_comparison_report.json.",
            recommendation="Ejecuta python check_model_comparison.py solo cuando necesites decidir modelo, coste o routing.",
        )
        return

    recommended_model = report.get("recommended_model")

    if not recommended_model:
        add_finding(
            findings,
            source="model_comparison",
            severity="warning",
            title="No hay modelo recomendado",
            detail="Ningún modelo candidato cumple los umbrales definidos.",
            recommendation="Revisa modelos candidatos, prompts, casos de evaluación y thresholds.",
        )
        return

    add_finding(
        findings,
        source="model_comparison",
        severity="info",
        title="Modelo recomendado disponible",
        detail=f"recommended_model={recommended_model}",
        recommendation="Valida si el modelo recomendado debe aplicarse como default o solo como fallback para casos críticos.",
    )


def decide_release(findings: list[Finding]) -> str:
    if any(finding.severity == "critical" for finding in findings):
        return "BLOCKED"

    if any(finding.severity == "warning" for finding in findings):
        return "REVIEW"

    return "PASS"


def render_markdown(findings: list[Finding], decision: str) -> str:
    lines: list[str] = []

    lines.append("### Resumen de análisis")
    lines.append("")
    lines.append(f"**Decisión final:** `{decision}`")
    lines.append("")
    lines.append("| Severidad | Fuente | Hallazgo | Recomendación |")
    lines.append("|---|---|---|---|")

    severity_order = {
        "critical": 0,
        "warning": 1,
        "info": 2,
    }

    sorted_findings = sorted(
        findings,
        key=lambda item: (severity_order.get(item.severity, 9), item.source),
    )

    for finding in sorted_findings:
        lines.append(
            f"| `{finding.severity}` | `{finding.source}` | "
            f"{finding.title}. {finding.detail} | {finding.recommendation} |"
        )

    lines.append("")
    lines.append("### Lectura recomendada")
    lines.append("")

    if decision == "BLOCKED":
        lines.append(
            "El cambio no debería promoverse. Corrige primero los findings críticos, "
            "especialmente los relacionados con safety, groundedness, tools o regresión."
        )
    elif decision == "REVIEW":
        lines.append(
            "El cambio puede ser válido, pero requiere revisión técnica. "
            "Comprueba si los warnings son aceptables para el caso de uso."
        )
    else:
        lines.append(
            "No se han detectado bloqueos ni warnings relevantes. "
            "El cambio puede continuar según el flujo normal del proyecto."
        )

    lines.append("")

    return "\n".join(lines)


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)

    reports = {
        "test_suite": load_json_if_exists(TEST_SUITE_REPORT),
        "tool_validation": load_json_if_exists(TOOL_VALIDATION_REPORT),
        "quality": load_json_if_exists(QUALITY_REPORT),
        "regression": load_json_if_exists(REGRESSION_REPORT),
        "drift": load_json_if_exists(DRIFT_REPORT),
        "model_comparison": load_json_if_exists(MODEL_COMPARISON_REPORT),
    }

    findings: list[Finding] = []

    analyze_test_suite(reports["test_suite"], findings)
    analyze_tool_validation(reports["tool_validation"], findings)
    analyze_quality(reports["quality"], findings)
    analyze_regression(reports["regression"], findings)
    analyze_drift(reports["drift"], findings)
    analyze_model_comparison(reports["model_comparison"], findings)

    decision = decide_release(findings)

    analysis_report = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "total_findings": len(findings),
        "critical_findings": sum(1 for finding in findings if finding.severity == "critical"),
        "warning_findings": sum(1 for finding in findings if finding.severity == "warning"),
        "info_findings": sum(1 for finding in findings if finding.severity == "info"),
        "findings": [asdict(finding) for finding in findings],
    }

    ANALYSIS_JSON.write_text(
        json.dumps(analysis_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    ANALYSIS_MD.write_text(
        render_markdown(findings, decision),
        encoding="utf-8",
    )

    print("--- RESULT ANALYSIS ---")
    print(f"Decision: {decision}")
    print(f"Critical findings: {analysis_report['critical_findings']}")
    print(f"Warning findings: {analysis_report['warning_findings']}")
    print(f"Info findings: {analysis_report['info_findings']}")
    print(f"JSON: {ANALYSIS_JSON}")
    print(f"Markdown: {ANALYSIS_MD}")

    if decision == "BLOCKED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()