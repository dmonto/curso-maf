import asyncio

from src.models.factory import create_chat_client
from src.settings import get_settings


async def main() -> None:
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    agent = client.as_agent(
        name="model_smoke_test_agent",
        instructions=(
            "Responde siempre en una frase. "
            "Tu tarea es confirmar que el modelo registrado funciona."
        ),
    )

    result = await agent.run(
        "Confirma que el registro del modelo funciona correctamente."
    )

    print("\n--- RESPUESTA ---")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())