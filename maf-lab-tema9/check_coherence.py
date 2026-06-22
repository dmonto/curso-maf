import json

from src.state.coherence import CoherenceController


def main() -> None:
    controller = CoherenceController()

    user_text = "Crea el ticket de la VPN como urgente."

    memory = {
        "servicio": "vpn",
        "ubicacion": "remoto",
        "sistema_operativo": "Windows 11",
        "usuarios_afectados": None,
        "prioridad": "p3",
    }

    enriched_context = {
        "service": {
            "key": "erp",
            "criticidad": "critica",
            "sla_default": "p1",
        },
        "policy": {
            "puede_crear_ticket_real": False,
            "puede_preparar_borrador": True,
            "requiere_confirmacion_para_envio": True,
        },
        "external_status": {
            "servicio": "erp",
            "estado": "operativo",
            "incidencia_global": False,
            "updated_utc": "2026-06-01T10:00:00+00:00",
        },
    }

    distributed_metadata = {
        "status": "open",
        "turn_count": 3,
    }

    report = controller.validate(
        user_text=user_text,
        memory=memory,
        enriched_context=enriched_context,
        distributed_metadata=distributed_metadata,
    )

    print("\n--- REPORTE DE COHERENCIA ---")
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))

    print("\n--- BLOQUE PARA PROMPT ---")
    print(report.to_prompt_block())


if __name__ == "__main__":
    main()