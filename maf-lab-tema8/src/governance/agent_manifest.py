from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


Environment = Literal["dev", "test", "prod"]
RiskLevel = Literal["low", "medium", "high", "critical"]
DataClassification = Literal["public", "internal", "confidential", "restricted"]


class ToolPolicy(BaseModel):
    allowed_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    requires_approval_for: list[str] = Field(default_factory=list)


class RuntimePolicy(BaseModel):
    model_alias: str
    generation_profile: str
    max_input_chars: int = Field(ge=100, le=20000)
    structured_response_required: bool
    human_validation_required_for: list[str] = Field(default_factory=list)


class TestPolicy(BaseModel):
    regression_suite: str
    minimum_cases: int = Field(ge=1)
    must_include_adversarial_cases: bool = True
    must_validate_structured_output: bool = True


class Ownership(BaseModel):
    business_owner: str
    technical_owner: str
    support_group: str
    change_approver: str


class AgentManifest(BaseModel):
    agent_name: str
    agent_version: str
    environment: Environment
    purpose: str
    risk_level: RiskLevel
    data_classification: DataClassification
    prompt_version: str
    tool_catalog_version: str
    response_contract_version: str
    ownership: Ownership
    tool_policy: ToolPolicy
    runtime_policy: RuntimePolicy
    test_policy: TestPolicy
    rollback_version: str | None = None

    @model_validator(mode="after")
    def validate_enterprise_rules(self) -> "AgentManifest":
        if self.environment == "prod" and self.rollback_version is None:
            raise ValueError("En producción debe existir rollback_version.")

        if self.risk_level in {"high", "critical"}:
            if not self.runtime_policy.structured_response_required:
                raise ValueError(
                    "Agentes de riesgo alto o crítico deben requerir respuesta estructurada."
                )

            if not self.test_policy.must_include_adversarial_cases:
                raise ValueError(
                    "Agentes de riesgo alto o crítico deben incluir tests adversariales."
                )

        dangerous_tools = {
            "delete_user",
            "modify_permissions",
            "create_real_ticket",
            "run_shell_command",
        }

        exposed_dangerous = dangerous_tools.intersection(
            set(self.tool_policy.allowed_tools)
        )

        if exposed_dangerous and not self.tool_policy.requires_approval_for:
            raise ValueError(
                "Hay tools sensibles permitidas, pero no se ha definido aprobación."
            )

        return self


SUPPORT_L1_MANIFEST = AgentManifest(
    agent_name="support_l1_agent",
    agent_version="1.0.0",
    environment="dev",
    purpose=(
        "Agente de soporte técnico L1 para diagnosticar incidencias básicas, "
        "consultar estado simulado, calcular SLA y preparar borradores de ticket."
    ),
    risk_level="medium",
    data_classification="internal",
    prompt_version="support-l1-structured-v1.0.0",
    tool_catalog_version="support-tools-l1-v1.0.0",
    response_contract_version="support-response-v1.0.0",
    ownership=Ownership(
        business_owner="IT Support",
        technical_owner="Equipo MAF",
        support_group="Soporte N1",
        change_approver="Responsable de Operaciones",
    ),
    tool_policy=ToolPolicy(
        allowed_tools=[
            "normalize_service",
            "get_service_status",
            "calculate_sla_deadline",
            "classify_incident_risk",
            "draft_support_ticket",
        ],
        forbidden_tools=[
            "create_real_ticket",
            "modify_permissions",
            "delete_user",
            "run_shell_command",
        ],
        requires_approval_for=[],
    ),
    runtime_policy=RuntimePolicy(
        model_alias="chat_default",
        generation_profile="balanced_support",
        max_input_chars=3000,
        structured_response_required=True,
        human_validation_required_for=[
            "priority_p1",
            "critical_risk",
            "real_action_requested",
        ],
    ),
    test_policy=TestPolicy(
        regression_suite="tests/prompt_cases_support_l1.json",
        minimum_cases=10,
        must_include_adversarial_cases=True,
        must_validate_structured_output=True,
    ),
    rollback_version=None,
)