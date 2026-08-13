"""Starter composition factories.

SESSION 143 / V3. Each starter is a small Python factory that
creates a ``Composition`` + its ``CompositionStep`` rows for a
named recipe. Operators (admin / CLI / eventual V15 SPA recipe
gallery) drive these to instantiate a fresh composition without
hand-stitching step rows.

A starter is **not** the composition itself — it's a builder
function that returns the newly-created ``Composition``. The
caller then enqueues ``execute_composition`` to run it.

v1 ships one starter: ``talking_head``. V4+ adds
``cinematic_visual``; V5 adds ``long_form_ad``; V6+ adds the
remaining 14 recipes from
``docs/design/VIDEO_COMPOSITION_V1.md`` §"Starter compositions".

Each starter is tagged with its ``template_kind`` on the
Composition row so admin + audit surfaces know which recipe a
composition forked from.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import transaction

from .models import Composition, CompositionStep
from .script_splitter import (
    DEFAULT_CHUNK_MAX_CHARS,
    chunk_script,
    split_script_with_llm,
)
from .transcription import (
    Segment,
    fetch_transcript,
    pick_strongest_segment,
)

if TYPE_CHECKING:
    from apps.accounts.models import Workspace
    from apps.scripts.models import Script
    from apps.spokespeople.models import Teammate
    from django.contrib.auth.models import AbstractBaseUser
    from .models import Asset

logger = logging.getLogger(__name__)


# Backdrop chain sizing for talking_head_with_backdrop (SESSION 179).
# gen4.5 video clips top out at 10s per call. When the avatar speech
# is longer than the backdrop, composite_video used to loop / freeze
# the single backdrop — operator-visible as "only 3 seconds of real
# motion in a 22-second video." We now generate N backdrop clips
# sized to cover the estimated speech duration + concat them so the
# composite shows continuous motion.
#
# Constants tuned against SESSION 179's real-mode dogfood:
#   - 280-char Riggs script rendered as a 22-second clip → ~12.7 chars/sec
#   - We use 11 chars/sec (slight over-estimate of duration) plus a
#     2-second safety buffer so N covers actual speech length even on
#     slower-paced voices. Composite trims long-edge to short-edge so
#     over-provisioning by a second or two is free.
_AVATAR_SPEECH_CHARS_PER_SECOND = 11
_AVATAR_SPEECH_DURATION_BUFFER_SECONDS = 2
_DEFAULT_BACKDROP_DURATION_SECONDS = 10
_MAX_BACKDROP_CHAIN_LENGTH = 6  # 60s of backdrop motion; safety stop


def _estimate_avatar_speech_seconds(script_chars: int) -> int:
    """Conservative estimate of how long an avatar_speech clip will
    run for a given script length. Over-estimating is safer than
    under-estimating — N backdrops will cover the avatar; the
    composite primitive trims the long edge."""
    base = max(0, script_chars) / _AVATAR_SPEECH_CHARS_PER_SECOND
    return max(5, int(base) + _AVATAR_SPEECH_DURATION_BUFFER_SECONDS)


def _compute_backdrop_chain_length(
    script_chars: int,
    backdrop_duration_seconds: int,
) -> int:
    """How many backdrop clips to chain so the concat covers the
    estimated speech duration. Clamped to
    ``_MAX_BACKDROP_CHAIN_LENGTH`` so a pathological script can't
    spin up 50 Runway calls."""
    speech_seconds = _estimate_avatar_speech_seconds(script_chars)
    n = -(-speech_seconds // max(1, backdrop_duration_seconds))  # ceil
    return max(1, min(n, _MAX_BACKDROP_CHAIN_LENGTH))


# V17.5 — extend-chain backdrop math. When the V8 starter is invoked
# with use_extend_for_backdrop=True, the backdrop is laid down as
# 1 base generate_visual_clip (10s, gen4.5) + N extend_visual_clip
# steps (5s each, gen4_turbo last-frame-conditioned). N is sized so
# the chain's total duration covers the estimated avatar speech
# length. The composite primitive trims the long edge so a slightly
# over-provisioned chain is free.
#
# Compared to the SESSION 179 multi-backdrop concat (the False
# path), this:
#   * removes visible motion seams every 10s (extends condition on
#     the prior segment's last frame),
#   * pays only for the new seconds rather than re-rendering a full
#     fresh 10s clip per chunk ($0.50 base + $0.25 per extend vs
#     $0.50 per backdrop in the concat chain),
#   * locks per-segment durations (10s base + 5s each extend) — the
#     ``backdrop_duration`` kwarg becomes redundant when this flag
#     is True.
#
# Q-v17-5 resolution: cost estimation routes through each
# primitive's estimate_cost(), which sums correctly across the
# generate base + N extends without a chain-wide helper.

_EXTEND_BASE_DURATION_SECONDS = 10
_EXTEND_SEGMENT_DURATION_SECONDS = 5


def _compute_extend_backdrop_chain_length(script_chars: int) -> int:
    """Number of extend_visual_clip steps to chain after the 10s
    base so the total backdrop covers estimated speech duration.

    Returns 0 when speech ≤ 10s (single generate is enough). Clamps
    to ``_MAX_BACKDROP_CHAIN_LENGTH - 1`` so total chain length
    (base + extends) stays bounded by the same safety cap as the
    concat path."""
    speech_seconds = _estimate_avatar_speech_seconds(script_chars)
    remaining = max(0, speech_seconds - _EXTEND_BASE_DURATION_SECONDS)
    n = -(-remaining // _EXTEND_SEGMENT_DURATION_SECONDS)  # ceil
    return max(0, min(n, _MAX_BACKDROP_CHAIN_LENGTH - 1))


# SESSION 180 — caption auto-timing for talking_head_polished's
# ``burn_captions`` shorthand. The avatar's actual cadence
# drifts from the chars-per-second estimate (vincent / felix /
# david etc all read at slightly different rates) so the
# timing is approximate. For tight sync, operators should pass
# captions= as an explicit list of {start_s, end_s, text}.
_CAPTION_MIN_SECONDS = 1.0
_CAPTION_MAX_SECONDS = 8.0


def _auto_caption_from_script(script: str) -> list[dict]:
    """Split a script on sentence boundaries and distribute time
    at the avatar's estimated speech rate. Each chunk gets a
    duration proportional to its character count, floored at
    1.0s (so short interjections still display long enough to
    read) and capped at 8.0s (so a long unpunctuated sentence
    doesn't sit on-screen forever)."""
    import re
    raw_chunks = re.split(r"(?<=[.!?])\s+", script.strip())
    chunks = [c.strip() for c in raw_chunks if c.strip()]
    if not chunks:
        return []

    captions: list[dict] = []
    t = 0.0
    for chunk in chunks:
        dur = max(
            _CAPTION_MIN_SECONDS,
            min(
                _CAPTION_MAX_SECONDS,
                len(chunk) / _AVATAR_SPEECH_CHARS_PER_SECOND,
            ),
        )
        captions.append({
            "start_s": round(t, 2),
            "end_s": round(t + dur, 2),
            "text": chunk,
        })
        t += dur
    return captions


@transaction.atomic
def auto_script(
    *,
    workspace: "Workspace",
    script: "Script",
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Create a single-step ``auto_script`` composition from a
    persistent ``Script`` row.

    B-2 / B2.3 (SESSION 206). The Script's persisted
    ``draft_text`` flows verbatim to step 0's
    ``generate_avatar_speech`` primitive as the ``script``
    param. **`use_knowledge` is NOT set** — per AUTO_SCRIPTING_V1
    rule 7, the in-primitive K6 synthesis is skipped because the
    draft is already synthesized + verified at draft-time.

    The Composition's ``knowledge_chunk_ids`` field is populated
    from the Script's persisted chunks for the lineage audit
    surface (so F-arc brief-mode + F6's
    ``resolve_chunk_ids_to_docs`` still light up on the rendered
    Composition detail page).

    Args:
        workspace: composition's workspace anchor. Must match
            ``script.workspace`` (rule 6 cross-workspace guard).
        script: a B-2 Script row with ``status=READY`` and a
            non-empty ``draft_text``. Caller (ScriptViewSet's
            render action) is responsible for the status check.
        mock_mode: V0 contract rule 9 — deterministic stub
            output, no Runway call.
        name: operator-visible Composition name. Defaults to
            ``"Auto-script — {script.name}"``.
        created_by: optional User for audit attribution.

    Returns:
        The fresh ``Composition`` row. Caller enqueues
        ``execute_composition.delay(str(comp.id))``.

    Raises:
        ValueError: script.workspace != workspace; script has
            empty draft_text; script.spokesperson missing /
            cross-workspace.
    """
    if script.workspace_id != workspace.pk:
        raise ValueError(
            f"script {script.id} (workspace {script.workspace_id}) is "
            f"not in workspace {workspace.pk}"
        )
    if not (script.draft_text or "").strip():
        raise ValueError(
            f"script {script.id} has empty draft_text; cannot "
            "fire auto_script without a draft"
        )
    spokesperson = script.spokesperson
    if spokesperson is None or spokesperson.workspace_id != workspace.pk:
        raise ValueError(
            f"script {script.id} spokesperson is missing or in a "
            f"different workspace than {workspace.pk}"
        )

    composition_name = name.strip() or f"Auto-script — {script.name}"
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=composition_name,
        template_kind="auto_script",
        mock_mode=mock_mode,
        created_by=created_by,
        # Rule 7 — populate the lineage field from the Script.
        # The primitive will see ``use_knowledge=False`` and
        # not overwrite this (it only writes
        # source_spec.knowledge_chunk_ids on the asset; the
        # composition row's field stays as we set it here).
        knowledge_chunk_ids=list(script.knowledge_chunk_ids or []),
        # The draft was already verified at draft-time by K6.4;
        # preserve the verdict on the Composition so F-arc
        # brief-mode shows the same status as the Script row.
        verification_status=script.verification_status or "",
        verification_warnings=list(script.verification_warnings or []),
        synthesized_brief=script.draft_text,
    )
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="generate_avatar_speech",
        inputs=[],
        params={
            "script": script.draft_text,
            # Rule 7 — explicit False. The primitive's
            # ``_maybe_synthesize_script`` short-circuits on
            # ``use_knowledge=False`` and returns the script
            # verbatim, no K6 call, no double synthesis.
            "use_knowledge": False,
        },
    )

    logger.info(
        "starter auto_script created composition=%s script=%s "
        "spokesperson=%s mock=%s chunks=%d",
        composition.id, script.id, spokesperson.id, mock_mode,
        len(script.knowledge_chunk_ids or []),
    )
    return composition


@transaction.atomic
def talking_head(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    script: str,
    use_knowledge: bool = False,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
    verifier_mode: str | None = None,
    opener: str | None = None,
) -> Composition:
    """Create a single-step ``talking_head`` composition.

    One step: ``generate_avatar_speech`` with the operator's
    script. The spokesperson's bound avatar provides the voice;
    Runway's ``/v1/avatar_videos`` produces a lip-synced
    talking-head clip.

    Args:
        workspace: Composition's workspace anchor (V0 contract
            rule 1). Must contain ``spokesperson``.
        spokesperson: Who's on camera. Must have
            ``runway_avatar_id`` set — primitive will fail at
            execute time otherwise. The V0 design lock
            classifies "avatar missing" as a clean
            ``PrimitiveError`` rather than a runtime crash.
        script: Words the avatar should speak. Required.
        use_knowledge: When True, the primitive pipes the
            script through K6's ``build_render_brief`` before
            firing media-engine — the synthesized brief replaces
            the raw script and the retrieved chunk ids land on
            the output asset's ``source_spec``.
        mock_mode: Run the composition in mock-mode (V0 contract
            rule 9). Deterministic stub asset, no Runway call.
        name: Operator-visible name. Defaults to
            "Talking-head — {spokesperson.name}".
        created_by: Optional User for audit attribution.

    Returns:
        The fresh ``Composition`` row. Caller should enqueue
        ``execute_composition.delay(str(comp.id))`` to run it.
    """
    if not script.strip():
        raise ValueError("talking_head starter requires a non-empty script")
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError(
            f"spokesperson {spokesperson.name!r} (workspace "
            f"{spokesperson.workspace_id}) is not in workspace "
            f"{workspace.pk}"
        )

    composition_name = name.strip() or f"Talking-head — {spokesperson.name}"
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=composition_name,
        template_kind="talking_head",
        mock_mode=mock_mode,
        created_by=created_by,
    )
    step_params: dict = {
        "script": script.strip(),
        "use_knowledge": bool(use_knowledge),
    }
    # K6.4 v1.1 — per-render verifier mode. Only stored when
    # the caller passed one; otherwise the primitive's lookup
    # falls back to settings.K6_CLAIM_VERIFIER_MODE.
    if verifier_mode:
        step_params["verifier_mode"] = verifier_mode
    # K6.6 — opener override. Empty / None ⇒ model picks under
    # the system prompt's standalone-video framing.
    if opener and opener.strip():
        step_params["opener"] = opener.strip()

    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="generate_avatar_speech",
        inputs=[],
        params=step_params,
    )

    logger.info(
        "starter talking_head created composition=%s spokesperson=%s "
        "mock=%s use_knowledge=%s verifier_mode=%s opener=%s",
        composition.id, spokesperson.id, mock_mode, use_knowledge,
        verifier_mode or "(default)",
        "set" if (opener and opener.strip()) else "(default)",
    )
    return composition


@transaction.atomic
def cinematic_visual(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    prompt: str,
    prompt_image: str | None = None,
    ratio: str | None = None,
    duration: int | None = None,
    # SESSION 199 — outro_text parity. Optional 3s white-on-black
    # outro appended after the generate_visual_clip step. Blank =
    # skip (existing 1-step shape preserved).
    outro_text: str | None = None,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Create a single-step ``cinematic_visual`` composition.

    One step: ``generate_visual_clip`` with the operator's
    prompt. Silent visual output — no avatar, no speech. Use for
    cinematic backdrops, b-roll, or standalone visual ads.

    Routes through Runway's ``gen4_turbo`` (image-to-video) when
    ``prompt_image`` is supplied, ``gen4.5`` (text-to-video)
    otherwise.

    Args:
        workspace: Composition's workspace anchor (V0 contract
            rule 1). Must contain ``spokesperson``.
        spokesperson: Brand owner for the clip — required on
            Composition even though the visual itself doesn't
            feature the avatar. The clip belongs to "Sasha's
            brand" even if Sasha isn't on screen.
        prompt: Visual prompt for Runway. Required.
        prompt_image: Optional reference image URL. When
            present, drives the ``gen4_turbo`` image-to-video
            path. Mirrors V13's eventual ``generate_image`` →
            ``generate_visual_clip`` chain via the
            ``reference_image`` input slot, but takes
            precedence over it when both are provided.
        ratio: ``1280:720`` | ``720:1280`` | ``960:960``.
            Server-side default ``1280:720``.
        duration: Output length in seconds. ``gen4_turbo``
            accepts ``{5}``; ``gen4.5`` accepts ``{5, 8, 10}``.
            Server-side default 5.
        mock_mode: Run in mock-mode (V0 contract rule 9).
        name: Operator-visible name. Defaults to
            "Cinematic visual — {prompt[:40]}".
        created_by: Optional User for audit attribution.

    Returns:
        The fresh ``Composition`` row. Caller enqueues
        ``execute_composition.delay(str(comp.id))`` to run it.
    """
    if not prompt.strip():
        raise ValueError("cinematic_visual starter requires a non-empty prompt")
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError(
            f"spokesperson {spokesperson.name!r} (workspace "
            f"{spokesperson.workspace_id}) is not in workspace "
            f"{workspace.pk}"
        )

    composition_name = name.strip() or f"Cinematic visual — {prompt[:40]}"
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=composition_name,
        template_kind="cinematic_visual",
        mock_mode=mock_mode,
        created_by=created_by,
    )
    params: dict[str, object] = {"prompt": prompt.strip()}
    if prompt_image is not None:
        params["prompt_image"] = prompt_image
    if ratio is not None:
        params["ratio"] = ratio
    if duration is not None:
        params["duration"] = duration

    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="generate_visual_clip",
        inputs=[],
        params=params,
    )

    # SESSION 199 — optional brand outro card.
    cleaned_outro = (outro_text or "").strip()
    if cleaned_outro:
        CompositionStep.objects.create(
            composition=composition,
            position=1,
            primitive="add_intro_outro",
            inputs=[{"slot": "base", "from_step_position": 0}],
            params={
                "outro": {
                    "text": cleaned_outro,
                    "duration_s": 3.0,
                },
            },
        )

    logger.info(
        "starter cinematic_visual created composition=%s spokesperson=%s "
        "mock=%s has_image=%s ratio=%s duration=%s outro=%s",
        composition.id, spokesperson.id, mock_mode,
        bool(prompt_image), ratio, duration, bool(cleaned_outro),
    )
    return composition


# ---- V17.2: cinematic_visual_extended ----------------------------
#
# SESSION 182 / V17.2. Chain V17.1's extend_visual_clip primitive
# off V4's generate_visual_clip to produce a cinematic clip
# longer than Runway's 10s per-render ceiling.
#
# Chain shape:
#
#   Step 0:        generate_visual_clip (duration=10, gen4.5 text-to-video)
#   Step 1..N:     extend_visual_clip (duration=5, gen4_turbo
#                  image-to-video conditioned on prior step's last frame)
#
# where N = (target_duration - 10) / 5. Q-v17-1 resolution shapes
# this — the extend primitive uses gen4_turbo image-to-video
# (always 5s per call), so all extend segments are exactly 5s.
# Base step uses gen4.5 (no prompt_image) so we get a clean 10s
# base. Operators wanting an image-conditioned base should use
# the V17.3 keyframe_shot recipe instead.
#
# Supported target_duration values: 15, 20, 25, 30, 40, 50 seconds
# (multiples of 5 ≥ 15). Larger values are deliberately restricted
# — beyond ~50s the operator should compose with long_form_ad or
# concat instead of relying on a single visual continuation chain.

_EXTENDED_BASE_DURATION_SECONDS = 10
_EXTENDED_SEGMENT_DURATION_SECONDS = 5
_EXTENDED_VALID_TARGETS = (15, 20, 25, 30, 40, 50)


@transaction.atomic
def cinematic_visual_extended(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    prompt: str,
    target_duration: int | str,
    ratio: str | None = None,
    seed: int | None = None,
    # SESSION 199 — outro_text parity. Optional 3s white-on-black
    # outro appended after the extend chain. Blank = skip.
    outro_text: str | None = None,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Create a multi-step cinematic clip longer than Runway's
    per-render 10s ceiling.

    Chain:
      Step 0: generate_visual_clip (10s, text-to-video via gen4.5)
      Steps 1..N: extend_visual_clip (5s each, conditioned on
                  the prior step's last frame via Runway gen4_turbo)

    where N = (target_duration - 10) / 5.

    Per V17 contract rules 10 + 12: each extend step is one
    primitive call emitting one CLIP Asset; the V4 generate
    base + N extends compose linearly (rule 5 — no DAG). All
    steps share one prompt for v1 simplicity; future v2 could
    accept per-step continuation prompts via separate fields.

    Args:
        workspace: Composition workspace anchor.
        spokesperson: Brand owner (same shape as cinematic_visual —
            required even though the avatar isn't on screen).
        prompt: Shared visual prompt across base + all extend
            steps. Required.
        target_duration: Final clip duration in seconds. Must
            be one of {15, 20, 25, 30, 40, 50}.
        ratio: ``1280:720`` | ``720:1280`` | ``960:960``. Default
            ``1280:720``. All steps use the same ratio.
        seed: Optional Runway seed for visual coherence across
            the chain. Passed to every extend step (the base
            generate doesn't currently accept seed, but recording
            it here keeps audit clean).
        mock_mode: Run in mock-mode (V0 contract rule 9).
        name: Operator-visible name. Defaults to
            "Cinematic visual {target}s — {prompt[:40]}".
        created_by: Optional User for audit attribution.

    Returns:
        Fresh ``Composition`` with 1 + N steps laid down.

    Raises:
        ``ValueError`` for empty prompt, cross-workspace
        spokesperson, or unsupported target_duration.
    """
    if not prompt.strip():
        raise ValueError(
            "cinematic_visual_extended starter requires a non-empty prompt"
        )
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError(
            f"spokesperson {spokesperson.name!r} (workspace "
            f"{spokesperson.workspace_id}) is not in workspace "
            f"{workspace.pk}"
        )
    # Coerce the SPA-submitted string ("15") to int. The recipe's
    # ``select`` field carries string choice values per the SPA
    # Zod schema (see web/src/lib/api/recipes.ts); the starter
    # accepts either str or int so direct Python callers (tests,
    # CLI scripts) don't have to wrap their ints in strings.
    try:
        target_duration_int = int(target_duration)
    except (TypeError, ValueError):
        raise ValueError(
            f"target_duration must be an integer or numeric string; "
            f"got {target_duration!r}"
        )
    if target_duration_int not in _EXTENDED_VALID_TARGETS:
        raise ValueError(
            f"target_duration must be one of "
            f"{list(_EXTENDED_VALID_TARGETS)}; got {target_duration_int}"
        )

    # N = number of extend steps after the base 10s.
    extend_count = (
        target_duration_int - _EXTENDED_BASE_DURATION_SECONDS
    ) // _EXTENDED_SEGMENT_DURATION_SECONDS

    composition_name = (
        name.strip()
        or f"Cinematic visual {target_duration}s — {prompt[:40]}"
    )
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=composition_name,
        template_kind="cinematic_visual_extended",
        mock_mode=mock_mode,
        created_by=created_by,
    )

    # Step 0: base generate_visual_clip. text-to-video (no
    # prompt_image) so we get the gen4.5 10s output, not the
    # gen4_turbo 5s. Same kwargs shape as cinematic_visual but
    # duration locked to 10.
    base_params: dict[str, object] = {
        "prompt": prompt.strip(),
        "duration": _EXTENDED_BASE_DURATION_SECONDS,
    }
    if ratio is not None:
        base_params["ratio"] = ratio
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="generate_visual_clip",
        inputs=[],
        params=base_params,
    )

    # Steps 1..N: extend_visual_clip, each consuming the prior
    # step's output. Linear chain — V1 rule 5 + V17 rule 10.
    for i in range(extend_count):
        step_position = i + 1
        prior_position = step_position - 1
        extend_params: dict[str, object] = {
            "prompt": prompt.strip(),
            "duration": _EXTENDED_SEGMENT_DURATION_SECONDS,
        }
        if ratio is not None:
            extend_params["ratio"] = ratio
        if seed is not None:
            extend_params["seed"] = seed
        CompositionStep.objects.create(
            composition=composition,
            position=step_position,
            primitive="extend_visual_clip",
            inputs=[
                {"slot": "source", "from_step_position": prior_position},
            ],
            params=extend_params,
        )

    # SESSION 199 — optional brand outro card. Position is after
    # the last extend step (or the base if extend_count=0, though
    # the valid_targets all require ≥1 extend).
    last_chain_position = extend_count  # base=0, then N extends → last is at position N
    cleaned_outro = (outro_text or "").strip()
    if cleaned_outro:
        CompositionStep.objects.create(
            composition=composition,
            position=last_chain_position + 1,
            primitive="add_intro_outro",
            inputs=[{"slot": "base", "from_step_position": last_chain_position}],
            params={
                "outro": {
                    "text": cleaned_outro,
                    "duration_s": 3.0,
                },
            },
        )

    logger.info(
        "starter cinematic_visual_extended created composition=%s "
        "spokesperson=%s mock=%s target=%ds extends=%d ratio=%s seed=%s outro=%s",
        composition.id, spokesperson.id, mock_mode,
        target_duration, extend_count, ratio, seed, bool(cleaned_outro),
    )
    return composition


@transaction.atomic
def long_form_ad(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    script: str,
    max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
    use_llm_split: bool = False,
    use_knowledge: bool = False,
    reencode_concat: bool = False,
    # SESSION 198 — outro_text parity with the cinematic recipes.
    # Optional 3-second white-on-black outro card appended after
    # the concat (or after the lone speech step on the degenerate
    # single-chunk path). Blank / whitespace-only = skip.
    outro_text: str | None = None,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
    verifier_mode: str | None = None,
    opener: str | None = None,
) -> Composition:
    """Create a long-form ad composition: split → N× speak → concat.

    No AI video provider ships single-call generation longer than
    ~20 seconds — every long-form AI video output in the wild is
    stitched. This starter is the platform's launch
    differentiator. The script gets pre-split into chunks at
    sentence boundaries (≤ ``max_chars`` per chunk to fit
    Runway's ``/v1/avatar_videos`` per-call ceiling), then a
    fixed N+1-step composition is laid down:

      Step 0..N-1: generate_avatar_speech (one per chunk)
      Step N: concat_clips (consumes all prior step outputs)

    The split happens **at starter time**, not at runtime —
    contract rule 5 (linear ordering only) means the
    composition needs a deterministic step count when it
    runs. The runtime then just walks the plan.

    Args:
        workspace: Composition workspace anchor.
        spokesperson: Who's on camera. Must have a runway
            avatar (the speech primitive validates).
        script: Long-form script. The whole thing is what
            the spokesperson will say across the chunks.
        max_chars: Per-chunk character cap. Defaults to
            ``DEFAULT_CHUNK_MAX_CHARS`` (280).
        use_llm_split: When True, the splitter consults
            gpt-5-mini for semantically clean boundaries
            (graceful fallback to naive on any failure).
            Default False — naive is deterministic and free.
        use_knowledge: When True, each speech step pipes its
            chunk through K6's ``build_render_brief`` before
            firing media-engine. The same chunk text becomes
            knowledge-informed per-step. Costs N synthesis
            calls instead of 1; tradeoff worth measuring.
        reencode_concat: Forces filter_complex normalization
            during concat. Default False uses the demuxer
            (-c copy) — fast, requires uniform inputs.
            Long-form ads are uniform (all gwm1_avatars),
            so False is safe.
        mock_mode: Run in mock-mode (V0 contract rule 9).
            All chunks render deterministic stubs; concat
            returns a stub output. End-to-end test-runnable.
        name: Operator-visible name. Defaults to
            "Long-form — {first 40 chars of script}".
        created_by: Optional User for audit attribution.

    Returns:
        The fresh ``Composition`` row with N+1 (or 1) steps
        already laid down. Caller enqueues
        ``execute_composition.delay(str(comp.id))`` to run.

    Raises:
        ``ValueError`` for empty script, cross-workspace
        spokesperson, or a splitter that produces zero
        chunks (impossible in practice, but defensive).
    """
    if not script.strip():
        raise ValueError("long_form_ad starter requires a non-empty script")
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError(
            f"spokesperson {spokesperson.name!r} (workspace "
            f"{spokesperson.workspace_id}) is not in workspace "
            f"{workspace.pk}"
        )

    # Pre-split at starter time. Choose path based on use_llm_split
    # (always naive when mock_mode — no point calling the LLM if
    # the renders are stubs).
    if use_llm_split and not mock_mode:
        chunks = split_script_with_llm(script, max_chars=max_chars)
    else:
        chunks = chunk_script(script, max_chars=max_chars)

    if not chunks:
        raise ValueError(
            "long_form_ad splitter produced zero chunks from "
            f"a {len(script)}-char input"
        )

    composition_name = name.strip() or f"Long-form — {script.strip()[:40]}"
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=composition_name,
        template_kind="long_form_ad",
        mock_mode=mock_mode,
        created_by=created_by,
    )

    # Lay down one generate_avatar_speech step per chunk.
    # K6.6 — opener applies only to the FIRST chunk; later
    # chunks continue the same script, so re-opening them with
    # the same line would be redundant.
    for i, chunk in enumerate(chunks):
        step_params: dict = {
            "script": chunk,
            "use_knowledge": bool(use_knowledge),
        }
        # K6.4 v1.1 — per-render verifier mode applies to every
        # synthesis step in the composition (one per chunk).
        if verifier_mode:
            step_params["verifier_mode"] = verifier_mode
        if i == 0 and opener and opener.strip():
            step_params["opener"] = opener.strip()
        CompositionStep.objects.create(
            composition=composition,
            position=i,
            primitive="generate_avatar_speech",
            inputs=[],
            params=step_params,
        )

    # Optimization: skip the concat step when there's exactly one
    # chunk — the composition is functionally identical to
    # ``talking_head``. Keeps the data clean (no degenerate
    # 1-input concat).
    last_output_position = len(chunks) - 1  # the final speech step
    if len(chunks) > 1:
        concat_inputs = [
            {"slot": "clip", "from_step_position": i}
            for i in range(len(chunks))
        ]
        # SESSION 198 slice C — long_form_ad's concat output is
        # extended talking-head content (N chunked avatar
        # speeches stitched together), not a backdrop. Pass
        # ``result_role=talking_head`` to the concat primitive
        # (introduced SESSION 196) so the final lands with the
        # right role + stays out of the A7 backdrop_clip_id
        # picker.
        CompositionStep.objects.create(
            composition=composition,
            position=len(chunks),
            primitive="concat_clips",
            inputs=concat_inputs,
            params={
                "reencode": bool(reencode_concat),
                "result_role": "talking_head",
            },
        )
        last_output_position = len(chunks)

    # SESSION 198 — optional brand outro card. Appended after the
    # last step (concat or lone speech). Blank = skip.
    cleaned_outro = (outro_text or "").strip()
    if cleaned_outro:
        CompositionStep.objects.create(
            composition=composition,
            position=last_output_position + 1,
            primitive="add_intro_outro",
            inputs=[{"slot": "base", "from_step_position": last_output_position}],
            params={
                "outro": {
                    "text": cleaned_outro,
                    "duration_s": 3.0,
                },
            },
        )

    logger.info(
        "starter long_form_ad created composition=%s spokesperson=%s "
        "mock=%s chunks=%d use_llm_split=%s use_knowledge=%s outro=%s",
        composition.id, spokesperson.id, mock_mode,
        len(chunks), use_llm_split, use_knowledge,
        bool(cleaned_outro),
    )
    return composition


# ---- V7 layout-modifier starters ---------------------------------
#
# Each starter takes one or more existing CLIP/AUDIO Assets and
# creates a single-step Composition that produces a new composited
# Asset. These are "modifier compositions" — they don't generate
# new clips, they recombine ones the operator already has.
#
# All five share a pattern: validate the input assets against the
# composition's workspace, build a one-step Composition with the
# right primitive + layout_spec/mix_spec, return it. The
# CompositionStep's ``inputs`` list references each Asset by id.


def _validate_workspace_assets(
    workspace: "Workspace",
    assets: list,
) -> None:
    """Defense in depth — the V1 signal already rejects
    cross-workspace asset references at save time. Catching it
    in the starter gives the operator a clearer error message
    than the signal's ValidationError."""
    for a in assets:
        if a.workspace_id != workspace.pk:
            raise ValueError(
                f"asset {a.id} (workspace {a.workspace_id}) is not in "
                f"workspace {workspace.pk}"
            )


@transaction.atomic
def pip_layout(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    base_clip,
    pip_clip,
    pip_width: int = 360,
    margin_x: int = 40,
    margin_y: int = 40,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Picture-in-picture layout. ``pip_clip`` overlays
    bottom-right on ``base_clip`` with a white border tile.
    Audio = base."""
    _validate_workspace_assets(workspace, [base_clip, pip_clip])
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError("spokesperson not in workspace")

    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=name.strip() or "PiP layout",
        template_kind="pip_layout",
        mock_mode=mock_mode,
        created_by=created_by,
    )
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="composite_video",
        inputs=[
            {"slot": "base", "asset_id": str(base_clip.id)},
            {"slot": "pip", "asset_id": str(pip_clip.id)},
        ],
        params={
            "layout_spec": {
                "kind": "pip",
                "options": {
                    "pip_width": pip_width,
                    "margin_x": margin_x,
                    "margin_y": margin_y,
                },
            },
        },
    )
    return composition


@transaction.atomic
def backdrop_layout(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    background_clip,
    foreground_clip,
    fg_width: int = 320,
    margin_x: int = 40,
    margin_y: int = 40,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Backdrop layout — the V8 building block.

    Inputs are ordered (background, foreground); ffmpeg uses
    input 0 as the canvas size, so the cinematic backdrop is
    [0] and the avatar tile is [1]. Audio = foreground avatar.

    This is the primitive shape ``talking_head_with_backdrop``
    (V8) composes on top of.
    """
    _validate_workspace_assets(workspace, [background_clip, foreground_clip])
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError("spokesperson not in workspace")

    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=name.strip() or "Backdrop layout",
        template_kind="backdrop_layout",
        mock_mode=mock_mode,
        created_by=created_by,
    )
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="composite_video",
        inputs=[
            {"slot": "background", "asset_id": str(background_clip.id)},
            {"slot": "foreground", "asset_id": str(foreground_clip.id)},
        ],
        params={
            "layout_spec": {
                "kind": "backdrop",
                "options": {
                    "fg_width": fg_width,
                    "margin_x": margin_x,
                    "margin_y": margin_y,
                },
            },
        },
    )
    return composition


@transaction.atomic
def cohost_layout(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    main_clip,
    cohost_clip,
    cohost_width: int = 240,
    margin_x: int = 40,
    margin_y: int = 40,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Cohost layout — main avatar with smaller cohost tile in
    the top-left corner. Audio = main."""
    _validate_workspace_assets(workspace, [main_clip, cohost_clip])
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError("spokesperson not in workspace")

    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=name.strip() or "Cohost layout",
        template_kind="cohost_layout",
        mock_mode=mock_mode,
        created_by=created_by,
    )
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="composite_video",
        inputs=[
            {"slot": "main", "asset_id": str(main_clip.id)},
            {"slot": "cohost", "asset_id": str(cohost_clip.id)},
        ],
        params={
            "layout_spec": {
                "kind": "cohost",
                "options": {
                    "cohost_width": cohost_width,
                    "margin_x": margin_x,
                    "margin_y": margin_y,
                },
            },
        },
    )
    return composition


@transaction.atomic
def broll_splice(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    base_clip,
    broll_clip,
    cutaway_start_s: float,
    cutaway_end_s: float,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """B-roll cutaway — splice a cinematic clip into the middle
    of an avatar's timeline at ``[cutaway_start_s, cutaway_end_s]``.
    Audio stays from the base avatar (the cutaway is
    video-only). The window must be strictly inside the base
    clip's duration.
    """
    _validate_workspace_assets(workspace, [base_clip, broll_clip])
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError("spokesperson not in workspace")
    if cutaway_end_s <= cutaway_start_s:
        raise ValueError(
            "broll cutaway_end_s must be greater than cutaway_start_s"
        )

    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=name.strip() or "B-roll splice",
        template_kind="broll_splice",
        mock_mode=mock_mode,
        created_by=created_by,
    )
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="composite_video",
        inputs=[
            {"slot": "base", "asset_id": str(base_clip.id)},
            {"slot": "broll", "asset_id": str(broll_clip.id)},
        ],
        params={
            "layout_spec": {
                "kind": "broll",
                "options": {
                    "cutaway_start_s": float(cutaway_start_s),
                    "cutaway_end_s": float(cutaway_end_s),
                },
            },
        },
    )
    return composition


@transaction.atomic
def talking_head_with_backdrop(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    script: str,
    backdrop_prompt: str = "",
    backdrop_ratio: str | None = None,
    backdrop_duration: int | None = None,
    fg_width: int = 320,
    margin_x: int = 40,
    margin_y: int = 40,
    use_knowledge: bool = False,
    # SESSION 179 / V16. When True, insert a
    # remove_avatar_background step between speech + composite
    # so the avatar tile rides over the backdrop without the
    # baked-in Runway white square. Default off — the matting
    # pipeline is slow (~2.4 min for a 22s clip on CPU) and the
    # operator may not always want to pay that latency.
    remove_avatar_bg: bool = False,
    # SESSION 183 / V17.5. When True, swap the N×generate +
    # concat backdrop chain for a 1×generate + N×extend chain
    # (last-frame-conditioned via Runway gen4_turbo). Removes
    # the visible 10s motion seams of the concat path. Default
    # off — V17 contract rule 12 (V13/V8 keep current
    # behaviour; new optional kwargs only). When this flag is
    # True, ``backdrop_duration`` is ignored (chain segments
    # are fixed at 10s base + 5s per extend per the Runway
    # gen4_turbo per-render limit).
    use_extend_for_backdrop: bool = False,
    # SESSION 184 / V18 — pre-recorded backdrop library. When
    # supplied, the picked CLIP is wired directly as the
    # composite background — no generate / extend / concat
    # chain fires. Saves the $1.25-$1.75 Runway backdrop cost
    # per render and turns iterative script tuning into a free
    # operation. ``backdrop_prompt`` / ``backdrop_ratio`` /
    # ``backdrop_duration`` / ``use_extend_for_backdrop`` are
    # all ignored on this path (the picked clip is the source
    # of truth for the backdrop's pixels + duration).
    backdrop_clip: "Asset | None" = None,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
    verifier_mode: str | None = None,
    opener: str | None = None,
) -> Composition:
    """Avatar talking over a cinematic backdrop. The first
    multi-step starter that combines V3 + V4 + V7's
    composite_video primitive.

    Three steps:

      Step 0 — generate_visual_clip (cinematic backdrop):
        Runway gen4_turbo (image-to-video, if prompt_image
        supplied via ratio params later) or gen4.5
        (text-to-video). Produces a silent cinematic clip
        sized to the composition's target aspect ratio.

      Step 1 — generate_avatar_speech (avatar talking):
        Runway gwm1_avatars. Produces a talking-head clip
        with audio. Knowledge integration (K6) optional
        via ``use_knowledge``.

      Step 2 — composite_video kind=backdrop:
        Step 0's output is the background canvas; step 1's
        output is the foreground avatar tile in top-right
        corner. Audio map = foreground (avatar).

    Args:
        workspace: Composition workspace anchor.
        spokesperson: Avatar identity for the speech step.
            Must have a runway_avatar_id.
        script: Words the avatar should say.
        backdrop_prompt: Visual prompt for the cinematic
            backdrop. Goes to generate_visual_clip's prompt
            param.
        backdrop_ratio: Optional aspect ratio for the
            backdrop. Defaults to media-engine's server-side
            default (1280:720).
        backdrop_duration: Optional output duration in
            seconds for the backdrop. The avatar clip's
            duration is controlled by Runway based on script
            length; for clean composite the backdrop should
            be at least as long as the avatar (the composite
            primitive trims to the shorter input).
        fg_width: Width in pixels of the avatar tile in the
            backdrop composite. Default 320 (~25% of a
            720p backdrop).
        margin_x, margin_y: Avatar tile margin from
            top-right corner.
        use_knowledge: Pipe the speech script through K6's
            build_render_brief synthesis.
        mock_mode: Run the composition in mock-mode (V0
            contract rule 9). All three steps short-circuit
            to deterministic stub assets; end-to-end
            test-runnable.
        name: Operator-visible name. Defaults to
            "Avatar over backdrop — {first 40 chars of script}".
        created_by: Optional User for audit attribution.

    Returns:
        The fresh ``Composition`` with 3 steps laid down.
        Caller enqueues ``execute_composition.delay()``.
    """
    if not script.strip():
        raise ValueError("talking_head_with_backdrop requires a non-empty script")
    # SESSION 184 / V18 — XOR validation. Exactly one of
    # (backdrop_prompt, backdrop_clip) must produce a backdrop. When
    # both are supplied, backdrop_clip wins (the operator's explicit
    # intent — they picked a clip; the prompt is ignored). When
    # neither is supplied, fail loud so the operator gets an
    # actionable error instead of a render with a blank backdrop.
    if backdrop_clip is None and not backdrop_prompt.strip():
        raise ValueError(
            "talking_head_with_backdrop requires either a non-empty "
            "backdrop_prompt or a picked backdrop_clip"
        )
    if backdrop_clip is not None:
        # Defense-in-depth — the recipe resolver already filters to
        # the workspace + CLIP type, but the starter is callable
        # programmatically too (admin / tests / future API).
        _validate_workspace_assets(workspace, [backdrop_clip])
        # Import inside the function to avoid the runtime/TYPE_CHECKING
        # circular import; AssetType is a TextChoices class.
        from .models import AssetType as _AssetType

        if backdrop_clip.asset_type != _AssetType.CLIP:
            raise ValueError(
                f"backdrop_clip must be a CLIP asset; got "
                f"{backdrop_clip.asset_type}"
            )
        # SESSION 184 — depend on slice 1's composite_video null-
        # duration guard. A picked clip without duration_ms would
        # let the composite trim use the speech duration but the
        # speech is the SHORT input on a saved-backdrop render, so
        # the composite would pick the backdrop's null and fall back
        # to the base clip's frame count. Refuse early with a
        # better error than the composite primitive's downstream one.
        if backdrop_clip.duration_ms is None:
            raise ValueError(
                f"backdrop_clip {backdrop_clip.id} has duration_ms=None; "
                f"the upstream primitive that produced it didn't persist "
                f"a duration. Fix that primitive first or use a clip "
                f"whose duration was recorded at create time."
            )
        # SESSION 194 V18 polish — duration-mismatch starter warning.
        # SESSION 184 dogfood #2 finding: when the picked backdrop is
        # shorter than the estimated speech, composite_video trims
        # the speech mid-sentence (it always trims the longer input
        # down to the shorter one). The bug surfaced live in the
        # SESSION 184 V18 dogfood — Riggs cut off at 5s because the
        # operator picked a 5s gen3a_turbo smoke as backdrop for a
        # ~9s speech.
        #
        # Refuse the render at starter time with an operator-
        # actionable message naming both durations + the script
        # length + the two ways to fix it (longer backdrop or shorter
        # script). Uses ``_estimate_avatar_speech_seconds`` which
        # adds a 2s safety buffer — the check effectively requires
        # backdrop ≥ estimated_speech + 2s, which protects against
        # Runway returning a clip slightly longer than the tight
        # estimate.
        estimated_speech_seconds = _estimate_avatar_speech_seconds(
            len(script.strip()),
        )
        backdrop_seconds = backdrop_clip.duration_ms // 1000
        if backdrop_seconds < estimated_speech_seconds:
            raise ValueError(
                f"backdrop_clip {backdrop_clip.id} is "
                f"{backdrop_seconds}s long but the estimated speech "
                f"duration is {estimated_speech_seconds}s "
                f"(script: {len(script.strip())} chars). The composite "
                f"primitive trims the longer input to the shorter one — "
                f"with this combination, the avatar speech would be cut "
                f"off mid-sentence. Either pick a backdrop_clip that's "
                f"at least {estimated_speech_seconds}s long or shorten "
                f"the script to roughly "
                f"{backdrop_seconds * _AVATAR_SPEECH_CHARS_PER_SECOND} "
                f"characters or fewer."
            )
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError(
            f"spokesperson {spokesperson.name!r} (workspace "
            f"{spokesperson.workspace_id}) is not in workspace "
            f"{workspace.pk}"
        )

    composition_name = (
        name.strip() or f"Avatar over backdrop — {script.strip()[:40]}"
    )
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=composition_name,
        template_kind="talking_head_with_backdrop",
        mock_mode=mock_mode,
        created_by=created_by,
    )

    # SESSION 179 — multi-backdrop chain (concat path). gen4.5
    # caps at 10s per clip; if we generate a single 10s backdrop
    # and the avatar speech is 22s, composite_video used to loop
    # the backdrop 2.2x (visible as a 3-second motion seam
    # repeating). Instead, we estimate the speech duration from
    # script length and lay down N backdrops sized so concat(N) ≥
    # speech duration. The composite primitive trims the long
    # edge automatically. N is clamped to
    # ``_MAX_BACKDROP_CHAIN_LENGTH`` so a pathological script
    # can't spin up runaway Runway calls.
    #
    # SESSION 183 / V17.5 — extend-chain path. When
    # ``use_extend_for_backdrop=True``, the visible 10s motion
    # seams of the concat path are eliminated by replacing the
    # N×generate chain with a 1×generate + N×extend chain where
    # each extend conditions on the prior segment's last frame.
    # Default off; V17 contract rule 12 keeps existing recipes
    # unchanged.
    #
    # SESSION 184 / V18 — picked-clip path. When ``backdrop_clip``
    # is supplied, both backdrop-generation paths are skipped; the
    # picked CLIP is wired straight into the composite as the
    # background. Operator-visible win: $1.25-$1.75 saved per
    # render and zero Runway latency on backdrop iteration.
    script_clean = script.strip()

    if backdrop_clip is not None:
        # V18 path — short-circuit. Three steps:
        #   0: generate_avatar_speech
        #   1 (optional, V16): remove_avatar_background
        #   N: composite_video, background = picked Asset
        speech_params: dict = {
            "script": script_clean,
            "use_knowledge": bool(use_knowledge),
        }
        if verifier_mode:
            speech_params["verifier_mode"] = verifier_mode
        if opener and opener.strip():
            speech_params["opener"] = opener.strip()
        CompositionStep.objects.create(
            composition=composition,
            position=0,
            primitive="generate_avatar_speech",
            inputs=[],
            params=speech_params,
        )

        if remove_avatar_bg:
            CompositionStep.objects.create(
                composition=composition,
                position=1,
                primitive="remove_avatar_background",
                inputs=[{"slot": "clip", "from_step_position": 0}],
                params={},
            )
            foreground_source_position = 1
            composite_position = 2
        else:
            foreground_source_position = 0
            composite_position = 1

        # Composite — background is the picked Asset (referenced
        # by asset_id, the same shape pip_layout / cohost_layout /
        # broll_splice use). Foreground is the speech step (or its
        # matted derivative).
        CompositionStep.objects.create(
            composition=composition,
            position=composite_position,
            primitive="composite_video",
            inputs=[
                {"slot": "background", "asset_id": str(backdrop_clip.id)},
                {
                    "slot": "foreground",
                    "from_step_position": foreground_source_position,
                },
            ],
            params={
                "layout_spec": {
                    "kind": "backdrop",
                    "options": {
                        "fg_width": fg_width,
                        "margin_x": margin_x,
                        "margin_y": margin_y,
                    },
                },
            },
        )

        logger.info(
            "starter talking_head_with_backdrop (V18 picked-clip) "
            "created composition=%s spokesperson=%s mock=%s "
            "use_knowledge=%s fg_width=%d backdrop_clip=%s "
            "backdrop_clip_duration_ms=%s remove_avatar_bg=%s",
            composition.id, spokesperson.id, mock_mode, use_knowledge,
            fg_width, backdrop_clip.id, backdrop_clip.duration_ms,
            remove_avatar_bg,
        )
        return composition

    if use_extend_for_backdrop:
        # V17.5 path. Fixed segment durations (10s base + 5s per
        # extend) — backdrop_duration is ignored. Build a base
        # generate_visual_clip + N extend_visual_clip chain.
        n_extends = _compute_extend_backdrop_chain_length(
            len(script_clean),
        )

        # Step 0 — base 10s generate_visual_clip. Same params
        # shape as the concat path's first backdrop step, but
        # duration is locked to 10 (gen4.5 text-to-video
        # ceiling).
        base_params: dict[str, object] = {
            "prompt": backdrop_prompt.strip(),
            "duration": _EXTEND_BASE_DURATION_SECONDS,
        }
        if backdrop_ratio is not None:
            base_params["ratio"] = backdrop_ratio
        CompositionStep.objects.create(
            composition=composition,
            position=0,
            primitive="generate_visual_clip",
            inputs=[],
            params=dict(base_params),
        )

        # Steps 1..N — extend_visual_clip, each consuming the
        # prior step's output (V1 rule 5 — linear chain; V17
        # rule 10 — one primitive per step).
        for i in range(n_extends):
            step_position = i + 1
            prior_position = step_position - 1
            extend_params: dict[str, object] = {
                "prompt": backdrop_prompt.strip(),
                "duration": _EXTEND_SEGMENT_DURATION_SECONDS,
            }
            if backdrop_ratio is not None:
                extend_params["ratio"] = backdrop_ratio
            CompositionStep.objects.create(
                composition=composition,
                position=step_position,
                primitive="extend_visual_clip",
                inputs=[
                    {"slot": "source", "from_step_position": prior_position},
                ],
                params=extend_params,
            )

        # The last extend's output is the final backdrop —
        # composite_video uses it directly, no concat step.
        background_source = n_extends  # position of last clip
        speech_position = n_extends + 1
        next_position_after_speech = speech_position + 1
        # ``backdrop_seconds`` is unused on this path, but
        # logged below for parity with the concat path's log
        # line.
        backdrop_seconds = _EXTEND_BASE_DURATION_SECONDS
        n_backdrops_for_log = 1 + n_extends
    else:
        # SESSION 179 — multi-backdrop concat path. Unchanged.
        backdrop_seconds = (
            backdrop_duration or _DEFAULT_BACKDROP_DURATION_SECONDS
        )
        n_backdrops = _compute_backdrop_chain_length(
            len(script_clean), backdrop_seconds,
        )

        # Steps 0..N-1 — N cinematic backdrops. Each carries the
        # same prompt + duration so they read as continuous
        # motion when concat'd. (Future tuning: vary the prompts
        # per chunk to give the operator narrative B-roll
        # variety.)
        base_backdrop_params: dict[str, object] = {
            "prompt": backdrop_prompt.strip(),
            "duration": backdrop_seconds,
        }
        if backdrop_ratio is not None:
            base_backdrop_params["ratio"] = backdrop_ratio
        for i in range(n_backdrops):
            CompositionStep.objects.create(
                composition=composition,
                position=i,
                primitive="generate_visual_clip",
                inputs=[],
                params=dict(base_backdrop_params),
            )

        speech_position = n_backdrops
        next_position_after_speech = speech_position + 1
        n_backdrops_for_log = n_backdrops

        # Set background_source after the (optional) concat
        # step below so the existing N>1 / N==1 branching is
        # preserved on this path.
        background_source = None  # filled in below

    # Step N — avatar speech. Same on both paths.
    speech_params: dict = {
        "script": script_clean,
        "use_knowledge": bool(use_knowledge),
    }
    if verifier_mode:
        speech_params["verifier_mode"] = verifier_mode
    if opener and opener.strip():
        speech_params["opener"] = opener.strip()
    CompositionStep.objects.create(
        composition=composition,
        position=speech_position,
        primitive="generate_avatar_speech",
        inputs=[],
        params=speech_params,
    )

    next_position = next_position_after_speech

    if not use_extend_for_backdrop:
        # Concat-path: optional concat step + background_source
        # resolution. Skipped on the extend path because each
        # extend already chains to the prior segment.
        if n_backdrops > 1:
            concat_position = next_position
            CompositionStep.objects.create(
                composition=composition,
                position=concat_position,
                primitive="concat_clips",
                inputs=[
                    {"slot": "clip", "from_step_position": i}
                    for i in range(n_backdrops)
                ],
                params={},
            )
            background_source = concat_position
            next_position += 1
        else:
            background_source = 0

    # Step N+? (optional, V16) — strip the avatar's baked white
    # background so the composite below lays the avatar over the
    # backdrop without a picture-frame. Inserted only when
    # ``remove_avatar_bg=True`` so the existing 3-step / chain
    # contracts (and their tests) hold by default.
    if remove_avatar_bg:
        matte_position = next_position
        CompositionStep.objects.create(
            composition=composition,
            position=matte_position,
            primitive="remove_avatar_background",
            inputs=[
                {"slot": "clip", "from_step_position": speech_position},
            ],
            params={},
        )
        foreground_source = matte_position
        next_position += 1
    else:
        foreground_source = speech_position

    composite_position = next_position

    # Final — composite avatar over the (concat'd or single)
    # backdrop. composite_video's `backdrop` layout expects
    # background + foreground slots; the primitive trims to the
    # shorter input, so a slightly-over-provisioned backdrop chain
    # is free (just gets trimmed to the speech duration).
    CompositionStep.objects.create(
        composition=composition,
        position=composite_position,
        primitive="composite_video",
        inputs=[
            {"slot": "background", "from_step_position": background_source},
            {"slot": "foreground", "from_step_position": foreground_source},
        ],
        params={
            "layout_spec": {
                "kind": "backdrop",
                "options": {
                    "fg_width": fg_width,
                    "margin_x": margin_x,
                    "margin_y": margin_y,
                },
            },
        },
    )

    logger.info(
        "starter talking_head_with_backdrop created composition=%s "
        "spokesperson=%s mock=%s use_knowledge=%s fg_width=%d "
        "n_backdrops=%d backdrop_seconds=%d remove_avatar_bg=%s "
        "use_extend_for_backdrop=%s",
        composition.id, spokesperson.id, mock_mode, use_knowledge,
        fg_width, n_backdrops_for_log, backdrop_seconds, remove_avatar_bg,
        use_extend_for_backdrop,
    )
    return composition


@transaction.atomic
def talking_head_polished(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    script: str,
    captions: list[dict] | None = None,
    intro: dict | None = None,
    outro: dict | None = None,
    # SESSION 180 — operator-friendly shorthands so the SPA
    # recipe form can drive the polish steps without exposing
    # the full JSON shape. The dict-form kwargs above still win
    # when supplied by a programmatic caller (no surprise
    # override).
    intro_text: str | None = None,
    outro_text: str | None = None,
    burn_captions: bool = False,
    use_knowledge: bool = False,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
    verifier_mode: str | None = None,
    opener: str | None = None,
    # BC2 — optional lineage kwargs per B2_B3_COMPOSITION_V1
    # rule 4 + rule 7. When the C-arc launch path derives a
    # per-recipient render from a B-2 Script, it propagates the
    # Script's lineage onto every per-recipient Composition so
    # F-arc brief-mode + verification flags render on each Asset
    # detail page. All four default to None — current callers
    # are unaffected.
    knowledge_chunk_ids: list[str] | None = None,
    synthesized_brief: str | None = None,
    verification_status: str | None = None,
    verification_warnings: list[dict] | None = None,
) -> Composition:
    """Polished talking-head ad — speech → captions → intro/outro.

    Three-step composition that produces a finished spokesperson
    ad with burnt-in subtitles and a brand intro/outro card.

    Args:
        captions: Operator-supplied caption timing as
            ``[{start_s, end_s, text}, ...]``. When None, the
            captions step is skipped unless ``burn_captions`` is
            on (in which case the starter auto-times captions
            from the script using a chars-per-second estimate).
        intro / outro: Title-card specs as
            ``{text, duration_s, bg_color, text_color, font_size}``.
            At least one must be supplied for the intro_outro
            step to fire; otherwise both can be None and the
            step is skipped.
        intro_text / outro_text: Plain-string convenience — the
            SPA recipe form passes these. Each builds a default-
            styled title card (black bg / white text / 3s
            duration / 48pt font) when the matching dict kwarg
            isn't supplied.
        burn_captions: When True and ``captions`` isn't supplied,
            auto-time captions from the script by splitting on
            sentence boundaries and distributing time at
            ~11 chars/sec. Timing is approximate (the avatar's
            actual cadence drifts vs. the estimate) — fall back
            to operator-supplied ``captions`` for tight sync.
        knowledge_chunk_ids: BC2 — optional list of chunk UUIDs
            (as strings) to stamp on the Composition row for
            F-arc brief-mode lineage. Used by the C-arc launch
            path when ``PersonalizedCampaign.source_script`` is
            set — every per-recipient Composition inherits the
            Script's chunks so each rendered Asset's detail page
            shows the same citation panel as the source Script.
            Defaults to None (current behavior — empty list on
            Composition).
        synthesized_brief: BC2 — optional pre-substituted brief
            text. Used by the C-arc launch path to record the
            per-recipient ``render_template(...)`` output for
            audit. Mirrors ``auto_script``'s rule-7 semantic:
            the script param IS the synthesized brief, no K6
            re-synthesis at render time. Defaults to None.
        verification_status: BC2 — optional K6.4 verification
            status carried over from the source Script. Per
            BC0 rule 8, propagated unchanged at launch; not
            re-verified per recipient. Defaults to None.
        verification_warnings: BC2 — optional list of K6.4
            warning dicts carried over from the source Script.
            Each per-recipient Composition gets its own copy
            (Q-bc-7 resolved as-proposed — storage cost is
            trivial; render path is simpler than join-through-FK).
            Defaults to None.
    """
    if not script.strip():
        raise ValueError("talking_head_polished requires a non-empty script")
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError(
            f"spokesperson {spokesperson.name!r} not in workspace {workspace.pk}"
        )

    # SESSION 180 — resolve the operator-friendly shorthands into
    # the dict-shaped kwargs the downstream step builders already
    # know how to handle. Explicit dict-form kwargs (intro / outro
    # / captions) win to preserve the programmatic API.
    if intro is None and intro_text and intro_text.strip():
        intro = {"text": intro_text.strip(), "duration_s": 3.0}
    if outro is None and outro_text and outro_text.strip():
        outro = {"text": outro_text.strip(), "duration_s": 3.0}
    if captions is None and burn_captions:
        captions = _auto_caption_from_script(script.strip())

    composition_name = (
        name.strip() or f"Polished talking-head — {script.strip()[:40]}"
    )
    # BC2 — assemble Composition create kwargs. The four lineage
    # fields are only set when the caller supplies them, so the
    # existing C-arc + recipe-gallery callers (which omit them)
    # see no behavior change.
    composition_kwargs: dict = {
        "workspace": workspace,
        "spokesperson": spokesperson,
        "name": composition_name,
        "template_kind": "talking_head_polished",
        "mock_mode": mock_mode,
        "created_by": created_by,
    }
    if knowledge_chunk_ids is not None:
        composition_kwargs["knowledge_chunk_ids"] = list(knowledge_chunk_ids)
    if synthesized_brief is not None:
        composition_kwargs["synthesized_brief"] = synthesized_brief
    if verification_status is not None:
        composition_kwargs["verification_status"] = verification_status
    if verification_warnings is not None:
        composition_kwargs["verification_warnings"] = list(
            verification_warnings
        )
    composition = Composition.objects.create(**composition_kwargs)

    # Step 0 — speech
    polished_speech_params: dict = {
        "script": script.strip(),
        "use_knowledge": bool(use_knowledge),
    }
    if verifier_mode:
        polished_speech_params["verifier_mode"] = verifier_mode
    if opener and opener.strip():
        polished_speech_params["opener"] = opener.strip()
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="generate_avatar_speech",
        inputs=[],
        params=polished_speech_params,
    )

    # Step 1 — captions (optional). When provided, takes step 0's
    # speech clip as its base input.
    next_position = 1
    last_output_position = 0
    if captions:
        CompositionStep.objects.create(
            composition=composition,
            position=next_position,
            primitive="add_captions",
            inputs=[
                {"slot": "base", "from_step_position": last_output_position},
            ],
            params={"captions": list(captions)},
        )
        last_output_position = next_position
        next_position += 1

    # Step 2 (or 1 if no captions) — intro/outro. Skipped when
    # both intro and outro are None.
    if intro is not None or outro is not None:
        step_params: dict[str, object] = {}
        if intro is not None:
            step_params["intro"] = dict(intro)
        if outro is not None:
            step_params["outro"] = dict(outro)
        CompositionStep.objects.create(
            composition=composition,
            position=next_position,
            primitive="add_intro_outro",
            inputs=[
                {"slot": "base", "from_step_position": last_output_position},
            ],
            params=step_params,
        )

    logger.info(
        "starter talking_head_polished created composition=%s steps=%d "
        "use_knowledge=%s has_captions=%s has_intro=%s has_outro=%s",
        composition.id, composition.steps.count(), use_knowledge,
        bool(captions), intro is not None, outro is not None,
    )
    return composition


@transaction.atomic
def reels_format(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    base_clip,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Convert a landscape clip to 9:16 vertical (Reels format).

    Single-step modifier composition. Takes an existing CLIP and
    runs ``reformat_clip`` with ``target_ratio="720:1280"``.
    """
    _validate_workspace_assets(workspace, [base_clip])
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError("spokesperson not in workspace")

    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=name.strip() or "Reels format",
        template_kind="reels_format",
        mock_mode=mock_mode,
        created_by=created_by,
    )
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="reformat_clip",
        inputs=[{"slot": "base", "asset_id": str(base_clip.id)}],
        params={"target_ratio": "720:1280"},
    )
    return composition


# D-arc / B14.1 (SESSION 205). Platform-variant publish starter.
# Fans out a source CLIP to one platform-ready packaging
# (target aspect ratio + duration cap). Internal recipe —
# invoked by the D-arc bundle launch handler, NOT surfaced in
# the operator-facing /recipes gallery per Q-d-11.
#
# template_kind="publish_variant" is the load-bearing tag —
# apps.billing.services.get_usage() excludes these from the
# videos_per_month count per rule 5 + Q-d-4. The constant
# lives in apps.compositions.platform_catalog so the recipe
# and the cap exclusion can't drift.
@transaction.atomic
def publish_variant(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    source_clip,
    target_ratio: str,
    max_duration_ms: int,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Two-step publish-variant composition: trim → reformat.

    Args:
        workspace: Composition workspace anchor.
        spokesperson: The source clip's spokesperson — passed
            through for V-arc rule consistency (every
            Composition has a spokesperson FK). The variant
            doesn't re-render the avatar; it just packages
            existing avatar footage for a target platform.
        source_clip: The Asset(asset_type=CLIP) being
            packaged. Workspace + type validated by
            ``_validate_workspace_assets`` plus the bundle's
            clean() guard. Must carry a non-null
            ``duration_ms`` so the trim step's end_ms can be
            computed without a probe.
        target_ratio: One of ``{"1280:720", "720:1280",
            "960:960"}`` — the existing ``reformat_clip``
            supported ratios.
        max_duration_ms: Platform's hard duration cap (e.g.
            60_000 for Reels). The trim step emits
            ``min(source_duration_ms, max_duration_ms)`` so
            short source clips become a near-noop trim and
            long sources hard-cap from the start (Q-d v1:
            first N seconds; selectable trim window deferred).
        mock_mode: Mock-mode stub.

    Step layout (always 2 steps for state-machine simplicity):
        Step 0: ``trim_clip`` from 0..min(source, max).
        Step 1: ``reformat_clip`` consuming step 0 output.

    Returns the Composition. Caller enqueues
    ``execute_composition.delay``.
    """
    from .models import AssetType as _AssetType
    from .platform_catalog import PUBLISH_VARIANT_TEMPLATE_KIND

    _validate_workspace_assets(workspace, [source_clip])
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError(
            f"spokesperson {spokesperson.name!r} not in workspace "
            f"{workspace.pk}"
        )
    if source_clip.asset_type != _AssetType.CLIP:
        raise ValueError(
            f"publish_variant source must be asset_type=CLIP; got "
            f"{source_clip.asset_type!r}"
        )
    if source_clip.duration_ms is None or source_clip.duration_ms <= 0:
        raise ValueError(
            f"publish_variant source clip {source_clip.id} has no "
            f"duration_ms; can't compute the trim window"
        )
    if max_duration_ms <= 0:
        raise ValueError(
            f"max_duration_ms must be positive; got {max_duration_ms}"
        )

    # Trim window: cap at the source's actual duration so a
    # 5s source on a 30s LinkedIn cap doesn't try to extend
    # past EOF. ffmpeg's ``-to`` would silently stop at EOF,
    # but storing accurate offsets in the step row keeps the
    # audit trail honest.
    end_ms = min(int(source_clip.duration_ms), int(max_duration_ms))

    composition_name = name.strip() or (
        f"Publish variant ({target_ratio}, ≤{max_duration_ms // 1000}s)"
    )
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=composition_name,
        template_kind=PUBLISH_VARIANT_TEMPLATE_KIND,
        mock_mode=mock_mode,
        created_by=created_by,
    )

    # Step 0 — trim to the platform window from the source's
    # start.
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="trim_clip",
        inputs=[{"slot": "base", "asset_id": str(source_clip.id)}],
        params={"start_ms": 0, "end_ms": end_ms},
    )

    # Step 1 — reformat the trimmed clip to the platform's
    # target aspect ratio.
    CompositionStep.objects.create(
        composition=composition,
        position=1,
        primitive="reformat_clip",
        inputs=[{"slot": "base", "from_step_position": 0}],
        params={"target_ratio": target_ratio},
    )

    logger.info(
        "starter publish_variant created composition=%s source=%s "
        "target_ratio=%s end_ms=%d mock=%s",
        composition.id, source_clip.id, target_ratio, end_ms, mock_mode,
    )
    return composition


@transaction.atomic
def voice_design(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    description: str,
    voice_name: str = "",
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Single-step voice-design composition. The operator
    supplies a text description of how they want the brand
    voice to sound; the composition runs ``design_voice``
    via Runway's ``/v1/voices`` and produces a VOICE Asset
    whose ``source_spec.voice_id`` holds the Runway voice_id
    (and whose ``file_path`` holds a playable preview MP3).

    Args:
        workspace: Composition workspace anchor.
        spokesperson: Brand owner — the voice is workspace
            scoped but each spokesperson can have its own
            distinct voice.
        description: Free-form description (4-1000 chars).
            Examples: "warm, conversational founder voice",
            "energetic young female with a slight British
            accent".
        voice_name: Optional display name. Defaults to
            "Character OS Voice" server-side.
        mock_mode: Run in mock-mode (V0 contract rule 9).
        name: Composition display name. Defaults to
            "Voice design — {description[:40]}".
    """
    if not description.strip():
        raise ValueError("voice_design requires a non-empty description")
    if len(description.strip()) < 4:
        raise ValueError("voice_design description must be at least 4 characters")
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError(
            f"spokesperson {spokesperson.name!r} not in workspace {workspace.pk}"
        )

    composition_name = name.strip() or f"Voice design — {description.strip()[:40]}"
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=composition_name,
        template_kind="voice_design",
        mock_mode=mock_mode,
        created_by=created_by,
    )
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="design_voice",
        inputs=[],
        params={
            "description": description.strip(),
            "name": voice_name.strip(),
        },
    )
    return composition


@transaction.atomic
def multi_lang_dub(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    source_audio,
    target_language: str,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Single-step multilingual dub composition. Takes an
    existing AUDIO Asset and a target language ISO code,
    produces a new AUDIO Asset in that language.

    v1 covers the audio-only dub path (the hackathon's
    production-tested capability). V12 will extend this
    starter to a two-step composition: ``transcribe``
    (extract audio from a video clip) → ``dub_audio``. For
    now operators dub already-extracted audio assets
    (voice design previews, talking-head audio extracted
    separately, etc.).

    Args:
        source_audio: AUDIO Asset to dub. Must belong to
            ``workspace``.
        target_language: One of the 29 supported ISO codes
            (en/hi/pt/zh/es/fr/de/ja/ar/ru/ko/id/it/nl/tr/
            pl/sv/fil/ms/ro/uk/el/cs/da/fi/bg/hr/sk/ta).
        mock_mode: Run in mock-mode (V0 contract rule 9).
    """
    _validate_workspace_assets(workspace, [source_audio])
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError("spokesperson not in workspace")
    if source_audio.asset_type != "audio":
        raise ValueError(
            f"multi_lang_dub source_audio must be an AUDIO asset; "
            f"got {source_audio.asset_type}"
        )

    composition_name = (
        name.strip() or f"Dub → {target_language.lower()}"
    )
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=composition_name,
        template_kind="multi_lang_dub",
        mock_mode=mock_mode,
        created_by=created_by,
    )
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="dub_audio",
        inputs=[{"slot": "source", "asset_id": str(source_audio.id)}],
        params={"target_language": target_language.lower().strip()},
    )
    return composition


@transaction.atomic
def recut_teaser(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    source_clip,
    criterion: str = "hook",
    target_ratio: str = "720:1280",
    transcript: list[dict] | None = None,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """First net-new composition beyond what the hackathon
    shipped. Take a rendered MP4, auto-pick the strongest
    sentence, output a short vertical teaser.

    Pattern mirrors V5's ``long_form_ad``: the LLM work
    happens at starter-creation time (synchronous Whisper +
    gpt-5-mini), the runtime sees a deterministic 2-step
    plan (trim + reformat).

    Steps laid down:
      Step 0 — trim_clip (start_ms, end_ms from picked segment)
      Step 1 — reformat_clip (target_ratio, default 720:1280
        for Reels)

    Args:
        source_clip: CLIP Asset to recut. Must belong to
            ``workspace``. Typically a finished long-form ad
            or talking_head output.
        criterion: How to pick the segment. ``"hook"``
            (default) uses gpt-5-mini; ``"first"`` /
            ``"last"`` / ``"longest"`` are deterministic
            fallbacks.
        target_ratio: Reformat target. Default 720:1280
            (vertical Reels). Pass ``1280:720`` to keep
            landscape, ``960:960`` for square.
        transcript: Pre-computed transcript segments (e.g.
            from a prior ``transcribe`` step's output asset
            parsed by the caller). When supplied, skips the
            synchronous Whisper call at starter time —
            useful for tests + for chained compositions.
            Shape: ``[{"start_s", "end_s", "text"}, ...]``.
        mock_mode: Run in mock-mode (V0 contract rule 9).
            Forces ``criterion="longest"`` and skips Whisper.
            When ``transcript`` is None, uses a deterministic
            stub.

    Returns:
        ``Composition`` with 2 steps. Caller enqueues
        ``execute_composition.delay(str(c.id))``.

    Raises:
        ``ValueError`` for empty source / cross-workspace /
        empty transcript.
    """
    _validate_workspace_assets(workspace, [source_clip])
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError("spokesperson not in workspace")
    if source_clip.asset_type != "clip":
        raise ValueError(
            f"recut_teaser source_clip must be a CLIP asset; "
            f"got {source_clip.asset_type}"
        )

    # Acquire the transcript. Three paths in priority order:
    # (1) operator-supplied, (2) mock-mode stub, (3) synchronous
    # Whisper call via the media-engine.
    segments: list[Segment]
    if transcript is not None:
        if not transcript:
            raise ValueError("recut_teaser transcript must be non-empty")
        segments = [
            Segment(
                start_s=float(s["start_s"]),
                end_s=float(s["end_s"]),
                text=str(s.get("text", "")).strip(),
            )
            for s in transcript
            if str(s.get("text", "")).strip()
        ]
    elif mock_mode:
        # Stub that mirrors what the media-engine returns in
        # mock-mode — three short sentences across ~9s.
        segments = [
            Segment(start_s=0.0, end_s=2.5, text="Welcome to our demo."),
            Segment(start_s=2.5, end_s=6.0, text="This is the strongest line in the ad."),
            Segment(start_s=6.0, end_s=9.0, text="Visit us today."),
        ]
    else:
        segments = fetch_transcript(
            source_clip.file_path, extract_audio=True,
        )

    if not segments:
        raise ValueError(
            "recut_teaser: transcript produced zero segments "
            "(source may be silent or too short)"
        )

    # Mock-mode forces the deterministic "longest" pick — no
    # LLM call needed, hermetic test path.
    effective_criterion = "longest" if mock_mode else criterion
    picked = pick_strongest_segment(segments, criterion=effective_criterion)  # type: ignore[arg-type]

    start_ms = max(0, int(round(picked.start_s * 1000)))
    end_ms = max(start_ms + 100, int(round(picked.end_s * 1000)))

    composition_name = name.strip() or f"Teaser — {picked.text[:40]}"
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=composition_name,
        template_kind="recut_teaser",
        mock_mode=mock_mode,
        created_by=created_by,
    )

    # Step 0 — trim to the picked sentence.
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="trim_clip",
        inputs=[{"slot": "base", "asset_id": str(source_clip.id)}],
        params={"start_ms": start_ms, "end_ms": end_ms},
    )

    # Step 1 — reformat to the target aspect ratio.
    CompositionStep.objects.create(
        composition=composition,
        position=1,
        primitive="reformat_clip",
        inputs=[{"slot": "base", "from_step_position": 0}],
        params={"target_ratio": target_ratio},
    )

    logger.info(
        "starter recut_teaser created composition=%s segments=%d "
        "picked_window=(%.2f,%.2f) text=%r criterion=%s",
        composition.id, len(segments),
        picked.start_s, picked.end_s, picked.text[:40], effective_criterion,
    )
    return composition


@transaction.atomic
def style_remix_pass(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    source_clip,
    style_preset: str,
    seed: int | None = None,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Single-step Aleph style remix composition.

    Takes an existing CLIP and a preset id, produces a remixed
    CLIP. Sources >5.5s are chunked + parallel-remixed +
    concatenated server-side (Aleph has a hard ~5s output cap);
    the composition step sees one input + one output regardless.

    v1 supports 5 presets — noir / anime / chrome / watercolor /
    cyberpunk — matching the hackathon's STYLE_PRESETS dict
    byte-for-byte.
    """
    _validate_workspace_assets(workspace, [source_clip])
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError("spokesperson not in workspace")
    preset = style_preset.lower().strip()
    if preset not in {"noir", "anime", "chrome", "watercolor", "cyberpunk"}:
        raise ValueError(
            f"style_preset {style_preset!r} not supported. "
            "Supported: ['anime', 'chrome', 'cyberpunk', 'noir', 'watercolor']"
        )
    if source_clip.asset_type != "clip":
        raise ValueError(
            f"style_remix_pass source_clip must be a CLIP asset; "
            f"got {source_clip.asset_type}"
        )

    composition_name = name.strip() or f"Style remix — {preset}"
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=composition_name,
        template_kind="style_remix_pass",
        mock_mode=mock_mode,
        created_by=created_by,
    )
    step_params: dict[str, object] = {"style_preset": preset}
    if seed is not None:
        step_params["seed"] = int(seed)

    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="style_remix",
        inputs=[{"slot": "source", "asset_id": str(source_clip.id)}],
        params=step_params,
    )
    return composition


@transaction.atomic
def storyboard_ad(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    hook_prompt: str,
    action_prompt: str,
    payoff_prompt: str,
    image_seed: int | None = None,
    clip_duration: int = 5,
    # SESSION 198 — outro_text parity with storyboard_voiced.
    # Optional 3-second white-on-black outro card appended after
    # the concat. Blank / whitespace-only = skip (existing
    # 7-step composition shape preserved).
    outro_text: str | None = None,
    # SESSION 200 — per-shot extend chain to close the V-arc UX
    # gap of hard motion seams between shots. When True, each shot
    # is generate_visual_clip (5s, image-to-video) THEN
    # extend_visual_clip (5s, last-frame conditioned) — doubling
    # per-shot length to 10s and softening intra-shot motion. The
    # inter-shot seam is addressed via ``crossfade_ms`` on concat.
    # Default False preserves the SESSION 198 7/8-step shape.
    use_extend_for_shots: bool = False,
    # SESSION 200 — optional ffmpeg xfade duration between
    # consecutive shots at concat time. Forwarded to the concat
    # step's params; concat_clips primitive validates >= 0 and
    # the media-engine endpoint caps at 5000ms.
    crossfade_ms: int = 0,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Three-shot cinematic ad — Hook / Action / Payoff.

    Ports the hackathon's storyboard_service.py pattern into
    the V0+ composition arc. Seven-step recipe:

      Step 0-2: generate_image (Hook / Action / Payoff frames)
      Step 3-5: generate_visual_clip (each step takes the
        matching image as reference_image; gen4_turbo image-
        to-video animates the still into a clip)
      Step 6: concat_clips (Hook + Action + Payoff in order)

    The reference_image chain keeps visual identity consistent
    across the three shots — same color palette, same subject,
    same composition logic. ``image_seed`` reused across all
    three generate_image steps for further coherence.

    Args:
        hook_prompt / action_prompt / payoff_prompt: Three
            visual beats. Operator writes one short prompt per
            shot. Order is preserved in the concat.
        image_seed: Optional Runway seed for image generation.
            Same seed across all three shots keeps visual
            style coherent. None lets Runway pick.
        clip_duration: Per-shot duration in seconds. gen4_turbo
            accepts only ``{5}``. Default 5 → ~15s total.
        mock_mode: Run in mock-mode (V0 contract rule 9). All
            seven steps short-circuit to deterministic stubs.

    Returns:
        ``Composition`` with 7 steps. Caller enqueues
        ``execute_composition.delay(str(c.id))``.

    Note: ``storyboard_voiced`` (the voiced variant per V0
    design) is deferred — it requires extracting the audio
    track from a generate_avatar_speech CLIP, which needs an
    ``audio_extract`` primitive we haven't built yet. Land
    that primitive (V14+) before adding the voiced starter.
    """
    if not hook_prompt.strip():
        raise ValueError("storyboard_ad requires a non-empty hook_prompt")
    if not action_prompt.strip():
        raise ValueError("storyboard_ad requires a non-empty action_prompt")
    if not payoff_prompt.strip():
        raise ValueError("storyboard_ad requires a non-empty payoff_prompt")
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError(
            f"spokesperson {spokesperson.name!r} not in workspace {workspace.pk}"
        )

    composition_name = (
        name.strip() or f"Storyboard — {hook_prompt.strip()[:30]}"
    )
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=composition_name,
        template_kind="storyboard_ad",
        mock_mode=mock_mode,
        created_by=created_by,
    )

    shot_prompts = [
        ("hook", hook_prompt.strip()),
        ("action", action_prompt.strip()),
        ("payoff", payoff_prompt.strip()),
    ]

    # Steps 0-2 — three reference images. Same seed across
    # shots for visual coherence.
    for idx, (_label, prompt) in enumerate(shot_prompts):
        image_params: dict[str, object] = {"prompt": prompt}
        if image_seed is not None:
            image_params["seed"] = int(image_seed)
        CompositionStep.objects.create(
            composition=composition,
            position=idx,
            primitive="generate_image",
            inputs=[],
            params=image_params,
        )

    # Steps 3-5 — three image-to-video clips, each consuming
    # the matching image step's output via reference_image
    # slot.
    for idx, (_label, prompt) in enumerate(shot_prompts):
        CompositionStep.objects.create(
            composition=composition,
            position=3 + idx,
            primitive="generate_visual_clip",
            inputs=[
                {"slot": "reference_image", "from_step_position": idx},
            ],
            params={"prompt": prompt, "duration": clip_duration},
        )

    # SESSION 200 — when use_extend_for_shots=True, each shot's
    # generate output (5s) is followed by an extend_visual_clip
    # (5s, last-frame conditioned). The concat then consumes the
    # extend outputs (6,7,8) instead of the generate outputs.
    if use_extend_for_shots:
        for idx, (_label, prompt) in enumerate(shot_prompts):
            extend_params: dict[str, object] = {
                "prompt": prompt,
                "duration": clip_duration,
            }
            if image_seed is not None:
                extend_params["seed"] = int(image_seed)
            CompositionStep.objects.create(
                composition=composition,
                position=6 + idx,
                primitive="extend_visual_clip",
                inputs=[
                    {"slot": "source", "from_step_position": 3 + idx},
                ],
                params=extend_params,
            )
        concat_position = 9
        concat_source_offset = 6
    else:
        concat_position = 6
        concat_source_offset = 3

    # Concat the three shots in order. When the extend chain is
    # enabled, the inputs point at the extend outputs (6,7,8);
    # otherwise they point at the generate outputs (3,4,5).
    concat_inputs = [
        {"slot": "clip", "from_step_position": concat_source_offset + idx}
        for idx in range(3)
    ]
    concat_params: dict[str, object] = {}
    if crossfade_ms:
        concat_params["crossfade_ms"] = int(crossfade_ms)
    CompositionStep.objects.create(
        composition=composition,
        position=concat_position,
        primitive="concat_clips",
        inputs=concat_inputs,
        params=concat_params,
    )

    # SESSION 198 — optional brand outro card. Mirrors
    # storyboard_voiced exactly. When ``outro_text`` is non-empty,
    # append an add_intro_outro step after the concat consuming
    # its output as base. Blank = skip (concat-only shape).
    cleaned_outro = (outro_text or "").strip()
    if cleaned_outro:
        CompositionStep.objects.create(
            composition=composition,
            position=concat_position + 1,
            primitive="add_intro_outro",
            inputs=[{"slot": "base", "from_step_position": concat_position}],
            params={
                "outro": {
                    "text": cleaned_outro,
                    "duration_s": 3.0,
                },
            },
        )

    logger.info(
        "starter storyboard_ad created composition=%s spokesperson=%s "
        "mock=%s seed=%s duration_per_shot=%d outro=%s extend_shots=%s "
        "crossfade_ms=%d",
        composition.id, spokesperson.id, mock_mode, image_seed, clip_duration,
        bool(cleaned_outro), use_extend_for_shots, int(crossfade_ms or 0),
    )
    return composition


@transaction.atomic
def dialogue_scene(
    *,
    workspace: "Workspace",
    primary_spokesperson: "Spokesperson",
    lines: list[dict],
    # SESSION 199 — outro_text parity. Optional 3s white-on-black
    # outro appended after the dialogue. Handles multi-line (after
    # concat) and single-line (after lone speech) degenerate paths.
    outro_text: str | None = None,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Multi-character dialogue scene — N speech turns + 1 concat.

    Ports the hackathon's ``dialogue_service.py`` 6-line skit
    pattern into the V0+ composition arc. Each line is a
    `generate_avatar_speech` step that overrides the
    composition's primary spokesperson via the
    ``spokesperson_avatar_id`` param, so different characters
    can speak across the turns without forking the
    Composition.spokesperson FK.

    Pattern mirrors V5's ``long_form_ad`` — pre-computation at
    starter creation (the lines list is fixed before the
    composition runs); V2 runtime sees a deterministic N+1
    step plan.

    Args:
        workspace: Composition workspace anchor.
        primary_spokesperson: The Composition.spokesperson FK
            owner. Typically the "narrator" / lead character.
            Used for audit + permission scoping; per-line
            avatar overrides handle the actual rendering.
        lines: Ordered list of dialogue turns. Each entry:
            ``{"spokesperson": <Teammate>, "text": "..."}``.
            All spokespeople must belong to ``workspace``;
            cross-workspace turns raise ValueError.
        mock_mode: V0 contract rule 9 — all primitives short-
          circuit to stub assets.

    Returns:
        ``Composition`` with N+1 steps (or 1 step for a
        single-line scene, same degenerate-case optimization
        as ``long_form_ad``).

    Raises:
        ``ValueError`` for empty lines, cross-workspace
        spokespeople, missing avatars, empty text.
    """
    if not lines:
        raise ValueError("dialogue_scene requires at least one line")
    if primary_spokesperson.workspace_id != workspace.pk:
        raise ValueError(
            f"primary spokesperson {primary_spokesperson.name!r} not in workspace"
        )

    # Validate all per-line spokespeople before creating
    # anything (atomic-or-bust).
    validated_lines: list[tuple] = []
    for idx, entry in enumerate(lines):
        if not isinstance(entry, dict):
            raise ValueError(
                f"dialogue_scene line {idx} must be a dict; got {type(entry).__name__}"
            )
        sp = entry.get("spokesperson")
        if sp is None:
            raise ValueError(f"dialogue_scene line {idx} missing spokesperson")
        text = str(entry.get("text", "")).strip()
        if not text:
            raise ValueError(f"dialogue_scene line {idx} requires non-empty text")
        if sp.workspace_id != workspace.pk:
            raise ValueError(
                f"dialogue_scene line {idx}: spokesperson {sp.name!r} "
                f"(workspace {sp.workspace_id}) is not in workspace {workspace.pk}"
            )
        if not sp.runway_avatar_id:
            raise ValueError(
                f"dialogue_scene line {idx}: spokesperson {sp.name!r} has no "
                "runway_avatar_id; finish the create-spokesperson wizard first"
            )
        validated_lines.append((sp, text))

    composition_name = (
        name.strip()
        or f"Dialogue — {validated_lines[0][1][:30]}"
    )
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=primary_spokesperson,
        name=composition_name,
        template_kind="dialogue_scene",
        mock_mode=mock_mode,
        created_by=created_by,
    )

    # Steps 0..N-1: one generate_avatar_speech per line, each
    # overriding the avatar via params.
    for idx, (sp, text) in enumerate(validated_lines):
        CompositionStep.objects.create(
            composition=composition,
            position=idx,
            primitive="generate_avatar_speech",
            inputs=[],
            params={
                "script": text,
                "use_knowledge": False,
                "spokesperson_avatar_id": sp.runway_avatar_id,
            },
        )

    # Step N: concat all prior steps. Skip when there's only
    # one line — same degenerate-case optimization as
    # long_form_ad.
    last_output_position = len(validated_lines) - 1  # the final speech step
    if len(validated_lines) > 1:
        concat_inputs = [
            {"slot": "clip", "from_step_position": i}
            for i in range(len(validated_lines))
        ]
        # SESSION 196 slice 2 — override concat_clips' default
        # BACKDROP role. A dialogue_scene's concat output is the
        # final deliverable (N talking-head turns stitched together),
        # not a backdrop. Tagging it COMPOSITE_OUTPUT keeps it out
        # of the A7 role-filtered backdrop_clip_id picker (the
        # SESSION 195 finding — avatars-over-avatars on V18 was
        # nonsense). The "composite" framing also matches the
        # operator's mental model: "dialogue scene = the
        # composed deliverable."
        CompositionStep.objects.create(
            composition=composition,
            position=len(validated_lines),
            primitive="concat_clips",
            inputs=concat_inputs,
            params={"result_role": "composite_output"},
        )
        last_output_position = len(validated_lines)

    # SESSION 199 — optional brand outro card. Appended after the
    # last step (concat or lone speech). Blank = skip. Same
    # variable-position logic as long_form_ad.
    cleaned_outro = (outro_text or "").strip()
    if cleaned_outro:
        CompositionStep.objects.create(
            composition=composition,
            position=last_output_position + 1,
            primitive="add_intro_outro",
            inputs=[{"slot": "base", "from_step_position": last_output_position}],
            params={
                "outro": {
                    "text": cleaned_outro,
                    "duration_s": 3.0,
                },
            },
        )

    logger.info(
        "starter dialogue_scene created composition=%s primary=%s "
        "mock=%s lines=%d distinct_avatars=%d outro=%s",
        composition.id, primary_spokesperson.id, mock_mode,
        len(validated_lines),
        len({sp.runway_avatar_id for sp, _ in validated_lines}),
        bool(cleaned_outro),
    )
    return composition


@transaction.atomic
def storyboard_voiced(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    hook_prompt: str,
    action_prompt: str,
    payoff_prompt: str,
    narration_script: str,
    image_seed: int | None = None,
    clip_duration: int = 5,
    # SESSION 197 — operator-noticed during SESSION 195 dogfood
    # that the storyboard ended cold without any brand mark.
    # Optional 3-second white-on-black outro card appended via
    # add_intro_outro after the mix step. Mirrors
    # talking_head_polished's outro_text shorthand exactly.
    # Empty / None / whitespace-only = skip the step (the
    # 10-step composition shape).
    outro_text: str | None = None,
    # SESSION 200 — per-shot extend chain (same pattern as
    # ``storyboard_ad``). When True, each shot is generate (5s) +
    # extend (5s last-frame conditioned) = 10s per shot, 30s
    # storyboard total. Default False preserves the original
    # 10/11-step shape.
    use_extend_for_shots: bool = False,
    # SESSION 200 — optional ffmpeg xfade between consecutive
    # shots at concat time. Forwarded to the concat step's params.
    crossfade_ms: int = 0,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Three-shot storyboard with avatar narration mixed under.

    The V13 deferral — needed V14's ``audio_extract`` primitive to
    pull audio from a talking-head clip so it could be mixed under
    a silent storyboard. Composition shape:

      Step 0-2: generate_image (Hook / Action / Payoff frames)
      Step 3-5: generate_visual_clip (each from matching image
                via reference_image slot; same pattern as
                ``storyboard_ad``)
      Step 6:   concat_clips (silent storyboard)
      Step 7:   generate_avatar_speech (narration; the audio
                from this clip becomes the storyboard's
                voiceover)
      Step 8:   audio_extract (pull AUDIO off step 7's CLIP)
      Step 9:   mix_audio (base = step 6 silent storyboard,
                music_slot = step 8 audio_extract output;
                ``music_gain_db`` overridden to 0 so the
                narration sits at full level)

    Per-shot duration is hard-coded to 5s by Runway's
    gen4_turbo today; the storyboard is therefore ~15s total
    and the narration clip's length should match — operators
    write narration that fits 15s.

    Args:
        hook_prompt / action_prompt / payoff_prompt: One short
            prompt per visual beat. Same as ``storyboard_ad``.
        narration_script: Words the avatar speaks. Avatar voice
            comes from ``spokesperson.runway_avatar_id``.
        image_seed: Optional shared seed across the three
            ``generate_image`` steps for visual coherence.
        clip_duration: Per-shot duration in seconds. gen4_turbo
            accepts only ``{5}`` today.
        mock_mode: Deterministic stubs end-to-end (V0 rule 9).

    Returns:
        ``Composition`` with 10 steps. Caller enqueues
        ``execute_composition.delay(str(c.id))``.

    Note: The narration is rendered as a talking-head clip first
    (step 7) and then the audio is extracted (step 8). That
    "wasted" talking-head render is the cleanest way to use the
    avatar's bound voice + the existing avatar_speech primitive
    without a separate "voice-only" call path — and the clip
    survives in the workspace as an Asset the operator can
    reuse.
    """
    if not hook_prompt.strip():
        raise ValueError("storyboard_voiced requires a non-empty hook_prompt")
    if not action_prompt.strip():
        raise ValueError("storyboard_voiced requires a non-empty action_prompt")
    if not payoff_prompt.strip():
        raise ValueError("storyboard_voiced requires a non-empty payoff_prompt")
    if not narration_script.strip():
        raise ValueError("storyboard_voiced requires a non-empty narration_script")
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError(
            f"spokesperson {spokesperson.name!r} not in workspace {workspace.pk}"
        )

    composition_name = (
        name.strip() or f"Storyboard voiced — {hook_prompt.strip()[:30]}"
    )
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=composition_name,
        template_kind="storyboard_voiced",
        mock_mode=mock_mode,
        created_by=created_by,
    )

    shot_prompts = [
        ("hook", hook_prompt.strip()),
        ("action", action_prompt.strip()),
        ("payoff", payoff_prompt.strip()),
    ]

    # Steps 0-2 — three reference images. Same seed = coherent
    # visual style across the storyboard. Mirrors ``storyboard_ad``.
    for idx, (_label, prompt) in enumerate(shot_prompts):
        image_params: dict[str, object] = {"prompt": prompt}
        if image_seed is not None:
            image_params["seed"] = int(image_seed)
        CompositionStep.objects.create(
            composition=composition,
            position=idx,
            primitive="generate_image",
            inputs=[],
            params=image_params,
        )

    # Steps 3-5 — image-to-video, each consuming the matching
    # image step via reference_image slot. Identical to
    # ``storyboard_ad``.
    for idx, (_label, prompt) in enumerate(shot_prompts):
        CompositionStep.objects.create(
            composition=composition,
            position=3 + idx,
            primitive="generate_visual_clip",
            inputs=[
                {"slot": "reference_image", "from_step_position": idx},
            ],
            params={"prompt": prompt, "duration": clip_duration},
        )

    # SESSION 200 — when use_extend_for_shots=True, interleave a
    # per-shot extend_visual_clip chain (positions 6-8) between
    # the generates and the concat. Downstream step positions
    # shift up by 3.
    if use_extend_for_shots:
        for idx, (_label, prompt) in enumerate(shot_prompts):
            extend_params: dict[str, object] = {
                "prompt": prompt,
                "duration": clip_duration,
            }
            if image_seed is not None:
                extend_params["seed"] = int(image_seed)
            CompositionStep.objects.create(
                composition=composition,
                position=6 + idx,
                primitive="extend_visual_clip",
                inputs=[
                    {"slot": "source", "from_step_position": 3 + idx},
                ],
                params=extend_params,
            )
        concat_position = 9
        concat_source_offset = 6
    else:
        concat_position = 6
        concat_source_offset = 3

    # Concat the three shots into the silent storyboard. Inputs
    # point at the extend outputs (6,7,8) when the chain is on,
    # otherwise at the generate outputs (3,4,5).
    concat_params: dict[str, object] = {}
    if crossfade_ms:
        concat_params["crossfade_ms"] = int(crossfade_ms)
    CompositionStep.objects.create(
        composition=composition,
        position=concat_position,
        primitive="concat_clips",
        inputs=[
            {"slot": "clip", "from_step_position": concat_source_offset + idx}
            for idx in range(3)
        ],
        params=concat_params,
    )

    # Narration as a talking-head clip — render the avatar (not
    # just audio) so the existing generate_avatar_speech primitive
    # uses the spokesperson's bound voice + the avatar_videos
    # endpoint; audio_extract pulls the audio in the next step.
    speech_position = concat_position + 1
    CompositionStep.objects.create(
        composition=composition,
        position=speech_position,
        primitive="generate_avatar_speech",
        inputs=[],
        params={
            "script": narration_script.strip(),
            "use_knowledge": False,
        },
    )

    # Extract the narration audio.
    extract_position = speech_position + 1
    CompositionStep.objects.create(
        composition=composition,
        position=extract_position,
        primitive="audio_extract",
        inputs=[{"slot": "base", "from_step_position": speech_position}],
        params={"format": "mp3"},
    )

    # Mix the narration AUDIO under the silent storyboard CLIP.
    # music_gain_db=0 so the narration sits at full level (the
    # music_bed default of -18 dB would bury it).
    mix_position = extract_position + 1
    CompositionStep.objects.create(
        composition=composition,
        position=mix_position,
        primitive="mix_audio",
        inputs=[
            {"slot": "base", "from_step_position": concat_position},
            {"slot": "music", "from_step_position": extract_position},
        ],
        params={
            "mix_spec": {
                "music_gain_db": 0.0,
                "fade_in_ms": 0,
                "fade_out_ms": 0,
            },
        },
    )

    # SESSION 197 — optional brand outro card. When ``outro_text``
    # is non-empty, append an add_intro_outro step after the mix.
    # 3-second white-on-black card matches talking_head_polished's
    # default styling. Blank = skip.
    cleaned_outro = (outro_text or "").strip()
    if cleaned_outro:
        CompositionStep.objects.create(
            composition=composition,
            position=mix_position + 1,
            primitive="add_intro_outro",
            inputs=[{"slot": "base", "from_step_position": mix_position}],
            params={
                "outro": {
                    "text": cleaned_outro,
                    "duration_s": 3.0,
                },
            },
        )

    logger.info(
        "starter storyboard_voiced created composition=%s "
        "spokesperson=%s mock=%s seed=%s outro=%s extend_shots=%s "
        "crossfade_ms=%d",
        composition.id, spokesperson.id, mock_mode, image_seed,
        bool(cleaned_outro), use_extend_for_shots, int(crossfade_ms or 0),
    )
    return composition


@transaction.atomic
def music_bed_pass(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    base_clip,
    music_asset,
    music_gain_db: float = -18.0,
    fade_in_ms: int = 1000,
    fade_out_ms: int = 2000,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Music bed — mix a music AUDIO track under the base
    clip's voice. Default gain -18 dB matches the hackathon's
    music_bed_client.
    """
    _validate_workspace_assets(workspace, [base_clip, music_asset])
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError("spokesperson not in workspace")

    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=name.strip() or "Music bed pass",
        template_kind="music_bed_pass",
        mock_mode=mock_mode,
        created_by=created_by,
    )
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="mix_audio",
        inputs=[
            {"slot": "base", "asset_id": str(base_clip.id)},
            {"slot": "music", "asset_id": str(music_asset.id)},
        ],
        params={
            "mix_spec": {
                "music_gain_db": float(music_gain_db),
                "fade_in_ms": int(fade_in_ms),
                "fade_out_ms": int(fade_out_ms),
            },
        },
    )
    return composition
