from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv


load_dotenv()


SecretsMode = Literal["env", "keyvault"]


class SecretResolutionError(RuntimeError):
    pass


def _normalize_mode(raw: str | None) -> SecretsMode:
    value = (raw or "env").strip().lower()

    if value not in {"env", "keyvault"}:
        raise SecretResolutionError(
            "SECRETS_MODE debe ser 'env' o 'keyvault'."
        )

    return value  # type: ignore[return-value]


def redact_secret(value: str | None) -> str:
    if not value:
        return "<missing>"

    return "<set:redacted>"


@dataclass(frozen=True)
class SecretStatus:
    logical_name: str
    source: str
    configured: bool
    value: str


@dataclass(frozen=True)
class SecretResolver:
    mode: SecretsMode
    key_vault_url: str | None = None

    @classmethod
    def from_env(cls) -> "SecretResolver":
        mode = _normalize_mode(os.getenv("SECRETS_MODE"))
        key_vault_url = os.getenv("AZURE_KEY_VAULT_URL")

        if mode == "keyvault" and not key_vault_url:
            raise SecretResolutionError(
                "SECRETS_MODE=keyvault requiere AZURE_KEY_VAULT_URL."
            )

        return cls(
            mode=mode,
            key_vault_url=key_vault_url.rstrip("/") if key_vault_url else None,
        )

    @lru_cache(maxsize=1)
    def _keyvault_client(self) -> SecretClient:
        if not self.key_vault_url:
            raise SecretResolutionError("Falta la URL de Azure Key Vault.")

        credential = DefaultAzureCredential()
        return SecretClient(
            vault_url=self.key_vault_url,
            credential=credential,
        )

    def get_secret(
        self,
        logical_name: str,
        *,
        env_name: str | None = None,
        keyvault_secret_name: str | None = None,
        required: bool = True,
    ) -> str | None:
        """
        Recupera un secreto sin exponer al agente de dónde viene ni su valor.
        """

        env_name = env_name or logical_name

        if self.mode == "env":
            value = os.getenv(env_name)

            if required and not value:
                raise SecretResolutionError(
                    f"Falta el secreto local {env_name}."
                )

            return value

        secret_name = (
            keyvault_secret_name
            or os.getenv(f"{logical_name}_SECRET_NAME")
            or logical_name.replace("_", "-")
        )

        try:
            secret = self._keyvault_client().get_secret(secret_name)
            value = secret.value
        except Exception as exc:
            if required:
                raise SecretResolutionError(
                    f"No se pudo recuperar el secreto {secret_name} desde Key Vault."
                ) from exc
            return None

        if required and not value:
            raise SecretResolutionError(
                f"El secreto {secret_name} no tiene valor."
            )

        return value

    def get_status(
        self,
        logical_name: str,
        *,
        env_name: str | None = None,
        keyvault_secret_name: str | None = None,
    ) -> SecretStatus:
        try:
            value = self.get_secret(
                logical_name,
                env_name=env_name,
                keyvault_secret_name=keyvault_secret_name,
                required=False,
            )
            return SecretStatus(
                logical_name=logical_name,
                source=self.mode,
                configured=bool(value),
                value=redact_secret(value),
            )
        except Exception:
            return SecretStatus(
                logical_name=logical_name,
                source=self.mode,
                configured=False,
                value="<error:redacted>",
            )