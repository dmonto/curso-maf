from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from dataclasses import dataclass, field


@dataclass
class ServiceState:
    total_jobs: int = 0
    affected_users: int = 0
    last_priority: str | None = None
    last_summary: str | None = None


class ConcurrentStateStore:
    def __init__(self) -> None:
        self._states: dict[str, ServiceState] = defaultdict(ServiceState)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._stats: Counter[str] = Counter()
        self._stats_lock = asyncio.Lock()

    async def update_service_state(
        self,
        service: str,
        priority: str,
        affected_users: int,
        summary: str,
    ) -> None:
        lock = self._locks[service]

        async with lock:
            state = self._states[service]
            state.total_jobs += 1
            state.affected_users += affected_users
            state.last_priority = priority
            state.last_summary = summary

    async def increment_stat(self, name: str) -> None:
        async with self._stats_lock:
            self._stats[name] += 1

    async def snapshot(self) -> dict:
        async with self._stats_lock:
            stats = dict(self._stats)

        services = {
            service: {
                "total_jobs": state.total_jobs,
                "affected_users": state.affected_users,
                "last_priority": state.last_priority,
                "last_summary": state.last_summary,
            }
            for service, state in self._states.items()
        }

        return {
            "stats": stats,
            "services": services,
        }