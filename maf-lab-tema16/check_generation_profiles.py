from src.models.azure_openai_runner import run_chat_completion
from src.models.generation_profiles import GENERATION_PROFILES


SYSTEM_PROMPT = """
Eres un agente de soporte técnico L1.

Debes ayudar con incidencias básicas de VPN, correo, Teams y ERP.
No creas tickets reales.
Si faltan datos, pide aclaración.
No inventes datos operativos.
"""


USER_PROMPT = """
La VPN va lenta desde casa y afecta a 3 usuarios.
Queremos tratarlo como p2.
Redacta una respuesta para el usuario indicando qué sabes, qué falta y cuál es el siguiente paso.
"""


def main() -> None:
    for profile_name, profile in GENERATION_PROFILES.items():
        print("\n" + "=" * 90)
        print(f"PERFIL: {profile_name}")
        print(f"DESCRIPCIÓN: {profile.description}")
        print(
            "PARAMS:",
            {
                "temperature": profile.temperature,
                "top_p": profile.top_p,
                "max_tokens": profile.max_tokens,
                "frequency_penalty": profile.frequency_penalty,
                "presence_penalty": profile.presence_penalty,
            },
        )
        print("-" * 90)

        output = run_chat_completion(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_PROMPT,
            profile=profile,
        )

        print(output)


if __name__ == "__main__":
    main()