from __future__ import annotations

import asyncio
import random

from src.concurrency.schemas import SupportJob


SERVICES = ["vpn", "erp", "correo", "teams"]


async def publish_support_jobs(
    queue: asyncio.Queue[SupportJob],
    total_jobs: int = 12,
) -> None:
    for index in range(total_jobs):
        service = random.choice(SERVICES)

        if index % 4 == 0:
            job = SupportJob(
                service="vpn",
                priority="p1",
                description="Usuarios no pueden conectar desde remoto",
                affected_users=random.randint(20, 60),
            )
        else:
            job = SupportJob(
                service=service,
                priority=random.choice(["p2", "p3", "p4"]),
                description=f"Incidencia operativa en {service}",
                affected_users=random.randint(1, 15),
            )

        await queue.put(job)
        print(f"[producer] job publicado {job.job_id} servicio={job.service}")