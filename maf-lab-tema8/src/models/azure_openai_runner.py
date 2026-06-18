from __future__ import annotations

from azure.identity import AzureCliCredential, get_bearer_token_provider
from openai import AzureOpenAI

from src.models.generation_profiles import GenerationProfile
from src.settings import get_settings


def build_azure_openai_client() -> AzureOpenAI:
    settings = get_settings()

    token_provider = get_bearer_token_provider(
        AzureCliCredential(),
        "https://cognitiveservices.azure.com/.default",
    )

    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
        azure_ad_token_provider=token_provider,
    )


def run_chat_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    profile: GenerationProfile,
) -> str:
    settings = get_settings()
    client = build_azure_openai_client()

    response = client.chat.completions.create(
        model=settings.azure_openai_chat_completion_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=profile.temperature,
        top_p=profile.top_p,
        max_tokens=profile.max_tokens,
        frequency_penalty=profile.frequency_penalty,
        presence_penalty=profile.presence_penalty,
    )

    message = response.choices[0].message.content

    if not message:
        return ""

    return message.strip()