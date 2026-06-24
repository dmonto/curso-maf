from src.integrations.m365_automation_client import M365AutomationClient


def main() -> None:
    client = M365AutomationClient.from_env()

    print("\n--- BORRADOR DE CORREO ---")
    draft_result = client.create_mail_draft(
        to="ana.garcia@empresa.local",
        subject="Seguimiento de incidencia VPN",
        body=(
            "Hola Ana,\n\n"
            "Te escribimos para confirmar si la incidencia de VPN continúa "
            "después de las pruebas realizadas.\n\n"
            "Un saludo."
        ),
    )
    print(draft_result.model_dump())

    print("\n--- EVENTO DE CALENDARIO ---")
    event_result = client.create_calendar_event(
        subject="Seguimiento incidencia VPN",
        start_datetime="2026-06-18T10:00:00",
        end_datetime="2026-06-18T10:30:00",
        attendees="ana.garcia@empresa.local",
        body="Revisar estado de la incidencia VPN y próximos pasos.",
    )
    print(event_result.model_dump())


if __name__ == "__main__":
    main()