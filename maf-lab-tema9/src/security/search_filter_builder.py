from __future__ import annotations

import re

from src.security.permission_policy import UserAccessContext


SAFE_VALUE_PATTERN = re.compile(r"^[a-zA-Z0-9@._:\-]+$")


def _validate_filter_value(value: str, field_name: str) -> str:
    if not value:
        raise ValueError(f"{field_name} no puede estar vacío.")

    if not SAFE_VALUE_PATTERN.match(value):
        raise ValueError(f"{field_name} contiene caracteres no permitidos: {value}")

    return value


def _quote(value: str) -> str:
    value = value.replace("'", "''")
    return f"'{value}'"


def build_permission_filter(
    user: UserAccessContext,
    domain: str | None = None,
    max_classification: str | None = None,
) -> str:
    tenant_id = _validate_filter_value(user.tenant_id, "tenant_id")
    user_id = _validate_filter_value(user.user_id, "user_id")

    allow_parts = [
        "visibility eq 'public'",
        f"allowed_users/any(u: u eq {_quote(user_id)})",
    ]

    for group in user.groups:
        safe_group = _validate_filter_value(group, "group")
        allow_parts.append(
            f"allowed_groups/any(g: g eq {_quote(safe_group)})"
        )

    deny_parts = [
        f"not denied_users/any(u: u eq {_quote(user_id)})",
    ]

    for group in user.groups:
        safe_group = _validate_filter_value(group, "group")
        deny_parts.append(
            f"not denied_groups/any(g: g eq {_quote(safe_group)})"
        )

    filters = [
        f"tenant_id eq {_quote(tenant_id)}",
        "(" + " or ".join(allow_parts) + ")",
        " and ".join(deny_parts),
    ]

    if domain:
        safe_domain = _validate_filter_value(domain, "domain")
        filters.append(f"domain eq {_quote(safe_domain)}")

    if max_classification:
        safe_classification = _validate_filter_value(
            max_classification,
            "max_classification",
        )
        filters.append(f"classification le {_quote(safe_classification)}")

    return " and ".join(f"({item})" for item in filters)