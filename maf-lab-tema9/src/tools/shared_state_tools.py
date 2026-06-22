from __future__ import annotations

import json
from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from src.agents.multiagent.shared_state import (
    STATE_STORE,
    StateConflictError,
    StatePermissionError,
    state_to_json,
)


RoleName = Literal[
    "support_coordinator",
    "network_specialist",
    "identity_specialist",
    "security_specialist",
    "itsm_specialist",
]


@tool(
    name="crear_estado_caso",
    description=(
        "Crea un nuevo estado compartido para un caso de soporte. "
        "Debe usarlo el coordinador al iniciar un caso nuevo."
    ),
)
def crear_estado_caso(
    servicio: Annotated[
        str,
        Field(description="Servicio afectado. Ejemplos: VPN, ERP, correo, Teams."),
    ],
    sintoma: Annotated[
        str,
        Field(description="Síntoma principal reportado por el usuario."),
    ],
    area_usuario: Annotated[
        str,
        Field(description="Área del usuario afectado. Ejemplo: Finanzas."),
    ] = "desconocida",
    ubicacion: Annotated[
        str,
        Field(description="Ubicación o contexto de conexión. Ejemplo: casa, oficina."),
    ] = "desconocida",
) -> str:
    state = STATE_STORE.create_case(
        {
            "service": servicio,
            "symptom": sintoma,
            "user_area": area_usuario,
            "location": ubicacion,
        }
    )

    return state_to_json(state)


@tool(
    name="leer_estado_caso",
    description=(
        "Lee el estado compartido actual de un caso. "
        "Devuelve la versión actual y los campos operativos relevantes."
    ),
)
def leer_estado_caso(
    case_id: Annotated[
        str,
        Field(description="Identificador del caso compartido."),
    ],
) -> str:
    try:
        state = STATE_STORE.get_case(case_id)
        return state_to_json(state)
    except KeyError as exc:
        return json.dumps(
            {
                "ok": False,
                "error": str(exc),
            },
            ensure_ascii=False,
            indent=2,
        )


@tool(
    name="actualizar_estado_caso",
    description=(
        "Actualiza el estado compartido de un caso aplicando control de rol y versión. "
        "Cada rol solo puede modificar campos permitidos. "
        "Si la versión esperada no coincide, devuelve conflicto."
    ),
)
def actualizar_estado_caso(
    role: Annotated[
        RoleName,
        Field(description="Rol que solicita la actualización del estado."),
    ],
    case_id: Annotated[
        str,
        Field(description="Identificador del caso."),
    ],
    expected_version: Annotated[
        int,
        Field(description="Versión del estado leída antes de proponer el cambio."),
    ],
    changes_json: Annotated[
        str,
        Field(
            description=(
                "Cambios en formato JSON. "
                "Ejemplo: {\"identity_findings\": [\"posible falta de grupo ERP\"]}"
            ),
        ),
    ],
    reason: Annotated[
        str,
        Field(description="Motivo funcional del cambio."),
    ],
) -> str:
    try:
        changes = json.loads(changes_json)

        if not isinstance(changes, dict):
            raise ValueError("changes_json debe representar un objeto JSON")

        state = STATE_STORE.update_case(
            case_id=case_id,
            role=role,
            expected_version=expected_version,
            changes=changes,
            reason=reason,
        )

        return json.dumps(
            {
                "ok": True,
                "state": json.loads(state_to_json(state)),
            },
            ensure_ascii=False,
            indent=2,
        )

    except StateConflictError as exc:
        return json.dumps(
            {
                "ok": False,
                "error_type": "state_conflict",
                "error": str(exc),
                "recommended_action": "leer_estado_caso y reintentar con la versión actual",
            },
            ensure_ascii=False,
            indent=2,
        )

    except StatePermissionError as exc:
        return json.dumps(
            {
                "ok": False,
                "error_type": "permission_error",
                "error": str(exc),
                "recommended_action": "revisar si el rol correcto debe hacer esta actualización",
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        return json.dumps(
            {
                "ok": False,
                "error_type": "unexpected_error",
                "error": str(exc),
            },
            ensure_ascii=False,
            indent=2,
        )