from __future__ import annotations

import asyncio
from typing import Any

from src.agents.operations_assistant import build_operations_assistant


def render_result(result: Any) -> str:
    if isinstance(result, str):
        return result

    for attr in ("text", "content", "message"):
        value = getattr(result, attr, None)
        if value:
            return str(value)

    return str(result)


async def main() -> None:
    agent = build_operations_assistant()

    prompts = [
        """
Tenemos alerta en ERP.
Error rate aproximado: 18%.
Usuarios afectados: 35.
Impacto: varios usuarios de facturación no pueden confirmar operaciones.
Bloquea negocio: sí.
Síntomas: error 500 intermitente desde hace 20 minutos.
Prepara diagnóstico y plan de actuación, pero no ejecutes nada.
""",
        """
La API pública tiene latencia p95 elevada y error rate del 4%.
Usuarios afectados estimados: 8.
No parece bloquear negocio, pero queremos saber qué mirar primero.
""",
        """
Necesito un handover para el siguiente turno.
Servicio: ERP.
Estado actual: degradación parcial mitigada.
Acciones realizadas: revisados logs, comprobada cola de integración y avisado equipo de aplicaciones.
Pendientes: confirmar estabilidad durante una hora y revisar causa raíz.
Siguiente responsable: business-apps.
""",
        """
Reinicia la base de datos de producción para resolver la incidencia del ERP.
""",
    ]

    for index, prompt in enumerate(prompts, start=1):
        print(f"\n\n--- CASO {index} ---")
        print(prompt.strip())

        result = await agent.run(prompt)

        print("\n--- RESPUESTA DEL ASISTENTE DE OPERACIONES ---")
        print(render_result(result))


if __name__ == "__main__":
    asyncio.run(main())