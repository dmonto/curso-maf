from __future__ import annotations

import asyncio
from typing import Any

from src.agents.document_automation_agent import build_document_automation_agent


def render_result(result: Any) -> str:
    if isinstance(result, str):
        return result

    for attr in ("text", "content", "message"):
        value = getattr(result, attr, None)
        if value:
            return str(value)

    return str(result)


async def main() -> None:
    agent = build_document_automation_agent()

    prompts = [
        """
Necesito preparar un informe de incidencia.

Servicio afectado: ERP.
Impacto: varios usuarios del área de facturación no pueden cerrar operaciones.
Estado actual: mitigado parcialmente.
Síntomas: error 500 al confirmar facturas desde las 10:15.
Acciones realizadas: se revisaron logs, se reinició el servicio de integración y se avisó a aplicaciones.
Cronología: 10:15 primer aviso, 10:25 validación con usuarios, 10:40 reinicio parcial.
Causa probable: pendiente de análisis, posible degradación en integración.
Pendientes: revisar logs completos y confirmar estabilidad durante la tarde.
Recomendación: escalar a aplicaciones corporativas y mantener seguimiento.
Bloquea negocio: sí.
""",
        """
Genera un informe sobre un problema de VPN.
Solo sé que no funciona.
""",
    ]

    for index, prompt in enumerate(prompts, start=1):
        print(f"\n\n--- CASO {index} ---")
        print(prompt.strip())

        result = await agent.run(prompt)

        print("\n--- RESPUESTA DEL AGENTE DOCUMENTAL ---")
        print(render_result(result))


if __name__ == "__main__":
    asyncio.run(main())