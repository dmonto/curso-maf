from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ComplianceStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"


class ComplianceSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ComplianceRequirement:
    id: str
    domain: str
    title: str
    description: str
    required_controls: list[str]
    required_evidence_events: list[str] = field(default_factory=list)
    required_evidence_files: list[str] = field(default_factory=list)
    severity_if_missing: ComplianceSeverity = ComplianceSeverity.MEDIUM


@dataclass(frozen=True)
class ComplianceFinding:
    requirement_id: str
    domain: str
    title: str
    status: ComplianceStatus
    severity: ComplianceSeverity
    controls_present: list[str]
    controls_missing: list[str]
    evidence_events_present: list[str]
    evidence_events_missing: list[str]
    evidence_files_present: list[str]
    evidence_files_missing: list[str]
    recommendation: str


@dataclass(frozen=True)
class ComplianceAssessment:
    framework: str
    version: str
    agent_name: str
    environment: str
    findings: list[ComplianceFinding]

    @property
    def passed(self) -> bool:
        return all(finding.status == ComplianceStatus.PASS for finding in self.findings)

    @property
    def blocking_findings(self) -> list[ComplianceFinding]:
        return [
            finding
            for finding in self.findings
            if finding.status != ComplianceStatus.PASS
            and finding.severity in {ComplianceSeverity.HIGH, ComplianceSeverity.CRITICAL}
        ]