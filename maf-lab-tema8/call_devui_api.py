from openai import OpenAI


client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="not-needed",
)


response = client.responses.create(
    metadata={"entity_id": "agent_in_memory_maf-tools-agent_a294bbc9cfe24bafae5930b6e5e49610"},
    input=(
        "Tengo un problema con la VPN. "
        "Comprueba el estado, calcula un SLA p2 y prepara un borrador de ticket."
    ),
)

print(response.output[0])