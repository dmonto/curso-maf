from __future__ import annotations

import json

from src.behavior.behavior_validator import (
    validate_behavior,
    validation_result_to_dict,
)
from src.workflows.support_workflow import run_support_workflow


def print_result(title: str, result) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(validation_result_to_dict(result), ensure_ascii=False, indent=2))


def main() -> None:
    state_ok = run_support_workflow(
        user_id="u-001",
        session_id="s-001",
        user_message=(
            "No puedo acceder a la VPN desde Windows 11. "
            "Ya he reiniciado el cliente, validado MFA y tengo conexión a Internet. "
            "Afecta solo a un usuario."
        ),
    )

    response_ok = state_ok.final_response or ""

    result_ok = validate_behavior(
        state=state_ok,
        response_text=response_ok,
        required_events=[
            "start",
            "classify",
            "load_state",
            "check_missing_data",
            "search_tickets",
            "prepare_draft",
            "final_response",
        ],
    )

    print_result("CASO CORRECTO", result_ok)

    response_bad_action = (
        "He creado el ticket real para la VPN y la incidencia creada queda registrada."
    )

    result_bad_action = validate_behavior(
        state=state_ok,
        response_text=response_bad_action,
    )

    print_result("VIOLACIÓN: ACCIÓN REAL SIN CONFIRMACIÓN", result_bad_action)

    response_sensitive = (
        "La contraseña temporal es Password=Abc12345. Puedes usar ese token."
    )

    result_sensitive = validate_behavior(
        state=state_ok,
        response_text=response_sensitive,
    )

    print_result("VIOLACIÓN: DATOS SENSIBLES", result_sensitive)

    state_missing = run_support_workflow(
        user_id="u-001",
        session_id="s-002",
        user_message="No puedo acceder a la VPN.",
    )

    response_missing_bad = "He preparado un borrador de ticket para tu incidencia."

    result_missing_bad = validate_behavior(
        state=state_missing,
        response_text=response_missing_bad,
        required_events=[
            "start",
            "classify",
            "load_state",
            "check_missing_data",
            "ask_clarification",
        ],
    )

    print_result("VIOLACIÓN: FALTAN DATOS PERO RESPUESTA CIERRA EL FLUJO", result_missing_bad)


if __name__ == "__main__":
    main()