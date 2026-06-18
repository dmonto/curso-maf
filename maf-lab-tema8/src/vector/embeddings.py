from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Literal

from azure.identity import AzureCliCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI, AzureOpenAI


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH, override=True)

AZURE_OPENAI_SCOPE = "https://cognitiveservices.azure.com/.default"
AZURE_AI_FOUNDRY_SCOPE = "https://ai.azure.com/.default"

EmbeddingProvider = Literal["foundry", "azure_openai"]


def _require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")

    return value


def _get_embedding_provider() -> EmbeddingProvider:
    provider = os.getenv("EMBEDDING_PROVIDER", "foundry").strip().lower()

    if provider not in {"foundry", "azure_openai"}:
        raise RuntimeError(
            "EMBEDDING_PROVIDER debe ser 'foundry' o 'azure_openai'. "
            f"Valor recibido: {provider}"
        )

    return provider  # type: ignore[return-value]


def _get_token_provider(scope: str):
    return get_bearer_token_provider(
        AzureCliCredential(),
        scope,
    )


@lru_cache(maxsize=1)
def _create_foundry_embedding_client() -> OpenAI:
    project_endpoint = _require_env("AZURE_AI_PROJECT_ENDPOINT").rstrip("/")
    base_url = f"{project_endpoint}/openai/v1/"

    token_provider = _get_token_provider(AZURE_AI_FOUNDRY_SCOPE)

    print("DEBUG embeddings")
    print("ENV_PATH:", ENV_PATH)
    print("PROVIDER: foundry")
    print("PROJECT_ENDPOINT:", project_endpoint)
    print("BASE_URL:", base_url)
    print("TOKEN_SCOPE:", AZURE_AI_FOUNDRY_SCOPE)
    print("DEPLOYMENT:", os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT"))

    return OpenAI(
        base_url=base_url,
        api_key=token_provider,
    )


@lru_cache(maxsize=1)
def _create_foundry_embedding_client() -> OpenAI:
    foundry_endpoint = _require_env("AZURE_AI_FOUNDRY_ENDPOINT").rstrip("/")

    # Endpoint OpenAI-compatible del recurso Foundry.
    # Ojo: no usa /api/projects/{project}
    base_url = f"{foundry_endpoint}/openai/v1/"

    token_provider = _get_token_provider(AZURE_AI_FOUNDRY_SCOPE)

    print("DEBUG embeddings")
    print("ENV_PATH:", ENV_PATH)
    print("PROVIDER: foundry")
    print("FOUNDRY_ENDPOINT:", foundry_endpoint)
    print("BASE_URL:", base_url)
    print("TOKEN_SCOPE:", AZURE_AI_FOUNDRY_SCOPE)
    print("DEPLOYMENT:", os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT"))

    return OpenAI(
        base_url=base_url,
        api_key=token_provider,
    )


def create_embedding_client():
    provider = _get_embedding_provider()

    if provider == "foundry":
        return _create_foundry_embedding_client()

    return _create_azure_openai_embedding_client()


def _get_embedding_deployment() -> str:
    provider = _get_embedding_provider()

    if provider == "foundry":
        return _require_env("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT")

    return _require_env("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT")


def embed_text(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("No se puede generar embedding de un texto vacío.")

    client = create_embedding_client()
    deployment = _get_embedding_deployment()

    response = client.embeddings.create(
        model=deployment,
        input=text,
    )

    return response.data[0].embedding


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    clean_texts = [text for text in texts if text and text.strip()]

    if not clean_texts:
        return []

    client = create_embedding_client()
    deployment = _get_embedding_deployment()

    response = client.embeddings.create(
        model=deployment,
        input=clean_texts,
    )

    return [item.embedding for item in response.data]