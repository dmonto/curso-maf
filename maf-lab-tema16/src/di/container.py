from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

from src.clean_arch.application.use_cases import ReportAndClassifyIncidentUseCase
from src.clean_arch.domain.policies import IncidentPolicy
from src.clean_arch.infrastructure.jsonl_events import JsonlEventPublisher
from src.clean_arch.infrastructure.jsonl_repositories import (
    JsonlClassificationRepository,
    JsonlIncidentRepository,
)
from src.clean_arch.infrastructure.rule_based_classifier import RuleBasedIncidentClassifier
from src.di.settings import DependencySettings, load_dependency_settings


class InMemoryEventPublisher:
    """
    Adaptador útil para tests.
    Implementa el mismo contrato que JsonlEventPublisher, pero guarda eventos en memoria.
    """

    def __init__(self) -> None:
        self.events: list[dict] = []

    def publish(self, event_type: str, payload: dict, correlation_id: str) -> None:
        self.events.append(
            {
                "event_type": event_type,
                "payload": payload,
                "correlation_id": correlation_id,
            }
        )


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    user_id: str | None = None
    session_id: str | None = None


class AppContainer:
    """
    Contenedor de aplicación.

    Responsabilidades:
    - Mantener settings.
    - Construir singletons.
    - Permitir overrides para tests.
    - Crear scopes por petición.
    """

    def __init__(
        self,
        settings: DependencySettings | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> None:
        self.settings = settings or load_dependency_settings()
        self._singletons: dict[str, Any] = {}
        self._overrides = overrides or {}

    def with_overrides(self, **overrides: Any) -> "AppContainer":
        merged = {
            **self._overrides,
            **overrides,
        }

        return AppContainer(
            settings=self.settings,
            overrides=merged,
        )

    def create_scope(
        self,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> "RequestContainer":
        return RequestContainer(
            app_container=self,
            context=RequestContext(
                request_id=f"req-{uuid4().hex[:10]}",
                user_id=user_id,
                session_id=session_id,
            ),
        )

    def _resolve_singleton(
        self,
        name: str,
        factory: Callable[[], Any],
    ) -> Any:
        if name in self._overrides:
            override = self._overrides[name]
            return override() if callable(override) else override

        if name not in self._singletons:
            self._singletons[name] = factory()

        return self._singletons[name]

    def incident_repository(self):
        return self._resolve_singleton(
            "incident_repository",
            lambda: JsonlIncidentRepository(self.settings.incidents_path),
        )

    def classification_repository(self):
        return self._resolve_singleton(
            "classification_repository",
            lambda: JsonlClassificationRepository(self.settings.classifications_path),
        )

    def event_publisher(self):
        def factory():
            if self.settings.event_publisher_mode == "jsonl":
                return JsonlEventPublisher(self.settings.events_path)

            if self.settings.event_publisher_mode == "memory":
                return InMemoryEventPublisher()

            raise ValueError(
                f"EVENT_PUBLISHER_MODE no soportado: {self.settings.event_publisher_mode}"
            )

        return self._resolve_singleton("event_publisher", factory)

    def incident_classifier(self):
        def factory():
            if self.settings.incident_classifier_mode == "rules":
                return RuleBasedIncidentClassifier()

            raise ValueError(
                "INCIDENT_CLASSIFIER_MODE no soportado: "
                f"{self.settings.incident_classifier_mode}"
            )

        return self._resolve_singleton("incident_classifier", factory)

    def incident_policy(self):
        return self._resolve_singleton(
            "incident_policy",
            IncidentPolicy,
        )


@dataclass(frozen=True)
class RequestContainer:
    """
    Scope por petición.

    Aquí colocaríamos dependencias que cambian por request:
    - usuario actual,
    - session_id,
    - correlation_id externo,
    - permisos efectivos,
    - trazas de una ejecución.
    """

    app_container: AppContainer
    context: RequestContext

    def report_and_classify_incident_use_case(self) -> ReportAndClassifyIncidentUseCase:
        return ReportAndClassifyIncidentUseCase(
            incident_repository=self.app_container.incident_repository(),
            classification_repository=self.app_container.classification_repository(),
            classifier=self.app_container.incident_classifier(),
            event_publisher=self.app_container.event_publisher(),
            policy=self.app_container.incident_policy(),
        )


def build_app_container() -> AppContainer:
    return AppContainer()