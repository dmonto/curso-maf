from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.security.permission_policy import UserAccessContext
from src.vector.azure_ai_search_store import vector_search


EVAL_CASES_PATH = Path("evals/rag_eval_cases.json")


@dataclass(frozen=True)
class RetrievalMetrics:
    case_id: str
    retrieved_sources: list[str]
    expected_sources: list[str]
    forbidden_sources: list[str]
    precision_at_k: float
    recall_at_k: float
    hit_rate: float
    forbidden_hit: bool
    passed: bool


def load_eval_cases() -> list[dict[str, Any]]:
    return json.loads(EVAL_CASES_PATH.read_text(encoding="utf-8"))


def make_user_context(payload: dict[str, Any]) -> UserAccessContext:
    return UserAccessContext(
        user_id=payload["user_id"],
        tenant_id=payload["tenant_id"],
        groups=payload.get("groups", []),
    )


def compute_retrieval_metrics(
    case: dict[str, Any],
    retrieved_sources: list[str],
) -> RetrievalMetrics:
    expected = set(case["expected_sources"])
    forbidden = set(case["forbidden_sources"])
    retrieved = retrieved_sources

    retrieved_set = set(retrieved)

    relevant_retrieved = [source for source in retrieved if source in expected]

    precision_at_k = (
        len(relevant_retrieved) / len(retrieved)
        if retrieved
        else 1.0 if not expected else 0.0
    )

    recall_at_k = (
        len(expected.intersection(retrieved_set)) / len(expected)
        if expected
        else 1.0
    )

    hit_rate = 1.0 if expected.intersection(retrieved_set) else 0.0

    if not expected:
        hit_rate = 1.0 if not retrieved else 0.0

    forbidden_hit = bool(forbidden.intersection(retrieved_set))

    passed = (
        recall_at_k == 1.0
        and not forbidden_hit
        and (precision_at_k >= 0.5 or not expected)
    )

    return RetrievalMetrics(
        case_id=case["case_id"],
        retrieved_sources=retrieved,
        expected_sources=list(expected),
        forbidden_sources=list(forbidden),
        precision_at_k=round(precision_at_k, 3),
        recall_at_k=round(recall_at_k, 3),
        hit_rate=hit_rate,
        forbidden_hit=forbidden_hit,
        passed=passed,
    )


def main() -> None:
    cases = load_eval_cases()
    metrics: list[RetrievalMetrics] = []

    for case in cases:
        user = make_user_context(case["user_context"])

        results = vector_search(
            query=case["question"],
            #user=user,
            #domain=case.get("domain"),
            top_k=3,
            hybrid=True,
        )

        retrieved_sources = []
        for result in results:
            source_id = result["source_id"]
            if source_id not in retrieved_sources:
                retrieved_sources.append(source_id)

        metric = compute_retrieval_metrics(
            case=case,
            retrieved_sources=retrieved_sources,
        )

        metrics.append(metric)

    print("\n--- RESULTADOS DE RECUPERACIÓN ---")

    passed_count = 0

    for metric in metrics:
        if metric.passed:
            passed_count += 1

        print(f"\nCaso: {metric.case_id}")
        print(f"Recuperadas: {metric.retrieved_sources}")
        print(f"Esperadas: {metric.expected_sources}")
        print(f"Prohibidas: {metric.forbidden_sources}")
        print(f"Precision@k: {metric.precision_at_k}")
        print(f"Recall@k: {metric.recall_at_k}")
        print(f"Forbidden hit: {metric.forbidden_hit}")
        print(f"Passed: {metric.passed}")

    total = len(metrics)
    print("\n--- RESUMEN ---")
    print(f"Casos correctos: {passed_count}/{total}")
    print(f"Pass rate: {passed_count / total:.2%}")


if __name__ == "__main__":
    main()