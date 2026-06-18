import json

from src.indexing.incremental_updater import run_incremental_update


def main() -> None:
    result = run_incremental_update()

    print("\n--- RESULTADO DE ACTUALIZACIÓN INCREMENTAL ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()