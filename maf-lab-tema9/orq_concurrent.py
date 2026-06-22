from agent_framework.orchestrations import ConcurrentBuilder
from orq_utils import *
from orq_rendering import print_workflow_result

async def aggregate_identity_network_results(results: list[Any]) -> str:
    identity_and_network_outputs = "\n\n".join(
        f"Resultado {index + 1}:\n{agent_result_to_text(result)}"
        for index, result in enumerate(results)
    )

    resolver = build_conflict_resolver()

    resolver_prompt = (
        "Se han recibido análisis paralelos de especialistas.\n\n"
        f"{identity_and_network_outputs}\n\n"
        "Resuelve si hay conflicto real o aparente entre las hipótesis. "
        "Devuelve una recomendación operativa segura, indicando datos pendientes."
    )

    resolver_result = await resolver.run(resolver_prompt)
    return str(resolver_result)


def build_concurrent_diagnosis_workflow():
    identity_agent = build_identity_agent()
    network_agent = build_network_agent()

    workflow = (
        ConcurrentBuilder(participants=[
                identity_agent,
                network_agent,
            ])
        .with_aggregator(aggregate_identity_network_results)
        .build()
    )

    return workflow


async def run_concurrent_example() -> None:
    workflow = build_concurrent_diagnosis_workflow()

    prompt = (
        "CASO DEMO-CONCURRENT-001\n\n"
        "Un usuario indica que no puede acceder al ERP desde fuera de la oficina. "
        "A veces entra por VPN, pero al pasar MFA recibe acceso denegado.\n\n"
        "Analiza el caso desde tu especialidad. No ejecutes acciones reales."
    )

    result = await workflow.run(prompt)

    print("\n=== CONCURRENTBUILDER ===")
    print_workflow_result(result)
    print(last_output_as_text(result))

if __name__ == "__main__":
    asyncio.run(run_concurrent_example())