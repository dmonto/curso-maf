from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


class LegacyTicketPlugin:
    """
    Simula un plugin heredado procedente de Semantic Kernel.

    Problemas típicos:
    - Una única función ejecuta varias acciones.
    - Usa payload genérico.
    - Devuelve texto JSON sin contrato formal.
    - No diferencia claramente consulta, borrador y acción real.
    """

    def execute(self, action: str, payload: dict[str, Any]) -> str:
        if action == "search":
            service = str(payload.get("service", "")).lower()
            return json.dumps(
                {
                    "ok": True,
                    "items": [
                        {
                            "ticket_id": "INC-1001",
                            "service": service,
                            "status": "open",
                            "summary": f"Incidencia intermitente en {service}",
                        }
                    ],
                },
                ensure_ascii=False,
            )

        if action == "create":
            now = datetime.now(timezone.utc).isoformat()
            return json.dumps(
                {
                    "ok": True,
                    "ticket_id": "INC-NEW-001",
                    "created_at_utc": now,
                    "payload": payload,
                },
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "ok": False,
                "error": f"Acción no soportada: {action}",
            },
            ensure_ascii=False,
        )