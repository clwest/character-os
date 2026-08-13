"""R10 — multi-provider drift verifier (last R slice).

Verifies the realtime provider abstraction (R2's
``RealtimeProvider`` Protocol) stays honored as the
registry grows. Two ways this can drift over time:

1. **A future Protocol method lands without a
   Runway implementation.** Someone adds
   ``rotate_session_key`` (say) to the Protocol because
   the spec evolved; Runway gets a real impl, but the
   mock provider doesn't get updated. The mock provider
   silently becomes broken in tests using mock-mode.

2. **A future provider lands missing methods.** Someone
   adds a Synthesia adapter; v1 of the file forgets
   `end_session`. Sessions never tear down cleanly;
   regression caught only when real Synthesia traffic
   hits production.

Both classes of drift are catchable by introspection
against the Protocol. The test runs on every CI / local
test pass; new methods + new providers both trip it.

R10 is small — one test file, no new code. It's the last
R slice. After this lands, the realtime arc is closed.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from app.config import Settings
from app.services.realtime_provider import (
    RealtimeProvider,
    get_provider,
)
from app.services.realtime_provider.mock import MockRealtimeProvider
from app.services.realtime_provider.runway import RunwayRealtimeProvider


# Methods the Protocol declares (scope-lock §"Provider
# abstraction" + R2's `__init__.py`). Order matters only
# for the failure message; the assertions don't depend on
# it.
PROTOCOL_METHODS = (
    "create_session",
    "poll_session",
    "attach_documents",
    "create_document",
    "fetch_transcript",
    "end_session",
)


def _provider_classes() -> list[type]:
    """The concrete provider classes the test discovers
    by inspecting the package. Adding a future provider
    (Synthesia, HeyGen, etc.) just adds an import + a row
    to this list; the test then verifies the new provider
    automatically.
    """
    return [MockRealtimeProvider, RunwayRealtimeProvider]


# ---- Protocol surface ------------------------------------------


def test_protocol_methods_match_expected_set():
    """The PROTOCOL_METHODS constant in this test mirrors
    the Protocol. If someone adds (or removes) a method on
    the Protocol, this test fails until the constant is
    updated — which is itself an audit event (the new
    method needs implementations everywhere).
    """
    # Pull public method names from the Protocol class.
    proto_methods = {
        name
        for name in dir(RealtimeProvider)
        if not name.startswith("_") and callable(getattr(RealtimeProvider, name))
    }
    expected = set(PROTOCOL_METHODS)
    assert proto_methods == expected, (
        f"Protocol method set drifted from PROTOCOL_METHODS.\n"
        f"  On Protocol: {sorted(proto_methods)}\n"
        f"  In test:     {sorted(expected)}\n"
        f"  Missing from test: {sorted(proto_methods - expected)}\n"
        f"  Extra in test:     {sorted(expected - proto_methods)}\n"
        f"If you added a Protocol method, update PROTOCOL_METHODS in "
        f"this test AND verify every concrete provider implements it."
    )


# ---- Per-provider completeness ---------------------------------


@pytest.mark.parametrize("provider_cls", _provider_classes())
def test_provider_implements_every_protocol_method(provider_cls: type):
    """Each concrete provider must define every Protocol
    method as an attribute. A new provider that forgets
    `end_session` (say) fails here loudly."""
    missing = [
        name for name in PROTOCOL_METHODS
        if not hasattr(provider_cls, name)
        or not callable(getattr(provider_cls, name))
    ]
    assert missing == [], (
        f"{provider_cls.__name__} is missing Protocol method(s): "
        f"{missing}. Every concrete provider must implement every "
        f"method in RealtimeProvider."
    )


@pytest.mark.parametrize("provider_cls", _provider_classes())
def test_provider_methods_are_not_notimplemented_stubs(provider_cls: type):
    """Each Protocol method's implementation must have a
    body — not a bare `raise NotImplementedError` stub.

    Caught via AST analysis: parse the source of each
    method + reject the case where the body is exactly
    one statement and that statement is
    `raise NotImplementedError(...)`. Methods with real
    work that happens to ALSO raise NotImplementedError
    deep in a branch are fine.

    This caught a real drift class at R3/R4/R5 — early R2
    shipped 4 methods as NotImplementedError stubs on
    Runway; the test would have fired on every subsequent
    slice until the stubs were filled in. (In practice the
    R2 test suite hand-asserted the stubs; this test
    generalises so a future stub-and-forget is caught
    automatically.)
    """
    stubs: list[str] = []
    for name in PROTOCOL_METHODS:
        method = getattr(provider_cls, name)
        if _method_is_notimplemented_stub(method):
            stubs.append(name)
    assert stubs == [], (
        f"{provider_cls.__name__} method(s) {stubs} are bare "
        f"`raise NotImplementedError` stubs. If a method is "
        f"deferred to a future slice, that's fine for an in-flight "
        f"WIP — but R10 (closing slice) requires every Protocol "
        f"method on every concrete provider to be fully implemented."
    )


def _method_is_notimplemented_stub(method) -> bool:
    """True if the method's body is exactly
    ``raise NotImplementedError(...)`` (possibly preceded
    by a docstring). False for any method with real logic.
    """
    try:
        source = inspect.getsource(method)
    except (OSError, TypeError):
        # Built-in / C-extension methods — assume real
        # impl. Won't happen for Python class methods but
        # be defensive.
        return False
    # `getsource` returns the method with indentation
    # matching its position in the file. ast.parse needs
    # dedented source.
    source = inspect.cleandoc(source)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    # The parse tree's root is a Module with one FunctionDef
    # (or AsyncFunctionDef) at the top.
    if not tree.body or not isinstance(
        tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef),
    ):
        return False
    fn_body = tree.body[0].body
    # Strip leading docstring if present.
    if (
        fn_body
        and isinstance(fn_body[0], ast.Expr)
        and isinstance(fn_body[0].value, ast.Constant)
        and isinstance(fn_body[0].value.value, str)
    ):
        fn_body = fn_body[1:]
    # Pure stub: exactly one statement, a `raise
    # NotImplementedError(...)`.
    if len(fn_body) != 1:
        return False
    stmt = fn_body[0]
    if not isinstance(stmt, ast.Raise):
        return False
    exc = stmt.exc
    # `raise NotImplementedError` (bare class)
    if isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
        return True
    # `raise NotImplementedError("msg")`
    if (
        isinstance(exc, ast.Call)
        and isinstance(exc.func, ast.Name)
        and exc.func.id == "NotImplementedError"
    ):
        return True
    return False


# ---- Registry behaviour ----------------------------------------


def test_get_provider_returns_runway_for_known_name():
    """``get_provider('runway', settings)`` returns the
    Runway impl when ``runway_mock`` is False (real key
    present)."""
    settings = Settings(runway_api_key="sk-fake-for-test")
    assert settings.runway_mock is False  # sanity
    provider = get_provider("runway", settings)
    assert isinstance(provider, RunwayRealtimeProvider)


def test_get_provider_returns_mock_when_runway_mock_is_true():
    """Mock-mode (empty `runway_api_key` →
    `runway_mock=True`) forces the deterministic mock
    regardless of the name arg. This is contract rule 9's
    enforcement point."""
    settings = Settings(runway_api_key="")
    assert settings.runway_mock is True  # sanity
    provider = get_provider("runway", settings)
    assert isinstance(provider, MockRealtimeProvider)


def test_get_provider_raises_for_unknown_name():
    """Unknown provider names raise — fail-fast on
    misconfigured workspace."""
    from app.services.realtime_provider import RealtimeProviderError

    settings = Settings(runway_api_key="sk-fake-for-test")
    with pytest.raises(RealtimeProviderError):
        get_provider("synthesia", settings)


# ---- Drift surface --------------------------------------------


def test_provider_package_only_contains_known_files():
    """Sanity check that the registry's file list matches
    what's actually in the package directory. A new file
    that ships without being added to `_provider_classes`
    above goes uncovered by the drift tests.

    The check is intentionally narrow — only `.py` files
    at the package root; sub-packages or build artifacts
    don't count. The maintenance cost is one line per new
    provider file (here + in `_provider_classes`).
    """
    pkg_dir = Path(
        inspect.getfile(MockRealtimeProvider),
    ).parent
    known_modules = {"__init__", "mock", "runway"}
    actual_modules = {
        p.stem for p in pkg_dir.glob("*.py")
        if not p.stem.startswith("_") or p.stem == "__init__"
    }
    unknown = actual_modules - known_modules
    assert unknown == set(), (
        f"New provider module(s) detected in "
        f"{pkg_dir.name}/: {sorted(unknown)}. Add the new "
        f"provider class to `_provider_classes` in this "
        f"test file + add the module name to `known_modules` "
        f"so the drift verifier covers it."
    )
