from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_VARIABLE_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


class PromptRenderError(RuntimeError):
    pass


def load_prompt_file(path: Path) -> str:
    if not path.exists():
        raise PromptRenderError(f"No existe el archivo de prompt: {path}")

    return path.read_text(encoding="utf-8")


def render_template(template: str, variables: dict[str, Any]) -> str:
    required_variables = set(_VARIABLE_PATTERN.findall(template))
    provided_variables = set(variables.keys())

    missing = required_variables - provided_variables

    if missing:
        missing_text = ", ".join(sorted(missing))
        raise PromptRenderError(
            f"Faltan variables para renderizar el prompt: {missing_text}"
        )

    def replace(match: re.Match[str]) -> str:
        variable_name = match.group(1)
        value = variables[variable_name]
        return str(value)

    return _VARIABLE_PATTERN.sub(replace, template)