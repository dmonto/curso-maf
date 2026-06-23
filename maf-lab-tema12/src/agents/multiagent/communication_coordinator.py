from __future__ import annotations

from uuid import uuid4

from src.agents.multiagent.communication import (
    InMemoryMailbox,
    InterAgentMessage,
    MessageType,
)
from src.agents.multiagent.specialists import (
    build_identity_specialist,
    build_itsm_specialist,
    build_security_specialist,
)


def _message_to_prompt(message: InterAgentMessage) -> str:
    payload = message.payload

    return (
        "MENSAJE INTERAGENTE\n\n"
        f"message_id: {message.message_id}\n"
        f"conversation_id: {message.conversation_id}\n"
        f"correlation_id: {message.correlation_id}\n"
        f"task_id: {message.task_id}\n"
        f"sender: {message.sender}\n"
        f"recipient: {message.recipient}\n"
        f"message_type: {message.message_type}\n\n"
        f"objetivo: {payload.get('objective')}\n"
        f"contexto: {payload.get('context')}\n"
        f"hechos_conocidos: {payload.get('known_facts')}\n"
        f"datos_desconocidos: {payload.get('unknowns')}\n\n"
        f"restricciones: {message.constraints}\n"
        f"salida_esperada: {message.expected_output}\n\n"
        "Responde únicamente dentro de tu dominio y respeta las restricciones."
    )


async def _send_to_specialist(
    *,
    mailbox: InMemoryMailbox,
    message: InterAgentMessage,
    agent_builder,
) -> InterAgentMessage:
    mailbox.publish(message)

    try:
        agent = agent_builder()
        prompt = _message_to_prompt(message)
        result = await agent.run(prompt)

        response = InterAgentMessage(
            sender=message.recipient,
            recipient=message.sender,
            message_type=MessageType.TASK_RESULT,
            conversation_id=message.conversation_id,
            correlation_id=message.correlation_id,
            task_id=message.task_id,
            payload={
                "request_message_id": message.message_id,
                "result": str(result),
            },
            constraints=[],
            expected_output=["result"],
        )

        mailbox.complete(response)
        return response

    except Exception as exc:
        return mailbox.fail(
            original_message=message,
            sender=message.recipient,
            error=str(exc),
        )


async def run_support_case_with_messages(user_request: str) -> dict:
    mailbox = InMemoryMailbox()

    conversation_id = str(uuid4())
    correlation_id = str(uuid4())

    coordinator_name = "support_coordinator"

    identity_message = InterAgentMessage(
        sender=coordinator_name,
        recipient="identity_specialist",
        message_type=MessageType.TASK_REQUEST,
        conversation_id=conversation_id,
        correlation_id=correlation_id,
        task_id="task-identity-001",
        payload={
            "objective": "Analizar si el problema puede deberse a permisos, grupos, MFA o autenticación.",
            "context": user_request,
            "known_facts": [
                "El usuario reporta problema de acceso",
                "No se debe modificar ningún permiso en esta fase",
            ],
            "unknowns": [
                "grupo actual del usuario",
                "mensaje exacto de error",
                "si el acceso falla también desde oficina",
            ],
        },
        constraints=[
            "No modificar permisos",
            "No desbloquear cuentas",
            "No solicitar credenciales",
        ],
        expected_output=[
            "hipotesis",
            "evidencias",
            "datos_faltantes",
            "siguiente_comprobacion",
            "confianza",
        ],
    )

    security_message = InterAgentMessage(
        sender=coordinator_name,
        recipient="security_specialist",
        message_type=MessageType.VALIDATION_REQUEST,
        conversation_id=conversation_id,
        correlation_id=correlation_id,
        task_id="task-security-001",
        payload={
            "objective": "Evaluar si el caso implica riesgo de seguridad o restricciones de acceso.",
            "context": user_request,
            "known_facts": [
                "Puede haber acceso a ERP",
                "Puede implicar permisos o datos financieros",
            ],
            "unknowns": [
                "nivel de privilegio solicitado",
                "responsable aprobador",
                "sensibilidad exacta del dato",
            ],
        },
        constraints=[
            "No aprobar accesos",
            "No recomendar permisos privilegiados sin validación",
        ],
        expected_output=[
            "riesgo_detectado",
            "severidad",
            "restriccion_aplicable",
            "accion_segura",
        ],
    )

    identity_response = await _send_to_specialist(
        mailbox=mailbox,
        message=identity_message,
        agent_builder=build_identity_specialist,
    )

    security_response = await _send_to_specialist(
        mailbox=mailbox,
        message=security_message,
        agent_builder=build_security_specialist,
    )

    itsm_context = (
        "Petición original:\n"
        f"{user_request}\n\n"
        "Resultado identidad:\n"
        f"{identity_response.payload.get('result')}\n\n"
        "Resultado seguridad:\n"
        f"{security_response.payload.get('result')}"
    )

    itsm_message = InterAgentMessage(
        sender=coordinator_name,
        recipient="itsm_specialist",
        message_type=MessageType.TASK_REQUEST,
        conversation_id=conversation_id,
        correlation_id=correlation_id,
        task_id="task-itsm-001",
        payload={
            "objective": "Proponer prioridad y resumen de ticket sin crear ticket real.",
            "context": itsm_context,
            "known_facts": [
                "Hay análisis preliminar de identidad",
                "Hay revisión preliminar de seguridad",
            ],
            "unknowns": [
                "impacto exacto",
                "usuarios afectados",
                "ventana temporal",
            ],
        },
        constraints=[
            "No crear ticket real",
            "No prometer resolución",
            "No recomendar cambios de permisos sin aprobación",
        ],
        expected_output=[
            "prioridad_sugerida",
            "resumen_ticket",
            "datos_minimos",
            "justificacion",
        ],
    )

    itsm_response = await _send_to_specialist(
        mailbox=mailbox,
        message=itsm_message,
        agent_builder=build_itsm_specialist,
    )

    return {
        "conversation_id": conversation_id,
        "correlation_id": correlation_id,
        "identity_result": identity_response.payload.get("result"),
        "security_result": security_response.payload.get("result"),
        "itsm_result": itsm_response.payload.get("result"),
        "trace": mailbox.trace_as_text(correlation_id),
    }