from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class LayerRule:
    name: str
    path_prefix: str
    forbidden_internal_prefixes: tuple[str, ...] = field(default_factory=tuple)
    forbidden_external_roots: tuple[str, ...] = field(default_factory=tuple)


FORBIDDEN_FRAMEWORK_IMPORTS = (
    "agent_framework",
    "openai",
    "azure",
    "httpx",
    "fastapi",
    "uvicorn",
)


LAYER_RULES: tuple[LayerRule, ...] = (
    LayerRule(
        name="domain",
        path_prefix="src/clean_arch/domain/",
        forbidden_internal_prefixes=(
            "src.clean_arch.application",
            "src.clean_arch.infrastructure",
            "src.tools",
            "src.agents",
            "src.di",
            "src.models",
            "src.events",
            "src.observability",
            "src.contracts",
        ),
        forbidden_external_roots=FORBIDDEN_FRAMEWORK_IMPORTS + ("pydantic",),
    ),
    LayerRule(
        name="application",
        path_prefix="src/clean_arch/application/",
        forbidden_internal_prefixes=(
            "src.clean_arch.infrastructure",
            "src.tools",
            "src.agents",
            "src.di",
            "src.models",
        ),
        forbidden_external_roots=FORBIDDEN_FRAMEWORK_IMPORTS,
    ),
    LayerRule(
        name="contracts",
        path_prefix="src/contracts/",
        forbidden_internal_prefixes=(
            "src.tools",
            "src.agents",
            "src.clean_arch.infrastructure",
            "src.di",
        ),
        forbidden_external_roots=(
            "agent_framework",
            "azure",
            "httpx",
            "fastapi",
            "uvicorn",
        ),
    ),
    LayerRule(
        name="infrastructure",
        path_prefix="src/clean_arch/infrastructure/",
        forbidden_internal_prefixes=(
            "src.tools",
            "src.agents",
        ),
        forbidden_external_roots=(
            "agent_framework",
        ),
    ),
    LayerRule(
        name="tools",
        path_prefix="src/tools/",
        forbidden_internal_prefixes=(
            "src.agents",
            "src.clean_arch.infrastructure",
        ),
        forbidden_external_roots=(),
    ),
    LayerRule(
        name="agents",
        path_prefix="src/agents/",
        forbidden_internal_prefixes=(
            "src.clean_arch.infrastructure",
        ),
        forbidden_external_roots=(
            "httpx",
            "fastapi",
            "uvicorn",
        ),
    ),
)


def normalize_path(path: Path) -> str:
    return path.as_posix()


def find_layer_rule(path: Path) -> LayerRule | None:
    normalized = normalize_path(path)

    for rule in LAYER_RULES:
        if normalized.startswith(rule.path_prefix):
            return rule

    return None