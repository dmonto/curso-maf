from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from src.contracts.support_contracts import (
    IncidentClassificationV1,
    IncidentReportedEventV1,
    ReportIncidentRequestV1,
    ReportIncidentResultV1,
)


CONTRACTS: dict[tuple[str, int], type[BaseModel]] = {
    ("support.report_incident.request", 1): ReportIncidentRequestV1,
    ("support.incident.reported", 1): IncidentReportedEventV1,
    ("support.incident.classified", 1): IncidentClassificationV1,
    ("support.report_incident.result", 1): ReportIncidentResultV1,
}


EVENT_TO_CONTRACT: dict[str, tuple[str, int]] = {
    "support.incident.reported.v1": ("support.incident.reported", 1),
    "support.incident.classified.v1": ("support.incident.classified", 1),
}


class ContractValidationError(Exception):
    def __init__(
        self,
        contract_name: str,
        schema_version: int,
        errors: list[dict[str, Any]],
    ) -> None:
        self.contract_name = contract_name
        self.schema_version = schema_version
        self.errors = errors

        super().__init__(
            f"Contract validation failed: {contract_name}.v{schema_version}"
        )


def get_contract_model(contract_name: str, schema_version: int) -> type[BaseModel]:
    key = (contract_name, schema_version)

    if key not in CONTRACTS:
        raise KeyError(f"Contrato no registrado: {contract_name}.v{schema_version}")

    return CONTRACTS[key]


def validate_payload(
    contract_name: str,
    schema_version: int,
    payload: dict[str, Any],
) -> BaseModel:
    model = get_contract_model(contract_name, schema_version)

    try:
        return model.model_validate(payload)
    except ValidationError as error:
        raise ContractValidationError(
            contract_name=contract_name,
            schema_version=schema_version,
            errors=error.errors(),
        ) from error


def validate_event_payload(event_type: str, payload: dict[str, Any]) -> BaseModel:
    if event_type not in EVENT_TO_CONTRACT:
        raise KeyError(f"Evento sin contrato registrado: {event_type}")

    contract_name, schema_version = EVENT_TO_CONTRACT[event_type]

    return validate_payload(
        contract_name=contract_name,
        schema_version=schema_version,
        payload=payload,
    )


def export_json_schema(
    contract_name: str,
    schema_version: int,
    output_dir: Path,
) -> Path:
    model = get_contract_model(contract_name, schema_version)

    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{contract_name}.v{schema_version}.schema.json"

    output_path.write_text(
        json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path