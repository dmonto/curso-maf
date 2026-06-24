
from __future__ import annotations

from typing import Any

from src.external_events.schemas import CanonicalEvent


def normalize_external_event(
    source: str,
    raw_event: dict[str, Any],
) -> CanonicalEvent:
    if source == "monitoring":
        return _normalize_monitoring_event(raw_event)

    if source == "sharepoint":
        return _normalize_sharepoint_event(raw_event)

    raise ValueError(f"Source no soportado: {source}")


def _normalize_monitoring_event(raw_event: dict[str, Any]) -> CanonicalEvent:
    external_id = str(raw_event.get("id", ""))

    if not external_id:
        raise ValueError("Evento de monitoring inválido: falta id")

    payload = raw_event.get("payload", {})

    if "service" not in payload or "severity" not in payload:
        raise ValueError("Evento de monitoring inválido: falta service o severity")

    return CanonicalEvent(
        source="monitoring",
        event_type="alert.created",
        external_id=external_id,
        payload={
            "service": payload["service"],
            "severity": payload["severity"],
            "description": payload.get("description", ""),
            "affected_users": payload.get("affected_users", 1),
        },
    )


def _normalize_sharepoint_event(raw_event: dict[str, Any]) -> CanonicalEvent:
    external_id = str(raw_event.get("id", ""))

    if not external_id:
        raise ValueError("Evento de SharePoint inválido: falta id")

    payload = raw_event.get("payload", {})

    if "document_id" not in payload or "file_name" not in payload:
        raise ValueError("Evento de SharePoint inválido: falta document_id o file_name")

    return CanonicalEvent(
        source="sharepoint",
        event_type="document.uploaded",
        external_id=external_id,
        payload={
            "document_id": payload["document_id"],
            "file_name": payload["file_name"],
            "site": payload.get("site", "desconocido"),
            "library": payload.get("library", "documentos"),
            "uploaded_by": payload.get("uploaded_by", "desconocido"),
            "classification_hint": payload.get("classification_hint", ""),
        },
    )