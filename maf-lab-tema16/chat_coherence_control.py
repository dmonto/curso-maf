import asyncio
import logging
import os
from typing import Any

from src.agents.support_agent import build_structured_support_agent
from src.context import ContextEnricher
from src.state import SupportSessionMemory
from src.state.coherence import CoherenceController, build_blocking_response


logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def render_result(result: object) -> str:
    for attr in ("text", "content", "message"):
        value = getattr(result, attr, None)
        if value:
            return str(value)

    return str(result)


def build_prompt(
    user_text: str,
    memory: SupportSessionMemory,
    enriched_context: dict[str, Any],
    coherence_block: str,
) -> str:
    return f"""
Eres un agente de soporte técnico de nivel 1.

Usa el contexto disponible, pero respeta el reporte de coherencia.
Si el reporte contiene warnings, responde con cautela.
No inventes datos.
No digas que has creado un ticket real. Como máximo puedes preparar un borrador.

MEMORIA ESTRUCTURADA:
{memory.to_model_context()}

CONTEXTO ENRIQUECIDO:
{enriched_context}

REPORTE DE COHERENCIA:
{coherence_block}

MENSAJE ACTUAL:
{user_text}
""".strip()


async def main() -> None:
    user_id = os.getenv("MAF_USER_ID", "usuario-demo")

    agent = build_structured_support_agent()
    enricher = ContextEnricher()
    coherence = CoherenceController()
    memory = SupportSessionMemory()

    distributed_metadata: dict[str, Any] = {
        "status": "open",
        "turn_count": 0,
    }

    last_report = None
    last_enriched_context = None

    print("\nChat con control de coherencia")
    print(f"Usuario activo: {user_id}")
    print("Comandos:")
    print("  /memoria      muestra memoria")
    print("  /coherencia   muestra último reporte")
    print("  /cerrar       marca el caso como cerrado")
    print("  /reabrir      reabre el caso")
    print("  /salir        termina\n")

    while True:
        user_text = input("Tú> ").strip()

        if not user_text:
            continue

        command = user_text.lower()

        if command == "/salir":
            print("Sesión finalizada.")
            break

        if command == "/memoria":
            print("\n--- MEMORIA ---")
            print(memory.to_json())
            print()
            continue

        if command == "/coherencia":
            print("\n--- COHERENCIA ---")
            print(
                last_report.to_dict()
                if last_report
                else "Todavía no hay reporte."
            )
            print()
            continue

        if command == "/cerrar":
            distributed_metadata["status"] = "closed"
            print("Caso marcado como cerrado.\n")
            continue

        if command == "/reabrir":
            distributed_metadata["status"] = "open"
            print("Caso reabierto.\n")
            continue

        memory.update_from_user_text(user_text)

        enriched = enricher.enrich(
            user_id=user_id,
            user_text=user_text,
            memory_service=memory.servicio,
        )

        last_enriched_context = enriched.to_dict()

        report = coherence.validate(
            user_text=user_text,
            memory=memory.to_dict(),
            enriched_context=last_enriched_context,
            distributed_metadata=distributed_metadata,
        )

        last_report = report

        if report.has_blocking:
            print("\nAgente>")
            print(build_blocking_response(report))
            print()
            continue

        prompt = build_prompt(
            user_text=user_text,
            memory=memory,
            enriched_context=last_enriched_context,
            coherence_block=report.to_prompt_block(),
        )

        result = await agent.run(prompt)
        assistant_text = render_result(result)

        distributed_metadata["turn_count"] = int(
            distributed_metadata.get("turn_count", 0)
        ) + 1

        print("\nAgente>")
        print(assistant_text)
        print()


if __name__ == "__main__":
    asyncio.run(main())