from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class IdentityContext:
    """
    Representa identidad confiable ya resuelta por el backend.

    No debe construirse a partir de texto libre generado por el usuario.
    """

    user_id: str
    tenant_id: str
    display_name: str
    groups: tuple[str, ...]
    department: str
    auth_method: str
    session_id: str
    authenticated_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_agent_summary(self) -> str:
        """
        Devuelve una versión segura para incluir en instrucciones del agente.

        No incluimos tokens, secretos ni claims completos.
        """
        return (
            f"Usuario autenticado: {self.display_name} ({self.user_id})\n"
            f"Tenant: {self.tenant_id}\n"
            f"Departamento: {self.department}\n"
            f"Grupos: {', '.join(self.groups) if self.groups else 'sin grupos'}\n"
            f"Método de autenticación: {self.auth_method}\n"
            f"Session ID: {self.session_id}"
        )

    def to_audit_record(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "display_name": self.display_name,
            "groups": list(self.groups),
            "department": self.department,
            "auth_method": self.auth_method,
            "session_id": self.session_id,
            "authenticated_at_utc": self.authenticated_at_utc,
        }