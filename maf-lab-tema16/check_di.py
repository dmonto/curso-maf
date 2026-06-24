from __future__ import annotations

import json

from src.clean_arch.application.use_cases import ReportIncidentCommand
from src.di.container import build_app_container


def main() -> None:
    container = build_app_container()

    scope = container.create_scope(
        user_id="usuario.demo@empresa.com",
        session_id="session-demo",
    )

    use_case = scope.report_and_classify_incident_use_case()

    result = use_case.execute(
        ReportIncidentCommand(
            service="erp",
            summary="El ERP no permite emitir facturas desde el módulo financiero.",
            affected_users=35,
            business_impact="Bloqueo de facturación a clientes.",
        )
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()