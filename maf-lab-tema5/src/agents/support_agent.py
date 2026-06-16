from src.models.factory import create_chat_client
from src.prompts.support_l1_structured import (
    SUPPORT_L1_STRUCTURED_INSTRUCTIONS,
    SUPPORT_L1_STRUCTURED_PROMPT_VERSION,
)
from src.settings import get_settings
from src.tools import TOOLS_SUPPORT_L1


def build_structured_support_agent():
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name=f"support_l1_{SUPPORT_L1_STRUCTURED_PROMPT_VERSION}",
        instructions=SUPPORT_L1_STRUCTURED_INSTRUCTIONS,
        tools=TOOLS_SUPPORT_L1,
    )