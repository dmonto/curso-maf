from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


CLASSIFICATION_RANK = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
}


GROUP_PERMISSIONS = {
    "support_l1": {
        "knowledge.search",
        "incident.draft",
    },
    "support_admin": {
        "knowledge.search",
        "incident.draft",
        "identity.read_restricted",
    },
    "security": {
        "knowledge.search",
        "identity.read_restricted",
    },
    "finance": {
        "knowledge.search",
    },
}


@dataclass(frozen=True)
class UserAccessContext:
    user_id: str
    tenant_id: str
    groups: tuple[str, ...]
    department: str
    allowed_areas: tuple[str, ...]
    data_clearance: str = "internal"


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    action: str
    reason: str
    matched_groups: tuple[str, ...] = field(default_factory=tuple)


def _rank(classification: str) -> int:
    return CLASSIFICATION_RANK.get(classification, 99)


def _permissions_for(groups: Iterable[str]) -> set[str]:
    permissions: set[str] = set()

    for group in groups:
        permissions.update(GROUP_PERMISSIONS.get(group, set()))

    return permissions


def authorize(
    user_context: UserAccessContext,
    *,
    action: str,
    area: str | None = None,
    classification: str = "internal",
    tenant_id: str | None = None,
) -> AccessDecision:
    """
    Decide si un usuario puede ejecutar una acción concreta.

    Esta función no usa el mensaje del usuario ni ningún texto generado por el modelo.
    Solo usa contexto confiable de identidad, grupos y atributos.
    """

    if tenant_id is not None and tenant_id != user_context.tenant_id:
        return AccessDecision(
            allowed=False,
            action=action,
            reason="El recurso pertenece a otro tenant.",
        )

    permissions = _permissions_for(user_context.groups)

    if action not in permissions:
        return AccessDecision(
            allowed=False,
            action=action,
            reason="Ningún grupo del usuario concede esta acción.",
            matched_groups=tuple(user_context.groups),
        )

    if area is not None and area not in user_context.allowed_areas:
        return AccessDecision(
            allowed=False,
            action=action,
            reason=f"El usuario no tiene acceso al área '{area}'.",
            matched_groups=tuple(user_context.groups),
        )

    if _rank(classification) > _rank(user_context.data_clearance):
        return AccessDecision(
            allowed=False,
            action=action,
            reason=(
                f"La clasificación '{classification}' supera el nivel "
                f"'{user_context.data_clearance}' del usuario."
            ),
            matched_groups=tuple(user_context.groups),
        )

    return AccessDecision(
        allowed=True,
        action=action,
        reason="Acceso autorizado.",
        matched_groups=tuple(user_context.groups),
    )