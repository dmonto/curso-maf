import asyncio
from typing import Any

from agent_framework.orchestrations import GroupChatBuilder, GroupChatState
from orq_utils import *


def select_support_speaker(state: GroupChatState) -> str | None:
    """
    Selector determinista de turnos para un debate corto.

    Usa los nombres reales registrados en state.participants.
    """
    participant_names = list(state.participants.keys())

    if state.current_round >= len(participant_names):
        return None

    return participant_names[state.current_round]


def build_group_chat_support_workflow():
    identity_agent = build_identity_agent()
    network_agent = build_network_agent()
    security_agent = build_security_reviewer()
    synthesizer_agent = build_final_synthesizer()

    participants = [
        identity_agent,
        network_agent,
        security_agent,
        synthesizer_agent,
    ]

    print("\n=== PARTICIPANTES GROUPCHAT ===")
    for agent in participants:
        print(getattr(agent, "name", repr(agent)))

    workflow = (
        GroupChatBuilder(
            participants=participants,
            selection_func=select_support_speaker,
        )
        .with_max_rounds(4)
        .build()
    )

    return workflow


async def run_group_chat_example() -> None:
    workflow = build_group_chat_support_workflow()

    prompt = (
        "CASO DEMO-GROUPCHAT-001\n\n"
        "Un usuario indica que la VPN funciona de forma intermitente. "
        "Cuando consigue conectar, algunas aplicaciones internas muestran acceso denegado. "
        "El usuario ha cambiado de móvil recientemente y usa MFA.\n\n"
        "Debatid el caso por turnos. "
        "Cada agente debe aportar solo desde su especialidad. "
        "La síntesis final debe incluir hipótesis, riesgos, datos pendientes "
        "y siguiente acción segura."
    )

    result = await workflow.run(prompt)

    print("\n=== GROUPCHATBUILDER ===")
    print([(r.type, r.executor_id, r.data) for r in result])
    print(last_output_as_text(result))


if __name__ == "__main__":
    asyncio.run(run_group_chat_example())