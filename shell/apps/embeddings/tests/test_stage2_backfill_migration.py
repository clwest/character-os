"""SESSION 276 Slice 7 / Delta Stage 2 — migration regression tests.

Tests the ``apply_forward`` / ``apply_reverse`` functions of migration
``0008_session276_stage2_backfill`` in isolation, by importing the
functions directly from the migration module and invoking them with
the current runtime app registry.

Test matrix:

* T1 — forward classifies correctly:
    * rows with M2M ≥ 1 → CHARACTER (regardless of Universe)
    * frozen-3 IDs → UNIVERSE
    * ambiguous rows (empty M2M + no Universe) → stay NULL
* T2 — no false Universe classification:
    * a synthetic KD with universe set + empty M2M + NOT in frozen-3 stays NULL
* T3 — inactive preflight aborts:
    * one inactive row → ``Stage2PreflightError`` raised
    * no partial classification persists
* T4 — reverse restores stage-1 NULL state for rows Stage 2 touched
* T5 — reverse does not touch unrelated audience_scope values
* T6 — forward is idempotent (running twice = running once)

See ``docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md`` §99-§111.
"""
from __future__ import annotations

import importlib
import uuid

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.embeddings.models import (
    AudienceScope,
    DocumentType,
    IngestedVia,
    KnowledgeDocument,
)
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe

User = get_user_model()

# Import the migration module by numeric name (module name starts with a
# digit → cannot be imported via a regular ``import`` statement).
_migration = importlib.import_module(
    "apps.embeddings.migrations.0008_session276_stage2_backfill",
)
apply_forward = _migration.apply_forward
apply_reverse = _migration.apply_reverse
UNIVERSE_CANON_ROWS_20260821 = _migration.UNIVERSE_CANON_ROWS_20260821
Stage2PreflightError = _migration.Stage2PreflightError


# ---- fixtures --------------------------------------------


def _make_workspace(email: str, name: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws


def _make_universe(ws: Workspace, name: str) -> Universe:
    return Universe.objects.create(workspace=ws, name=name)


def _make_teammate(ws: Workspace, name: str, universe=None) -> Teammate:
    return Teammate.objects.create(workspace=ws, name=name, universe=universe)


def _make_kd(
    ws: Workspace,
    title: str,
    *,
    pk: str | None = None,
    universe: Universe | None = None,
    spokespeople: list[Teammate] | None = None,
    is_active: bool = True,
) -> KnowledgeDocument:
    kwargs: dict = dict(
        workspace=ws,
        title=title,
        document_type=DocumentType.TEXT,
        raw_content=f"body-{title}",
        processed_content=f"body-{title}",
        content_hash=f"hash-{uuid.uuid4().hex}",
        ingested_via=IngestedVia.PASTE,
        universe=universe,
        is_active=is_active,
    )
    if pk is not None:
        kwargs["id"] = uuid.UUID(pk)
    kd = KnowledgeDocument.objects.create(**kwargs)
    if spokespeople:
        kd.spokespeople.set(spokespeople)
    return kd


# ---- T1 — forward classifies correctly ------------------


@pytest.mark.django_db
def test_forward_classifies_character_universe_and_ambiguous() -> None:
    ws = _make_workspace("stage2-t1@test.local", "Stage2 T1")
    u = _make_universe(ws, "T1 Universe")
    tm_legacy = _make_teammate(ws, "TmLegacy")
    tm_universe = _make_teammate(ws, "TmUniverse", universe=u)

    # Rows that should become CHARACTER (M2M ≥ 1):
    kd_char_legacy = _make_kd(
        ws, "char-legacy", spokespeople=[tm_legacy],
    )
    kd_char_universe = _make_kd(
        ws, "char-universe", universe=u, spokespeople=[tm_universe],
    )

    # Row that should become UNIVERSE (frozen-3):
    kd_frozen = _make_kd(
        ws, "frozen-canon",
        pk=UNIVERSE_CANON_ROWS_20260821[0],
        universe=u,
    )

    # Row that should stay NULL (ambiguous: empty M2M + no Universe):
    kd_ambig = _make_kd(ws, "ambiguous")

    # Sanity — all NULL before forward
    for k in (kd_char_legacy, kd_char_universe, kd_frozen, kd_ambig):
        k.refresh_from_db()
        assert k.audience_scope is None

    apply_forward(django_apps, None)

    kd_char_legacy.refresh_from_db()
    kd_char_universe.refresh_from_db()
    kd_frozen.refresh_from_db()
    kd_ambig.refresh_from_db()

    assert kd_char_legacy.audience_scope == AudienceScope.CHARACTER
    assert kd_char_universe.audience_scope == AudienceScope.CHARACTER
    assert kd_frozen.audience_scope == AudienceScope.UNIVERSE
    assert kd_ambig.audience_scope is None


# ---- T2 — no false Universe classification --------------


@pytest.mark.django_db
def test_forward_does_not_falsely_classify_non_frozen_universe_row_as_universe() -> None:
    """A row with ``universe != NULL AND M2M empty`` that is NOT one of
    the frozen three must remain NULL. This is the load-bearing rule
    that prevents Stage 2 from recreating the shape-derived ambiguity
    Delta was introduced to eliminate.
    """
    ws = _make_workspace("stage2-t2@test.local", "Stage2 T2")
    u = _make_universe(ws, "T2 Universe")

    # Synthetic Universe-canon-shape row, NOT in the frozen set
    kd_non_frozen_universe_shape = _make_kd(
        ws, "not-frozen-universe-shape", universe=u,
    )
    assert kd_non_frozen_universe_shape.audience_scope is None
    assert str(kd_non_frozen_universe_shape.pk) not in UNIVERSE_CANON_ROWS_20260821

    apply_forward(django_apps, None)

    kd_non_frozen_universe_shape.refresh_from_db()
    assert kd_non_frozen_universe_shape.audience_scope is None, (
        "non-frozen Universe-canon-shape row must NOT auto-classify as UNIVERSE"
    )


# ---- T3 — inactive preflight aborts ---------------------


@pytest.mark.django_db
def test_forward_aborts_when_any_inactive_row_exists() -> None:
    """Preflight must abort on ANY inactive KD; no partial writes."""
    ws = _make_workspace("stage2-t3@test.local", "Stage2 T3")
    tm = _make_teammate(ws, "TmT3")

    # An active row that WOULD have been classified CHARACTER if forward
    # ran to completion:
    kd_would_be_char = _make_kd(ws, "would-be-char", spokespeople=[tm])
    # An inactive row that triggers the preflight:
    kd_inactive = _make_kd(ws, "inactive-trigger", is_active=False)

    with pytest.raises(Stage2PreflightError):
        apply_forward(django_apps, None)

    kd_would_be_char.refresh_from_db()
    kd_inactive.refresh_from_db()

    # No partial writes — audience_scope must still be NULL.
    assert kd_would_be_char.audience_scope is None, (
        "preflight abort must not leave partial CHARACTER writes"
    )
    assert kd_inactive.audience_scope is None


# ---- T4 — reverse restores stage-1 NULL state ----------


@pytest.mark.django_db
def test_reverse_restores_stage1_state_for_forward_touched_rows() -> None:
    ws = _make_workspace("stage2-t4@test.local", "Stage2 T4")
    u = _make_universe(ws, "T4 Universe")
    tm = _make_teammate(ws, "TmT4")

    kd_char = _make_kd(ws, "char-t4", spokespeople=[tm])
    kd_frozen = _make_kd(
        ws, "frozen-t4",
        pk=UNIVERSE_CANON_ROWS_20260821[1],
        universe=u,
    )
    kd_ambig = _make_kd(ws, "ambig-t4")

    apply_forward(django_apps, None)
    kd_char.refresh_from_db()
    kd_frozen.refresh_from_db()
    kd_ambig.refresh_from_db()
    assert kd_char.audience_scope == AudienceScope.CHARACTER
    assert kd_frozen.audience_scope == AudienceScope.UNIVERSE
    assert kd_ambig.audience_scope is None

    apply_reverse(django_apps, None)
    kd_char.refresh_from_db()
    kd_frozen.refresh_from_db()
    kd_ambig.refresh_from_db()

    assert kd_char.audience_scope is None, "CHARACTER must revert to NULL"
    assert kd_frozen.audience_scope is None, "UNIVERSE must revert to NULL"
    assert kd_ambig.audience_scope is None, "ambiguous row must remain NULL"


# ---- T5 — reverse does not touch unrelated values ------


@pytest.mark.django_db
def test_reverse_does_not_touch_unrelated_audience_values() -> None:
    """Reverse must not clobber audience_scope values that Stage 2's
    forward would NOT have set. Specifically:

    * A CHARACTER row with M2M=∅ (a Stage-3+ malformed shape that the
      forward Rule A shape-filter would NOT match) must be untouched
      by the reverse.
    * A UNIVERSE row whose PK is NOT in the frozen-3 must be untouched
      by the reverse.
    * A WORKSPACE row must be untouched.
    * A NONE row must be untouched.
    """
    ws = _make_workspace("stage2-t5@test.local", "Stage2 T5")
    u = _make_universe(ws, "T5 Universe")

    # Rows carrying non-Stage-2 audience values (simulating Stage-3+
    # state). Stage 2's reverse must not touch these.
    kd_workspace_preset = _make_kd(ws, "workspace-preset")
    kd_workspace_preset.audience_scope = AudienceScope.WORKSPACE
    kd_workspace_preset.save(update_fields=["audience_scope"])

    kd_none_preset = _make_kd(ws, "none-preset", is_active=False)
    kd_none_preset.audience_scope = AudienceScope.NONE
    kd_none_preset.deactivated_reason = "orphaned_by_teammate_delete"
    kd_none_preset.save(update_fields=[
        "audience_scope", "deactivated_reason",
    ])

    # Off-frozen UNIVERSE row (would not be set by Stage 2 forward, so
    # reverse must not touch).
    kd_off_frozen_universe = _make_kd(
        ws, "off-frozen-universe-preset", universe=u,
    )
    kd_off_frozen_universe.audience_scope = AudienceScope.UNIVERSE
    kd_off_frozen_universe.save(update_fields=["audience_scope"])
    assert str(kd_off_frozen_universe.pk) not in UNIVERSE_CANON_ROWS_20260821

    # CHARACTER-with-empty-M2M — Rule A shape filter would exclude this
    # from both forward and reverse. Must survive reverse untouched.
    kd_char_empty_m2m = _make_kd(ws, "char-empty-m2m-preset")
    kd_char_empty_m2m.audience_scope = AudienceScope.CHARACTER
    kd_char_empty_m2m.save(update_fields=["audience_scope"])

    # Preflight would fire on kd_none_preset (inactive) — so we cannot
    # run apply_forward with these preset rows present. Directly test
    # apply_reverse behavior against a mid-Stage-3+ mixed state.
    apply_reverse(django_apps, None)

    kd_workspace_preset.refresh_from_db()
    kd_none_preset.refresh_from_db()
    kd_off_frozen_universe.refresh_from_db()
    kd_char_empty_m2m.refresh_from_db()

    assert kd_workspace_preset.audience_scope == AudienceScope.WORKSPACE
    assert kd_none_preset.audience_scope == AudienceScope.NONE
    assert kd_off_frozen_universe.audience_scope == AudienceScope.UNIVERSE
    assert kd_char_empty_m2m.audience_scope == AudienceScope.CHARACTER


# ---- T6 — forward is idempotent ------------------------


@pytest.mark.django_db
def test_forward_is_idempotent() -> None:
    """Running the forward migration twice must produce identical state
    to running it once."""
    ws = _make_workspace("stage2-t6@test.local", "Stage2 T6")
    u = _make_universe(ws, "T6 Universe")
    tm = _make_teammate(ws, "TmT6")

    _make_kd(ws, "char-t6-a", spokespeople=[tm])
    _make_kd(ws, "char-t6-b", spokespeople=[tm])
    _make_kd(
        ws, "frozen-t6",
        pk=UNIVERSE_CANON_ROWS_20260821[2],
        universe=u,
    )
    _make_kd(ws, "ambig-t6")

    apply_forward(django_apps, None)
    state1 = tuple(sorted(
        KnowledgeDocument.objects.values_list("id", "audience_scope"),
        key=lambda r: str(r[0]),
    ))

    apply_forward(django_apps, None)
    state2 = tuple(sorted(
        KnowledgeDocument.objects.values_list("id", "audience_scope"),
        key=lambda r: str(r[0]),
    ))

    assert state1 == state2, "apply_forward is not idempotent"
