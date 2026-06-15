import logging

from agent_framework.devui import serve

from src.agents.support_agent import build_support_agent
from src.observability.context import set_run_context
from src.observability.events import log_event
from src.observability.logging_config import configure_json_logging


logger = logging.getLogger("maf_lab.devui")


configure_json_logging(logging.INFO)

agent_name = "maf_tools_agent"

set_run_context(
    session_id="devui-local",
    agent_name=agent_name,
)

log_event(
    logger,
    logging.INFO,
    "devui.started",
    "Arranca DevUI para agente local.",
    host="127.0.0.1",
    port=8080,
)

agent = build_support_agent()

serve(
    entities=[agent],
    port=8080,
    host="127.0.0.1",
    auto_open=True,
    mode="developer",
    instrumentation_enabled=True,
)