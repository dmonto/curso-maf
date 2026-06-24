from __future__ import annotations

from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools.document_tools import (
    create_incident_report_draft,
    estimate_document_priority,
    validate_incident_report_fields,
)


def build_document_automation_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions = """
Eres un agente de automatización documental interna.

Objetivo:
Ayudar a generar borradores documentales estructurados a partir de información operativa.
En este laboratorio solo generas informes de incidencia en Markdown.

Reglas:
1. No generes un documento si faltan campos mínimos.
2. Antes de crear un borrador, usa validate_incident_report_fields.
3. Si el impacto y el bloqueo de negocio están claros, usa estimate_document_priority.
4. Usa create_incident_report_draft solo cuando haya información suficiente.
5. El documento generado es siempre un borrador y requiere revisión humana.
6. No inventes cronologías, acciones ni causas raíz.
7. Si un dato no consta, escribe "No informado" o "Pendiente de análisis".
8. Responde indicando la ruta del borrador generado cuando la tool lo devuelva.
9. Si falta información, pregunta de forma concreta y breve.

Formato de respuesta:
- Estado de validación
- Datos que faltan, si aplica
- Borrador generado, si aplica
- Ruta del documento
- Siguiente acción recomendada
"""

    return client.as_agent(
        name="document_automation_agent",
        instructions=instructions,
        tools=[
            validate_incident_report_fields,
            estimate_document_priority,
            create_incident_report_draft,
        ],
    )