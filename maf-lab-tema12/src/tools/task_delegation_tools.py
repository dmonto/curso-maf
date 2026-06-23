from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from agent_framework import tool
from pydantic import Field

from src.agents.multiagent.specialists import (
    build_identity_specialist,
    build_itsm_specialist,
    build_network_specialist,
)


SpecialistName = Literal[
    "network_specialist",
    "identity_specialist",
    "itsm_specialist",
]

RiskLevel = Literal["bajo", "medio", "alto"]


def _build_task_payload(
    *,
    specialist: SpecialistName,
    objective: str,
    context: str,
    constraints: str,
    expected_output: str,
    risk_level: RiskLevel,
) -> dict:
    return {
        "task_id": str(uuid4()),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_specialist": specialist,
        "objective": objective,
        "context": context,
        "constraints": constraints,
        "expected_output": expected_output,
        "risk_level": risk_level,
    }


def _format_task_for_specialist(task: dict) -> str:
    return (
        "TAREA DELEGADA\n\n"
        f"task_id: {task['task_id']}\n"
        f"especialista_destino: {task['target_specialist']}\n"
        f"objetivo: {task['objective']}\n"
        f"contexto: {task['context']}\n"
        f"limites: {task['constraints']}\n"
        f"salida_esperada: {task['expected_output']}\n"
        f"riesgo: {task['risk_level']}\n\n"
        "Responde únicamente dentro de tu dominio."
    )


async def _delegate_to_agent(agent_builder, task: dict) -> str:
    agent = agent_builder()
    prompt = _format_task_for_specialist(task)
    result = await agent.run(prompt)

    envelope = {
        "delegation": task,
        "specialist_result": str(result),
    }

    return json.dumps(envelope, ensure_ascii=False, indent=2)


@tool(
    name="delegar_tarea_red",
    description=(
        "Delega una tarea acotada al especialista de red/VPN. "
        "Úsala solo para conectividad, VPN, DNS, latencia o red local. "
        "No crea tickets ni modifica sistemas."
    ),
)
async def delegar_tarea_red(
    objetivo: Annotated[
        str,
        Field(
            description="Objetivo concreto de análisis para el especialista de red.",
            min_length=10,
        ),
    ],
    contexto: Annotated[
        str,
        Field(
            description="Contexto mínimo necesario: síntoma, servicio, alcance e impacto.",
            min_length=10,
        ),
    ],
    limites: Annotated[
        str,
        Field(
            description="Qué no debe hacer el especialista.",
            min_length=5,
        ),
    ] = "No modificar sistemas. No preparar tickets. No asumir datos no proporcionados.",
) -> str:
    task = _build_task_payload(
        specialist="network_specialist",
        objective=objetivo,
        context=contexto,
        constraints=limites,
        expected_output="diagnostico_probable, datos_faltantes, siguiente_comprobacion, confianza",
        risk_level="bajo",
    )
    return await _delegate_to_agent(build_network_specialist, task)


@tool(
    name="delegar_tarea_identidad",
    description=(
        "Delega una tarea acotada al especialista de identidad. "
        "Úsala para MFA, login, bloqueo de cuenta, permisos, grupos o autenticación."
    ),
)
async def delegar_tarea_identidad(
    objetivo: Annotated[
        str,
        Field(
            description="Objetivo concreto de análisis para identidad.",
            min_length=10,
        ),
    ],
    contexto: Annotated[
        str,
        Field(
            description="Contexto mínimo necesario: usuario, aplicación, síntoma y momento del fallo.",
            min_length=10,
        ),
    ],
    limites: Annotated[
        str,
        Field(
            description="Qué no debe hacer el especialista.",
            min_length=5,
        ),
    ] = "No cambiar permisos. No desbloquear cuentas. No solicitar credenciales.",
) -> str:
    task = _build_task_payload(
        specialist="identity_specialist",
        objective=objetivo,
        context=contexto,
        constraints=limites,
        expected_output="hipotesis_identidad, datos_faltantes, riesgo_seguridad, siguiente_comprobacion",
        risk_level="medio",
    )
    return await _delegate_to_agent(build_identity_specialist, task)


@tool(
    name="delegar_tarea_itsm",
    description=(
        "Delega una tarea acotada al especialista ITSM. "
        "Úsala cuando haya que proponer prioridad, resumen o datos mínimos para un ticket. "
        "No crea tickets reales."
    ),
)
async def delegar_tarea_itsm(
    objetivo: Annotated[
        str,
        Field(
            description="Objetivo concreto para preparar clasificación ITSM.",
            min_length=10,
        ),
    ],
    contexto: Annotated[
        str,
        Field(
            description="Contexto mínimo: servicio afectado, impacto, urgencia y diagnóstico parcial.",
            min_length=10,
        ),
    ],
    limites: Annotated[
        str,
        Field(
            description="Qué no debe hacer el especialista ITSM.",
            min_length=5,
        ),
    ] = "No crear ticket real. Solo preparar borrador y prioridad sugerida.",
) -> str:
    task = _build_task_payload(
        specialist="itsm_specialist",
        objective=objetivo,
        context=contexto,
        constraints=limites,
        expected_output="prioridad_sugerida, resumen_ticket, datos_minimos, justificacion_prioridad",
        risk_level="medio",
    )
    return await _delegate_to_agent(build_itsm_specialist, task)