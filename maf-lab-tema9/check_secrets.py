from src.security.secrets import SecretResolver


def main() -> None:
    resolver = SecretResolver.from_env()

    status = resolver.get_status("ITSM_API_TOKEN")

    print("\n--- ESTADO DE SECRETOS ---")
    print(status)

    token = resolver.get_secret("ITSM_API_TOKEN")
    print("\n--- TOKEN REDACTADO ---")
    print("ITSM_API_TOKEN =", "<set:redacted>" if token else "<missing>")


if __name__ == "__main__":
    main()