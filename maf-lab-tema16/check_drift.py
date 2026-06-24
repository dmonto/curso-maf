import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


CURRENT_REPORT_PATH = Path("reports/quality_metrics_report.json")
HISTORY_DIR = Path("reports/history")
HISTORY_PATH = HISTORY_DIR / "quality_runs.jsonl"
DRIFT_REPORT_PATH = Path("reports/drift_report.json")

RECENT_WINDOW_SIZE = 5
MIN_HISTORY_FOR_DRIFT = 3

THRESHOLDS = {
    "average_quality_score": {
        "warning_drop": 0.05,
        "critical_drop": 0.10,
        "minimum": 0.80,
    },
    "pass_rate": {
        "warning_drop": 0.05,
        "critical_drop": 0.10,
        "minimum": 0.90,
    },
    "safety_avg": {
        "warning_drop": 0.01,
        "critical_drop": 0.05,
        "minimum": 0.95,
    },
    "groundedness_avg": {
        "warning_drop": 0.05,
        "critical_drop": 0.10,
        "minimum": 0.85,
    },
    "tool_accuracy_avg": {
        "warning_drop": 0.05,
        "critical_drop": 0.10,
        "minimum": 0.80,
    },
}


@dataclass
class DriftFinding:
    metric: str
    severity: str
    kind: str
    detail: str
    baseline_value: float
    recent_value: float
    delta: float


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero requerido: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def safe_metric_avg(report: dict[str, Any], metric_name: str) -> float | None:
    metric_summary = report.get("metric_summary", {})
    metric_data = metric_summary.get(metric_name)

    if not metric_data:
        return None

    value = metric_data.get("avg")

    if value is None:
        return None

    return float(value)


def extract_run_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "run_at_utc": report.get("run_at_utc") or datetime.now(timezone.utc).isoformat(),
        "agent_name": report.get("agent_name"),
        "prompt_version": report.get("prompt_version"),
        "total_cases": report.get("total_cases"),
        "passed_cases": report.get("passed_cases"),
        "failed_cases": report.get("failed_cases"),
        "pass_rate": float(report.get("pass_rate", 0.0)),
        "average_quality_score": float(report.get("average_quality_score", 0.0)),
        "safety_avg": safe_metric_avg(report, "safety"),
        "groundedness_avg": safe_metric_avg(report, "groundedness"),
        "tool_accuracy_avg": safe_metric_avg(report, "tool_accuracy"),
        "completeness_avg": safe_metric_avg(report, "completeness"),
        "relevance_avg": safe_metric_avg(report, "relevance"),
        "conciseness_avg": safe_metric_avg(report, "conciseness"),
    }

    return {
        key: value
        for key, value in summary.items()
        if value is not None
    }


def append_history(run_summary: dict[str, Any]) -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    with HISTORY_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(run_summary, ensure_ascii=False) + "\n")


def load_history() -> list[dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []

    runs: list[dict[str, Any]] = []

    with HISTORY_PATH.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Histórico inválido en línea {line_number}: {exc}") from exc

    return runs


def average_metric(runs: list[dict[str, Any]], metric: str) -> float | None:
    values = [
        float(run[metric])
        for run in runs
        if run.get(metric) is not None
    ]

    if not values:
        return None

    return round(mean(values), 4)


def detect_metric_drift(
    metric: str,
    baseline_value: float,
    recent_value: float,
) -> DriftFinding | None:
    config = THRESHOLDS[metric]
    delta = round(recent_value - baseline_value, 4)
    drop = baseline_value - recent_value

    if recent_value < config["minimum"]:
        return DriftFinding(
            metric=metric,
            severity="critical",
            kind="below_minimum",
            detail=f"La métrica {metric} está por debajo del mínimo permitido.",
            baseline_value=baseline_value,
            recent_value=recent_value,
            delta=delta,
        )

    if drop >= config["critical_drop"]:
        return DriftFinding(
            metric=metric,
            severity="critical",
            kind="critical_drop",
            detail=f"La métrica {metric} ha caído por encima del umbral crítico.",
            baseline_value=baseline_value,
            recent_value=recent_value,
            delta=delta,
        )

    if drop >= config["warning_drop"]:
        return DriftFinding(
            metric=metric,
            severity="warning",
            kind="warning_drop",
            detail=f"La métrica {metric} muestra una caída relevante.",
            baseline_value=baseline_value,
            recent_value=recent_value,
            delta=delta,
        )

    return None


def detect_drift(history: list[dict[str, Any]]) -> list[DriftFinding]:
    if len(history) < MIN_HISTORY_FOR_DRIFT:
        return []

    recent_runs = history[-RECENT_WINDOW_SIZE:]
    baseline_runs = history[:-RECENT_WINDOW_SIZE] or history[:-1]

    if not baseline_runs:
        return []

    findings: list[DriftFinding] = []

    for metric in THRESHOLDS:
        baseline_value = average_metric(baseline_runs, metric)
        recent_value = average_metric(recent_runs, metric)

        if baseline_value is None or recent_value is None:
            continue

        finding = detect_metric_drift(
            metric=metric,
            baseline_value=baseline_value,
            recent_value=recent_value,
        )

        if finding:
            findings.append(finding)

    return findings


def main() -> None:
    current_report = load_json(CURRENT_REPORT_PATH)
    current_summary = extract_run_summary(current_report)

    append_history(current_summary)
    history = load_history()

    findings = detect_drift(history)

    critical_findings = [
        finding for finding in findings
        if finding.severity == "critical"
    ]

    recent_runs = history[-RECENT_WINDOW_SIZE:]
    baseline_runs = history[:-RECENT_WINDOW_SIZE] or history[:-1]

    drift_report = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "history_path": str(HISTORY_PATH),
        "history_runs": len(history),
        "recent_window_size": RECENT_WINDOW_SIZE,
        "min_history_for_drift": MIN_HISTORY_FOR_DRIFT,
        "current_summary": current_summary,
        "baseline_summary": {
            metric: average_metric(baseline_runs, metric)
            for metric in THRESHOLDS
        },
        "recent_summary": {
            metric: average_metric(recent_runs, metric)
            for metric in THRESHOLDS
        },
        "total_findings": len(findings),
        "critical_findings": len(critical_findings),
        "has_critical_drift": bool(critical_findings),
        "findings": [asdict(finding) for finding in findings],
    }

    DRIFT_REPORT_PATH.write_text(
        json.dumps(drift_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("--- DRIFT CHECK ---")
    print(f"Ejecuciones históricas: {len(history)}")
    print(f"Findings totales: {len(findings)}")
    print(f"Findings críticos: {len(critical_findings)}")
    print(f"Reporte: {DRIFT_REPORT_PATH}")

    if len(history) < MIN_HISTORY_FOR_DRIFT:
        print("Aún no hay suficiente histórico para detectar drift de forma útil.")
        return

    if not findings:
        print("Sin drift detectado.")

    for finding in findings:
        print()
        print(f"[{finding.severity.upper()}] {finding.metric} | {finding.kind}")
        print(f"  {finding.detail}")
        print(f"  Baseline: {finding.baseline_value}")
        print(f"  Reciente: {finding.recent_value}")
        print(f"  Delta:    {finding.delta}")

    if critical_findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()