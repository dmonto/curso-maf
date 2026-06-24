from __future__ import annotations

import asyncio

from src.agents.prompt_migration_agent import build_prompt_migration_agent


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
    agent = build_prompt_migration_agent()

    legacy_prompt = """
    Eres un agente de soporte IT de nivel 1.
    Clasifica la incidencia del usuario.
    Si es VPN, pregunta por sistema operativo.
    Si afecta a más de 10 usuarios, asigna prioridad alta.
    Usa la tool de tickets para preparar un borrador.
    No crees tickets reales sin confirmación.
    Devuelve JSON con categoria, prioridad y siguiente_accion.
    No reveles datos sensibles ni credenciales.
    Si falta información, pregunta antes de responder.
    Recuerda los pasos ya intentados en la sesión.
    Si hay riesgo de seguridad, deriva al agente de seguridad.
    Usa el procedimiento interno de VPN como referencia.
    """

    prompt = f"""
Analiza este prompt heredado y propón una migración a Microsoft Agent Framework.

Nombre: support_triage_prompt

Prompt:
{legacy_prompt}

Devuelve:
1. Qué partes conservarías como instructions.
2. Qué partes moverías a tools.
3. Qué partes moverías a workflow.
4. Qué partes moverías a estado o memoria.
5. Qué partes validarías fuera del modelo.
6. Riesgos principales.
"""

    response = await agent.run(prompt)
    print(render_response(response))


if __name__ == "__main__":
    asyncio.run(main())