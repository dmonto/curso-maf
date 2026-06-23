from __future__ import annotations

from src.identity.context import IdentityContext


DEMO_IDENTITIES = {
    "ana": IdentityContext(
        user_id="ana@contoso.com",
        tenant_id="contoso",
        display_name="Ana Soporte",
        groups=("support_l1",),
        department="it",
        auth_method="demo_entra_id",
        session_id="session-ana-001",
    ),
    "bruno": IdentityContext(
        user_id="bruno@contoso.com",
        tenant_id="contoso",
        display_name="Bruno Administrador",
        groups=("support_admin", "identity_readers"),
        department="it",
        auth_method="demo_entra_id",
        session_id="session-bruno-001",
    ),
    "carla": IdentityContext(
        user_id="carla@contoso.com",
        tenant_id="contoso",
        display_name="Carla Finanzas",
        groups=("finance",),
        department="finance",
        auth_method="demo_entra_id",
        session_id="session-carla-001",
    ),
}


def get_demo_identity(alias: str) -> IdentityContext:
    key = alias.strip().lower()

    if key not in DEMO_IDENTITIES:
        available = ", ".join(DEMO_IDENTITIES)
        raise ValueError(f"Identidad demo no reconocida: {alias}. Opciones: {available}")

    return DEMO_IDENTITIES[key]