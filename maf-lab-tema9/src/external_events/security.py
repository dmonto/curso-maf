# src/external_events/security.py

from __future__ import annotations

import hashlib
import hmac
import os


def get_shared_secret() -> str:
    secret = os.getenv("EXTERNAL_EVENTS_SHARED_SECRET")

    if not secret:
        raise RuntimeError("Falta EXTERNAL_EVENTS_SHARED_SECRET")

    return secret


def compute_signature(body: bytes, secret: str) -> str:
    digest = hmac.new(
        key=secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return f"sha256={digest}"


def validate_signature(body: bytes, received_signature: str | None) -> bool:
    if not received_signature:
        return False

    expected_signature = compute_signature(
        body=body,
        secret=get_shared_secret(),
    )

    return hmac.compare_digest(expected_signature, received_signature)