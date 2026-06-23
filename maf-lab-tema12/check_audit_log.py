from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


AUDIT_LOG_PATH = Path("logs/interaction_audit.jsonl")


def main() -> None:
    if not AUDIT_LOG_PATH.exists():
        print("No existe logs/interaction_audit.jsonl")
        return

    events = []

    with AUDIT_LOG_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                events.append(json.loads(line))

    print(f"Eventos encontrados: {len(events)}")

    by_type = Counter(event["event_type"] for event in events)
    by_component = Counter(event["component"] for event in events)

    print("\nEventos por tipo:")
    for event_type, count in by_type.items():
        print(f"- {event_type}: {count}")

    print("\nEventos por componente:")
    for component, count in by_component.items():
        print(f"- {component}: {count}")

    print("\nÚltimos eventos:")
    for event in events[-5:]:
        print(
            {
                "timestamp_utc": event["timestamp_utc"],
                "event_type": event["event_type"],
                "component": event["component"],
                "action": event["action"],
                "user_id": event["user_id"],
                "turn_id": event["turn_id"],
                "allowed": event["allowed"],
                "duration_ms": event.get("duration_ms"),
                "metadata": event.get("metadata", {}),
            }
        )


if __name__ == "__main__":
    main()