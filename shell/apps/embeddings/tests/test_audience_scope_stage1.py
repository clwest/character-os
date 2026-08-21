"""SESSION 276 Slice 5 / Delta Stage 1 — inertness tests.

Verifies that adding the nullable ``KnowledgeDocument.audience_scope``
field is a schema-only additive change that does not affect any
existing runtime semantics:

* Test A — model default is NULL when the field is unspecified on create.
* Test B — existing rows have ``audience_scope IS NULL`` post-migration
  (asserted via a fresh KD create; the production DB verification is in
  ``docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md`` §75).
* Test C — all four choice values are accepted when directly assigned.
* Test D (invariant NON-enforcement) — Stage 1 must NOT yet enforce any
  audience invariant (e.g. ``CHARACTER`` with empty M2M must still
  save). Deferred to later Delta stages.

Retrieval regression + SESSION 275 lifecycle regression are covered by
running the existing suites, not by this file.

See ``docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md`` §72-§80.
"""
from __future__ import annotations

import pytest

from apps.accounts.models import Workspace
from apps.embeddings.models import (
    AudienceScope,
    DocumentType,
    IngestedVia,
    KnowledgeDocument,
)
from django.contrib.auth import get_user_model

User = get_user_model()


# ---- fixtures --------------------------------------------


def _make_workspace(email: str, name: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws


def _make_kd(ws: Workspace, title: str = "Stage 1 KD", **kwargs) -> KnowledgeDocument:
    defaults = dict(
        workspace=ws,
        title=title,
        document_type=DocumentType.TEXT,
        raw_content="body",
        processed_content="body",
        content_hash=f"hash-{title}",
        ingested_via=IngestedVia.PASTE,
    )
    defaults.update(kwargs)
    return KnowledgeDocument.objects.create(**defaults)


# ---- Test A — default NULL on create ---------------------


@pytest.mark.django_db
def test_audience_scope_defaults_to_null_when_unspecified() -> None:
    """SESSION 276 Slice 5 Test A. Creating a KD without specifying
    ``audience_scope`` leaves it NULL — no default classifies the row.

    Stage 1 invariant: no code path assigns an audience_scope value.
    """
    ws = _make_workspace("stage1-a@test.local", "Stage1 WS A")
    kd = _make_kd(ws)
    kd.refresh_from_db()
    assert kd.audience_scope is None, (
        f"Expected NULL default; got {kd.audience_scope!r}. Stage 1 must "
        "not classify rows automatically."
    )


# ---- Test B — Stage 1 does not touch other lifecycle fields


@pytest.mark.django_db
def test_stage1_leaves_existing_lifecycle_fields_untouched() -> None:
    """SESSION 276 Slice 5 Test B (surrogate). A freshly created KD
    still has the pre-Delta lifecycle shape: is_active=True,
    deactivated_reason='', universe=None, spokespeople=∅. Nothing about
    Stage 1 changes those. Together with the DB verification in
    §75 of the audit doc, this asserts that Stage 1 is behaviorally
    inert for both new and existing rows.
    """
    ws = _make_workspace("stage1-b@test.local", "Stage1 WS B")
    kd = _make_kd(ws)
    kd.refresh_from_db()
    assert kd.audience_scope is None
    assert kd.is_active is True
    assert kd.deactivated_reason == ""
    assert kd.universe_id is None
    assert kd.spokespeople.count() == 0


# ---- Test C — choice validity ---------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "value",
    [
        AudienceScope.CHARACTER,
        AudienceScope.UNIVERSE,
        AudienceScope.WORKSPACE,
        AudienceScope.NONE,
    ],
)
def test_audience_scope_accepts_all_four_choices(value: str) -> None:
    """SESSION 276 Slice 5 Test C. Direct assignment of each valid
    choice succeeds and round-trips through the DB. Stage 1 does NOT
    yet enforce invariants (CHARACTER→M2M≥1, UNIVERSE→universe non-null,
    etc.) so this test intentionally exercises each value without a
    consistent surrounding shape — it proves choice validity ONLY.
    """
    ws = _make_workspace(
        f"stage1-c-{value}@test.local", f"Stage1 WS C-{value}",
    )
    kd = _make_kd(ws, title=f"Stage1 KD {value}", audience_scope=value)
    kd.refresh_from_db()
    assert kd.audience_scope == value


# ---- Test D — invariant NON-enforcement in Stage 1 ------


@pytest.mark.django_db
def test_stage1_does_not_yet_enforce_character_requires_m2m() -> None:
    """SESSION 276 Slice 5 Test D. Assigning ``audience_scope=CHARACTER``
    to a row with an empty M2M must SUCCEED in Stage 1. The
    ``CHARACTER → M2M ≥ 1`` invariant (Slice 4 §52 #1) belongs to
    later Delta stages; enforcing it now would be an out-of-scope
    behavior change and would break the Stage 1 promise of zero
    lifecycle behavior change.

    This test guards against accidental early invariant enforcement.
    """
    ws = _make_workspace("stage1-d@test.local", "Stage1 WS D")
    kd = _make_kd(ws, audience_scope=AudienceScope.CHARACTER)
    # No M2M assigned. In post-Delta stages this row would be
    # rejected; in Stage 1 it must be a legitimate save.
    kd.refresh_from_db()
    assert kd.audience_scope == AudienceScope.CHARACTER
    assert kd.spokespeople.count() == 0
    assert kd.is_active is True


@pytest.mark.django_db
def test_stage1_does_not_yet_enforce_universe_requires_non_null_universe() -> None:
    """SESSION 276 Slice 5 Test D (paired). Assigning
    ``audience_scope=UNIVERSE`` with ``universe=None`` must SUCCEED
    in Stage 1. The ``UNIVERSE → universe non-null`` invariant
    (Slice 4 §52 #2) belongs to later stages.
    """
    ws = _make_workspace("stage1-d2@test.local", "Stage1 WS D2")
    kd = _make_kd(ws, audience_scope=AudienceScope.UNIVERSE)
    kd.refresh_from_db()
    assert kd.audience_scope == AudienceScope.UNIVERSE
    assert kd.universe_id is None
    assert kd.is_active is True


@pytest.mark.django_db
def test_stage1_does_not_yet_enforce_none_requires_inactive() -> None:
    """SESSION 276 Slice 5 Test D (paired). Assigning
    ``audience_scope=NONE`` to an active row must SUCCEED in Stage 1.
    The ``NONE → is_active=False`` invariant (Slice 4 §52 #4) belongs
    to later stages.
    """
    ws = _make_workspace("stage1-d3@test.local", "Stage1 WS D3")
    kd = _make_kd(ws, audience_scope=AudienceScope.NONE)
    kd.refresh_from_db()
    assert kd.audience_scope == AudienceScope.NONE
    assert kd.is_active is True
