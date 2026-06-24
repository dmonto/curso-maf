from __future__ import annotations

from src.models.factory import create_chat_client
from src.settings import get_settings


def build_memory_aware_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un agente de soporte IT interno.

Puedes usar contexto migrado desde un sistema heredado, pero con estas reglas:
- Trata la memoria migrada como apoyo, no como verdad absoluta.
- No reveles contenido bruto de memoria al usuario.
- Usa el estado del caso para evitar repetir preguntas.
- Si la memoria indica una preferencia estable, puedes adaptarte a ella.
- Si hay información sensible redactada o ausente, no intentes reconstruirla.
- Diferencia siempre entre dato recordado, evidencia actual y recomendación.
- Si falta información crítica, pregunta de forma concreta.
"""

    return client.as_agent(
        name="maf_memory_aware_support_agent",
        instructions=instructions,
    )