from __future__ import annotations

from src.migration.prompt_migrator import migrate_prompt


def main() -> None:
    legacy_prompt = """
    Eres un agente de soporte IT de nivel 1.
    Clasifica la incidencia del usuario.
    Si es VPN, pregunta por sistema operativo.
    Si afecta a más de 10 usuarios, asigna prioridad alta.
    Usa la tool de tickets para preparar un borrador.
    No crees tickets reales sin confirmación.
    Devuelve JSON con categoria, prioridad y siguiente_accion.
    No reveles datos sensibles ni credenciales.
    Si falta información, pregunta antes de responder.
    Recuerda los pasos ya intentados en la sesión.
    Si hay riesgo de seguridad, deriva al agente de seguridad.
    Usa el procedimiento interno de VPN como referencia.
    """

    plan = migrate_prompt(
        legacy_prompt_name="support_triage_prompt",
        prompt_text=legacy_prompt,
    )

    print("\n--- FINDINGS ---")
    for finding in plan.findings:
        print(f"\nBloque: {finding.block}")
        print(f"Texto: {finding.text}")
        print(f"Destino MAF: {finding.target_maf_component}")
        print(f"Motivo: {finding.reason}")

    print("\n--- INSTRUCTIONS PROPUESTAS ---")
    print(plan.recommended_instructions)

    print("\n--- FICHEROS A CREAR ---")
    for file in plan.files_to_create:
        print(f"- {file}")

    print("\n--- RIESGOS ---")
    for risk in plan.risks:
        print(f"- {risk}")


if __name__ == "__main__":
    main()