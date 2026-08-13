"""Shared rembg session cache tests (SESSION 246 7.c.a).

Coverage:

* ``get_rembg_session`` returns the identity-same session for
  repeat calls of the same model — proves the module-level
  cache works.
* V16's `internal.py` and the new shared helper resolve to the
  same cached object — proves the extraction was complete
  (no second cache).
* Rejects empty/non-string model names before touching rembg.
* Determinism probe: ``rembg.remove()`` against the pinned
  ``u2net_human_seg`` model produces byte-identical output over
  repeat invocations on the same session. Recorded live so a
  future rembg/onnxruntime upgrade that introduces
  nondeterminism is caught before the normalization pipeline
  starts silently producing drifting alpha.

The determinism probe uses a small synthetic RGBA input so the
test runs fast (< 2 s including ONNX load). ONNX model file is
cached to ``~/.u2net/`` after first invocation; subsequent runs
are near-instant.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app.services.rembg_session import (
    _registered_session_model_names,
    _reset_sessions_for_tests,
    get_rembg_session,
)


_U2NET_HUMAN_SEG = "u2net_human_seg"


@pytest.fixture(autouse=True)
def _reset_between_tests():
    """The rembg session cache is module-level. Tests that need
    a clean cache use this fixture; the fresh-session determinism
    test exercises the reset behavior explicitly.
    """
    yield
    _reset_sessions_for_tests()


# ---- Cache identity ---------------------------------------------


def test_same_model_returns_identity_same_session_object() -> None:
    a = get_rembg_session(_U2NET_HUMAN_SEG)
    b = get_rembg_session(_U2NET_HUMAN_SEG)
    assert a is b


def test_v16_import_site_resolves_to_the_same_shared_cache() -> None:
    """V16's ``internal.py`` was extracted to import
    ``get_rembg_session`` from the shared module at SESSION 246
    7.c.a. This test proves the extraction produced ONE cache —
    a session created via the shared helper is identity-same to
    the session V16 would resolve for the same model.
    """
    from app.routers.internal import _get_rembg_session as v16_get_session

    shared = get_rembg_session(_U2NET_HUMAN_SEG)
    from_v16 = v16_get_session(_U2NET_HUMAN_SEG)
    assert shared is from_v16


def test_registered_model_names_after_load() -> None:
    assert _registered_session_model_names() == ()
    get_rembg_session(_U2NET_HUMAN_SEG)
    assert _registered_session_model_names() == (_U2NET_HUMAN_SEG,)


# ---- Input validation -------------------------------------------


def test_empty_model_name_raises() -> None:
    with pytest.raises(ValueError):
        get_rembg_session("")


def test_non_string_model_name_raises() -> None:
    with pytest.raises(ValueError):
        get_rembg_session(None)  # type: ignore[arg-type]


# ---- Determinism probe (live rembg call) ------------------------


def _make_synthetic_rgba_png(width: int = 128, height: int = 128) -> bytes:
    """Small RGBA PNG for rembg smoke — not a real portrait; the
    goal is only to prove determinism, not matting quality.
    """
    img = Image.new("RGBA", (width, height), (200, 120, 60, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_rembg_output_deterministic_across_repeat_invocations_on_same_session() -> None:
    """Load-bearing for §10.6: same input + same session →
    byte-identical rembg output. If this ever regresses (a
    future rembg or onnxruntime upgrade introduces
    nondeterminism), the pipeline's determinism contract
    breaks and this test catches it before any normalization
    manifest silently records drifting alpha.
    """
    from rembg import remove

    session = get_rembg_session(_U2NET_HUMAN_SEG)
    input_bytes = _make_synthetic_rgba_png()
    a = remove(input_bytes, session=session)
    b = remove(input_bytes, session=session)
    assert a == b, "rembg.remove is nondeterministic on same session"


def test_rembg_output_deterministic_across_fresh_session_for_same_model() -> None:
    """Even after cache reset (fresh session for the same model),
    rembg output on the same input is byte-identical. Proves
    determinism across process restarts / worker recycles,
    which the pipeline's ``pipeline_version`` contract relies
    on.
    """
    from rembg import remove

    input_bytes = _make_synthetic_rgba_png()
    session_a = get_rembg_session(_U2NET_HUMAN_SEG)
    out_a = remove(input_bytes, session=session_a)

    _reset_sessions_for_tests()
    session_b = get_rembg_session(_U2NET_HUMAN_SEG)
    assert session_a is not session_b, "cache reset did not produce a fresh session"
    out_b = remove(input_bytes, session=session_b)

    assert out_a == out_b, (
        "rembg.remove is nondeterministic across sessions — "
        "the pipeline's byte-for-byte determinism contract "
        "cannot hold. Investigate before shipping v1."
    )
