"""AST import-boundary guard for the benchmark_harness package.

Operator discipline #13: benchmark_harness production modules
MUST NOT import legacy portrait HTTP endpoints, MediaEngineClient,
Django identity models/services, scoring code, or bootstrap
review code. Allowed dependencies: PortraitProvider,
NormalizationPipeline/config loaders, stdlib, and
jsonschema/yaml.

If a Step 9 module ever gets built inside media-engine, this
test's forbidden list catches accidental import backflow into
Step 8's boundary.
"""
from __future__ import annotations

import ast
import pathlib


_HARNESS_ROOT = (
    pathlib.Path(__file__).resolve().parents[2]
    / "app" / "services" / "benchmark_harness"
)

# Modules exempt from the guard — none currently. Tests + this
# guard live under ``tests/benchmark_harness/`` and are outside
# ``_HARNESS_ROOT``.


# Forbidden module-prefix substrings. If any of these appears in
# an import path within the harness package, the test fails.
_FORBIDDEN_IMPORT_SUBSTRINGS: tuple[str, ...] = (
    # Legacy direct portrait / image services.
    "app.services.character_studio_client",
    "app.services.stability_ai_service",
    "app.services.stability_portrait",
    "app.services.runway_client",
    "app.services.image_stability",
    # MediaEngineClient (Django-side HTTP client shim).
    "app.clients.media_engine_client",
    "media_engine_client",
    # Django-side identity substrate.
    "apps.identity",
    "shell.apps.identity",
    "django",
    # Scoring / bootstrap review code (Step 9/10 territory —
    # doesn't exist yet, but if it lands, it MUST NOT import
    # back into 8.b).
    "app.services.scoring",
    "app.services.bootstrap_review",
    # Media-engine internal endpoints that would collapse the
    # provider-abstraction boundary.
    "app.routers.internal",
)


def _iter_harness_modules() -> list[pathlib.Path]:
    return sorted(_HARNESS_ROOT.rglob("*.py"))


def _absolute_imports(path: pathlib.Path) -> set[str]:
    """Absolute-import module paths only (used by the forbidden-
    module scan). Relative imports resolve to the harness package
    itself and are always allowed."""
    tree = ast.parse(path.read_bytes())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None and node.level == 0:
                names.add(node.module)
    return names


def _relative_import_modules(path: pathlib.Path) -> set[str]:
    """Relative-import target module names — captured so the
    positive whitelist can prove the harness uses the ratified
    abstractions even when it reaches them via ``..portrait_provider``
    style imports."""
    tree = ast.parse(path.read_bytes())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level > 0 and node.module is not None:
                names.add(node.module)
    return names


def test_no_harness_module_imports_forbidden_module_paths() -> None:
    offenders: list[tuple[str, str]] = []
    for py in _iter_harness_modules():
        for imp in _absolute_imports(py):
            for forbidden in _FORBIDDEN_IMPORT_SUBSTRINGS:
                if imp == forbidden or imp.startswith(forbidden + "."):
                    offenders.append((str(py.relative_to(_HARNESS_ROOT)), imp))
    assert offenders == [], (
        f"benchmark_harness production modules import forbidden paths — "
        f"boundary violation per SESSION 247 operator discipline #13: "
        f"{offenders}"
    )


def test_harness_only_imports_allowed_third_party_packages() -> None:
    """Every third-party (non-stdlib, non-local) import in the
    harness must be in the whitelist. Guards against a future
    session pulling in a new dep without noticing."""
    allowed_third_party: set[str] = {
        "yaml",             # PyYAML — schema loader
        "jsonschema",       # fixture schema validation
    }
    # Standard-lib prefixes to exclude when scanning.
    stdlib_prefixes = (
        "os", "sys", "io", "json", "hashlib", "pathlib", "typing",
        "dataclasses", "enum", "collections", "datetime", "time",
        "argparse", "inspect", "tempfile", "shutil", "ast",
        "re", "functools", "itertools", "contextlib", "logging",
        "__future__",
    )
    # Own-package prefixes.
    own = ("app.",)

    seen_third_party: set[str] = set()
    for py in _iter_harness_modules():
        for imp in _absolute_imports(py):
            root = imp.split(".")[0]
            if root in stdlib_prefixes:
                continue
            if imp.startswith(own):
                continue
            if root == "__future__":
                continue
            seen_third_party.add(root)

    unexpected = seen_third_party - allowed_third_party
    assert unexpected == set(), (
        f"benchmark_harness imports unexpected third-party packages: "
        f"{unexpected}. If a new dependency is legitimate, add it to "
        f"``allowed_third_party`` in this test AND to "
        f"media-engine/requirements.txt in the same commit."
    )


def test_harness_import_of_portrait_provider_is_explicit() -> None:
    """Positive whitelist: the harness DOES import from the
    ratified provider package + normalization package. Failing
    this test would mean the harness has stopped using the
    ratified abstractions — a scope regression.

    Scans both absolute and relative import forms — the harness's
    intra-media-engine imports are typically the ``..portrait_provider``
    dotted-relative shape."""
    portrait_provider_seen = False
    normalization_seen = False
    for py in _iter_harness_modules():
        for imp in _absolute_imports(py) | _relative_import_modules(py):
            if "portrait_provider" in imp:
                portrait_provider_seen = True
            if "normalization" in imp:
                normalization_seen = True
    assert portrait_provider_seen, (
        "no harness module imports from app.services.portrait_provider — "
        "the ratified abstraction boundary is unused"
    )
    assert normalization_seen, (
        "no harness module imports from app.services.normalization — "
        "the ratified normalization pipeline is unused"
    )
