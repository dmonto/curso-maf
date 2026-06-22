from src.integrations.access_lab_repository import AccessLabRepository
from src.security.access_control import authorize


def test_user(user_upn: str, ticket_id: str) -> None:
    repo = AccessLabRepository.from_env()

    user = repo.get_user(user_upn)
    ticket = repo.get_ticket(ticket_id)

    print(f"\nUsuario: {user_upn}")
    print(f"Ticket: {ticket_id}")

    for action in [
        "ticket.read",
        "ticket.note.add",
        "ticket.priority.update",
    ]:
        decision = authorize(
            user=user,
            action=action,  # type: ignore[arg-type]
            ticket=ticket,
        )
        print(f"{action}: allowed={decision.allowed} reason={decision.reason}")


def main() -> None:
    test_user("ana.garcia@empresa.local", "INC-1001")
    test_user("soporte.n1@empresa.local", "INC-1001")
    test_user("soporte.n1@empresa.local", "INC-2001")
    test_user("soporte.n2@empresa.local", "INC-1001")
    test_user("manager.it@empresa.local", "INC-1001")


if __name__ == "__main__":
    main()