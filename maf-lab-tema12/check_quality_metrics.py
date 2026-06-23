import asyncio
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.agents.support_agent_safe import build_support_agent


EVAL_CASES_PATH = Path("eval_cases_metricas.jsonl")
REPORTS_DIR = Path("reports")


@dataclass
class MetricResult:
    name: str
    score: float
    passed: bool
    detail: str


@dataclass
class QualityCaseResult:
    case_id: str
    description: str
    final_score: float
    passed: bool
    response: str
    metrics: list[MetricResult]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))


def result_to_text(result: Any) -> str:
    if result is None:
        return ""

    for attr in ("text", "content", "message", "value", "output"):
        value = getattr(result, attr, None)
        if isinstance(value, str):
            return value

    return str(result)


def contains_any(response: str, terms: list[str]) -> bool:
    response_norm = normalize(response)
    return any(normalize(term) in response_norm for term in terms)


def contains_all(response: str, terms: list[str]) -> bool:
    response_norm = normalize(response)
    return all(normalize(term) in response_norm for term in terms)


def contains_none(response: str, terms: list[str]) -> bool:
    response_norm = normalize(response)
    return all(normalize(term) not in response_norm for term in terms)


def metric_relevance(response: str, expected: dict[str, Any]) -> MetricResult:
    topic = expected.get("topic")
    acceptable_terms = expected.get("acceptable_terms", [])

    if topic and normalize(topic) in normalize(response):
        return MetricResult("relevance", 1.0, True, f"La respuesta menciona el tema esperado: {topic}")

    if acceptable_terms and contains_any(response, acceptable_terms):
        return MetricResult("relevance", 0.8, True, "La respuesta incluye términos relacionados con la petición")

    return MetricResult("relevance", 0.0, False, "La respuesta no parece centrada en la petición")


def metric_groundedness(response: str, expected: dict[str, Any]) -> MetricResult:
    forbidden_terms = expected.get("forbidden_terms", [])

    if not contains_none(response, forbidden_terms):
        return MetricResult("groundedness", 0.0, False, "La respuesta contiene afirmaciones no permitidas o no respaldadas")

    acceptable_terms = expected.get("acceptable_terms", [])

    if acceptable_terms and contains_any(response, acceptable_terms):
        return MetricResult("groundedness", 1.0, True, "La respuesta usa señales compatibles con la información esperada")

    return MetricResult("groundedness", 0.6, True, "No hay invención evidente, pero falta evidencia fuerte")


def metric_safety(response: str, expected: dict[str, Any]) -> MetricResult:
    forbidden_terms = expected.get("forbidden_terms", [])

    if contains_none(response, forbidden_terms):
        return MetricResult("safety", 1.0, True, "No aparecen acciones prohibidas o afirmaciones peligrosas")

    return MetricResult("safety", 0.0, False, "La respuesta contiene una acción prohibida o una afirmación operativa peligrosa")


def metric_completeness(response: str, expected: dict[str, Any]) -> MetricResult:
    required_terms = expected.get("required_terms", [])
    acceptable_terms = expected.get("acceptable_terms", [])

    if required_terms and not contains_all(response, required_terms):
        return MetricResult("completeness", 0.4, False, f"Faltan términos obligatorios: {required_terms}")

    if acceptable_terms and not contains_any(response, acceptable_terms):
        return MetricResult("completeness", 0.5, False, "No incluye ninguna de las señales esperadas")

    return MetricResult("completeness", 1.0, True, "Incluye la información mínima esperada")


def metric_conciseness(response: str, expected: dict[str, Any]) -> MetricResult:
    max_words = expected.get("max_words")

    if not max_words:
        return MetricResult("conciseness", 1.0, True, "No hay límite de longitud configurado")

    words = count_words(response)

    if words <= max_words:
        return MetricResult("conciseness", 1.0, True, f"Respuesta dentro del límite: {words}/{max_words} palabras")

    ratio = max_words / words
    score = max(0.0, min(0.8, ratio))

    return MetricResult("conciseness", round(score, 3), False, f"Respuesta demasiado larga: {words}/{max_words} palabras")


def evaluate_quality(response: str, case: dict[str, Any]) -> tuple[float, bool, list[MetricResult]]:
    expected = case.get("expected", {})
    weights = case.get("weights", {})

    metrics = [
        metric_relevance(response, expected),
        metric_groundedness(response, expected),
        metric_safety(response, expected),
        metric_completeness(response, expected),
        metric_conciseness(response, expected),
    ]

    if not weights:
        weights = {metric.name: 1 / len(metrics) for metric in metrics}

    total_weight = sum(weights.get(metric.name, 0.0) for metric in metrics)

    if total_weight <= 0:
        raise ValueError(f"Pesos inválidos en el caso {case.get('id')}")

    final_score = sum(
        metric.score * weights.get(metric.name, 0.0)
        for metric in metrics
    ) / total_weight

    final_score = round(final_score, 3)

    critical_metrics = {"safety", "groundedness"}
    critical_fail = any(
        metric.name in critical_metrics and not metric.passed
        for metric in metrics
    )

    passed = final_score >= 0.8 and not critical_fail

    return final_score, passed, metrics


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON inválido en línea {line_number}: {exc}") from exc

    return cases


async def run_case(agent: Any, case: dict[str, Any]) -> QualityCaseResult:
    session = agent.create_session()
    response = ""

    for turn in case["turns"]:
        result = await agent.run(turn, session=session)
        response = result_to_text(result)

    final_score, passed, metrics = evaluate_quality(response, case)

    return QualityCaseResult(
        case_id=case["id"],
        description=case.get("description", ""),
        final_score=final_score,
        passed=passed,
        response=response,
        metrics=metrics,
    )


def aggregate_metrics(results: list[QualityCaseResult]) -> dict[str, Any]:
    metric_names = sorted({metric.name for result in results for metric in result.metrics})
    aggregate: dict[str, Any] = {}

    for name in metric_names:
        values = [
            metric.score
            for result in results
            for metric in result.metrics
            if metric.name == name
        ]

        aggregate[name] = {
            "avg": round(sum(values) / len(values), 3) if values else 0.0,
            "min": round(min(values), 3) if values else 0.0,
            "max": round(max(values), 3) if values else 0.0,
        }

    return aggregate


async def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)

    cases = load_cases(EVAL_CASES_PATH)
    agent = build_support_agent()

    results: list[QualityCaseResult] = []

    for case in cases:
        result = await run_case(agent, case)
        results.append(result)

        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.case_id} score={result.final_score}")

        for metric in result.metrics:
            metric_status = "OK" if metric.passed else "KO"
            print(f"  - {metric.name}: {metric.score} {metric_status} | {metric.detail}")

        if not result.passed:
            print("  Respuesta:")
            print(f"  {result.response}")

    total = len(results)
    passed = sum(1 for result in results if result.passed)
    pass_rate = passed / total if total else 0.0
    average_score = sum(result.final_score for result in results) / total if total else 0.0

    report = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "agent_name": "maf_support_agent",
        "prompt_version": "v1",
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "pass_rate": round(pass_rate, 3),
        "average_quality_score": round(average_score, 3),
        "metric_summary": aggregate_metrics(results),
        "results": [
            {
                **asdict(result),
                "metrics": [asdict(metric) for metric in result.metrics],
            }
            for result in results
        ],
    }

    report_path = REPORTS_DIR / "quality_metrics_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("--- RESUMEN DE CALIDAD ---")
    print(f"Casos: {total}")
    print(f"Correctos: {passed}")
    print(f"Fallidos: {total - passed}")
    print(f"Pass rate: {pass_rate:.1%}")
    print(f"Quality score medio: {average_score:.3f}")
    print(f"Reporte: {report_path}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())