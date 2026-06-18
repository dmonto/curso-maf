from src.agents.multiagent.role_catalog import get_role
from src.models.factory import create_chat_client
from src.settings import get_settings


def _build_role_instructions(role_name: str) -> str:
    role = get_role(role_name)

    return (
        f"Eres el agente con rol {role.name}.\n\n"
        f"Propósito:\n{role.purpose}\n\n"
        f"Dominio:\n{role.domain}\n\n"
        f"Tareas permitidas:\n- " + "\n- ".join(role.allowed_tasks) + "\n\n"
        f"Tareas prohibidas:\n- " + "\n- ".join(role.forbidden_tasks) + "\n\n"
        f"Debes escalar a:\n- " + "\n- ".join(role.escalation_targets) + "\n\n"
        f"Contrato de salida obligatorio:\n- " + "\n- ".join(role.output_contract) + "\n\n"
        "No salgas de tu rol. Si la tarea no pertenece a tu dominio, indícalo y recomienda escalado."
    )


def build_agent_for_role(role_name: str):
    settings = get_settings()
    client = create_chat_client(settings.default_chat_model)

    return client.as_agent(
        name=role_name,
        instructions=_build_role_instructions(role_name),
    )