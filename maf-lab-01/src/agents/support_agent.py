from azure.identity import AzureCliCredential
from agent_framework.openai import OpenAIChatCompletionClient

from src.settings import get_settings


def build_support_agent():
    settings = get_settings()

    client = OpenAIChatCompletionClient(
        model=settings.azure_openai_chat_completion_model,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
        credential=AzureCliCredential(),
    )

    return client.as_agent(
        name="maf_setup_agent",
        instructions=(
            "Eres un agente técnico de soporte para validar la configuración "
            "inicial de un proyecto MAF en Python. Responde de forma breve, "
            "clara y orientada a diagnóstico."
        ),
    )