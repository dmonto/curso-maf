from agent_framework.devui import serve

from src.agents.support_agent import build_support_agent


agent = build_support_agent()

serve(
    entities=[agent],
    auto_open=True,
    auth_enabled=False,
    mode="developer",
    instrumentation_enabled=True,    
)