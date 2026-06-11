import asyncio
import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Annotated, Any, Literal

from agent_framework import Agent, tool
from agent_framework.openai import OpenAIChatCompletionClient
from azure.identity import AzureCliCredential
from pydantic import BaseModel, Field, ValidationError


# ---------------------------------------------------------------------
# 1. Modelos de resultado
# ---------------------------------------------------------------------

class SupportResult(BaseModel):
    """
    Contrato estructurado de salida del agente.
    Este objeto representa lo que la aplicación necesita,
    no solo lo que el usuario va a leer.
    """

    service: Literal["vpn", "correo", "teams", "erp", "desconocido"]
    summary: str = Field(min_length=10)
    priority: Literal["baja", "media", "alta", "desconocida"]
    requires_escalation: bool
    missing_fields: list[str]
    recommended_next_action: Literal[
        "ask_missing_data",
        "diagnostic_steps",
        "prepare_ticket_draft",
        "escalate",
        "close",
    ]
    user_message: str = Field(min_length=10)


@dataclass
class ResultEnvelope:
    """
    Resultado normalizado de una ejecución.
    Agrupa salida de negocio, metadatos técnicos y estado de validación.
    """

    run_id: str
    session_id: str
    agent_name: str
    agent_version: str
    timestamp: float
    ok: bool
    result: dict[str, Any] | None = None
    user_message: str | None = None
    raw_text: str | None = None
    response_id: str | None = None
    usage_details: dict[str, Any] | None = None
    validation_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------
# 2. Utilidades de configuración y persistencia
# ---------------------------------------------------------------------

def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")
    return value


def append_jsonl(path: str, item: dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def redact_sensitive_text(text: str) -> str:
    """
    Redacción mínima para demo.
    En producción, esto debería integrarse con políticas,
    detección de secretos o clasificación de información.
    """
    text = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[email_redactado]", text)
    text = re.sub(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*\S+", r"\1=[redactado]", text)
    return text


# ---------------------------------------------------------------------
# 3. Tools con resultados compactos
# ---------------------------------------------------------------------

@tool(
    name="consultar_incidencia_conocida",
    description=(
        "Consulta si hay una incidencia conocida para un servicio corporativo. "
        "Devuelve JSON compacto con estado, severidad y detalle."
    ),
    approval_mode="never_require",
)
def consultar_incidencia_conocida(
    service: Annotated[
        Literal["vpn", "correo", "teams", "erp"],
        Field(description="Servicio corporativo afectado."),
    ],
) -> str:
    data = {
        "vpn": {
            "known_incident": True,
            "severity": "media",
            "details": "Incidencias intermitentes de VPN para usuarios remotos.",
        },
        "correo": {
            "known_incident": False,
            "severity": "baja",
            "details": "No hay incidencia global de correo registrada.",
        },
        "teams": {
            "known_incident": True,
            "severity": "media",
            "details": "Degradación parcial en reuniones de Teams.",
        },
        "erp": {
            "known_incident": False,
            "severity": "baja",
            "details": "No hay incidencia general registrada para ERP.",
        },
    }

    return json.dumps(data[service], ensure_ascii=False)


@tool(
    name="clasificar_prioridad",
    description=(
        "Clasifica la prioridad de una incidencia según impacto y usuarios afectados. "
        "No debe usarse si faltan esos datos."
    ),
    approval_mode="never_require",
)
def clasificar_prioridad(
    impact: Annotated[
        Literal["bajo", "medio", "alto"],
        Field(description="Impacto funcional indicado por el usuario."),
    ],
    users_affected: Annotated[
        int,
        Field(description="Número de usuarios afectados.", ge=1, le=10000),
    ],
) -> str:
    if impact == "alto" or users_affected > 10:
        result = {
            "priority": "alta",
            "requires_escalation": True,
            "reason": "Impacto alto o más de 10 usuarios afectados.",
        }
    elif impact == "medio" or users_affected > 1:
        result = {
            "priority": "media",
            "requires_escalation": False,
            "reason": "Impacto medio o más de un usuario afectado.",
        }
    else:
        result = {
            "priority": "baja",
            "requires_escalation": False,
            "reason": "Impacto bajo y un único usuario afectado.",
        }

    return json.dumps(result, ensure_ascii=False)


@tool(
    name="preparar_borrador_ticket",
    description=(
        "Prepara un borrador de ticket. "
        "No crea tickets reales. "
        "Devuelve JSON con identificador de borrador y estado."
    ),
    approval_mode="never_require",
)
def preparar_borrador_ticket(
    service: Annotated[
        Literal["vpn", "correo", "teams", "erp"],
        Field(description="Servicio afectado."),
    ],
    summary: Annotated[
        str,
        Field(description="Resumen breve de la incidencia.", min_length=10),
    ],
    priority: Annotated[
        Literal["baja", "media", "alta"],
        Field(description="Prioridad de la incidencia."),
    ],
) -> str:
    draft = {
        "draft_id": f"DRAFT-{uuid.uuid4().hex[:8].upper()}",
        "service": service,
        "summary": summary,
        "priority": priority,
        "status": "draft_pending_confirmation",
        "real_ticket_created": False,
    }

    return json.dumps(draft, ensure_ascii=False)


# ---------------------------------------------------------------------
# 4. Construcción del agente
# ---------------------------------------------------------------------

def build_agent() -> Agent:
    client = OpenAIChatCompletionClient(
        model=require_env("AZURE_OPENAI_DEPLOYMENT_CHAT"),
        azure_endpoint=require_env("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        credential=AzureCliCredential(),
    )

    return client.as_agent(
        name="AgenteSoporteGestionResultados",
        instructions=(
            "Eres un agente de soporte técnico de nivel 1. "
            "Debes devolver SIEMPRE un resultado que encaje con el esquema SupportResult. "
            "Usa tools si necesitas consultar incidencias conocidas, clasificar prioridad "
            "o preparar un borrador de ticket. "
            "No inventes usuarios afectados, impacto ni servicio. "
            "Si falta información, usa recommended_next_action='ask_missing_data' "
            "e indica los campos pendientes en missing_fields. "
            "No digas que has creado un ticket real. Solo puedes preparar borradores. "
            "El campo user_message debe contener la respuesta final visible para el usuario."
        ),
        tools=[
            consultar_incidencia_conocida,
            clasificar_prioridad,
            preparar_borrador_ticket,
        ],
    )


# ---------------------------------------------------------------------
# 5. Validación adicional de negocio
# ---------------------------------------------------------------------

def validate_business_rules(result: SupportResult) -> list[str]:
    errors: list[str] = []

    if result.recommended_next_action == "prepare_ticket_draft":
        required = {"service", "summary", "priority"}

        if result.service == "desconocido":
            errors.append("No se puede preparar borrador si el servicio es desconocido.")

        if result.priority == "desconocida":
            errors.append("No se puede preparar borrador si la prioridad es desconocida.")

        if result.missing_fields:
            errors.append(
                "No se puede preparar borrador si existen campos pendientes: "
                + ", ".join(result.missing_fields)
            )

    if result.requires_escalation and result.priority == "baja":
        errors.append("Inconsistencia: requiere escalado pero la prioridad es baja.")

    return errors


# ---------------------------------------------------------------------
# 6. Fallback si la salida estructurada falla
# ---------------------------------------------------------------------

def fallback_from_text(raw_text: str) -> SupportResult:
    """
    Fallback deliberadamente conservador.
    Si no se puede obtener estructura fiable, no se inventan campos:
    se devuelve resultado desconocido y se pide aclaración.
    """
    clean_text = redact_sensitive_text(raw_text)

    return SupportResult(
        service="desconocido",
        summary="No se pudo extraer un resultado estructurado fiable.",
        priority="desconocida",
        requires_escalation=False,
        missing_fields=["service", "impact", "users_affected"],
        recommended_next_action="ask_missing_data",
        user_message=(
            "No tengo datos suficientes en un formato fiable. "
            "Indica el servicio afectado, el impacto y cuántos usuarios están afectados."
        ),
    )


# ---------------------------------------------------------------------
# 7. Ejecución y gestión del resultado
# ---------------------------------------------------------------------

async def run_and_manage_result(
    agent: Agent,
    session,
    user_input: str,
    session_id: str,
) -> ResultEnvelope:
    run_id = str(uuid.uuid4())

    try:
        response = await agent.run(
            user_input,
            session=session,
            options={"response_format": SupportResult},
        )

        raw_text = getattr(response, "text", None)
        response_id = getattr(response, "response_id", None)
        usage_details = getattr(response, "usage_details", None)

        warnings: list[str] = []

        if response.value:
            support_result = response.value
        else:
            warnings.append("La respuesta no incluía value estructurado. Se usa fallback.")
            support_result = fallback_from_text(raw_text or "")

        business_errors = validate_business_rules(support_result)

        ok = len(business_errors) == 0

        envelope = ResultEnvelope(
            run_id=run_id,
            session_id=session_id,
            agent_name="AgenteSoporteGestionResultados",
            agent_version="0.1.0",
            timestamp=time.time(),
            ok=ok,
            result=support_result.model_dump(),
            user_message=redact_sensitive_text(support_result.user_message),
            raw_text=redact_sensitive_text(raw_text or ""),
            response_id=response_id,
            usage_details=usage_details if isinstance(usage_details, dict) else None,
            validation_errors=business_errors,
            warnings=warnings,
        )

    except ValidationError as ex:
        envelope = ResultEnvelope(
            run_id=run_id,
            session_id=session_id,
            agent_name="AgenteSoporteGestionResultados",
            agent_version="0.1.0",
            timestamp=time.time(),
            ok=False,
            validation_errors=[str(ex)],
            user_message=(
                "No he podido generar un resultado válido. "
                "Reformula la incidencia indicando servicio, impacto y usuarios afectados."
            ),
        )

    except Exception as ex:
        envelope = ResultEnvelope(
            run_id=run_id,
            session_id=session_id,
            agent_name="AgenteSoporteGestionResultados",
            agent_version="0.1.0",
            timestamp=time.time(),
            ok=False,
            validation_errors=[f"Error de ejecución: {ex}"],
            user_message=(
                "Se ha producido un error controlado durante la ejecución. "
                "No se ha realizado ninguna acción real."
            ),
        )

    append_jsonl("agent_results.jsonl", asdict(envelope))
    return envelope


# ---------------------------------------------------------------------
# 8. Demo
# ---------------------------------------------------------------------

async def main() -> None:
    agent = build_agent()
    session = agent.create_session()
    session_id = str(uuid.uuid4())

    test_cases = [
        "No puedo acceder a la VPN desde casa. Solo me pasa a mí y el impacto es bajo.",
        "El correo no funciona en todo el departamento. Somos 25 personas y el impacto es alto.",
        "Teams va lento, pero no sé si afecta a alguien más.",
        "Prepara un ticket real y usa este token=abc123",
    ]

    for user_input in test_cases:
        print("\n" + "=" * 100)
        print("Usuario>")
        print(user_input)

        envelope = await run_and_manage_result(
            agent=agent,
            session=session,
            user_input=user_input,
            session_id=session_id,
        )

        print("\nRespuesta visible>")
        print(envelope.user_message)

        print("\nResultado normalizado>")
        print(json.dumps(asdict(envelope), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())