import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.tools.support_tools import (
    _calculate_sla_deadline_impl,
    _draft_support_ticket_impl,
    _get_service_status_impl,
)


CASES_PATH = Path("tool_validation_cases.jsonl")
REPORTS_DIR = Path("reports")
REPORT_PATH = REPORTS_DIR / "tool_validation_report.json"


TOOL_IMPLEMENTATIONS: dict[str, Callable[..., dict[str, Any]]] = {
    "get_service_status": _get_service_status_impl,
    "calculate_sla_deadline": _calculate_sla_deadline_impl,
    "draft_support_ticket": _draft_support_ticket_impl,
}


@dataclass
class ValidationCheck:
    name: str
    passed: bool
    detail: str


@dataclass
class ToolValidationResult:
    case_id: str
    tool: str
    passed: bool
    output: dict[str, Any]
    checks: list[ValidationCheck]


def load_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero: {path}")

    cases: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON inválido en línea {line_number}: {exc}") from exc

    return cases


def check_json_serializable(output: dict[str, Any]) -> ValidationCheck:
    try:
        json.dumps(output, ensure_ascii=False)
        return ValidationCheck(
            name="json_serializable",
            passed=True,
            detail="La salida es serializable a JSON.",
        )
    except TypeError as exc:
        return ValidationCheck(
            name="json_serializable",
            passed=False,
            detail=f"La salida no es serializable a JSON: {exc}",
        )


def check_must_include_keys(
    output: dict[str, Any],
    keys: list[str],
) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []

    for key in keys:
        checks.append(
            ValidationCheck(
                name="must_include_key",
                passed=key in output,
                detail=f"Debe incluir la clave: {key}",
            )
        )

    return checks


def check_field_equals(
    output: dict[str, Any],
    expected_values: dict[str, Any],
) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []

    for field, expected_value in expected_values.items():
        actual_value = output.get(field)
        checks.append(
            ValidationCheck(
                name="field_equals",
                passed=actual_value == expected_value,
                detail=f"{field}: esperado={expected_value!r}, actual={actual_value!r}",
            )
        )

    return checks


def check_field_in(
    output: dict[str, Any],
    expected_options: dict[str, list[Any]],
) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []

    for field, options in expected_options.items():
        actual_value = output.get(field)
        checks.append(
            ValidationCheck(
                name="field_in",
                passed=actual_value in options,
                detail=f"{field}: actual={actual_value!r}, opciones={options!r}",
            )
        )

    return checks


def validate_output(
    output: dict[str, Any],
    expected: dict[str, Any],
) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []

    checks.append(check_json_serializable(output))

    if "ok" in expected:
        checks.append(
            ValidationCheck(
                name="ok_expected",
                passed=output.get("ok") == expected["ok"],
                detail=f"ok esperado={expected['ok']!r}, actual={output.get('ok')!r}",
            )
        )

    checks.extend(
        check_must_include_keys(
            output=output,
            keys=expected.get("must_include_keys", []),
        )
    )

    checks.extend(
        check_field_equals(
            output=output,
            expected_values=expected.get("field_equals", {}),
        )
    )

    checks.extend(
        check_field_in(
            output=output,
            expected_options=expected.get("field_in", {}),
        )
    )

    return checks


def run_case(case: dict[str, Any]) -> ToolValidationResult:
    case_id = case["id"]
    tool_name = case["tool"]
    tool_input = case.get("input", {})
    expected = case.get("expected", {})

    if tool_name not in TOOL_IMPLEMENTATIONS:
        output = {
            "ok": False,
            "code": "unknown_tool",
            "error": f"Tool no registrada en el runner: {tool_name}",
            "external_side_effect": False,
        }

        return ToolValidationResult(
            case_id=case_id,
            tool=tool_name,
            passed=False,
            output=output,
            checks=[
                ValidationCheck(
                    name="tool_registered",
                    passed=False,
                    detail=f"La tool {tool_name} no está registrada en TOOL_IMPLEMENTATIONS.",
                )
            ],
        )

    implementation = TOOL_IMPLEMENTATIONS[tool_name]

    try:
        output = implementation(**tool_input)

        if not isinstance(output, dict):
            output = {
                "ok": False,
                "code": "invalid_output_type",
                "error": f"La tool devolvió {type(output).__name__}, se esperaba dict.",
                "external_side_effect": False,
            }

    except Exception as exc:
        output = {
            "ok": False,
            "code": "unhandled_exception",
            "error": f"Excepción no controlada: {type(exc).__name__}: {exc}",
            "external_side_effect": False,
        }

    checks = validate_output(output, expected)
    passed = all(check.passed for check in checks)

    return ToolValidationResult(
        case_id=case_id,
        tool=tool_name,
        passed=passed,
        output=output,
        checks=checks,
    )


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)

    cases = load_cases(CASES_PATH)
    results = [run_case(case) for case in cases]

    total = len(results)
    passed = sum(1 for result in results if result.passed)

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.case_id} | tool={result.tool}")

        if not result.passed:
            print("  Output:")
            print(f"  {json.dumps(result.output, ensure_ascii=False)}")
            print("  Checks fallidos:")

            for check in result.checks:
                if not check.passed:
                    print(f"   - {check.name}: {check.detail}")

    report = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "results": [
            {
                **asdict(result),
                "checks": [asdict(check) for check in result.checks],
            }
            for result in results
        ],
    }

    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("--- TOOL VALIDATION ---")
    print(f"Casos: {total}")
    print(f"Correctos: {passed}")
    print(f"Fallidos: {total - passed}")
    print(f"Pass rate: {passed / total:.1%}" if total else "Pass rate: n/a")
    print(f"Reporte: {REPORT_PATH}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()