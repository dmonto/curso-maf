# 

from __future__ import annotations

import hashlib
import hmac
import json
import os

import httpx


def compute_signature(body: bytes, secret: str) -> str:
    digest = hmac.new(
        key=secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return f"sha256={digest}"


def send_event(source: str, event: dict) -> None:
    secret = os.getenv("EXTERNAL_EVENTS_SHARED_SECRET")

    if not secret:
        raise RuntimeError("Falta EXTERNAL_EVENTS_SHARED_SECRET")

    body = json.dumps(event, ensure_ascii=False).encode("utf-8")
    signature = compute_signature(body, secret)

    response = httpx.post(
        "http://127.0.0.1:8090/webhooks/external",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Event-Source": source,
            "X-Signature": signature,
        },
        timeout=10,
    )

    print(response.status_code)
    print(response.text)


if __name__ == "__main__":
    monitoring_event = {
        "id": "alert-1001",
        "payload": {
            "service": "vpn",
            "severity": "high",
            "description": "Aumento de errores de conexión remota",
            "affected_users": 25,
        },
    }

    sharepoint_event = {
        "id": "doc-event-2001",
        "payload": {
            "document_id": "DOC-1001",
            "file_name": "manual_vpn_windows.pdf",
            "site": "Soporte IT",
            "library": "Procedimientos",
            "uploaded_by": "usuario.demo",
            "classification_hint": "soporte",
        },
    }

    send_event("monitoring", monitoring_event)
    send_event("sharepoint", sharepoint_event)