from __future__ import annotations

import argparse

from src.pipeline_governance.governance_checks import run_pipeline_governance_gate
from src.pipeline_governance.governance_report import (
    render_gate_markdown,
    save_gate_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env",
        choices=["dev", "test", "prod"],
        default="dev",
        help="Entorno objetivo del gate.",
    )
    args = parser.parse_args()

    result = run_pipeline_governance_gate(args.env)
    save_gate_outputs(result)

    print(render_gate_markdown(result))
    print("\nInformes generados:")
    print("- reports/pipeline_governance_report.md")
    print("- reports/pipeline_governance_report.json")

    if not result.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()