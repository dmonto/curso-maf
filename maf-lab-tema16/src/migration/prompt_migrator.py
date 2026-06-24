from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class PromptBlock(StrEnum):
    ROLE = "role"
    GOAL = "goal"
    TOOL_POLICY = "tool_policy"
    BUSINESS_RULE = "business_rule"
    OUTPUT_FORMAT = "output_format"
    SAFETY = "safety"
    MEMORY_OR_STATE = "memory_or_state"
    ROUTING = "routing"
    UNCERTAINTY = "uncertainty"
    KNOWLEDGE = "knowledge"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PromptFinding:
    block: str
    text: str
    target_maf_component: str
    reason: str


@dataclass(frozen=True)
class PromptMigrationPlan:
    legacy_prompt_name: str
    findings: list[PromptFinding]
    recommended_instructions: str
    files_to_create: list[str]
    risks: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "legacy_prompt_name": self.legacy_prompt_name,
            "findings": [asdict(item) for item in self.findings],
            "recommended_instructions": self.recommended_instructions,
            "files_to_create": self.files_to_create,
            "risks": self.risks,
        }


PATTERNS: list[tuple[PromptBlock, re.Pattern[str], str, str]] = [
    (
        PromptBlock.ROLE,
        re.compile(r"\b(eres|actúa como|tu rol|you are)\b", re.IGNORECASE),
        "agent.instructions",
        "Define identidad y responsabilidad general del agente.",
    ),
    (
        PromptBlock.TOOL_POLICY,
        re.compile(r"\b(usa la tool|usa la herramienta|llama a|invoca|consulta la api)\b", re.IGNORECASE),
        "tool descriptions + agent.instructions",
        "Describe cuándo el agente debería usar una capacidad externa.",
    ),
    (
        PromptBlock.BUSINESS_RULE,
        re.compile(r"\b(si .* entonces|prioridad|sla|impacto|afecta a|regla)\b", re.IGNORECASE),
        "domain service / workflow / validation tool",
        "Contiene reglas repetibles que no deberían depender solo del modelo.",
    ),
    (
        PromptBlock.OUTPUT_FORMAT,
        re.compile(r"\b(json|yaml|formato|devuelve|estructura|campos)\b", re.IGNORECASE),
        "output model + validator",
        "Define contrato de salida y debería validarse fuera del LLM.",
    ),
    (
        PromptBlock.SAFETY,
        re.compile(r"\b(no reveles|datos sensibles|confidencial|credenciales|privacidad|permisos)\b", re.IGNORECASE),
        "guardrail + instructions + tests",
        "Impone límites de seguridad que deben probarse y reforzarse.",
    ),
    (
        PromptBlock.MEMORY_OR_STATE,
        re.compile(r"\b(recuerda|historial|estado|sesión|ya se ha|pasos previos)\b", re.IGNORECASE),
        "session state / memory store",
        "Describe continuidad de conversación o proceso.",
    ),
    (
        PromptBlock.ROUTING,
        re.compile(r"\b(deriva|escala|pasa a|agente de|coordinador|especialista)\b", re.IGNORECASE),
        "workflow / handoff / routing function",
        "Coordina agentes o rutas y conviene hacerla explícita.",
    ),
    (
        PromptBlock.UNCERTAINTY,
        re.compile(r"\b(si no sabes|si falta|pregunta|aclara|información insuficiente)\b", re.IGNORECASE),
        "agent.instructions",
        "Define comportamiento ante incertidumbre o datos incompletos.",
    ),
    (
        PromptBlock.KNOWLEDGE,
        re.compile(r"\b(procedimiento|manual|documentación|política interna|base de conocimiento)\b", re.IGNORECASE),
        "RAG / knowledge tool",
        "Introduce conocimiento de dominio que debería vivir en fuente documental.",
    ),
]


def split_prompt(prompt_text: str) -> list[str]:
    lines = [line.strip(" -•\t") for line in prompt_text.splitlines()]
    return [line for line in lines if line]


def classify_line(line: str) -> PromptFinding:
    for block, pattern, target, reason in PATTERNS:
        if pattern.search(line):
            return PromptFinding(
                block=block.value,
                text=line,
                target_maf_component=target,
                reason=reason,
            )

    return PromptFinding(
        block=PromptBlock.UNKNOWN.value,
        text=line,
        target_maf_component="manual_review",
        reason="No se ha reconocido un patrón claro; requiere revisión.",
    )


def build_recommended_instructions(findings: list[PromptFinding]) -> str:
    role_lines = [f.text for f in findings if f.block == PromptBlock.ROLE.value]
    uncertainty_lines = [f.text for f in findings if f.block == PromptBlock.UNCERTAINTY.value]
    safety_lines = [f.text for f in findings if f.block == PromptBlock.SAFETY.value]

    instructions = [
        "Eres un agente especializado en soporte IT interno.",
        "Tu objetivo es ayudar a diagnosticar incidencias y preparar respuestas accionables.",
        "Trabaja únicamente dentro del alcance de soporte de nivel 1.",
        "Usa tools registradas cuando necesites consultar documentación, validar prioridad o preparar acciones.",
        "No ejecutes acciones reales sin confirmación explícita.",
        "Si falta información crítica, pide una aclaración concreta.",
        "No expongas credenciales, secretos ni datos personales innecesarios.",
    ]

    if role_lines:
        instructions[0] = role_lines[0]

    for line in uncertainty_lines + safety_lines:
        if line not in instructions:
            instructions.append(line)

    return "\n".join(f"- {line}" for line in instructions)


def migrate_prompt(
    *,
    legacy_prompt_name: str,
    prompt_text: str,
) -> PromptMigrationPlan:
    lines = split_prompt(prompt_text)
    findings = [classify_line(line) for line in lines]

    blocks = {finding.block for finding in findings}

    files_to_create = [
        "src/prompts/<agent_name>/instructions.md",
        "src/prompts/<agent_name>/metadata.json",
        "tests/test_prompt_rendering.py",
    ]

    if PromptBlock.BUSINESS_RULE.value in blocks:
        files_to_create.append("src/domain/support_policy.py")

    if PromptBlock.TOOL_POLICY.value in blocks:
        files_to_create.append("src/tools/support_tools.py")

    if PromptBlock.ROUTING.value in blocks:
        files_to_create.append("src/workflows/support_workflow.py")

    if PromptBlock.MEMORY_OR_STATE.value in blocks:
        files_to_create.append("src/state/support_session_state.py")

    if PromptBlock.KNOWLEDGE.value in blocks:
        files_to_create.append("src/tools/rag_tools.py")

    risks: list[str] = []

    if PromptBlock.OUTPUT_FORMAT.value in blocks:
        risks.append("El formato de salida no debería depender solo del prompt; añade validación.")

    if PromptBlock.SAFETY.value in blocks:
        risks.append("Las reglas de seguridad deben probarse con casos negativos.")

    if PromptBlock.BUSINESS_RULE.value in blocks:
        risks.append("Las reglas de negocio embebidas en prompt pueden generar resultados inconsistentes.")

    if PromptBlock.UNKNOWN.value in blocks:
        risks.append("Hay líneas que requieren revisión manual antes de migrar.")

    return PromptMigrationPlan(
        legacy_prompt_name=legacy_prompt_name,
        findings=findings,
        recommended_instructions=build_recommended_instructions(findings),
        files_to_create=files_to_create,
        risks=risks,
    )