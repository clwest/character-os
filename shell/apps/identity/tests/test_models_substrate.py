"""Canonical Identity substrate — model-shape tests (2.a slice).

Covers ``CharacterIdentity`` and ``CharacterIdentityVersion`` only.
Concurrency / service-level approval semantics live in the 2.d
tests once the write-path service lands.

The load-bearing DB invariant tested here is the ratified
partial unique constraint from §17.3.b:

    UNIQUE (character_identity_id) WHERE state = 'approved'
    -- name: one_approved_version_per_character_identity

That invariant is validated by attempting a **direct ORM bypass**
of the service layer — creating two approved versions against the
same identity via ``.objects.create()``. Postgres must reject the
second insert. This is a database-level invariant test; it does
not claim the service layer produces this outcome under normal
operation. Service-level serialization (which prevents this shape
of contention in the first place) is tested in 2.d.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.accounts.models import Workspace
from apps.identity.models import CharacterIdentity, CharacterIdentityVersion
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- helpers --------------------------------------------------------


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None, "workspace should be auto-provisioned on signup"
    return ws


def _make_identity(
    ws: Workspace,
    *,
    name: str = "Ruby",
    kind: str = CharacterIdentity.Kind.HUMAN,
    teammate: Teammate | None = None,
) -> CharacterIdentity:
    return CharacterIdentity.objects.create(
        workspace=ws,
        teammate=teammate,
        kind=kind,
        name=name,
    )


def _make_version(
    identity: CharacterIdentity,
    *,
    revision: int = 1,
    state: str = CharacterIdentityVersion.State.DRAFT,
    spec: dict | None = None,
) -> CharacterIdentityVersion:
    return CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=revision,
        state=state,
        spec=spec if spec is not None else {},
        spec_schema_version=1,
    )


# ---- CharacterIdentity: round-trip + unique name -------------------


def test_character_identity_round_trip() -> None:
    ws = _make_workspace("ci-round-trip@t")
    identity = _make_identity(ws, name="Alex", kind=CharacterIdentity.Kind.HUMAN)

    reloaded = CharacterIdentity.objects.get(pk=identity.pk)
    assert reloaded.workspace_id == ws.id
    assert reloaded.name == "Alex"
    assert reloaded.kind == "human"
    assert reloaded.teammate_id is None  # nullable during bootstrap (§15.1)
    assert reloaded.archived_at is None
    assert reloaded.created_at is not None


def test_character_identity_teammate_fk_nullable_during_bootstrap() -> None:
    """§15.1 — benchmark fixtures land as identities without a
    Teammate; the FK is nullable so bootstrap can proceed before a
    customer-facing Teammate exists.
    """
    ws = _make_workspace("ci-bootstrap@t")
    identity = _make_identity(ws, name="Fixture-H1", teammate=None)
    assert identity.teammate is None


def test_character_identity_unique_name_per_workspace() -> None:
    ws = _make_workspace("ci-uniq@t")
    _make_identity(ws, name="Alex")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _make_identity(ws, name="Alex")


def test_character_identity_same_name_different_workspaces_ok() -> None:
    ws_a = _make_workspace("ci-cross-a@t")
    ws_b = _make_workspace("ci-cross-b@t")
    _make_identity(ws_a, name="Alex")
    _make_identity(ws_b, name="Alex")  # must not raise


def test_character_identity_kind_choices_enforced() -> None:
    ws = _make_workspace("ci-kind@t")
    assert CharacterIdentity.Kind.HUMAN == "human"
    assert CharacterIdentity.Kind.NON_HUMAN == "non_human"
    # Enforcement happens at full_clean() time (choices are not DB
    # constraints in Django by default). The write-path service
    # (2.d) is the authoritative gate; this test locks the enum
    # values themselves so downstream schemas don't drift.
    identity = _make_identity(ws, name="NH-Test", kind=CharacterIdentity.Kind.NON_HUMAN)
    assert identity.kind == "non_human"


# ---- CharacterIdentityVersion: shape + revision uniqueness ---------


def test_character_identity_version_round_trip() -> None:
    ws = _make_workspace("civ-round-trip@t")
    identity = _make_identity(ws, name="Alex")
    version = _make_version(identity, revision=1, spec={"spec_schema_version": 1})

    reloaded = CharacterIdentityVersion.objects.get(pk=version.pk)
    assert reloaded.identity_id == identity.id
    assert reloaded.revision == 1
    assert reloaded.state == "draft"
    assert reloaded.spec_schema_version == 1
    assert reloaded.spec == {"spec_schema_version": 1}
    assert reloaded.approved_at is None
    assert reloaded.superseded_at is None
    assert reloaded.approved_by is None


def test_character_identity_version_unique_revision_per_identity() -> None:
    ws = _make_workspace("civ-uniq-rev@t")
    identity = _make_identity(ws, name="Alex")
    _make_version(identity, revision=1)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _make_version(identity, revision=1)


def test_character_identity_version_same_revision_across_identities_ok() -> None:
    ws = _make_workspace("civ-cross-identity@t")
    identity_a = _make_identity(ws, name="Alex")
    identity_b = _make_identity(ws, name="Blake")
    _make_version(identity_a, revision=1)
    _make_version(identity_b, revision=1)  # must not raise


# ---- Partial unique constraint (§17.3.b) — DB-level invariant ------


def test_partial_unique_constraint_blocks_direct_bypass() -> None:
    """§17.3.b — the DB partial unique constraint is the final
    invariant. Even if the service layer is bypassed (direct ORM
    ``.objects.create()``, admin, shell, migration code) the DB
    must reject a second approved row for the same identity.

    This is not a claim about how the service behaves under
    concurrent load — that is tested in 2.d.
    """
    ws = _make_workspace("civ-partial-unique@t")
    identity = _make_identity(ws, name="Alex")
    _make_version(
        identity,
        revision=1,
        state=CharacterIdentityVersion.State.APPROVED,
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _make_version(
                identity,
                revision=2,
                state=CharacterIdentityVersion.State.APPROVED,
            )


def test_partial_unique_constraint_permits_zero_approved() -> None:
    """§17.3.b — the constraint permits zero approved versions. An
    identity in draft with no approvals yet is a legal state.
    """
    ws = _make_workspace("civ-partial-zero@t")
    identity = _make_identity(ws, name="Alex")
    _make_version(identity, revision=1, state=CharacterIdentityVersion.State.DRAFT)
    _make_version(identity, revision=2, state=CharacterIdentityVersion.State.DRAFT)
    approved = CharacterIdentityVersion.objects.filter(
        identity=identity,
        state="approved",
    ).count()
    assert approved == 0


def test_partial_unique_constraint_permits_multiple_non_approved() -> None:
    """The constraint targets ``state='approved'`` only. Multiple
    draft / superseded / rejected rows against the same identity
    are all legal.
    """
    ws = _make_workspace("civ-partial-multi@t")
    identity = _make_identity(ws, name="Alex")
    _make_version(identity, revision=1, state=CharacterIdentityVersion.State.SUPERSEDED)
    _make_version(identity, revision=2, state=CharacterIdentityVersion.State.SUPERSEDED)
    _make_version(identity, revision=3, state=CharacterIdentityVersion.State.REJECTED)
    _make_version(identity, revision=4, state=CharacterIdentityVersion.State.DRAFT)
    # No IntegrityError. Substrate must accept this multi-state
    # history because supersede-plus-approve is the normal
    # migration path across authoring rounds.


def test_partial_unique_constraint_permits_approved_across_identities() -> None:
    """The constraint is per-identity; two different identities may
    each have an approved version simultaneously.
    """
    ws = _make_workspace("civ-partial-across@t")
    identity_a = _make_identity(ws, name="Alex")
    identity_b = _make_identity(ws, name="Blake")
    _make_version(
        identity_a,
        revision=1,
        state=CharacterIdentityVersion.State.APPROVED,
    )
    _make_version(
        identity_b,
        revision=1,
        state=CharacterIdentityVersion.State.APPROVED,
    )  # must not raise
