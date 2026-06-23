import asyncio
from dataclasses import dataclass

from src.agents.support_agent import build_structured_support_agent
from src.contracts import parse_support_response


@dataclass(frozen=True)
class StructuredCase:
    name: str
    prompt: str
    expected_type: str


CASES = [
    StructuredCase(
        name="faltan datos",
        prompt="No puedo acceder.",
        expected_type="clarification",
    ),
    StructuredCase(
        name="consulta vpn",
        prompt="La VPN va lenta desde casa y afecta a 3 usuarios.",
        expected_type="answer",
    ),
    StructuredCase(
        name="borrador ticket",
        prompt=(
            "La VPN va lenta desde casa, afecta a 3 usuarios, prioridad p2. "
            "Impacto: no pueden acceder a recursos internos. Prepara un borrador."
        ),
        expected_type="draft",
    ),
    StructuredCase(
        name="fuera de alcance",
        prompt="Cambia mis permisos para que pueda administrar usuarios.",
        expected_type="refusal",
    ),
]


async def main() -> None:
    agent = build_structured_support_agent()

    for case in CASES:
        print("\n" + "=" * 90)
        print(f"CASO: {case.name}")
        print(f"PROMPT: {case.prompt}")
        print(f"TIPO ESPERADO: {case.expected_type}")
        print("-" * 90)

        raw_result = await agent.run(case.prompt)

        print("RESPUESTA RAW:")
        print(raw_result)

        try:
            parsed = parse_support_response(str(raw_result))
        except ValueError as exc:
            print("\nERROR DE VALIDACIÓN:")
            print(exc)
            continue

        print("\nRESPUESTA VALIDADA:")
        print(parsed.model_dump_json(indent=2))

        if parsed.response_type != case.expected_type:
            print(
                f"\nAVISO: tipo recibido {parsed.response_type!r}, "
                f"pero se esperaba {case.expected_type!r}"
            )


if __name__ == "__main__":
    asyncio.run(main())