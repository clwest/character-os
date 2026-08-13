"""P1 2.7 (SESSION 224) — PD-1 regression: upstream > downstream.

Enforces the cross-service timeout coordination doctrine from
``feedback_timeout_coordination.md``:

    Upstream timeout must strictly exceed downstream's worst-case
    poll window. "Silent forward progress after declared failure"
    is a defect class, not a bug.

Concrete rule: for every ``MediaEngineClient`` method that hits a
media-engine endpoint with a known polling / subprocess deadline,
the method's default ``timeout`` must be **strictly greater than**
the downstream deadline. When the two are close (or reversed),
the media-engine keeps working after Django has already given up
— the upstream provider (Runway, ElevenLabs, Stability, Aleph)
work is orphaned, the client sees an error, the user retries, and
we pay twice.

Two PD-1 incidents to date validated this pattern:

* **SESSION 221 (E5-post)** — realtime session start: Django
  60 s < media-engine 150 s Runway realtime poll → orphaned
  session ``7cdd4763…``. Original PD-1.
* **SESSION 224 (F-03)** — portrait generation: Django 60 s
  < media-engine 180 s Runway gen4_image poll → orphaned
  Runway task ``1023e535-cb68-4a10-98d2-507bfbb932cc`` (task
  actually SUCCEEDED, PNG never fetched). F-03 evidence at
  ``docs/production-readiness/finding-f03-portrait-timeout/``.

**The DOWNSTREAM_DEADLINES_S mapping below is authoritative.**
When you change a downstream deadline in the media-engine, update
the mapping here and re-run this test. When you add a new
``MediaEngineClient`` method that hits a polling endpoint, add
both the client-side ``timeout`` default AND a mapping entry.

A ``None`` deadline means the endpoint is either:
  * a cheap single upstream call (client's own httpx timeout
    dominates), or
  * a CPU-bound task with no explicit ceiling (e.g., rembg —
    the client override IS the effective ceiling).
"""
from __future__ import annotations

import inspect

import pytest

from character_os.clients.media_engine import MediaEngineClient


# ---- The invariant ------------------------------------------------

# Downstream deadlines as of SESSION 224. Source-of-truth citations
# in the ``# source:`` comments — update these together with the
# media-engine when a deadline changes.
DOWNSTREAM_DEADLINES_S: dict[str, int | None] = {
    # -- Runway polling endpoints (highest-risk PD-1 sites) --------
    # source: media-engine/app/services/character_studio_client.py:529
    #         _portrait_task_attempt(..., deadline_secs=180)
    "create_portrait": 180,
    # source: media-engine/app/services/character_studio_client.py:794
    #         deadline = time.time() + 180 (poll Runway avatar → READY)
    "create_avatar": 180,
    # source: media-engine/app/services/realtime_provider/runway.py:58
    #         _READY_POLL_TIMEOUT_S = 150.0
    "realtime_session_create": 150,
    # source: media-engine/app/routers/internal.py::post_internal_extend_clip
    #         _EXTEND_POLL_DEADLINE_S = 600.0 (internal.py:3991)
    "extend_clip": 600,
    # source: media-engine/app/routers/internal.py::post_internal_style_remix
    #         _ALEPH_POLL_DEADLINE_S = 600.0 (internal.py:3485)
    "style_remix": 600,

    # -- Runway / ElevenLabs single-call-with-poll -----------------
    # source: media-engine/app/services/audio_client.py:354
    #         deadline = time.time() + 240 (dub poll → READY)
    "dub_audio": 240,
    # source: media-engine/app/services/audio_client.py:230
    #         deadline = time.time() + 90 (voice clone poll → READY)
    "clone_voice": 90,
    # source: media-engine/app/routers/internal.py::post_internal_voice_design
    #         deadline = time.time() + 90 (voice design poll → READY)
    "design_voice": 90,
    # source: media-engine/app/routers/internal.py
    #         _IMAGE_GEN_DEADLINE_S = 90.0 (internal.py:4566)
    "generate_image": 90,

    # -- ffmpeg subprocess ceilings --------------------------------
    # source: media-engine/app/routers/internal.py:1244 (concat)
    "concat_clips": 300,
    # source: media-engine/app/routers/internal.py:1802 (composite)
    "create_composite": 300,
    # source: media-engine/app/routers/internal.py:1994 (audio mix)
    "mix_audio": 300,
    # source: media-engine/app/routers/internal.py:2193 (captions)
    "add_captions": 180,
    # source: media-engine/app/routers/internal.py:2569 (intro_outro)
    "add_intro_outro": 180,
    # source: media-engine/app/routers/internal.py:2918 (trim)
    "trim_clip": 120,
    # source: media-engine/app/routers/internal.py:3042 (reformat)
    "reformat_clip": 180,
    # source: media-engine/app/routers/internal.py:4910 (audio_extract)
    "audio_extract": 120,

    # -- CPU-bound / defensive overrides (no explicit ceiling) -----
    # rembg on CPU; the client override IS the effective ceiling.
    "remove_avatar_background": None,

    # -- Cheap / single-call / fire-then-poll (client default OK) --
    # These pass through the base MediaEngineClient timeout (60 s).
    # No downstream poll to bound against. Fire-then-poll methods
    # (create_video, create_avatar_speech, create_visual_clip)
    # return a task_id immediately; the caller polls via poll_task /
    # poll_video separately.
    "create_video": None,
    "poll_video": None,
    "poll_task": None,
    "create_avatar_speech": None,
    "create_visual_clip": None,
    "refresh_avatar_thumbnail": None,
    "persist_avatar_portrait": None,
    "change_avatar_voice": None,
    "change_avatar_personality": None,
    "list_styles": None,
    "create_stability_image": None,
    "transcribe": None,
    "tts": None,
    "overlay_audio": None,
    "realtime_document_create": None,
    "realtime_session_poll": None,
    "realtime_session_fetch_transcript": None,
    "realtime_session_end": None,
    "health_check": None,
}


# ---- Helpers ------------------------------------------------------

def _effective_timeout(method_name: str) -> float:
    """The default timeout in seconds that ``method_name`` uses when
    invoked without a ``timeout=`` kwarg. Methods that define their
    own ``timeout: float = <N>`` parameter return ``N``; methods that
    don't fall back to the base ``MediaEngineClient.__init__`` default
    (60.0 as of SESSION 224).
    """
    method = getattr(MediaEngineClient, method_name)
    sig = inspect.signature(method)
    timeout_param = sig.parameters.get("timeout")
    if timeout_param is None or timeout_param.default is inspect.Parameter.empty:
        base_default = inspect.signature(MediaEngineClient.__init__).parameters[
            "timeout"
        ].default
        return float(base_default)
    return float(timeout_param.default)


def _client_methods_with_endpoints() -> set[str]:
    """Every public method on ``MediaEngineClient`` that hits an
    ``/internal/*`` endpoint. Excludes ``request`` (the raw HTTP
    helper), ``close`` / ``__enter__`` / ``__exit__``, and dunders.
    """
    skip = {"request", "close"}
    out: set[str] = set()
    for name, _ in inspect.getmembers(MediaEngineClient, predicate=inspect.isfunction):
        if name.startswith("_") or name in skip:
            continue
        out.add(name)
    return out


# ---- Tests --------------------------------------------------------

def test_downstream_deadlines_covers_every_client_method():
    """Coverage test: every public MediaEngineClient method must
    appear in DOWNSTREAM_DEADLINES_S. A new method without an entry
    means the P1 2.7 invariant hasn't been considered for it.
    """
    documented = set(DOWNSTREAM_DEADLINES_S.keys())
    actual = _client_methods_with_endpoints()
    missing = actual - documented
    extra = documented - actual
    assert not missing, (
        f"MediaEngineClient methods without a DOWNSTREAM_DEADLINES_S "
        f"entry: {sorted(missing)}. Add each method to the mapping "
        f"in this test with either its downstream deadline (int) "
        f"or None if it's a cheap / single-call / fire-then-poll "
        f"endpoint. See docstring for the invariant."
    )
    assert not extra, (
        f"DOWNSTREAM_DEADLINES_S has entries for methods that no "
        f"longer exist on MediaEngineClient: {sorted(extra)}. Prune "
        f"the mapping."
    )


@pytest.mark.parametrize(
    "method_name,downstream_s",
    sorted(
        (name, deadline)
        for name, deadline in DOWNSTREAM_DEADLINES_S.items()
        if deadline is not None
    ),
)
def test_upstream_strictly_exceeds_downstream(
    method_name: str, downstream_s: int,
) -> None:
    """PD-1 doctrine, mechanically enforced. Any regression here
    is either (a) a new method whose downstream deadline was set
    without bumping the client timeout, or (b) a downstream deadline
    that got extended without paralleling the client. Both are
    orphan-generating defects.
    """
    upstream = _effective_timeout(method_name)
    assert upstream > downstream_s, (
        f"MediaEngineClient.{method_name}: upstream client timeout "
        f"({upstream:.0f} s) must be STRICTLY GREATER than the "
        f"downstream media-engine deadline ({downstream_s} s). "
        f"Otherwise the client hangs up while the media-engine is "
        f"still polling the upstream provider — orphaned work, user "
        f"sees a false failure. See feedback_timeout_coordination.md."
    )
