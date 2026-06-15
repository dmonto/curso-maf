from src.models.factory import create_chat_client
from src.prompts.registry import render_support_prompt
from src.settings import get_settings
from src.tools import (
    calculate_sla_deadline,
    draft_support_ticket,
    get_service_status,
)


def build_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    instructions, prompt_registration = render_support_prompt()

    return client.as_agent(
        name=prompt_registration.agent_name,
        instructions=instructions,
        tools=[
            get_service_status,
            calculate_sla_deadline,
            draft_support_ticket,
        ],
    )