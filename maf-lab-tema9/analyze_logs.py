import json
from collections import Counter
from pathlib import Path


LOG_FILE = Path("logs/maf_lab.jsonl")


def main() -> None:
    if not LOG_FILE.exists():
        print(f"No existe {LOG_FILE}. Ejecuta primero chat_cli.py.")
        return

    events = []

    with LOG_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))

    print(f"Eventos totales: {len(events)}")

    by_event = Counter(event.get("event") for event in events)
    print("\nEventos por tipo:")
    for event_name, count in by_event.most_common():
        print(f"  {event_name}: {count}")

    errors = [event for event in events if event.get("level") == "ERROR"]
    print(f"\nErrores: {len(errors)}")

    slow_runs = [
        event
        for event in events
        if event.get("event") == "agent.run.completed"
        and event.get("duration_ms", 0) > 3000
    ]

    print(f"Ejecuciones de agente > 3000 ms: {len(slow_runs)}")

    tool_events = [
        event
        for event in events
        if event.get("event") == "tool.completed"
    ]

    by_tool = Counter(event.get("tool_name") for event in tool_events)
    print("\nTools completadas:")
    for tool_name, count in by_tool.most_common():
        print(f"  {tool_name}: {count}")


if __name__ == "__main__":
    main()