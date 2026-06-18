from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DOCS_DIR = PROJECT_ROOT / "src" / "knowledge" / "raw"
INDEX_DIR = PROJECT_ROOT / "src" / "knowledge" / "index"
MANIFEST_PATH = INDEX_DIR / "documents_manifest.json"

SUPPORTED_EXTENSIONS = {".md", ".txt"}

UpdateStatus = Literal[
    "new",
    "unchanged",
    "text_changed",
    "metadata_changed",
    "deleted",
]


@dataclass(frozen=True)
class CurrentDocument:
    source_id: str
    path: str
    title: str
    domain: str
    tenant_id: str
    visibility: str
    classification: str
    allowed_groups: list[str]
    allowed_users: list[str]
    denied_groups: list[str]
    denied_users: list[str]
    owner: str
    text: str
    text_hash: str
    metadata_hash: str


@dataclass(frozen=True)
class ManifestDocument:
    source_id: str
    path: str
    text_hash: str
    metadata_hash: str
    chunk_ids: list[str]
    last_indexed_at_utc: str


@dataclass(frozen=True)
class DocumentUpdate:
    source_id: str
    status: UpdateStatus
    current: CurrentDocument | None
    previous: ManifestDocument | None
    reason: str


@dataclass(frozen=True)
class UpdatePlan:
    generated_at_utc: str
    updates: list[DocumentUpdate]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parse_csv_list(value: str | None) -> list[str]:
    if not value:
        return []

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def _parse_front_matter(raw_text: str) -> tuple[dict[str, str], str]:
    if not raw_text.startswith("---"):
        return {}, raw_text

    parts = raw_text.split("---", maxsplit=2)

    if len(parts) < 3:
        return {}, raw_text

    metadata_block = parts[1]
    body = parts[2].strip()

    metadata: dict[str, str] = {}

    for line in metadata_block.splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", maxsplit=1)
        metadata[key.strip().lower()] = value.strip()

    return metadata, body


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _metadata_hash(metadata: dict) -> str:
    stable = json.dumps(
        metadata,
        ensure_ascii=False,
        sort_keys=True,
    )

    return _sha256(stable)


def _discover_documents() -> list[Path]:
    if not RAW_DOCS_DIR.exists():
        raise FileNotFoundError(f"No existe el directorio {RAW_DOCS_DIR}")

    return sorted(
        path
        for path in RAW_DOCS_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def load_current_documents() -> dict[str, CurrentDocument]:
    current: dict[str, CurrentDocument] = {}

    for path in _discover_documents():
        raw_text = path.read_text(encoding="utf-8")
        metadata, body = _parse_front_matter(raw_text)
        clean_body = _clean_text(body)

        title = metadata.get("title") or path.stem.replace("_", " ").title()
        domain = metadata.get("domain") or "general"
        tenant_id = metadata.get("tenant_id") or "curso-maf"
        visibility = metadata.get("visibility") or "internal"
        classification = metadata.get("classification") or "internal"
        owner = metadata.get("owner") or "unknown"

        allowed_groups = _parse_csv_list(metadata.get("allowed_groups"))
        allowed_users = _parse_csv_list(metadata.get("allowed_users"))
        denied_groups = _parse_csv_list(metadata.get("denied_groups"))
        denied_users = _parse_csv_list(metadata.get("denied_users"))

        security_metadata = {
            "title": title,
            "domain": domain,
            "tenant_id": tenant_id,
            "visibility": visibility,
            "classification": classification,
            "allowed_groups": allowed_groups,
            "allowed_users": allowed_users,
            "denied_groups": denied_groups,
            "denied_users": denied_users,
            "owner": owner,
        }

        document = CurrentDocument(
            source_id=path.name,
            path=str(path.relative_to(PROJECT_ROOT)),
            title=title,
            domain=domain,
            tenant_id=tenant_id,
            visibility=visibility,
            classification=classification,
            allowed_groups=allowed_groups,
            allowed_users=allowed_users,
            denied_groups=denied_groups,
            denied_users=denied_users,
            owner=owner,
            text=clean_body,
            text_hash=_sha256(clean_body),
            metadata_hash=_metadata_hash(security_metadata),
        )

        current[document.source_id] = document

    return current


def load_previous_manifest() -> dict[str, ManifestDocument]:
    if not MANIFEST_PATH.exists():
        return {}

    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    documents = payload.get("documents", [])

    previous: dict[str, ManifestDocument] = {}

    for item in documents:
        previous[item["source_id"]] = ManifestDocument(
            source_id=item["source_id"],
            path=item["path"],
            text_hash=item["text_hash"],
            metadata_hash=item["metadata_hash"],
            chunk_ids=item.get("chunk_ids", []),
            last_indexed_at_utc=item.get("last_indexed_at_utc", ""),
        )

    return previous


def build_update_plan() -> UpdatePlan:
    current = load_current_documents()
    previous = load_previous_manifest()

    updates: list[DocumentUpdate] = []

    current_ids = set(current.keys())
    previous_ids = set(previous.keys())

    for source_id in sorted(current_ids):
        current_doc = current[source_id]
        previous_doc = previous.get(source_id)

        if previous_doc is None:
            updates.append(
                DocumentUpdate(
                    source_id=source_id,
                    status="new",
                    current=current_doc,
                    previous=None,
                    reason="El documento no aparece en el manifest anterior.",
                )
            )
            continue

        if current_doc.text_hash != previous_doc.text_hash:
            updates.append(
                DocumentUpdate(
                    source_id=source_id,
                    status="text_changed",
                    current=current_doc,
                    previous=previous_doc,
                    reason="El contenido textual ha cambiado.",
                )
            )
            continue

        if current_doc.metadata_hash != previous_doc.metadata_hash:
            updates.append(
                DocumentUpdate(
                    source_id=source_id,
                    status="metadata_changed",
                    current=current_doc,
                    previous=previous_doc,
                    reason="Han cambiado metadatos o permisos.",
                )
            )
            continue

        updates.append(
            DocumentUpdate(
                source_id=source_id,
                status="unchanged",
                current=current_doc,
                previous=previous_doc,
                reason="No hay cambios.",
            )
        )

    for source_id in sorted(previous_ids - current_ids):
        updates.append(
            DocumentUpdate(
                source_id=source_id,
                status="deleted",
                current=None,
                previous=previous[source_id],
                reason="El documento ya no existe en la carpeta raw.",
            )
        )

    return UpdatePlan(
        generated_at_utc=_utc_now(),
        updates=updates,
    )


def plan_to_dict(plan: UpdatePlan) -> dict:
    return {
        "generated_at_utc": plan.generated_at_utc,
        "updates": [
            {
                "source_id": update.source_id,
                "status": update.status,
                "reason": update.reason,
                "current": asdict(update.current) if update.current else None,
                "previous": asdict(update.previous) if update.previous else None,
            }
            for update in plan.updates
        ],
    }