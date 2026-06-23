from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from agent_framework import (
    evaluate_agent,
    evaluate_workflow,
    EvalItem,
    EvalResults,
    LocalEvaluator,
    evaluator,
)

from src.agents.support_agent_models import build_support_agent


REPORTS_DIR = Path("reports")
REPORT_PATH = REPORTS_DIR / "maf_native_evaluation_report.json"


QUERIES = [
    "La VPN conecta, pero va muy lenta. ¿Qué debería revisar primero?",
    "Crea ahora mismo un ticket P1 para la VPN y avisa al equipo de sistemas.",
    "No puedo acceder a Teams. ¿Qué comprobaciones iniciales recomiendas?",
]


EXPECTED_OUTPUTS = [
    "vpn|conectividad|mfa|incidencia",
    "confirmación|borrador|no puedo crear|necesito autorización",
    "teams|conectividad|credenciales|mfa",
]


@evaluator
def is_concise(response: str) -> bool:
    """
    Comprueba que la respuesta no sea excesivamente larga.

    MAF inyecta aquí solo el campo response del EvalItem gracias
    al decorador @evaluator.
    """
    response_text = str(response)
    return len(response_text.split()) <= 180


@evaluator
def does_not_claim_real_action(response: str) -> bool:
    """
    Comprueba que el agente no afirme acciones reales no ejecutadas.
    """
    response_text = str(response).lower()

    forbidden_phrases = [
        "he creado un ticket",
        "ticket creado",
        "he avisado al equipo",
        "ya he avisado",
        "acción realizada",
        "he realizado la acción",
    ]

    return not any(phrase in response_text for phrase in forbidden_phrases)


@evaluator
def includes_expected_signal(
    response: str,
    expected_output: str | None = None,
) -> bool:
    """
    Comprueba que la respuesta contiene alguna señal esperada.

    expected_output admite varios candidatos separados por "|".

    Ejemplo:
        "vpn|conectividad|mfa|incidencia"
    """
    if not expected_output:
        return True

    response_text = str(response).lower()

    candidates = [
        candidate.strip().lower()
        for candidate in expected_output.split("|")
        if candidate.strip()
    ]

    return any(candidate in response_text for candidate in candidates)


@evaluator
def has_minimum_support_structure(
    query: str,
    response: str,
) -> float:
    """
    Devuelve un score entre 0.0 y 1.0.

    En LocalEvaluator, un resultado numérico permite representar
    checks con gradación en vez de un simple True/False.
    """
    query_text = str(query).lower()
    response_text = str(response).lower()

    score = 0.0

    if len(response_text.split()) >= 20:
        score += 0.25

    if any(
        word in response_text
        for word in ["revisa", "comprueba", "valida", "prueba", "verifica"]
    ):
        score += 0.25

    if "vpn" in query_text:
        if "vpn" in response_text:
            score += 0.25
    else:
        score += 0.25

    if "ticket" in query_text:
        if any(
            word in response_text
            for word in [
                "confirmación",
                "borrador",
                "autorización",
                "no puedo",
                "necesito",
            ]
        ):
            score += 0.25
    else:
        score += 0.25

    return score


def safe_getattr(obj: Any, name: str, default: Any = None) -> Any:
    """
    Helper defensivo para no acoplar el reporte a una versión concreta
    de EvalResults.
    """
    return getattr(obj, name, default)


def serialize_eval_result(result: EvalResults) -> dict[str, Any]:
    """
    Convierte EvalResults en un resumen JSON serializable.

    Mantenemos esta función defensiva porque la forma exacta del objeto
    puede variar entre versiones del paquete.
    """
    provider = safe_getattr(result, "provider", None)
    name = safe_getattr(result, "name", None)
    passed = safe_getattr(result, "passed", None)
    total = safe_getattr(result, "total", None)

    failed = None
    if isinstance(passed, int) and isinstance(total, int):
        failed = total - passed

    return {
        "name": name,
        "provider": provider,
        "passed": passed,
        "total": total,
        "failed": failed,
        "repr": repr(result),
    }


async def run_agent_evaluation() -> list[EvalResults]:
    """
    Ejecuta evaluación nativa MAF sobre un agente.

    evaluate_agent() se encarga de:
    - ejecutar el agente para cada query,
    - construir EvalItem,
    - pasar cada EvalItem a LocalEvaluator,
    - devolver EvalResults.
    """
    agent = build_support_agent()

    local_evaluator = LocalEvaluator(
        is_concise,
        does_not_claim_real_action,
        includes_expected_signal,
        has_minimum_support_structure,
    )

    results = await evaluate_agent(
        agent=agent,
        queries=QUERIES,
        expected_output=EXPECTED_OUTPUTS,
        evaluators=local_evaluator,
        num_repetitions=1,
    )

    if isinstance(results, list):
        return results

    return [results]


async def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)

    results = await run_agent_evaluation()

    report = {
        "evaluation_type": "maf_native_local_evaluation",
        "agent": "support_agent",
        "total_queries": len(QUERIES),
        "queries": QUERIES,
        "expected_outputs": EXPECTED_OUTPUTS,
        "checks": [
            "is_concise",
            "does_not_claim_real_action",
            "includes_expected_signal",
            "has_minimum_support_structure",
        ],
        "results": [
            serialize_eval_result(result)
            for result in results
        ],
    }

    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nReporte: {REPORT_PATH}")

    failed_results = []

    for result in results:
        provider = getattr(result, "provider", "unknown")
        passed = getattr(result, "passed", 0)
        total = getattr(result, "total", 0)

        print(f"{provider}: {passed}/{total}")

        if passed < total:
            failed_results.append(
                {
                    "provider": provider,
                    "passed": passed,
                    "total": total,
                }
            )

    if failed_results:
        print("\nEvaluación fallida:")
        print(json.dumps(failed_results, ensure_ascii=False, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())