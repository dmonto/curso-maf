from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv("..\\..\\.env")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Falta la variable de entorno {name}. "
            "Revisa el archivo .env o la configuración de la terminal."
        )
    return value


@dataclass(frozen=True)
class Settings:
    azure_openai_endpoint: str
    azure_openai_chat_completion_model: str
    azure_openai_api_version: str


def get_settings() -> Settings:
    return Settings(
        azure_openai_endpoint=require_env("AZURE_OPENAI_ENDPOINT").rstrip("/"),
        azure_openai_chat_completion_model=require_env(
            "AZURE_OPENAI_DEPLOYMENT_CHAT"
        ),
        azure_openai_api_version=os.getenv(
            "AZURE_OPENAI_API_VERSION",
            "2024-10-21",
        ),
    )