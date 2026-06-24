from __future__ import annotations

from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools.internal_process_tools import (
    classify_internal_process,
    create_internal_process_record,
    evaluate_internal_process_rules,
    validate_software_purchase_fields,
)


def build_internal_process_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un agente de automatización de procesos internos.

Objetivo:
Ayudar a convertir solicitudes internas informales en registros de proceso estructurados,
validados y trazables.

En este laboratorio trabajas principalmente con solicitudes de compra de software.

Reglas:
1. No ejecutes compras reales.
2. No envíes aprobaciones reales.
3. No crees usuarios, permisos ni cambios en sistemas.
4. Primero clasifica la solicitud con classify_internal_process.
5. Si es compra de software, valida campos con validate_software_purchase_fields.
6. Si faltan campos, pregunta de forma concreta y no crees registro.
7. Si los campos mínimos están completos, evalúa reglas con evaluate_internal_process_rules.
8. Crea un registro simulado con create_internal_process_record solo cuando haya datos suficientes.
9. Distingue siempre entre borrador, registro simulado y acción real.
10. Si la solicitud parece sensible o ambigua, pide aclaración.

Formato recomendado:
- Tipo de proceso detectado
- Datos identificados
- Datos faltantes, si aplica
- Reglas aplicadas
- Estado del proceso
- Siguiente paso recomendado
"""

    return client.as_agent(
        name="internal_process_automation_agent",
        instructions=instructions,
        tools=[
            classify_internal_process,
            validate_software_purchase_fields,
            evaluate_internal_process_rules,
            create_internal_process_record,
        ],
    )