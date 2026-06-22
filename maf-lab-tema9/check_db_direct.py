from src.integrations.support_db import SupportDbRepository


def main() -> None:
    repo = SupportDbRepository.from_env()

    print("\n--- TICKET ---")
    ticket = repo.get_ticket("INC-1001")
    print(ticket.model_dump() if ticket else "No encontrado")

    print("\n--- ACTIVOS ---")
    assets = repo.find_assets_by_owner("ana.garcia@empresa.local")
    for asset in assets:
        print(asset.model_dump())

    print("\n--- RESUMEN ---")
    for row in repo.summarize_tickets_by_service():
        print(row)

    print("\n--- NOTA ---")
    note = repo.add_ticket_note(
        ticket_id="INC-1001",
        note="Usuario confirma que la lentitud continúa tras reiniciar VPN.",
        created_by="soporte.n1@empresa.local",
    )
    print(note.model_dump())


if __name__ == "__main__":
    main()