

from __future__ import annotations

from dataclasses import asdict
from threading import Lock

from src.async_jobs.schemas import AsyncJob, JobStatus, utc_now


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, AsyncJob] = {}
        self._lock = Lock()

    def create_job(self, job_type: str, payload: dict) -> AsyncJob:
        job = AsyncJob(job_type=job_type, payload=payload)

        with self._lock:
            self._jobs[job.job_id] = job

        return job

    def get_job(self, job_id: str) -> AsyncJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        result: dict | None = None,
        error: str | None = None,
    ) -> AsyncJob:
        with self._lock:
            job = self._jobs[job_id]
            job.status = status
            job.updated_at = utc_now()

            if result is not None:
                job.result = result

            if error is not None:
                job.error = error

            return job

    def increment_attempts(self, job_id: str) -> int:
        with self._lock:
            job = self._jobs[job_id]
            job.attempts += 1
            job.updated_at = utc_now()
            return job.attempts

    def as_dict(self, job_id: str) -> dict | None:
        job = self.get_job(job_id)

        if not job:
            return None

        return asdict(job)