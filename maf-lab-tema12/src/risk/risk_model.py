from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RiskSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskStatus(StrEnum):
    OPEN = "open"
    MITIGATED = "mitigated"
    ACCEPTED = "accepted"


@dataclass(frozen=True)
class RiskFinding:
    risk_id: str
    title: str
    category: str
    description: str
    impact: int
    likelihood: int
    controls_present: list[str] = field(default_factory=list)
    controls_missing: list[str] = field(default_factory=list)
    recommendation: str = ""
    status: RiskStatus = RiskStatus.OPEN

    @property
    def score(self) -> int:
        return self.impact * self.likelihood

    @property
    def severity(self) -> RiskSeverity:
        if self.score >= 15:
            return RiskSeverity.CRITICAL
        if self.score >= 10:
            return RiskSeverity.HIGH
        if self.score >= 5:
            return RiskSeverity.MEDIUM
        return RiskSeverity.LOW


@dataclass(frozen=True)
class RiskAssessment:
    agent_name: str
    environment: str
    findings: list[RiskFinding]

    @property
    def highest_severity(self) -> RiskSeverity:
        if not self.findings:
            return RiskSeverity.LOW

        order = {
            RiskSeverity.LOW: 1,
            RiskSeverity.MEDIUM: 2,
            RiskSeverity.HIGH: 3,
            RiskSeverity.CRITICAL: 4,
        }

        return max((finding.severity for finding in self.findings), key=lambda item: order[item])

    @property
    def total_score(self) -> int:
        return sum(finding.score for finding in self.findings)