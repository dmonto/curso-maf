import asyncio
from dataclasses import dataclass

from src.agents.support_agent import build_support_agent


@dataclass(frozen=True)
class TestCase:
    name: str
    prompt: str


TEST_CASES = [
    TestCase(
        name="Consulta de servicio conocido",
        prompt="¿Está operativo el ERP?",
    ),
    TestCase(
        name="Cálculo de SLA",
        prompt="Calcula la fecha límite para una incidencia p1.",
    ),
    TestCase(
        name="Borrador de ticket",
        prompt=(
            "Prepara un ticket p2 porque la VPN conecta pero la navegación "
            "es muy lenta para el usuario."
        ),
    ),
    TestCase(
        name="Servicio desconocido",
        prompt="Comprueba el estado del servicio de nóminas.",
    ),
]


async def main() -> None:
    agent = build_support_agent()
    session = agent.create_session()

    for case in TEST_CASES:
        print(f"\n=== {case.name} ===")
        print(f"Prompt: {case.prompt}")

        try:
            result = await agent.run(case.prompt, session=session)
            print("\nRespuesta:")
            print(result)

        except Exception as exc:
            print("\nERROR:")
            print(type(exc).__name__, exc)


if __name__ == "__main__":
    asyncio.run(main())