import asyncio

from src.models.factory import create_chat_client


async def main():
    client = create_chat_client("chat_fast")

    agent = client.as_agent(
        name="check_foundry_chat_agent",
        instructions="Responde de forma breve.",
    )

    result = await agent.run("Di OK si puedes responder desde Foundry.")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())