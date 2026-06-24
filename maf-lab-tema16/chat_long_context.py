import asyncio
import logging

from src.agents.support_agent import build_structured_support_agent
from src.models.factory import create_chat_client
from src.settings import get_settings
from src.state import SupportSessionMemory
from src.state.long_context import LongContextManager


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


def build_summarizer_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name="context_summarizer",
        instructions=(
            "Eres un compactador de contexto para conversaciones de soporte técnico. "
            "Produces resúmenes breves, fieles y operativos. "
            "No inventes datos. No añadas recomendaciones que no estén soportadas."
        ),
    )


async def compact_if_needed(
    context_manager: LongContextManager,
    summarizer_agent,
) -> None:
    if not context_manager.needs_compaction():
        return

    turns_to_compact, kept_turns = context_manager.split_turns_for_compaction()

    if not turns_to_compact:
        return

    prompt = context_manager.build_compaction_prompt(turns_to_compact)
    result = await summarizer_agent.run(prompt)
    new_summary = render_result(result)

    context_manager.apply_compaction(
        new_summary=new_summary,
        kept_turns=kept_turns,
    )


def build_agent_prompt(
    user_text: str,
    memory: SupportSessionMemory,
    context_manager: LongContextManager,
) -> str:
    context_package = context_manager.build_context_package(
        memory_json=memory.to_model_context(),
    )

    return f"""
Eres un agente de soporte técnico de nivel 1.

Usa el paquete de contexto para mantener continuidad en una conversación larga.
No asumas que tienes todo el historial completo.
Prioriza:
1. mensaje actual del usuario;
2. memoria estructurada;
3. resumen acumulado;
4. últimos turnos.

No repitas preguntas ya respondidas.
Si falta información crítica, pregunta de forma concreta.
No digas que has creado un ticket real. Como máximo puedes preparar un borrador.

PAQUETE DE CONTEXTO:
{context_package}

MENSAJE ACTUAL:
{user_text}
""".strip()


async def main() -> None:
    support_agent = build_structured_support_agent()
    summarizer_agent = build_summarizer_agent()

    memory = SupportSessionMemory()
    context_manager = LongContextManager(
        max_recent_turns=6,
        max_context_chars=5000,
    )

    print("\nChat con gestión de contexto largo")
    print("Comandos:")
    print("  /memoria   muestra memoria estructurada")
    print("  /contexto  muestra paquete de contexto")
    print("  /stats     muestra métricas de contexto")
    print("  /resumen   muestra resumen acumulado")
    print("  /salir     termina la sesión\n")

    while True:
        user_text = input("Tú> ").strip()

        if not user_text:
            continue

        command = user_text.lower()

        if command == "/salir":
            print("Sesión finalizada.")
            break

        if command == "/memoria":
            print("\n--- MEMORIA ESTRUCTURADA ---")
            print(memory.to_json())
            print()
            continue

        if command == "/contexto":
            print("\n--- PAQUETE DE CONTEXTO ---")
            print(
                context_manager.build_context_package(
                    memory_json=memory.to_model_context()
                )
            )
            print()
            continue

        if command == "/stats":
            print("\n--- STATS CONTEXTO ---")
            print(context_manager.stats())
            print()
            continue

        if command == "/resumen":
            print("\n--- RESUMEN ACUMULADO ---")
            print(context_manager.state.rolling_summary or "Todavía no hay resumen.")
            print()
            continue

        memory.update_from_user_text(user_text)
        context_manager.add_turn("user", user_text)

        await compact_if_needed(
            context_manager=context_manager,
            summarizer_agent=summarizer_agent,
        )

        prompt = build_agent_prompt(
            user_text=user_text,
            memory=memory,
            context_manager=context_manager,
        )

        result = await support_agent.run(prompt)
        assistant_text = render_result(result)

        context_manager.add_turn("assistant", assistant_text)

        await compact_if_needed(
            context_manager=context_manager,
            summarizer_agent=summarizer_agent,
        )

        print("\nAgente>")
        print(assistant_text)
        print()


if __name__ == "__main__":
    asyncio.run(main())