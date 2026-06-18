import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_framework import (
    Executor,
    FileCheckpointStorage,
    WorkflowBuilder,
    WorkflowContext,
    handler,
    response_handler,
)


CHECKPOINT_DIR = Path(".checkpoints/incident_persistence")
AUDIT_FILE = Path("approvals_audit.jsonl")
WORKFLOW_NAME = "incident_persistence_workflow"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def detect_service(text: str) -> str:
    value = text.lower()

    if "vpn" in value:
        return "vpn"
    if "erp" in value or "sap" in value:
        return "erp"
    if "correo" in value or "email" in value or "outlook" in value:
        return "email"
    if "teams" in value:
        return "teams"

    return "unknown"


def classify_priority(description: str, service: str, users_affected: int | None) -> tuple[str, str]:
    value = description.lower()

    if "error 500" in value or "caído" in value or "caido" in value:
        if service == "erp" and users_affected is not None and users_affected >= 5:
            return "p1", "Error severo en ERP con varios usuarios afectados."
        return "p2", "Error severo con impacto limitado o no confirmado."

    if "lento" in value or "intermitente" in value or "degradado" in value:
        return "p2", "Servicio degradado o intermitente."

    if service == "unknown":
        return "p3", "No se ha identificado claramente el servicio."

    return "p3", "Incidencia estándar sin señales de criticidad alta."


def build_incident_input(
    description: str,
    reported_by: str,
    users_affected: int | None,
) -> dict[str, Any]:
    if len(description.strip()) < 5:
        raise ValueError("La descripción debe tener al menos 5 caracteres.")

    if users_affected is not None and users_affected < 1:
        raise ValueError("users_affected debe ser >= 1.")

    return {
        "description": description.strip(),
        "reported_by": reported_by.strip(),
        "users_affected": users_affected,
        "created_at_utc": utc_now(),
    }


def write_audit_record(record: dict[str, Any]) -> None:
    with AUDIT_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_decision(value: str) -> tuple[str, str | None]:
    normalized = value.strip()

    if normalized.lower() in {"approve", "approved", "aprobar", "aprobado", "si", "sí", "yes", "y"}:
        return "approved", None

    if normalized.lower() in {"reject", "rejected", "rechazar", "rechazado", "no", "n"}:
        return "rejected", None

    return "needs_revision", normalized


class PrepareTicketDraft(Executor):
    def __init__(self, id: str = "prepare_ticket_draft") -> None:
        super().__init__(id=id)

    @handler
    async def handle(
        self,
        message: dict[str, Any],
        ctx: WorkflowContext[dict[str, Any]],
    ) -> None:
        service = detect_service(message["description"])
        priority, reason = classify_priority(
            description=message["description"],
            service=service,
            users_affected=message.get("users_affected"),
        )

        draft_id = f"draft-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        draft = {
            "draft_id": draft_id,
            "title": f"[{priority.upper()}] Incidencia en {service.upper()}",
            "description": message["description"],
            "reported_by": message["reported_by"],
            "users_affected": message.get("users_affected"),
            "service": service,
            "priority": priority,
            "priority_reason": reason,
            "requires_approval": priority in {"p1", "p2"},
            "prepared_at_utc": utc_now(),
        }

        await ctx.send_message(draft)


class ApprovalGate(Executor):
    def __init__(self, id: str = "approval_gate", reviewer: str = "operador.soporte") -> None:
        super().__init__(id=id)
        self._reviewer = reviewer
        self._handled_drafts: list[str] = []

    @handler
    async def handle(
        self,
        message: dict[str, Any],
        ctx: WorkflowContext[dict[str, Any]],
    ) -> None:
        self._handled_drafts.append(message["draft_id"])

        if not message["requires_approval"]:
            result = {
                "draft_id": message["draft_id"],
                "decision": "approved",
                "approved_by": "auto",
                "approved_at_utc": utc_now(),
                "simulated_ticket_id": f"SIM-{message['draft_id']}",
                "message": "Aprobación automática por bajo riesgo.",
                "ready_for_real_action": False,
            }

            write_audit_record(result)
            await ctx.yield_output(result)
            return

        approval_request = {
            "prompt": (
                "Revisa el borrador. Responde 'approve' para aprobar, "
                "'reject' para rechazar, o escribe comentarios para pedir revisión."
            ),
            "draft_id": message["draft_id"],
            "title": message["title"],
            "description": message["description"],
            "service": message["service"],
            "priority": message["priority"],
            "priority_reason": message["priority_reason"],
            "reported_by": message["reported_by"],
            "users_affected": message["users_affected"],
            "requested_at_utc": utc_now(),
        }

        await ctx.request_info(
            request_data=approval_request,
            response_type=str,
        )

    @response_handler
    async def handle_response(
        self,
        original_request: dict[str, Any],
        feedback: str,
        ctx: WorkflowContext[dict[str, Any]],
    ) -> None:
        decision, comments = parse_decision(feedback)

        if decision == "approved":
            result = {
                "draft_id": original_request["draft_id"],
                "decision": "approved",
                "approved_by": self._reviewer,
                "approved_at_utc": utc_now(),
                "simulated_ticket_id": f"SIM-{original_request['draft_id']}",
                "human_feedback": None,
                "message": (
                    "El borrador ha sido aprobado. "
                    "Se simula la creación del ticket, sin integración externa real."
                ),
                "ready_for_real_action": False,
            }

            write_audit_record(result)
            await ctx.yield_output(result)
            return

        if decision == "rejected":
            result = {
                "draft_id": original_request["draft_id"],
                "decision": "rejected",
                "approved_by": self._reviewer,
                "approved_at_utc": utc_now(),
                "simulated_ticket_id": None,
                "human_feedback": "rechazado",
                "message": "El operador ha rechazado el borrador. No se ejecuta ninguna acción.",
                "ready_for_real_action": False,
            }

            write_audit_record(result)
            await ctx.yield_output(result)
            return

        result = {
            "draft_id": original_request["draft_id"],
            "decision": "needs_revision",
            "approved_by": self._reviewer,
            "approved_at_utc": utc_now(),
            "simulated_ticket_id": None,
            "human_feedback": comments,
            "message": (
                "El operador ha pedido revisión del borrador. "
                "El workflow termina sin crear ticket simulado."
            ),
            "ready_for_real_action": False,
        }

        write_audit_record(result)
        await ctx.yield_output(result)

    async def on_checkpoint_save(self) -> dict[str, Any]:
        return {
            "reviewer": self._reviewer,
            "handled_drafts": self._handled_drafts,
        }

    async def on_checkpoint_restore(self, state: dict[str, Any]) -> None:
        self._reviewer = state.get("reviewer", self._reviewer)
        self._handled_drafts = state.get("handled_drafts", [])


def create_checkpoint_storage() -> FileCheckpointStorage:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    return FileCheckpointStorage(
        storage_path=str(CHECKPOINT_DIR),
    )


def build_incident_persistence_workflow():
    storage = create_checkpoint_storage()

    prepare_draft = PrepareTicketDraft()
    approval_gate = ApprovalGate(reviewer="operador.soporte")

    workflow = (
        WorkflowBuilder(
            name=WORKFLOW_NAME,
            start_executor=prepare_draft,
            checkpoint_storage=storage,
        )
        .add_edge(prepare_draft, approval_gate)
        .build()
    )

    return workflow, storage


async def get_latest_checkpoint_id(storage: FileCheckpointStorage) -> str | None:
    checkpoints = await storage.list_checkpoints(workflow_name=WORKFLOW_NAME)

    if not checkpoints:
        return None

    latest = sorted(checkpoints, key=lambda item: item.timestamp, reverse=True)[0]
    return latest.checkpoint_id


async def print_checkpoints(storage: FileCheckpointStorage) -> None:
    checkpoints = await storage.list_checkpoints(workflow_name=WORKFLOW_NAME)

    print("\n=== CHECKPOINTS ===")
    if not checkpoints:
        print("No hay checkpoints guardados.")
        return

    for checkpoint in sorted(checkpoints, key=lambda item: item.timestamp):
        print(f"{checkpoint.timestamp} | {checkpoint.checkpoint_id}")


def print_request(request_id: str, request: dict[str, Any]) -> None:
    print("\n=== APROBACIÓN PENDIENTE ===")
    print(f"request_id: {request_id}")
    print(f"draft_id: {request['draft_id']}")
    print(f"prioridad: {request['priority']}")
    print(f"servicio: {request['service']}")
    print(f"motivo: {request['priority_reason']}")
    print("\n--- BORRADOR ---")
    print(request["title"])
    print(request["description"])
    print("--- FIN BORRADOR ---")
    print(request["prompt"])


async def start_workflow(args: argparse.Namespace) -> None:
    workflow, storage = build_incident_persistence_workflow()

    incident = build_incident_input(
        description=args.description,
        reported_by=args.reported_by,
        users_affected=args.users_affected,
    )

    pending_requests: dict[str, dict[str, Any]] = {}
    completed_output: dict[str, Any] | None = None

    result = await workflow.run(incident)
    for event in result:
        if event.type == "request_info":
            pending_requests[event.request_id] = event.data

        if event.type == "output":
            completed_output = event.data

    if completed_output is not None:
        print("\n=== WORKFLOW COMPLETADO ===")
        print(json.dumps(completed_output, indent=2, ensure_ascii=False))
        await print_checkpoints(storage)
        return

    if pending_requests:
        latest_checkpoint_id = await get_latest_checkpoint_id(storage)

        print("\n=== WORKFLOW PAUSADO ===")
        print(f"checkpoint_id: {latest_checkpoint_id}")

        for request_id, request in pending_requests.items():
            print_request(request_id, request)

        print("\nPuedes cerrar el proceso y continuar después con:")
        print(
            "python -m src.workflows.incident_persistence_workflow resume "
            f"--checkpoint-id {latest_checkpoint_id} --decision approve"
        )

        await print_checkpoints(storage)
        return

    raise RuntimeError("El workflow terminó sin output y sin solicitudes pendientes.")


async def resume_workflow(args: argparse.Namespace) -> None:
    workflow, storage = build_incident_persistence_workflow()

    checkpoint_id = args.checkpoint_id

    if checkpoint_id is None:
        checkpoint_id = await get_latest_checkpoint_id(storage)

    if checkpoint_id is None:
        raise RuntimeError("No hay checkpoints disponibles para reanudar.")

    print(f"\nReanudando desde checkpoint: {checkpoint_id}")

    restored_requests: dict[str, dict[str, Any]] = {}

    result = list(workflow.run(checkpoint_id=checkpoint_id))
    for event in result:
        if event.type == "request_info":
            restored_requests[event.request_id] = event.data

        if event.type == "output":
            print("\n=== WORKFLOW YA TENÍA OUTPUT ===")
            print(json.dumps(event.data, indent=2, ensure_ascii=False))
            return

    if not restored_requests:
        raise RuntimeError("No se reemitieron solicitudes pendientes desde el checkpoint.")

    responses: dict[str, str] = {}

    for request_id, request in restored_requests.items():
        print_request(request_id, request)
        responses[request_id] = args.decision

    completed_output: dict[str, Any] | None = None

    async for event in workflow.send_responses_streaming(responses):
        if event.type == "output":
            completed_output = event.data

    if completed_output is None:
        raise RuntimeError("El workflow no produjo output después de enviar la respuesta.")

    print("\n=== RESULTADO FINAL ===")
    print(json.dumps(completed_output, indent=2, ensure_ascii=False))

    await print_checkpoints(storage)


async def list_workflow_checkpoints(_: argparse.Namespace) -> None:
    _, storage = build_incident_persistence_workflow()
    await print_checkpoints(storage)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Workflow MAF con persistencia de flujo mediante checkpoints."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument(
        "--description",
        required=True,
        help="Descripción de la incidencia.",
    )
    start_parser.add_argument(
        "--reported-by",
        default="usuario.lab@contoso.com",
        help="Usuario que reporta la incidencia.",
    )
    start_parser.add_argument(
        "--users-affected",
        type=int,
        default=None,
        help="Número de usuarios afectados.",
    )

    resume_parser = subparsers.add_parser("resume")
    resume_parser.add_argument(
        "--checkpoint-id",
        default=None,
        help="Checkpoint concreto. Si se omite, usa el último.",
    )
    resume_parser.add_argument(
        "--decision",
        required=True,
        help="approve, reject o comentario de revisión.",
    )

    subparsers.add_parser("list")

    args = parser.parse_args()

    if args.command == "start":
        await start_workflow(args)
    elif args.command == "resume":
        await resume_workflow(args)
    elif args.command == "list":
        await list_workflow_checkpoints(args)


if __name__ == "__main__":
    asyncio.run(main())