from __future__ import annotations

from pathlib import Path

from src.retention.retention_runner import apply_retention


def main() -> None:
    decisions = apply_retention(
        input_path=Path("logs/interaction_audit.jsonl"),
        output_path=Path("logs/interaction_audit.retained.jsonl"),
        archive_path=Path("logs/archive/interaction_audit.archive.jsonl"),
        purge_log_path=Path("logs/retention_purge_log.jsonl"),
        dry_run=False,
    )

    print(f"Decisiones procesadas: {len(decisions)}")
    print("Salida retenida: logs/interaction_audit.retained.jsonl")
    print("Archivo compactado: logs/archive/interaction_audit.archive.jsonl")
    print("Log de purga: logs/retention_purge_log.jsonl")
    print("Backup del original: logs/interaction_audit.jsonl.bak")


if __name__ == "__main__":
    main()