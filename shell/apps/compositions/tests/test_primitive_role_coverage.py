"""Asset Library v1 (SESSION 186, A2) — contract rule 20 coverage.

Contract rule 20: every primitive in ``apps.compositions.primitives``
stamps a role on its output. The full contract has three layers; this
test file is the static + runtime enforcement for all three:

1. **Static AST scan.** Every ``"primitive_kind": "<literal>"`` string
   in the primitives package has a corresponding entry in
   :data:`apps.compositions.asset_roles.PRIMITIVE_TO_ROLE`. Adding a
   new primitive without updating the mapping fails this test.
2. **Static emit scan.** Every ``PrimitiveResult(...)`` constructor
   call in the primitives package passes a ``role=`` kwarg. A new
   primitive that emits an Asset without stamping role fails this test.
3. **Runtime backstop.** The mock primitives stamp ``EXPERIMENT``;
   ``capture_transcript`` stamps ``TRANSCRIPT``; the runner's
   ``_persist_output_asset`` raises if ``result.role`` is empty.

The companion A1-level coverage test in
``test_backfill_asset_roles.py`` enforces that every codebase
primitive_kind also lives in PRIMITIVE_TO_ROLE — the two together
make it impossible to forget either side of the contract.
"""
from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.compositions.asset_roles import PRIMITIVE_TO_ROLE
from apps.compositions.models import (
    Asset,
    AssetRole,
    AssetType,
    Composition,
    CompositionStep,
)
from apps.compositions.primitives import (
    MockPassthroughPrimitive,
    MockSlowPrimitive,
    PrimitiveError,
    PrimitiveResult,
)
from apps.compositions.tasks import _persist_output_asset
from apps.realtime.models import RealtimeSession
from apps.realtime.tasks import fetch_transcript_for_session
from apps.spokespeople.models import Teammate
from character_os.clients.media_engine import RealtimeTranscriptResult

User = get_user_model()
pytestmark = pytest.mark.django_db


PRIMITIVES_DIR = (
    Path(__file__).resolve().parents[1] / "primitives"
)


# ---- AST helpers ---------------------------------------------------


def _walk_primitive_modules() -> list[tuple[Path, ast.Module]]:
    """Return (path, parsed-AST) pairs for every ``*.py`` in the
    primitives package excluding ``__init__.py`` (it doesn't emit
    Assets — pure registry)."""
    out: list[tuple[Path, ast.Module]] = []
    for py in sorted(PRIMITIVES_DIR.glob("*.py")):
        if py.name == "__init__.py":
            continue
        out.append((py, ast.parse(py.read_text())))
    return out


def _primitive_kinds_in_module(tree: ast.Module) -> set[str]:
    """Collect every string literal mapped from the key
    ``"primitive_kind"`` in any dict literal in ``tree``."""
    kinds: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for k, v in zip(node.keys, node.values):
            if (
                isinstance(k, ast.Constant)
                and k.value == "primitive_kind"
                and isinstance(v, ast.Constant)
                and isinstance(v.value, str)
            ):
                kinds.add(v.value)
    return kinds


def _primitive_result_calls(tree: ast.Module) -> list[ast.Call]:
    """All ``PrimitiveResult(...)`` constructor calls in ``tree``."""
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and (
            (isinstance(node.func, ast.Name) and node.func.id == "PrimitiveResult")
            or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "PrimitiveResult"
            )
        ):
            calls.append(node)
    return calls


# ---- Layer 1: AST primitive_kind coverage --------------------------


def test_every_primitive_kind_literal_has_a_role_mapping() -> None:
    """Static AST scan of ``apps/compositions/primitives/*.py``.
    Every primitive_kind string literal that appears in production
    code must have a row in PRIMITIVE_TO_ROLE — contract rule 20
    static enforcement.

    Mock primitives (mock.py) intentionally don't stamp
    primitive_kind in their extra_source_spec (they're test
    fixtures, not real production primitives), so they won't
    appear here.
    """
    all_kinds: set[str] = set()
    per_module: dict[str, set[str]] = {}
    for path, tree in _walk_primitive_modules():
        kinds = _primitive_kinds_in_module(tree)
        if kinds:
            per_module[path.name] = kinds
            all_kinds |= kinds

    missing = all_kinds - set(PRIMITIVE_TO_ROLE)
    assert not missing, (
        f"PRIMITIVE_TO_ROLE missing entries for primitive_kind "
        f"literals found in code: {sorted(missing)}. Per-module "
        f"breakdown: {per_module}. Add the mapping to "
        "apps.compositions.asset_roles.PRIMITIVE_TO_ROLE."
    )


def test_no_orphan_mappings() -> None:
    """Every key in PRIMITIVE_TO_ROLE has at least one
    matching primitive_kind literal in the codebase OR is one of
    the known emit-from-outside-primitives entries (e.g.
    realtime_transcript is emitted by apps.realtime.tasks, not by
    the primitives package; smoke_keyframes by a management
    command). Orphans signal a removed primitive whose mapping
    leaked through."""
    in_code: set[str] = set()
    for _path, tree in _walk_primitive_modules():
        in_code |= _primitive_kinds_in_module(tree)

    # Known emitters outside apps/compositions/primitives/:
    EMITTED_ELSEWHERE = {
        "realtime_transcript",  # apps/realtime/tasks.py capture_transcript
        "smoke_keyframes",  # apps/compositions/management/commands/smoke_keyframes.py
    }

    orphans = set(PRIMITIVE_TO_ROLE) - in_code - EMITTED_ELSEWHERE
    assert not orphans, (
        f"PRIMITIVE_TO_ROLE has entries with no matching "
        f"primitive_kind literal anywhere: {sorted(orphans)}. If the "
        "primitive was removed, drop the mapping. If it's emitted "
        "outside the primitives package, add it to EMITTED_ELSEWHERE."
    )


# ---- Layer 2: AST emit-site role coverage --------------------------


def test_every_primitive_result_constructor_passes_a_role_kwarg() -> None:
    """Every ``PrimitiveResult(...)`` constructor in the primitives
    package must include a ``role=`` keyword argument. The runner's
    runtime backstop catches the empty-string case at execute time,
    but this static check catches it before the test would even run.

    Walks every ``.py`` in ``apps/compositions/primitives/``,
    locates every ``PrimitiveResult(...)`` call, and asserts a
    ``role`` keyword is present.
    """
    offenders: list[str] = []
    for path, tree in _walk_primitive_modules():
        for call in _primitive_result_calls(tree):
            kwargs = {kw.arg for kw in call.keywords if kw.arg}
            if "role" not in kwargs:
                offenders.append(f"{path.name}:{call.lineno}")

    assert not offenders, (
        f"PrimitiveResult constructors missing role= kwarg at "
        f"{offenders}. Contract rule 20: every primitive stamps a "
        "role on its output."
    )


# ---- Layer 3: runtime backstop --------------------------------------


class _StubStep:
    """Minimal duck-typed step the mock primitives accept."""

    def __init__(self) -> None:
        self.id = "step-aaaa-bbbb"
        self.params = {}
        self.position = 0


def test_mock_passthrough_stamps_experiment() -> None:
    result = MockPassthroughPrimitive.execute(_StubStep(), [], mock_mode=True)
    assert result.role == AssetRole.EXPERIMENT.value


def test_mock_slow_stamps_experiment() -> None:
    result = MockSlowPrimitive.execute(_StubStep(), [], mock_mode=True)
    assert result.role == AssetRole.EXPERIMENT.value


# ---- Layer 3: runner persists role + raises on missing -------------


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_composition(ws: Workspace) -> Composition:
    sp = Teammate.objects.create(
        workspace=ws,
        name="A2 cast",
        runway_avatar_id="av_test",
        portrait_path="https://fake/p.png",
        business_brief="b",
    )
    return Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="A2 runner test",
        mock_mode=True,
    )


def _make_step(composition: Composition, primitive: str = "mock_passthrough") -> CompositionStep:
    return CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive=primitive,
        params={},
    )


def test_persist_output_asset_writes_role_to_db() -> None:
    """End-to-end: a PrimitiveResult with role flows through the
    runner and the Asset row's role column reflects it. This is the
    proof the role makes it from PrimitiveResult → Asset.role; the
    A4 endpoint / A5 SPA / A7 picker all read from this column."""
    ws = _make_workspace("a2runner@test.local")
    comp = _make_composition(ws)
    step = _make_step(comp)
    result = PrimitiveResult(
        asset_type=AssetType.CLIP,
        file_path="https://example/clip.mp4",
        duration_ms=5000,
        cost_micros=100,
        role=AssetRole.TALKING_HEAD.value,
    )
    asset = _persist_output_asset(comp, step, result)
    asset.refresh_from_db()
    assert asset.role == AssetRole.TALKING_HEAD


def test_persist_output_asset_raises_when_role_missing() -> None:
    """Defense-in-depth — a primitive that forgets to stamp role
    crashes the step rather than silently writing a role-less
    Asset row."""
    ws = _make_workspace("a2norole@test.local")
    comp = _make_composition(ws)
    step = _make_step(comp)
    result = PrimitiveResult(
        asset_type=AssetType.CLIP,
        file_path="https://example/clip.mp4",
        cost_micros=0,
        role="",
    )
    with pytest.raises(PrimitiveError, match="Contract rule 20"):
        _persist_output_asset(comp, step, result)


# ---- Realtime transcript also stamps role --------------------------


@pytest.fixture(autouse=False)
def _eager_celery():
    with override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


def test_realtime_capture_transcript_stamps_transcript_role(_eager_celery) -> None:
    """``apps.realtime.tasks.capture_transcript`` writes
    ``Asset(TRANSCRIPT)`` directly (it doesn't go through the
    primitives runner). A2 stamps the role explicitly on that
    direct emit so the Asset Library is consistent across both
    code paths."""
    ws = _make_workspace("a2realtime@test.local")
    sp = Teammate.objects.create(
        workspace=ws,
        name="A2 Test",
        runway_avatar_id="av_test",
        portrait_path="https://fake/p.png",
        business_brief="b",
    )
    session = RealtimeSession.objects.create(
        workspace=ws,
        spokesperson=sp,
        provider_session_id="rt_a2_test",
        provider_session_key="key",
        status=RealtimeSession.Status.READY,
    )

    fake = MagicMock()
    fake.realtime_session_fetch_transcript.return_value = RealtimeTranscriptResult(
        session_id="rt_a2_test",
        text="User: Hi.\nSpokesperson: Hello.",
        segments=[
            {"role": "user", "text": "Hi.", "ts": "t1"},
            {"role": "spokesperson", "text": "Hello.", "ts": "t2"},
        ],
        mock_mode=True,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    with patch("apps.realtime.tasks.MediaEngineClient", return_value=cm):
        out = fetch_transcript_for_session.apply(
            args=[str(session.id)]
        ).get()

    assert out["status"] == "persisted"
    asset = Asset.objects.get(pk=out["asset_id"])
    assert asset.role == AssetRole.TRANSCRIPT
