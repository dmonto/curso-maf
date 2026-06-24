from __future__ import annotations

import json
from typing import Annotated

from agent_framework import tool
from pydantic import Field

from src.migration.prompt_migrator import migrate_prompt


@tool(
    name="analyze_legacy_prompt",
    description=(
        "Analiza un prompt legacy de Semantic Kernel o AutoGen y propone "
        "cómo descomponerlo en instrucciones, tools, workflow, estado, memoria o validadores MAF."
    ),
    approval_mode="never_require",
)
def analyze_legacy_prompt(
    legacy_prompt_name: Annotated[
        str,
        Field(description="Nombre del prompt heredado. Ejemplo: support_triage_prompt."),
    ],
    prompt_text: Annotated[
        str,
        Field(description="Texto completo del prompt heredado."),
    ],
) -> str:
    plan = migrate_prompt(
        legacy_prompt_name=legacy_prompt_name,
        prompt_text=prompt_text,
    )

    return json.dumps(
        plan.to_dict(),
        ensure_ascii=False,
        indent=2,
    )