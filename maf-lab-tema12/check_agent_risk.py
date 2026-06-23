from __future__ import annotations

from pathlib import Path

from src.risk.risk_model import RiskAssessment
from src.risk.risk_report import render_markdown_report, save_assessment_json, save_markdown_report
from src.risk.risk_rules import evaluate_architecture_risks, load_agent_risk_profile


def main() -> None:
    profile_path = Path("config/agent_risk_profile.json")
    profile = load_agent_risk_profile(profile_path)

    findings = evaluate_architecture_risks(profile)

    assessment = RiskAssessment(
        agent_name=profile["agent_name"],
        environment=profile["environment"],
        findings=findings,
    )

    report = render_markdown_report(assessment)

    save_markdown_report(report, Path("reports/agent_risk_assessment.md"))
    save_assessment_json(assessment, Path("reports/agent_risk_assessment.json"))

    print(report)
    print("\nInformes generados:")
    print("- reports/agent_risk_assessment.md")
    print("- reports/agent_risk_assessment.json")


if __name__ == "__main__":
    main()