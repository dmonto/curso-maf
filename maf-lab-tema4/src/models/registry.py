from dataclasses import dataclass
from enum import StrEnum

from src.settings import get_settings


class ModelKind(StrEnum):
    CHAT_COMPLETION = "chat_completion"
    RESPONSES = "responses"
    EMBEDDING = "embedding"


@dataclass(frozen=True)
class ModelRegistration:
    logical_name: str
    kind: ModelKind
    deployment_name: str
    endpoint: str
    api_version: str
    description: str


def build_model_registry() -> dict[str, ModelRegistration]:
    settings = get_settings()

    return {
        "chat_default": ModelRegistration(
            logical_name="chat_default",
            kind=ModelKind.CHAT_COMPLETION,
            deployment_name=settings.chat_default_deployment,
            endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
            description="Modelo conversacional por defecto para agentes básicos.",
        ),
        "chat_fast": ModelRegistration(
            logical_name="chat_fast",
            kind=ModelKind.CHAT_COMPLETION,
            deployment_name=settings.chat_fast_deployment,
            endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
            description="Modelo rápido para tareas simples, pruebas y bajo coste.",
        ),
        "chat_quality": ModelRegistration(
            logical_name="chat_quality",
            kind=ModelKind.CHAT_COMPLETION,
            deployment_name=settings.chat_quality_deployment,
            endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
            description="Modelo de mayor calidad para tareas más exigentes.",
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