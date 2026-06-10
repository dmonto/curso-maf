import asyncio
import os
from typing import Annotated

from azure.identity.aio import AzureCliCredential
from agent_framework import tool
from agent_framework.openai import OpenAIChatCompletionClient
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()

def require_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value

    raise RuntimeError(
        "Falta configurar alguna de estas variables de entorno: "
        + ", ".join(names)
    )


@tool(
    name="classify_architecture_pattern",
    description=(
        "Clasifica una necesidad empresarial como función simple, agente o workflow "
        "según ambigüedad, pasos de proceso, necesidad de tools y control operativo."
    ),
    approval_mode="never_require",
)
def classify_architecture_pattern(
    description: Annotated[
        str,
        Field(description="Descripción breve del caso de uso o necesidad empresarial.")
    ],
    has_fixed_rules: Annotated[
        bool,
        Field(description="True si la lógica puede expresarse con reglas deterministas.")
    ] = False,
    has_natural_language_ambiguity: Annotated[
        bool,
        Field(description="True si hay ambigüedad de lenguaje natural o intención.")
    ] = False,
    has_multiple_steps: Annotated[
        bool,
        Field(description="True si hay varios pasos, validaciones o decisiones.")
    ] = False,
    needs_external_tools: Annotated[
        bool,
        Field(description="True si necesita consultar APIs, bases de datos o sistemas externos.")
    ] = False,
    needs_human_approval: Annotated[
        bool,
        Field(description="True si hay aprobación o revisión humana en algún punto.")
    ] = False,
) -> dict:
    """
    Tool determinista de arquitectura.

    El agente puede explicar la decisión, pero la clasificación base
    se calcula con reglas explícitas y fáciles de auditar.
    """

    reasons: list[str] = []

    if has_fixed_rules and not has_natural_language_ambiguity and not has_multiple_steps:
        pattern = "funcion_simple"
        reasons.append("La lógica parece determinista y no requiere razonamiento agentic.")

    elif has_multiple_steps or needs_human_approval:
        pattern = "workflow"
        reasons.append("Hay pasos definidos, decisiones de proceso o intervención humana.")

    elif has_natural_language_ambiguity or needs_external_tools:
        pattern = "agent"
        reasons.append("Hay interpretación de lenguaje natural o selección dinámica de tools.")

    else:
        pattern = "funcion_simple"
        reasons.append("No hay señales suficientes para introducir un agente.")

    if needs_external_tools:
        reasons.append("Conviene encapsular integraciones externas como tools.")

    if needs_human_approval:
        reasons.append("La aprobación humana debe modelarse como paso explícito del proceso.")

    return {
        "recommended_pattern": pattern,
        "reasons": reasons,
        "description": description,
    }


async def build_agent():
    endpoint = require_env("AZURE_OPENAI_ENDPOINT")
    model = require_env(
        "AZURE_OPENAI_CHAT_COMPLETION_MODEL",
        "AZURE_OPENAI_DEPLOYMENT_CHAT",
        "AZURE_OPENAI_DEPLOYMENT_1",
    )
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    print("AZURE_OPENAI_ENDPOINT:", endpoint)
    print("MODEL / DEPLOYMENT:", model)
    print("API VERSION:", api_version)
    credential = AzureCliCredential()

    client = OpenAIChatCompletionClient(
        model=model,
        azure_endpoint=endpoint,
        api_version=api_version,
        credential=credential,
    )

    return client.as_agent(
        name="MAFArchitectureAdvisor",
        instructions=(
            "Eres un arquitecto de soluciones con Microsoft Agent Framework. "
            "Usa siempre la tool classify_architecture_pattern antes de responder. "
            "Después explica la recomendación en español, diferenciando claramente "
            "función simple, agent y workflow. "
            "No recomiendes agentes si una función determinista es suficiente."
        ),
        tools=[classify_architecture_pattern],
    )


async def main() -> None:

    agent = await build_agent()

    cases = [
        (
            "Calcular el IVA de una factura.",
            "has_fixed_rules=True, has_natural_language_ambiguity=False, "
            "has_multiple_steps=False, needs_external_tools=False, needs_human_approval=False",
        ),
        (
            "Clasificar correos de soporte y decidir si consultar una base de conocimiento.",
            "has_fixed_rules=False, has_natural_language_ambiguity=True, "
            "has_multiple_steps=False, needs_external_tools=True, needs_human_approval=False",
        ),
        (
            "Aprobar una solicitud de compra con validación de proveedor, presupuesto "
            "y aprobación humana si supera 5000 euros.",
            "has_fixed_rules=False, has_natural_language_ambiguity=True, "
            "has_multiple_steps=True, needs_external_tools=True, needs_human_approval=True",
        ),
    ]

    for description, signals in cases:
        user_prompt = (
            f"Caso de uso: {description}\n"
            f"Señales arquitectónicas: {signals}\n"
            "Recomienda el patrón MAF adecuado."
        )

        print("\n" + "=" * 100)
        print(user_prompt)
        print("\nRespuesta:\n")

        result = await agent.run(user_prompt)
        print(result.text if hasattr(result, "text") else str(result))


if __name__ == "__main__":
    asyncio.run(main())