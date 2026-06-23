import asyncio
import json

from src.agents.support_agent import build_support_agent


USERS = {
    "support": {
        "user_id": "ana@curso.local",
        "tenant_id": "curso-maf",
        "groups": ["support-l1"],
    },
    "hr": {
        "user_id": "beatriz@curso.local",
        "tenant_id": "curso-maf",
        "groups": ["hr-managers"],
    },
    "basic": {
        "user_id": "carlos@curso.local",
        "tenant_id": "curso-maf",
        "groups": [],
    },
}


async def ask(agent, user_key: str, question: str) -> None:
    user_context = USERS[user_key]

    prompt = f"""
Contexto autenticado del usuario:
{json.dumps(user_context, ensure_ascii=False)}

Pregunta:
{question}

Usa recuperación documental con control de permisos si necesitas consultar documentación interna.
"""

    print("\n" + "=" * 80)
    print(f"Perfil: {user_key}")
    print(f"Pregunta: {question}")
    print("-" * 80)

    result = await agent.run(prompt)
    print(result)


async def main() -> None:
    agent = build_support_agent()

    await ask(
        agent,
        "support",
        "¿Qué pasos sigo si no puedo acceder a la VPN desde Windows 11?",
    )

    await ask(
        agent,
        "basic",
        "¿Qué pasos sigo si no puedo acceder a la VPN desde Windows 11?",
    )

    await ask(
        agent,
        "support",
        "¿Qué dice el procedimiento disciplinario interno?",
    )

    await ask(
        agent,
        "hr",
        "¿Qué dice el procedimiento disciplinario interno?",
    )

    await ask(
        agent,
        "basic",
        "¿Cómo se clasifican las prioridades P1, P2 y P3?",
    )


if __name__ == "__main__":
    asyncio.run(main())