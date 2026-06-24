from __future__ import annotations

from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from src.domain.support_models import SupportService, SupportTicketDraftRequest
from src.domain.ticket_policy import TicketPolicy, TicketPolicyError
from src.domain.ticket_service import SupportTicketService
from src.repositories.ticket_repository import TicketDraftRepository


def build_ticket_service() -> SupportTicketService:
    return SupportTicketService(
        policy=TicketPolicy(),
        repository=TicketDraftRepository(),
    )


@tool(
    name="prepare_support_ticket_draft",
    description=(
        "Prepara un borrador de ticket de soporte interno. "
        "No crea un ticket real. Debe usarse cuando ya se conoce el servicio afectado, "
        "el resumen del problema, los usuarios afectados y el impacto de negocio."
    ),
)
def prepare_support_ticket_draft(
    service: Annotated[
        Literal["vpn", "erp", "correo", "teams"],
        Field(description="Servicio afectado por la incidencia."),
    ],
    summary: Annotated[
        str,
        Field(description="Resumen concreto del problema reportado.", min_length=10),
    ],
    affected_users: Annotated[
        int,
        Field(description="Número estimado de usuarios afectados.", ge=1),
    ],
    business_impact: Annotated[
        str,
        Field(description="Impacto operativo o de negocio de la incidencia.", min_length=5),
    ],
) -> dict:
    request = SupportTicketDraftRequest(
        service=SupportService(service),
        summary=summary,
        affected_users=affected_users,
        business_impact=business_impact,
    )

    service_layer = build_ticket_service()

    try:
        return service_layer.prepare_ticket_draft(request)
    except TicketPolicyError as error:
        return {
            "error": "policy_error",
            "message": str(error),
        }