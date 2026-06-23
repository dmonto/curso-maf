from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class GateStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass(frozen=True)
class GovernanceFinding:
    check_id: str
    title: str
    status: GateStatus
    severity: str
    description: str
    recommendation: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineGateResult:
    pipeline_name: str
    target_environment: str
    status: GateStatus
    findings: list[GovernanceFinding]

    @property
    def passed(self) -> bool:
        return self.status != GateStatus.FAIL

    @property
    def blocking_findings(self) -> list[GovernanceFinding]:
        return [finding for finding in self.findings if finding.status == GateStatus.FAIL]