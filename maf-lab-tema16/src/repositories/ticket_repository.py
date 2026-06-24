from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from src.domain.support_models import SupportTicketDraft


class TicketDraftRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/ticket_drafts.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save_draft(self, draft: SupportTicketDraft) -> str:
        draft_id = f"draft-{uuid4().hex[:8]}"

        payload = {
            "draft_id": draft_id,
            **asdict(draft),
        }

        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")

        return draft_id