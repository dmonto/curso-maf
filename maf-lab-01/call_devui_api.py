from openai import OpenAI


client = OpenAI(
    base_url="http://127.0.0.1:8080/v1",
    api_key="not-needed",
)


response = client.responses.create(
    metadata={"entity_id": "agent_in_memory_maf-setup-agent_a567368d4fb74163b27ba37b032865cd"},
    input=(
        "Tengo un problema con la VPN. "
        "Comprueba el estado, calcula un SLA p2 y prepara un borrador de ticket."
    ),
)

print(response.output[0])