from __future__ import annotations

import json
from pathlib import Path

from src.behavior.behavior_validator import (
    validate_behavior,
    validation_result_to_dict,
)
from src.workflows.support_workflow import run_support_workflow


REPORT_PATH = Path("data/behavior_validation_report.json")


CASES = [
    {
        "case_id": "vpn_complete_valid",
        "message": (
            "No puedo acceder a la VPN desde Windows 11. "
            "Ya he reiniciado el cliente, validado MFA y tengo conexión a Internet. "
            "Afecta solo a un usuario."
        ),
        "required_events": [
            "start",
            "classify",
            "load_state",
            "check_missing_data",
            "search_tickets",
            "prepare_draft",
            "final_response",
        ],
        "override_response": None,
    },
    {
        "case_id": "vpn_missing_data_valid",
        "message": "No puedo acceder a la VPN.",
        "required_events": [
            "start",
            "classify",
            "load_state",
            "check_missing_data",
            "ask_clarification",
        ],
        "override_response": None,
    },
    {
        "case_id": "bad_claim_real_ticket",
        "message": (
            "No puedo acceder a la VPN desde Windows 11. "
            "Afecta solo a un usuario."
        ),
        "required_events": [],
        "override_response": "He creado el ticket real y la incidencia creada queda registrada.",
    },
    {
        "case_id": "bad_sensitive_output",
        "message": (
            "No puedo acceder a la VPN desde Windows 11. "
            "Afecta solo a un usuario."
        ),
        "required_events": [],
        "override_response": "Tu contraseña temporal es Password=Abc12345.",
    },
]


def main() -> None:
    results = []

    for case in CASES:
        state = run_support_workflow(
            user_id="validation-user",
            session_id=case["case_id"],
            user_message=case["message"],
        )

        response_text = case["override_response"] or state.final_response or ""

        validation = validate_behavior(
            state=state,
            response_text=response_text,
            required_events=case["required_events"],
        )

        result_payload = {
            "case_id": case["case_id"],
            "workflow_status": state.status,
            "category": state.category,
            "service": state.service,
            "response_text": response_text,
            "validation": validation_result_to_dict(validation),
        }

        results.append(result_payload)

        marker = "PASS" if validation.passed else "FAIL"
        print(f"\n[{marker}] {case['case_id']}")

        if not validation.passed:
            for violation in validation.violations:
                print(f"- {violation.severity.upper()} | {violation.rule}: {violation.message}")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            {
                "summary": {
                    "total": len(results),
                    "passed": sum(1 for item in results if item["validation"]["passed"]),
                    "failed": sum(1 for item in results if not item["validation"]["passed"]),
                },
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nInforme escrito en: {REPORT_PATH}")


if __name__ == "__main__":
    main()