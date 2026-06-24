from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DependencySettings:
    app_env: str
    incident_classifier_mode: str
    event_publisher_mode: str
    incidents_path: Path
    classifications_path: Path
    events_path: Path


def load_dependency_settings() -> DependencySettings:
    return DependencySettings(
        app_env=os.getenv("APP_ENV", "dev"),
        incident_classifier_mode=os.getenv("INCIDENT_CLASSIFIER_MODE", "rules"),
        event_publisher_mode=os.getenv("EVENT_PUBLISHER_MODE", "jsonl"),
        incidents_path=Path(os.getenv("INCIDENTS_PATH", "data/di_incidents.jsonl")),
        classifications_path=Path(
            os.getenv("CLASSIFICATIONS_PATH", "data/di_classifications.jsonl")
        ),
        events_path=Path(os.getenv("EVENTS_PATH", "data/di_events.jsonl")),
    )