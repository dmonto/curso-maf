from __future__ import annotations

import asyncio
import json

from src.agents.workflow_response_agent import build_workflow_response_agent
from src.workflows.support_workflow import run_support_workflow


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
    user_message = (
        "No puedo acceder a la VPN desde Windows 11. "
        "Ya he reiniciado el cliente, validado MFA y tengo conexión a Internet. "
        "Afecta solo a un usuario. ¿Puedes preparar un ticket si hace falta?"
    )

    workflow_state = run_support_workflow(
        user_id="u-001",
        session_id="s-001",
        user_message=user_message,
    )

    agent = build_workflow_response_agent()

    prompt = f"""
Petición original del usuario:
{user_message}

Estado del workflow:
{json.dumps(workflow_state.to_dict(), ensure_ascii=False, indent=2)}

Redacta la respuesta final para el usuario.
No cambies decisiones del workflow.
"""

    response = await agent.run(prompt)
    print(render_response(response))


if __name__ == "__main__":
    asyncio.run(main())