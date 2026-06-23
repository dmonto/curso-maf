from __future__ import annotations

from collections import Counter
from pathlib import Path

from src.retention.retention_runner import make_retention_plan


def main() -> None:
    input_path = Path("logs/interaction_audit.jsonl")
    decisions = make_retention_plan(input_path=input_path)

    if not decisions:
        print("No hay eventos para analizar.")
        return

    print(f"Eventos analizados: {len(decisions)}")

    by_policy = Counter(decision.policy_name for decision in decisions)
    by_action = Counter(decision.action.value for decision in decisions)
    expired = [decision for decision in decisions if decision.expired]

    print("\nPor política:")
    for policy, count in by_policy.items():
        print(f"- {policy}: {count}")

    print("\nPor acción:")
    for action, count in by_action.items():
        print(f"- {action}: {count}")

    print(f"\nEventos expirados: {len(expired)}")

    print("\nPrimeros eventos expirados:")
    for decision in expired[:10]:
        print(
            {
                "line": decision.line_number,
                "event_type": decision.event_type,
                "policy": decision.policy_name,
                "action": decision.action.value,
                "age_days": decision.age_days,
                "reason": decision.reason,
            }
        )


if __name__ == "__main__":
    main()