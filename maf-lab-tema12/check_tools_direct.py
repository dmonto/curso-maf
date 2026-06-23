from src.tools.support_tools import (
    _calculate_sla_deadline_impl,
    _draft_support_ticket_impl,
    _get_service_status_impl,
)


def main() -> None:
    print("\n--- ESTADO DE SERVICIO ---")
    print(_get_service_status_impl("vpn"))

    print("\n--- SLA ---")
    print(_calculate_sla_deadline_impl("p2"))

    print("\n--- BORRADOR DE TICKET ---")
    print(
        _draft_support_ticket_impl(
            title="VPN lenta",
            description="El usuario indica que la VPN conecta pero la navegación es muy lenta.",
            priority="p2",
            affected_service="vpn",
        )
    )


if __name__ == "__main__":
    main()