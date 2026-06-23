from __future__ import annotations

from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools.privacy_support_tools import get_mock_customer_record


def build_privacy_safe_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un agente interno de soporte con protección de datos sensibles.

Reglas:
- No solicites contraseñas, tokens, claves privadas ni API keys.
- Si el usuario pega un secreto, indica que debe rotarlo y no lo repitas.
- No muestres datos personales completos si no son necesarios.
- Si una tool devuelve campos redactados, no intentes reconstruirlos.
- No guardes datos sensibles en memoria.
- No inventes valores personales.
- Resume incidencias sin exponer teléfonos, IBAN, tokens o identificadores innecesarios.
"""

    return client.as_agent(
        name="privacy_safe_support_agent",
        instructions=instructions,
        tools=[
            get_mock_customer_record,
        ],
    )