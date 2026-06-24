from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import httpx

from src.settings import get_settings


class SupportMicroserviceError(Exception):
    pass


@dataclass(frozen=True)
class SupportMicroserviceClient:
    base_url: str
    api_key: str
    timeout_seconds: float

    def triage_incident(
        self,
        service: str,
        summary: str,
        affected_users: int,
        business_impact: str,
    ) -> dict:
        correlation_id = f"corr-{uuid4().hex[:8]}"

        payload = {
            "service": service,
            "summary": summary,
            "affected_users": affected_users,
            "business_impact": business_impact,
        }

        headers = {
            "x-api-key": self.api_key,
            "x-correlation-id": correlation_id,
        }

        try:
            response = httpx.post(
                f"{self.base_url}/incidents/triage",
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()

        except httpx.TimeoutException as error:
            raise SupportMicroserviceError(
                f"Timeout llamando al microservicio de soporte. correlation_id={correlation_id}"
            ) from error

        except httpx.ConnectError as error:
            raise SupportMicroserviceError(
                f"No se pudo conectar con el microservicio de soporte. correlation_id={correlation_id}"
            ) from error

        except httpx.HTTPStatusError as error:
            status_code = error.response.status_code
            raise SupportMicroserviceError(
                f"Error HTTP {status_code} llamando al microservicio de soporte. "
                f"correlation_id={correlation_id}"
            ) from error

        data = response.json()
        data["client_correlation_id"] = correlation_id

        return data


def build_support_microservice_client() -> SupportMicroserviceClient:
    settings = get_settings()

    return SupportMicroserviceClient(
        base_url=settings.support_service_base_url,
        api_key=settings.support_service_api_key,
        timeout_seconds=settings.support_service_timeout_seconds,
    )