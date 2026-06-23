from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.agents.support_agent import build_structured_support_agent
from src.contracts import SupportResponse, parse_support_response


CASES_PATH = Path(__file__).parent / "prompt_cases_support_l1.json"


def load_cases() -> list[dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def assert_contains_all(text: str, expected_terms: list[str]) -> None:
    normalized = text.lower()

    for term in expected_terms:
        assert term.lower() in normalized, f"No aparece el término esperado: {term!r}"


def assert_contains_any(text: str, expected_terms: list[str]) -> None:
    normalized = text.lower()

    assert any(term.lower() in normalized for term in expected_terms), (
        f"No aparece ninguno de los términos esperados: {expected_terms!r}"
    )


def assert_not_contains(text: str, forbidden_terms: list[str]) -> None:
    normalized = text.lower()

    for term in forbidden_terms:
        assert term.lower() not in normalized, f"Aparece un término prohibido: {term!r}"


def assert_case_expectations(parsed: SupportResponse, case: dict[str, Any]) -> None:
    full_text = parsed.model_dump_json().lower() + "\n" + parsed.message.lower()

    if expected := case.get("expected_response_type"):
        assert parsed.response_type == expected

    if expected := case.get("expected_next_action"):
        assert parsed.next_action == expected

    if allowed := case.get("allowed_next_actions"):
        assert parsed.next_action in allowed

    if expected := case.get("expected_service"):
        assert parsed.service == expected

    if expected := case.get("expected_priority"):
        assert parsed.priority == expected

    if case.get("ticket_draft_required"):
        assert parsed.ticket_draft is not None, "Se esperaba ticket_draft, pero es None"

    if terms := case.get("must_include"):
        assert_contains_all(full_text, terms)

    if terms := case.get("must_include_any"):
        assert_contains_any(full_text, terms)

    if terms := case.get("must_not_include"):
        assert_not_contains(full_text, terms)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", load_cases(), ids=lambda c: c["id"])
async def test_support_l1_prompt_cases(case: dict[str, Any]) -> None:
    agent = build_structured_support_agent()

    raw_result = await agent.run(case["input"])

    parsed = parse_support_response(str(raw_result))

    assert_case_expectations(parsed, case)