from agent_framework.orchestrations import MagenticBuilder
from orq_utils import *
from orq_rendering import print_magentic_result

def build_magentic_support_workflow():
    manager_agent = build_final_synthesizer()

    triage_agent = build_triage_agent()
    identity_agent = build_identity_agent()
    network_agent = build_network_agent()
    security_agent = build_security_reviewer()

    workflow = (
        MagenticBuilder(participants=[
            triage_agent,
            identity_agent,
            network_agent,
            security_agent,
        ], manager_agent=manager_agent, max_round_count=10)
        .build()
    )

    return workflow


async def run_magentic_example() -> None:
    workflow = build_magentic_support_workflow()

    prompt = (
        "CASO DEMO-MAGENTIC-001\n\n"
        "Diseña un plan de diagnóstico seguro para este caso:\n"
        "- varios usuarios no pueden acceder al ERP desde fuera de la oficina\n"
        "- algunos reportan fallos de VPN\n"
        "- otros reciben errores de MFA\n"
        "- el área de negocio indica impacto alto\n"
        "- no se permite ejecutar cambios reales ni modificar permisos\n\n"
        "Coordina a los especialistas necesarios, identifica riesgos, "
        "propón un plan y entrega una recomendación final operativa."
    )

    result = await workflow.run(prompt)

    print("\n=== MAGENTICBUILDER ===")
    print_magentic_result(result)
    print(last_output_as_text(result))

if __name__ == "__main__":
    asyncio.run(run_magentic_example())    