from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2] / "src" / "careerpilot"

_FORBIDDEN_DOMAIN = {
    "sqlalchemy",
    "fastapi",
    "temporalio",
    "asyncpg",
    "alembic",
    "psycopg",
    "careerpilot.infrastructure",
    "careerpilot.config",
}

_FORBIDDEN_APPLICATION = {
    "sqlalchemy",
    "fastapi",
    "temporalio",
    "asyncpg",
    "alembic",
    "psycopg",
    "careerpilot.infrastructure",
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
            names.add(node.module)
    return names


def _python_files(package: str) -> list[Path]:
    return sorted((_ROOT / package).rglob("*.py"))


def test_domain_does_not_import_infrastructure_or_frameworks() -> None:
    violations: list[str] = []
    for path in _python_files("domain"):
        imported = _imported_modules(path)
        for banned in _FORBIDDEN_DOMAIN:
            if banned in imported or any(
                item == banned or item.startswith(banned + ".") for item in imported
            ):
                violations.append(f"{path.relative_to(_ROOT)} imports {banned}")
    assert violations == []


def test_application_does_not_import_infrastructure_or_frameworks() -> None:
    violations: list[str] = []
    for path in _python_files("application"):
        imported = _imported_modules(path)
        for banned in _FORBIDDEN_APPLICATION:
            if banned in imported or any(
                item == banned or item.startswith(banned + ".") for item in imported
            ):
                violations.append(f"{path.relative_to(_ROOT)} imports {banned}")
    assert violations == []


def test_domain_and_application_do_not_mention_adzuna() -> None:
    hits: list[str] = []
    for package in ("domain", "application", "ports"):
        for path in _python_files(package):
            text = path.read_text(encoding="utf-8")
            if "adzuna" in text.lower():
                hits.append(str(path.relative_to(_ROOT)))
    assert hits == []
