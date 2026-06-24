from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

import requests
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

from src.connectors.models import CorporateDocument


load_dotenv()


SUPPORTED_EXTENSIONS = {".md", ".txt"}


def _require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")

    return value


def _get_graph_token() -> str:
    credential = AzureCliCredential()
    token = credential.get_token("https://graph.microsoft.com/.default")
    return token.token


def _graph_get(url: str) -> dict:
    headers = {
        "Authorization": f"Bearer {_get_graph_token()}",
    }

    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code >= 400:
        raise RuntimeError(
            f"Error llamando a Graph {response.status_code}: {response.text}"
        )

    return response.json()


def _graph_get_bytes(url: str) -> bytes:
    headers = {
        "Authorization": f"Bearer {_get_graph_token()}",
    }

    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code >= 400:
        raise RuntimeError(
            f"Error descargando contenido {response.status_code}: {response.text}"
        )

    return response.content


def _is_supported(name: str) -> bool:
    return Path(name).suffix.lower() in SUPPORTED_EXTENSIONS


def _infer_domain_from_path(path: str) -> str:
    parts = [part for part in path.split("/") if part]

    if len(parts) >= 2:
        return parts[-2].lower()

    return "general"


def _list_children(site_id: str, drive_id: str, folder_path: str) -> list[dict]:
    encoded_path = quote(folder_path.strip("/"))

    if encoded_path:
        url = (
            f"https://graph.microsoft.com/v1.0/sites/{site_id}"
            f"/drives/{drive_id}/root:/{encoded_path}:/children"
        )
    else:
        url = (
            f"https://graph.microsoft.com/v1.0/sites/{site_id}"
            f"/drives/{drive_id}/root/children"
        )

    payload = _graph_get(url)
    return payload.get("value", [])


def _download_drive_item(site_id: str, drive_id: str, item_id: str) -> bytes:
    url = (
        f"https://graph.microsoft.com/v1.0/sites/{site_id}"
        f"/drives/{drive_id}/items/{item_id}/content"
    )

    return _graph_get_bytes(url)


def list_sharepoint_documents() -> list[CorporateDocument]:
    site_id = _require_env("SHAREPOINT_SITE_ID")
    drive_id = _require_env("SHAREPOINT_DRIVE_ID")
    folder_path = os.getenv("SHAREPOINT_FOLDER_PATH", "")

    items = _list_children(
        site_id=site_id,
        drive_id=drive_id,
        folder_path=folder_path,
    )

    documents: list[CorporateDocument] = []

    for item in items:
        name = item["name"]

        if "folder" in item:
            continue

        if not _is_supported(name):
            continue

        content = _download_drive_item(
            site_id=site_id,
            drive_id=drive_id,
            item_id=item["id"],
        ).decode("utf-8")

        relative_path = f"{folder_path.strip('/')}/{name}".strip("/")
        domain = _infer_domain_from_path(relative_path)

        documents.append(
            CorporateDocument(
                source_id=f"sharepoint://{site_id}/{drive_id}/{item['id']}",
                source_type="sharepoint",
                title=Path(name).stem.replace("_", " ").title(),
                domain=domain,
                tenant_id="curso-maf",
                visibility="internal",
                classification="internal",
                allowed_groups=["support-l1", "support-l2"],
                allowed_users=[],
                denied_groups=[],
                denied_users=[],
                owner="it-support",
                path=relative_path,
                text=content,
                source_last_modified_utc=item.get("lastModifiedDateTime"),
            )
        )

    return documents