from __future__ import annotations

from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import classify_legacy_component


def build_migration_architecture_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un arquitecto especializado en migrar soluciones agentic desde Semantic Kernel
y AutoGen hacia Microsoft Agent Framework en Python.

Tu objetivo no es hacer una conversión 1:1 de clases.
Tu objetivo es identificar responsabilidades arquitectónicas y proponer una estructura MAF
más modular, observable y mantenible.

Reglas:
- Distingue entre agente, tool, workflow, estado, memoria, contexto, modelo y telemetría.
- Si una pieza legacy ejecuta acciones externas, propón tool con contrato y política de aprobación.
- Si una pieza coordina pasos o varios agentes, propón workflow o handoff explícito.
- Si una pieza guarda historial o variables de proceso, separa session state de memoria persistente.
- Si una pieza mezcla muchas responsabilidades, propón dividirla.
- Usa la tool classify_legacy_component para clasificar piezas heredadas concretas.
- No propongas reescribir todo de golpe.
- Devuelve siempre una propuesta de arquitectura destino en MAF.
"""

    return client.as_agent(
        name="maf_migration_architecture_agent",
        instructions=instructions,
        tools=[
            classify_legacy_component,
        ],
    )