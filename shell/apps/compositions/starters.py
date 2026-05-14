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

if TYPE_CHECKING:
    from apps.accounts.models import Workspace
    from apps.spokespeople.models import Spokesperson
    from django.contrib.auth.models import AbstractBaseUser

logger = logging.getLogger(__name__)


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
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="generate_avatar_speech",
        inputs=[],
        params={
            "script": script.strip(),
            "use_knowledge": bool(use_knowledge),
        },
    )

    logger.info(
        "starter talking_head created composition=%s spokesperson=%s "
        "mock=%s use_knowledge=%s",
        composition.id, spokesperson.id, mock_mode, use_knowledge,
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

    logger.info(
        "starter cinematic_visual created composition=%s spokesperson=%s "
        "mock=%s has_image=%s ratio=%s duration=%s",
        composition.id, spokesperson.id, mock_mode,
        bool(prompt_image), ratio, duration,
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
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
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
    for i, chunk in enumerate(chunks):
        CompositionStep.objects.create(
            composition=composition,
            position=i,
            primitive="generate_avatar_speech",
            inputs=[],
            params={
                "script": chunk,
                "use_knowledge": bool(use_knowledge),
            },
        )

    # Optimization: skip the concat step when there's exactly one
    # chunk — the composition is functionally identical to
    # ``talking_head``. Keeps the data clean (no degenerate
    # 1-input concat).
    if len(chunks) > 1:
        concat_inputs = [
            {"slot": "clip", "from_step_position": i}
            for i in range(len(chunks))
        ]
        CompositionStep.objects.create(
            composition=composition,
            position=len(chunks),
            primitive="concat_clips",
            inputs=concat_inputs,
            params={"reencode": bool(reencode_concat)},
        )

    logger.info(
        "starter long_form_ad created composition=%s spokesperson=%s "
        "mock=%s chunks=%d use_llm_split=%s use_knowledge=%s",
        composition.id, spokesperson.id, mock_mode,
        len(chunks), use_llm_split, use_knowledge,
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
    backdrop_prompt: str,
    backdrop_ratio: str | None = None,
    backdrop_duration: int | None = None,
    fg_width: int = 320,
    margin_x: int = 40,
    margin_y: int = 40,
    use_knowledge: bool = False,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
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
    if not backdrop_prompt.strip():
        raise ValueError("talking_head_with_backdrop requires a non-empty backdrop_prompt")
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

    # Step 0 — cinematic backdrop. Params mirror the
    # cinematic_visual starter shape.
    backdrop_params: dict[str, object] = {"prompt": backdrop_prompt.strip()}
    if backdrop_ratio is not None:
        backdrop_params["ratio"] = backdrop_ratio
    if backdrop_duration is not None:
        backdrop_params["duration"] = backdrop_duration
    CompositionStep.objects.create(
        composition=composition,
        position=0,
        primitive="generate_visual_clip",
        inputs=[],
        params=backdrop_params,
    )

    # Step 1 — avatar speech. Mirrors the talking_head starter.
    CompositionStep.objects.create(
        composition=composition,
        position=1,
        primitive="generate_avatar_speech",
        inputs=[],
        params={
            "script": script.strip(),
            "use_knowledge": bool(use_knowledge),
        },
    )

    # Step 2 — composite the avatar over the backdrop.
    # composite_video's `backdrop` layout expects
    # [0] = background (cinematic), [1] = foreground (avatar).
    CompositionStep.objects.create(
        composition=composition,
        position=2,
        primitive="composite_video",
        inputs=[
            {"slot": "background", "from_step_position": 0},
            {"slot": "foreground", "from_step_position": 1},
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
        "spokesperson=%s mock=%s use_knowledge=%s fg_width=%d",
        composition.id, spokesperson.id, mock_mode, use_knowledge, fg_width,
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
