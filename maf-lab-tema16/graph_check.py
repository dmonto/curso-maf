import json

from src.integrations.graph_client import GraphClient, GraphIntegrationError


def main() -> None:
    client = GraphClient.from_env()

    print("\n--- USUARIO ACTUAL ---")
    try:
        me = client.get_me()
        print(me.model_dump_json(indent=2))
    except GraphIntegrationError as exc:
        print(f"ERROR /me: {exc}")

    print("\n--- USUARIOS ---")
    try:
        users = client.list_users(limit=5)
        for user in users:
            print(
                json.dumps(
                    user.model_dump(),
                    ensure_ascii=False,
                    indent=2,
                )
            )
    except GraphIntegrationError as exc:
        print(f"ERROR /users: {exc}")

    print("\n--- GRUPOS ---")
    try:
        groups = client.list_groups(limit=5)
        for group in groups:
            print(
                json.dumps(
                    group.model_dump(),
                    ensure_ascii=False,
                    indent=2,
                )
            )
    except GraphIntegrationError as exc:
        print(f"ERROR /groups: {exc}")




if __name__ == "__main__":
    main()