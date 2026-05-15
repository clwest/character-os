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
def talking_head_polished(
    *,
    workspace: "Workspace",
    spokesperson: "Spokesperson",
    script: str,
    captions: list[dict] | None = None,
    intro: dict | None = None,
    outro: dict | None = None,
    use_knowledge: bool = False,
    mock_mode: bool = False,
    name: str = "",
    created_by: "AbstractBaseUser | None" = None,
) -> Composition:
    """Polished talking-head ad — speech → captions → intro/outro.

    Three-step composition that produces a finished spokesperson
    ad with burnt-in subtitles and a brand intro/outro card.

    Args:
        captions: Operator-supplied caption timing as
            ``[{start_s, end_s, text}, ...]``. When None, the
            captions step is skipped — useful for operators who
            want the polish format without subtitles (or when
            V12 lands and auto-captioning is the default).
        intro / outro: Title-card specs as
            ``{text, duration_s, bg_color, text_color, font_size}``.
            At least one must be supplied for the intro_outro
            step to fire; otherwise both can be None and the
            step is skipped.
    """
    if not script.strip():
        raise ValueError("talking_head_polished requires a non-empty script")
    if spokesperson.workspace_id != workspace.pk:
        raise ValueError(
            f"spokesperson {spokesperson.name!r} not in workspace {workspace.pk}"
        )

    composition_name = (
        name.strip() or f"Polished talking-head — {script.strip()[:40]}"
    )
    composition = Composition.objects.create(
        workspace=workspace,
        spokesperson=spokesperson,
        name=composition_name,
        template_kind="talking_head_polished",
        mock_mode=mock_mode,
        created_by=created_by,
    )

    # Step 0 — speech
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

    # Step 6 — concat the three clips in order.
    concat_inputs = [
        {"slot": "clip", "from_step_position": 3 + idx}
        for idx in range(3)
    ]
    CompositionStep.objects.create(
        composition=composition,
        position=6,
        primitive="concat_clips",
        inputs=concat_inputs,
        params={},
    )

    logger.info(
        "starter storyboard_ad created composition=%s spokesperson=%s "
        "mock=%s seed=%s duration_per_shot=%d",
        composition.id, spokesperson.id, mock_mode, image_seed, clip_duration,
    )
    return composition


@transaction.atomic
def dialogue_scene(
    *,
    workspace: "Workspace",
    primary_spokesperson: "Spokesperson",
    lines: list[dict],
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
            ``{"spokesperson": <Spokesperson>, "text": "..."}``.
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
    if len(validated_lines) > 1:
        concat_inputs = [
            {"slot": "clip", "from_step_position": i}
            for i in range(len(validated_lines))
        ]
        CompositionStep.objects.create(
            composition=composition,
            position=len(validated_lines),
            primitive="concat_clips",
            inputs=concat_inputs,
            params={},
        )

    logger.info(
        "starter dialogue_scene created composition=%s primary=%s "
        "mock=%s lines=%d distinct_avatars=%d",
        composition.id, primary_spokesperson.id, mock_mode,
        len(validated_lines),
        len({sp.runway_avatar_id for sp, _ in validated_lines}),
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

    # Step 6 — concat the three clips into the silent storyboard.
    CompositionStep.objects.create(
        composition=composition,
        position=6,
        primitive="concat_clips",
        inputs=[
            {"slot": "clip", "from_step_position": 3 + idx}
            for idx in range(3)
        ],
        params={},
    )

    # Step 7 — narration as a talking-head clip. We render the
    # avatar (not just audio) because the existing
    # generate_avatar_speech primitive is the cleanest way to
    # use the spokesperson's bound voice + the avatar_videos
    # endpoint; audio_extract pulls the audio in the next step.
    CompositionStep.objects.create(
        composition=composition,
        position=7,
        primitive="generate_avatar_speech",
        inputs=[],
        params={
            "script": narration_script.strip(),
            "use_knowledge": False,
        },
    )

    # Step 8 — extract the narration audio.
    CompositionStep.objects.create(
        composition=composition,
        position=8,
        primitive="audio_extract",
        inputs=[{"slot": "base", "from_step_position": 7}],
        params={"format": "mp3"},
    )

    # Step 9 — mix the narration AUDIO under the silent
    # storyboard CLIP. music_gain_db=0 so the narration sits
    # at full level (the music_bed default of -18 dB would
    # bury it).
    CompositionStep.objects.create(
        composition=composition,
        position=9,
        primitive="mix_audio",
        inputs=[
            {"slot": "base", "from_step_position": 6},
            {"slot": "music", "from_step_position": 8},
        ],
        params={
            "mix_spec": {
                "music_gain_db": 0.0,
                "fade_in_ms": 0,
                "fade_out_ms": 0,
            },
        },
    )

    logger.info(
        "starter storyboard_voiced created composition=%s "
        "spokesperson=%s mock=%s seed=%s",
        composition.id, spokesperson.id, mock_mode, image_seed,
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
