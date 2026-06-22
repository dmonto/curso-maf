from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class CorporateDocument:
    source_id: str
    source_type: str
    title: str
    domain: str
    tenant_id: str
    visibility: str
    classification: str
    allowed_groups: list[str]
    allowed_users: list[str]
    denied_groups: list[str]
    denied_users: list[str]
    owner: str
    path: str
    text: str
    source_last_modified_utc: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)