from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH, override=True)


def require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Falta la variable de entorno {name}. "
            f"Se ha intentado cargar el .env desde: {ENV_PATH}"
        )

    return value


@dataclass(frozen=True)
class Settings:
    default_chat_model: str
    azure_ai_project_endpoint: str


def get_settings() -> Settings:
    return Settings(
        default_chat_model=os.getenv("DEFAULT_CHAT_MODEL", "chat_fast"),
        azure_ai_project_endpoint=require_env("AZURE_AI_PROJECT_ENDPOINT"),
    )