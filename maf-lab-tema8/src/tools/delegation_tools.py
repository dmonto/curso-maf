from typing import Annotated

from agent_framework import tool
from pydantic import Field

from src.agents.multiagent.specialists import (
    build_identity_specialist,
    build_itsm_specialist,
    build_network_specialist,
)


async def _run_specialist(agent_builder, task: str) -> str:
    agent = agent_builder()
    result = await agent.run(task)
    return str(result)


@tool(
    name="consultar_especialista_red",
    description=(
        "Delega en el especialista de red/VPN una subtarea relacionada con conectividad, "
        "VPN, DNS, latencia, conexión remota o red local. No crea tickets ni modifica sistemas."
    ),
)
async def consultar_especialista_red(
    descripcion: Annotated[
        str,
        Field(
            description=(
                "Descripción concreta del problema de conectividad. "
                "Incluye servicio afectado, síntoma, ubicación, alcance y datos técnicos si existen."
            ),
            min_length=10,
        ),
    ],
) -> str:
    return await _run_specialist(build_network_specialist, descripcion)


@tool(
    name="consultar_especialista_identidad",
    description=(
        "Delega en el especialista de identidad una subtarea relacionada con MFA, "
        "bloqueo de cuenta, permisos, grupos o problemas de autenticación."
    ),
)
async def consultar_especialista_identidad(
    descripcion: Annotated[
        str,
        Field(
            description=(
                "Descripción concreta del problema de identidad o acceso. "
                "Incluye usuario, síntoma, aplicación afectada y contexto de autenticación si existe."
            ),
            min_length=10,
        ),
    ],
) -> str:
    return await _run_specialist(build_identity_specialist, descripcion)


@tool(
    name="consultar_especialista_itsm",
    description=(
        "Delega en el especialista ITSM la preparación de prioridad, resumen y datos mínimos "
        "para un posible ticket. No crea tickets reales."
    ),
)
async def consultar_especialista_itsm(
    descripcion: Annotated[
        str,
        Field(
            description=(
                "Descripción de la incidencia candidata a ticket. "
                "Incluye impacto, urgencia, servicio afectado y diagnóstico parcial si existe."
            ),
            min_length=10,
        ),
    ],
) -> str:
    return await _run_specialist(build_itsm_specialist, descripcion)