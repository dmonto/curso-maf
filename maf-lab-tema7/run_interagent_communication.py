import asyncio
import logging

from src.agents.multiagent.communication_coordinator import (
    run_support_case_with_messages,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main() -> None:
    user_request = (
        "Un usuario de Finanzas no puede acceder al ERP desde casa. "
        "La VPN conecta correctamente, pero el ERP muestra 'acceso denegado'. "
        "Necesita entrar antes de una reunión de auditoría."
    )

    result = await run_support_case_with_messages(user_request)

    print("\n--- RESULTADO IDENTIDAD ---\n")
    print(result["identity_result"])

    print("\n--- RESULTADO SEGURIDAD ---\n")
    print(result["security_result"])

    print("\n--- RESULTADO ITSM ---\n")
    print(result["itsm_result"])

    print("\n--- TRAZA DE COMUNICACIÓN ---\n")
    print(result["trace"])


if __name__ == "__main__":
    asyncio.run(main())