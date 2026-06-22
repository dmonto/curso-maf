from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.identity import AzureCliCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv

from src.indexing.index_update_plan import (
    INDEX_DIR,
    MANIFEST_PATH,
    CurrentDocument,
    DocumentUpdate,
    build_update_plan,
    load_current_documents,
)
from src.vector.embeddings import embed_texts


load_dotenv()

LOCAL_INDEX_PATH = INDEX_DIR / "documents_index.json"

TOKEN_PATTERN = re.compile(r"[a-záéíóúüñ0-9]{2,}", re.IGNORECASE)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")

    return value


def _get_search_credential():
    api_key = os.getenv("AZURE_AI_SEARCH_API_KEY")

    if api_key:
        return AzureKeyCredential(api_key)

    return AzureCliCredential()


def _get_index_name() -> str:
    return os.getenv("AZURE_AI_SEARCH_INDEX_NAME", "maf-support-vector-index")


def _safe_key(value: str) -> str:
    raw = value.encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii")
    return encoded.rstrip("=")


def _estimate_tokens(text: str) -> int:
    return len(TOKEN_PATTERN.findall(text))


def _split_into_chunks(
    text: str,
    max_words: int = 90,
    overlap_words: int = 20,
) -> list[str]:
    words = text.split()

    if len(words) <= max_words:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(words):
        end = start + max_words
        chunks.append(" ".join(words[start:end]).strip())

        if end >= len(words):
            break

        start = max(0, end - overlap_words)

    return chunks


def build_chunks_for_document(document: CurrentDocument) -> list[dict[str, Any]]:
    text_chunks = _split_into_chunks(document.text)

    output: list[dict[str, Any]] = []

    for index, chunk_text in enumerate(text_chunks, start=1):
        chunk_id = f"{document.source_id}#chunk-{index}"

        output.append(
            {
                "id": _safe_key(chunk_id),
                "chunk_id": chunk_id,
                "source_id": document.source_id,
                "title": document.title,
                "domain": document.domain,
                "tenant_id": document.tenant_id,
                "visibility": document.visibility,
                "classification": document.classification,
                "allowed_groups": document.allowed_groups,
                "allowed_users": document.allowed_users,
                "denied_groups": document.denied_groups,
                "denied_users": document.denied_users,
                "owner": document.owner,
                "path": document.path,
                "chunk_index": index,
                "text_hash": document.text_hash,
                "metadata_hash": document.metadata_hash,
                "text": chunk_text,
                "token_count": _estimate_tokens(chunk_text),
                "indexed_at_utc": _utc_now(),
            }
        )

    return output


def attach_embeddings(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not chunks:
        return []

    texts = [chunk["text"] for chunk in chunks]
    vectors = embed_texts(texts)

    output: list[dict[str, Any]] = []

    for chunk, vector in zip(chunks, vectors, strict=True):
        enriched = dict(chunk)
        enriched["content_vector"] = vector
        output.append(enriched)

    return output


def get_search_client() -> SearchClient:
    endpoint = _require_env("AZURE_AI_SEARCH_ENDPOINT")
    index_name = _get_index_name()

    return SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=_get_search_credential(),
    )


def delete_chunks_from_search(chunk_ids: list[str]) -> int:
    if not chunk_ids:
        return 0

    search_client = get_search_client()

    documents = [
        {
            "id": _safe_key(chunk_id),
        }
        for chunk_id in chunk_ids
    ]

    results = search_client.delete_documents(documents=documents)

    succeeded = sum(1 for result in results if result.succeeded)
    return succeeded

INDEX_ALLOWED_FIELDS = {
    "id",
    "source_id",
    "chunk_id",
    "content",
    "title",
    "domain",
    "content_vector",
}

def sanitize_chunk_for_index(chunk: dict) -> dict:
    return {
        key: value
        for key, value in chunk.items()
        if key in INDEX_ALLOWED_FIELDS
    }

def merge_or_upload_chunks(chunks: list[dict[str, Any]]) -> int:
    if not chunks:
        return 0

    search_client = get_search_client()
    safe_chunks = [sanitize_chunk_for_index(chunk) for chunk in chunks]

    results = search_client.merge_or_upload_documents(documents=safe_chunks)    

    succeeded = sum(1 for result in results if result.succeeded)
    return succeeded


def metadata_update_documents(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Prepara documentos para actualizar metadatos sin recalcular embeddings.
    Requiere que los chunk_id antiguos sigan siendo válidos.
    """
    fields = [
        "id",
        "chunk_id",
        "source_id",
        "title",
        "domain",
        "tenant_id",
        "visibility",
        "classification",
        "allowed_groups",
        "allowed_users",
        "denied_groups",
        "denied_users",
        "owner",
        "path",
        "metadata_hash",
    ]

    return [
        {
            field: chunk[field]
            for field in fields
            if field in chunk
        }
        for chunk in chunks
    ]


def rebuild_local_index_file() -> dict[str, Any]:
    current_documents = load_current_documents()
    all_chunks: list[dict[str, Any]] = []

    for document in current_documents.values():
        all_chunks.extend(build_chunks_for_document(document))

    payload = {
        "generated_at_utc": _utc_now(),
        "documents_count": len(current_documents),
        "chunks_count": len(all_chunks),
        "chunks": all_chunks,
    }

    LOCAL_INDEX_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return payload


def write_manifest_from_current_documents() -> dict[str, Any]:
    current_documents = load_current_documents()
    documents_payload: list[dict[str, Any]] = []

    for document in current_documents.values():
        chunks = build_chunks_for_document(document)

        documents_payload.append(
            {
                "source_id": document.source_id,
                "path": document.path,
                "text_hash": document.text_hash,
                "metadata_hash": document.metadata_hash,
                "chunk_ids": [chunk["chunk_id"] for chunk in chunks],
                "last_indexed_at_utc": _utc_now(),
            }
        )

    manifest = {
        "generated_at_utc": _utc_now(),
        "embedding_model": os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", ""),
        "chunking_strategy": "words_90_overlap_20",
        "documents": sorted(
            documents_payload,
            key=lambda item: item["source_id"],
        ),
    }

    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return manifest


def apply_update(update: DocumentUpdate) -> dict[str, Any]:
    if update.status == "unchanged":
        return {
            "source_id": update.source_id,
            "status": update.status,
            "action": "skipped",
            "deleted": 0,
            "uploaded": 0,
        }

    if update.status == "deleted":
        previous_chunk_ids = update.previous.chunk_ids if update.previous else []
        deleted = delete_chunks_from_search(previous_chunk_ids)

        return {
            "source_id": update.source_id,
            "status": update.status,
            "action": "delete",
            "deleted": deleted,
            "uploaded": 0,
        }

    if update.status == "text_changed":
        previous_chunk_ids = update.previous.chunk_ids if update.previous else []
        deleted = delete_chunks_from_search(previous_chunk_ids)

        chunks = build_chunks_for_document(update.current)
        chunks_with_embeddings = attach_embeddings(chunks)
        uploaded = merge_or_upload_chunks(chunks_with_embeddings)

        return {
            "source_id": update.source_id,
            "status": update.status,
            "action": "delete_and_reupload",
            "deleted": deleted,
            "uploaded": uploaded,
        }

    if update.status == "new":
        chunks = build_chunks_for_document(update.current)
        chunks_with_embeddings = attach_embeddings(chunks)
        uploaded = merge_or_upload_chunks(chunks_with_embeddings)

        return {
            "source_id": update.source_id,
            "status": update.status,
            "action": "upload",
            "deleted": 0,
            "uploaded": uploaded,
        }

    if update.status == "metadata_changed":
        chunks = build_chunks_for_document(update.current)
        metadata_docs = metadata_update_documents(chunks)
        uploaded = merge_or_upload_chunks(metadata_docs)

        return {
            "source_id": update.source_id,
            "status": update.status,
            "action": "metadata_update",
            "deleted": 0,
            "uploaded": uploaded,
        }

    raise ValueError(f"Estado no soportado: {update.status}")


def run_incremental_update() -> dict[str, Any]:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    plan = build_update_plan()
    results: list[dict[str, Any]] = []

    for update in plan.updates:
        result = apply_update(update)
        results.append(result)

    local_index = rebuild_local_index_file()
    manifest = write_manifest_from_current_documents()

    return {
        "generated_at_utc": _utc_now(),
        "plan": [
            {
                "source_id": update.source_id,
                "status": update.status,
                "reason": update.reason,
            }
            for update in plan.updates
        ],
        "results": results,
        "local_index": {
            "documents_count": local_index["documents_count"],
            "chunks_count": local_index["chunks_count"],
        },
        "manifest": {
            "documents_count": len(manifest["documents"]),
            "embedding_model": manifest["embedding_model"],
            "chunking_strategy": manifest["chunking_strategy"],
        },
    }