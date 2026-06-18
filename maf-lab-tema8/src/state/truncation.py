from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class TruncationStrategy(StrEnum):
    NONE = "none"
    HEAD = "head"
    TAIL = "tail"
    MIDDLE = "middle"
    JSON_FIELDS = "json_fields"


def estimate_tokens(text: str) -> int:
    """
    Estimación simple para laboratorio.

    Aproximamos 1 token cada 4 caracteres.
    Para producción conviene usar un tokenizador específico del modelo.
    """
    return max(1, len(text) // 4)


def truncate_tail(text: str, max_chars: int) -> str:
    """
    Conserva el inicio y corta el final.
    Útil para textos donde la introducción es más importante.
    """
    if len(text) <= max_chars:
        return text

    return text[:max_chars].rstrip() + "\n...[truncado al final]"


def truncate_head(text: str, max_chars: int) -> str:
    """
    Conserva el final y corta el inicio.
    Útil para logs donde lo último suele ser más relevante.
    """
    if len(text) <= max_chars:
        return text

    return "[truncado al inicio]...\n" + text[-max_chars:].lstrip()


def truncate_middle(text: str, max_chars: int) -> str:
    """
    Conserva principio y final.
    Útil para logs, trazas, errores y resultados técnicos.
    """
    if len(text) <= max_chars:
        return text

    if max_chars < 200:
        return truncate_tail(text, max_chars)

    head_size = int(max_chars * 0.55)
    tail_size = max_chars - head_size

    head = text[:head_size].rstrip()
    tail = text[-tail_size:].lstrip()

    return (
        head
        + "\n\n...[contenido intermedio truncado]...\n\n"
        + tail
    )


def truncate_json_fields(text: str, max_chars: int) -> str:
    """
    Intenta compactar JSON eliminando campos vacíos o demasiado largos.
    Si no es JSON válido, aplica middle truncation.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return truncate_middle(text, max_chars)

    compacted = _compact_json_value(data)
    rendered = json.dumps(compacted, ensure_ascii=False, indent=2)

    if len(rendered) <= max_chars:
        return rendered

    return truncate_middle(rendered, max_chars)


def _compact_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}

        for key, item in value.items():
            if item is None:
                continue

            if item == "":
                continue

            result[key] = _compact_json_value(item)

        return result

    if isinstance(value, list):
        if len(value) <= 8:
            return [_compact_json_value(item) for item in value]

        return {
            "items_iniciales": [_compact_json_value(item) for item in value[:4]],
            "items_finales": [_compact_json_value(item) for item in value[-2:]],
            "total_items_original": len(value),
            "truncado": True,
        }

    if isinstance(value, str):
        if len(value) > 800:
            return truncate_middle(value, 800)

        return value

    return value


@dataclass(frozen=True)
class ContextBlock:
    name: str
    content: str
    priority: int
    strategy: TruncationStrategy
    min_chars: int = 500
    max_chars: int = 4000
    required: bool = False

    def token_estimate(self) -> int:
        return estimate_tokens(self.content)


@dataclass
class TruncatedContext:
    content: str
    original_tokens: int
    final_tokens: int
    truncated_blocks: list[str]

    def report(self) -> dict:
        return {
            "original_tokens": self.original_tokens,
            "final_tokens": self.final_tokens,
            "tokens_saved": self.original_tokens - self.final_tokens,
            "truncated_blocks": self.truncated_blocks,
        }


class ContextTruncator:
    """
    Aplica truncado por bloques.

    Reglas:
    - Los bloques required no se eliminan.
    - Los bloques de mayor prioridad se preservan más.
    - Los bloques menos prioritarios se recortan antes.
    """

    def __init__(
        self,
        max_context_tokens: int,
        response_margin_tokens: int = 1000,
    ) -> None:
        if max_context_tokens <= 0:
            raise ValueError("max_context_tokens debe ser positivo")

        if response_margin_tokens < 0:
            raise ValueError("response_margin_tokens no puede ser negativo")

        self.max_context_tokens = max_context_tokens
        self.response_margin_tokens = response_margin_tokens
        self.available_tokens = max_context_tokens - response_margin_tokens

        if self.available_tokens <= 0:
            raise ValueError("El margen de respuesta deja el presupuesto sin espacio")

    def truncate(self, blocks: list[ContextBlock]) -> TruncatedContext:
        original_text = self._render_blocks(blocks)
        original_tokens = estimate_tokens(original_text)

        if original_tokens <= self.available_tokens:
            return TruncatedContext(
                content=original_text,
                original_tokens=original_tokens,
                final_tokens=original_tokens,
                truncated_blocks=[],
            )

        sorted_blocks = sorted(
            blocks,
            key=lambda block: block.priority,
            reverse=True,
        )

        truncated_blocks: list[str] = []
        rendered_parts: list[str] = []

        remaining_chars = self.available_tokens * 4

        total_priority = sum(max(1, block.priority) for block in sorted_blocks)

        for block in sorted_blocks:
            block_budget = int(
                remaining_chars * (max(1, block.priority) / total_priority)
            )

            if block.required:
                block_budget = max(block_budget, min(len(block.content), block.max_chars))

            block_budget = max(block.min_chars, block_budget)
            block_budget = min(block_budget, block.max_chars)

            final_content = self._apply_strategy(
                block=block,
                max_chars=block_budget,
            )

            if final_content != block.content:
                truncated_blocks.append(block.name)

            rendered_parts.append(
                self._render_block(
                    name=block.name,
                    content=final_content,
                )
            )

        final_text = "\n\n".join(rendered_parts)
        final_tokens = estimate_tokens(final_text)

        # Segunda pasada defensiva: si sigue siendo demasiado grande,
        # recortamos bloques no requeridos empezando por menor prioridad.
        if final_tokens > self.available_tokens:
            final_text, second_pass_blocks = self._second_pass(
                blocks=sorted_blocks,
                current_text=final_text,
            )
            truncated_blocks.extend(second_pass_blocks)
            final_tokens = estimate_tokens(final_text)

        return TruncatedContext(
            content=final_text,
            original_tokens=original_tokens,
            final_tokens=final_tokens,
            truncated_blocks=sorted(set(truncated_blocks)),
        )

    def _apply_strategy(
        self,
        block: ContextBlock,
        max_chars: int,
    ) -> str:
        if len(block.content) <= max_chars:
            return block.content

        if block.strategy == TruncationStrategy.NONE:
            if block.required:
                return block.content
            return truncate_tail(block.content, max_chars)

        if block.strategy == TruncationStrategy.HEAD:
            return truncate_head(block.content, max_chars)

        if block.strategy == TruncationStrategy.TAIL:
            return truncate_tail(block.content, max_chars)

        if block.strategy == TruncationStrategy.MIDDLE:
            return truncate_middle(block.content, max_chars)

        if block.strategy == TruncationStrategy.JSON_FIELDS:
            return truncate_json_fields(block.content, max_chars)

        return truncate_middle(block.content, max_chars)

    def _second_pass(
        self,
        blocks: list[ContextBlock],
        current_text: str,
    ) -> tuple[str, list[str]]:
        truncated: list[str] = []
        parts: list[str] = []

        remaining_blocks = sorted(
            blocks,
            key=lambda block: block.priority,
            reverse=True,
        )

        for block in remaining_blocks:
            if block.required:
                content = block.content
            else:
                content = self._apply_strategy(
                    block=block,
                    max_chars=block.min_chars,
                )
                truncated.append(block.name)

            parts.append(self._render_block(block.name, content))

        final_text = "\n\n".join(parts)

        if estimate_tokens(final_text) <= self.available_tokens:
            return final_text, truncated

        # Última defensa: conservar required completos y reducir el resto al mínimo.
        defensive_parts: list[str] = []

        for block in remaining_blocks:
            if block.required:
                content = block.content
            else:
                content = self._apply_strategy(
                    block=block,
                    max_chars=max(200, block.min_chars // 2),
                )
                truncated.append(block.name)

            defensive_parts.append(self._render_block(block.name, content))

        return "\n\n".join(defensive_parts), truncated

    def _render_blocks(self, blocks: list[ContextBlock]) -> str:
        ordered = sorted(
            blocks,
            key=lambda block: block.priority,
            reverse=True,
        )

        return "\n\n".join(
            self._render_block(block.name, block.content)
            for block in ordered
        )

    def _render_block(self, name: str, content: str) -> str:
        return f"### {name}\n{content}"