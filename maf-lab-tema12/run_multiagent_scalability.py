import asyncio
import logging

from src.agents.multiagent.scalable_orchestrator import (
    SupportCase,
    process_cases_batch,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main() -> None:
    cases = [
        SupportCase(
            case_id="case-001",
            description=(
                "Un usuario de Finanzas no puede acceder al ERP desde casa. "
                "La VPN conecta correctamente, pero aparece acceso denegado."
            ),
        ),
        SupportCase(
            case_id="case-002",
            description=(
                "La VPN va muy lenta para un usuario desde casa. "
                "No hay error de MFA y puede trabajar parcialmente."
            ),
        ),
        SupportCase(
            case_id="case-003",
            description=(
                "Un proveedor externo solicita acceso administrador temporal "
                "al ERP para revisar una incidencia urgente."
            ),
        ),
        SupportCase(
            case_id="case-004",
            description=(
                "El ERP está caído para todo Finanzas durante cierre contable. "
                "Piden abrir incidencia P1."
            ),
        ),
    ]

    results = await process_cases_batch(
        cases=cases,
        max_concurrent_cases=2,
        max_parallel_specialists_per_case=2,
        timeout_seconds=30.0,
    )

    for result in results:
        print("\n" + "=" * 80)
        print(result.final_summary)

        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"- {warning}")


if __name__ == "__main__":
    asyncio.run(main())