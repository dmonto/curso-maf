from src.security.permission_policy import UserAccessContext
from src.security.search_filter_builder import build_permission_filter


def main() -> None:
    users = [
        UserAccessContext(
            user_id="ana@curso.local",
            tenant_id="curso-maf",
            groups=["support-l1"],
        ),
        UserAccessContext(
            user_id="beatriz@curso.local",
            tenant_id="curso-maf",
            groups=["hr-managers"],
        ),
        UserAccessContext(
            user_id="carlos@curso.local",
            tenant_id="curso-maf",
            groups=[],
        ),
    ]

    for user in users:
        print("\n" + "=" * 80)
        print(user)

        filter_expression = build_permission_filter(
            user=user,
            domain=None,
        )

        print(filter_expression)


if __name__ == "__main__":
    main()