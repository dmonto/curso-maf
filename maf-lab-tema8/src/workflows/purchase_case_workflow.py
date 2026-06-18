from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import StrEnum
from typing_extensions import Never

from agent_framework import WorkflowBuilder, WorkflowContext, executor
from pydantic import BaseModel, Field


class PurchaseCategory(StrEnum):
    SOFTWARE = "software"
    CLOUD = "cloud"
    HARDWARE = "hardware"
    SERVICES = "services"
    TRAINING = "training"
    UNKNOWN = "unknown"


class VendorStatus(StrEnum):
    APPROVED = "approved"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DecisionRoute(StrEnum):
    REQUEST_MORE_DATA = "request_more_data"
    AUTO_APPROVE = "auto_approve"
    MANAGER_APPROVAL = "manager_approval"
    PROCUREMENT_REVIEW = "procurement_review"
    POLICY_REJECTED = "policy_rejected"


class FindingSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PurchaseRequestInput(BaseModel):
    description: str = Field(min_length=5)
    requester: str = Field(default="usuario.lab@contoso.com")
    department: str = Field(default="IT")
    amount_eur: float | None = Field(default=None, ge=0)
    vendor: str | None = None
    justification: str | None = None
    category_hint: PurchaseCategory | None = None


class Finding(BaseModel):
    code: str
    severity: FindingSeverity
    step: str
    message: str
    field: str | None = None


class NormalizedPurchase(BaseModel):
    description: str
    normalized_description: str
    requester: str
    department: str
    amount_eur: float | None
    vendor: str | None
    category: PurchaseCategory
    justification: str | None
    findings: list[Finding] = Field(default_factory=list)


class EnrichedPurchase(BaseModel):
    description: str
    requester: str
    department: str
    amount_eur: float | None
    vendor: str | None
    category: PurchaseCategory
    justification: str | None
    department_limit_eur: float
    budget_owner: str
    vendor_status: VendorStatus
    security_review_required: bool
    findings: list[Finding]


class ValidatedPurchase(BaseModel):
    description: str
    requester: str
    department: str
    amount_eur: float | None
    vendor: str | None
    category: PurchaseCategory
    justification: str | None
    department_limit_eur: float
    budget_owner: str
    vendor_status: VendorStatus
    security_review_required: bool
    missing_fields: list[str]
    findings: list[Finding]


class AssessedPurchase(BaseModel):
    description: str
    requester: str
    department: str
    amount_eur: float | None
    vendor: str | None
    category: PurchaseCategory
    justification: str | None
    department_limit_eur: float
    budget_owner: str
    vendor_status: VendorStatus
    security_review_required: bool
    missing_fields: list[str]
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    route: DecisionRoute
    findings: list[Finding]


class PurchaseWorkflowOutput(BaseModel):
    decision: DecisionRoute
    title: str
    message: str
    requester: str
    department: str
    next_owner: str
    amount_eur: float | None
    vendor: str | None
    vendor_status: VendorStatus | None
    category: PurchaseCategory
    risk_score: int | None
    risk_level: RiskLevel | None
    required_actions: list[str]
    findings: list[Finding]
    approval_payload: dict[str, object] | None = None
    ready_for_real_action: bool = False
    created_at_utc: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def detect_category(text: str, hint: PurchaseCategory | None) -> PurchaseCategory:
    if hint is not None:
        return hint

    value = text.lower()

    if any(term in value for term in ["licencia", "software", "saas", "crm"]):
        return PurchaseCategory.SOFTWARE
    if any(term in value for term in ["azure", "cloud", "hosting", "storage"]):
        return PurchaseCategory.CLOUD
    if any(term in value for term in ["portátil", "portatil", "monitor", "servidor", "hardware"]):
        return PurchaseCategory.HARDWARE
    if any(term in value for term in ["consultoría", "consultoria", "servicio", "implantación"]):
        return PurchaseCategory.SERVICES
    if any(term in value for term in ["curso", "formación", "formacion", "training"]):
        return PurchaseCategory.TRAINING

    return PurchaseCategory.UNKNOWN


def lookup_department_policy(department: str) -> tuple[float, str]:
    policies = {
        "it": (5000.0, "it.manager@contoso.com"),
        "finance": (3000.0, "finance.manager@contoso.com"),
        "sales": (2500.0, "sales.manager@contoso.com"),
        "hr": (2000.0, "hr.manager@contoso.com"),
    }

    return policies.get(department.strip().lower(), (1000.0, "operations.manager@contoso.com"))


def lookup_vendor_status(vendor: str | None) -> VendorStatus:
    if vendor is None or not vendor.strip():
        return VendorStatus.UNKNOWN

    value = vendor.strip().lower()

    blocked = {"vendor-bloqueado", "risky-supplies", "unknown-payments"}
    approved = {"microsoft", "contoso partners", "fabrikam services", "adatum training"}

    if value in blocked:
        return VendorStatus.BLOCKED

    if value in approved:
        return VendorStatus.APPROVED

    return VendorStatus.UNKNOWN


def requires_security_review(category: PurchaseCategory, description: str) -> bool:
    value = description.lower()

    if category in {PurchaseCategory.SOFTWARE, PurchaseCategory.CLOUD}:
        return True

    sensitive_terms = ["datos personales", "cliente", "seguridad", "acceso", "integración", "api"]

    return any(term in value for term in sensitive_terms)


def route_is(route: DecisionRoute):
    def _condition(message: AssessedPurchase) -> bool:
        return message.route == route

    return _condition


@executor(id="normalize_purchase_request")
async def normalize_purchase_request(
    message: PurchaseRequestInput,
    ctx: WorkflowContext[NormalizedPurchase],
) -> None:
    normalized = message.description.strip().lower()
    category = detect_category(normalized, message.category_hint)

    findings: list[Finding] = []

    if category == PurchaseCategory.UNKNOWN:
        findings.append(
            Finding(
                code="category_not_identified",
                severity=FindingSeverity.WARNING,
                step="normalize_purchase_request",
                field="category",
                message="No se ha identificado claramente la categoría de compra.",
            )
        )

    await ctx.send_message(
        NormalizedPurchase(
            description=message.description.strip(),
            normalized_description=normalized,
            requester=message.requester.strip(),
            department=message.department.strip(),
            amount_eur=message.amount_eur,
            vendor=message.vendor.strip() if message.vendor else None,
            category=category,
            justification=message.justification.strip() if message.justification else None,
            findings=findings,
        )
    )


@executor(id="enrich_purchase_context")
async def enrich_purchase_context(
    message: NormalizedPurchase,
    ctx: WorkflowContext[EnrichedPurchase],
) -> None:
    limit, budget_owner = lookup_department_policy(message.department)
    vendor_status = lookup_vendor_status(message.vendor)
    security_review_required = requires_security_review(
        category=message.category,
        description=message.normalized_description,
    )

    findings = list(message.findings)

    if vendor_status == VendorStatus.UNKNOWN:
        findings.append(
            Finding(
                code="vendor_unknown",
                severity=FindingSeverity.WARNING,
                step="enrich_purchase_context",
                field="vendor",
                message="El proveedor no aparece en el catálogo de proveedores aprobados.",
            )
        )

    if vendor_status == VendorStatus.BLOCKED:
        findings.append(
            Finding(
                code="vendor_blocked",
                severity=FindingSeverity.CRITICAL,
                step="enrich_purchase_context",
                field="vendor",
                message="El proveedor aparece bloqueado por política interna.",
            )
        )

    if security_review_required:
        findings.append(
            Finding(
                code="security_review_required",
                severity=FindingSeverity.INFO,
                step="enrich_purchase_context",
                field="category",
                message="La compra requiere revisión de seguridad por su categoría o descripción.",
            )
        )

    await ctx.send_message(
        EnrichedPurchase(
            description=message.description,
            requester=message.requester,
            department=message.department,
            amount_eur=message.amount_eur,
            vendor=message.vendor,
            category=message.category,
            justification=message.justification,
            department_limit_eur=limit,
            budget_owner=budget_owner,
            vendor_status=vendor_status,
            security_review_required=security_review_required,
            findings=findings,
        )
    )


@executor(id="validate_purchase_request")
async def validate_purchase_request(
    message: EnrichedPurchase,
    ctx: WorkflowContext[ValidatedPurchase],
) -> None:
    missing_fields: list[str] = []
    findings = list(message.findings)

    if message.amount_eur is None:
        missing_fields.append("amount_eur")
        findings.append(
            Finding(
                code="amount_missing",
                severity=FindingSeverity.ERROR,
                step="validate_purchase_request",
                field="amount_eur",
                message="Falta el importe estimado de la compra.",
            )
        )

    if message.vendor is None:
        missing_fields.append("vendor")
        findings.append(
            Finding(
                code="vendor_missing",
                severity=FindingSeverity.ERROR,
                step="validate_purchase_request",
                field="vendor",
                message="Falta indicar el proveedor propuesto.",
            )
        )

    if message.amount_eur is not None and message.amount_eur >= 5000 and not message.justification:
        missing_fields.append("justification")
        findings.append(
            Finding(
                code="justification_required",
                severity=FindingSeverity.ERROR,
                step="validate_purchase_request",
                field="justification",
                message="Las compras de 5.000 EUR o más requieren justificación.",
            )
        )

    await ctx.send_message(
        ValidatedPurchase(
            description=message.description,
            requester=message.requester,
            department=message.department,
            amount_eur=message.amount_eur,
            vendor=message.vendor,
            category=message.category,
            justification=message.justification,
            department_limit_eur=message.department_limit_eur,
            budget_owner=message.budget_owner,
            vendor_status=message.vendor_status,
            security_review_required=message.security_review_required,
            missing_fields=missing_fields,
            findings=findings,
        )
    )


@executor(id="assess_purchase_risk")
async def assess_purchase_risk(
    message: ValidatedPurchase,
    ctx: WorkflowContext[AssessedPurchase],
) -> None:
    findings = list(message.findings)

    if message.missing_fields:
        route = DecisionRoute.REQUEST_MORE_DATA
        risk_score = 40
        risk_level = RiskLevel.MEDIUM

    elif message.vendor_status == VendorStatus.BLOCKED:
        route = DecisionRoute.POLICY_REJECTED
        risk_score = 100
        risk_level = RiskLevel.HIGH

    else:
        risk_score = 10

        if message.amount_eur is not None:
            if message.amount_eur > message.department_limit_eur:
                risk_score += 35
            if message.amount_eur >= 10000:
                risk_score += 25
            if message.amount_eur >= 50000:
                risk_score += 30

        if message.vendor_status == VendorStatus.UNKNOWN:
            risk_score += 25

        if message.security_review_required:
            risk_score += 20

        if message.category == PurchaseCategory.UNKNOWN:
            risk_score += 15

        risk_score = min(risk_score, 100)

        if risk_score >= 70:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 40:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        if message.amount_eur is not None and message.amount_eur >= 100000:
            route = DecisionRoute.POLICY_REJECTED
            findings.append(
                Finding(
                    code="amount_exceeds_policy_limit",
                    severity=FindingSeverity.CRITICAL,
                    step="assess_purchase_risk",
                    field="amount_eur",
                    message="El importe excede el límite permitido para este flujo automático.",
                )
            )
        elif message.vendor_status == VendorStatus.UNKNOWN or message.security_review_required:
            route = DecisionRoute.PROCUREMENT_REVIEW
        elif message.amount_eur is not None and message.amount_eur > message.department_limit_eur:
            route = DecisionRoute.MANAGER_APPROVAL
        else:
            route = DecisionRoute.AUTO_APPROVE

    await ctx.send_message(
        AssessedPurchase(
            description=message.description,
            requester=message.requester,
            department=message.department,
            amount_eur=message.amount_eur,
            vendor=message.vendor,
            category=message.category,
            justification=message.justification,
            department_limit_eur=message.department_limit_eur,
            budget_owner=message.budget_owner,
            vendor_status=message.vendor_status,
            security_review_required=message.security_review_required,
            missing_fields=message.missing_fields,
            risk_score=risk_score,
            risk_level=risk_level,
            route=route,
            findings=findings,
        )
    )


@executor(id="request_more_data")
async def request_more_data(
    message: AssessedPurchase,
    ctx: WorkflowContext[Never, PurchaseWorkflowOutput],
) -> None:
    await ctx.yield_output(
        PurchaseWorkflowOutput(
            decision=DecisionRoute.REQUEST_MORE_DATA,
            title="Faltan datos para evaluar la compra",
            message="La solicitud no puede avanzar hasta completar los campos obligatorios.",
            requester=message.requester,
            department=message.department,
            next_owner=message.requester,
            amount_eur=message.amount_eur,
            vendor=message.vendor,
            vendor_status=message.vendor_status,
            category=message.category,
            risk_score=message.risk_score,
            risk_level=message.risk_level,
            required_actions=[f"Completar campo: {field}" for field in message.missing_fields],
            findings=message.findings,
            ready_for_real_action=False,
            created_at_utc=utc_now(),
        )
    )


@executor(id="auto_approve_purchase")
async def auto_approve_purchase(
    message: AssessedPurchase,
    ctx: WorkflowContext[Never, PurchaseWorkflowOutput],
) -> None:
    await ctx.yield_output(
        PurchaseWorkflowOutput(
            decision=DecisionRoute.AUTO_APPROVE,
            title="Compra apta para aprobación automática simulada",
            message=(
                "La solicitud está dentro del límite del departamento, "
                "el proveedor está aprobado y no requiere revisión adicional."
            ),
            requester=message.requester,
            department=message.department,
            next_owner="procurement.operations@contoso.com",
            amount_eur=message.amount_eur,
            vendor=message.vendor,
            vendor_status=message.vendor_status,
            category=message.category,
            risk_score=message.risk_score,
            risk_level=message.risk_level,
            required_actions=["Registrar aprobación simulada", "Preparar orden de compra borrador"],
            findings=message.findings,
            approval_payload={
                "approved_by": "policy:auto",
                "policy_limit_eur": message.department_limit_eur,
                "budget_owner": message.budget_owner,
            },
            ready_for_real_action=False,
            created_at_utc=utc_now(),
        )
    )


@executor(id="manager_approval_pack")
async def manager_approval_pack(
    message: AssessedPurchase,
    ctx: WorkflowContext[Never, PurchaseWorkflowOutput],
) -> None:
    await ctx.yield_output(
        PurchaseWorkflowOutput(
            decision=DecisionRoute.MANAGER_APPROVAL,
            title="Aprobación de responsable requerida",
            message=(
                "La compra supera el límite automático del departamento. "
                "Debe revisarla el responsable presupuestario."
            ),
            requester=message.requester,
            department=message.department,
            next_owner=message.budget_owner,
            amount_eur=message.amount_eur,
            vendor=message.vendor,
            vendor_status=message.vendor_status,
            category=message.category,
            risk_score=message.risk_score,
            risk_level=message.risk_level,
            required_actions=[
                "Revisar justificación",
                "Confirmar disponibilidad presupuestaria",
                "Aprobar o rechazar la solicitud",
            ],
            findings=message.findings,
            approval_payload={
                "budget_owner": message.budget_owner,
                "amount_eur": message.amount_eur,
                "department_limit_eur": message.department_limit_eur,
                "justification": message.justification,
            },
            ready_for_real_action=False,
            created_at_utc=utc_now(),
        )
    )


@executor(id="procurement_review_pack")
async def procurement_review_pack(
    message: AssessedPurchase,
    ctx: WorkflowContext[Never, PurchaseWorkflowOutput],
) -> None:
    required_actions = ["Revisar proveedor y categoría de compra"]

    if message.vendor_status == VendorStatus.UNKNOWN:
        required_actions.append("Validar alta de proveedor")

    if message.security_review_required:
        required_actions.append("Solicitar revisión de seguridad")

    await ctx.yield_output(
        PurchaseWorkflowOutput(
            decision=DecisionRoute.PROCUREMENT_REVIEW,
            title="Revisión de compras requerida",
            message=(
                "La solicitud requiere revisión de compras por proveedor, "
                "categoría o posible revisión de seguridad."
            ),
            requester=message.requester,
            department=message.department,
            next_owner="procurement.review@contoso.com",
            amount_eur=message.amount_eur,
            vendor=message.vendor,
            vendor_status=message.vendor_status,
            category=message.category,
            risk_score=message.risk_score,
            risk_level=message.risk_level,
            required_actions=required_actions,
            findings=message.findings,
            approval_payload={
                "security_review_required": message.security_review_required,
                "vendor_status": message.vendor_status,
                "risk_score": message.risk_score,
            },
            ready_for_real_action=False,
            created_at_utc=utc_now(),
        )
    )


@executor(id="policy_rejected")
async def policy_rejected(
    message: AssessedPurchase,
    ctx: WorkflowContext[Never, PurchaseWorkflowOutput],
) -> None:
    await ctx.yield_output(
        PurchaseWorkflowOutput(
            decision=DecisionRoute.POLICY_REJECTED,
            title="Solicitud rechazada por política",
            message="La solicitud incumple una política que impide continuar por este flujo.",
            requester=message.requester,
            department=message.department,
            next_owner="procurement.policy@contoso.com",
            amount_eur=message.amount_eur,
            vendor=message.vendor,
            vendor_status=message.vendor_status,
            category=message.category,
            risk_score=message.risk_score,
            risk_level=message.risk_level,
            required_actions=[
                "Revisar política aplicable",
                "Crear solicitud excepcional si procede",
            ],
            findings=message.findings,
            ready_for_real_action=False,
            created_at_utc=utc_now(),
        )
    )


def build_purchase_case_workflow():
    workflow = (
        WorkflowBuilder(start_executor=normalize_purchase_request)
        .add_edge(normalize_purchase_request, enrich_purchase_context)
        .add_edge(enrich_purchase_context, validate_purchase_request)
        .add_edge(validate_purchase_request, assess_purchase_risk)
        .add_edge(
            assess_purchase_risk,
            request_more_data,
            condition=route_is(DecisionRoute.REQUEST_MORE_DATA),
        )
        .add_edge(
            assess_purchase_risk,
            auto_approve_purchase,
            condition=route_is(DecisionRoute.AUTO_APPROVE),
        )
        .add_edge(
            assess_purchase_risk,
            manager_approval_pack,
            condition=route_is(DecisionRoute.MANAGER_APPROVAL),
        )
        .add_edge(
            assess_purchase_risk,
            procurement_review_pack,
            condition=route_is(DecisionRoute.PROCUREMENT_REVIEW),
        )
        .add_edge(
            assess_purchase_risk,
            policy_rejected,
            condition=route_is(DecisionRoute.POLICY_REJECTED),
        )
        .build()
    )

    return workflow


async def run_case(name: str, request: PurchaseRequestInput) -> None:
    workflow = build_purchase_case_workflow()

    events = await workflow.run(request)
    outputs = events.get_outputs()

    print(f"\n--- CASO: {name} ---")

    for output in outputs:
        if isinstance(output, BaseModel):
            print(output.model_dump_json(indent=2))
        else:
            print(output)


async def main() -> None:
    await run_case(
        name="Compra simple aprobable",
        request=PurchaseRequestInput(
            description="Compra de curso de formación técnica para el equipo.",
            requester="ana@contoso.com",
            department="HR",
            amount_eur=850,
            vendor="Adatum Training",
            justification="Formación necesaria para el plan anual.",
        ),
    )

    await run_case(
        name="Compra cloud con revisión",
        request=PurchaseRequestInput(
            description="Nuevo servicio Azure cloud con integración por API y datos de cliente.",
            requester="luis@contoso.com",
            department="IT",
            amount_eur=4200,
            vendor="Microsoft",
            justification="Necesario para el proyecto de automatización.",
        ),
    )

    await run_case(
        name="Compra sin datos suficientes",
        request=PurchaseRequestInput(
            description="Necesito una licencia software para el equipo.",
            requester="marta@contoso.com",
            department="Sales",
            amount_eur=None,
            vendor=None,
            justification=None,
        ),
    )

    await run_case(
        name="Proveedor bloqueado",
        request=PurchaseRequestInput(
            description="Servicio de consultoría para migración de datos.",
            requester="carlos@contoso.com",
            department="Finance",
            amount_eur=12000,
            vendor="risky-supplies",
            justification="Proyecto urgente.",
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())