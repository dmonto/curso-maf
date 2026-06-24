from src.models.registry import build_model_registry


def main() -> None:
    registry = build_model_registry()

    print("\n--- MODELOS REGISTRADOS ---")

    for logical_name, registration in registry.items():
        print(f"\nNombre lógico: {logical_name}")
        print(f"Tipo:          {registration.kind}")
        print(f"Deployment:    {registration.deployment_name}")
        print(f"Endpoint:      {registration.endpoint}")
        print(f"API version:   {registration.api_version}")
        print(f"Descripción:   {registration.description}")


if __name__ == "__main__":
    main()