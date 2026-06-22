from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from azure.identity import AzureCliCredential
from pydantic import BaseModel, Field, ValidationError


class GraphIntegrationError(RuntimeError):
    pass


class GraphUserDto(BaseModel):
    id: str
    displayName: str | None = None
    userPrincipalName: str | None = None
    mail: str | None = None
    jobTitle: str | None = None
    department: str | None = None


class GraphEventDto(BaseModel):
    id: str
    subject: str | None = None
    start: dict[str, Any] = Field(default_factory=dict)
    end: dict[str, Any] = Field(default_factory=dict)
    location: dict[str, Any] = Field(default_factory=dict)

class GraphGroupDto(BaseModel):
    id: str
    displayName: str | None = None
    mail: str | None = None
    mailEnabled: bool | None = None
    securityEnabled: bool | None = None

@dataclass(frozen=True)
class GraphClient:
    base_url: str
    timeout_seconds: float = 10.0

    @classmethod
    def from_env(cls) -> "GraphClient":
        base_url = os.getenv("GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0")
        return cls(base_url=base_url.rstrip("/"))

    def _access_token(self) -> str:
        credential = AzureCliCredential()
        token = credential.get_token("https://graph.microsoft.com/.default")
        return token.token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"

        try:
            response = httpx.get(
                url,
                headers=self._headers(),
                params=params,
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise GraphIntegrationError("Timeout llamando a Microsoft Graph.") from exc
        except httpx.RequestError as exc:
            raise GraphIntegrationError(f"Error de red llamando a Graph: {exc}") from exc

        if response.status_code == 401:
            raise GraphIntegrationError(
                "No autorizado. Revisa az login y los permisos concedidos."
            )

        if response.status_code == 403:
            raise GraphIntegrationError(
                "Permiso denegado. La identidad no tiene permisos suficientes en Graph."
            )

        if response.status_code == 404:
            raise GraphIntegrationError("Recurso no encontrado en Microsoft Graph.")

        if response.status_code == 429:
            raise GraphIntegrationError(
                "Graph ha limitado temporalmente las llamadas. Reintenta más tarde."
            )

        if response.status_code >= 400:
            raise GraphIntegrationError(
                f"Error HTTP {response.status_code} llamando a Graph: {response.text}"
            )

        return response.json()

    def get_me(self) -> GraphUserDto:
        data = self._get(
            "/me",
            params={
                "$select": "id,displayName,userPrincipalName,mail,jobTitle,department"
            },
        )

        try:
            return GraphUserDto.model_validate(data)
        except ValidationError as exc:
            raise GraphIntegrationError(
                "La respuesta de /me no tiene el formato esperado."
            ) from exc

    def get_user_by_upn(self, upn: str) -> GraphUserDto:
        clean_upn = upn.strip().lower()

        data = self._get(
            f"/users/{clean_upn}",
            params={
                "$select": "id,displayName,userPrincipalName,mail,jobTitle,department"
            },
        )

        try:
            return GraphUserDto.model_validate(data)
        except ValidationError as exc:
            raise GraphIntegrationError(
                "La respuesta de /users/{upn} no tiene el formato esperado."
            ) from exc

    def get_my_upcoming_events(self, days: int = 7, limit: int = 10) -> list[GraphEventDto]:
        safe_days = max(1, min(days, 30))
        safe_limit = max(1, min(limit, 25))

        now = datetime.now(timezone.utc)
        end = now + timedelta(days=safe_days)

        data = self._get(
            "/me/calendarView",
            params={
                "startDateTime": now.isoformat(),
                "endDateTime": end.isoformat(),
                "$select": "id,subject,start,end,location",
                "$orderby": "start/dateTime",
                "$top": safe_limit,
            },
        )

        raw_events = data.get("value", [])

        try:
            return [GraphEventDto.model_validate(item) for item in raw_events]
        except ValidationError as exc:
            raise GraphIntegrationError(
                "La respuesta de calendario no tiene el formato esperado."
            ) from exc
        
    def list_users(self, limit: int = 10) -> list[GraphUserDto]:
        safe_limit = max(1, min(limit, 25))

        data = self._get(
            "/users",
            params={
                "$select": "id,displayName,userPrincipalName,mail,jobTitle,department",
                "$top": str(safe_limit),
            },
        )

        raw_users = data.get("value", [])

        try:
            return [GraphUserDto.model_validate(item) for item in raw_users]
        except ValidationError as exc:
            raise GraphIntegrationError(
                "La respuesta de /users no tiene el formato esperado."
            ) from exc


    def list_groups(self, limit: int = 10) -> list[GraphGroupDto]:
        safe_limit = max(1, min(limit, 25))

        data = self._get(
            "/groups",
            params={
                "$select": "id,displayName,mail,mailEnabled,securityEnabled",
                "$top": str(safe_limit),
            },
        )

        raw_groups = data.get("value", [])

        try:
            return [GraphGroupDto.model_validate(item) for item in raw_groups]
        except ValidationError as exc:
            raise GraphIntegrationError(
                "La respuesta de /groups no tiene el formato esperado."
            ) from exc        