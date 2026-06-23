from src.integrations.external_ticket_client import (
    ExternalDataValidationError,
    ExternalTicketClient,
    ExternalTicketError,
)

from dotenv import load_dotenv

load_dotenv()

def test_ticket(ticket_id: str) -> None:
    client = ExternalTicketClient.from_env()

    print(f"\n--- {ticket_id} ---")

    try:
        ticket = client.get_validated_ticket(ticket_id)
        print("VALIDO")
        print(ticket.model_dump(mode="json"))

    except ExternalDataValidationError as exc:
        print("ERROR DE VALIDACION")
        print(str(exc))

    except ExternalTicketError as exc:
        print("ERROR EXTERNO")
        print(str(exc))


def main() -> None:
    test_ticket("INC-1001")
    test_ticket("INC-1002")
    test_ticket("INC-1003")
    test_ticket("INC-9999")


if __name__ == "__main__":
    main()