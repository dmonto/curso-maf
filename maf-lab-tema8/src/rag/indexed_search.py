from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.rag.document_indexer import INDEX_PATH


TOKEN_PATTERN = re.compile(r"[a-záéíóúüñ0-9]{2,}", re.IGNORECASE)


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(text)}


def _load_index(index_path: Path = INDEX_PATH) -> dict[str, Any]:
    if not index_path.exists():
        raise FileNotFoundError(
            f"No existe el índice documental: {index_path}. "
            "Ejecuta primero python check_index_documents.py"
        )

    return json.loads(index_path.read_text(encoding="utf-8"))


def search_indexed_documents(
    query: str,
    domain: str | None = None,
    top_k: int = 3,
    index_path: Path = INDEX_PATH,
) -> list[dict[str, Any]]:
    payload = _load_index(index_path)
    query_terms = _tokenize(query)

    if not query_terms:
        return []

    results: list[dict[str, Any]] = []

    for chunk in payload["chunks"]:
        if domain and chunk["domain"].lower() != domain.lower():
            continue

        searchable_text = " ".join(
            [
                chunk["title"],
                chunk["domain"],
                chunk["source_id"],
                chunk["text"],
            ]
        )

        chunk_terms = _tokenize(searchable_text)
        overlap = query_terms.intersection(chunk_terms)

        if not overlap:
            continue

        score = len(overlap) / max(len(query_terms), 1)

        results.append(
            {
                "chunk_id": chunk["chunk_id"],
                "source_id": chunk["source_id"],
                "title": chunk["title"],
                "domain": chunk["domain"],
                "visibility": chunk["visibility"],
                "path": chunk["path"],
                "score": round(score, 3),
                "text": chunk["text"],
                "indexed_at_utc": chunk["indexed_at_utc"],
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)

    return results[:top_k]