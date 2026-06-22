import json

from src.state.truncation import (
    ContextBlock,
    ContextTruncator,
    TruncationStrategy,
)


def fake_logs() -> str:
    lines = []

    for i in range(1, 81):
        lines.append(
            f"2026-06-15T10:{i:02d}:00Z vpn-gateway "
            f"user=demo status=retry latency_ms={120 + i} "
            f"message='connection attempt {i}'"
        )

    lines.append(
        "2026-06-15T11:22:00Z vpn-gateway ERROR "
        "code=AUTH_TIMEOUT message='MFA validation timeout after retries'"
    )

    return "\n".join(lines)


def main() -> None:
    memory = {
        "servicio": "vpn",
        "ubicacion": "remoto",
        "sistema_operativo": "Windows 11",
        "usuarios_afectados": 1,
        "pasos_probados": ["validar_mfa", "probar_otra_red"],
        "pendiente_confirmacion": "preparar_borrador_ticket",
        "notas_largas": "x" * 2500,
    }

    blocks = [
        ContextBlock(
            name="politicas_seguridad",
            content=(
                "No crear tickets reales sin confirmación. "
                "No solicitar contraseñas. "
                "No exponer secretos ni tokens."
            ),
            priority=100,
            strategy=TruncationStrategy.NONE,
            required=True,
            max_chars=2000,
        ),
        ContextBlock(
            name="mensaje_actual",
            content="El usuario pregunta qué sabemos hasta ahora y si podemos preparar un borrador.",
            priority=95,
            strategy=TruncationStrategy.NONE,
            required=True,
            max_chars=2000,
        ),
        ContextBlock(
            name="memoria_estructurada",
            content=json.dumps(memory, ensure_ascii=False, indent=2),
            priority=85,
            strategy=TruncationStrategy.JSON_FIELDS,
            min_chars=800,
            max_chars=2500,
        ),
        ContextBlock(
            name="resumen_acumulado",
            content=(
                "El usuario reporta problema de VPN desde casa. "
                "Usa Windows 11. Ha validado MFA y probado otra red. "
                "El problema afecta solo a un usuario. "
            )
            * 20,
            priority=60,
            strategy=TruncationStrategy.MIDDLE,
            min_chars=800,
            max_chars=2500,
        ),
        ContextBlock(
            name="logs_vpn",
            content=fake_logs(),
            priority=25,
            strategy=TruncationStrategy.MIDDLE,
            min_chars=600,
            max_chars=1800,
        ),
    ]

    truncator = ContextTruncator(
        max_context_tokens=2200,
        response_margin_tokens=500,
    )

    result = truncator.truncate(blocks)

    print("\n--- REPORTE ---")
    print(json.dumps(result.report(), ensure_ascii=False, indent=2))

    print("\n--- CONTEXTO FINAL ---")
    print(result.content)


if __name__ == "__main__":
    main()