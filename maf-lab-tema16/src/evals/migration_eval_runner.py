from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.workflows.support_workflow import run_support_workflow


@dataclass
class EvalCheck:
    name: str
    passed: bool
    detail: str


@dataclass
class EvalResult:
    case_id: str
    source_legacy: str
    passed: bool
    score: float
    checks: list[EvalCheck] = field(default_factory=list)
    final_response: str | None = None
    workflow_status: str | None = None
    category: str | None = None
    service: str | None = None


def load_eval_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def contains_all(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return all(term.lower() in lower for term in terms)


def contains_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def add_check(checks: list[EvalCheck], name: str, passed: bool, detail: str) -> None:
    checks.append(
        EvalCheck(
            name=name,
            passed=passed,
            detail=detail,
        )
    )


def evaluate_case(case: dict[str, Any]) -> EvalResult:
    expected = case["expected"]

    state = run_support_workflow(
        user_id="eval-user",
        session_id=case["case_id"],
        user_message=case["user_message"],
    )

    final_response = state.final_response or ""
    checks: list[EvalCheck] = []

    if "category" in expected:
        add_check(
            checks,
            "category",
            state.category == expected["category"],
            f"expected={expected['category']} actual={state.category}",
        )

    if "status" in expected:
        add_check(
            checks,
            "status",
            state.status == expected["status"],
            f"expected={expected['status']} actual={state.status}",
        )

    if "service" in expected:
        add_check(
            checks,
            "service",
            state.service == expected["service"],
            f"expected={expected['service']} actual={state.service}",
        )

    if "operating_system" in expected:
        add_check(
            checks,
            "operating_system",
            state.operating_system == expected["operating_system"],
            f"expected={expected['operating_system']} actual={state.operating_system}",
        )

    if "must_ask_fields" in expected:
        missing_fields = set(state.missing_fields)
        required = set(expected["must_ask_fields"])
        add_check(
            checks,
            "must_ask_fields",
            required.issubset(missing_fields),
            f"required={sorted(required)} actual={sorted(missing_fields)}",
        )

    if expected.get("must_prepare_ticket"):
        add_check(
            checks,
            "must_prepare_ticket",
            state.ticket_draft is not None,
            f"ticket_draft={state.ticket_draft}",
        )

    if expected.get("must_not_prepare_ticket"):
        add_check(
            checks,
            "must_not_prepare_ticket",
            state.ticket_draft is None,
            f"ticket_draft={state.ticket_draft}",
        )

    if expected.get("must_not_create_real_action"):
        real_action_terms = [
            "ticket real creado",
            "incidencia creada correctamente",
            "se ha creado el ticket real",
        ]
        add_check(
            checks,
            "must_not_create_real_action",
            not contains_any(final_response, real_action_terms),
            "La respuesta no debe afirmar que se ejecutó una acción real.",
        )

    if "must_have_steps" in expected:
        actual_steps = set(state.steps_tried)
        required_steps = set(expected["must_have_steps"])
        add_check(
            checks,
            "must_have_steps",
            required_steps.issubset(actual_steps),
            f"required={sorted(required_steps)} actual={sorted(actual_steps)}",
        )

    if "priority" in expected:
        actual_priority = None
        if state.ticket_draft:
            actual_priority = state.ticket_draft.get("priority")

        add_check(
            checks,
            "priority",
            actual_priority == expected["priority"],
            f"expected={expected['priority']} actual={actual_priority}",
        )

    if "must_mention" in expected:
        add_check(
            checks,
            "must_mention",
            contains_all(final_response, expected["must_mention"]),
            f"terms={expected['must_mention']}",
        )

    if "forbidden_terms" in expected:
        add_check(
            checks,
            "forbidden_terms",
            not contains_any(final_response, expected["forbidden_terms"]),
            f"forbidden={expected['forbidden_terms']}",
        )

    passed_count = sum(1 for check in checks if check.passed)
    total_count = len(checks)
    score = passed_count / total_count if total_count else 0.0

    return EvalResult(
        case_id=case["case_id"],
        source_legacy=case["source_legacy"],
        passed=score == 1.0,
        score=round(score, 3),
        checks=checks,
        final_response=final_response,
        workflow_status=state.status,
        category=state.category,
        service=state.service,
    )


def run_eval_suite(cases_path: Path) -> list[EvalResult]:
    cases = load_eval_cases(cases_path)
    return [evaluate_case(case) for case in cases]


def write_eval_report(results: list[EvalResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "summary": {
            "total_cases": len(results),
            "passed_cases": sum(1 for result in results if result.passed),
            "failed_cases": sum(1 for result in results if not result.passed),
            "average_score": round(
                sum(result.score for result in results) / len(results),
                3,
            )
            if results
            else 0,
        },
        "results": [
            {
                **asdict(result),
                "checks": [asdict(check) for check in result.checks],
            }
            for result in results
        ],
    }

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )