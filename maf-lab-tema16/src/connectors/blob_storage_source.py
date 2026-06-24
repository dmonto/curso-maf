from __future__ import annotations

import os
from pathlib import Path

from azure.identity import AzureCliCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

from src.connectors.models import CorporateDocument


load_dotenv()


SUPPORTED_EXTENSIONS = {".md", ".txt"}


def _require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")

    return value


def _parse_metadata_from_blob_name(blob_name: str) -> dict:
    """
    Convención simple para el laboratorio:
    rag/vpn/manual_vpn.md      → domain=vpn
    rag/erp/erp_outage.md      → domain=erp
    rag/support/prioridad.md   → domain=support
    """
    parts = blob_name.split("/")

    domain = "general"

    if len(parts) >= 2:
        domain = parts[-2]

    return {
        "domain": domain,
        "visibility": "internal",
        "classification": "internal",
        "tenant_id": "curso-maf",
        "allowed_groups": ["support-l1", "support-l2"],
        "allowed_users": [],
        "denied_groups": [],
        "denied_users": [],
        "owner": "it-support",
    }


def _is_supported(blob_name: str) -> bool:
    return Path(blob_name).suffix.lower() in SUPPORTED_EXTENSIONS


def list_blob_documents() -> list[CorporateDocument]:
    account_name = _require_env("AZURE_STORAGE_ACCOUNT")
    container_name = _require_env("AZURE_STORAGE_CONTAINER")
    prefix = os.getenv("AZURE_STORAGE_PREFIX", "")

    account_url = f"https://{account_name}.blob.core.windows.net"

    service_client = BlobServiceClient(
        account_url=account_url,
        credential=AzureCliCredential(),
    )

    container_client = service_client.get_container_client(container_name)

    documents: list[CorporateDocument] = []

    for blob in container_client.list_blobs(name_starts_with=prefix):
        blob_name = blob.name

        if not _is_supported(blob_name):
            continue

        blob_client = container_client.get_blob_client(blob_name)
        content = blob_client.download_blob().readall().decode("utf-8")

        metadata = _parse_metadata_from_blob_name(blob_name)

        documents.append(
            CorporateDocument(
                source_id=f"blob://{container_name}/{blob_name}",
                source_type="azure_blob",
                title=Path(blob_name).stem.replace("_", " ").title(),
                path=blob_name,
                text=content,
                source_last_modified_utc=(
                    blob.last_modified.isoformat()
                    if blob.last_modified
                    else None
                ),
                **metadata,
            )
        )

    return documents