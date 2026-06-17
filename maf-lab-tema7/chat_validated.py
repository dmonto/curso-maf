import asyncio

from src.agents.support_agent import build_support_agent
from src.validation import validate_user_input


async def main() -> None:
    agent = build_support_agent()

    print("Chat validado. Escribe 's' para salir.")

    while True:
        raw = input("\nUsuario> ")

        if raw.lower().strip() == "s":
            break

        validation = validate_user_input(raw)

        if validation.status == "blocked":
            print("\nAgente>")
            print(
                "No puedo procesar esa entrada. "
                f"Motivo: {'; '.join(validation.reasons)}"
            )
            continue

        if validation.status == "needs_clarification":
            print("\nAgente>")
            print(
                "Necesito algo más de información. "
                "Indica el servicio afectado y el síntoma principal."
            )
            continue

        if validation.reasons:
            print("\n[Validación]")
            for reason in validation.reasons:
                print(f"- {reason}")

        result = await agent.run(validation.user_message_for_agent)

        print("\nAgente>")
        print(result)


if __name__ == "__main__":
    asyncio.run(main())