from __future__ import annotations

import re
from pathlib import Path

from src.connectors.models import CorporateDocument


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPORATE_RAW_DIR = PROJECT_ROOT / "src" / "knowledge" / "raw"


def _safe_filename(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9_\-\.]+", "_", value)
    value = value.strip("_")

    return value or "document.md"


def _csv(values: list[str]) -> str:
    return ",".join(values)


def document_to_markdown(document: CorporateDocument) -> str:
    return f"""---
title: {document.title}
domain: {document.domain}
tenant_id: {document.tenant_id}
visibility: {document.visibility}
classification: {document.classification}
allowed_groups: {_csv(document.allowed_groups)}
allowed_users: {_csv(document.allowed_users)}
denied_groups: {_csv(document.denied_groups)}
denied_users: {_csv(document.denied_users)}
owner: {document.owner}
source_type: {document.source_type}
source_id: {document.source_id}
source_path: {document.path}
source_last_modified_utc: {document.source_last_modified_utc or ""}
---

# {document.title}

{document.text}
"""


def sync_documents_to_raw_folder(
    documents: list[CorporateDocument],
    subfolder: str = "corporate",
) -> list[Path]:
    target_dir = CORPORATE_RAW_DIR / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)

    written_paths: list[Path] = []

    for document in documents:
        filename_base = _safe_filename(document.source_id)
        filename = f"{filename_base}.md"

        path = target_dir / filename
        path.write_text(
            document_to_markdown(document),
            encoding="utf-8",
        )

        written_paths.append(path)

    return written_paths