from __future__ import annotations

from src.compliance.compliance_loader import (
    load_agent_profile,
    load_compliance_requirements,
)
from src.compliance.compliance_report import (
    evaluate_compliance,
    render_compliance_markdown,
    save_compliance_outputs,
)


def main() -> None:
    framework, version, requirements = load_compliance_requirements()
    profile = load_agent_profile()

    # Marcamos si existe informe de riesgo previo.
    profile["has_risk_assessment"] = True

    assessment = evaluate_compliance(
        framework=framework,
        version=version,
        requirements=requirements,
        profile=profile,
    )

    save_compliance_outputs(assessment)

    print(render_compliance_markdown(assessment))
    print("\nInformes generados:")
    print("- reports/compliance_report.md")
    print("- reports/compliance_report.json")

    if assessment.blocking_findings:
        print("\nHay hallazgos bloqueantes. Revisa controles y evidencias pendientes.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()