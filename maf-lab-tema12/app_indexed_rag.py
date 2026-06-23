import asyncio

from src.agents.support_agent_rag_ind import build_support_agent
from src.rag.document_indexer import build_document_index


async def main() -> None:
    print("\n--- ACTUALIZANDO ÍNDICE ---")
    build_document_index()

    agent = build_support_agent()

    prompt = """
Un usuario no puede acceder a la VPN desde Windows 11.
Dice que tiene Internet y que solo le pasa a él.
¿Qué pasos debería seguir soporte y qué prioridad tendría normalmente?
"""

    print("\n--- RESPUESTA DEL AGENTE ---")
    result = await agent.run(prompt)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())