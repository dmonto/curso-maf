from __future__ import annotations

from src.workflows.support_workflow import (
    run_support_workflow,
    workflow_state_to_json,
)


def main() -> None:
    cases = [
        {
            "name": "VPN con datos suficientes",
            "message": (
                "No puedo acceder a la VPN desde Windows 11. "
                "Ya he reiniciado el cliente, validado MFA y tengo conexión a Internet. "
                "Afecta solo a un usuario."
            ),
        },
        {
            "name": "VPN con datos incompletos",
            "message": "No puedo acceder a la VPN.",
        },
        {
            "name": "ERP con varios usuarios",
            "message": "El ERP no responde y afecta a varios usuarios.",
        },
    ]

    for case in cases:
        print(f"\n=== {case['name']} ===")
        state = run_support_workflow(
            user_id="u-001",
            session_id="s-001",
            user_message=case["message"],
        )

        print("\nRespuesta:")
        print(state.final_response)

        print("\nEstado completo:")
        print(workflow_state_to_json(state))


if __name__ == "__main__":
    main()