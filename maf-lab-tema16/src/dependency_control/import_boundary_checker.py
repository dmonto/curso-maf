from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

from src.dependency_control.dependency_policy import find_layer_rule


@dataclass(frozen=True)
class ImportViolation:
    file_path: str
    layer: str
    imported_module: str
    reason: str
    line_number: int


def is_stdlib_module(module_name: str) -> bool:
    root = module_name.split(".", maxsplit=1)[0]

    return root in sys.stdlib_module_names


def extract_imports(file_path: Path) -> list[tuple[str, int]]:
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))

    imports: list[tuple[str, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.module, node.lineno))

    return imports


def check_file(file_path: Path) -> list[ImportViolation]:
    rule = find_layer_rule(file_path)

    if rule is None:
        return []

    violations: list[ImportViolation] = []

    for imported_module, line_number in extract_imports(file_path):
        if is_stdlib_module(imported_module):
            continue

        for forbidden_prefix in rule.forbidden_internal_prefixes:
            if imported_module == forbidden_prefix or imported_module.startswith(
                forbidden_prefix + "."
            ):
                violations.append(
                    ImportViolation(
                        file_path=file_path.as_posix(),
                        layer=rule.name,
                        imported_module=imported_module,
                        reason=f"La capa {rule.name} no puede importar {forbidden_prefix}",
                        line_number=line_number,
                    )
                )

        external_root = imported_module.split(".", maxsplit=1)[0]

        for forbidden_external in rule.forbidden_external_roots:
            if external_root == forbidden_external:
                violations.append(
                    ImportViolation(
                        file_path=file_path.as_posix(),
                        layer=rule.name,
                        imported_module=imported_module,
                        reason=(
                            f"La capa {rule.name} no puede depender de "
                            f"{forbidden_external}"
                        ),
                        line_number=line_number,
                    )
                )

    return violations


def check_project(root: Path = Path("src")) -> list[ImportViolation]:
    violations: list[ImportViolation] = []

    for file_path in root.rglob("*.py"):
        if "__pycache__" in file_path.parts:
            continue

        violations.extend(check_file(file_path))

    return violations