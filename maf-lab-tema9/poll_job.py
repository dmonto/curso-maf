from __future__ import annotations

import sys
import time

import requests


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python poll_job.py <job_id>")

    job_id = sys.argv[1]

    while True:
        response = requests.get(f"http://127.0.0.1:8091/jobs/{job_id}", timeout=10)
        response.raise_for_status()

        job = response.json()
        status = job["status"]

        print(f"Estado: {status}")

        if status in {"succeeded", "failed", "cancelled"}:
            print(job)
            return

        time.sleep(2)


if __name__ == "__main__":
    main()