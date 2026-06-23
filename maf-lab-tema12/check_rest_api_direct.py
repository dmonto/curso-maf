from src.integrations.itsm_client import ItsmClient
from dotenv import load_dotenv

load_dotenv()

def main() -> None:
    client = ItsmClient.from_env()

    print("\n--- CONSULTA TICKET EXISTENTE ---")
    ticket = client.get_ticket("INC-1001")
    print(ticket.model_dump())

    print("\n--- CREA TICKET NUEVO ---")
    created = client.create_ticket(
        service="vpn",
        summary="Usuario no puede conectar a VPN desde Windows 11",
        priority="p2",
    )
    print(created.model_dump())


if __name__ == "__main__":
    main()