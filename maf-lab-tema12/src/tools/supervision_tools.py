from __future__ import annotations

import json
from typing import Annotated, Literal
from uuid import uuid4

from agent_framework import tool
from pydantic import Field

from src.agents.multiagent.supervision import (
    SUPERVISION_STORE,
    SupervisionEvent,
    SupervisionEventType,
    SupervisionSeverity,
    decision_to_json,
    event_to_json,
)


SeverityLiteral = Literal["info", "warning", "high", "critical"]

EventTypeLiteral = Literal[
    "delegation",
    "tool_call",
    "state_update",
    "recommendation",
    "risk_detected",
    "conflict_detected",
    "policy_check",
    "error",
]


@tool(
    name="crear_run_supervision",
    description=(
        "Crea un identificador de ejecución supervisada. "
        "Debe usarse al inicio de un caso multiagente."
    ),
)
def crear_run_supervision() -> str:
    return json.dumps(
        {
            "run_id": str(uuid4()),
        },
        ensure_ascii=False,
        indent=2,
    )


@tool(
    name="registrar_evento_supervision",
    description=(
        "Registra un evento de supervisión centralizada. "
        "Úsala para delegaciones, riesgos, conflictos, recomendaciones, errores o cambios relevantes."
    ),
)
def registrar_evento_supervision(
    run_id: Annotated[
        str,
        Field(description="Identificador de la ejecución supervisada."),
    ],
    agent_name: Annotated[
        str,
        Field(description="Nombre del agente que genera o provoca el evento."),
    ],
    event_type: Annotated[
        EventTypeLiteral,
        Field(description="Tipo de evento de supervisión."),
    ],
    severity: Annotated[
        SeverityLiteral,
        Field(description="Severidad del evento."),
    ],
    summary: Annotated[
        str,
        Field(description="Resumen breve del evento.", min_length=5),
    ],
    details_json: Annotated[
        str,
        Field(
            description=(
                "Detalles adicionales en JSON. "
                "Usa {} si no hay detalles."
            ),
        ),
    ] = "{}",
    requires_review: Annotated[
        bool,
        Field(description="Indica si el evento requiere revisión antes de continuar."),
    ] = False,
) -> str:
    try:
        details = json.loads(details_json)
        if not isinstance(details, dict):
            raise ValueError("details_json debe ser un objeto JSON")

        event = SupervisionEvent(
            run_id=run_id,
            agent_name=agent_name,
            event_type=SupervisionEventType(event_type),
            severity=SupervisionSeverity(severity),
            summary=summary,
            details=details,
            requires_review=requires_review,
        )

        SUPERVISION_STORE.record(event)

        return json.dumps(
            {
                "ok": True,
                "event": json.loads(event_to_json(event)),
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        return json.dumps(
            {
                "ok": False,
                "error": str(exc),
            },
            ensure_ascii=False,
            indent=2,
        )


@tool(
    name="consultar_eventos_supervision",
    description=(
        "Consulta todos los eventos de supervisión registrados para una ejecución."
    ),
)
def consultar_eventos_supervision(
    run_id: Annotated[
        str,
        Field(description="Identificador de la ejecución supervisada."),
    ],
) -> str:
    return SUPERVISION_STORE.to_json(run_id)


@tool(
    name="evaluar_politicas_supervision",
    description=(
        "Evalúa políticas centralizadas sobre los eventos de una ejecución. "
        "Devuelve si se puede continuar o si debe bloquearse/escalarse."
    ),
)
def evaluar_politicas_supervision(
    run_id: Annotated[
        str,
        Field(description="Identificador de la ejecución supervisada."),
    ],
) -> str:
    decision = SUPERVISION_STORE.evaluate_policies(run_id)
    return decision_to_json(decision)