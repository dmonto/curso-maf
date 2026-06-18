from agent_framework.devui import serve

from src.workflows.incident_observability_workflow import (
    build_incident_observability_workflow,
    configure_observability,
)

configure_observability()

workflow = build_incident_observability_workflow()

serve(
    entities=[workflow],
    auto_open=True,
    instrumentation_enabled=True,
    auth_enabled=False
)