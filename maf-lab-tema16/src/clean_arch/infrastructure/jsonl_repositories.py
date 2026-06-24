from __future__ import annotations

import json
from pathlib import Path

from src.clean_arch.domain.incident import Incident, IncidentClassification


class JsonlIncidentRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/clean_arch_incidents.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def save_incident(self, incident: Incident) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(incident.to_dict(), ensure_ascii=False) + "\n")


class JsonlClassificationRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/clean_arch_classifications.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def save_classification(self, classification: IncidentClassification) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(classification.to_dict(), ensure_ascii=False) + "\n")