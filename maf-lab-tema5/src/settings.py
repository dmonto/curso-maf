from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv("..\\.env")


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
    azure_openai_api_version: str
    azure_openai_chat_completion_model: str

    chat_default_deployment: str
    chat_fast_deployment: str
    chat_quality_deployment: str   

    default_chat_model: str

    agent_prompt_version: str
    agent_prompt_profile: str
    agent_environment: str
    agent_allowed_services: str

def get_settings() -> Settings:
    return Settings(
        azure_openai_endpoint=require_env("AZURE_OPENAI_ENDPOINT").rstrip("/"),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        azure_openai_chat_completion_model=require_env("AZURE_OPENAI_CHAT_COMPLETION_MODEL"),
        
        chat_default_deployment=require_env("AZURE_OPENAI_CHAT_DEFAULT_DEPLOYMENT"),
        chat_fast_deployment=require_env("AZURE_OPENAI_CHAT_FAST_DEPLOYMENT"),
        chat_quality_deployment=require_env("AZURE_OPENAI_CHAT_QUALITY_DEPLOYMENT"),

        default_chat_model=os.getenv("DEFAULT_CHAT_MODEL", "chat_default"),

        agent_prompt_version=os.getenv("AGENT_PROMPT_VERSION", "v1"),
        agent_prompt_profile=os.getenv("AGENT_PROMPT_PROFILE", "default"),
        agent_environment=os.getenv("AGENT_ENVIRONMENT", "lab"),
        agent_allowed_services=os.getenv(
            "AGENT_ALLOWED_SERVICES",
            "vpn, correo, sharepoint, erp",
        ),
    )