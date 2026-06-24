from __future__ import annotations

import os

from azure.core.credentials import TokenCredential
from azure.identity import (
    AzureCliCredential,
    DefaultAzureCredential,
    ManagedIdentityCredential,
    get_bearer_token_provider,
)

from src.settings import get_settings


AZURE_OPENAI_SCOPE = "https://cognitiveservices.azure.com/.default"


def create_azure_credential() -> TokenCredential:
    """
    Crea credenciales Entra ID para modos basados en token.

    No soporta api_key porque una API Key no es un TokenCredential.
    """
    settings = get_settings()
    mode = settings.azure_auth_mode.lower().strip()

    if mode == "azure_cli":
        return AzureCliCredential()

    if mode == "managed_identity":
        client_id = os.getenv("AZURE_CLIENT_ID")

        if client_id:
            return ManagedIdentityCredential(client_id=client_id)

        return ManagedIdentityCredential()

    if mode == "default":
        return DefaultAzureCredential(
            exclude_interactive_browser_credential=True,
        )

    if mode == "api_key":
        raise RuntimeError(
            "AZURE_AUTH_MODE=api_key no usa TokenCredential. "
            "Pasa AZURE_OPENAI_API_KEY directamente al cliente del modelo."
        )

    raise RuntimeError(
        "AZURE_AUTH_MODE debe ser azure_cli, default, managed_identity o api_key"
    )


def create_azure_token_provider():
    """
    Crea un token provider compatible con Azure OpenAI.

    Se usa solo cuando AZURE_AUTH_MODE no es api_key.
    """
    credential = create_azure_credential()

    return get_bearer_token_provider(
        credential,
        AZURE_OPENAI_SCOPE,
    )


def get_azure_openai_api_key() -> str:
    """
    Devuelve la API Key para Docker local o escenarios simples de laboratorio.
    """
    settings = get_settings()

    api_key = getattr(settings, "azure_openai_api_key", None)

    if not api_key:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "AZURE_OPENAI_API_KEY es obligatoria cuando AZURE_AUTH_MODE=api_key"
        )

    return api_key