from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ProfileName = Literal[
    "deterministic_json",
    "balanced_support",
    "creative_draft",
    "short_answer",
]


@dataclass(frozen=True)
class GenerationProfile:
    name: str
    temperature: float
    top_p: float
    max_tokens: int
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    description: str = ""


GENERATION_PROFILES: dict[str, GenerationProfile] = {
    "deterministic_json": GenerationProfile(
        name="deterministic_json",
        temperature=0.0,
        top_p=1.0,
        max_tokens=500,
        description="Salidas estructuradas, clasificación y respuestas que deben ser estables.",
    ),
    "balanced_support": GenerationProfile(
        name="balanced_support",
        temperature=0.2,
        top_p=1.0,
        max_tokens=700,
        description="Soporte técnico L1 con equilibrio entre claridad y estabilidad.",
    ),
    "creative_draft": GenerationProfile(
        name="creative_draft",
        temperature=0.7,
        top_p=1.0,
        max_tokens=900,
        description="Redacción de alternativas, mensajes al usuario o borradores explicativos.",
    ),
    "short_answer": GenerationProfile(
        name="short_answer",
        temperature=0.1,
        top_p=1.0,
        max_tokens=180,
        description="Respuesta breve para ahorrar coste y reducir latencia.",
    ),
}


def get_generation_profile(name: str) -> GenerationProfile:
    try:
        return GENERATION_PROFILES[name]
    except KeyError as exc:
        allowed = ", ".join(GENERATION_PROFILES)
        raise ValueError(f"Perfil de generación no registrado: {name}. Permitidos: {allowed}") from exc