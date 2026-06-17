import json

from src.security import MemorySecurityGuard


def main() -> None:
    guard = MemorySecurityGuard()

    unsafe_memory = {
        "servicio": "vpn",
        "ubicacion": "remoto",
        "sistema_operativo": "Windows 11",
        "usuarios_afectados": 1,
        "pasos_probados": [
            "validar_mfa",
            "El usuario ana.garcia@empresa.com ha probado otra red",
        ],
        "ultima_accion_recomendada": (
            "Llamar al usuario al 600123456. "
            "El código MFA es 123456."
        ),
        "password": "Temporal123!",
        "access_token": "Bearer abc.def.ghi",
        "notas_libres": "Este campo no debería persistirse.",
        "connection_string": (
            "DefaultEndpointsProtocol=https;"
            "AccountName=demo;AccountKey=abc123;"
        ),
    }

    sanitized, report = guard.sanitize_memory(unsafe_memory)

    print("\n--- MEMORIA ORIGINAL ---")
    print(json.dumps(unsafe_memory, ensure_ascii=False, indent=2))

    print("\n--- MEMORIA SANITIZADA ---")
    print(json.dumps(sanitized, ensure_ascii=False, indent=2))

    print("\n--- REPORTE DE SEGURIDAD ---")
    print(report.to_json())


if __name__ == "__main__":
    main()