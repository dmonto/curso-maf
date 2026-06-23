from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero requerido: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def load_governance_config(path: Path = Path("config/pipeline_governance.json")) -> dict[str, Any]:
    return load_json(path)


def load_agent_profile(path: Path = Path("config/agent_risk_profile.json")) -> dict[str, Any] | None:
    return load_optional_json(path)


def load_evaluation_summary(path: Path = Path("reports/evaluation_summary.json")) -> dict[str, Any] | None:
    return load_optional_json(path)


def load_risk_report(path: Path = Path("reports/agent_risk_assessment.json")) -> dict[str, Any] | None:
    return load_optional_json(path)


def load_compliance_report(path: Path = Path("reports/compliance_report.json")) -> dict[str, Any] | None:
    return load_optional_json(path)