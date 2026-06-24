from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class RetentionAction(StrEnum):
    DELETE = "delete"
    ARCHIVE = "archive"
    COMPACT = "compact"
    NEVER_STORE = "never_store"
    KEEP = "keep"


@dataclass(frozen=True)
class RetentionPolicy:
    name: str
    retention_days: int
    action: RetentionAction
    description: str


def load_retention_policies(
    path: Path = Path("config/retention_policies.json"),
) -> dict[str, RetentionPolicy]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    policies: dict[str, RetentionPolicy] = {}

    for name, raw_policy in payload["policies"].items():
        policies[name] = RetentionPolicy(
            name=name,
            retention_days=int(raw_policy["retention_days"]),
            action=RetentionAction(raw_policy["action"]),
            description=raw_policy.get("description", ""),
        )

    return policies