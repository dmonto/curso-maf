from __future__ import annotations

import json
from pathlib import Path

from src.contracts.registry import (
    ContractValidationError,
    export_json_schema,
    validate_payload,
)


def print_json(title: str, payload: dict) -> None:
    print(f"\n--- {title} ---")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    valid_request = {
        "service": "erp",
        "summary": "El ERP no permite emitir facturas desde el módulo financiero.",
        "affected_users": 35,
        "business_impact": "Bloqueo de facturación a clientes.",
    }

    invalid_request = {
        "service": "erp",
        "summary": "ERP roto",
        "affected_users": 0,
        "business_impact": "",
        "raw_prompt": "Tenemos un problema, haz lo que puedas.",
    }

    validated = validate_payload(
        contract_name="support.report_incident.request",
        schema_version=1,
        payload=valid_request,
    )

    print_json("CONTRATO VÁLIDO", validated.model_dump())

    try:
        validate_payload(
            contract_name="support.report_incident.request",
            schema_version=1,
            payload=invalid_request,
        )
    except ContractValidationError as error:
        print(f"\n--- CONTRATO INVÁLIDO ---")
        print(f"Contrato: {error.contract_name}.v{error.schema_version}")
        print(json.dumps(error.errors, ensure_ascii=False, indent=2))

    output_dir = Path("docs/contracts")

    exported = export_json_schema(
        contract_name="support.report_incident.request",
        schema_version=1,
        output_dir=output_dir,
    )

    print(f"\nSchema exportado en: {exported}")


if __name__ == "__main__":
    main()