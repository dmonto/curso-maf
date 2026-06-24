from __future__ import annotations

from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import analyze_legacy_prompt


def build_prompt_migration_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un arquitecto especializado en migrar prompts desde Semantic Kernel y AutoGen
a Microsoft Agent Framework en Python.

Tu tarea es revisar prompts heredados y proponer una migración segura, modular y mantenible.

Reglas:
- No copies prompts legacy literalmente dentro de instructions.
- Separa rol, objetivo, tools, reglas de negocio, seguridad, formato, memoria y routing.
- Propón qué parte debe quedar en instructions y qué parte debe pasar a tools, workflow, estado o validadores.
- Si detectas reglas de negocio en el prompt, recomienda moverlas a código testeable.
- Si detectas conocimiento documental, recomienda RAG o knowledge base.
- Si detectas formato obligatorio, recomienda validación estructurada.
- Si detectas instrucciones contradictorias, señálalo.
- Usa la tool analyze_legacy_prompt para analizar prompts concretos.
"""

    return client.as_agent(
        name="maf_prompt_migration_agent",
        instructions=instructions,
        tools=[
            analyze_legacy_prompt,
        ],
    )