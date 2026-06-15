from azure.identity import AzureCliCredential
from agent_framework.openai import OpenAIChatCompletionClient, OpenAIChatClient

from src.models.registry import ModelKind, get_model_registration


def create_chat_client(logical_name: str):
    registration = get_model_registration(logical_name)

    if registration.kind == ModelKind.CHAT_COMPLETION:
        return OpenAIChatCompletionClient(
            model=registration.deployment_name,
            azure_endpoint=registration.endpoint,
            api_version=registration.api_version,
            credential=AzureCliCredential(),
        )

    if registration.kind == ModelKind.RESPONSES:
        return OpenAIChatClient(
            model=registration.deployment_name,
            azure_endpoint=registration.endpoint,
            api_version=registration.api_version,
            credential=AzureCliCredential(),
        )

    raise ValueError(
        f"El modelo {logical_name} no es válido para chat. "
        f"Tipo recibido: {registration.kind}"
    )