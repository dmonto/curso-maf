from agent_framework.devui import serve

from src.agents.multiagent.coordinator_agent import build_support_coordinator


agent = build_support_coordinator()

serve(
    entities=[agent],
    auto_open=True,
    auth_enabled=False
)