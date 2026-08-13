"""Shared rembg session cache — extracted for reuse across
V16 (video composite background removal) and §19 Step 7
(portrait normalization background replacement).

Extracted from ``app/routers/internal.py`` at SESSION 246 7.c.a
per operator ratification. The 5-line helper existed inline in
V16's router file since SESSION 179; extracting it produces
one deterministic cache shared by both consumers rather than
two independent module-level dicts, and lets the normalization
pipeline reuse the lowest honest primitive without importing
private symbols from a 3000-line router file.

What this module owns:

* Lazy, module-cached ``rembg.new_session(model)`` initialization.
  The ONNX model load is ~1 s + ~176 MB for ``u2net_human_seg``;
  per-call would dominate small workloads.
* Nothing else. V16's video pipeline (ffmpeg decode → per-frame
  rembg.remove() → ffmpeg alpha encode → disk output → hash
  cache) stays in ``internal.py`` untouched. Normalization's
  still-portrait pipeline in ``services/normalization/stages/
  background_replacement.py`` calls ``rembg.remove(bytes,
  session=...)`` directly.

Determinism note (live-probed under
``rembg==2.0.75`` + ``onnxruntime==1.26.0`` +
``opencv-python-headless==4.13.0.92`` on macOS/arm64):

* Same-session ``rembg.remove()`` on identical input bytes
  produces byte-identical output.
* A **fresh session** for the same model on the same input
  bytes also produces byte-identical output.

Therefore normalization's determinism contract holds
transparently across process restarts — the pipeline
manifest's ``pipeline_version`` correctly reflects the ONNX
model as a stable transformation rather than a
session-scoped one. Recorded in the SESSION 246 handoff.

Model policy:

* ``u2net_human_seg`` is the sole Step 7 model. V16 also
  restricts to that model today. Adding another rembg model
  requires an explicit ratification against §17.6.a — round-
  one benchmark work should not silently introduce a second
  segmentation model whose alpha behavior differs from
  ``u2net_human_seg``.
"""
from __future__ import annotations

from typing import Any


# Module-level cache. One entry per model name; entries are the
# rembg ``BaseSession`` instances returned by ``new_session``.
# The dict itself is private; callers reach for ``get_rembg_session``.
_SESSIONS: dict[str, Any] = {}


def get_rembg_session(model: str) -> Any:
    """Return the shared cached ``rembg`` session for ``model``.

    Lazily loads the ONNX model on first call; subsequent calls
    for the same model name return the same session object
    (identity-equal). Callers pass the session to
    ``rembg.remove(input, session=session)``.

    Not thread-safe under a race on first load — the cache write
    is a plain dict assignment. Under FastAPI's ASGI worker model
    (one worker process per rembg workload), this has never been
    a real issue in V16's shipping usage. If future concurrent
    initialization becomes a concern, a ``threading.Lock`` around
    the ``if model not in _SESSIONS`` block is the incremental
    upgrade — not needed today.
    """
    if not isinstance(model, str) or not model:
        raise ValueError(f"model must be a non-empty string; got {model!r}")
    if model not in _SESSIONS:
        # Imported inside the function so importing this module
        # does not force the rembg dependency to load at every
        # media-engine startup (rembg pulls onnxruntime, which
        # is ~40 MB of CPython initialization even before any
        # ONNX model is loaded).
        from rembg import new_session

        _SESSIONS[model] = new_session(model)
    return _SESSIONS[model]


def _registered_session_model_names() -> tuple[str, ...]:
    """Enumerate every model currently cached. Exists for
    diagnostics + tests; not meant as a public API for
    resource management.
    """
    return tuple(_SESSIONS.keys())


def _reset_sessions_for_tests() -> None:
    """Test-only cache reset. Enables fresh-session determinism
    probes without a process restart. Not part of the public
    surface; leading underscore is a deliberate signal.
    """
    _SESSIONS.clear()


__all__ = ["get_rembg_session"]
