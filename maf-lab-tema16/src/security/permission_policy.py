from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Decision = Literal["allow", "deny"]


@dataclass(frozen=True)
class UserAccessContext:
    user_id: str
    tenant_id: str
    groups: list[str]


@dataclass(frozen=True)
class DocumentPermission:
    tenant_id: str
    visibility: str
    allowed_users: list[str]
    allowed_groups: list[str]
    denied_users: list[str]
    denied_groups: list[str]
    classification: str
    owner: str


@dataclass(frozen=True)
class PermissionDecision:
    decision: Decision
    reason: str


def _intersects(left: list[str], right: list[str]) -> bool:
    return bool(set(left).intersection(set(right)))


def evaluate_document_permission(
    user: UserAccessContext,
    permission: DocumentPermission,
) -> PermissionDecision:
    if user.tenant_id != permission.tenant_id:
        return PermissionDecision(
            decision="deny",
            reason="tenant_mismatch",
        )

    if user.user_id in permission.denied_users:
        return PermissionDecision(
            decision="deny",
            reason="user_explicitly_denied",
        )

    if _intersects(user.groups, permission.denied_groups):
        return PermissionDecision(
            decision="deny",
            reason="group_explicitly_denied",
        )

    if permission.visibility == "public":
        return PermissionDecision(
            decision="allow",
            reason="public_within_tenant",
        )

    if user.user_id in permission.allowed_users:
        return PermissionDecision(
            decision="allow",
            reason="user_explicitly_allowed",
        )

    if _intersects(user.groups, permission.allowed_groups):
        return PermissionDecision(
            decision="allow",
            reason="group_allowed",
        )

    return PermissionDecision(
        decision="deny",
        reason="no_matching_allow_rule",
    )