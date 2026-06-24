from __future__ import annotations

import json
from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from src.security.sensitive_data import sanitize_text


def _safe_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


@tool(
    name="get_mock_customer_record",
    description=(
        "Devuelve un registro simulado de cliente para practicar sanitización. "
        "Úsala solo en el laboratorio. No consulta sistemas reales."
    ),
)
def get_mock_customer_record(
    customer_id: Annotated[
        Literal["CUST-001", "CUST-002"],
        Field(description="Identificador simulado de cliente del laboratorio."),
    ],
) -> str:
    records = {
        "CUST-001": {
            "customer_id": "CUST-001",
            "name": "Ana García",
            "email": "ana.garcia@contoso.com",
            "phone": "+34 600 123 456",
            "issue": "No puede acceder a la VPN desde Windows 11.",
            "internal_note": "Cliente prioritario. No exponer teléfono si no es necesario.",
        },
        "CUST-002": {
            "customer_id": "CUST-002",
            "name": "Bruno López",
            "email": "bruno.lopez@contoso.com",
            "phone": "+34 611 222 333",
            "issue": "El ERP devuelve error 500.",
            "internal_note": "Revisar contrato antes de escalar.",
        },
    }

    record = records[customer_id]

    # Simulamos que la API devuelve más datos de los que el agente necesita.
    raw_output = _safe_json(record)

    report = sanitize_text(raw_output, block_critical=False)

    return _safe_json(
        {
            "sanitized": True,
            "customer_id": customer_id,
            "record": json.loads(report.sanitized_text),
            "redactions": [
                {
                    "kind": match.kind,
                    "level": match.level.value,
                    "replacement": match.replacement,
                }
                for match in report.matches
            ],
        }
    )