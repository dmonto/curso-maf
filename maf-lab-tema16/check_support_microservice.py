from __future__ import annotations

from src.integrations.support_microservice_client import (
    SupportMicroserviceError,
    build_support_microservice_client,
)


def main() -> None:
    client = build_support_microservice_client()

    try:
        result = client.triage_incident(
            service="erp",
            summary="El ERP no permite emitir facturas desde el módulo financiero.",
            affected_users=35,
            business_impact="Bloqueo de facturación a clientes.",
        )
    except SupportMicroserviceError as error:
        print(f"ERROR: {error}")
        return

    print("\n--- RESULTADO DEL MICROSERVICIO ---")
    print(result)


if __name__ == "__main__":
    main()