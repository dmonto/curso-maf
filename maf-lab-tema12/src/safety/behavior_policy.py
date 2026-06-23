from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal


BehaviorAction = Literal[
    "allow",
    "ask_clarification",
    "safe_refusal",
    "safe_redirect",
]


@dataclass(frozen=True)
class BehaviorDecision:
    action: BehaviorAction
    safe_message: str | None
    reasons: list[str]
    sanitized_user_text: str


FORBIDDEN_USER_PATTERNS = {
    "prompt_disclosure": [
        r"muestra tus instrucciones",
        r"revela tu prompt",
        r"lista tus reglas internas",
        r"system prompt",
    ],
    "role_override": [
        r"ignora (tus|las|los) instrucciones",
        r"act[uú]a como administrador",
        r"ahora eres administrador",
        r"ignore previous instructions",
    ],
    "real_action_bypass": [
        r"sin aprobaci[oó]n",
        r"salta( te)? la validaci[oó]n",
        r"crea.*ticket real",
        r"ejecuta.*directamente",
    ],
    "sensitive_admin_action": [
        r"cambia.*permisos",
        r"hazme administrador",
        r"borra.*usuario",
        r"elimina.*datos",
        r"desactiva.*mfa",
    ],
}


FORBIDDEN_RESPONSE_PATTERNS = {
    "claims_real_ticket_created": [
        r"he creado (el )?ticket real",
        r"ticket real creado",
        r"ya he abierto la incidencia en el sistema",
    ],
    "claims_permission_change": [
        r"he cambiado (los )?permisos",
        r"ya tienes permisos de administrador",
        r"he desactivado.*mfa",
    ],
    "prompt_leak": [
        r"mis instrucciones internas son",
        r"mi prompt de sistema",
        r"estas son mis reglas internas",
    ],
}


AZURE_CONTENT_SAFETY_MARKERS = (
    "content_filter",
    "content filter",
    "responsibleaipolicyviolation",
    "responsible ai policy",
    "content management policy",
    "prompt was filtered",
    "response was filtered",
    "filtered due to",
    "jailbreak",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _find_matches(text: str, pattern_groups: dict[str, list[str]]) -> list[str]:
    lowered = text.lower()
    matches: list[str] = []

    for group_name, patterns in pattern_groups.items():
        for pattern in patterns:
            if re.search(pattern, lowered):
                matches.append(group_name)
                break

    return matches


def _remove_pattern_groups(text: str, groups: set[str]) -> str:
    cleaned = text

    for group_name in groups:
        for pattern in FORBIDDEN_USER_PATTERNS.get(group_name, []):
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"^\s*(y|and)\s+", "", cleaned, flags=re.IGNORECASE)

    return _normalize(cleaned)


def precheck_user_behavior(raw_user_text: str) -> BehaviorDecision:
    """
    Revisión previa al agente.

    No sustituye a la validación de entrada ni a las validaciones internas
    de las tools. Aplica reglas de comportamiento de alto nivel antes de
    llamar al modelo.
    """
    sanitized = _normalize(raw_user_text)

    if not sanitized:
        return BehaviorDecision(
            action="ask_clarification",
            safe_message="Indica qué problema necesitas revisar.",
            reasons=["empty_message"],
            sanitized_user_text="",
        )

    matches = _find_matches(sanitized, FORBIDDEN_USER_PATTERNS)

    if "prompt_disclosure" in matches:
        return BehaviorDecision(
            action="safe_refusal",
            safe_message=(
                "No puedo mostrar instrucciones internas, prompts ni reglas del sistema. "
                "Sí puedo ayudarte con una incidencia técnica concreta."
            ),
            reasons=matches,
            sanitized_user_text=sanitized,
        )

    if "sensitive_admin_action" in matches:
        return BehaviorDecision(
            action="safe_redirect",
            safe_message=(
                "No puedo modificar permisos, borrar usuarios ni ejecutar acciones "
                "administrativas. Si necesitas soporte, puedo ayudarte a preparar un "
                "borrador de incidencia con servicio afectado, impacto y usuarios afectados."
            ),
            reasons=matches,
            sanitized_user_text=sanitized,
        )

    if "real_action_bypass" in matches:
        return BehaviorDecision(
            action="safe_redirect",
            safe_message=(
                "No puedo saltarme aprobaciones ni ejecutar acciones reales directamente. "
                "Puedo ayudarte a preparar un borrador de incidencia para revisión, "
                "incluyendo servicio afectado, impacto, prioridad y descripción."
            ),
            reasons=matches,
            sanitized_user_text=sanitized,
        )

    if "role_override" in matches:
        cleaned = _remove_pattern_groups(sanitized, {"role_override"})

        if not cleaned:
            return BehaviorDecision(
                action="ask_clarification",
                safe_message=(
                    "He retirado instrucciones no válidas del mensaje. Indica la incidencia "
                    "técnica que necesitas revisar."
                ),
                reasons=matches,
                sanitized_user_text="",
            )

        return BehaviorDecision(
            action="allow",
            safe_message=None,
            reasons=matches,
            sanitized_user_text=cleaned,
        )

    return BehaviorDecision(
        action="allow",
        safe_message=None,
        reasons=[],
        sanitized_user_text=sanitized,
    )


def postcheck_agent_response(agent_response: str) -> BehaviorDecision:
    """
    Revisión posterior a la respuesta del agente.

    Sirve como red de seguridad cuando el agente promete acciones que este rol
    no puede hacer.
    """
    sanitized = _normalize(agent_response)
    matches = _find_matches(sanitized, FORBIDDEN_RESPONSE_PATTERNS)

    if not matches:
        return BehaviorDecision(
            action="allow",
            safe_message=None,
            reasons=[],
            sanitized_user_text=sanitized,
        )

    if "claims_real_ticket_created" in matches:
        return BehaviorDecision(
            action="safe_redirect",
            safe_message=(
                "Corrección: este agente no crea tickets reales. "
                "Solo puede preparar borradores de ticket para revisión o validación."
            ),
            reasons=matches,
            sanitized_user_text=sanitized,
        )

    if "claims_permission_change" in matches:
        return BehaviorDecision(
            action="safe_refusal",
            safe_message=(
                "Corrección: este agente no modifica permisos ni realiza acciones "
                "administrativas. Debe escalarse al equipo autorizado."
            ),
            reasons=matches,
            sanitized_user_text=sanitized,
        )

    if "prompt_leak" in matches:
        return BehaviorDecision(
            action="safe_refusal",
            safe_message=(
                "No puedo mostrar instrucciones internas. "
                "Puedo resumir mis capacidades funcionales: diagnosticar incidencias básicas, "
                "consultar estado de servicios, calcular SLA y preparar borradores."
            ),
            reasons=matches,
            sanitized_user_text=sanitized,
        )

    return BehaviorDecision(
        action="allow",
        safe_message=None,
        reasons=matches,
        sanitized_user_text=sanitized,
    )


def _exception_payload_text(exc: BaseException) -> str:
    """
    Extrae texto de una excepción del SDK o de una excepción envuelta por MAF.

    No dependemos de una clase concreta porque el error puede venir envuelto
    como BadRequestError, APIStatusError, RuntimeError u otro tipo según versión
    del SDK, proveedor y runtime.
    """
    chunks: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()

    while current is not None and id(current) not in seen:
        seen.add(id(current))

        chunks.append(type(current).__name__)
        chunks.append(str(current))

        for attr in ("body", "error", "response"):
            value = getattr(current, attr, None)

            if value is None:
                continue

            chunks.append(str(value))

            if attr == "response":
                for response_attr in ("text", "content"):
                    try:
                        response_value = getattr(value, response_attr, None)
                    except Exception:
                        response_value = None

                    if response_value:
                        chunks.append(str(response_value))

                try:
                    chunks.append(str(value.json()))
                except Exception:
                    pass

        current = current.__cause__ or current.__context__

    return "\n".join(chunks).lower()


def is_azure_content_safety_exception(exc: BaseException) -> bool:
    payload = _exception_payload_text(exc)
    return any(marker in payload for marker in AZURE_CONTENT_SAFETY_MARKERS)


def behavior_decision_from_model_exception(
    exc: BaseException,
) -> BehaviorDecision | None:
    """
    Convierte una excepción de Azure OpenAI Content Safety en una respuesta segura.

    Si la excepción no parece estar relacionada con Content Safety, devuelve None
    para que el error real pueda propagarse.
    """
    if not is_azure_content_safety_exception(exc):
        return None

    return BehaviorDecision(
        action="safe_redirect",
        safe_message=(
            "No puedo procesar esa petición tal como está formulada porque ha sido "
            "bloqueada por la política de seguridad del modelo. Reformula la incidencia "
            "técnica sin instrucciones para saltar reglas, permisos, validaciones o "
            "acciones reales."
        ),
        reasons=["azure_content_safety"],
        sanitized_user_text="",
    )


def _agent_result_to_text(result: Any) -> str:
    """
    Normaliza el resultado devuelto por agent.run(...).

    Según proveedor y versión, el resultado puede ser string o un objeto con
    atributos como text, content o message.
    """
    if isinstance(result, str):
        return result

    for attr in ("text", "content", "message"):
        value = getattr(result, attr, None)
        if isinstance(value, str):
            return value

    return str(result)


async def run_agent_with_behavior_guardrails(
    raw_user_text: str,
    agent_run: Callable[[str], Awaitable[Any]],
) -> str:
    """
    Ejecuta el agente con tres capas:

    1. Precheck local del mensaje del usuario.
    2. Captura de excepción de Azure OpenAI Content Safety.
    3. Postcheck local de la respuesta del agente.
    """
    pre_decision = precheck_user_behavior(raw_user_text)

    if pre_decision.action != "allow":
        return pre_decision.safe_message or "No puedo procesar esa petición."

    try:
        result = await agent_run(pre_decision.sanitized_user_text)

    except Exception as exc:
        safety_decision = behavior_decision_from_model_exception(exc)

        if safety_decision is not None:
            return safety_decision.safe_message or "La petición ha sido bloqueada."

        raise

    response_text = _agent_result_to_text(result)
    post_decision = postcheck_agent_response(response_text)

    if post_decision.action != "allow":
        return post_decision.safe_message or "La respuesta ha sido bloqueada por seguridad."

    return response_text