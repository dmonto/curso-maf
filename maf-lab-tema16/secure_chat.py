from __future__ import annotations

import asyncio

from src.agents.secure_support_agent import build_secure_support_agent
from src.security.access_policy import UserAccessContext


DEMO_USERS = {
    "ana": UserAccessContext(
        user_id="ana@contoso.com",
        tenant_id="contoso",
        groups=("support_l1",),
        department="it",
        allowed_areas=("vpn", "correo"),
        data_clearance="internal",
    ),
    "bruno": UserAccessContext(
        user_id="bruno@contoso.com",
        tenant_id="contoso",
        groups=("support_admin",),
        department="it",
        allowed_areas=("vpn", "correo", "seguridad"),
        data_clearance="restricted",
    ),
    "carla": UserAccessContext(
        user_id="carla@contoso.com",
        tenant_id="contoso",
        groups=("finance",),
        department="finance",
        allowed_areas=("facturacion",),
        data_clearance="confidential",
    ),
}


async def main() -> None:
    print("Usuarios disponibles:", ", ".join(DEMO_USERS))
    selected = input("Usuario> ").strip().lower()

    if selected not in DEMO_USERS:
        raise ValueError(f"Usuario no reconocido: {selected}")

    user_context = DEMO_USERS[selected]
    agent = build_secure_support_agent(user_context)
    session = agent.create_session()

    print("\nEscribe 's' para salir.\n")

    while True:
        prompt = input("Tú> ").strip()

        if prompt.lower() == "s":
            break

        result = await agent.run(prompt, session=session)
        print(f"\nAgente> {result}\n")


if __name__ == "__main__":
    asyncio.run(main())