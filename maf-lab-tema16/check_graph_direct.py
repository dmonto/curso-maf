from src.integrations.graph_client import GraphClient, GraphIntegrationError


def main() -> None:
    client = GraphClient.from_env()

    try:
        print("\n--- MI PERFIL ---")
        me = client.get_me()
        print(me.model_dump())

        print("\n--- MIS EVENTOS ---")
        events = client.get_my_upcoming_events(days=7, limit=5)
        for event in events:
            print(event.model_dump())

    except GraphIntegrationError as exc:
        print(f"Error Graph: {exc}")


if __name__ == "__main__":
    main()