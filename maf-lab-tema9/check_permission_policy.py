from src.security.permission_policy import (
    DocumentPermission,
    UserAccessContext,
    evaluate_document_permission,
)


def check_case(
    name: str,
    user: UserAccessContext,
    permission: DocumentPermission,
    expected: str,
) -> None:
    decision = evaluate_document_permission(user, permission)

    print(f"\n--- {name} ---")
    print(f"Decision: {decision.decision}")
    print(f"Reason: {decision.reason}")

    assert decision.decision == expected, (
        f"Esperaba {expected}, pero recibí {decision.decision}"
    )


def main() -> None:
    support_user = UserAccessContext(
        user_id="ana@curso.local",
        tenant_id="curso-maf",
        groups=["support-l1"],
    )

    hr_user = UserAccessContext(
        user_id="beatriz@curso.local",
        tenant_id="curso-maf",
        groups=["hr-managers"],
    )

    external_user = UserAccessContext(
        user_id="externo@curso.local",
        tenant_id="curso-maf",
        groups=["external-support"],
    )

    other_tenant_user = UserAccessContext(
        user_id="ana@otro.local",
        tenant_id="otro-tenant",
        groups=["support-l1"],
    )

    vpn_doc = DocumentPermission(
        tenant_id="curso-maf",
        visibility="internal",
        allowed_users=[],
        allowed_groups=["support-l1", "support-l2"],
        denied_users=[],
        denied_groups=[],
        classification="internal",
        owner="it-support",
    )

    hr_doc = DocumentPermission(
        tenant_id="curso-maf",
        visibility="restricted",
        allowed_users=[],
        allowed_groups=["hr-managers"],
        denied_users=[],
        denied_groups=["external-support"],
        classification="confidential",
        owner="hr",
    )

    public_doc = DocumentPermission(
        tenant_id="curso-maf",
        visibility="public",
        allowed_users=[],
        allowed_groups=[],
        denied_users=[],
        denied_groups=[],
        classification="internal",
        owner="it-support",
    )

    check_case("support_user puede ver VPN", support_user, vpn_doc, "allow")
    check_case("support_user no puede ver RRHH", support_user, hr_doc, "deny")
    check_case("hr_user puede ver RRHH", hr_user, hr_doc, "allow")
    check_case("external_user bloqueado en RRHH", external_user, hr_doc, "deny")
    check_case("support_user puede ver público", support_user, public_doc, "allow")
    check_case("otro tenant no puede ver VPN", other_tenant_user, vpn_doc, "deny")

    print("\nTodas las pruebas de permisos han pasado.")


if __name__ == "__main__":
    main()