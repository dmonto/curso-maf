from src.integrations.unstable_ticket_client import UnstableTicketClient
from dotenv import load_dotenv

load_dotenv()

def main() -> None:
    client = UnstableTicketClient.from_env()

    for ticket_id in [
        "INC-1001",
        "INC-404",
        "INC-403",
        "INC-429",
        "INC-500",
        "INC-SLOW",
        "INC-BADJSON",
    ]:
        print(f"\n--- {ticket_id} ---")
        result = client.get_ticket(ticket_id)
        print(result.model_dump(mode="json"))


if __name__ == "__main__":
    main()