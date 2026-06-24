from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


logger = logging.getLogger("maf_lab")


def emit_event(event_name: str, **payload: Any) -> None:
    event = {
        "event_name": event_name,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **payload,
    }

    logger.info(json.dumps(event, ensure_ascii=False))