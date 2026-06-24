from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DOCS_DIR = PROJECT_ROOT / "src" / "knowledge" / "raw"
INDEX_DIR = PROJECT_ROOT / "src" / "knowledge" / "index"

INDEX_PATH = INDEX_DIR / "documents_index.json"
MANIFEST_PATH = INDEX_DIR / "documents_manifest.json"

SUPPORTED_EXTENSIONS = {".md", ".txt"}

TOKEN_PATTERN = re.compile(r"[a-záéíóúüñ0-9]{2,}", re.IGNORECASE)


@dataclass(frozen=True)
class SourceDocument:
    source_id: str
    path: str
    title: str
    domain: str
    visibility: str
    text: str
    content_hash: str


@dataclass(frozen=True)
class IndexedChunk:
    chunk_id: str
    source_id: str
    title: str
    domain: str
    visibility: str
    path: str
    chunk_index: int
    content_hash: str
    text: str
    token_count: int
    indexed_at_utc: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _estimate_tokens(text: str) -> int:
    return len(TOKEN_PATTERN.findall(text))


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


def _load_source_document(path: Path) -> SourceDocument:
    raw_text = path.read_text(encoding="utf-8")
    metadata, body = _parse_front_matter(raw_text)
    clean_body = _clean_text(body)

    title = metadata.get("title") or path.stem.replace("_", " ").title()
    domain = metadata.get("domain") or "general"
    visibility = metadata.get("visibility") or "internal"

    return SourceDocument(
        source_id=path.name,
        path=str(path.relative_to(PROJECT_ROOT)),
        title=title,
        domain=domain,
        visibility=visibility,
        text=clean_body,
        content_hash=_sha256(clean_body),
    )


def _split_into_chunks(text: str, max_words: int = 90, overlap_words: int = 20) -> list[str]:
    words = text.split()

    if len(words) <= max_words:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(words):
        end = start + max_words
        chunk = " ".join(words[start:end]).strip()
        chunks.append(chunk)

        if end >= len(words):
            break

        start = max(0, end - overlap_words)

    return chunks


def _discover_documents(raw_docs_dir: Path) -> list[Path]:
    if not raw_docs_dir.exists():
        raise FileNotFoundError(f"No existe el directorio de documentos: {raw_docs_dir}")

    paths = [
        path
        for path in raw_docs_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    return sorted(paths)


def build_document_index(
    raw_docs_dir: Path = RAW_DOCS_DIR,
    index_path: Path = INDEX_PATH,
    manifest_path: Path = MANIFEST_PATH,
) -> dict[str, Any]:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    document_paths = _discover_documents(raw_docs_dir)
    indexed_at = _utc_now()

    source_documents = [_load_source_document(path) for path in document_paths]

    chunks: list[IndexedChunk] = []

    for source_doc in source_documents:
        text_chunks = _split_into_chunks(source_doc.text)

        for index, chunk_text in enumerate(text_chunks, start=1):
            chunks.append(
                IndexedChunk(
                    chunk_id=f"{source_doc.source_id}#chunk-{index}",
                    source_id=source_doc.source_id,
                    title=source_doc.title,
                    domain=source_doc.domain,
                    visibility=source_doc.visibility,
                    path=source_doc.path,
                    chunk_index=index,
                    content_hash=source_doc.content_hash,
                    text=chunk_text,
                    token_count=_estimate_tokens(chunk_text),
                    indexed_at_utc=indexed_at,
                )
            )

    index_payload = {
        "generated_at_utc": indexed_at,
        "documents_count": len(source_documents),
        "chunks_count": len(chunks),
        "chunks": [asdict(chunk) for chunk in chunks],
    }

    manifest_payload = {
        "generated_at_utc": indexed_at,
        "documents": [
            {
                "source_id": document.source_id,
                "path": document.path,
                "title": document.title,
                "domain": document.domain,
                "visibility": document.visibility,
                "content_hash": document.content_hash,
            }
            for document in source_documents
        ],
    }

    index_path.write_text(
        json.dumps(index_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest_path.write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return index_payload