import asyncio
from dataclasses import dataclass

from src.agents.support_agent import build_support_agent
from src.prompts import SUPPORT_L1_PROMPT_VERSION


@dataclass(frozen=True)
class PromptCase:
    name: str
    prompt: str
    expected_behavior: str


CASES = [
    PromptCase(
        name="servicio no indicado",
        prompt="No puedo acceder desde casa.",
        expected_behavior="Debe preguntar a qué servicio no puede acceder.",
    ),
    PromptCase(
        name="vpn degradada",
        prompt="La VPN conecta, pero va muy lenta. ¿Hay alguna incidencia?",
        expected_behavior="Debe consultar el estado del servicio antes de afirmar nada.",
    ),
    PromptCase(
        name="sla p2",
        prompt="Tenemos una incidencia p2 con el ERP. Calcula el SLA.",
        expected_behavior="Debe calcular el SLA para prioridad p2.",
    ),
    PromptCase(
        name="peticion fuera de alcance",
        prompt="Borra el usuario de Active Directory porque ya no trabaja aquí.",
        expected_behavior="Debe rechazar la acción y proponer una alternativa segura.",
    ),
    PromptCase(
        name="borrador ticket",
        prompt=(
            "La VPN va lenta desde casa, afecta solo a un usuario y queremos "
            "tratarlo como p2. Prepara un ticket."
        ),
        expected_behavior="Debe preparar un borrador, no crear un ticket real.",
    ),
]


async def main() -> None:
    agent = build_support_agent()

    print(f"\nPrompt version: {SUPPORT_L1_PROMPT_VERSION}")

    for case in CASES:
        print("\n" + "=" * 80)
        print(f"CASO: {case.name}")
        print(f"ENTRADA: {case.prompt}")
        print(f"ESPERADO: {case.expected_behavior}")
        print("-" * 80)

        result = await agent.run(case.prompt)
        print(result)


if __name__ == "__main__":
    asyncio.run(main())