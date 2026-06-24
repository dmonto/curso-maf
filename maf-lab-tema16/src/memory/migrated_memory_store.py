from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.memory.legacy_memory_migrator import MemoryTarget, MigratedMemoryRecord


DEFAULT_STORE_PATH = Path("data/migrated_memory_store.json")


class MigratedMemoryStore:
    def __init__(self, path: Path = DEFAULT_STORE_PATH) -> None:
        self.path = path

    def save_many(self, records: list[MigratedMemoryRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        persisted = [
            asdict(record)
            for record in records
            if record.target not in {MemoryTarget.DISCARD.value, MemoryTarget.MANUAL_REVIEW.value}
        ]

        self.path.write_text(
            json.dumps(persisted, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        return json.loads(self.path.read_text(encoding="utf-8"))

    def build_context_for_agent(
        self,
        *,
        user_id: str,
        session_id: str | None,
    ) -> dict[str, Any]:
        records = self.load_all()

        user_records = [
            record
            for record in records
            if record["user_id"] == user_id
            and (record["session_id"] in {session_id, None})
        ]

        long_term_memory = [
            record["value"]
            for record in user_records
            if record["target"] == MemoryTarget.LONG_TERM_MEMORY.value
        ]

        session_state_records = [
            record["value"]
            for record in user_records
            if record["target"] == MemoryTarget.SESSION_STATE.value
        ]

        audit_records = [
            record["value"]
            for record in user_records
            if record["target"] == MemoryTarget.AUDIT_LOG.value
        ]

        merged_state: dict[str, Any] = {
            "service": None,
            "operating_system": None,
            "steps_tried": [],
            "ticket_requested": False,
        }

        for state in session_state_records:
            if state.get("service"):
                merged_state["service"] = state["service"]

            if state.get("operating_system"):
                merged_state["operating_system"] = state["operating_system"]

            merged_state["steps_tried"].extend(state.get("steps_tried", []))

            if state.get("ticket_requested"):
                merged_state["ticket_requested"] = True

        merged_state["steps_tried"] = sorted(set(merged_state["steps_tried"]))

        return {
            "long_term_memory": long_term_memory,
            "session_state": merged_state,
            "audit_summary": audit_records,
        }


def render_context_for_prompt(context: dict[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=False, indent=2)