import json

from src.agents.multiagent.shared_state import STATE_STORE, state_to_json


def main() -> None:
    state = STATE_STORE.create_case(
        {
            "service": "ERP",
            "symptom": "acceso denegado",
            "user_area": "Finanzas",
            "location": "casa",
        }
    )

    print("\n--- ESTADO INICIAL ---")
    print(state_to_json(state))

    updated = STATE_STORE.update_case(
        case_id=state.case_id,
        role="identity_specialist",
        expected_version=state.version,
        changes={
            "identity_findings": ["posible falta de grupo ERP"],
            "pending_data": ["grupo esperado", "usuario exacto"],
        },
        reason="Análisis inicial de acceso denegado en ERP",
    )

    print("\n--- ESTADO ACTUALIZADO ---")
    print(state_to_json(updated))

    try:
        STATE_STORE.update_case(
            case_id=state.case_id,
            role="network_specialist",
            expected_version=updated.version,
            changes={
                "priority_suggestion": "p1",
            },
            reason="Intento incorrecto de modificar prioridad desde red",
        )
    except Exception as exc:
        print("\n--- ERROR ESPERADO ---")
        print(type(exc).__name__, str(exc))


if __name__ == "__main__":
    main()