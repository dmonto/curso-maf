from src.tools.support_logic import (
    IncidentInput,
    build_ticket_draft_payload,
    calculate_sla,
    classify_incident_risk,
    normalize_service_name,
    validate_incident_input,
)


def main() -> None:
    print("\n--- NORMALIZACIÓN ---")
    for value in ["VPN", "email", "Microsoft Teams", "sistema desconocido"]:
        print(value, "=>", normalize_service_name(value))

    print("\n--- SLA ---")
    for priority in ["p1", "p2", "p3", "p4"]:
        print(priority, "=>", calculate_sla(priority))  # type: ignore[arg-type]

    print("\n--- INCIDENTE VÁLIDO ---")
    incident = IncidentInput(
        service="erp",
        priority="p2",
        summary="ERP con errores de autenticación",
        impact="El equipo financiero no puede validar pedidos pendientes.",
        users_affected=15,
    )

    print("Errores:", validate_incident_input(incident))
    print("Riesgo:", classify_incident_risk(incident))
    print("Borrador:", build_ticket_draft_payload(incident))

    print("\n--- INCIDENTE P1 INVÁLIDO ---")
    invalid_p1 = IncidentInput(
        service="vpn",
        priority="p1",
        summary="VPN lenta",
        impact="Va mal.",
        users_affected=2,
    )

    print("Errores:", validate_incident_input(invalid_p1))
    print("Riesgo:", classify_incident_risk(invalid_p1))
    print("Borrador:", build_ticket_draft_payload(invalid_p1))


if __name__ == "__main__":
    main()