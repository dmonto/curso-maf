from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.prompts.renderer import load_prompt_file, render_template
from src.settings import get_settings


PROMPTS_ROOT = Path(__file__).parent


@dataclass(frozen=True)
class PromptRegistration:
    agent_name: str
    version: str
    profile: str
    path: Path
    description: str


def get_support_prompt_registration(
    *,
    version: str,
    profile: str,
) -> PromptRegistration:
    supported_versions = {
        "v1": PROMPTS_ROOT / "support_agent" / "v1_system.md",
    }

    supported_profiles = {"default", "strict", "diagnostic"}

    if version not in supported_versions:
        available = ", ".join(sorted(supported_versions.keys()))
        raise ValueError(
            f"Versión de prompt no soportada: {version}. "
            f"Versiones disponibles: {available}"
        )

    if profile not in supported_profiles:
        available = ", ".join(sorted(supported_profiles))
        raise ValueError(
            f"Perfil de prompt no soportado: {profile}. "
            f"Perfiles disponibles: {available}"
        )

    return PromptRegistration(
        agent_name="maf_tools_agent",
        version=version,
        profile=profile,
        path=supported_versions[version],
        description="Prompt de sistema para agente de soporte IT.",
    )


def render_support_prompt() -> tuple[str, PromptRegistration]:
    settings = get_settings()

    registration = get_support_prompt_registration(
        version=settings.agent_prompt_version,
        profile=settings.agent_prompt_profile,
    )

    template = load_prompt_file(registration.path)

    prompt = render_template(
        template,
        {
            "environment": settings.agent_environment,
            "profile": registration.profile,
            "allowed_services": settings.agent_allowed_services,
        },
    )

    if registration.profile == "strict":
        prompt += """

Reglas adicionales del perfil strict:
- Si falta información, pregunta antes de asumir.
- No prepares borradores de ticket si falta descripción concreta del impacto.
- No sugieras prioridad alta sin evidencia suficiente.
"""

    elif registration.profile == "diagnostic":
        prompt += """

Reglas adicionales del perfil diagnostic:
- Explica brevemente qué comprobación has realizado.
- Diferencia entre datos devueltos por tools y recomendaciones.
- Si hay incertidumbre, indícala de forma explícita.
"""

    return prompt, registration