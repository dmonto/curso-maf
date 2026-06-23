from __future__ import annotations

import os
from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from src.integrations.access_lab_repository import AccessLabRepository
from src.security.access_control import authorize


def _current_user_upn() -> str:
    upn = os.getenv("CURRENT_USER_UPN")
    if not upn:
        raise RuntimeError("Falta CURRENT_USER_UPN en .env")
    return upn.strip().lower()


@tool(
    name="consultar_ticket_con_acceso",
    description=(
        "Consulta un ticket aplicando control de acceso. "
        "Úsala cuando el usuario quiera ver datos de una incidencia. "
        "No modifica datos."
    ),
)
def consultar_ticket_con_acceso(
    ticket_id: Annotated[
        str,
        Field(description="Identificador del ticket. Ejemplo: INC-1001."),
    ],
) -> dict:
    repo = AccessLabRepository.from_env()
    requester_upn = _current_user_upn()

    user = repo.get_user(requester_upn)
    ticket = repo.get_ticket(ticket_id)

    decision = authorize(
        user=user,
        action="ticket.read",
        ticket=ticket,
    )

    repo.write_audit(
        requester_upn=requester_upn,
        action="ticket.read",
        resource_id=ticket_id,
        allowed=decision.allowed,
        reason=decision.reason,
    )

    if not decision.allowed:
        return {
            "ok": False,
            "allowed": False,
            "reason": decision.reason,
        }

    return {
        "ok": True,
        "allowed": True,
        "reason": decision.reason,
        "ticket": ticket.model_dump() if ticket else None,
    }


@tool(
    name="cambiar_prioridad_ticket_con_acceso",
    description=(
        "Cambia la prioridad de un ticket aplicando control de acceso. "
        "Úsala solo si el usuario solicita explícitamente cambiar la prioridad. "
        "Requiere rol support_l2 o manager en el departamento del ticket."
    ),
)
def cambiar_prioridad_ticket_con_acceso(
    ticket_id: Annotated[
        str,
        Field(description="Identificador del ticket. Ejemplo: INC-1001."),
    ],
    priority: Annotated[
        Literal["p1", "p2", "p3", "p4"],
        Field(description="Nueva prioridad permitida: p1, p2, p3 o p4."),
    ],
) -> dict:
    repo = AccessLabRepository.from_env()
    requester_upn = _current_user_upn()

    user = repo.get_user(requester_upn)
    ticket = repo.get_ticket(ticket_id)

    decision = authorize(
        user=user,
        action="ticket.priority.update",
        ticket=ticket,
    )

    repo.write_audit(
        requester_upn=requester_upn,
        action="ticket.priority.update",
        resource_id=ticket_id,
        allowed=decision.allowed,
        reason=decision.reason,
    )

    if not decision.allowed:
        return {
            "ok": False,
            "allowed": False,
            "updated": False,
            "reason": decision.reason,
        }

    updated = repo.update_ticket_priority(ticket_id, priority)

    return {
        "ok": True,
        "allowed": True,
        "updated": True,
        "reason": decision.reason,
        "ticket": updated.model_dump(),
    }


@tool(
    name="resumen_global_tickets_con_acceso",
    description=(
        "Devuelve un resumen global de tickets aplicando control de acceso. "
        "Solo debe usarse para perfiles manager."
    ),
)
def resumen_global_tickets_con_acceso() -> dict:
    repo = AccessLabRepository.from_env()
    requester_upn = _current_user_upn()

    user = repo.get_user(requester_upn)

    decision = authorize(
        user=user,
        action="ticket.summary.global",
    )

    repo.write_audit(
        requester_upn=requester_upn,
        action="ticket.summary.global",
        resource_id=None,
        allowed=decision.allowed,
        reason=decision.reason,
    )

    if not decision.allowed:
        return {
            "ok": False,
            "allowed": False,
            "reason": decision.reason,
        }

    return {
        "ok": True,
        "allowed": True,
        "reason": decision.reason,
        "rows": repo.summarize_tickets(),
    }