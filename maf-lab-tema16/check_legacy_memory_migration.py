from __future__ import annotations

from pathlib import Path

from src.memory.legacy_memory_migrator import migrate_legacy_memory, write_migration_report
from src.memory.migrated_memory_store import MigratedMemoryStore, render_context_for_prompt


LEGACY_PATH = Path("src/legacy/legacy_memory_dump.json")
REPORT_PATH = Path("data/legacy_memory_migration_report.json")


def main() -> None:
    migrated = migrate_legacy_memory(LEGACY_PATH)

    print("\n--- REGISTROS MIGRADOS ---")
    for record in migrated:
        print(f"\nOrigen: {record.source_record_id}")
        print(f"Destino: {record.target}")
        print(f"Clave: {record.key}")
        print(f"Redactado: {record.redacted}")
        print(f"Motivo: {record.reason}")
        print(f"Valor: {record.value}")

    write_migration_report(migrated, REPORT_PATH)

    store = MigratedMemoryStore()
    store.save_many(migrated)

    context = store.build_context_for_agent(
        user_id="u-001",
        session_id="s-100",
    )

    print("\n--- CONTEXTO CONTROLADO PARA AGENTE ---")
    print(render_context_for_prompt(context))

    print(f"\nInforme escrito en: {REPORT_PATH}")


if __name__ == "__main__":
    main()