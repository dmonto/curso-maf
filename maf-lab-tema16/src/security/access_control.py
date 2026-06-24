
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.integrations.access_lab_repository import TicketRecord, UserRecord


Action = Literal[
    "ticket.read",
    "ticket.note.add",
    "ticket.priority.update",
    "ticket.summary.global",
]


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str


def authorize(
    *,
    user: UserRecord | None,
    action: Action,
    ticket: TicketRecord | None = None,
) -> AuthorizationDecision:
    if user is None:
        return AuthorizationDecision(
            allowed=False,
            reason="Usuario no reconocido.",
        )

    if action == "ticket.summary.global":
        if user.role == "manager":
            return AuthorizationDecision(True, "Rol manager autorizado para resumen global.")

        return AuthorizationDecision(False, "Solo manager puede ver resumen global.")

    if ticket is None:
        return AuthorizationDecision(False, "El recurso solicitado no existe.")

    if action == "ticket.read":
        if ticket.owner_upn.lower() == user.upn.lower():
            return AuthorizationDecision(True, "El usuario es propietario del ticket.")

        if user.role in {"support_l1", "support_l2", "manager"} and user.department == ticket.department:
            return AuthorizationDecision(True, "Rol de soporte autorizado en el mismo departamento.")

        if user.role == "manager":
            return AuthorizationDecision(True, "Rol manager autorizado.")

        return AuthorizationDecision(False, "No tienes permiso para consultar este ticket.")

    if action == "ticket.note.add":
        if user.role in {"support_l1", "support_l2", "manager"} and user.department == ticket.department:
            return AuthorizationDecision(True, "Rol autorizado para añadir notas en el departamento.")

        return AuthorizationDecision(False, "No tienes permiso para añadir notas a este ticket.")

    if action == "ticket.priority.update":
        if user.role in {"support_l2", "manager"} and user.department == ticket.department:
            return AuthorizationDecision(True, "Rol autorizado para cambiar prioridad.")

        return AuthorizationDecision(False, "Solo support_l2 o manager pueden cambiar prioridad.")

    return AuthorizationDecision(False, "Acción no reconocida.")