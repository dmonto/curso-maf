from __future__ import annotations

import asyncio

from src.agents.migration_architecture_agent import build_migration_architecture_agent


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
    agent = build_migration_architecture_agent()

    prompt = """
Tenemos una solución legacy de soporte IT construida con una mezcla de Semantic Kernel
y AutoGen.

Componentes actuales:
1. support_kernel: registra modelo, plugins, prompts y memoria.
2. TicketPlugin: consulta tickets y crea borradores en el sistema ITSM.
3. KnowledgePlugin: busca documentación interna.
4. classify_incident_prompt: clasifica la petición del usuario.
5. AutoGen GroupChat: coordina triage_agent, network_agent, security_agent y summary_agent.
6. speaker_selector: decide qué agente habla en cada turno.
7. chat_history: se usa como historial completo y también como estado del caso.
8. print_logger: escribe trazas básicas por consola.

Propón una arquitectura destino en MAF.
Indica qué se convierte en agente, tool, workflow, estado, memoria o telemetría.
También indica qué NO migrarías de forma directa.
"""

    response = await agent.run(prompt)
    print(render_response(response))


if __name__ == "__main__":
    asyncio.run(main())