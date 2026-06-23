from agent_framework.orchestrations import HandoffBuilder
from orq_utils import *
from orq_rendering import print_workflow_result

def build_handoff_support_workflow():
    coordinator = build_triage_agent()
    identity_agent = build_identity_agent()
    network_agent = build_network_agent()
    security_agent = build_security_reviewer()

    workflow = (
        HandoffBuilder(
            name="support_handoff_workflow",
            participants=[
                coordinator,
                identity_agent,
                network_agent,
                security_agent,
            ],
            description="Workflow de soporte con traspaso dinámico entre especialistas.",
        )
        .add_handoff(
            coordinator,
            [
                identity_agent,
                network_agent,
                security_agent,
            ],
        )
        .with_start_agent(coordinator)
        .build()
    )

    return workflow


async def run_handoff_example() -> None:
    workflow = build_handoff_support_workflow()

    prompt = (
        "CASO DEMO-HANDOFF-001\n\n"
        "Un usuario externo solicita acceso temporal como administrador "
        "a un entorno de producción para revisar datos sensibles.\n\n"
        "El coordinador debe decidir si responde directamente o transfiere "
        "el caso al especialista adecuado. No ejecutes acciones reales."
    )

    result = await workflow.run(prompt)

    print("\n=== HANDOFFBUILDER ===")
    print_workflow_result(result)
    print(last_output_as_text(result))

if __name__ == "__main__":
    asyncio.run(run_handoff_example())