from src.models.factory import create_chat_client
from src.settings import get_settings
from src.tools import (
    calculate_sla_deadline,
    draft_support_ticket,
    get_service_status,
)


def build_support_agent(model_alias: str | None = None):
    settings = get_settings()
    selected_model = model_alias or settings.default_chat_model

    client = create_chat_client(selected_model)

    return client.as_agent(
        name=f"maf_support_agent_{selected_model}",
        instructions=(
            "Eres un agente de soporte técnico interno. "
            "Ayudas a diagnosticar incidencias de servicios corporativos. "
            "Puedes consultar estado de servicios, calcular SLA y preparar borradores de ticket. "
            "No afirmes que has creado tickets reales ni que has ejecutado acciones externas "
            "si solo has preparado un borrador. "
            "Para acciones sensibles, pide confirmación o indica la limitación."
        ),
        tools=[
            get_service_status,
            calculate_sla_deadline,
            draft_support_ticket,
        ],
    )