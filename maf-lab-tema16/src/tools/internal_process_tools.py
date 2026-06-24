from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field


AUDIT_PATH = Path("logs/internal_process_automation_audit.jsonl")
PROCESS_STORE_PATH = Path("data/internal_process_requests.jsonl")

AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
PROCESS_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)


ProcessType = Literal[
    "software_purchase",
    "access_request",
    "supplier_onboarding",
    "document_review",
    "unknown",
]

Priority = Literal["low", "medium", "high", "critical"]
ProcessStatus = Literal[
    "draft",
    "ready_for_review",
    "approval_required",
    "blocked",
]


@dataclass(frozen=True)
class FieldValidation:
    is_complete: bool
    missing_fields: list[str]
    recommendation: str


@dataclass(frozen=True)
class BusinessRuleDecision:
    approval_required: bool
    security_review_required: bool
    finance_review_required: bool
    priority: str
    reasons: list[str]


@dataclass(frozen=True)
class ProcessRecord:
    process_id: str
    process_type: str
    status: str
    requester_area: str
    title: str
    amount_eur: float
    approval_required: bool
    security_review_required: bool
    next_step: str


def _audit(event: dict) -> None:
    payload = {
        "event_id": str(uuid.uuid4()),
        "ts": time.time(),
        **event,
    }

    with AUDIT_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


@tool(
    name="classify_internal_process",
    description=(
        "Clasifica una solicitud interna según el tipo de proceso corporativo. "
        "Usar al inicio cuando el usuario describe una necesidad interna."
    ),
)
def classify_internal_process(
    request_text: Annotated[
        str,
        Field(description="Texto original o resumen de la solicitud interna.", min_length=10),
    ],
) -> str:
    text = request_text.lower()

    if any(term in text for term in ["licencia", "software", "herramienta", "saas", "comprar"]):
        process_type: ProcessType = "software_purchase"
    elif any(term in text for term in ["acceso", "permiso", "rol", "usuario"]):
        process_type = "access_request"
    elif any(term in text for term in ["proveedor", "alta proveedor", "facturación proveedor"]):
        process_type = "supplier_onboarding"
    elif any(term in text for term in ["revisar documento", "procedimiento", "política"]):
        process_type = "document_review"
    else:
        process_type = "unknown"

    result = {
        "process_type": process_type,
        "confidence_note": "Clasificación heurística para laboratorio.",
    }

    _audit(
        {
            "event_type": "process.classified",
            "tool_name": "classify_internal_process",
            "process_type": process_type,
        }
    )

    return json.dumps(result, ensure_ascii=False)


@tool(
    name="validate_software_purchase_fields",
    description=(
        "Valida los campos mínimos para una solicitud interna de compra de software."
    ),
)
def validate_software_purchase_fields(
    tool_name: Annotated[
        str,
        Field(description="Nombre de la herramienta o software solicitado."),
    ],
    requester_area: Annotated[
        str,
        Field(description="Área o departamento solicitante."),
    ],
    amount_eur: Annotated[
        float,
        Field(description="Importe estimado en euros.", ge=0),
    ],
    business_justification: Annotated[
        str,
        Field(description="Justificación de negocio.", min_length=0),
    ],
    budget_owner: Annotated[
        str,
        Field(description="Responsable presupuestario. Usar 'desconocido' si no consta."),
    ],
) -> str:
    missing_fields: list[str] = []

    if not tool_name or tool_name.lower() == "desconocido":
        missing_fields.append("tool_name")

    if not requester_area or requester_area.lower() == "desconocido":
        missing_fields.append("requester_area")

    if amount_eur <= 0:
        missing_fields.append("amount_eur")

    if not business_justification or len(business_justification.strip()) < 15:
        missing_fields.append("business_justification")

    if not budget_owner or budget_owner.lower() == "desconocido":
        missing_fields.append("budget_owner")

    is_complete = len(missing_fields) == 0

    result = FieldValidation(
        is_complete=is_complete,
        missing_fields=missing_fields,
        recommendation=(
            "ready_for_business_rules"
            if is_complete
            else "ask_for_missing_fields"
        ),
    )

    _audit(
        {
            "event_type": "fields.validated",
            "tool_name": "validate_software_purchase_fields",
            "is_complete": is_complete,
            "missing_fields": missing_fields,
        }
    )

    return json.dumps(asdict(result), ensure_ascii=False)


@tool(
    name="evaluate_internal_process_rules",
    description=(
        "Evalúa reglas de negocio para una solicitud de compra de software. "
        "Determina aprobaciones, revisión financiera y revisión de seguridad."
    ),
)
def evaluate_internal_process_rules(
    amount_eur: Annotated[
        float,
        Field(description="Importe estimado en euros.", ge=0),
    ],
    handles_personal_data: Annotated[
        bool,
        Field(description="True si la herramienta tratará datos personales o sensibles."),
    ],
    business_critical: Annotated[
        bool,
        Field(description="True si la solicitud afecta a un proceso crítico de negocio."),
    ],
    urgent: Annotated[
        bool,
        Field(description="True si el solicitante indica urgencia."),
    ],
) -> str:
    reasons: list[str] = []

    approval_required = amount_eur >= 1000
    finance_review_required = amount_eur >= 5000
    security_review_required = handles_personal_data

    if approval_required:
        reasons.append("El importe supera el umbral de aprobación de 1.000 €.")

    if finance_review_required:
        reasons.append("El importe supera el umbral de revisión financiera de 5.000 €.")

    if security_review_required:
        reasons.append("La herramienta puede tratar datos personales o sensibles.")

    if business_critical:
        reasons.append("La solicitud afecta a un proceso crítico de negocio.")

    if urgent:
        priority: Priority = "high"
        reasons.append("La solicitud se ha marcado como urgente.")
    elif business_critical:
        priority = "high"
    elif amount_eur >= 5000:
        priority = "medium"
    else:
        priority = "low"

    result = BusinessRuleDecision(
        approval_required=approval_required,
        security_review_required=security_review_required,
        finance_review_required=finance_review_required,
        priority=priority,
        reasons=reasons or ["No se han detectado reglas especiales."],
    )

    _audit(
        {
            "event_type": "rules.evaluated",
            "tool_name": "evaluate_internal_process_rules",
            "amount_eur": amount_eur,
            "approval_required": approval_required,
            "security_review_required": security_review_required,
            "finance_review_required": finance_review_required,
            "priority": priority,
        }
    )

    return json.dumps(asdict(result), ensure_ascii=False)


@tool(
    name="create_internal_process_record",
    description=(
        "Crea un registro simulado de proceso interno. "
        "No ejecuta compras reales, no envía aprobaciones y no modifica sistemas."
    ),
)
def create_internal_process_record(
    process_type: Annotated[
        ProcessType,
        Field(description="Tipo de proceso interno."),
    ],
    requester_area: Annotated[
        str,
        Field(description="Área solicitante."),
    ],
    title: Annotated[
        str,
        Field(description="Título breve de la solicitud.", min_length=5),
    ],
    amount_eur: Annotated[
        float,
        Field(description="Importe estimado en euros.", ge=0),
    ],
    approval_required: Annotated[
        bool,
        Field(description="True si requiere aprobación del responsable."),
    ],
    security_review_required: Annotated[
        bool,
        Field(description="True si requiere revisión de seguridad."),
    ],
) -> str:
    if approval_required or security_review_required:
        status: ProcessStatus = "approval_required"
        next_step = "Preparar solicitud de aprobación y revisión humana."
    else:
        status = "ready_for_review"
        next_step = "Revisión operativa antes de ejecución real."

    record = ProcessRecord(
        process_id=f"proc-{uuid.uuid4().hex[:10]}",
        process_type=process_type,
        status=status,
        requester_area=requester_area,
        title=title,
        amount_eur=amount_eur,
        approval_required=approval_required,
        security_review_required=security_review_required,
        next_step=next_step,
    )

    with PROCESS_STORE_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    _audit(
        {
            "event_type": "process_record.created",
            "tool_name": "create_internal_process_record",
            "process_id": record.process_id,
            "process_type": process_type,
            "status": status,
            "approval_required": approval_required,
            "security_review_required": security_review_required,
        }
    )

    return json.dumps(asdict(record), ensure_ascii=False)