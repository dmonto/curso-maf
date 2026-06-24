from __future__ import annotations

from src.clean_arch.application.use_cases import ReportAndClassifyIncidentUseCase
from src.clean_arch.domain.policies import IncidentPolicy
from src.clean_arch.infrastructure.jsonl_events import JsonlEventPublisher
from src.clean_arch.infrastructure.jsonl_repositories import (
    JsonlClassificationRepository,
    JsonlIncidentRepository,
)
from src.clean_arch.infrastructure.rule_based_classifier import RuleBasedIncidentClassifier


class CleanArchContainer:
    def report_and_classify_incident_use_case(self) -> ReportAndClassifyIncidentUseCase:
        return ReportAndClassifyIncidentUseCase(
            incident_repository=JsonlIncidentRepository(),
            classification_repository=JsonlClassificationRepository(),
            classifier=RuleBasedIncidentClassifier(),
            event_publisher=JsonlEventPublisher(),
            policy=IncidentPolicy(),
        )


def build_container() -> CleanArchContainer:
    return CleanArchContainer()