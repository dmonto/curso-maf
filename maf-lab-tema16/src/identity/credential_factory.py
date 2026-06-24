from __future__ import annotations

import os
from typing import Literal

from azure.identity import AzureCliCredential, DefaultAzureCredential, ManagedIdentityCredential


CredentialMode = Literal["local_cli", "managed_identity", "default"]


def get_credential_mode() -> CredentialMode:
    value = os.getenv("AZURE_CREDENTIAL_MODE", "local_cli").strip().lower()

    if value not in {"local_cli", "managed_identity", "default"}:
        raise ValueError(
            "AZURE_CREDENTIAL_MODE debe ser local_cli, managed_identity o default."
        )

    return value  # type: ignore[return-value]


def create_azure_credential():
    """
    Crea la credencial operativa del backend.

    local_cli:
        Para desarrollo local con az login.

    managed_identity:
        Para App Service, Container Apps, AKS u otro runtime Azure con identidad gestionada.

    default:
        Cadena flexible de Azure Identity. Útil cuando quieres soportar varios entornos,
        pero conviene entender exactamente qué credencial está usando.
    """

    mode = get_credential_mode()

    if mode == "local_cli":
        return AzureCliCredential()

    if mode == "managed_identity":
        return ManagedIdentityCredential()

    return DefaultAzureCredential(exclude_interactive_browser_credential=True)