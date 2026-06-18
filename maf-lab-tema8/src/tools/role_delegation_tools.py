from typing import Annotated, Literal

from agent_framework import tool
from pydantic import Field

from src.agents.multiagent.role_catalog import get_role, render_role_catalog
from src.agents.multiagent.role_specialists import build_agent_for_role


RoleName = Literal[
    "network_specialist",
    "identity_specialist",
    "itsm_specialist",
    "security_specialist",
]


@tool(
    name="consultar_catalogo_roles",
    description=(
        "Devuelve el catálogo de roles disponibles, sus responsabilidades, límites y escalados. "
        "Úsala cuando necesites decidir qué rol debe intervenir."
    ),
)
def consultar_catalogo_roles() -> str:
    return render_role_catalog()


@tool(
    name="delegar_por_rol",
    description=(
        "Delega una tarea a un agente especializado según su rol registrado. "
        "La tarea debe estar alineada con el dominio del rol. "
        "No ejecuta acciones reales; solo obtiene análisis o recomendación."
    ),
)
async def delegar_por_rol(
    rol_destino: Annotated[
        RoleName,
        Field(
            description=(
                "Rol especializado al que se delega la tarea. "
                "Debe ser network_specialist, identity_specialist, itsm_specialist o security_specialist."
            ),
        ),
    ],
    tarea: Annotated[
        str,
        Field(
            description="Tarea concreta que debe resolver el rol seleccionado.",
            min_length=10,
        ),
    ],
    contexto: Annotated[
        str,
        Field(
            description="Contexto mínimo necesario para resolver la tarea.",
            min_length=10,
        ),
    ],
) -> str:
    role = get_role(rol_destino)

    prompt = (
        "TAREA ASIGNADA POR ROL\n\n"
        f"Rol destino: {role.name}\n"
        f"Dominio del rol: {role.domain}\n"
        f"Riesgo máximo permitido: {role.max_risk_level}\n\n"
        f"Tarea:\n{tarea}\n\n"
        f"Contexto:\n{contexto}\n\n"
        f"Límites del rol:\n- " + "\n- ".join(role.forbidden_tasks) + "\n\n"
        f"Contrato de salida:\n- " + "\n- ".join(role.output_contract) + "\n\n"
        "Si la tarea excede tu rol, no la resuelvas: indica el escalado adecuado."
    )

    agent = build_agent_for_role(rol_destino)
    result = await agent.run(prompt)

    return str(result)