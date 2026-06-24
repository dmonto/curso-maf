from __future__ import annotations

from pathlib import Path

from src.evals.migration_eval_runner import run_eval_suite, write_eval_report


CASES_PATH = Path("src/evals/migration_eval_cases.json")
REPORT_PATH = Path("data/migration_eval_report.json")


def main() -> None:
    results = run_eval_suite(CASES_PATH)

    print("\n=== RESULTADOS DE EVALUACIÓN DE MIGRACIÓN ===")

    for result in results:
        status = "PASS" if result.passed else "FAIL"

        print(f"\n[{status}] {result.case_id}")
        print(f"Origen legacy: {result.source_legacy}")
        print(f"Score: {result.score}")
        print(f"Workflow status: {result.workflow_status}")
        print(f"Category: {result.category}")
        print(f"Service: {result.service}")

        print("\nChecks:")
        for check in result.checks:
            marker = "✓" if check.passed else "✗"
            print(f"  {marker} {check.name}: {check.detail}")

        print("\nRespuesta final:")
        print(result.final_response)

    write_eval_report(results, REPORT_PATH)

    failed = [result for result in results if not result.passed]

    print(f"\nInforme escrito en: {REPORT_PATH}")

    if failed:
        raise SystemExit(f"Hay {len(failed)} caso(s) fallidos.")

    print("Todos los casos han pasado.")


if __name__ == "__main__":
    main()