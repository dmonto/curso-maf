from __future__ import annotations

import json
import os
from pathlib import Path

from azure.ai.evaluation import (
    CoherenceEvaluator,
    FluencyEvaluator,
    RelevanceEvaluator,
)
from dotenv import load_dotenv

load_dotenv()

REPORTS_DIR = Path("reports")
REPORT_PATH = REPORTS_DIR / "azure_ai_evaluation_report.json"


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)

    model_config = {
        "azure_endpoint": os.environ["AZURE_AI_FOUNDRY_ENDPOINT"],
        "azure_deployment": os.environ["AZURE_OPENAI_DEPLOYMENT_CHAT"],
        "api_key": os.environ["AZURE_OPENAI_API_KEY"],
    }

    query = "La VPN conecta, pero va muy lenta. ¿Qué debería revisar primero?"

    response = (
        "Revisa primero si el problema afecta solo a tu equipo o a varios usuarios. "
        "Comprueba conectividad, reinicia el cliente VPN, valida MFA y prueba otra red. "
        "Si afecta a varios usuarios, conviene comprobar si hay una incidencia global. "
        "No he creado ningún ticket real."
    )

    relevance = RelevanceEvaluator(model_config)
    coherence = CoherenceEvaluator(model_config)
    fluency = FluencyEvaluator(model_config)

    results = {
        "query": query,
        "response": response,
        "relevance": relevance(
            query=query,
            response=response,
        ),
        "coherence": coherence(
            query=query,
            response=response,
        ),
        "fluency": fluency(
            query=query,
            response=response,
        ),
        "deterministic_checks": {
            "does_not_claim_ticket_created": "ticket creado" not in response.lower(),
            "mentions_vpn": "vpn" in response.lower(),
        },
    }

    REPORT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nReporte: {REPORT_PATH}")


if __name__ == "__main__":
    main()