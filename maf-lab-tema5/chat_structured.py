import asyncio

from src.agents.support_agent import build_structured_support_agent
from src.contracts import SupportResponse, parse_support_response


def render_for_user(response: SupportResponse) -> str:
    lines: list[str] = []

    lines.append(response.message)

    if response.missing_fields:
        lines.append("\nDatos que faltan:")
        for field in response.missing_fields:
            lines.append(f"- {field}")

    if response.ticket_draft:
        draft = response.ticket_draft
        lines.append("\nBorrador de ticket:")
        lines.append(f"- Servicio: {draft.service}")
        lines.append(f"- Prioridad: {draft.priority}")
        lines.append(f"- Resumen: {draft.summary}")
        lines.append(f"- Impacto: {draft.impact}")
        lines.append(f"- Usuarios afectados: {draft.users_affected}")
        lines.append(
            f"- Requiere validación humana: "
            f"{'sí' if draft.requires_human_validation else 'no'}"
        )

    if response.next_action != "none":
        lines.append(f"\nSiguiente acción: {response.next_action}")

    return "\n".join(lines)


async def main() -> None:
    agent = build_structured_support_agent()

    print("Chat con respuestas estructuradas. Escribe 's' para salir.")

    while True:
        user_text = input("\nUsuario> ").strip()

        if user_text.lower() == "s":
            break

        raw_result = await agent.run(user_text)

        try:
            parsed = parse_support_response(str(raw_result))
        except ValueError as exc:
            print("\nAgente>")
            print("No he podido generar una respuesta con el formato esperado.")
            print(f"Detalle técnico: {exc}")
            continue

        print("\nAgente>")
        print(render_for_user(parsed))


if __name__ == "__main__":
    asyncio.run(main())