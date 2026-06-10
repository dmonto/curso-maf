import asyncio
import json
import os
import time
from typing import Annotated

from azure.identity import AzureCliCredential
from agent_framework import tool
from agent_framework.foundry import FoundryChatClient
from pydantic import Field


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")
    return value


def emit_event(event_type: str, **payload) -> None:
    """
    En una solución real, esto iría a logs estructurados,
    OpenTelemetry o Application Insights.
    """
    event = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": event_type,
        **payload,
    }
    print(json.dumps(event, ensure_ascii=False))


@tool(
    name="classify_support_incident",
    description=(
        "Clasifica una incidencia de soporte IT y recomienda la siguiente acción. "
        "No crea tickets reales."
    ),
    approval_mode="never_require",
)
def classify_support_incident(
    message: Annotated[
        str,
        Field(description="Mensaje original del usuario con la incidencia.")
    ],
) -> dict:
    emit_event("tool_invoked", tool="classify_support_incident")

    text = message.lower()

    if "vpn" in text:
        category = "vpn"
    elif "correo" in text or "outlook" in text or "email" in text:
        category = "correo"
    elif "contraseña" in text or "password" in text:
        category = "identidad"
    else:
        category = "otro"

    if "bloqueado" in text or "urgente" in text or "no puedo trabajar" in text:
        priority = "alta"
    elif "lento" in text or "a veces" in text:
        priority = "media"
    else:
        priority = "baja"

    missing_fields: list[str] = []

    if category == "vpn" and "portátil" not in text:
        missing_fields.append("dispositivo")

    if category == "correo" and "error" not in text:
        missing_fields.append("mensaje_error")

    if missing_fields:
        next_action = "pedir_datos"
    elif priority == "alta":
        next_action = "revision_humana"
    else:
        next_action = "crear_ticket"

    result = {
        "category": category,
        "priority": priority,
        "missing_fields": missing_fields,
        "next_action": next_action,
    }

    emit_event(
        "tool_completed",
        tool="classify_support_incident",
        result=result,
    )

    return result


async def build_agent():
    project_endpoint = require_env("AZURE_AI_PROJECT_ENDPOINT")
    model = require_env("AZURE_OPENAI_DEPLOYMENT_CHAT")

    credential = AzureCliCredential()

    client = FoundryChatClient(
        project_endpoint=project_endpoint,
        model=model,
        credential=credential,
    )

    agent = client.as_agent(
        name="ExecutionModelSupportAgent",
        instructions=(
            "Eres un agente de soporte IT de primer nivel. "
            "Debes usar siempre la tool classify_support_incident antes de responder. "
            "Después explica en español: categoría, prioridad, datos faltantes y siguiente acción. "
            "Si faltan datos, no inventes. Pide la información necesaria. "
            "Si la prioridad es alta, indica que requiere revisión humana antes de automatizar acciones. "
            "No digas que has creado un ticket real."
        ),
        tools=[classify_support_incident],
    )

    return agent


async def run_case(agent, message: str) -> None:
    emit_event("agent_run_started", user_message=message)

    result = await agent.run(message)

    emit_event("agent_run_completed")

    print("\nRespuesta final del agente:\n")
    print(result.text if hasattr(result, "text") else str(result))


async def main() -> None:
    agent = await build_agent()

    cases = [
        "No puedo conectarme a la VPN desde el portátil y estoy bloqueado.",
        "Outlook va lento desde esta mañana.",
        "Necesito cambiar mi contraseña.",
    ]

    for case in cases:
        print("\n" + "=" * 100)
        await run_case(agent, case)


if __name__ == "__main__":
    asyncio.run(main())