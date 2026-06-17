from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


Sensitivity = Literal["low", "medium", "high"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"\b(?:\+34\s?)?(?:6|7|8|9)\d{8}\b"
)

MFA_PATTERN = re.compile(
    r"\b(?:mfa|otp|código|codigo|token)\s*(?:es|:)?\s*\d{4,8}\b",
    re.IGNORECASE,
)

SECRET_LIKE_PATTERN = re.compile(
    r"(?i)\b(password|contraseña|passwd|api[_-]?key|secret|token|connection string)\b"
)

BEARER_PATTERN = re.compile(
    r"(?i)\bbearer\s+[a-z0-9._\-]+"
)

AZURE_CONNECTION_STRING_PATTERN = re.compile(
    r"(?i)DefaultEndpointsProtocol=.*?AccountKey=.*?(?:;|$)"
)


@dataclass(frozen=True)
class SecurityFinding:
    code: str
    severity: Sensitivity
    field_path: str
    action: str
    detail: str


@dataclass
class MemorySecurityReport:
    findings: list[SecurityFinding] = field(default_factory=list)
    original_hash: str | None = None
    sanitized_hash: str | None = None
    sanitized_at_utc: str = field(default_factory=utc_now)

    def add(
        self,
        code: str,
        severity: Sensitivity,
        field_path: str,
        action: str,
        detail: str,
    ) -> None:
        self.findings.append(
            SecurityFinding(
                code=code,
                severity=severity,
                field_path=field_path,
                action=action,
                detail=detail,
            )
        )

    def sensitivity(self) -> Sensitivity:
        if any(finding.severity == "high" for finding in self.findings):
            return "high"

        if any(finding.severity == "medium" for finding in self.findings):
            return "medium"

        return "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensitivity": self.sensitivity(),
            "original_hash": self.original_hash,
            "sanitized_hash": self.sanitized_hash,
            "sanitized_at_utc": self.sanitized_at_utc,
            "findings": [asdict(finding) for finding in self.findings],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class MemorySecurityGuard:
    """
    Sanitiza memoria antes de persistirla.

    Objetivos:
    - permitir solo campos esperados;
    - eliminar secretos;
    - redactar PII básica;
    - generar reporte de seguridad;
    - evitar que el agente convierta la memoria persistente en un almacén sin control.
    """

    def __init__(self) -> None:
        self.allowed_top_level_fields = {
            "servicio",
            "ubicacion",
            "sistema_operativo",
            "usuarios_afectados",
            "prioridad",
            "pasos_probados",
            "pendiente_confirmacion",
            "ultima_accion_recomendada",
            "impacto_negocio",
            "hora_inicio_aproximada",
            "hay_error_visible",
            "codigo_error",
        }

        self.blocked_field_names = {
            "password",
            "contraseña",
            "passwd",
            "secret",
            "api_key",
            "apikey",
            "token",
            "access_token",
            "refresh_token",
            "connection_string",
            "mfa_code",
            "otp",
        }

    def sanitize_memory(
        self,
        memory: dict[str, Any],
    ) -> tuple[dict[str, Any], MemorySecurityReport]:
        original = copy.deepcopy(memory)
        report = MemorySecurityReport()
        report.original_hash = self._hash_json(original)

        sanitized: dict[str, Any] = {}

        for key, value in original.items():
            field_path = key

            if key not in self.allowed_top_level_fields:
                report.add(
                    code="field_not_allowed",
                    severity="medium",
                    field_path=field_path,
                    action="dropped",
                    detail=f"Campo no permitido en memoria persistente: {key}",
                )
                continue

            if key.lower() in self.blocked_field_names:
                report.add(
                    code="blocked_field",
                    severity="high",
                    field_path=field_path,
                    action="dropped",
                    detail=f"Campo bloqueado por nombre: {key}",
                )
                continue

            sanitized_value = self._sanitize_value(
                value=value,
                field_path=field_path,
                report=report,
            )

            if sanitized_value is not None:
                sanitized[key] = sanitized_value

        report.sanitized_hash = self._hash_json(sanitized)

        return sanitized, report

    def _sanitize_value(
        self,
        value: Any,
        field_path: str,
        report: MemorySecurityReport,
    ) -> Any:
        if value is None:
            return None

        if isinstance(value, str):
            return self._sanitize_text(
                text=value,
                field_path=field_path,
                report=report,
            )

        if isinstance(value, list):
            sanitized_items = []

            for index, item in enumerate(value):
                sanitized_item = self._sanitize_value(
                    value=item,
                    field_path=f"{field_path}[{index}]",
                    report=report,
                )

                if sanitized_item is not None:
                    sanitized_items.append(sanitized_item)

            return sanitized_items

        if isinstance(value, dict):
            sanitized_dict: dict[str, Any] = {}

            for key, item in value.items():
                child_path = f"{field_path}.{key}"

                if key.lower() in self.blocked_field_names:
                    report.add(
                        code="blocked_nested_field",
                        severity="high",
                        field_path=child_path,
                        action="dropped",
                        detail=f"Campo anidado bloqueado por nombre: {key}",
                    )
                    continue

                sanitized_item = self._sanitize_value(
                    value=item,
                    field_path=child_path,
                    report=report,
                )

                if sanitized_item is not None:
                    sanitized_dict[key] = sanitized_item

            return sanitized_dict

        return value

    def _sanitize_text(
        self,
        text: str,
        field_path: str,
        report: MemorySecurityReport,
    ) -> str | None:
        if SECRET_LIKE_PATTERN.search(text):
            report.add(
                code="secret_like_text",
                severity="high",
                field_path=field_path,
                action="dropped",
                detail="El texto parece contener contraseña, token, secreto o clave.",
            )
            return None

        if BEARER_PATTERN.search(text):
            report.add(
                code="bearer_token_detected",
                severity="high",
                field_path=field_path,
                action="dropped",
                detail="Se ha detectado un token Bearer.",
            )
            return None

        if AZURE_CONNECTION_STRING_PATTERN.search(text):
            report.add(
                code="connection_string_detected",
                severity="high",
                field_path=field_path,
                action="dropped",
                detail="Se ha detectado una cadena de conexión.",
            )
            return None

        sanitized = text

        if MFA_PATTERN.search(sanitized):
            report.add(
                code="mfa_or_otp_detected",
                severity="high",
                field_path=field_path,
                action="redacted",
                detail="Se ha detectado un posible código MFA/OTP.",
            )
            sanitized = MFA_PATTERN.sub("[MFA_REDACTADO]", sanitized)

        if EMAIL_PATTERN.search(sanitized):
            report.add(
                code="email_detected",
                severity="medium",
                field_path=field_path,
                action="redacted",
                detail="Se ha detectado un email en memoria.",
            )
            sanitized = EMAIL_PATTERN.sub("[EMAIL_REDACTADO]", sanitized)

        if PHONE_PATTERN.search(sanitized):
            report.add(
                code="phone_detected",
                severity="medium",
                field_path=field_path,
                action="redacted",
                detail="Se ha detectado un teléfono en memoria.",
            )
            sanitized = PHONE_PATTERN.sub("[TELEFONO_REDACTADO]", sanitized)

        return sanitized

    def _hash_json(self, value: Any) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")

        return hashlib.sha256(payload).hexdigest()