from __future__ import annotations

import sys

from src.dependency_control.import_boundary_checker import check_project


def main() -> None:
    violations = check_project()

    if not violations:
        print("OK - No se han detectado violaciones de dependencias internas.")
        return

    print("\nERROR - Violaciones de dependencias detectadas:\n")

    for violation in violations:
        print(
            f"- {violation.file_path}:{violation.line_number} "
            f"[{violation.layer}] importa {violation.imported_module}"
        )
        print(f"  Motivo: {violation.reason}")

    print("\nCorrige los imports antes de continuar.")
    sys.exit(1)


if __name__ == "__main__":
    main()