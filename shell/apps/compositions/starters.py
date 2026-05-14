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
