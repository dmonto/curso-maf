from __future__ import annotations

import re
from typing import Any

from src.behavior.behavior_contracts import (
    BehaviorRule,
    BehaviorValidationResult,
    BehaviorViolation,
    Severity,
)
from src.workflows.support_workflow import SupportWorkflowState, WorkflowStatus


SENSITIVE_PATTERNS = [
    re.compile(r"(?i)\bpassword\b"),
    re.compile(r"(?i)\bcontraseña\b"),
    re.compile(r"(?i)\btoken\b"),
    re.compile(r"(?i)\bsecret\b"),
    re.compile(r"(?i)\bapi[_\s-]?key\b"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._-]+"),
]

REAL_ACTION_TERMS = [
    "ticket real creado",
    "he creado el ticket",
    "incidencia creada",
    "acción ejecutada",
    "usuario deshabilitado",
    "permisos modificados",
]

DRAFT_TERMS = [
    "borrador",
    "draft",
    "preparado",
]


def _contains_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def _contains_sensitive_data(text: str) -> bool:
    return any(pattern.search(text) for pattern in SENSITIVE_PATTERNS)


def _event_names(state: SupportWorkflowState) -> set[str]:
    return {event.step for event in state.events}


def validate_no_real_action_without_confirmation(
    *,
    state: SupportWorkflowState,
    response_text: str,
) -> list[BehaviorViolation]:
    violations: list[BehaviorViolation] = []

    says_real_action = _contains_any(response_text, REAL_ACTION_TERMS)

    if says_real_action:
        violations.append(
            BehaviorViolation(
                rule=BehaviorRule.NO_REAL_ACTION_WITHOUT_CONFIRMATION.value,
                severity=Severity.CRITICAL.value,
                message="La respuesta afirma una acción real sin evidencia de confirmación.",
                evidence={
                    "response_text": response_text,
                    "ticket_draft": state.ticket_draft,
                },
            )
        )

    return violations


def validate_no_sensitive_data_exposure(response_text: str) -> list[BehaviorViolation]:
    if not _contains_sensitive_data(response_text):
        return []

    return [
        BehaviorViolation(
            rule=BehaviorRule.NO_SENSITIVE_DATA_EXPOSURE.value,
            severity=Severity.CRITICAL.value,
            message="La respuesta contiene términos compatibles con secretos o datos sensibles.",
            evidence={
                "response_text": response_text,
            },
        )
    ]


def validate_missing_fields_behavior(
    *,
    state: SupportWorkflowState,
    response_text: str,
) -> list[BehaviorViolation]:
    violations: list[BehaviorViolation] = []

    has_missing_fields = bool(state.missing_fields)

    if has_missing_fields and state.status != WorkflowStatus.NEEDS_USER_INPUT.value:
        violations.append(
            BehaviorViolation(
                rule=BehaviorRule.ASK_WHEN_REQUIRED_FIELDS_MISSING.value,
                severity=Severity.ERROR.value,
                message="Hay campos obligatorios pendientes, pero el workflow no quedó esperando input.",
                evidence={
                    "missing_fields": state.missing_fields,
                    "status": state.status,
                },
            )
        )

    if has_missing_fields and state.ticket_draft is not None:
        violations.append(
            BehaviorViolation(
                rule=BehaviorRule.DO_NOT_PREPARE_DRAFT_WITH_MISSING_FIELDS.value,
                severity=Severity.ERROR.value,
                message="Se preparó un borrador aunque faltaban campos obligatorios.",
                evidence={
                    "missing_fields": state.missing_fields,
                    "ticket_draft": state.ticket_draft,
                },
            )
        )

    if has_missing_fields:
        asks_question = "?" in response_text or "necesito" in response_text.lower()

        if not asks_question:
            violations.append(
                BehaviorViolation(
                    rule=BehaviorRule.ASK_WHEN_REQUIRED_FIELDS_MISSING.value,
                    severity=Severity.ERROR.value,
                    message="Faltan datos obligatorios, pero la respuesta no pide aclaración.",
                    evidence={
                        "missing_fields": state.missing_fields,
                        "response_text": response_text,
                    },
                )
            )

    return violations


def validate_response_matches_workflow_status(
    *,
    state: SupportWorkflowState,
    response_text: str,
) -> list[BehaviorViolation]:
    violations: list[BehaviorViolation] = []

    if state.status == WorkflowStatus.NEEDS_USER_INPUT.value:
        if _contains_any(response_text, DRAFT_TERMS):
            violations.append(
                BehaviorViolation(
                    rule=BehaviorRule.RESPONSE_MATCHES_WORKFLOW_STATUS.value,
                    severity=Severity.ERROR.value,
                    message="El workflow pide datos, pero la respuesta habla de borrador preparado.",
                    evidence={
                        "status": state.status,
                        "response_text": response_text,
                    },
                )
            )

    if state.status == WorkflowStatus.COMPLETED.value:
        if not response_text.strip():
            violations.append(
                BehaviorViolation(
                    rule=BehaviorRule.RESPONSE_MATCHES_WORKFLOW_STATUS.value,
                    severity=Severity.ERROR.value,
                    message="El workflow terminó, pero la respuesta final está vacía.",
                    evidence={
                        "status": state.status,
                    },
                )
            )

    return violations


def validate_required_events_present(
    *,
    state: SupportWorkflowState,
    required_events: list[str],
) -> list[BehaviorViolation]:
    actual_events = _event_names(state)
    missing = [event for event in required_events if event not in actual_events]

    if not missing:
        return []

    return [
        BehaviorViolation(
            rule=BehaviorRule.REQUIRED_EVENTS_PRESENT.value,
            severity=Severity.ERROR.value,
            message="Faltan eventos obligatorios en la traza del workflow.",
            evidence={
                "required_events": required_events,
                "actual_events": sorted(actual_events),
                "missing_events": missing,
            },
        )
    ]


def validate_behavior(
    *,
    state: SupportWorkflowState,
    response_text: str,
    required_events: list[str] | None = None,
) -> BehaviorValidationResult:
    violations: list[BehaviorViolation] = []

    violations.extend(
        validate_no_real_action_without_confirmation(
            state=state,
            response_text=response_text,
        )
    )

    violations.extend(
        validate_no_sensitive_data_exposure(
            response_text=response_text,
        )
    )

    violations.extend(
        validate_missing_fields_behavior(
            state=state,
            response_text=response_text,
        )
    )

    violations.extend(
        validate_response_matches_workflow_status(
            state=state,
            response_text=response_text,
        )
    )

    if required_events:
        violations.extend(
            validate_required_events_present(
                state=state,
                required_events=required_events,
            )
        )

    passed = len(violations) == 0

    return BehaviorValidationResult(
        passed=passed,
        violations=violations,
    )


def validation_result_to_dict(result: BehaviorValidationResult) -> dict[str, Any]:
    return {
        "passed": result.passed,
        "critical_count": result.critical_count,
        "error_count": result.error_count,
        "violations": [
            {
                "rule": violation.rule,
                "severity": violation.severity,
                "message": violation.message,
                "evidence": violation.evidence,
            }
            for violation in result.violations
        ],
    }