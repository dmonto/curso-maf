from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class UserContext:
    user_id: str
    display_name: str
    area: str
    ubicacion: str
    idioma: str
    perfil_soporte: str


@dataclass(frozen=True)
class ServiceContext:
    key: str
    nombre_visible: str
    criticidad: str
    owner: str
    sla_default: str
    descripcion: str


@dataclass(frozen=True)
class PolicyContext:
    puede_crear_ticket_real: bool
    puede_preparar_borrador: bool
    requiere_confirmacion_para_envio: bool
    puede_mostrar_datos_personales: bool
    max_tool_calls_recomendadas: int


@dataclass(frozen=True)
class ExternalStatusContext:
    servicio: str
    estado: str
    incidencia_global: bool
    detalle: str
    updated_utc: str


@dataclass(frozen=True)
class EnrichedContext:
    user: UserContext
    service: ServiceContext | None
    policy: PolicyContext
    external_status: ExternalStatusContext | None
    enrichment_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "user": asdict(self.user),
            "service": asdict(self.service) if self.service else None,
            "policy": asdict(self.policy),
            "external_status": (
                asdict(self.external_status)
                if self.external_status
                else None
            ),
            "enrichment_notes": self.enrichment_notes,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ContextEnricher:
    """
    Enriquecedor contextual controlado.

    En producción, estas fuentes podrían venir de:
    - Microsoft Graph;
    - base de datos corporativa;
    - sistema ITSM;
    - Azure Monitor;
    - Azure App Configuration;
    - Azure Table Storage;
    - APIs internas.

    Para el laboratorio usamos catálogos locales deterministas.
    """

    def __init__(self) -> None:
        self._users = {
            "usuario-demo": UserContext(
                user_id="usuario-demo",
                display_name="Usuario Demo",
                area="Finanzas",
                ubicacion="remoto",
                idioma="es",
                perfil_soporte="empleado_interno",
            ),
            "admin-demo": UserContext(
                user_id="admin-demo",
                display_name="Admin Demo",
                area="Sistemas",
                ubicacion="oficina",
                idioma="es",
                perfil_soporte="it_admin",
            ),
        }

        self._services = {
            "vpn": ServiceContext(
                key="vpn",
                nombre_visible="VPN corporativa",
                criticidad="alta",
                owner="equipo-redes",
                sla_default="p2",
                descripcion="Acceso remoto seguro a la red corporativa.",
            ),
            "correo": ServiceContext(
                key="correo",
                nombre_visible="Correo corporativo",
                criticidad="alta",
                owner="equipo-m365",
                sla_default="p2",
                descripcion="Servicio de correo y calendario corporativo.",
            ),
            "teams": ServiceContext(
                key="teams",
                nombre_visible="Microsoft Teams",
                criticidad="media",
                owner="equipo-colaboracion",
                sla_default="p3",
                descripcion="Mensajería, reuniones y colaboración interna.",
            ),
            "erp": ServiceContext(
                key="erp",
                nombre_visible="ERP financiero",
                criticidad="critica",
                owner="equipo-aplicaciones",
                sla_default="p1",
                descripcion="Sistema financiero y operativo principal.",
            ),
        }

        self._external_status = {
            "vpn": ExternalStatusContext(
                servicio="vpn",
                estado="degradado",
                incidencia_global=True,
                detalle="Latencia elevada en conexiones remotas desde algunos operadores.",
                updated_utc=utc_now(),
            ),
            "correo": ExternalStatusContext(
                servicio="correo",
                estado="operativo",
                incidencia_global=False,
                detalle="Sin incidencias conocidas.",
                updated_utc=utc_now(),
            ),
            "teams": ExternalStatusContext(
                servicio="teams",
                estado="operativo",
                incidencia_global=False,
                detalle="Sin incidencias conocidas.",
                updated_utc=utc_now(),
            ),
            "erp": ExternalStatusContext(
                servicio="erp",
                estado="operativo",
                incidencia_global=False,
                detalle="Sin incidencias conocidas.",
                updated_utc=utc_now(),
            ),
        }

    def enrich(
        self,
        user_id: str,
        user_text: str,
        memory_service: str | None,
    ) -> EnrichedContext:
        notes: list[str] = []

        user = self._resolve_user(user_id)
        notes.append(f"Usuario resuelto: {user.user_id}")

        service_key = self._resolve_service_key(
            user_text=user_text,
            memory_service=memory_service,
        )

        service = self._services.get(service_key) if service_key else None

        if service:
            notes.append(f"Servicio enriquecido: {service.key}")
        else:
            notes.append("No se ha podido resolver un servicio del catálogo.")

        policy = self._resolve_policy(user=user, service=service)

        external_status = (
            self._external_status.get(service.key)
            if service
            else None
        )

        if external_status:
            notes.append(
                f"Estado externo añadido: {external_status.estado}, "
                f"incidencia_global={external_status.incidencia_global}"
            )

        return EnrichedContext(
            user=user,
            service=service,
            policy=policy,
            external_status=external_status,
            enrichment_notes=notes,
        )

    def _resolve_user(self, user_id: str) -> UserContext:
        if user_id in self._users:
            return self._users[user_id]

        return UserContext(
            user_id=user_id,
            display_name="Usuario no catalogado",
            area="desconocida",
            ubicacion="desconocida",
            idioma="es",
            perfil_soporte="empleado_interno",
        )

    def _resolve_service_key(
        self,
        user_text: str,
        memory_service: str | None,
    ) -> str | None:
        normalized = user_text.lower()

        for key in self._services:
            if key in normalized:
                return key

        if "email" in normalized or "outlook" in normalized:
            return "correo"

        if memory_service:
            return memory_service

        return None

    def _resolve_policy(
        self,
        user: UserContext,
        service: ServiceContext | None,
    ) -> PolicyContext:
        is_admin = user.perfil_soporte == "it_admin"

        if service and service.criticidad in {"alta", "critica"}:
            return PolicyContext(
                puede_crear_ticket_real=is_admin,
                puede_preparar_borrador=True,
                requiere_confirmacion_para_envio=True,
                puede_mostrar_datos_personales=False,
                max_tool_calls_recomendadas=4,
            )

        return PolicyContext(
            puede_crear_ticket_real=is_admin,
            puede_preparar_borrador=True,
            requiere_confirmacion_para_envio=True,
            puede_mostrar_datos_personales=False,
            max_tool_calls_recomendadas=3,
        )