from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field


GENERATED_DOCS_DIR = Path("generated_docs")
TEMPLATE_PATH = Path("src/templates/incident_report.md")
AUDIT_PATH = Path("logs/document_automation_audit.jsonl")

GENERATED_DOCS_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)


Priority = Literal["P1", "P2", "P3", "P4"]
Impact = Literal["solo_usuario", "varios_usuarios", "area_completa", "desconocido"]


@dataclass(frozen=True)
class FieldValidationResult:
    is_complete: bool
    missing_fields: list[str]
    recommendation: str


@dataclass(frozen=True)
class IncidentReportPayload:
    service: str
    impact: str
    priority: str
    current_status: str
    symptoms: str
    actions_taken: str
    timeline: str
    probable_cause: str
    pending_items: str
    recommendation: str


def _audit(event: dict) -> None:
    payload = {
        "event_id": str(uuid.uuid4()),
        "ts": time.time(),
        **event,
    }

    with AUDIT_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9áéíóúüñ]+", "-", value)
    value = value.strip("-")
    return value[:60] or "documento"


def _render_template(template: str, values: dict[str, str]) -> str:
    output = template

    for key, value in values.items():
        output = output.replace("{{ " + key + " }}", value)

    return output


@tool(
    name="validate_incident_report_fields",
    description=(
        "Valida si hay información mínima suficiente para generar un borrador "
        "de informe de incidencia."
    ),
)
def validate_incident_report_fields(
    service: Annotated[str, Field(description="Servicio afectado por la incidencia.")],
    impact: Annotated[Impact, Field(description="Impacto de la incidencia.")],
    symptoms: Annotated[str, Field(description="Síntomas reportados por el usuario.")],
    current_status: Annotated[str, Field(description="Estado actual de la incidencia.")],
) -> str:
    missing_fields: list[str] = []

    if not service or service.lower() == "desconocido":
        missing_fields.append("service")

    if impact == "desconocido":
        missing_fields.append("impact")

    if not symptoms or len(symptoms.strip()) < 15:
        missing_fields.append("symptoms")

    if not current_status or len(current_status.strip()) < 5:
        missing_fields.append("current_status")

    is_complete = len(missing_fields) == 0

    result = FieldValidationResult(
        is_complete=is_complete,
        missing_fields=missing_fields,
        recommendation=(
            "ready_for_draft"
            if is_complete
            else "ask_for_missing_information_before_generating_document"
        ),
    )

    _audit(
        {
            "event_type": "validation.completed",
            "tool_name": "validate_incident_report_fields",
            "is_complete": is_complete,
            "missing_fields": missing_fields,
        }
    )

    return json.dumps(asdict(result), ensure_ascii=False)


@tool(
    name="estimate_document_priority",
    description=(
        "Estima la prioridad documental de una incidencia según impacto y bloqueo de negocio. "
        "Usar antes de generar un informe de incidencia."
    ),
)
def estimate_document_priority(
    impact: Annotated[Impact, Field(description="Impacto de la incidencia.")],
    business_blocker: Annotated[
        bool,
        Field(description="True si la incidencia bloquea una operación crítica de negocio."),
    ],
) -> str:
    if impact == "area_completa" or business_blocker:
        priority: Priority = "P1"
    elif impact == "varios_usuarios":
        priority = "P2"
    elif impact == "solo_usuario":
        priority = "P3"
    else:
        priority = "P4"

    result = {
        "priority": priority,
        "reason": "Prioridad estimada para clasificar el borrador documental.",
    }

    _audit(
        {
            "event_type": "priority.estimated",
            "tool_name": "estimate_document_priority",
            "impact": impact,
            "business_blocker": business_blocker,
            "priority": priority,
        }
    )

    return json.dumps(result, ensure_ascii=False)


@tool(
    name="create_incident_report_draft",
    description=(
        "Genera y guarda un borrador Markdown de informe de incidencia usando "
        "la plantilla corporativa. No publica el documento final."
    ),
)
def create_incident_report_draft(
    service: Annotated[str, Field(description="Servicio afectado.")],
    impact: Annotated[Impact, Field(description="Impacto de la incidencia.")],
    priority: Annotated[Priority, Field(description="Prioridad estimada.")],
    current_status: Annotated[str, Field(description="Estado actual de la incidencia.")],
    symptoms: Annotated[str, Field(description="Síntomas reportados.")],
    actions_taken: Annotated[
        str,
        Field(description="Acciones ya realizadas. Si no constan, indicar 'No informado'."),
    ],
    timeline: Annotated[
        str,
        Field(description="Cronología conocida. Si no consta, indicar 'No informado'."),
    ],
    probable_cause: Annotated[
        str,
        Field(description="Causa probable. Si no se conoce, indicar 'Pendiente de análisis'."),
    ],
    pending_items: Annotated[
        str,
        Field(description="Pendientes o próximos pasos."),
    ],
    recommendation: Annotated[
        str,
        Field(description="Recomendación operativa para el siguiente paso."),
    ],
) -> str:
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"No existe la plantilla: {TEMPLATE_PATH}")

    draft_id = f"doc-{uuid.uuid4().hex[:10]}"

    values = {
        "executive_summary": (
            f"Incidencia en {service} con impacto {impact}. "
            f"Prioridad estimada {priority}. Estado actual: {current_status}."
        ),
        "service": service,
        "impact": impact,
        "priority": priority,
        "current_status": current_status,
        "symptoms": symptoms,
        "actions_taken": actions_taken,
        "timeline": timeline,
        "probable_cause": probable_cause,
        "pending_items": pending_items,
        "recommendation": recommendation,
        "generated_by": "document_automation_agent",
        "draft_id": draft_id,
        "requires_review": "Sí",
    }

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    rendered = _render_template(template, values)

    filename = f"{draft_id}-{_slugify(service)}-incident-report.md"
    output_path = GENERATED_DOCS_DIR / filename
    output_path.write_text(rendered, encoding="utf-8")

    result = {
        "draft_id": draft_id,
        "path": str(output_path),
        "service": service,
        "priority": priority,
        "requires_human_review": True,
        "message": "Borrador documental generado correctamente.",
    }

    _audit(
        {
            "event_type": "document_draft.created",
            "tool_name": "create_incident_report_draft",
            "draft_id": draft_id,
            "path": str(output_path),
            "service": service,
            "priority": priority,
        }
    )

    return json.dumps(result, ensure_ascii=False)