from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Telemetry:
    counters: Counter[str] = field(default_factory=Counter)
    latencies_ms: dict[str, list[float]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def log(self, event_name: str, **fields: Any) -> None:
        record = {
            "timestamp": utc_iso(),
            "event": event_name,
            **fields,
        }

        print(json.dumps(record, ensure_ascii=False))

    def increment(self, metric_name: str, value: int = 1, **dimensions: Any) -> None:
        key = self._metric_key(metric_name, dimensions)
        self.counters[key] += value

    def observe_latency(
        self,
        metric_name: str,
        latency_ms: float,
        **dimensions: Any,
    ) -> None:
        key = self._metric_key(metric_name, dimensions)
        self.latencies_ms[key].append(latency_ms)

    @contextmanager
    def span(self, span_name: str, **fields: Any) -> Iterator[None]:
        started = time.perf_counter()

        self.log(f"{span_name}_started", **fields)

        try:
            yield
            status = "success"
            error = None
        except Exception as exc:
            status = "error"
            error = str(exc)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000

            self.observe_latency(
                f"{span_name}_latency_ms",
                elapsed_ms,
                status=status,
            )

            self.log(
                f"{span_name}_finished",
                status=status,
                latency_ms=round(elapsed_ms, 2),
                error=error,
                **fields,
            )

    def summary(self) -> dict[str, Any]:
        latency_summary = {}

        for key, values in self.latencies_ms.items():
            if not values:
                continue

            sorted_values = sorted(values)
            count = len(sorted_values)
            p95_index = max(0, int(count * 0.95) - 1)

            latency_summary[key] = {
                "count": count,
                "avg_ms": round(sum(sorted_values) / count, 2),
                "p95_ms": round(sorted_values[p95_index], 2),
                "max_ms": round(max(sorted_values), 2),
            }

        return {
            "counters": dict(self.counters),
            "latencies": latency_summary,
        }

    def _metric_key(self, metric_name: str, dimensions: dict[str, Any]) -> str:
        if not dimensions:
            return metric_name

        suffix = ",".join(
            f"{key}={value}"
            for key, value in sorted(dimensions.items())
        )

        return f"{metric_name}|{suffix}"