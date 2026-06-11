import asyncio
import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Annotated, Literal

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential
from pydantic import Field


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")
    return value


@dataclass
class EstadoIncidencia:
    servicio: str | None = None
    descripcion: str | None = None
    ubicacion: str | None = None
    usuarios_afectados: int | None = None
    prioridad: str | None = None
    ticket_preparado: bool = False


ESTADO = EstadoIncidencia()


def actualizar_estado_desde_texto(texto: str) -> None:
    """
    Parser simple para demo.
    En producción, esta lógica puede moverse a tools, validadores,
    extracción estructurada o workflows.
    """
    t = texto.lower()

    if "vpn" in t:
        ESTADO.servicio = "vpn"
    elif "correo" in t or "outlook" in t or "email" in t:
        ESTADO.servicio = "correo"
    elif "teams" in t:
        ESTADO.servicio = "teams"
    elif "erp" in t:
        ESTADO.servicio = "erp"

    if "casa" in t or "remoto" in t:
        ESTADO.ubicacion = "remoto"
    elif "oficina" in t:
        ESTADO.ubicacion = "oficina"

    if ESTADO.descripcion is None and len(texto.strip()) > 10:
        ESTADO.descripcion = texto.strip()

    match = re.search(r"(\d+)\s+(usuarios|personas|compañeros|companeros)", t)
    if match:
        ESTADO.usuarios_afectados = int(match.group(1))
    elif "solo a mí" in t or "solo a mi" in t:
        ESTADO.usuarios_afectados = 1

    if "prioridad alta" in t or "urgente" in t:
        ESTADO.prioridad = "alta"
    elif "prioridad media" in t:
        ESTADO.prioridad = "media"
    elif "prioridad baja" in t:
        ESTADO.prioridad = "baja"


@tool(
    name="leer_estado_incidencia",
    description=(
        "Devuelve el estado estructurado de la incidencia que se está recopilando "
        "en la conversación actual. Úsala cuando necesites saber qué datos ya se conocen."
    ),
    approval_mode="never_require",
)
def leer_estado_incidencia() -> str:
    return json.dumps(asdict(ESTADO), ensure_ascii=False)


@tool(
    name="validar_datos_para_ticket",
    description=(
        "Valida si hay datos suficientes para preparar un ticket de soporte. "
        "Úsala antes de preparar un ticket."
    ),
    approval_mode="never_require",
)
def validar_datos_para_ticket() -> str:
    pendientes: list[str] = []

    if not ESTADO.servicio:
        pendientes.append("servicio")
    if not ESTADO.descripcion:
        pendientes.append("descripcion")
    if not ESTADO.ubicacion:
        pendientes.append("ubicacion")
    if ESTADO.usuarios_afectados is None:
        pendientes.append("usuarios_afectados")

    return json.dumps(
        {
            "datos_suficientes": len(pendientes) == 0,
            "campos_pendientes": pendientes,
            "estado_actual": asdict(ESTADO),
        },
        ensure_ascii=False,
    )


@tool(
    name="preparar_borrador_ticket",
    description=(
        "Prepara un borrador de ticket con el estado actual de la incidencia. "
        "No crea el ticket en ningún sistema real."
    ),
    approval_mode="never_require",
)
def preparar_borrador_ticket(
    prioridad: Annotated[
        Literal["baja", "media", "alta"],
        Field(description="Prioridad recomendada para el ticket."),
    ],
) -> str:
    ESTADO.prioridad = prioridad
    ESTADO.ticket_preparado = True

    return json.dumps(
        {
            "accion": "borrador_ticket",
            "servicio": ESTADO.servicio,
            "descripcion": ESTADO.descripcion,
            "ubicacion": ESTADO.ubicacion,
            "usuarios_afectados": ESTADO.usuarios_afectados,
            "prioridad": ESTADO.prioridad,
            "estado": "pendiente_de_confirmacion",
        },
        ensure_ascii=False,
    )


def construir_instrucciones() -> str:
    return (
        "Eres un agente de soporte técnico de nivel 1. "
        "Debes manejar conversaciones multi-turno sin perder el contexto. "
        "Usa leer_estado_incidencia cuando necesites comprobar qué datos ya conoces. "
        "Usa validar_datos_para_ticket antes de preparar cualquier ticket. "
        "Usa preparar_borrador_ticket solo si hay datos suficientes. "
        "No digas que has creado un ticket real, solo puedes preparar un borrador. "
        "Si falta información, pregunta solo por el dato pendiente más importante. "
        "Responde de forma breve y operativa."
    )


async def main() -> None:
    project_endpoint = require_env("AZURE_OPENAI_ENDPOINT")
    model = os.getenv("AZURE_OPENAI_DEPLOYMENT_CHAT", "gpt-4o")

    client = FoundryChatClient(
        project_endpoint=project_endpoint,
        model=model,
        credential=AzureCliCredential(),
    )

    agent = Agent(
        client=client,
        name="AgenteContextoSoporte",
        instructions=construir_instrucciones(),
        tools=[
            leer_estado_incidencia,
            validar_datos_para_ticket,
            preparar_borrador_ticket,
        ],
    )

    session = agent.create_session()

    print("Agente listo. Escribe 's' para salir.\n")

    while True:
        mensaje = input("Usuario> ").strip()

        if mensaje.lower() in {"s", "salir", "exit", "quit"}:
            print("Fin de la conversación.")
            break

        actualizar_estado_desde_texto(mensaje)

        respuesta = await agent.run(mensaje, session=session)

        print("\nAgente>")
        print(respuesta)

        print("\n[Estado estructurado interno]")
        print(json.dumps(asdict(ESTADO), indent=2, ensure_ascii=False))
        print("-" * 80)


if __name__ == "__main__":
    asyncio.run(main())