from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal


Role = Literal["user", "assistant", "tool", "system"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def estimate_tokens(text: str) -> int:
    """
    Estimación simple para laboratorio.

    No sustituye a un tokenizador real, pero sirve para tener una señal
    aproximada de crecimiento del contexto.
    """
    return max(1, len(text) // 4)


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text

    return text[:max_chars].rstrip() + "\n...[truncado]"


@dataclass
class ConversationTurn:
    role: Role
    content: str
    created_utc: str = field(default_factory=utc_now)

    def compact(self, max_chars: int = 800) -> dict:
        return {
            "role": self.role,
            "created_utc": self.created_utc,
            "content": truncate_text(self.content, max_chars),
        }


@dataclass
class LongContextState:
    rolling_summary: str = ""
    recent_turns: list[ConversationTurn] = field(default_factory=list)
    total_turns: int = 0
    compactions: int = 0

    def to_dict(self) -> dict:
        return {
            "rolling_summary": self.rolling_summary,
            "recent_turns": [asdict(turn) for turn in self.recent_turns],
            "total_turns": self.total_turns,
            "compactions": self.compactions,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class LongContextManager:
    """
    Gestiona contexto largo combinando:
    - resumen acumulado;
    - últimos turnos;
    - estimación de tamaño;
    - compactación de turnos antiguos.
    """

    def __init__(
        self,
        max_recent_turns: int = 8,
        max_context_chars: int = 6000,
    ) -> None:
        self.max_recent_turns = max_recent_turns
        self.max_context_chars = max_context_chars
        self.state = LongContextState()

    def add_turn(self, role: Role, content: str) -> None:
        self.state.recent_turns.append(
            ConversationTurn(
                role=role,
                content=content,
            )
        )
        self.state.total_turns += 1

    def current_context_size_chars(self) -> int:
        return len(self.build_recent_turns_block()) + len(self.state.rolling_summary)

    def current_context_size_tokens_estimate(self) -> int:
        return estimate_tokens(
            self.state.rolling_summary + "\n" + self.build_recent_turns_block()
        )

    def needs_compaction(self) -> bool:
        if len(self.state.recent_turns) > self.max_recent_turns:
            return True

        if self.current_context_size_chars() > self.max_context_chars:
            return True

        return False

    def split_turns_for_compaction(self) -> tuple[list[ConversationTurn], list[ConversationTurn]]:
        """
        Compacta los turnos antiguos y conserva los últimos N.
        """
        if len(self.state.recent_turns) <= self.max_recent_turns:
            return [], self.state.recent_turns

        keep = self.state.recent_turns[-self.max_recent_turns:]
        compact = self.state.recent_turns[:-self.max_recent_turns]

        return compact, keep

    def build_recent_turns_block(self) -> str:
        compact_turns = [
            turn.compact(max_chars=900)
            for turn in self.state.recent_turns
        ]

        return json.dumps(compact_turns, ensure_ascii=False, indent=2)

    def build_compaction_prompt(self, turns_to_compact: list[ConversationTurn]) -> str:
        turns_json = json.dumps(
            [turn.compact(max_chars=1200) for turn in turns_to_compact],
            ensure_ascii=False,
            indent=2,
        )

        previous_summary = self.state.rolling_summary or "No hay resumen previo."

        return f"""
Actualiza el resumen acumulado de una conversación de soporte técnico.

Objetivo:
- conservar decisiones, datos del caso, pasos probados, errores, prioridades y pendientes;
- eliminar saludos, repeticiones y texto irrelevante;
- no inventar datos;
- mantener un resumen breve y operativo.

RESUMEN PREVIO:
{previous_summary}

TURNOS ANTIGUOS A COMPACTAR:
{turns_json}

Devuelve solo el nuevo resumen actualizado.
""".strip()

    def apply_compaction(
        self,
        new_summary: str,
        kept_turns: list[ConversationTurn],
    ) -> None:
        self.state.rolling_summary = new_summary.strip()
        self.state.recent_turns = kept_turns
        self.state.compactions += 1

    def build_context_package(self, memory_json: str) -> str:
        """
        Construye el bloque que se enviará al agente en el turno actual.
        """
        package = {
            "memoria_estructurada": json.loads(memory_json),
            "resumen_acumulado": self.state.rolling_summary,
            "ultimos_turnos": [
                turn.compact(max_chars=900)
                for turn in self.state.recent_turns
            ],
            "estadisticas_contexto": {
                "total_turnos": self.state.total_turns,
                "compactaciones": self.state.compactions,
                "tokens_estimados": self.current_context_size_tokens_estimate(),
            },
        }

        return json.dumps(package, ensure_ascii=False, indent=2)

    def stats(self) -> dict:
        return {
            "total_turns": self.state.total_turns,
            "recent_turns": len(self.state.recent_turns),
            "compactions": self.state.compactions,
            "context_chars": self.current_context_size_chars(),
            "estimated_tokens": self.current_context_size_tokens_estimate(),
            "has_summary": bool(self.state.rolling_summary),
        }