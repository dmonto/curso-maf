import asyncio
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.agents.support_agent_safe import build_support_agent


EVAL_CASES_PATH = Path("eval_cases.jsonl")
REPORTS_DIR = Path("reports")


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass
class CaseResult:
    case_id: str
    description: str
    passed: bool
    score: float
    response: str
    checks: list[CheckResult]


def result_to_text(result: Any) -> str:
    """
    Convierte el resultado devuelto por agent.run(...) a texto.
    La forma exacta puede variar según versión del framework o provider.
    """
    if result is None:
        return ""

    for attr in ("text", "content", "message", "value", "output"):
        value = getattr(result, attr, None)
        if isinstance(value, str):
            return value

    return str(result)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def check_must_include(response: str, expected: list[str]) -> list[CheckResult]:
    response_norm = normalize(response)
    results: list[CheckResult] = []

    for item in expected:
        item_norm = normalize(item)
        passed = item_norm in response_norm
        results.append(
            CheckResult(
                name="must_include",
                passed=passed,
                detail=f"Debe incluir: {item}",
            )
        )

    return results


def check_must_not_include(response: str, forbidden: list[str]) -> list[CheckResult]:
    response_norm = normalize(response)
    results: list[CheckResult] = []

    for item in forbidden:
        item_norm = normalize(item)
        passed = item_norm not in response_norm
        results.append(
            CheckResult(
                name="must_not_include",
                passed=passed,
                detail=f"No debe incluir: {item}",
            )
        )

    return results


def check_must_include_any(response: str, groups: list[list[str]]) -> list[CheckResult]:
    response_norm = normalize(response)
    results: list[CheckResult] = []

    for group in groups:
        passed = any(normalize(option) in response_norm for option in group)
        results.append(
            CheckResult(
                name="must_include_any",
                passed=passed,
                detail=f"Debe incluir al menos una opción de: {group}",
            )
        )

    return results


def evaluate_response(response: str, checks: dict[str, Any]) -> tuple[bool, float, list[CheckResult]]:
    results: list[CheckResult] = []

    if "must_include" in checks:
        results.extend(check_must_include(response, checks["must_include"]))

    if "must_not_include" in checks:
        results.extend(check_must_not_include(response, checks["must_not_include"]))

    if "must_include_any" in checks:
        results.extend(check_must_include_any(response, checks["must_include_any"]))

    if not results:
        return True, 1.0, []

    passed_count = sum(1 for result in results if result.passed)
    score = passed_count / len(results)
    passed = passed_count == len(results)

    return passed, score, results


def load_eval_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero de evaluación: {path}")

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


async def run_case(agent: Any, case: dict[str, Any]) -> CaseResult:
    session = agent.create_session()
    last_response = ""

    for turn in case["turns"]:
        result = await agent.run(turn, session=session)
        last_response = result_to_text(result)

    passed, score, check_results = evaluate_response(
        response=last_response,
        checks=case.get("checks", {}),
    )

    return CaseResult(
        case_id=case["id"],
        description=case.get("description", ""),
        passed=passed,
        score=round(score, 3),
        response=last_response,
        checks=check_results,
    )


async def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)

    cases = load_eval_cases(EVAL_CASES_PATH)
    agent = build_support_agent()

    results: list[CaseResult] = []

    for case in cases:
        result = await run_case(agent, case)
        results.append(result)

        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.case_id} score={result.score}")

        if not result.passed:
            print("  Respuesta:")
            print(f"  {result.response}")
            print("  Checks fallidos:")
            for check in result.checks:
                if not check.passed:
                    print(f"   - {check.detail}")

    total = len(results)
    passed = sum(1 for result in results if result.passed)
    pass_rate = passed / total if total else 0

    report = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "pass_rate": round(pass_rate, 3),
        "results": [
            {
                **asdict(result),
                "checks": [asdict(check) for check in result.checks],
            }
            for result in results
        ],
    }

    report_path = REPORTS_DIR / "response_eval_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("--- RESUMEN ---")
    print(f"Casos: {total}")
    print(f"Correctos: {passed}")
    print(f"Fallidos: {total - passed}")
    print(f"Pass rate: {pass_rate:.1%}")
    print(f"Reporte: {report_path}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())