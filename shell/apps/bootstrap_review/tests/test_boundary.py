"""AST-level import boundary for §19 Step 9.b (SESSION 249, 9.b.0).

Enforces the mechanical lock described in the SESSION 249
architecture plan §Q28:

    9.b code must never regenerate evidence. The frozen 9.a run
    ``bootstrap_20260808T044853Z_7eb392992e0f`` is the sole input.

The bootstrap-review app therefore MUST NOT import:

* ``app.services.portrait_provider.*`` — media-engine provider
  namespace. Django cannot import media-engine at runtime anyway;
  the AST scan makes the intent explicit + catches accidental
  cross-service coupling before it lands.
* ``app.services.benchmark_harness.*`` — the SESSION 247 harness.
  Bootstrap review consumes its output, does not re-invoke it.
* ``MediaEngineClient`` (any casing / any module path) — the
  Django-side client to the media-engine HTTP surface. 9.b never
  needs to speak to media-engine.

Also forbids naming ``runway_still_portrait`` or ``stability_still``
as a Python symbol (import target or bare name binding) — those
belong to the provider vocabulary that only the frozen evidence
carries.

Scope: this test walks every ``*.py`` under
``shell/apps/bootstrap_review/`` (including this file's siblings,
migrations, and future 9.b.1+ additions). If a legitimate future
need for one of these symbols arises, this test is the correct
place to add a scoped allow-list — never a silent pattern-based
carve-out.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_IMPORT_PREFIXES = (
    "app.services.portrait_provider",
    "app.services.benchmark_harness",
)
FORBIDDEN_NAME_SUBSTRINGS = ("MediaEngineClient",)
FORBIDDEN_BARE_NAMES = ("runway_still_portrait", "stability_still")


def _walk_python_files() -> list[Path]:
    return sorted(p for p in APP_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


@pytest.mark.parametrize("path", _walk_python_files(), ids=lambda p: str(p.relative_to(APP_ROOT)))
def test_no_forbidden_imports(path: Path) -> None:
    """Every module under ``apps.bootstrap_review`` must be free of
    the imports enumerated in this module's docstring.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for prefix in FORBIDDEN_IMPORT_PREFIXES:
                assert not module.startswith(prefix), (
                    f"Forbidden import in {path}: "
                    f"from {module} import ... — §Q28 boundary lock."
                )
            for alias in node.names:
                for forbidden in FORBIDDEN_NAME_SUBSTRINGS:
                    assert forbidden not in alias.name, (
                        f"Forbidden import in {path}: "
                        f"from {module} import {alias.name} — §Q28 boundary lock."
                    )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                for prefix in FORBIDDEN_IMPORT_PREFIXES:
                    assert not alias.name.startswith(prefix), (
                        f"Forbidden import in {path}: "
                        f"import {alias.name} — §Q28 boundary lock."
                    )
                for forbidden in FORBIDDEN_NAME_SUBSTRINGS:
                    assert forbidden not in alias.name, (
                        f"Forbidden import in {path}: "
                        f"import {alias.name} — §Q28 boundary lock."
                    )


@pytest.mark.parametrize("path", _walk_python_files(), ids=lambda p: str(p.relative_to(APP_ROOT)))
def test_no_forbidden_bare_names(path: Path) -> None:
    """No provider vocabulary appears as a bare Python name binding.

    Provider names live only in frozen evidence JSON strings, never
    as Python symbols in 9.b code.
    """
    source = path.read_text(encoding="utf-8")
    # Skip this test file itself — we legitimately name the
    # forbidden strings in the constants above.
    if path.samefile(Path(__file__)):
        pytest.skip("boundary test module legitimately names the forbidden strings")
    tree = ast.parse(source, filename=str(path))

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            for forbidden in FORBIDDEN_BARE_NAMES:
                assert node.id != forbidden, (
                    f"Forbidden bare name in {path} at line {node.lineno}: "
                    f"{node.id!r} — §Q28 boundary lock. Provider vocabulary "
                    "lives in evidence JSON, not in Python symbols."
                )
