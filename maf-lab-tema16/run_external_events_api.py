# run_external_events_api.py

from __future__ import annotations

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "src.external_events.api:app",
        host="127.0.0.1",
        port=8090,
        reload=False,
    )