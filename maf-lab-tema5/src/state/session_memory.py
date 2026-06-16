from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Literal


PasoProbado = Literal[
    "reiniciar_cliente_vpn",
    "validar_mfa",
    "probar_otra_red",
    "reinstalar_cliente",
]


@dataclass
class SupportSessionMemory:
    servicio: str | None = None
    ubicacion: str | None = None
    sistema_operativo: str | None = None
    usuarios_afectados: int | None = None
    prioridad: str | None = None
    pasos_probados: list[str] = field(default_factory=list)
    pendiente_confirmacion: str | None = None
    ultima_accion_recomendada: str | None = None

    def update_from_user_text(self, text: str) -> None:
        """
        Actualización determinista y controlada de memoria de sesión.

        En producción esta extracción podría combinar reglas, formularios,
        validadores, tools o un extractor estructurado. Para el laboratorio
        usamos reglas simples para que el comportamiento sea visible.
        """
        normalized = text.lower()

        if "vpn" in normalized:
            self.servicio = "vpn"

        if "correo" in normalized or "email" in normalized or "outlook" in normalized:
            self.servicio = "correo"

        if "teams" in normalized:
            self.servicio = "teams"

        if "erp" in normalized:
            self.servicio = "erp"

        if "desde casa" in normalized or "remoto" in normalized:
            self.ubicacion = "remoto"

        if "oficina" in normalized:
            self.ubicacion = "oficina"

        if "windows 11" in normalized:
            self.sistema_operativo = "Windows 11"
        elif "windows 10" in normalized:
            self.sistema_operativo = "Windows 10"
        elif "mac" in normalized or "macos" in normalized:
            self.sistema_operativo = "macOS"
        elif "linux" in normalized:
            self.sistema_operativo = "Linux"

        if "solo me pasa a mí" in normalized or "solo a mí" in normalized:
            self.usuarios_afectados = 1

        if "varios usuarios" in normalized or "más usuarios" in normalized:
            self.usuarios_afectados = 5

        priority_match = re.search(r"\bp([1-4])\b", normalized)
        if priority_match:
            self.prioridad = f"p{priority_match.group(1)}"

        if "validado mfa" in normalized or "validar mfa" in normalized:
            self._add_step("validar_mfa")

        if "otra red" in normalized:
            self._add_step("probar_otra_red")

        if "reiniciado" in normalized or "reiniciar" in normalized:
            self._add_step("reiniciar_cliente_vpn")

        if "reinstalado" in normalized or "reinstalar" in normalized:
            self._add_step("reinstalar_cliente")

        if "prepara" in normalized and "ticket" in normalized:
            self.pendiente_confirmacion = "preparar_borrador_ticket"

    def _add_step(self, step: str) -> None:
        if step not in self.pasos_probados:
            self.pasos_probados.append(step)

    def missing_fields(self) -> list[str]:
        missing: list[str] = []

        if not self.servicio:
            missing.append("servicio")
        if not self.ubicacion:
            missing.append("ubicacion")
        if not self.sistema_operativo:
            missing.append("sistema_operativo")
        if self.usuarios_afectados is None:
            missing.append("usuarios_afectados")

        return missing

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_model_context(self) -> str:
        """
        Contexto compacto para inyectar en el turno actual.
        No contiene todo el historial. Solo contiene memoria operativa.
        """
        return json.dumps(
            {
                "memoria_sesion_soporte": self.to_dict(),
                "datos_pendientes": self.missing_fields(),
            },
            ensure_ascii=False,
            indent=2,
        )