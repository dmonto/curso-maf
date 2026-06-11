import asyncio
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Annotated, Literal, Protocol

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential
from pydantic import Field


# ---------------------------------------------------------------------
# 1. Configuración
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class AppConfig:
    app_env: str
    project_endpoint: str
    model: str
    max_ticket_description_chars: int = 500
    allow_real_ticket_creation: bool = False


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")
    return value


def load_config() -> AppConfig:
    return AppConfig(
        app_env=os.getenv("APP_ENV", "dev"),
        project_endpoint=require_env("AZURE_OPENAI_ENDPOINT"),
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_CHAT", "gpt-4o"),
        allow_real_ticket_creation=False,
    )


# ---------------------------------------------------------------------
# 2. Contratos de dependencias
# ---------------------------------------------------------------------

class IncidentRepository(Protocol):
    def get_known_incident(self, service: str) -> dict:
        ...

    def prepare_ticket_draft(
        self,
        service: str,
        description: str,
        priority: str,
        users_affected: int,
    ) -> dict:
        ...


class AuditLogger(Protocol):
    def info(self, event_name: str, **details) -> None:
        ...

    def warning(self, event_name: str, **details) -> None:
        ...


# ---------------------------------------------------------------------
# 3. Implementaciones concretas
# ---------------------------------------------------------------------

class InMemoryIncidentRepository:
    """
    Implementación de laboratorio.
    En producción podría sustituirse por ServiceNow, Jira, Azure DevOps,
    una API interna o una base de datos.
    """

    def __init__(self) -> None:
        self.known_incidents = {
            "vpn": {
                "has_incident": True,
                "severity": "media",
                "details": (
                    "Hay incidencias intermitentes de VPN para usuarios remotos. "
                    "Revisar cliente VPN, MFA y conectividad."
                ),
            },
            "correo": {
                "has_incident": False,
                "severity": "baja",
                "details": "No hay incidencia global de correo registrada.",
            },
            "teams": {
                "has_incident": True,
                "severity": "media",
                "details": "Hay degradación parcial en reuniones de Teams.",
            },
            "erp": {
                "has_incident": False,
                "severity": "baja",
                "details": "No hay incidencia general registrada para ERP.",
            },
        }

    def get_known_incident(self, service: str) -> dict:
        return self.known_incidents.get(
            service,
            {
                "has_incident": False,
                "severity": "desconocida",
                "details": "Servicio no reconocido.",
            },
        )

    def prepare_ticket_draft(
        self,
        service: str,
        description: str,
        priority: str,
        users_affected: int,
    ) -> dict:
        return {
            "ticket_id": f"DRAFT-{uuid.uuid4().hex[:8].upper()}",
            "service": service,
            "description": description,
            "priority": priority,
            "users_affected": users_affected,
            "status": "draft_pending_confirmation",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }


class ConsoleAuditLogger:
    def info(self, event_name: str, **details) -> None:
        print(
            "[audit:info]",
            event_name,
            json.dumps(details, ensure_ascii=False),
        )

    def warning(self, event_name: str, **details) -> None:
        print(
            "[audit:warning]",
            event_name,
            json.dumps(details, ensure_ascii=False),
        )


# ---------------------------------------------------------------------
# 4. Política de negocio inyectable
# ---------------------------------------------------------------------

@dataclass
class SupportPolicy:
    max_ticket_description_chars: int
    allow_real_ticket_creation: bool = False

    def classify_priority(self, impact: str, users_affected: int) -> dict:
        if impact == "alto" or users_affected > 10:
            return {
                "priority": "alta",
                "requires_escalation": True,
                "reason": "Impacto alto o más de 10 usuarios afectados.",
            }

        if impact == "medio" or users_affected > 1:
            return {
                "priority": "media",
                "requires_escalation": False,
                "reason": "Impacto medio o más de un usuario afectado.",
            }

        return {
            "priority": "baja",
            "requires_escalation": False,
            "reason": "Impacto bajo y un único usuario afectado.",
        }

    def validate_ticket_draft(
        self,
        service: str,
        description: str,
        priority: str,
        users_affected: int,
    ) -> None:
        if service not in {"vpn", "correo", "teams", "erp"}:
            raise ValueError("Servicio no permitido para preparación de ticket.")

        if not description or len(description.strip()) < 10:
            raise ValueError("La descripción del ticket es demasiado corta.")

        if len(description) > self.max_ticket_description_chars:
            raise ValueError("La descripción supera la longitud máxima permitida.")

        if priority not in {"baja", "media", "alta"}:
            raise ValueError("Prioridad no válida.")

        if users_affected < 1:
            raise ValueError("El número de usuarios afectados debe ser al menos 1.")


# ---------------------------------------------------------------------
# 5. Contenedor simple de dependencias
# ---------------------------------------------------------------------

@dataclass
class AppContainer:
    config: AppConfig
    incident_repository: IncidentRepository
    audit_logger: AuditLogger
    support_policy: SupportPolicy


def build_container() -> AppContainer:
    config = load_config()

    return AppContainer(
        config=config,
        incident_repository=InMemoryIncidentRepository(),
        audit_logger=ConsoleAuditLogger(),
        support_policy=SupportPolicy(
            max_ticket_description_chars=config.max_ticket_description_chars,
            allow_real_ticket_creation=config.allow_real_ticket_creation,
        ),
    )


# ---------------------------------------------------------------------
# 6. Factory de tools con dependencias inyectadas
# ---------------------------------------------------------------------

def build_support_tools(container: AppContainer):
    repository = container.incident_repository
    audit = container.audit_logger
    policy = container.support_policy

    @tool(
        name="consultar_incidencia_conocida",
        description=(
            "Consulta si existe una incidencia conocida para un servicio corporativo. "
            "Úsala cuando el usuario mencione VPN, correo, Teams o ERP."
        ),
        approval_mode="never_require",
    )
    def consultar_incidencia_conocida(
        service: Annotated[
            Literal["vpn", "correo", "teams", "erp"],
            Field(description="Servicio corporativo afectado."),
        ],
    ) -> str:
        audit.info("known_incident_requested", service=service)

        incident = repository.get_known_incident(service)

        audit.info(
            "known_incident_returned",
            service=service,
            has_incident=incident["has_incident"],
            severity=incident["severity"],
        )

        return json.dumps(incident, ensure_ascii=False)

    @tool(
        name="clasificar_prioridad",
        description=(
            "Clasifica la prioridad de una incidencia según impacto y número de usuarios afectados. "
            "No inventes usuarios afectados: si falta el dato, pide aclaración."
        ),
        approval_mode="never_require",
    )
    def clasificar_prioridad(
        impact: Annotated[
            Literal["bajo", "medio", "alto"],
            Field(description="Impacto funcional indicado por el usuario."),
        ],
        users_affected: Annotated[
            int,
            Field(description="Número de usuarios afectados.", ge=1),
        ],
    ) -> str:
        audit.info(
            "priority_classification_requested",
            impact=impact,
            users_affected=users_affected,
        )

        result = policy.classify_priority(
            impact=impact,
            users_affected=users_affected,
        )

        audit.info("priority_classification_returned", **result)

        return json.dumps(result, ensure_ascii=False)

    @tool(
        name="preparar_borrador_ticket",
        description=(
            "Prepara un borrador de ticket de soporte. "
            "No crea tickets reales. "
            "Debe usarse solo cuando ya existen servicio, descripción, prioridad y usuarios afectados."
        ),
        approval_mode="never_require",
    )
    def preparar_borrador_ticket(
        service: Annotated[
            Literal["vpn", "correo", "teams", "erp"],
            Field(description="Servicio afectado."),
        ],
        description: Annotated[
            str,
            Field(description="Resumen claro de la incidencia.", min_length=10),
        ],
        priority: Annotated[
            Literal["baja", "media", "alta"],
            Field(description="Prioridad clasificada."),
        ],
        users_affected: Annotated[
            int,
            Field(description="Número de usuarios afectados.", ge=1),
        ],
    ) -> str:
        audit.info(
            "ticket_draft_requested",
            service=service,
            priority=priority,
            users_affected=users_affected,
        )

        policy.validate_ticket_draft(
            service=service,
            description=description,
            priority=priority,
            users_affected=users_affected,
        )

        draft = repository.prepare_ticket_draft(
            service=service,
            description=description,
            priority=priority,
            users_affected=users_affected,
        )

        audit.info(
            "ticket_draft_created",
            ticket_id=draft["ticket_id"],
            service=service,
            priority=priority,
        )

        return json.dumps(draft, ensure_ascii=False)

    return [
        consultar_incidencia_conocida,
        clasificar_prioridad,
        preparar_borrador_ticket,
    ]


# ---------------------------------------------------------------------
# 7. Construcción del agente con dependencias externas
# ---------------------------------------------------------------------

def build_agent(container: AppContainer) -> Agent:
    config = container.config

    client = FoundryChatClient(
        project_endpoint=config.project_endpoint,
        model=config.model,
        credential=AzureCliCredential(),
    )

    tools = build_support_tools(container)

    return Agent(
        client=client,
        name="AgenteSoporteDI",
        instructions=(
            "Eres un agente de soporte técnico de nivel 1. "
            "Usa las tools disponibles para consultar incidencias conocidas, clasificar prioridad "
            "y preparar borradores de ticket. "
            "No puedes crear tickets reales. "
            "No inventes datos operativos. "
            "Si falta servicio, impacto o número de usuarios afectados, pide solo ese dato. "
            "Antes de preparar un borrador, asegúrate de tener servicio, descripción, prioridad "
            "y usuarios afectados. "
            "Responde de forma breve, profesional y orientada a la siguiente acción."
        ),
        tools=tools,
    )


# ---------------------------------------------------------------------
# 8. Ejecución de demo
# ---------------------------------------------------------------------

async def main() -> None:
    container = build_container()

    container.audit_logger.info(
        "application_started",
        app_env=container.config.app_env,
        model=container.config.model,
    )

    agent = build_agent(container)
    session = agent.create_session()

    demo_messages = [
        "No puedo acceder a la VPN desde casa. ¿Hay alguna incidencia conocida?",
        "Solo me pasa a mí y el impacto es bajo.",
        "Prepara un borrador de ticket con prioridad baja.",
    ]

    for message in demo_messages:
        print("\nUsuario>")
        print(message)

        result = await agent.run(message, session=session)

        print("\nAgente>")
        print(result)
        print("-" * 80)

    container.audit_logger.info("application_finished")


if __name__ == "__main__":
    asyncio.run(main())