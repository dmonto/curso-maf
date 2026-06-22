from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum


class ModelKind(StrEnum):
    CHAT_COMPLETION = "chat_completion"
    RESPONSES = "responses"
    EMBEDDING = "embedding"


class ModelProvider(StrEnum):
    AZURE_OPENAI = "azure_openai"
    AZURE_FOUNDRY = "azure_foundry"


@dataclass(frozen=True)
class ModelRegistration:
    logical_name: str
    kind: ModelKind
    provider: ModelProvider
    deployment_name: str
    endpoint: str
    api_version: str | None = None
    description: str = ""


def _require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")

    return value


def build_model_registry() -> dict[str, ModelRegistration]:
    project_endpoint = _require_env("AZURE_AI_PROJECT_ENDPOINT")

    azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

    return {
        "chat_default": ModelRegistration(
            logical_name="chat_default",
            kind=ModelKind.CHAT_COMPLETION,
            provider=ModelProvider.AZURE_FOUNDRY,
            deployment_name=_require_env("AZURE_OPENAI_DEPLOYMENT_CHAT"),
            endpoint=project_endpoint,
            description="Modelo conversacional por defecto en Azure AI Foundry.",
        ),
        "chat_fast": ModelRegistration(
            logical_name="chat_fast",
            kind=ModelKind.CHAT_COMPLETION,
            provider=ModelProvider.AZURE_FOUNDRY,
            deployment_name=_require_env("AZURE_OPENAI_DEPLOYMENT_CHAT"),
            endpoint=project_endpoint,
            description="Modelo rápido para pruebas y agentes de laboratorio en Foundry.",
        ),
        "chat_quality": ModelRegistration(
            logical_name="chat_quality",
            kind=ModelKind.CHAT_COMPLETION,
            provider=ModelProvider.AZURE_FOUNDRY,
            deployment_name=_require_env("AZURE_OPENAI_DEPLOYMENT_CHAT"),
            endpoint=project_endpoint,
            description="Modelo de más calidad para respuestas críticas en Foundry.",
        ),
        "embedding_default": ModelRegistration(
            logical_name="embedding_default",
            kind=ModelKind.EMBEDDING,
            provider=ModelProvider.AZURE_OPENAI,
            deployment_name=_require_env("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT"),
            endpoint=azure_openai_endpoint,
            api_version=azure_openai_api_version,
            description="Modelo de embeddings en Azure OpenAI clásico.",
        ),
    }


def get_model_registration(logical_name: str) -> ModelRegistration:
    registry = build_model_registry()

    if logical_name not in registry:
        available = ", ".join(registry.keys())
        raise ValueError(
            f"Modelo lógico no registrado: {logical_name}. "
            f"Modelos disponibles: {available}"
        )

    return registry[logical_name]