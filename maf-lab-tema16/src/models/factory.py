from __future__ import annotations

from agent_framework.openai import OpenAIChatCompletionClient

from src.runtime.credential_factory import (
    create_azure_token_provider,
    get_azure_openai_api_key,
)
from src.settings import get_settings


def resolve_chat_deployment(model_alias: str) -> str:
    settings = get_settings()
    alias = model_alias.lower().strip()

    if alias == "chat_default":
        return settings.chat_default_deployment

    if alias == "chat_fast":
        return settings.chat_fast_deployment

    if alias == "chat_quality":
        return settings.chat_quality_deployment

    raise RuntimeError(
        f"Modelo lógico no soportado: {model_alias}"
    )


def create_chat_client(model_alias: str | None = None) -> OpenAIChatCompletionClient:
    settings = get_settings()

    selected_alias = model_alias or settings.default_chat_model
    deployment = resolve_chat_deployment(selected_alias)

    mode = settings.azure_auth_mode.lower().strip()

    if mode == "api_key":
        return OpenAIChatCompletionClient(
            model=deployment,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
            api_key=get_azure_openai_api_key(),
        )

    return OpenAIChatCompletionClient(
        model=deployment,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
        azure_ad_token_provider=create_azure_token_provider(),
    )