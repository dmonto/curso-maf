from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.compliance.compliance_model import (
    ComplianceRequirement,
    ComplianceSeverity,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_compliance_requirements(
    path: Path = Path("config/compliance_requirements.json"),
) -> tuple[str, str, list[ComplianceRequirement]]:
    payload = load_json(path)

    requirements = [
        ComplianceRequirement(
            id=item["id"],
            domain=item["domain"],
            title=item["title"],
            description=item["description"],
            required_controls=item.get("required_controls", []),
            required_evidence_events=item.get("required_evidence_events", []),
            required_evidence_files=item.get("required_evidence_files", []),
            severity_if_missing=ComplianceSeverity(item.get("severity_if_missing", "medium")),
        )
        for item in payload["requirements"]
    ]

    return payload["framework"], payload["version"], requirements


def load_agent_profile(path: Path = Path("config/agent_risk_profile.json")) -> dict[str, Any]:
    return load_json(path)