from src.tools.support_tools import (
    calculate_sla_deadline,
    classify_incident_risk_tool,
    draft_support_ticket,
    normalize_service,
)


TOOLS_SUPPORT_L1 = [
    normalize_service,
    calculate_sla_deadline,
    classify_incident_risk_tool,
    draft_support_ticket,
]