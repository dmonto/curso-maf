from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from src.identity.context import IdentityContext


class ModelExposureAction(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    SAFE_REDIRECT = "safe_redirect"


@dataclass(frozen=True)
class ModelExposureDecision:
    action: ModelExposureAction
    model_alias: str | None
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    safe_message: str | None = None
    risk_tags: list[str] = field(default_factory=list)


ALLOWED_MODELS_BY_GROUP = {
    "support_l1": {"chat_fast", "chat_default"},
    "support_admin": {"chat_fast", "chat_default", "chat_quality"},
    "finance": {"chat_fast", "chat_default"},
    "security": {"chat_default", "chat_quality"},
}


DEFAULT_MODEL_BY_GROUP = {
    "support_l1": "chat_fast",
    "support_admin": "chat_default",
    "finance": "chat_fast",
    "security": "chat_default",
}


PUBLIC_MODEL_LABELS = {
    "chat_fast": "modelo rápido autorizado",
    "chat_default": "modelo conversacional estándar autorizado",
    "chat_quality": "modelo avanzado autorizado",
}


BLOCKED_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "system_prompt_disclosure",
        re.compile(
            r"(system prompt|prompt del sistema|instrucciones internas|mu[eé]strame tus instrucciones)",
            re.IGNORECASE,
        ),
        "No puedo mostrar instrucciones internas del agente.",
    ),
    (
        "deployment_disclosure",
        re.compile(
            r"(deployment|endpoint|api version|api_key|azure_openai|connection string)",
            re.IGNORECASE,
        ),
        "No puedo revelar detalles internos de infraestructura, endpoints o deployments.",
    ),
    (
        "model_forcing",
        re.compile(
            r"(usa el modelo m[aá]s caro|cambia al deployment|ignora el router|usa gpt-4o directamente)",
            re.IGNORECASE,
        ),
        "No puedo cambiar el modelo saltando la política de exposición.",
    ),
    (
        "parameter_abuse",
        re.compile(
            r"(temperature\s*=\s*[2-9]|max_tokens\s*=\s*[1-9]\d{4,}|sin l[ií]mite de tokens)",
            re.IGNORECASE,
        ),
        "No puedo aplicar parámetros que incumplen los límites operativos.",
    ),
]


def allowed_models_for(identity: IdentityContext) -> set[str]:
    allowed: set[str] = set()

    for group in identity.groups:
        allowed.update(ALLOWED_MODELS_BY_GROUP.get(group, set()))

    return allowed


def default_model_for(identity: IdentityContext) -> str:
    for group in identity.groups:
        if group in DEFAULT_MODEL_BY_GROUP:
            return DEFAULT_MODEL_BY_GROUP[group]

    return "chat_fast"


def detect_model_exposure_risks(user_text: str) -> list[tuple[str, str]]:
    risks: list[tuple[str, str]] = []

    for tag, pattern, message in BLOCKED_PATTERNS:
        if pattern.search(user_text):
            risks.append((tag, message))

    return risks


def decide_model_exposure(
    *,
    identity: IdentityContext,
    user_text: str,
    requested_model_alias: str | None = None,
    environment: str = "local",
) -> ModelExposureDecision:
    """
    Decide si una petición puede llegar al modelo y qué alias lógico debe usarse.

    No devuelve nombres reales de deployment.
    No acepta escalado de modelo desde el texto del usuario.
    """

    risks = detect_model_exposure_risks(user_text)

    if risks:
        return ModelExposureDecision(
            action=ModelExposureAction.SAFE_REDIRECT,
            model_alias=None,
            allowed=False,
            reasons=[message for _, message in risks],
            safe_message="La petición solicita detalles internos o cambios de modelo no permitidos.",
            risk_tags=[tag for tag, _ in risks],
        )

    allowed_aliases = allowed_models_for(identity)

    if not allowed_aliases:
        return ModelExposureDecision(
            action=ModelExposureAction.DENY,
            model_alias=None,
            allowed=False,
            reasons=["La identidad no tiene modelos autorizados."],
            safe_message="No tienes modelos autorizados para esta operación.",
        )

    selected_alias = requested_model_alias or default_model_for(identity)

    if selected_alias not in allowed_aliases:
        return ModelExposureDecision(
            action=ModelExposureAction.DENY,
            model_alias=None,
            allowed=False,
            reasons=[
                f"El alias lógico solicitado no está autorizado para los grupos del usuario."
            ],
            safe_message="El modelo solicitado no está autorizado para tu perfil.",
            risk_tags=["unauthorized_model_alias"],
        )

    if environment == "prod" and selected_alias == "chat_quality":
        if "support_admin" not in identity.groups and "security" not in identity.groups:
            return ModelExposureDecision(
                action=ModelExposureAction.DENY,
                model_alias=None,
                allowed=False,
                reasons=["El modelo avanzado en producción requiere perfil autorizado."],
                safe_message="No tienes permiso para usar el modelo avanzado en producción.",
                risk_tags=["prod_quality_model_denied"],
            )

    return ModelExposureDecision(
        action=ModelExposureAction.ALLOW,
        model_alias=selected_alias,
        allowed=True,
        reasons=[
            f"Modelo lógico autorizado: {PUBLIC_MODEL_LABELS.get(selected_alias, 'modelo autorizado')}"
        ],
    )


def shield_model_output(text: str) -> str:
    """
    Evita que la respuesta final exponga detalles internos si aparecen por error.
    """

    replacements = [
        (
            re.compile(r"https://[a-z0-9.-]+\.openai\.azure\.com/?", re.IGNORECASE),
            "[AZURE_OPENAI_ENDPOINT_REDACTED]",
        ),
        (
            re.compile(r"https://[a-z0-9.-]+\.cognitiveservices\.azure\.com/?", re.IGNORECASE),
            "[AZURE_ENDPOINT_REDACTED]",
        ),
        (
            re.compile(r"\bAZURE_OPENAI_[A-Z0-9_]+\b"),
            "[AZURE_CONFIG_REDACTED]",
        ),
        (
            re.compile(r"\b(?:gpt-4o|gpt-4\.1|o3|o4-mini)[a-z0-9.-]*\b", re.IGNORECASE),
            "[MODEL_DETAIL_REDACTED]",
        ),
    ]

    sanitized = text

    for pattern, replacement in replacements:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized