from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")

    return value


@dataclass(frozen=True)
class Settings:
    app_env: str
    azure_auth_mode: str

    azure_openai_endpoint: str
    azure_openai_api_version: str
    azure_openai_api_key: str | None
    chat_default_deployment: str
    chat_fast_deployment: str
    chat_quality_deployment: str
    default_chat_model: str

    support_service_base_url: str
    support_service_api_key: str
    support_service_timeout_seconds: float


def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "local"),
        azure_auth_mode=os.getenv("AZURE_AUTH_MODE", "azure_cli"),

        azure_openai_endpoint=require_env("AZURE_AI_FOUNDRY_ENDPOINT").rstrip("/"),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),

        chat_default_deployment=require_env("AZURE_OPENAI_CHAT_DEFAULT_DEPLOYMENT"),
        chat_fast_deployment=require_env("AZURE_OPENAI_CHAT_FAST_DEPLOYMENT"),
        chat_quality_deployment=require_env("AZURE_OPENAI_CHAT_QUALITY_DEPLOYMENT"),
        default_chat_model=os.getenv("DEFAULT_CHAT_MODEL", "chat_fast"),

        support_service_base_url=os.getenv("SUPPORT_SERVICE_BASE_URL",  "http://127.0.0.1:8010",),
        support_service_api_key=os.getenv("SUPPORT_SERVICE_API_KEY", "dev-support-key"),
        support_service_timeout_seconds=float(os.getenv("SUPPORT_SERVICE_TIMEOUT_SECONDS", "5")
),
    )