from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LatencyTelemetry:
    counters: Counter[str] = field(default_factory=Counter)
    latencies: dict[str, list[float]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def log(self, event: str, **fields: Any) -> None:
        print(
            json.dumps(
                {
                    "timestamp": utc_iso(),
                    "event": event,
                    **fields,
                },
                ensure_ascii=False,
            )
        )

    def increment(self, name: str, **dimensions: Any) -> None:
        self.counters[self._key(name, dimensions)] += 1

    def observe(self, name: str, value_ms: float, **dimensions: Any) -> None:
        self.latencies[self._key(name, dimensions)].append(value_ms)

    def summary(self) -> dict[str, Any]:
        latency_summary = {}

        for key, values in self.latencies.items():
            ordered = sorted(values)
            count = len(ordered)

            if count == 0:
                continue

            p95_index = max(0, int(count * 0.95) - 1)

            latency_summary[key] = {
                "count": count,
                "avg_ms": round(sum(ordered) / count, 2),
                "p95_ms": round(ordered[p95_index], 2),
                "max_ms": round(max(ordered), 2),
            }

        return {
            "counters": dict(self.counters),
            "latencies": latency_summary,
        }

    def _key(self, name: str, dimensions: dict[str, Any]) -> str:
        if not dimensions:
            return name

        suffix = ",".join(
            f"{key}={value}"
            for key, value in sorted(dimensions.items())
        )

        return f"{name}|{suffix}"


class Stopwatch:
    def __init__(self) -> None:
        self.started = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self.started) * 1000