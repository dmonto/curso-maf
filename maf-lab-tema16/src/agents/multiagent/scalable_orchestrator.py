from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable

from src.agents.multiagent.scalable_specialists import (
    build_identity_specialist,
    build_itsm_specialist,
    build_network_specialist,
    build_security_specialist,
)


AgentBuilder = Callable[[], object]


@dataclass(frozen=True)
class SupportCase:
    case_id: str
    description: str
    priority_hint: str = "unknown"


@dataclass
class SpecialistCallResult:
    case_id: str
    specialist_name: str
    ok: bool
    elapsed_ms: int
    output: str | None = None
    error: str | None = None
    timed_out: bool = False


@dataclass
class CaseExecutionResult:
    case_id: str
    selected_specialists: list[str]
    specialist_results: list[SpecialistCallResult]
    elapsed_ms: int
    final_summary: str
    warnings: list[str] = field(default_factory=list)


SPECIALIST_BUILDERS: dict[str, AgentBuilder] = {
    "network_specialist": build_network_specialist,
    "identity_specialist": build_identity_specialist,
    "security_specialist": build_security_specialist,
    "itsm_specialist": build_itsm_specialist,
}


def select_specialists(case: SupportCase) -> list[str]:
    text = case.description.lower()
    selected: list[str] = []

    network_signals = ["vpn", "red", "dns", "latencia", "conectividad", "conecta lento"]
    identity_signals = ["mfa", "login", "acceso denegado", "permiso", "grupo", "autenticación"]
    security_signals = [
        "administrador",
        "admin",
        "externo",
        "datos sensibles",
        "borrar",
        "eliminar",
        "producción",
    ]
    itsm_signals = ["ticket", "incidencia", "p1", "p2", "urgente", "sla", "caído", "caida"]

    if any(signal in text for signal in network_signals):
        selected.append("network_specialist")

    if any(signal in text for signal in identity_signals):
        selected.append("identity_specialist")

    if any(signal in text for signal in security_signals):
        selected.append("security_specialist")

    if any(signal in text for signal in itsm_signals):
        selected.append("itsm_specialist")

    if not selected:
        selected.append("itsm_specialist")

    # Si hay seguridad, conviene que ITSM también prepare registro operativo.
    if "security_specialist" in selected and "itsm_specialist" not in selected:
        selected.append("itsm_specialist")

    return selected


async def run_specialist_with_limits(
    *,
    case: SupportCase,
    specialist_name: str,
    per_case_semaphore: asyncio.Semaphore,
    timeout_seconds: float,
) -> SpecialistCallResult:
    start = time.perf_counter()

    async with per_case_semaphore:
        try:
            agent_builder = SPECIALIST_BUILDERS[specialist_name]
            agent = agent_builder()

            prompt = (
                f"CASO: {case.case_id}\n\n"
                f"Descripción:\n{case.description}\n\n"
                "Analiza únicamente desde tu rol. "
                "No ejecutes acciones reales. "
                "Devuelve datos accionables y datos faltantes."
            )

            result = await asyncio.wait_for(
                agent.run(prompt),
                timeout=timeout_seconds,
            )

            elapsed_ms = int((time.perf_counter() - start) * 1000)

            return SpecialistCallResult(
                case_id=case.case_id,
                specialist_name=specialist_name,
                ok=True,
                elapsed_ms=elapsed_ms,
                output=str(result),
            )

        except asyncio.TimeoutError:
            elapsed_ms = int((time.perf_counter() - start) * 1000)

            return SpecialistCallResult(
                case_id=case.case_id,
                specialist_name=specialist_name,
                ok=False,
                elapsed_ms=elapsed_ms,
                error=f"Timeout tras {timeout_seconds} segundos",
                timed_out=True,
            )

        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)

            return SpecialistCallResult(
                case_id=case.case_id,
                specialist_name=specialist_name,
                ok=False,
                elapsed_ms=elapsed_ms,
                error=str(exc),
            )


def build_case_summary(
    *,
    case: SupportCase,
    selected_specialists: list[str],
    results: list[SpecialistCallResult],
    elapsed_ms: int,
) -> str:
    ok_results = [result for result in results if result.ok]
    failed_results = [result for result in results if not result.ok]

    lines = [
        f"case_id: {case.case_id}",
        f"especialistas_seleccionados: {', '.join(selected_specialists)}",
        f"tiempo_total_ms: {elapsed_ms}",
        "",
        "resultados:",
    ]

    for result in ok_results:
        lines.append(f"\n[{result.specialist_name}] OK en {result.elapsed_ms} ms")
        lines.append(result.output or "")

    for result in failed_results:
        lines.append(f"\n[{result.specialist_name}] ERROR en {result.elapsed_ms} ms")
        lines.append(result.error or "Error desconocido")

    if failed_results:
        lines.append(
            "\nAdvertencia: hay resultados parciales. "
            "No debe ejecutarse ninguna acción sensible sin completar validación."
        )

    return "\n".join(lines)


async def process_case(
    *,
    case: SupportCase,
    global_semaphore: asyncio.Semaphore,
    max_parallel_specialists_per_case: int,
    timeout_seconds: float,
) -> CaseExecutionResult:
    case_start = time.perf_counter()

    async with global_semaphore:
        selected_specialists = select_specialists(case)
        per_case_semaphore = asyncio.Semaphore(max_parallel_specialists_per_case)

        tasks = [
            run_specialist_with_limits(
                case=case,
                specialist_name=specialist_name,
                per_case_semaphore=per_case_semaphore,
                timeout_seconds=timeout_seconds,
            )
            for specialist_name in selected_specialists
        ]

        results = await asyncio.gather(*tasks)

        elapsed_ms = int((time.perf_counter() - case_start) * 1000)

        warnings = []

        if any(result.timed_out for result in results):
            warnings.append("Uno o más especialistas han excedido el timeout.")

        if any(not result.ok for result in results):
            warnings.append("La síntesis contiene resultados parciales.")

        if "security_specialist" in selected_specialists:
            warnings.append("Caso con revisión de seguridad: no ejecutar acciones sin aprobación.")

        final_summary = build_case_summary(
            case=case,
            selected_specialists=selected_specialists,
            results=results,
            elapsed_ms=elapsed_ms,
        )

        return CaseExecutionResult(
            case_id=case.case_id,
            selected_specialists=selected_specialists,
            specialist_results=results,
            elapsed_ms=elapsed_ms,
            final_summary=final_summary,
            warnings=warnings,
        )


async def process_cases_batch(
    *,
    cases: list[SupportCase],
    max_concurrent_cases: int = 3,
    max_parallel_specialists_per_case: int = 2,
    timeout_seconds: float = 30.0,
) -> list[CaseExecutionResult]:
    global_semaphore = asyncio.Semaphore(max_concurrent_cases)

    tasks = [
        process_case(
            case=case,
            global_semaphore=global_semaphore,
            max_parallel_specialists_per_case=max_parallel_specialists_per_case,
            timeout_seconds=timeout_seconds,
        )
        for case in cases
    ]

    return await asyncio.gather(*tasks)