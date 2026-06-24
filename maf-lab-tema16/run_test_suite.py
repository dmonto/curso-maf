from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


REPORTS_DIR = Path("reports")
SUITE_REPORT_PATH = REPORTS_DIR / "test_suite_report.json"

RUN_LLM_TESTS = os.getenv("RUN_LLM_TESTS", "0") == "1"
RUN_MODEL_COMPARISON = os.getenv("RUN_MODEL_COMPARISON", "0") == "1"
RUN_DRIFT_CHECK = os.getenv("RUN_DRIFT_CHECK", "1") == "1"
REQUIRE_BASELINE = os.getenv("REQUIRE_BASELINE", "0") == "1"

BASELINE_PATH = Path("baselines/quality_baseline.json")


@dataclass
class TestStep:
    name: str
    command: list[str]
    required: bool = True
    enabled: bool = True
    timeout_seconds: int = 300


@dataclass
class StepResult:
    name: str
    command: str
    status: str
    required: bool
    return_code: int | None
    duration_ms: int
    stdout: str
    stderr: str


def run_command(step: TestStep) -> StepResult:
    command_text = " ".join(step.command)

    if not step.enabled:
        return StepResult(
            name=step.name,
            command=command_text,
            status="SKIPPED",
            required=step.required,
            return_code=None,
            duration_ms=0,
            stdout="",
            stderr="",
        )

    start = time.perf_counter()

    try:
        completed = subprocess.run(
            step.command,
            capture_output=True,
            text=True,
            timeout=step.timeout_seconds,
            check=False,
        )

        duration_ms = int((time.perf_counter() - start) * 1000)

        status = "PASS" if completed.returncode == 0 else "FAIL"

        return StepResult(
            name=step.name,
            command=command_text,
            status=status,
            required=step.required,
            return_code=completed.returncode,
            duration_ms=duration_ms,
            stdout=completed.stdout[-5000:],
            stderr=completed.stderr[-5000:],
        )

    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)

        return StepResult(
            name=step.name,
            command=command_text,
            status="TIMEOUT",
            required=step.required,
            return_code=None,
            duration_ms=duration_ms,
            stdout=(exc.stdout or "")[-5000:] if isinstance(exc.stdout, str) else "",
            stderr=(exc.stderr or "")[-5000:] if isinstance(exc.stderr, str) else "",
        )


def build_steps() -> list[TestStep]:
    regression_enabled = RUN_LLM_TESTS and BASELINE_PATH.exists()

    if RUN_LLM_TESTS and REQUIRE_BASELINE and not BASELINE_PATH.exists():
        regression_enabled = True

    return [
        TestStep(
            name="compile_src",
            command=[sys.executable, "-m", "compileall", "src"],
            required=True,
            enabled=True,
            timeout_seconds=120,
        ),
        TestStep(
            name="validate_tools",
            command=[sys.executable, "check_tool_validation.py"],
            required=True,
            enabled=True,
            timeout_seconds=120,
        ),
        TestStep(
            name="quality_metrics",
            command=[sys.executable, "check_quality_metrics.py"],
            required=True,
            enabled=RUN_LLM_TESTS,
            timeout_seconds=600,
        ),
        TestStep(
            name="regression",
            command=[sys.executable, "check_regression.py"],
            required=REQUIRE_BASELINE,
            enabled=regression_enabled,
            timeout_seconds=300,
        ),
        TestStep(
            name="drift",
            command=[sys.executable, "check_drift.py"],
            required=False,
            enabled=RUN_LLM_TESTS and RUN_DRIFT_CHECK,
            timeout_seconds=300,
        ),
        TestStep(
            name="model_comparison",
            command=[sys.executable, "check_model_comparison.py"],
            required=True,
            enabled=RUN_MODEL_COMPARISON,
            timeout_seconds=1800,
        ),
    ]


def determine_suite_status(results: list[StepResult]) -> str:
    for result in results:
        if result.required and result.status in {"FAIL", "TIMEOUT"}:
            return "FAIL"

    return "PASS"


def print_result(result: StepResult) -> None:
    if result.status == "PASS":
        symbol = "PASS"
    elif result.status == "SKIPPED":
        symbol = "SKIP"
    else:
        symbol = "FAIL"

    print(f"[{symbol}] {result.name} ({result.duration_ms} ms)")

    if result.status in {"FAIL", "TIMEOUT"}:
        if result.stdout:
            print("  STDOUT:")
            print(result.stdout)

        if result.stderr:
            print("  STDERR:")
            print(result.stderr)


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)

    print("--- MAF TEST SUITE ---")
    print(f"RUN_LLM_TESTS={RUN_LLM_TESTS}")
    print(f"RUN_MODEL_COMPARISON={RUN_MODEL_COMPARISON}")
    print(f"RUN_DRIFT_CHECK={RUN_DRIFT_CHECK}")
    print(f"REQUIRE_BASELINE={REQUIRE_BASELINE}")
    print()

    steps = build_steps()
    results: list[StepResult] = []

    for step in steps:
        result = run_command(step)
        results.append(result)
        print_result(result)

    suite_status = determine_suite_status(results)

    report = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "suite_status": suite_status,
        "run_llm_tests": RUN_LLM_TESTS,
        "run_model_comparison": RUN_MODEL_COMPARISON,
        "run_drift_check": RUN_DRIFT_CHECK,
        "require_baseline": REQUIRE_BASELINE,
        "baseline_exists": BASELINE_PATH.exists(),
        "total_steps": len(results),
        "passed_steps": sum(1 for result in results if result.status == "PASS"),
        "failed_steps": sum(1 for result in results if result.status in {"FAIL", "TIMEOUT"}),
        "skipped_steps": sum(1 for result in results if result.status == "SKIPPED"),
        "results": [asdict(result) for result in results],
    }

    SUITE_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("--- RESULTADO FINAL ---")
    print(f"Estado suite: {suite_status}")
    print(f"Reporte: {SUITE_REPORT_PATH}")

    if suite_status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()