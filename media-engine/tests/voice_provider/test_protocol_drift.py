"""Protocol drift verifier — §19 Step 6.a (SESSION 245).

Mirrors the Step 5 portrait drift verifier
(``tests/portrait_provider/test_protocol_drift.py``) and the R10
realtime drift verifier before it. Catches two classes of drift
that would otherwise land silently and only surface later under
real traffic:

1. **A Protocol method lands without an implementation on every
   adapter.** Someone adds ``list_voices`` (say) to the Protocol;
   Runway gets a real impl but Mock silently doesn't. Mock-mode
   tests silently break the day someone actually exercises the
   new method.

2. **A new adapter file lands missing methods.** Someone drops
   in ``playht.py`` and forgets ``capabilities``. Every
   qualification record from that adapter is unstamped; the
   miss is caught only on the day the Django broker persists
   such a row and hits the NOT NULL constraint.

Both classes are catchable by introspection against the
Protocol. This test runs on every CI / local pass; new methods
and new providers both trip it.

The 6.b Runway adapter will re-run this verifier over the
Mock + Runway registry as the closing gate.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from app.services.voice_provider import VoiceDesignProvider
from app.services.voice_provider.mock import MockVoiceProvider
from app.services.voice_provider.runway import RunwayVoiceProvider


# Protocol methods per SESSION 245 scope-lock (three methods,
# no more). Extending this tuple requires extending the Protocol,
# which requires re-ratification against §17.4.a. Do not extend
# without an operator scope amendment.
PROTOCOL_METHODS = (
    "design_voice",
    "clone_voice",
    "capabilities",
)


def _provider_classes() -> list[type]:
    """The concrete provider classes the test discovers. v1
    registry closes at these two (Mock 6.a, Runway 6.b). Adding
    a future adapter means adding an import + a row here — same
    discipline as portrait ``_provider_classes``.
    """
    return [
        MockVoiceProvider,
        RunwayVoiceProvider,
    ]


# ---- Protocol surface ------------------------------------------


def test_protocol_methods_match_expected_set():
    """The PROTOCOL_METHODS constant mirrors the Protocol. If
    someone adds (or removes) a method on the Protocol, this
    test fails until the constant is updated — which is itself
    an audit event (the new method needs implementations on
    every adapter AND SESSION 245 scope-lock revisited).
    """
    proto_methods: set[str] = {
        name
        for name in dir(VoiceDesignProvider)
        if not name.startswith("_") and callable(getattr(VoiceDesignProvider, name))
    }
    expected: set[str] = set(PROTOCOL_METHODS)
    assert proto_methods == expected, (
        f"Protocol method set drifted from PROTOCOL_METHODS.\n"
        f"  On Protocol: {sorted(proto_methods)}\n"
        f"  In test:     {sorted(expected)}\n"
        f"  Missing from test: {sorted(proto_methods - expected)}\n"
        f"  Extra in test:     {sorted(expected - proto_methods)}\n"
        f"If you added a Protocol method, update PROTOCOL_METHODS "
        f"AND verify every concrete adapter implements it AND "
        f"revisit §17.4.a / SESSION 245 scope-lock — the "
        f"Protocol was ratified at exactly three methods."
    )


# ---- Per-provider completeness ---------------------------------


@pytest.mark.parametrize("provider_cls", _provider_classes())
def test_provider_implements_every_protocol_method(provider_cls: type):
    """Each concrete adapter must define every Protocol method
    as a callable attribute. A new adapter that forgets
    ``capabilities`` fails here loudly."""
    missing = [
        name for name in PROTOCOL_METHODS
        if not hasattr(provider_cls, name)
        or not callable(getattr(provider_cls, name))
    ]
    assert missing == [], (
        f"{provider_cls.__name__} is missing Protocol method(s): "
        f"{missing}. Every concrete adapter must implement every "
        f"method in VoiceDesignProvider."
    )


@pytest.mark.parametrize("provider_cls", _provider_classes())
def test_provider_methods_are_not_notimplemented_stubs(provider_cls: type):
    """Each Protocol method's implementation must have a body —
    not a bare ``raise NotImplementedError`` stub. Methods with
    real work that ALSO raise NotImplementedError deep in a
    branch are fine.

    Providers that do NOT support an operation raise
    ``VoiceOperationUnsupportedError``, not
    ``NotImplementedError`` — see the design_voice / clone_voice
    docstrings.
    """
    stubs: list[str] = []
    for name in PROTOCOL_METHODS:
        method = getattr(provider_cls, name)
        if _method_is_notimplemented_stub(method):
            stubs.append(name)
    assert stubs == [], (
        f"{provider_cls.__name__} method(s) {stubs} are bare "
        f"`raise NotImplementedError` stubs. If a method is "
        f"deferred to a future slice, keep it out of the "
        f"registry until it's implemented — the Protocol has "
        f"no reserved stubs. Providers that structurally lack "
        f"an operation raise VoiceOperationUnsupportedError, "
        f"not NotImplementedError."
    )


def _method_is_notimplemented_stub(method) -> bool:
    """True if the method's body is exactly ``raise
    NotImplementedError(...)`` (possibly preceded by a
    docstring). False for any method with real logic.
    """
    try:
        source = inspect.getsource(method)
    except (OSError, TypeError):
        return False
    source = inspect.cleandoc(source)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    if not tree.body or not isinstance(
        tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef),
    ):
        return False
    fn_body = tree.body[0].body
    if (
        fn_body
        and isinstance(fn_body[0], ast.Expr)
        and isinstance(fn_body[0].value, ast.Constant)
        and isinstance(fn_body[0].value.value, str)
    ):
        fn_body = fn_body[1:]
    if len(fn_body) != 1:
        return False
    stmt = fn_body[0]
    if not isinstance(stmt, ast.Raise):
        return False
    exc = stmt.exc
    if isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
        return True
    if (
        isinstance(exc, ast.Call)
        and isinstance(exc.func, ast.Name)
        and exc.func.id == "NotImplementedError"
    ):
        return True
    return False


# ---- Registry drift --------------------------------------------


def test_provider_package_only_contains_known_files():
    """Sanity check that the package's file list matches what
    the test knows about. A new adapter file that ships without
    being added to ``_provider_classes`` above goes uncovered
    by the drift tests otherwise.

    The check is narrow — only ``.py`` files at the package
    root. Sub-packages, build artifacts, and private helpers
    (``_*.py``) don't count.

    6.b lock: ``__init__``, ``mock``, ``runway``.
    """
    pkg_dir = Path(inspect.getfile(MockVoiceProvider)).parent
    known_modules = {"__init__", "mock", "runway"}
    actual_modules = {
        p.stem for p in pkg_dir.glob("*.py")
        if not p.stem.startswith("_") or p.stem == "__init__"
    }
    unknown = actual_modules - known_modules
    assert unknown == set(), (
        f"New provider module(s) detected in {pkg_dir.name}/: "
        f"{sorted(unknown)}. Add the new adapter class to "
        f"``_provider_classes`` in this test file AND add the "
        f"module name to ``known_modules`` so the drift verifier "
        f"covers it."
    )
