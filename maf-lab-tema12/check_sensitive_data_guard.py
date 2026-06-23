from src.security.sensitive_data import sanitize_text, summarize_matches


TEST_MESSAGES = [
    "Mi correo es ana.garcia@contoso.com y mi teléfono es +34 600 123 456.",
    "El IBAN del proveedor es ES91 2100 0418 4502 0005 1332.",
    "Mi token es sk-proj-1234567890abcdefghijklmnop.",
    "No puedo acceder a la VPN desde Windows 11.",
]


def main() -> None:
    for message in TEST_MESSAGES:
        print("\n--- ORIGINAL ---")
        print(message)

        report = sanitize_text(message)

        print("\n--- SANITIZED ---")
        print(report.sanitized_text)

        print("\n--- REPORT ---")
        print(
            {
                "has_sensitive_data": report.has_sensitive_data,
                "highest_level": report.highest_level.value,
                "blocked": report.blocked,
                "reason": report.reason,
                "matches": summarize_matches(report.matches),
            }
        )


if __name__ == "__main__":
    main()