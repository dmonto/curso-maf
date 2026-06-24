from __future__ import annotations

from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from src.services.ticket_service import ServiceName, TicketPriority, TicketService


def _ticket_service() -> TicketService:
    return TicketService()


@tool(
    name="search_support_tickets",
    description=(
        "Consulta tickets existentes relacionados con un servicio corporativo. "
        "Usa esta tool antes de proponer crear una incidencia nueva si el usuario "
        "describe un problema que podría estar ya registrado."
    ),
    approval_mode="never_require",
)
def search_support_tickets(
    service: Annotated[
        Literal["vpn", "correo", "teams", "erp"],
        Field(description="Servicio afectado por la incidencia."),
    ],
    max_results: Annotated[
        int,
        Field(
            description="Número máximo de tickets a devolver. Usa valores pequeños.",
            ge=1,
            le=5,
        ),
    ] = 3,
) -> str:
    result = _ticket_service().search_tickets(
        service=ServiceName(service),
        max_results=max_results,
    )
    return result.to_json()


@tool(
    name="prepare_ticket_draft",
    description=(
        "Prepara un borrador de ticket de soporte. No crea una incidencia real. "
        "Debe usarse cuando ya hay información suficiente para resumir el problema."
    ),
    approval_mode="never_require",
)
def prepare_ticket_draft(
    service: Annotated[
        Literal["vpn", "correo", "teams", "erp"],
        Field(description="Servicio afectado."),
    ],
    title: Annotated[
        str,
        Field(description="Título breve del ticket.", min_length=8, max_length=120),
    ],
    description: Annotated[
        str,
        Field(description="Descripción clara del problema y pasos ya probados.", min_length=20),
    ],
    priority: Annotated[
        Literal["low", "medium", "high", "critical"],
        Field(description="Prioridad estimada según impacto."),
    ] = "medium",
) -> str:
    result = _ticket_service().prepare_ticket_draft(
        service=ServiceName(service),
        title=title,
        description=description,
        priority=TicketPriority(priority),
    )
    return result.to_json()


@tool(
    name="create_ticket_real",
    description=(
        "Crea un ticket real a partir de un borrador confirmado. "
        "Solo debe usarse cuando el usuario haya confirmado explícitamente la creación."
    ),
    approval_mode="always_require",
)
def create_ticket_real(
    draft_id: Annotated[
        str,
        Field(description="Identificador del borrador previamente preparado.", min_length=5),
    ],
    confirmed_by_user: Annotated[
        bool,
        Field(description="Debe ser True solo si el usuario confirmó explícitamente."),
    ],
) -> str:
    result = _ticket_service().create_ticket_real(
        draft_id=draft_id,
        confirmed_by_user=confirmed_by_user,
    )
    return result.to_json()