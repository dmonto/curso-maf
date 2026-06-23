import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from agent_framework import (
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)
from pydantic import BaseModel, Field


class ServiceName(StrEnum):
    VPN = "vpn"
    ERP = "erp"
    EMAIL = "email"
    TEAMS = "teams"
    UNKNOWN = "unknown"


class Priority(StrEnum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class IncidentInput(BaseModel):
    description: str = Field(min_length=5)
    reported_by: str = Field(default="usuario.lab")
    users_affected: int | None = Field(default=None, ge=1)


class TicketDraft(BaseModel):
    draft_id: str
    title: str
    description: str
    service: ServiceName
    priority: Priority
    reported_by: str
    users_affected: int | None
    requires_approval: bool
    reason: str


@dataclass
class HumanApprovalRequest:
    prompt: str
    draft_id: str
    title: str
    description: str
    service: str
    priority: str
    reason: str


class ApprovalResult(BaseModel):
    draft_id: str
    decision: ApprovalDecision
    approved_by: str | None = None
    approved_at_utc: str | None = None
    simulated_ticket_id: str | None = None
    human_feedback: str | None = None
    message: str


def detect_service(text: str) -> ServiceName:
    text = text.lower()

    if "vpn" in text:
        return ServiceName.VPN

    if "erp" in text or "sap" in text:
        return ServiceName.ERP

    if "correo" in text or "email" in text or "outlook" in text:
        return ServiceName.EMAIL

    if "teams" in text:
        return ServiceName.TEAMS

    return ServiceName.UNKNOWN


def classify_priority(
    text: str,
    service: ServiceName,
    users_affected: int | None,
) -> tuple[Priority, str]:
    normalized = text.lower()

    if "error 500" in normalized or "caído" in normalized or "caido" in normalized:
        if users_affected is not None and users_affected >= 5:
            return Priority.P1, "Error severo con impacto en varios usuarios."

        return Priority.P2, "Error severo con impacto limitado o no confirmado."

    if "lento" in normalized or "degradado" in normalized or "intermitente" in normalized:
        return Priority.P2, "Servicio degradado o intermitente."

    if service == ServiceName.UNKNOWN:
        return Priority.P3, "No se ha identificado claramente el servicio."

    return Priority.P3, "Incidencia estándar sin criticidad alta."


def parse_human_feedback(value: str) -> tuple[ApprovalDecision, str | None]:
    normalized = value.strip()

    if normalized.lower() in {
        "approve",
        "approved",
        "aprobar",
        "aprobado",
        "si",
        "sí",
        "y",
        "yes",
    }:
        return ApprovalDecision.APPROVED, None

    if normalized.lower() in {
        "reject",
        "rejected",
        "rechazar",
        "rechazado",
        "no",
        "n",
    }:
        return ApprovalDecision.REJECTED, None

    return ApprovalDecision.NEEDS_REVISION, normalized


class PrepareTicketDraft(Executor):
    def __init__(self, id: str = "prepare_ticket_draft") -> None:
        super().__init__(id=id)

    @handler
    async def prepare(
        self,
        message: IncidentInput,
        ctx: WorkflowContext[TicketDraft],
    ) -> None:
        service = detect_service(message.description)

        priority, reason = classify_priority(
            text=message.description,
            service=service,
            users_affected=message.users_affected,
        )

        requires_approval = priority in {Priority.P1, Priority.P2}

        draft = TicketDraft(
            draft_id=f"draft-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            title=f"[{priority.upper()}] Incidencia en {service.value.upper()}",
            description=(
                f"Descripción original: {message.description}\n"
                f"Servicio detectado: {service.value}\n"
                f"Usuarios afectados: {message.users_affected or 'pendiente'}\n"
                f"Reportado por: {message.reported_by}\n"
                f"Motivo de prioridad: {reason}\n"
            ),
            service=service,
            priority=priority,
            reported_by=message.reported_by,
            users_affected=message.users_affected,
            requires_approval=requires_approval,
            reason=reason,
        )

        await ctx.send_message(draft)


class ApprovalGate(Executor):
    def __init__(
        self,
        id: str = "approval_gate",
        reviewer: str = "operador.lab",
    ) -> None:
        super().__init__(id=id)
        self._reviewer = reviewer

    @handler
    async def request_approval(
        self,
        message: TicketDraft,
        ctx: WorkflowContext[Any],
    ) -> None:
        if not message.requires_approval:
            await ctx.yield_output(
                ApprovalResult(
                    draft_id=message.draft_id,
                    decision=ApprovalDecision.APPROVED,
                    approved_by="auto",
                    approved_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    simulated_ticket_id=f"SIM-{message.draft_id}",
                    human_feedback=None,
                    message="Borrador aprobado automáticamente por ser de bajo riesgo.",
                )
            )
            return

        request = HumanApprovalRequest(
            prompt=(
                "Revisa el borrador. Responde 'approve' para aprobar, "
                "'reject' para rechazar, o escribe comentarios para pedir revisión."
            ),
            draft_id=message.draft_id,
            title=message.title,
            description=message.description,
            service=message.service.value,
            priority=message.priority.value,
            reason=message.reason,
        )

        # Compatibilidad con agent-framework 1.8.1:
        # en vez de usar request_info + response_handler + streaming,
        # emitimos una solicitud de aprobación como output normal.
        # La CLI recoge este output y pide la decisión humana por consola.
        await ctx.yield_output(request)


def build_approval_result_from_human_feedback(
    original_request: HumanApprovalRequest,
    feedback: str,
    reviewer: str = "operador.soporte",
) -> ApprovalResult:
    decision, comments = parse_human_feedback(feedback)

    if decision == ApprovalDecision.APPROVED:
        return ApprovalResult(
            draft_id=original_request.draft_id,
            decision=ApprovalDecision.APPROVED,
            approved_by=reviewer,
            approved_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            simulated_ticket_id=f"SIM-{original_request.draft_id}",
            human_feedback=None,
            message=(
                "El borrador ha sido aprobado. "
                "Se simula la creación del ticket, sin ejecutar integración externa real."
            ),
        )

    if decision == ApprovalDecision.REJECTED:
        return ApprovalResult(
            draft_id=original_request.draft_id,
            decision=ApprovalDecision.REJECTED,
            approved_by=reviewer,
            approved_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            simulated_ticket_id=None,
            human_feedback="rechazado",
            message="El operador ha rechazado el borrador. No se ejecuta ninguna acción.",
        )

    return ApprovalResult(
        draft_id=original_request.draft_id,
        decision=ApprovalDecision.NEEDS_REVISION,
        approved_by=reviewer,
        approved_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        simulated_ticket_id=None,
        human_feedback=comments,
        message=(
            "El operador ha solicitado revisión del borrador. "
            "El workflow queda cerrado sin crear ticket simulado."
        ),
    )


def build_incident_hitl_workflow():
    prepare_draft = PrepareTicketDraft()
    approval_gate = ApprovalGate(reviewer="operador.soporte")

    workflow = (
        WorkflowBuilder(start_executor=prepare_draft)
        .add_edge(prepare_draft, approval_gate)
        .build()
    )

    return workflow


def prompt_for_responses(
    requests: dict[str, HumanApprovalRequest],
) -> dict[str, str]:
    responses: dict[str, str] = {}

    for request_id, request in requests.items():
        print("\n=== APROBACIÓN HUMANA REQUERIDA ===")
        print(f"request_id: {request_id}")
        print(f"draft_id: {request.draft_id}")
        print(f"prioridad: {request.priority}")
        print(f"servicio: {request.service}")
        print(f"motivo: {request.reason}")

        print("\n--- BORRADOR ---")
        print(request.title)
        print(request.description)
        print("--- FIN BORRADOR ---")

        print(request.prompt)

        response = input("\nDecisión humana: ").strip()
        responses[request_id] = response

    return responses


def extract_outputs(result: object) -> list[object]:
    """
    Extrae outputs de WorkflowRunResult de forma tolerante a pequeños cambios
    entre versiones de agent-framework.

    En 1.8.1 normalmente basta con result.get_outputs().
    """
    if hasattr(result, "get_outputs"):
        outputs = result.get_outputs()
        return list(outputs)

    if hasattr(result, "outputs"):
        outputs = getattr(result, "outputs")
        return list(outputs)

    events = getattr(result, "events", None)
    if events is not None:
        return [
            event.data
            for event in events
            if getattr(event, "type", None) == "output"
        ]

    available = [
        name
        for name in dir(result)
        if "output" in name.lower() or "event" in name.lower()
    ]

    raise TypeError(
        "No se han podido extraer outputs del resultado del workflow. "
        f"Tipo recibido: {type(result)}. "
        f"Atributos relacionados disponibles: {available}"
    )


async def run_interactive_session(
    workflow,
    initial_message: IncidentInput,
) -> ApprovalResult:
    result = await workflow.run(initial_message)
    outputs = extract_outputs(result)

    if not outputs:
        raise RuntimeError("El workflow terminó sin outputs.")

    last_output = outputs[-1]

    if isinstance(last_output, ApprovalResult):
        return last_output

    if isinstance(last_output, HumanApprovalRequest):
        responses = prompt_for_responses(
            {
                "manual-approval": last_output,
            }
        )

        human_feedback = responses["manual-approval"]

        return build_approval_result_from_human_feedback(
            original_request=last_output,
            feedback=human_feedback,
            reviewer="operador.soporte",
        )

    raise TypeError(
        "Output no esperado del workflow. "
        f"Tipo recibido: {type(last_output)}. "
        f"Valor: {last_output}"
    )


async def main() -> None:
    workflow = build_incident_hitl_workflow()

    request = IncidentInput(
        description="El ERP devuelve error 500 y afecta a 12 usuarios.",
        reported_by="ana.soporte@contoso.com",
        users_affected=12,
    )

    result = await run_interactive_session(workflow, request)

    print("\n=== RESULTADO FINAL ===")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())