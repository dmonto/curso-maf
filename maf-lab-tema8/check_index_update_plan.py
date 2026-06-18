from collections import Counter

from src.indexing.index_update_plan import build_update_plan


def main() -> None:
    plan = build_update_plan()

    print("\n--- PLAN DE ACTUALIZACIÓN ---")
    print(f"Generado en: {plan.generated_at_utc}")

    counter = Counter(update.status for update in plan.updates)

    print("\nResumen:")
    for status, count in sorted(counter.items()):
        print(f"- {status}: {count}")

    print("\nDetalle:")
    for update in plan.updates:
        print(f"\n{update.source_id}")
        print(f"  Estado: {update.status}")
        print(f"  Motivo: {update.reason}")

        if update.previous:
            print(f"  Chunks anteriores: {len(update.previous.chunk_ids)}")


if __name__ == "__main__":
    main()