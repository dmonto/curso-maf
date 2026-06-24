from __future__ import annotations

import asyncio
from pathlib import Path

from src.agents.memory_aware_support_agent import build_memory_aware_support_agent
from src.memory.legacy_memory_migrator import migrate_legacy_memory
from src.memory.migrated_memory_store import MigratedMemoryStore, render_context_for_prompt


def render_response(response: object) -> str:
    for attr in ("text", "content", "message"):
        value = getattr(response, attr, None)
        if value:
            return str(value)

    value = getattr(response, "value", None)
    if value:
        return str(value)

    return str(response)


async def main() -> None:
    legacy_path = Path("src/legacy/legacy_memory_dump.json")

    migrated = migrate_legacy_memory(legacy_path)
    store = MigratedMemoryStore()
    store.save_many(migrated)

    context = store.build_context_for_agent(
        user_id="u-001",
        session_id="s-100",
    )

    agent = build_memory_aware_support_agent()

    prompt = f"""
Contexto migrado controlado:
{render_context_for_prompt(context)}

Petición actual del usuario:
Sigo sin poder acceder a la VPN. ¿Qué deberíamos hacer ahora?

Responde usando el contexto migrado solo si ayuda.
No muestres el JSON de memoria al usuario.
"""

    response = await agent.run(prompt)
    print(render_response(response))


if __name__ == "__main__":
    asyncio.run(main())