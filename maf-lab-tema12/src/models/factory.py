from __future__ import annotations

from azure.identity import AzureCliCredential

from agent_framework.foundry import FoundryChatClient
from agent_framework.openai import OpenAIChatCompletionClient, OpenAIChatClient

from src.models.registry import (
    ModelKind,
    ModelProvider,
    get_model_registration,
)


def create_chat_client(logical_name: str):
    registration = get_model_registration(logical_name)

    print("DEBUG model factory")
    print("logical_name:", logical_name)
    print("kind:", registration.kind)
    print("provider:", registration.provider)
    print("deployment:", registration.deployment_name)
    print("endpoint:", registration.endpoint)
    print("api_version:", registration.api_version)

    credential = AzureCliCredential()

    if registration.kind not in {
        ModelKind.CHAT_COMPLETION,
        ModelKind.RESPONSES,
    }:
        raise ValueError(
            f"El modelo {logical_name} no es válido para chat. "
            f"Tipo recibido: {registration.kind}"
        )

    if registration.provider == ModelProvider.AZURE_FOUNDRY:
        return FoundryChatClient(
            project_endpoint=registration.endpoint,
            model=registration.deployment_name,
            credential=credential,
        )

    if registration.provider == ModelProvider.AZURE_OPENAI:
        if registration.kind == ModelKind.CHAT_COMPLETION:
            return OpenAIChatCompletionClient(
                model=registration.deployment_name,
                azure_endpoint=registration.endpoint,
                api_version=registration.api_version,
                credential=credential,
            )

        if registration.kind == ModelKind.RESPONSES:
            return OpenAIChatClient(
                model=registration.deployment_name,
                azure_endpoint=registration.endpoint,
                api_version=registration.api_version,
                credential=credential,
            )

    raise ValueError(
        f"Provider no soportado para {logical_name}: {registration.provider}"
    )