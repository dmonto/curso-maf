from __future__ import annotations

from src.tools.adapted_ticket_tools import (
    prepare_ticket_draft,
    search_support_tickets,
)


def main() -> None:
    print("\n--- CONSULTA DE TICKETS ---")
    print(
        search_support_tickets(
            service="vpn",
            max_results=2,
        )
    )

    print("\n--- BORRADOR DE TICKET ---")
    print(
        prepare_ticket_draft(
            service="vpn",
            title="Usuario sin acceso a VPN desde Windows 11",
            description=(
                "El usuario no puede acceder a la VPN desde casa. "
                "Ya ha comprobado conexión a Internet y ha reiniciado el cliente."
            ),
            priority="medium",
        )
    )


if __name__ == "__main__":
    main()