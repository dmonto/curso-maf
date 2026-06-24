from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from src.clean_arch.application.ports import (
    ClassificationRepository,
    EventPublisher,
    IncidentClassifier,
    IncidentRepository,
)
from src.clean_arch.domain.incident import Incident, SupportService
from src.clean_arch.domain.policies import IncidentPolicy


@dataclass(frozen=True)
class ReportIncidentCommand:
    service: str
    summary: str
    affected_users: int
    business_impact: str


class ReportAndClassifyIncidentUseCase:
    def __init__(
        self,
        incident_repository: IncidentRepository,
        classification_repository: ClassificationRepository,
        classifier: IncidentClassifier,
        event_publisher: EventPublisher,
        policy: IncidentPolicy,
    ) -> None:
        self.incident_repository = incident_repository
        self.classification_repository = classification_repository
        self.classifier = classifier
        self.event_publisher = event_publisher
        self.policy = policy

    def execute(self, command: ReportIncidentCommand) -> dict:
        correlation_id = f"corr-{uuid4().hex[:10]}"

        incident = Incident.create(
            service=SupportService(command.service),
            summary=command.summary,
            affected_users=command.affected_users,
            business_impact=command.business_impact,
        )

        self.policy.validate(incident)

        self.incident_repository.save_incident(incident)

        self.event_publisher.publish(
            event_type="support.incident.reported.v1",
            payload=incident.to_dict(),
            correlation_id=correlation_id,
        )

        classification = self.classifier.classify(incident)

        self.classification_repository.save_classification(classification)

        self.event_publisher.publish(
            event_type="support.incident.classified.v1",
            payload=classification.to_dict(),
            correlation_id=correlation_id,
        )

        return {
            "correlation_id": correlation_id,
            "incident": incident.to_dict(),
            "classification": classification.to_dict(),
        }