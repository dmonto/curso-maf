from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class SensitivityLevel(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class SensitiveMatch:
    kind: str
    value: str
    start: int
    end: int
    level: SensitivityLevel
    replacement: str


@dataclass(frozen=True)
class SensitiveDataReport:
    original_text: str
    sanitized_text: str
    matches: list[SensitiveMatch] = field(default_factory=list)
    blocked: bool = False
    reason: str | None = None

    @property
    def has_sensitive_data(self) -> bool:
        return bool(self.matches)

    @property
    def highest_level(self) -> SensitivityLevel:
        if not self.matches:
            return SensitivityLevel.NONE

        order = {
            SensitivityLevel.NONE: 0,
            SensitivityLevel.LOW: 1,
            SensitivityLevel.MEDIUM: 2,
            SensitivityLevel.HIGH: 3,
            SensitivityLevel.CRITICAL: 4,
        }

        return max((match.level for match in self.matches), key=lambda level: order[level])


PATTERNS: list[tuple[str, re.Pattern[str], SensitivityLevel, str]] = [
    (
        "email",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
        SensitivityLevel.LOW,
        "[EMAIL_REDACTED]",
    ),
    (
        "phone_es",
        re.compile(r"(?<!\d)(?:\+34\s?)?[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}(?!\d)"),
        SensitivityLevel.MEDIUM,
        "[PHONE_REDACTED]",
    ),
    (
        "dni_nif",
        re.compile(r"\b\d{8}[A-Z]\b", re.IGNORECASE),
        SensitivityLevel.MEDIUM,
        "[ID_REDACTED]",
    ),
    (
        "iban",
        re.compile(r"\bES\d{2}[\s-]?(?:\d{4}[\s-]?){5}\b", re.IGNORECASE),
        SensitivityLevel.HIGH,
        "[IBAN_REDACTED]",
    ),
    (
        "api_key_like",
        re.compile(
            r"\b(?:sk|pk|api|key|token)[-_]?[A-Za-z0-9]{16,}\b",
            re.IGNORECASE,
        ),
        SensitivityLevel.CRITICAL,
        "[SECRET_REDACTED]",
    ),
    (
        "jwt_like",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        SensitivityLevel.CRITICAL,
        "[JWT_REDACTED]",
    ),
    (
        "private_key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |)?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH |)?PRIVATE KEY-----",
            re.IGNORECASE | re.DOTALL,
        ),
        SensitivityLevel.CRITICAL,
        "[PRIVATE_KEY_REDACTED]",
    ),
]


def detect_sensitive_data(text: str) -> list[SensitiveMatch]:
    matches: list[SensitiveMatch] = []

    for kind, pattern, level, replacement in PATTERNS:
        for match in pattern.finditer(text):
            matches.append(
                SensitiveMatch(
                    kind=kind,
                    value=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    level=level,
                    replacement=replacement,
                )
            )

    # Evita solapes simples priorizando coincidencias más largas.
    matches.sort(key=lambda item: (item.start, -(item.end - item.start)))

    filtered: list[SensitiveMatch] = []
    occupied: set[int] = set()

    for match in matches:
        span = set(range(match.start, match.end))
        if occupied.intersection(span):
            continue
        filtered.append(match)
        occupied.update(span)

    return filtered


def sanitize_text(text: str, *, block_critical: bool = True) -> SensitiveDataReport:
    matches = detect_sensitive_data(text)

    if not matches:
        return SensitiveDataReport(
            original_text=text,
            sanitized_text=text,
            matches=[],
            blocked=False,
        )

    sanitized_parts: list[str] = []
    cursor = 0

    for match in sorted(matches, key=lambda item: item.start):
        sanitized_parts.append(text[cursor:match.start])
        sanitized_parts.append(match.replacement)
        cursor = match.end

    sanitized_parts.append(text[cursor:])
    sanitized_text = "".join(sanitized_parts)

    critical_detected = any(match.level == SensitivityLevel.CRITICAL for match in matches)

    if block_critical and critical_detected:
        return SensitiveDataReport(
            original_text=text,
            sanitized_text=sanitized_text,
            matches=matches,
            blocked=True,
            reason="Se han detectado secretos o credenciales. No se enviará este contenido al modelo.",
        )

    return SensitiveDataReport(
        original_text=text,
        sanitized_text=sanitized_text,
        matches=matches,
        blocked=False,
    )


def summarize_matches(matches: list[SensitiveMatch]) -> list[dict[str, str]]:
    """
    Devuelve un resumen seguro. No devuelve los valores originales.
    """
    return [
        {
            "kind": match.kind,
            "level": match.level.value,
            "replacement": match.replacement,
        }
        for match in matches
    ]