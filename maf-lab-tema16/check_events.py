from __future__ import annotations

import argparse
import json

from src.events.local_event_bus import LocalEventBus


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("correlation_id", help="Correlation ID a consultar")
    args = parser.parse_args()

    event_bus = LocalEventBus()
    events = event_bus.read_by_correlation_id(args.correlation_id)

    print(f"\n--- EVENTOS PARA {args.correlation_id} ---")

    for event in events:
        print(
            json.dumps(
                event.to_dict(),
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()