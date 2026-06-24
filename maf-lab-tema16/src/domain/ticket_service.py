from __future__ import annotations

from src.domain.support_models import (
    SupportTicketDraft,
    SupportTicketDraftRequest,
)
from src.domain.ticket_policy import TicketPolicy
from src.observability.events_resp import emit_event
from src.repositories.ticket_repository import TicketDraftRepository


class SupportTicketService:
    def __init__(
        self,
        policy: TicketPolicy,
        repository: TicketDraftRepository,
    ) -> None:
        self.policy = policy
        self.repository = repository

    def prepare_ticket_draft(self, request: SupportTicketDraftRequest) -> dict:
        emit_event(
            "ticket_draft.prepare.started",
            service=request.service,
            affected_users=request.affected_users,
        )

        self.policy.ensure_draft_only()
        self.policy.validate_draft_request(request)

        priority = self.policy.calculate_priority(request)

        draft = SupportTicketDraft(
            ticket_type="support_incident",
            service=request.service,
            priority=priority,
            summary=request.summary.strip(),
            business_impact=request.business_impact.strip(),
            recommended_queue=self._select_queue(request),
            requires_human_review=priority in {"p1", "p2"},
        )

        draft_id = self.repository.save_draft(draft)

        emit_event(
            "ticket_draft.prepare.completed",
            draft_id=draft_id,
            service=draft.service,
            priority=draft.priority,
            requires_human_review=draft.requires_human_review,
        )

        return {
            "draft_id": draft_id,
            "draft": {
                "ticket_type": draft.ticket_type,
                "service": draft.service,
                "priority": draft.priority,
                "summary": draft.summary,
                "business_impact": draft.business_impact,
                "recommended_queue": draft.recommended_queue,
                "requires_human_review": draft.requires_human_review,
            },
        }

    def _select_queue(self, request: SupportTicketDraftRequest) -> str:
        if request.service.value == "vpn":
            return "network-support-l2"

        if request.service.value == "erp":
            return "business-apps-l2"

        if request.service.value in {"correo", "teams"}:
            return "collaboration-support-l2"

        return "service-desk-l1"