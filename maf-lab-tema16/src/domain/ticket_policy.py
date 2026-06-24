from __future__ import annotations

from src.domain.support_models import (
    SupportTicketDraftRequest,
    TicketPriority,
)


class TicketPolicyError(Exception):
    pass


class TicketPolicy:
    def validate_draft_request(self, request: SupportTicketDraftRequest) -> None:
        if len(request.summary.strip()) < 10:
            raise TicketPolicyError("El resumen del ticket es demasiado corto.")

        if request.affected_users < 1:
            raise TicketPolicyError("affected_users debe ser mayor o igual que 1.")

        if not request.business_impact.strip():
            raise TicketPolicyError("Debe indicarse impacto de negocio.")

    def calculate_priority(self, request: SupportTicketDraftRequest) -> TicketPriority:
        impact = request.business_impact.lower()

        if request.affected_users >= 50:
            return TicketPriority.P1

        if request.affected_users >= 10:
            return TicketPriority.P2

        if "facturación" in impact or "producción" in impact or "clientes" in impact:
            return TicketPriority.P2

        return TicketPriority.P3

    def ensure_draft_only(self) -> None:
        """
        Control duro: este laboratorio solo permite preparar borradores.
        No se permite crear tickets reales.
        """
        return None