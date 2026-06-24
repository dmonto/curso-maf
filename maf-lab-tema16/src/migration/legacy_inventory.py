from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class LegacyFramework(StrEnum):
    SEMANTIC_KERNEL = "semantic_kernel"
    AUTOGEN = "autogen"
    MIXED = "mixed"


class TargetMafComponent(StrEnum):
    AGENT = "agent"
    TOOL = "tool"
    WORKFLOW = "workflow"
    SESSION_STATE = "session_state"
    MEMORY = "memory"
    CONTEXT_PROVIDER = "context_provider"
    MODEL_REGISTRY = "model_registry"
    TELEMETRY = "telemetry"
    INTERNAL_SERVICE = "internal_service"
    REVIEW_NEEDED = "review_needed"


@dataclass(frozen=True)
class MigrationRecommendation:
    source_framework: str
    component_name: str
    legacy_role: str
    target_component: str
    reason: str
    migration_notes: list[str]
    risks: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_component(
    *,
    source_framework: LegacyFramework,
    component_name: str,
    legacy_role: str,
    has_external_action: bool,
    has_state: bool,
    is_multi_step: bool,
    is_user_facing: bool,
) -> MigrationRecommendation:
    role = legacy_role.lower()
    name = component_name.lower()

    notes: list[str] = []
    risks: list[str] = []

    target = TargetMafComponent.REVIEW_NEEDED
    reason = "No hay suficiente información para asignar un destino único."

    if "plugin" in role or "function" in role:
        if has_external_action:
            target = TargetMafComponent.TOOL
            reason = "La pieza expone una capacidad invocable por el agente."
            notes.append("Definir contrato de entrada y salida con tipos claros.")
            notes.append("Añadir política de aprobación si modifica sistemas reales.")
            risks.append("No migrar funciones internas como tools si el agente no debe decidir cuándo usarlas.")
        else:
            target = TargetMafComponent.INTERNAL_SERVICE
            reason = "Parece una utilidad interna, no necesariamente una tool agentic."
            notes.append("Mantener como servicio Python si solo lo usa la aplicación.")

    if "prompt" in role or "template" in role:
        target = TargetMafComponent.AGENT
        reason = "La pieza contiene instrucciones de comportamiento o generación."
        notes.append("Separar instrucciones estables, reglas de seguridad y formato de salida.")
        risks.append("No trasladar prompts largos sin dividir responsabilidades.")

    if "memory" in role or "history" in role or has_state:
        target = TargetMafComponent.SESSION_STATE
        reason = "La pieza mantiene continuidad de sesión o proceso."
        notes.append("Distinguir entre historial conversacional, estado operativo y memoria persistente.")
        risks.append("Migrar todo el historial como memoria puede aumentar coste, ruido y exposición de datos.")

    if "groupchat" in role or "speaker" in role or is_multi_step:
        target = TargetMafComponent.WORKFLOW
        reason = "La pieza coordina pasos, rutas o varios participantes."
        notes.append("Convertir turnos implícitos en pasos explícitos.")
        notes.append("Definir condiciones de entrada, salida y error para cada paso.")
        risks.append("Un debate libre entre agentes puede ser difícil de auditar en producción.")

    if "agent" in role and not is_multi_step:
        target = TargetMafComponent.AGENT
        reason = "La pieza representa una responsabilidad conversacional o especializada."
        notes.append("Mantener instrucciones cortas y delegar acciones en tools.")

    if "kernel" in role:
        target = TargetMafComponent.MODEL_REGISTRY
        reason = "El kernel suele mezclar composición de modelo, funciones y configuración."
        notes.append("Separar configuración de modelos, tools, agentes y workflows.")
        risks.append("Migrar el kernel como un único agente conserva el acoplamiento original.")

    if "log" in role or "trace" in role or "callback" in role:
        target = TargetMafComponent.TELEMETRY
        reason = "La pieza está relacionada con observabilidad o trazabilidad."
        notes.append("Convertir logs dispersos en eventos estructurados.")

    if is_user_facing:
        notes.append("Separar la experiencia de usuario de la lógica agentic.")

    return MigrationRecommendation(
        source_framework=source_framework.value,
        component_name=component_name,
        legacy_role=legacy_role,
        target_component=target.value,
        reason=reason,
        migration_notes=notes,
        risks=risks,
    )