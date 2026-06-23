
from __future__ import annotations

import json

from src.event_persistence.store import EventStore


store = EventStore(db_path="event_store.db")

for event in store.list_events():
    print(json.dumps(event, indent=2, ensure_ascii=False))