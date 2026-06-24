from __future__ import annotations

import json
from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from src.migration.legacy_inventory import LegacyFramework, classify_component


@tool(
    name="classify_legacy_component",
    description=(
        "Clasifica una pieza heredada de Semantic Kernel o AutoGen y propone "
        "su destino arquitectónico en Microsoft Agent Framework."
    ),
    approval_mode="never_require",
)
def classify_legacy_component(
    source_framework: Annotated[
        Literal["semantic_kernel", "autogen", "mixed"],
        Field(description="Framework principal del que procede la pieza heredada."),
    ],
    component_name: Annotated[
        str,
        Field(description="Nombre de la pieza legacy. Ejemplo: TicketPlugin, GroupChat, Kernel."),
    ],
    legacy_role: Annotated[
        str,
        Field(description="Responsabilidad actual de la pieza en la arquitectura heredada."),
    ],
    has_external_action: Annotated[
        bool,
        Field(description="Indica si la pieza ejecuta acciones sobre sistemas externos."),
    ] = False,
    has_state: Annotated[
        bool,
        Field(description="Indica si la pieza guarda historial, memoria o estado operativo."),
    ] = False,
    is_multi_step: Annotated[
        bool,
        Field(description="Indica si la pieza coordina varios pasos, agentes o decisiones."),
    ] = False,
    is_user_facing: Annotated[
        bool,
        Field(description="Indica si la pieza está directamente expuesta al usuario final."),
    ] = False,
) -> str:
    recommendation = classify_component(
        source_framework=LegacyFramework(source_framework),
        component_name=component_name,
        legacy_role=legacy_role,
        has_external_action=has_external_action,
        has_state=has_state,
        is_multi_step=is_multi_step,
        is_user_facing=is_user_facing,
    )

    return json.dumps(
        recommendation.to_dict(),
        ensure_ascii=False,
        indent=2,
    )