import asyncio
import logging

from src.agents.multiagent.collaborative_patterns import (
    CollaborativeCase,
    run_collaborative_case,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main() -> None:
    cases = [
        CollaborativeCase(
            case_id="case-simple",
            description=(
                "Un usuario pregunta qué datos debe aportar para abrir una incidencia "
                "porque no accede al ERP."
            ),
        ),
        CollaborativeCase(
            case_id="case-risk",
            description=(
                "Un proveedor externo solicita acceso administrador temporal al ERP "
                "en producción para resolver una incidencia urgente."
            ),
        ),
        CollaborativeCase(
            case_id="case-ambiguous",
            description=(
                "Un usuario no puede entrar al ERP desde casa. "
                "La VPN conecta, pero aparece acceso denegado. "
                "No sé si puede ser VPN, MFA o permisos."
            ),
        ),
    ]

    for case in cases:
        result = await run_collaborative_case(case)

        print("\n" + "=" * 90)
        print(f"CASE: {result.case_id}")
        print(f"PATRÓN: {result.selected_pattern}")
        print(f"TIEMPO TOTAL: {result.elapsed_ms} ms")

        print("\n--- PASOS ---")
        for step in result.steps:
            print(f"\n[{step.agent_name}] {step.purpose} ({step.elapsed_ms} ms)")
            print(step.output)

        if result.warnings:
            print("\n--- WARNINGS ---")
            for warning in result.warnings:
                print(f"- {warning}")

        print("\n--- RESPUESTA FINAL ---")
        print(result.final_answer)


if __name__ == "__main__":
    asyncio.run(main())