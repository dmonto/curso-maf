from src.identity.demo_users import get_demo_identity


def main() -> None:
    for alias in ("ana", "bruno", "carla"):
        identity = get_demo_identity(alias)

        print(f"\n=== {alias.upper()} ===")
        print(identity.to_agent_summary())
        print("\nAuditoría:")
        print(identity.to_audit_record())


if __name__ == "__main__":
    main()