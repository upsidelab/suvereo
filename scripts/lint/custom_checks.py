"""AST checks for conventions ruff has no rule for."""

import ast
from collections.abc import Iterator
from pathlib import Path

from violation import Violation

MAX_MODULE_LINES = 300
SERVER_APPS = {"account", "agent", "catalog", "pecl", "utils"}
SKIPPED_PARTS = {"tests", "migrations", ".venv", "node_modules"}


def python_files(root: Path, base: str) -> Iterator[Path]:
    for path in sorted((root / base).rglob("*.py")):
        relative = path.relative_to(root)
        if not SKIPPED_PARTS & set(relative.parts) and path.name != "conftest.py":
            yield relative


def plugin_packages(root: Path) -> set[str]:
    packages = {path.name for path in root.glob("plugins/*/suvereo_*") if path.is_dir()}
    packages |= {path.name for path in root.glob("plugins/*/src/suvereo_*") if path.is_dir()}
    return packages - {"suvereo_common"}


def imported_modules(tree: ast.Module) -> Iterator[tuple[int, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from ((node.lineno, alias.name.split(".")[0]) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.lineno, node.module.split(".")[0]


def check_server_module(path: Path, tree: ast.Module, plugins: set[str]) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(node) is not None:
                line = node.body[0].lineno
                yield Violation(path, line, "CV001", "Docstring in server code; only public interfaces have docstrings")
    for line, module in imported_modules(tree):
        if module in plugins:
            yield Violation(path, line, "CV003", f"Server imports the concrete plugin '{module}'; use suvereo-common")


def check_plugin_module(path: Path, tree: ast.Module) -> Iterator[Violation]:
    for line, module in imported_modules(tree):
        if module in SERVER_APPS:
            yield Violation(path, line, "CV004", f"Plugin imports the server app '{module}'; use suvereo-common")


def run_custom_checks(root: Path) -> list[Violation]:
    plugins = plugin_packages(root)
    violations = []
    for base in ("server", "plugins"):
        for path in python_files(root, base):
            source = (root / path).read_text()
            lines = source.count("\n") + 1
            if lines > MAX_MODULE_LINES:
                violations.append(
                    Violation(path, 1, "CV002", f"Module has {lines} lines; split it (max {MAX_MODULE_LINES})")
                )
            tree = ast.parse(source)
            if base == "server":
                violations += check_server_module(path, tree, plugins)
            else:
                violations += check_plugin_module(path, tree)
    return violations
