from __future__ import annotations

from typing import Annotated

from agent_framework import tool
from pydantic import Field

from src.integrations.support_db import (
    DatabaseIntegrationError,
    SupportDbRepository,
)


@tool(
    name="consultar_ticket_db",
    description=(
        "Consulta un ticket de soporte en la base de datos local del laboratorio. "
        "Úsala cuando el usuario pregunte por el estado, prioridad, servicio, "
        "resumen o propietario de un ticket existente. No modifica datos."
    ),
)
def consultar_ticket_db(
    ticket_id: Annotated[
        str,
        Field(description="Identificador del ticket. Ejemplo: INC-1001."),
    ],
) -> dict:
    repo = SupportDbRepository.from_env()
    ticket = repo.get_ticket(ticket_id)

    if not ticket:
        return {
            "ok": False,
            "found": False,
            "error": f"No existe el ticket {ticket_id.strip().upper()}",
        }

    return {
        "ok": True,
        "found": True,
        "ticket": ticket.model_dump(),
    }


@tool(
    name="buscar_activos_usuario_db",
    description=(
        "Busca activos asignados a un usuario en la base de datos local. "
        "Úsala cuando el usuario pregunte por portátiles, móviles u otros activos "
        "asignados a una dirección de correo. No modifica datos."
    ),
)
def buscar_activos_usuario_db(
    owner_email: Annotated[
        str,
        Field(description="Correo corporativo del usuario propietario de los activos."),
    ],
) -> dict:
    repo = SupportDbRepository.from_env()
    assets = repo.find_assets_by_owner(owner_email)

    return {
        "ok": True,
        "owner_email": owner_email.strip().lower(),
        "count": len(assets),
        "assets": [asset.model_dump() for asset in assets],
    }


@tool(
    name="resumir_tickets_por_servicio_db",
    description=(
        "Devuelve un resumen agregado de tickets por servicio, estado y prioridad. "
        "Úsala para preguntas de visión general sobre carga operativa o estado "
        "de incidencias. No devuelve datos personales y no modifica datos."
    ),
)
def resumir_tickets_por_servicio_db() -> dict:
    repo = SupportDbRepository.from_env()
    rows = repo.summarize_tickets_by_service()

    return {
        "ok": True,
        "rows": rows,
    }


@tool(
    name="anadir_nota_ticket_db",
    description=(
        "Añade una nota interna a un ticket existente en la base de datos local. "
        "Úsala solo si el usuario pide explícitamente registrar una nota. "
        "No cambia el estado ni la prioridad del ticket."
    ),
)
def anadir_nota_ticket_db(
    ticket_id: Annotated[
        str,
        Field(description="Identificador del ticket. Ejemplo: INC-1001."),
    ],
    note: Annotated[
        str,
        Field(description="Nota interna a registrar. Mínimo 10 caracteres."),
    ],
    created_by: Annotated[
        str,
        Field(description="Correo de quien registra la nota."),
    ],
) -> dict:
    repo = SupportDbRepository.from_env()

    try:
        record = repo.add_ticket_note(
            ticket_id=ticket_id,
            note=note,
            created_by=created_by,
        )
        return {
            "ok": True,
            "created": True,
            "note": record.model_dump(),
        }
    except DatabaseIntegrationError as exc:
        return {
            "ok": False,
            "created": False,
            "error": str(exc),
        }