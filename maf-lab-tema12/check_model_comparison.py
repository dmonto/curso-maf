import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from src.agents.support_agent_models import build_support_agent


EVAL_CASES_PATH = Path("eval_cases_metricas.jsonl")
REPORTS_DIR = Path("reports")
REPORT_PATH = REPORTS_DIR / "model_comparison_report.json"

MODEL_ALIASES = [
    "chat_fast",
    "chat_quality",
    "chat_default",
]

MIN_ACCEPTABLE_PASS_RATE = 0.90
MIN_ACCEPTABLE_QUALITY_SCORE = 0.80

CRITICAL_METRICS = {
    "safety",
    "groundedness",
    "tool_accuracy",
}


@dataclass
class MetricResult:
    name: str
    score: float
    passed: bool
    detail: str


@dataclass
class CaseRunResult:
    case_id: str
    description: str
    model_alias: str
    final_score: float
    passed: bool
    latency_ms: int
    word_count: int
    response: str
    metrics: list[MetricResult]


@dataclass
class ModelSummary:
    model_alias: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    average_quality_score: float
    average_latency_ms: int
    average_word_count: float
    critical_failures: int


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
        return MetricResult("relevance", 1.0, True, f"Menciona el tema esperado: {topic}")

    if acceptable_terms and contains_any(response, acceptable_terms):
        return MetricResult("relevance", 0.8, True, "Incluye términos relacionados con la petición")

    return MetricResult("relevance", 0.0, False, "No parece centrada en la petición")


def metric_groundedness(response: str, expected: dict[str, Any]) -> MetricResult:
    forbidden_terms = expected.get("forbidden_terms", [])

    if not contains_none(response, forbidden_terms):
        return MetricResult("groundedness", 0.0, False, "Contiene afirmaciones no permitidas o no respaldadas")

    acceptable_terms = expected.get("acceptable_terms", [])

    if acceptable_terms and contains_any(response, acceptable_terms):
        return MetricResult("groundedness", 1.0, True, "Usa señales compatibles con la información esperada")

    return MetricResult("groundedness", 0.6, True, "No hay invención evidente, pero falta evidencia fuerte")


def metric_safety(response: str, expected: dict[str, Any]) -> MetricResult:
    forbidden_terms = expected.get("forbidden_terms", [])

    if contains_none(response, forbidden_terms):
        return MetricResult("safety", 1.0, True, "No aparecen acciones prohibidas")

    return MetricResult("safety", 0.0, False, "Contiene una acción prohibida o peligrosa")


def metric_completeness(response: str, expected: dict[str, Any]) -> MetricResult:
    required_terms = expected.get("required_terms", [])
    acceptable_terms = expected.get("acceptable_terms", [])

    if required_terms and not contains_all(response, required_terms):
        return MetricResult("completeness", 0.4, False, f"Faltan términos obligatorios: {required_terms}")

    if acceptable_terms and not contains_any(response, acceptable_terms):
        return MetricResult("completeness", 0.5, False, "No incluye señales esperadas")

    return MetricResult("completeness", 1.0, True, "Incluye información mínima esperada")


def metric_conciseness(response: str, expected: dict[str, Any]) -> MetricResult:
    max_words = expected.get("max_words")

    if not max_words:
        return MetricResult("conciseness", 1.0, True, "Sin límite configurado")

    words = count_words(response)

    if words <= max_words:
        return MetricResult("conciseness", 1.0, True, f"Dentro del límite: {words}/{max_words}")

    ratio = max_words / words
    score = max(0.0, min(0.8, ratio))

    return MetricResult("conciseness", round(score, 3), False, f"Demasiado larga: {words}/{max_words}")


def metric_tool_accuracy(response: str, expected: dict[str, Any]) -> MetricResult:
    signals = expected.get("expected_tool_signals", [])

    if not signals:
        return MetricResult("tool_accuracy", 1.0, True, "No hay señales de tool esperadas")

    if contains_any(response, signals):
        return MetricResult("tool_accuracy", 1.0, True, "Contiene señales compatibles con la tool esperada")

    return MetricResult("tool_accuracy", 0.3, False, "No muestra señales de haber usado la capacidad esperada")


def evaluate_quality(response: str, case: dict[str, Any]) -> tuple[float, bool, list[MetricResult]]:
    expected = case.get("expected", {})
    weights = case.get("weights", {})

    metrics = [
        metric_relevance(response, expected),
        metric_groundedness(response, expected),
        metric_safety(response, expected),
        metric_completeness(response, expected),
        metric_conciseness(response, expected),
        metric_tool_accuracy(response, expected),
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

    critical_fail = any(
        metric.name in CRITICAL_METRICS and not metric.passed
        for metric in metrics
    )

    passed = final_score >= MIN_ACCEPTABLE_QUALITY_SCORE and not critical_fail

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


async def run_case_for_model(model_alias: str, case: dict[str, Any]) -> CaseRunResult:
    agent = build_support_agent(model_alias=model_alias)
    session = agent.create_session()

    response = ""
    start = time.perf_counter()

    for turn in case["turns"]:
        result = await agent.run(turn, session=session)
        response = result_to_text(result)

    latency_ms = int((time.perf_counter() - start) * 1000)
    final_score, passed, metrics = evaluate_quality(response, case)

    return CaseRunResult(
        case_id=case["id"],
        description=case.get("description", ""),
        model_alias=model_alias,
        final_score=final_score,
        passed=passed,
        latency_ms=latency_ms,
        word_count=count_words(response),
        response=response,
        metrics=metrics,
    )


def summarize_model(model_alias: str, results: list[CaseRunResult]) -> ModelSummary:
    model_results = [
        result for result in results
        if result.model_alias == model_alias
    ]

    total = len(model_results)
    passed = sum(1 for result in model_results if result.passed)

    critical_failures = 0
    for result in model_results:
        for metric in result.metrics:
            if metric.name in CRITICAL_METRICS and not metric.passed:
                critical_failures += 1

    return ModelSummary(
        model_alias=model_alias,
        total_cases=total,
        passed_cases=passed,
        failed_cases=total - passed,
        pass_rate=round(passed / total, 3) if total else 0.0,
        average_quality_score=round(mean(result.final_score for result in model_results), 3) if model_results else 0.0,
        average_latency_ms=int(mean(result.latency_ms for result in model_results)) if model_results else 0,
        average_word_count=round(mean(result.word_count for result in model_results), 1) if model_results else 0.0,
        critical_failures=critical_failures,
    )


def rank_models(summaries: list[ModelSummary]) -> list[dict[str, Any]]:
    ranked = sorted(
        summaries,
        key=lambda item: (
            item.critical_failures == 0,
            item.pass_rate,
            item.average_quality_score,
            -item.average_latency_ms,
        ),
        reverse=True,
    )

    return [
        {
            "rank": index + 1,
            **asdict(summary),
        }
        for index, summary in enumerate(ranked)
    ]


def select_recommended_model(summaries: list[ModelSummary]) -> str | None:
    eligible = [
        summary for summary in summaries
        if summary.critical_failures == 0
        and summary.pass_rate >= MIN_ACCEPTABLE_PASS_RATE
        and summary.average_quality_score >= MIN_ACCEPTABLE_QUALITY_SCORE
    ]

    if not eligible:
        return None

    eligible.sort(
        key=lambda item: (
            item.average_quality_score,
            item.pass_rate,
            -item.average_latency_ms,
        ),
        reverse=True,
    )

    return eligible[0].model_alias


async def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)

    cases = load_cases(EVAL_CASES_PATH)

    all_results: list[CaseRunResult] = []

    for model_alias in MODEL_ALIASES:
        print()
        print(f"=== Evaluando modelo: {model_alias} ===")

        for case in cases:
            result = await run_case_for_model(model_alias, case)
            all_results.append(result)

            status = "PASS" if result.passed else "FAIL"
            print(
                f"[{status}] {case['id']} "
                f"score={result.final_score} "
                f"latency={result.latency_ms}ms "
                f"words={result.word_count}"
            )

    summaries = [
        summarize_model(model_alias, all_results)
        for model_alias in MODEL_ALIASES
    ]

    ranking = rank_models(summaries)
    recommended_model = select_recommended_model(summaries)

    report = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_aliases": MODEL_ALIASES,
        "total_cases": len(cases),
        "min_acceptable_pass_rate": MIN_ACCEPTABLE_PASS_RATE,
        "min_acceptable_quality_score": MIN_ACCEPTABLE_QUALITY_SCORE,
        "recommended_model": recommended_model,
        "ranking": ranking,
        "summaries": [asdict(summary) for summary in summaries],
        "results": [
            {
                **asdict(result),
                "metrics": [asdict(metric) for metric in result.metrics],
            }
            for result in all_results
        ],
    }

    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("--- COMPARATIVA DE MODELOS ---")

    for item in ranking:
        print(
            f"{item['rank']}. {item['model_alias']} | "
            f"pass_rate={item['pass_rate']} | "
            f"quality={item['average_quality_score']} | "
            f"latency={item['average_latency_ms']}ms | "
            f"critical_failures={item['critical_failures']}"
        )

    print()
    print(f"Modelo recomendado: {recommended_model or 'ninguno'}")
    print(f"Reporte: {REPORT_PATH}")

    if recommended_model is None:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())