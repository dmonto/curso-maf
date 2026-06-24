from src.retrieval.contextual_retriever import build_context_package


def print_package(package: dict) -> None:
    print(f"\nConsulta original: {package['original_query']}")
    print(f"Consulta recuperación: {package['retrieval_query']}")
    print(f"Dominio: {package['domain']}")
    print(f"Confianza: {package['confidence']}")
    print(f"Resultados: {package['results_count']}")

    if package["warnings"]:
        print("\nWarnings:")
        for warning in package["warnings"]:
            print(f"- {warning}")

    print("\nContexto seleccionado:")

    for item in package["context"]:
        print(f"\nFuente: {item['source_id']}")
        print(f"Título: {item['title']}")
        print(f"Dominio: {item['domain']}")
        print(f"Motivo: {item['reason']}")
        print(f"Texto: {item['text'][:220]}...")


def main() -> None:
    case_state = {
        "servicio": "VPN",
        "sistema_operativo": "Windows 11",
        "sintoma": "No puede acceder desde casa",
        "usuarios_afectados": 1,
        "pasos_probados": ["validar_mfa", "probar_otra_red"],
    }

    package = build_context_package(
        user_query="¿Qué debería revisar ahora y qué prioridad tendría?",
        conversation_summary=(
            "El usuario no puede acceder a la red privada corporativa desde casa. "
            "Indica que tiene Internet y que el problema solo le ocurre a él."
        ),
        case_state=case_state,
    )

    print_package(package)


if __name__ == "__main__":
    main()