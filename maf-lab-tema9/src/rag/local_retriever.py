from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


TOKEN_PATTERN = re.compile(r"[a-záéíóúüñ0-9]{3,}", re.IGNORECASE)

KNOWLEDGE_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "support_docs.json"


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_id: str
    title: str
    text: str


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    source_id: str
    title: str
    score: float
    text: str


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(text)}


def _load_documents() -> list[dict[str, Any]]:
    if not KNOWLEDGE_PATH.exists():
        raise FileNotFoundError(f"No existe la base documental: {KNOWLEDGE_PATH}")

    with KNOWLEDGE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _chunk_text(text: str, max_words: int = 80, overlap: int = 20) -> list[str]:
    words = text.split()

    if len(words) <= max_words:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(words):
        end = start + max_words
        chunks.append(" ".join(words[start:end]))

        if end >= len(words):
            break

        start = max(0, end - overlap)

    return chunks


def build_chunks() -> list[Chunk]:
    documents = _load_documents()
    chunks: list[Chunk] = []

    for doc in documents:
        for index, chunk_text in enumerate(_chunk_text(doc["text"])):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc['source_id']}#chunk-{index + 1}",
                    source_id=doc["source_id"],
                    title=doc["title"],
                    text=chunk_text,
                )
            )

    return chunks


def search_knowledge(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    query_terms = _tokenize(query)

    if not query_terms:
        return []

    results: list[SearchResult] = []

    for chunk in build_chunks():
        chunk_terms = _tokenize(chunk.title + " " + chunk.text)
        overlap = query_terms.intersection(chunk_terms)

        if not overlap:
            continue

        score = len(overlap) / max(len(query_terms), 1)

        results.append(
            SearchResult(
                chunk_id=chunk.chunk_id,
                source_id=chunk.source_id,
                title=chunk.title,
                score=round(score, 3),
                text=chunk.text,
            )
        )

    results.sort(key=lambda item: item.score, reverse=True)

    return [asdict(result) for result in results[:top_k]]