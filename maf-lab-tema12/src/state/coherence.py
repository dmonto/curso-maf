from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


Severity = Literal["info", "warning", "error", "blocking"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(frozen=True)
class CoherenceIssue:
    code: str
    severity: Severity
    message: str
    field: str | None = None
    recommendation: str | None = None


@dataclass
class CoherenceReport:
    issues: list[CoherenceIssue] = field(default_factory=list)

    def add(
        self,
        code: str,
        severity: Severity,
        message: str,
        field: str | None = None,
        recommendation: str | None = None,
    ) -> None:
        self.issues.append(
            CoherenceIssue(
                code=code,
                severity=severity,
                message=message,
                field=field,
                recommendation=recommendation,
            )
        )

    @property
    def has_blocking(self) -> bool:
        return any(issue.severity == "blocking" for issue in self.issues)

    @property
    def has_errors(self) -> bool:
        return any(issue.severity in {"error", "blocking"} for issue in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(issue.severity == "warning" for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status(),
            "issues": [asdict(issue) for issue in self.issues],
        }

    def status(self) -> str:
        if self.has_blocking:
            return "blocking"
        if self.has_errors:
            return "error"
        if self.has_warnings:
            return "warning"
        return "ok"

    def to_prompt_block(self) -> str:
        if not self.issues:
            return "No se han detectado problemas de coherencia."

        lines: list[str] = []

        for issue in self.issues:
            lines.append(
                f"- [{issue.severity.upper()}] {issue.code}: {issue.message}"
            )

            if issue.recommendation:
                lines.append(f"  Recomendación: {issue.recommendation}")

        return "\n".join(lines)


class CoherenceController:
    """
    Controla coherencia entre:
    - mensaje actual;
    - memoria estructurada;
    - contexto enriquecido;
    - estado distribuido;
    - políticas.

    La lógica crítica se mantiene en código, no solo en el prompt.
    """

    def __init__(
        self,
        max_external_status_age_minutes: int = 60,
    ) -> None:
        self.max_external_status_age_minutes = max_external_status_age_minutes

    def validate(
        self,
        user_text: str,
        memory: dict[str, Any],
        enriched_context: dict[str, Any] | None,
        distributed_metadata: dict[str, Any] | None,
    ) -> CoherenceReport:
        report = CoherenceReport()

        normalized_text = user_text.lower()
        enriched_context = enriched_context or {}
        distributed_metadata = distributed_metadata or {}

        self._check_closed_case(
            report=report,
            normalized_text=normalized_text,
            distributed_metadata=distributed_metadata,
        )

        self._check_service_consistency(
            report=report,
            memory=memory,
            enriched_context=enriched_context,
        )

        self._check_ticket_readiness(
            report=report,
            normalized_text=normalized_text,
            memory=memory,
            enriched_context=enriched_context,
        )

        self._check_priority_consistency(
            report=report,
            memory=memory,
            enriched_context=enriched_context,
        )

        self._check_policy_consistency(
            report=report,
            normalized_text=normalized_text,
            enriched_context=enriched_context,
        )

        self._check_external_status_freshness(
            report=report,
            enriched_context=enriched_context,
        )

        if not report.issues:
            report.add(
                code="coherence_ok",
                severity="info",
                message="El contexto es coherente para continuar.",
            )

        return report

    def _check_closed_case(
        self,
        report: CoherenceReport,
        normalized_text: str,
        distributed_metadata: dict[str, Any],
    ) -> None:
        status = distributed_metadata.get("status")

        if status != "closed":
            return

        wants_continue = any(
            token in normalized_text
            for token in [
                "sigo",
                "continúo",
                "continuo",
                "prepara",
                "ticket",
                "actualiza",
                "haz",
            ]
        )

        if wants_continue:
            report.add(
                code="case_closed",
                severity="blocking",
                field="metadata.status",
                message="El caso está cerrado y el usuario pide continuar o actuar.",
                recommendation="Solicita confirmación para reabrir la sesión antes de continuar.",
            )

    def _check_service_consistency(
        self,
        report: CoherenceReport,
        memory: dict[str, Any],
        enriched_context: dict[str, Any],
    ) -> None:
        memory_service = memory.get("servicio")

        service = enriched_context.get("service") or {}
        enriched_service = service.get("key")

        if memory_service and enriched_service and memory_service != enriched_service:
            report.add(
                code="service_conflict",
                severity="blocking",
                field="servicio",
                message=(
                    f"La memoria indica servicio '{memory_service}', "
                    f"pero el contexto enriquecido indica '{enriched_service}'."
                ),
                recommendation="Pide aclaración antes de preparar acciones o tickets.",
            )

    def _check_ticket_readiness(
        self,
        report: CoherenceReport,
        normalized_text: str,
        memory: dict[str, Any],
        enriched_context: dict[str, Any],
    ) -> None:
        wants_ticket = "ticket" in normalized_text or "incidencia" in normalized_text

        if not wants_ticket:
            return

        memory_service = memory.get("servicio")
        enriched_service = (enriched_context.get("service") or {}).get("key")

        if not memory_service and not enriched_service:
            report.add(
                code="missing_service_for_ticket",
                severity="blocking",
                field="servicio",
                message="El usuario pide preparar una incidencia, pero no hay servicio identificado.",
                recommendation="Pregunta qué servicio está afectado.",
            )

        if memory.get("usuarios_afectados") is None:
            report.add(
                code="missing_impact_for_ticket",
                severity="warning",
                field="usuarios_afectados",
                message="No se conoce cuántos usuarios están afectados.",
                recommendation="Pregunta si afecta solo al usuario o a más personas.",
            )

        if not memory.get("sistema_operativo"):
            report.add(
                code="missing_os_for_ticket",
                severity="warning",
                field="sistema_operativo",
                message="No se conoce el sistema operativo.",
                recommendation="Pregunta el sistema operativo si el diagnóstico depende del cliente local.",
            )

    def _check_priority_consistency(
        self,
        report: CoherenceReport,
        memory: dict[str, Any],
        enriched_context: dict[str, Any],
    ) -> None:
        priority = memory.get("prioridad")

        service = enriched_context.get("service") or {}
        criticality = service.get("criticidad")

        if criticality in {"critica", "crítica"} and priority == "p4":
            report.add(
                code="priority_too_low_for_critical_service",
                severity="warning",
                field="prioridad",
                message="El servicio es crítico, pero la prioridad registrada es p4.",
                recommendation="Revisar prioridad sugerida antes de preparar el borrador.",
            )

    def _check_policy_consistency(
        self,
        report: CoherenceReport,
        normalized_text: str,
        enriched_context: dict[str, Any],
    ) -> None:
        policy = enriched_context.get("policy") or {}

        wants_real_creation = any(
            token in normalized_text
            for token in [
                "crea el ticket",
                "abre el ticket",
                "registra el ticket",
                "envía el ticket",
                "lanza la incidencia",
            ]
        )

        can_create_real_ticket = bool(policy.get("puede_crear_ticket_real", False))

        if wants_real_creation and not can_create_real_ticket:
            report.add(
                code="real_action_not_allowed",
                severity="blocking",
                field="policy.puede_crear_ticket_real",
                message="El usuario pide una acción real, pero la política no permite crear tickets reales.",
                recommendation="Ofrece preparar un borrador y solicita confirmación o intervención autorizada.",
            )

    def _check_external_status_freshness(
        self,
        report: CoherenceReport,
        enriched_context: dict[str, Any],
    ) -> None:
        external_status = enriched_context.get("external_status")

        if not external_status:
            return

        updated = parse_utc(external_status.get("updated_utc"))

        if not updated:
            report.add(
                code="external_status_without_timestamp",
                severity="warning",
                field="external_status.updated_utc",
                message="El estado externo no tiene timestamp válido.",
                recommendation="No lo trates como dato actual sin validación adicional.",
            )
            return

        age_minutes = (utc_now() - updated).total_seconds() / 60

        if age_minutes > self.max_external_status_age_minutes:
            report.add(
                code="external_status_stale",
                severity="warning",
                field="external_status.updated_utc",
                message=(
                    f"El estado externo tiene {age_minutes:.1f} minutos de antigüedad."
                ),
                recommendation="Refresca el estado externo antes de tomar decisiones operativas.",
            )


def build_blocking_response(report: CoherenceReport) -> str:
    """
    Respuesta segura cuando no conviene llamar al agente para actuar.
    """
    blocking_issues = [
        issue for issue in report.issues if issue.severity == "blocking"
    ]

    lines = [
        "Antes de continuar necesito resolver una incoherencia del contexto:"
    ]

    for issue in blocking_issues:
        lines.append(f"- {issue.message}")

        if issue.recommendation:
            lines.append(f"  {issue.recommendation}")

    return "\n".join(lines)