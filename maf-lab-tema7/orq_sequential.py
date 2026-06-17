from agent_framework.orchestrations import SequentialBuilder
from src.agents.multiagent.collaborative_agents import *
from orq_utils import *

def build_proposal_review_workflow():
    return (
        SequentialBuilder(participants=[
                build_triage_agent(),
                build_security_reviewer(),
                build_final_synthesizer(),
            ])
        .build()
    )


async def run_proposal_review_native() -> str:
    workflow = build_proposal_review_workflow()

    prompt = (
        f"CASO Un usuario indica que no puede acceder al ERP desde fuera de la oficina.A veces entra por VPN, pero al pasar MFA recibe acceso denegado.\n\n"
        "Genera una propuesta operativa segura, revísala desde seguridad "
        "y produce una respuesta final. No ejecutes acciones reales."
    )

    result = await workflow.run(prompt)
    
    print([(r.type, r.executor_id, r.data) for r in result])
    outputs = list(result.get_outputs())

    if not outputs:
        raise RuntimeError("El workflow secuencial no produjo salida.")

    return str(outputs[-1])

if __name__ == "__main__":
    asyncio.run(run_proposal_review_native())    