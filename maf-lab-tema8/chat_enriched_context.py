import asyncio
import logging
import os

from src.agents.support_agent import build_structured_support_agent
from src.context import ContextEnricher
from src.state import SupportSessionMemory
from src.state.truncation import (
    ContextBlock,
    ContextTruncator,
    TruncationStrategy,
)


logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


POLITICAS_BASE = """
- No crear tickets reales sin confirmación explícita.
- No solicitar contraseñas, tokens ni secretos.
- No exponer datos personales innecesarios.
- Si el contexto enriquecido indica que el usuario no puede ejecutar una acción, prepara solo un borrador.
- Si existe una incidencia global, informa de ello antes de pedir pasos repetitivos.
""".strip()


def render_result(result: object) -> str:
    for attr in ("text", "content", "message"):
        value = getattr(result, attr, None)
        if value:
            return str(value)

    return str(result)


def build_prompt(
    user_text: str,
    memory: SupportSessionMemory,
    enriched_context_json: str,
) -> tuple[str, dict]:
    blocks = [
        ContextBlock(
            name="politicas_base",
            content=POLITICAS_BASE,
            priority=100,
            strategy=TruncationStrategy.NONE,
            required=True,
            max_chars=2500,
        ),
        ContextBlock(
            name="mensaje_actual",
            content=user_text,
            priority=95,
            strategy=TruncationStrategy.NONE,
            required=True,
            max_chars=2500,
        ),
        ContextBlock(
            name="memoria_estructurada",
            content=memory.to_model_context(),
            priority=85,
            strategy=TruncationStrategy.JSON_FIELDS,
            min_chars=800,
            max_chars=2500,
        ),
        ContextBlock(
            name="contexto_enriquecido",
            content=enriched_context_json,
            priority=80,
            strategy=TruncationStrategy.JSON_FIELDS,
            min_chars=800,
            max_chars=3000,
        ),
    ]

    truncator = ContextTruncator(
        max_context_tokens=5000,
        response_margin_tokens=1200,
    )

    truncated = truncator.truncate(blocks)

    prompt = f"""
Eres un agente de soporte técnico de nivel 1.

Usa el contexto enriquecido para responder con precisión.
No inventes datos que no estén en el contexto.
Distingue entre:
- datos aportados por el usuario;
- memoria de sesión;
- contexto enriquecido por sistemas externos;
- políticas de ejecución.

Si hay incidencia global del servicio, no repitas diagnósticos innecesarios.
Si el usuario no tiene permiso para una acción real, ofrece un borrador o siguiente paso seguro.

CONTEXTO FINAL:
{truncated.content}
""".strip()

    return prompt, truncated.report()


async def main() -> None:
    user_id = os.getenv("MAF_USER_ID", "usuario-demo")

    agent = build_structured_support_agent()
    memory = SupportSessionMemory()
    enricher = ContextEnricher()

    last_enriched_context = None
    last_truncation_report = None

    print("\nChat con enriquecimiento contextual")
    print(f"Usuario activo: {user_id}")
    print("Comandos:")
    print("  /memoria       muestra memoria estructurada")
    print("  /enriquecido   muestra último contexto enriquecido")
    print("  /truncado      muestra último reporte de truncado")
    print("  /salir         termina la sesión\n")

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

        if command == "/enriquecido":
            print("\n--- CONTEXTO ENRIQUECIDO ---")
            print(
                last_enriched_context.to_json()
                if last_enriched_context
                else "Todavía no hay contexto enriquecido."
            )
            print()
            continue

        if command == "/truncado":
            print("\n--- REPORTE DE TRUNCADO ---")
            print(last_truncation_report or "Todavía no hay reporte.")
            print()
            continue

        memory.update_from_user_text(user_text)

        enriched_context = enricher.enrich(
            user_id=user_id,
            user_text=user_text,
            memory_service=memory.servicio,
        )

        last_enriched_context = enriched_context

        prompt, truncation_report = build_prompt(
            user_text=user_text,
            memory=memory,
            enriched_context_json=enriched_context.to_json(),
        )

        last_truncation_report = truncation_report

        result = await agent.run(prompt)
        assistant_text = render_result(result)

        print("\nAgente>")
        print(assistant_text)
        print()


if __name__ == "__main__":
    asyncio.run(main())