from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import StrEnum

from src.agents.multiagent.collaborative_agents import (
    build_conflict_resolver,
    build_final_synthesizer,
    build_identity_agent,
    build_network_agent,
    build_security_reviewer,
    build_triage_agent,
)


class CollaborationPattern(StrEnum):
    SPECIALIST_CONSULTATION = "specialist_consultation"
    PROPOSAL_REVIEW = "proposal_review"
    CONTROLLED_DEBATE = "controlled_debate"


@dataclass(frozen=True)
class CollaborativeCase:
    case_id: str
    description: str


@dataclass
class AgentStep:
    agent_name: str
    purpose: str
    output: str
    elapsed_ms: int


@dataclass
class CollaborativeResult:
    case_id: str
    selected_pattern: CollaborationPattern
    steps: list[AgentStep]
    final_answer: str
    elapsed_ms: int
    warnings: list[str] = field(default_factory=list)


def select_collaboration_pattern(case: CollaborativeCase) -> CollaborationPattern:
    text = case.description.lower()

    risk_signals = [
        "administrador",
        "admin",
        "externo",
        "producción",
        "borrar",
        "eliminar",
        "datos sensibles",
        "permisos privilegiados",
    ]

    ambiguity_signals = [
        "no sé si",
        "puede ser",
        "vpn",
        "mfa",
        "acceso denegado",
        "a veces",
        "intermitente",
    ]

    if any(signal in text for signal in risk_signals):
        return CollaborationPattern.PROPOSAL_REVIEW

    if sum(1 for signal in ambiguity_signals if signal in text) >= 2:
        return CollaborationPattern.CONTROLLED_DEBATE

    return CollaborationPattern.SPECIALIST_CONSULTATION


async def _run_agent(agent_builder, prompt: str, purpose: str) -> AgentStep:
    start = time.perf_counter()
    agent = agent_builder()
    result = await agent.run(prompt)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    return AgentStep(
        agent_name=getattr(agent, "name", agent_builder.__name__),
        purpose=purpose,
        output=str(result),
        elapsed_ms=elapsed_ms,
    )


async def run_specialist_consultation(case: CollaborativeCase) -> list[AgentStep]:
    triage_prompt = (
        f"CASO {case.case_id}\n\n"
        f"{case.description}\n\n"
        "Clasifica el caso y recomienda siguiente acción."
    )

    triage_step = await _run_agent(
        build_triage_agent,
        triage_prompt,
        "Clasificar el caso y detectar dominio principal.",
    )

    return [triage_step]


async def run_proposal_review(case: CollaborativeCase) -> list[AgentStep]:
    triage_prompt = (
        f"CASO {case.case_id}\n\n"
        f"{case.description}\n\n"
        "Genera una propuesta operativa segura. "
        "No ejecutes acciones reales."
    )

    proposal_step = await _run_agent(
        build_triage_agent,
        triage_prompt,
        "Generar propuesta inicial.",
    )

    review_prompt = (
        f"CASO {case.case_id}\n\n"
        f"Petición original:\n{case.description}\n\n"
        f"Propuesta inicial:\n{proposal_step.output}\n\n"
        "Revisa la propuesta desde seguridad. "
        "Bloquea o pide cambios si hay acceso privilegiado, usuario externo, "
        "producción o acción irreversible."
    )

    review_step = await _run_agent(
        build_security_reviewer,
        review_prompt,
        "Revisar propuesta desde seguridad.",
    )

    return [proposal_step, review_step]


async def run_controlled_debate(case: CollaborativeCase) -> list[AgentStep]:
    identity_prompt = (
        f"CASO {case.case_id}\n\n"
        f"{case.description}\n\n"
        "Analiza únicamente desde identidad y acceso."
    )

    network_prompt = (
        f"CASO {case.case_id}\n\n"
        f"{case.description}\n\n"
        "Analiza únicamente desde red y VPN."
    )

    identity_step, network_step = await asyncio.gather(
        _run_agent(
            build_identity_agent,
            identity_prompt,
            "Analizar hipótesis de identidad.",
        ),
        _run_agent(
            build_network_agent,
            network_prompt,
            "Analizar hipótesis de red.",
        ),
    )

    resolver_prompt = (
        f"CASO {case.case_id}\n\n"
        f"Petición original:\n{case.description}\n\n"
        f"Resultado identidad:\n{identity_step.output}\n\n"
        f"Resultado red:\n{network_step.output}\n\n"
        "Resuelve si hay conflicto real o aparente. "
        "Propón siguiente acción segura."
    )

    resolver_step = await _run_agent(
        build_conflict_resolver,
        resolver_prompt,
        "Resolver conflicto entre hipótesis.",
    )

    return [identity_step, network_step, resolver_step]


async def synthesize_final_answer(
    *,
    case: CollaborativeCase,
    pattern: CollaborationPattern,
    steps: list[AgentStep],
) -> str:
    partials = "\n\n".join(
        [
            f"AGENTE: {step.agent_name}\n"
            f"PROPÓSITO: {step.purpose}\n"
            f"SALIDA:\n{step.output}"
            for step in steps
        ]
    )

    prompt = (
        f"CASO {case.case_id}\n\n"
        f"Patrón colaborativo usado: {pattern}\n\n"
        f"Petición original:\n{case.description}\n\n"
        f"Resultados parciales:\n{partials}\n\n"
        "Construye la respuesta final. "
        "Debe incluir:\n"
        "- patrón usado\n"
        "- agentes participantes\n"
        "- hechos conocidos\n"
        "- hipótesis o riesgos\n"
        "- datos pendientes\n"
        "- siguiente acción segura"
    )

    step = await _run_agent(
        build_final_synthesizer,
        prompt,
        "Sintetizar respuesta final.",
    )

    return step.output


async def run_collaborative_case(case: CollaborativeCase) -> CollaborativeResult:
    start = time.perf_counter()
    pattern = select_collaboration_pattern(case)
    warnings: list[str] = []

    if pattern == CollaborationPattern.SPECIALIST_CONSULTATION:
        steps = await run_specialist_consultation(case)

    elif pattern == CollaborationPattern.PROPOSAL_REVIEW:
        steps = await run_proposal_review(case)
        warnings.append(
            "Caso con revisión: no ejecutar acciones sensibles sin aprobación."
        )

    elif pattern == CollaborationPattern.CONTROLLED_DEBATE:
        steps = await run_controlled_debate(case)

    else:
        raise ValueError(f"Patrón no soportado: {pattern}")

    final_answer = await synthesize_final_answer(
        case=case,
        pattern=pattern,
        steps=steps,
    )

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    return CollaborativeResult(
        case_id=case.case_id,
        selected_pattern=pattern,
        steps=steps,
        final_answer=final_answer,
        elapsed_ms=elapsed_ms,
        warnings=warnings,
    )