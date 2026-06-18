from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


ResponseType = Literal["answer", "clarification", "draft", "refusal", "error"]
ServiceName = Literal["vpn", "correo", "teams", "erp", "unknown"]
Priority = Literal["p1", "p2", "p3", "p4", "unknown"]
NextAction = Literal[
    "ask_user",
    "prepare_draft",
    "review_draft",
    "escalate",
    "close",
    "none",
]


class KnownFact(BaseModel):
    name: str = Field(description="Nombre del dato conocido.")
    value: str = Field(description="Valor del dato.")
    source: Literal["user", "tool", "policy", "inferred"] = Field(
        description="Origen del dato."
    )


class TicketDraft(BaseModel):
    service: Literal["vpn", "correo", "teams", "erp"]
    priority: Literal["p1", "p2", "p3", "p4"]
    summary: str = Field(min_length=10, max_length=200)
    impact: str = Field(min_length=15, max_length=500)
    users_affected: int = Field(ge=1, le=10000)
    requires_human_validation: bool = False


class SupportResponse(BaseModel):
    response_type: ResponseType
    message: str = Field(min_length=1, max_length=1200)
    service: ServiceName = "unknown"
    priority: Priority = "unknown"
    known_facts: list[KnownFact] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    next_action: NextAction = "none"
    requires_human_validation: bool = False
    ticket_draft: TicketDraft | None = None


def extract_json_object(raw_text: str) -> str:
    """
    Extrae un objeto JSON de una respuesta del modelo.

    Acepta JSON limpio o JSON dentro de un bloque ```json.
    Si no encuentra un objeto, lanza ValueError.
    """
    text = raw_text.strip()

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("No se ha encontrado un objeto JSON en la respuesta.")

    return text[start : end + 1]


def parse_support_response(raw_text: str) -> SupportResponse:
    json_text = extract_json_object(raw_text)

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido: {exc}") from exc

    try:
        return SupportResponse.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"La respuesta no cumple el contrato: {exc}") from exc