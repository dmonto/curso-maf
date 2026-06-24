from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from src.agents.support_agent_rag_embed import build_support_agent


EVAL_CASES_PATH = Path("evals/rag_eval_cases.json")


def load_eval_cases() -> list[dict[str, Any]]:
    return json.loads(EVAL_CASES_PATH.read_text(encoding="utf-8"))


def normalize(text: str) -> str:
    return text.lower().strip()


def answer_contains_terms(answer: str, terms: list[str]) -> bool:
    normalized_answer = normalize(answer)

    return all(
        normalize(term) in normalized_answer
        for term in terms
    )


def answer_mentions_forbidden_sources(answer: str, forbidden_sources: list[str]) -> bool:
    normalized_answer = normalize(answer)

    return any(
        normalize(source) in normalized_answer
        for source in forbidden_sources
    )


def answer_mentions_expected_sources(answer: str, expected_sources: list[str]) -> bool:
    if not expected_sources:
        return True

    normalized_answer = normalize(answer)

    return any(
        normalize(source) in normalized_answer
        for source in expected_sources
    )


def answer_abstains(answer: str) -> bool:
    normalized_answer = normalize(answer)

    abstain_markers = [
        "no tengo documentación autorizada",
        "no tengo evidencia suficiente",
        "no dispongo de documentación",
        "no puedo confirmar",
    ]

    return any(marker in normalized_answer for marker in abstain_markers)


async def run_case(agent, case: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""
Contexto autenticado del usuario:
{json.dumps(case["user_context"], ensure_ascii=False)}

Pregunta:
{case["question"]}

Usa recuperación documental con control de permisos si necesitas documentación interna.
"""

    result = await agent.run(prompt)
    answer = str(result)

    contains_expected_terms = answer_contains_terms(
        answer=answer,
        terms=case["expected_answer_contains"],
    )

    mentions_forbidden = answer_mentions_forbidden_sources(
        answer=answer,
        forbidden_sources=case["forbidden_sources"],
    )

    mentions_expected_source = answer_mentions_expected_sources(
        answer=answer,
        expected_sources=case["expected_sources"],
    )

    abstains = answer_abstains(answer)

    abstention_ok = (
        abstains if case["should_abstain"] else not abstains
    )

    passed = (
        contains_expected_terms
        and not mentions_forbidden
        and mentions_expected_source
        and abstention_ok
    )

    return {
        "case_id": case["case_id"],
        "passed": passed,
        "contains_expected_terms": contains_expected_terms,
        "mentions_expected_source": mentions_expected_source,
        "mentions_forbidden": mentions_forbidden,
        "abstains": abstains,
        "should_abstain": case["should_abstain"],
        "answer": answer,
    }


async def main() -> None:
    agent = build_support_agent()
    cases = load_eval_cases()

    results = []

    for case in cases:
        print(f"\nEvaluando caso: {case['case_id']}")
        result = await run_case(agent, case)
        results.append(result)

    print("\n--- RESULTADOS DE RESPUESTA ---")

    passed_count = 0

    for result in results:
        if result["passed"]:
            passed_count += 1

        print(f"\nCaso: {result['case_id']}")
        print(f"Passed: {result['passed']}")
        print(f"Contiene términos esperados: {result['contains_expected_terms']}")
        print(f"Cita fuente esperada: {result['mentions_expected_source']}")
        print(f"Menciona fuente prohibida: {result['mentions_forbidden']}")
        print(f"Abstención: {result['abstains']} | Esperada: {result['should_abstain']}")
        print("\nRespuesta:")
        print(result["answer"][:800])

    total = len(results)

    print("\n--- RESUMEN ---")
    print(f"Casos correctos: {passed_count}/{total}")
    print(f"Pass rate: {passed_count / total:.2%}")


if __name__ == "__main__":
    asyncio.run(main())