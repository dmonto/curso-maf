from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BehaviorRule(StrEnum):
    NO_REAL_ACTION_WITHOUT_CONFIRMATION = "no_real_action_without_confirmation"
    NO_SENSITIVE_DATA_EXPOSURE = "no_sensitive_data_exposure"
    ASK_WHEN_REQUIRED_FIELDS_MISSING = "ask_when_required_fields_missing"
    DO_NOT_PREPARE_DRAFT_WITH_MISSING_FIELDS = "do_not_prepare_draft_with_missing_fields"
    RESPONSE_MATCHES_WORKFLOW_STATUS = "response_matches_workflow_status"
    REQUIRED_EVENTS_PRESENT = "required_events_present"


@dataclass(frozen=True)
class BehaviorViolation:
    rule: str
    severity: str
    message: str
    evidence: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class BehaviorValidationResult:
    passed: bool
    violations: list[BehaviorViolation]

    @property
    def critical_count(self) -> int:
        return sum(1 for item in self.violations if item.severity == Severity.CRITICAL.value)

    @property
    def error_count(self) -> int:
        return sum(1 for item in self.violations if item.severity == Severity.ERROR.value)