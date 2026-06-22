from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.latency_control.event import Severity


LatencyMode = Literal["normal", "fast", "fallback"]


@dataclass(frozen=True)
class LatencyPolicy:
    max_total_ms: int
    agent_timeout_ms: int
    max_prompt_events: int
    allow_tools: bool
    mode: LatencyMode


def policy_for_event(severity: Severity, queue_lag_ms: float) -> LatencyPolicy:
    if severity == "critical":
        return LatencyPolicy(
            max_total_ms=10_000,
            agent_timeout_ms=6_000,
            max_prompt_events=8,
            allow_tools=True,
            mode="normal",
        )

    if severity == "high":
        return LatencyPolicy(
            max_total_ms=15_000,
            agent_timeout_ms=8_000,
            max_prompt_events=10,
            allow_tools=True,
            mode="normal",
        )

    if queue_lag_ms > 20_000:
        return LatencyPolicy(
            max_total_ms=5_000,
            agent_timeout_ms=2_000,
            max_prompt_events=3,
            allow_tools=False,
            mode="fallback",
        )

    if queue_lag_ms > 8_000:
        return LatencyPolicy(
            max_total_ms=8_000,
            agent_timeout_ms=3_000,
            max_prompt_events=5,
            allow_tools=False,
            mode="fast",
        )

    return LatencyPolicy(
        max_total_ms=12_000,
        agent_timeout_ms=5_000,
        max_prompt_events=6,
        allow_tools=False,
        mode="fast",
    )