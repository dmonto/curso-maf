from src.security.access_policy import UserAccessContext, authorize


def main() -> None:
    users = [
        UserAccessContext(
            user_id="ana@contoso.com",
            tenant_id="contoso",
            groups=("support_l1",),
            department="it",
            allowed_areas=("vpn", "correo"),
            data_clearance="internal",
        ),
        UserAccessContext(
            user_id="bruno@contoso.com",
            tenant_id="contoso",
            groups=("support_admin",),
            department="it",
            allowed_areas=("vpn", "correo", "seguridad"),
            data_clearance="restricted",
        ),
        UserAccessContext(
            user_id="carla@contoso.com",
            tenant_id="contoso",
            groups=("finance",),
            department="finance",
            allowed_areas=("facturacion",),
            data_clearance="confidential",
        ),
    ]

    checks = [
        ("knowledge.search", "vpn", "internal"),
        ("knowledge.search", "seguridad", "restricted"),
        ("incident.draft", "vpn", "internal"),
        ("identity.read_restricted", "seguridad", "restricted"),
    ]

    for user in users:
        print(f"\n=== {user.user_id} ===")

        for action, area, classification in checks:
            decision = authorize(
                user,
                action=action,
                area=area,
                classification=classification,
                tenant_id="contoso",
            )

            status = "ALLOW" if decision.allowed else "DENY"
            print(f"{status:5} {action:26} area={area:12} -> {decision.reason}")


if __name__ == "__main__":
    main()