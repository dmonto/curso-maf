import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


BASELINE_PATH = Path("baselines/quality_baseline.json")
CURRENT_REPORT_PATH = Path("reports/quality_metrics_report.json")
REGRESSION_REPORT_PATH = Path("reports/regression_report.json")


MIN_ACCEPTABLE_SCORE = 0.80
MAX_SCORE_DROP = 0.10

CRITICAL_METRICS = {
    "safety",
    "groundedness",
    "tool_accuracy",
}


@dataclass
class RegressionFinding:
    case_id: str
    severity: str
    kind: str
    detail: str
    baseline_value: Any
    current_value: Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero requerido: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def index_results(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["case_id"]: item
        for item in report.get("results", [])
    }


def index_metrics(case_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        metric["name"]: metric
        for metric in case_result.get("metrics", [])
    }


def compare_case_presence(
    baseline_cases: dict[str, dict[str, Any]],
    current_cases: dict[str, dict[str, Any]],
) -> list[RegressionFinding]:
    findings: list[RegressionFinding] = []

    for case_id in baseline_cases:
        if case_id not in current_cases:
            findings.append(
                RegressionFinding(
                    case_id=case_id,
                    severity="critical",
                    kind="missing_case",
                    detail="El caso existía en la baseline pero no aparece en el reporte actual.",
                    baseline_value="present",
                    current_value="missing",
                )
            )

    return findings


def compare_case_pass_status(
    case_id: str,
    baseline_case: dict[str, Any],
    current_case: dict[str, Any],
) -> list[RegressionFinding]:
    findings: list[RegressionFinding] = []

    baseline_passed = baseline_case.get("passed")
    current_passed = current_case.get("passed")

    if baseline_passed and not current_passed:
        findings.append(
            RegressionFinding(
                case_id=case_id,
                severity="critical",
                kind="pass_to_fail",
                detail="El caso pasaba en la baseline y ahora falla.",
                baseline_value=baseline_passed,
                current_value=current_passed,
            )
        )

    return findings


def compare_case_score(
    case_id: str,
    baseline_case: dict[str, Any],
    current_case: dict[str, Any],
) -> list[RegressionFinding]:
    findings: list[RegressionFinding] = []

    baseline_score = float(baseline_case.get("final_score", 0.0))
    current_score = float(current_case.get("final_score", 0.0))
    score_drop = baseline_score - current_score

    if current_score < MIN_ACCEPTABLE_SCORE:
        findings.append(
            RegressionFinding(
                case_id=case_id,
                severity="critical",
                kind="score_below_threshold",
                detail=f"El score actual está por debajo del mínimo aceptable {MIN_ACCEPTABLE_SCORE}.",
                baseline_value=baseline_score,
                current_value=current_score,
            )
        )

    elif score_drop > MAX_SCORE_DROP:
        findings.append(
            RegressionFinding(
                case_id=case_id,
                severity="medium",
                kind="score_drop",
                detail=f"El score ha bajado más de {MAX_SCORE_DROP}.",
                baseline_value=baseline_score,
                current_value=current_score,
            )
        )

    return findings


def compare_metrics(
    case_id: str,
    baseline_case: dict[str, Any],
    current_case: dict[str, Any],
) -> list[RegressionFinding]:
    findings: list[RegressionFinding] = []

    baseline_metrics = index_metrics(baseline_case)
    current_metrics = index_metrics(current_case)

    for metric_name, baseline_metric in baseline_metrics.items():
        if metric_name not in current_metrics:
            findings.append(
                RegressionFinding(
                    case_id=case_id,
                    severity="medium",
                    kind="missing_metric",
                    detail=f"La métrica {metric_name} existía en la baseline y no aparece ahora.",
                    baseline_value="present",
                    current_value="missing",
                )
            )
            continue

        current_metric = current_metrics[metric_name]

        baseline_passed = baseline_metric.get("passed")
        current_passed = current_metric.get("passed")

        baseline_score = float(baseline_metric.get("score", 0.0))
        current_score = float(current_metric.get("score", 0.0))

        if metric_name in CRITICAL_METRICS and baseline_passed and not current_passed:
            findings.append(
                RegressionFinding(
                    case_id=case_id,
                    severity="critical",
                    kind="critical_metric_regression",
                    detail=f"La métrica crítica {metric_name} pasaba y ahora falla.",
                    baseline_value=baseline_metric,
                    current_value=current_metric,
                )
            )

        elif baseline_score - current_score > MAX_SCORE_DROP:
            findings.append(
                RegressionFinding(
                    case_id=case_id,
                    severity="medium",
                    kind="metric_score_drop",
                    detail=f"La métrica {metric_name} ha bajado más de {MAX_SCORE_DROP}.",
                    baseline_value=baseline_score,
                    current_value=current_score,
                )
            )

    return findings


def compare_reports(
    baseline_report: dict[str, Any],
    current_report: dict[str, Any],
) -> list[RegressionFinding]:
    findings: list[RegressionFinding] = []

    baseline_cases = index_results(baseline_report)
    current_cases = index_results(current_report)

    findings.extend(compare_case_presence(baseline_cases, current_cases))

    for case_id, baseline_case in baseline_cases.items():
        current_case = current_cases.get(case_id)

        if not current_case:
            continue

        findings.extend(compare_case_pass_status(case_id, baseline_case, current_case))
        findings.extend(compare_case_score(case_id, baseline_case, current_case))
        findings.extend(compare_metrics(case_id, baseline_case, current_case))

    return findings


def main() -> None:
    baseline_report = load_json(BASELINE_PATH)
    current_report = load_json(CURRENT_REPORT_PATH)

    findings = compare_reports(baseline_report, current_report)

    critical_findings = [
        finding for finding in findings
        if finding.severity == "critical"
    ]

    regression_report = {
        "baseline_path": str(BASELINE_PATH),
        "current_report_path": str(CURRENT_REPORT_PATH),
        "total_findings": len(findings),
        "critical_findings": len(critical_findings),
        "has_regression": bool(critical_findings),
        "findings": [asdict(finding) for finding in findings],
    }

    REGRESSION_REPORT_PATH.write_text(
        json.dumps(regression_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("--- REGRESSION CHECK ---")
    print(f"Findings totales: {len(findings)}")
    print(f"Findings críticos: {len(critical_findings)}")
    print(f"Reporte: {REGRESSION_REPORT_PATH}")

    if not findings:
        print("Sin regresiones detectadas.")

    for finding in findings:
        print()
        print(f"[{finding.severity.upper()}] {finding.case_id} | {finding.kind}")
        print(f"  {finding.detail}")
        print(f"  Baseline: {finding.baseline_value}")
        print(f"  Actual:   {finding.current_value}")

    if critical_findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()