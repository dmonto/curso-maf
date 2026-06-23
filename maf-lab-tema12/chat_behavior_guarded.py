import asyncio

from src.agents.support_agent import build_support_agent
from src.safety import postcheck_agent_response, precheck_user_behavior


async def main() -> None:
    agent = build_support_agent()

    print("Chat con política de comportamiento. Escribe 's' para salir.")

    while True:
        raw = input("\nUsuario> ")

        if raw.strip().lower() == "s":
            break

        precheck = precheck_user_behavior(raw)

        if precheck.action in {"safe_refusal", "safe_redirect", "ask_clarification"}:
            print("\nAgente>")
            print(precheck.safe_message)
            continue

        if precheck.reasons:
            print("\n[Política detectada]")
            for reason in precheck.reasons:
                print(f"- {reason}")

        result = await agent.run(precheck.sanitized_user_text)

        postcheck = postcheck_agent_response(str(result))

        print("\nAgente>")
        if postcheck.action == "allow":
            print(result)
        else:
            print(postcheck.safe_message)


if __name__ == "__main__":
    asyncio.run(main())