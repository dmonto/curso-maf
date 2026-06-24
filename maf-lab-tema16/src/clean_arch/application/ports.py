from __future__ import annotations

from typing import Protocol

from src.clean_arch.domain.incident import Incident, IncidentClassification


class IncidentRepository(Protocol):
    def save_incident(self, incident: Incident) -> None:
        ...


class ClassificationRepository(Protocol):
    def save_classification(self, classification: IncidentClassification) -> None:
        ...


class IncidentClassifier(Protocol):
    def classify(self, incident: Incident) -> IncidentClassification:
        ...


class EventPublisher(Protocol):
    def publish(self, event_type: str, payload: dict, correlation_id: str) -> None:
        ...