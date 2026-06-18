from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.identity import AzureCliCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv

from src.vector.embeddings import embed_text, embed_texts


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_INDEX_PATH = PROJECT_ROOT / "src" / "knowledge" / "index" / "documents_index.json"


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


def create_search_index(vector_dimensions: int) -> None:
    endpoint = _require_env("AZURE_AI_SEARCH_ENDPOINT")
    index_name = _get_index_name()

    index_client = SearchIndexClient(
        endpoint=endpoint,
        credential=_get_search_credential(),
    )

    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SimpleField(
            name="chunk_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="source_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchableField(
            name="title",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="domain",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="visibility",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="path",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchableField(
            name="text",
            type=SearchFieldDataType.String,
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=vector_dimensions,
            vector_search_profile_name="vector-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-config",
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="vector-profile",
                algorithm_configuration_name="hnsw-config",
            )
        ],
    )

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
    )

    index_client.create_or_update_index(index)
    print(f"Índice creado o actualizado: {index_name}")


def _load_local_chunks() -> list[dict[str, Any]]:
    if not LOCAL_INDEX_PATH.exists():
        raise FileNotFoundError(
            f"No existe {LOCAL_INDEX_PATH}. "
            "Ejecuta primero la indexación documental local."
        )

    payload = json.loads(LOCAL_INDEX_PATH.read_text(encoding="utf-8"))
    return payload["chunks"]


def build_vector_documents() -> list[dict[str, Any]]:
    chunks = _load_local_chunks()

    texts = [chunk["text"] for chunk in chunks]
    vectors = embed_texts(texts)

    documents: list[dict[str, Any]] = []

    for chunk, vector in zip(chunks, vectors, strict=True):
        documents.append(
            {
                "id": _safe_key(chunk["chunk_id"]),
                "chunk_id": chunk["chunk_id"],
                "source_id": chunk["source_id"],
                "title": chunk["title"],
                "domain": chunk["domain"],
                "visibility": chunk["visibility"],
                "path": chunk["path"],
                "text": chunk["text"],
                "content_vector": vector,
            }
        )

    return documents


def upload_vector_documents(documents: list[dict[str, Any]]) -> None:
    endpoint = _require_env("AZURE_AI_SEARCH_ENDPOINT")
    index_name = _get_index_name()

    search_client = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=_get_search_credential(),
    )

    result = search_client.upload_documents(documents=documents)

    succeeded = sum(1 for item in result if item.succeeded)
    print(f"Documentos subidos correctamente: {succeeded}/{len(documents)}")


def rebuild_vector_index() -> None:
    chunks = _load_local_chunks()

    if not chunks:
        raise RuntimeError("No hay chunks en el índice local.")

    sample_vector = embed_text(chunks[0]["text"])
    vector_dimensions = len(sample_vector)

    print(f"Dimensión detectada del embedding: {vector_dimensions}")

    create_search_index(vector_dimensions=vector_dimensions)

    documents = build_vector_documents()
    upload_vector_documents(documents)


def vector_search(
    query: str,
    domain: str | None = None,
    top_k: int = 3,
    hybrid: bool = True,
) -> list[dict[str, Any]]:
    endpoint = _require_env("AZURE_AI_SEARCH_ENDPOINT")
    index_name = _get_index_name()

    query_vector = embed_text(query)

    search_client = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=_get_search_credential(),
    )

    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top_k,
        fields="content_vector",
    )

    filter_expression = None

    if domain:
        filter_expression = f"domain eq '{domain}'"

    results = search_client.search(
        search_text=query if hybrid else None,
        vector_queries=[vector_query],
        filter=filter_expression,
        top=top_k,
        select=[
            "chunk_id",
            "source_id",
            "title",
            "domain",
            "visibility",
            "path",
            "text",
        ],
    )

    output: list[dict[str, Any]] = []

    for result in results:
        output.append(
            {
                "chunk_id": result["chunk_id"],
                "source_id": result["source_id"],
                "title": result["title"],
                "domain": result["domain"],
                "visibility": result["visibility"],
                "path": result["path"],
                "score": result.get("@search.score"),
                "text": result["text"],
            }
        )

    return output