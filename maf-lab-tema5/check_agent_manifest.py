from src.governance import SUPPORT_L1_MANIFEST


def main() -> None:
    manifest = SUPPORT_L1_MANIFEST

    print("\n--- MANIFEST DEL AGENTE ---")
    print(manifest.model_dump_json(indent=2))

    print("\n--- RESUMEN OPERATIVO ---")
    print(f"Agente: {manifest.agent_name}")
    print(f"Versión: {manifest.agent_version}")
    print(f"Entorno: {manifest.environment}")
    print(f"Riesgo: {manifest.risk_level}")
    print(f"Clasificación del dato: {manifest.data_classification}")
    print(f"Prompt: {manifest.prompt_version}")
    print(f"Tools permitidas: {', '.join(manifest.tool_policy.allowed_tools)}")
    print(f"Suite de tests: {manifest.test_policy.regression_suite}")


if __name__ == "__main__":
    main()