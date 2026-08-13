"""Postgres integration tests for concurrent identity-version
approval (§17.3.b, Correction 1 to SESSION 241 plan).

Ratified expectations these tests lock:

1. **Two concurrent service approvals of two different versions**
   serialize safely through the ``select_for_update`` lock. Both
   threads complete without raising; exactly one approved version
   exists at the end; the losing version ends ``superseded``.
   ``constraint_violation`` is NOT the expected outcome — that is
   the database's final defense against a bypass or implementation
   defect.

2. **Two concurrent service approvals of the same version** are
   idempotent. Both threads complete without raising; exactly one
   approved version exists at the end (the one both were trying
   to approve).

3. **Direct ORM bypass** attempting to create two approved rows on
   the same identity is refused by the Postgres partial unique
   constraint. That path is covered by
   ``test_models_substrate::test_partial_unique_constraint_blocks_direct_bypass``
   and re-asserted here in the concurrency context so all three
   cases live in one file for the reviewer.

``TransactionTestCase`` semantics are required so real
transactions cross the thread boundary; the ``django_db(transaction=True)``
marker below turns on that behavior. Each thread closes its
connection at teardown to avoid leaking.
"""
from __future__ import annotations

import threading

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connections, transaction

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetType
from apps.identity import services
from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    IdentityReference,
    IdentityReferenceKind,
    ReferenceState,
)

User = get_user_model()

pytestmark = pytest.mark.django_db(transaction=True)


def _valid_human_spec() -> dict:
    return {
        "spec_schema_version": 1,
        "age_presentation": {"min_years": 30, "max_years": 45},
        "skin_tone": {"descriptor": "medium olive", "undertone": "olive"},
        "hair": {"length": "medium", "texture": "wavy", "color": "dark brown"},
        "eye": {"color": "hazel", "shape": "almond"},
        "face_shape": {"descriptor": "oval"},
        "gender_presentation": {"descriptor": "feminine", "primary_axis": "feminine"},
        "canonical_outfit": {
            "descriptor": "cream linen blazer over a navy tee",
            "formality": "smart_casual",
            "material_family": "linen",
        },
    }


def _make_setup(email: str):
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    identity = CharacterIdentity.objects.create(
        workspace=ws,
        kind=CharacterIdentity.Kind.HUMAN,
        name="Ruby",
    )
    return user, ws, identity


def _satisfy_floor(ws: Workspace, version: CharacterIdentityVersion) -> None:
    for purpose in ("front", "neutral_rest"):
        asset = Asset.objects.create(
            workspace=ws,
            asset_type=AssetType.IMAGE,
            file_path=f"media/{version.pk}-{purpose}.png",
        )
        ref = services.attach_reference(
            version,
            asset=asset,
            kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
            purpose=purpose,
        )
        IdentityReference.objects.filter(pk=ref.pk).update(state=ReferenceState.APPROVED)


def _run_approval_in_thread(version_pk, user_pk, results, index) -> None:
    """Approve ``version_pk`` from a fresh thread. Each thread
    acquires its own Django connection lazily; we close it at
    the end so the connection returns to the pool.
    """
    try:
        version = CharacterIdentityVersion.objects.get(pk=version_pk)
        user = User.objects.get(pk=user_pk)
        approved = services.approve_version(version, approver=user)
        results[index] = ("ok", approved.pk, approved.state)
    except Exception as exc:  # pragma: no cover - surfaced via assert
        results[index] = ("error", type(exc).__name__, str(exc))
    finally:
        connections.close_all()


# ---- (1) two versions, two threads ---------------------------------


def test_concurrent_approvals_of_different_versions_serialize_safely() -> None:
    """Both operations serialize; final state contains exactly one
    approved version. The losing version ends superseded. No
    duplicate-approved window survives.
    """
    user, ws, identity = _make_setup("conc-two-versions@t")
    v_a = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    v_b = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    _satisfy_floor(ws, v_a)
    _satisfy_floor(ws, v_b)

    results: dict[int, tuple] = {}
    t_a = threading.Thread(
        target=_run_approval_in_thread,
        args=(v_a.pk, user.pk, results, 0),
    )
    t_b = threading.Thread(
        target=_run_approval_in_thread,
        args=(v_b.pk, user.pk, results, 1),
    )
    t_a.start()
    t_b.start()
    t_a.join(timeout=30)
    t_b.join(timeout=30)

    # Both threads must have completed without raising.
    assert results[0][0] == "ok", results[0]
    assert results[1][0] == "ok", results[1]

    # Exactly one approved version now exists on the identity.
    approved_qs = CharacterIdentityVersion.objects.filter(
        identity=identity, state="approved",
    )
    assert approved_qs.count() == 1

    # And it is one of the two versions we asked about (the last
    # writer wins the race, but the invariant holds either way).
    approved_pk = approved_qs.values_list("pk", flat=True).first()
    assert approved_pk in {v_a.pk, v_b.pk}

    # The other version must be superseded (not still draft, not
    # a duplicate approved). Non-approved must be exactly one
    # superseded row.
    non_approved = CharacterIdentityVersion.objects.filter(identity=identity).exclude(pk=approved_pk)
    assert non_approved.count() == 1
    assert non_approved.first().state == "superseded"


# ---- (2) same version, two threads --------------------------------


def test_concurrent_approvals_of_same_version_are_idempotent() -> None:
    """Both threads complete without raising; exactly that version
    is approved at the end.
    """
    user, ws, identity = _make_setup("conc-same-version@t")
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    _satisfy_floor(ws, version)

    results: dict[int, tuple] = {}
    t_a = threading.Thread(
        target=_run_approval_in_thread,
        args=(version.pk, user.pk, results, 0),
    )
    t_b = threading.Thread(
        target=_run_approval_in_thread,
        args=(version.pk, user.pk, results, 1),
    )
    t_a.start()
    t_b.start()
    t_a.join(timeout=30)
    t_b.join(timeout=30)

    assert results[0][0] == "ok", results[0]
    assert results[1][0] == "ok", results[1]

    # Exactly one approved row, and it is our version.
    approved = CharacterIdentityVersion.objects.filter(
        identity=identity, state="approved",
    )
    assert approved.count() == 1
    assert approved.first().pk == version.pk


# ---- (3) direct ORM bypass ----------------------------------------


def test_direct_orm_bypass_two_approved_rows_raises_integrity_error() -> None:
    """Even if the service layer is bypassed (direct ORM
    ``.objects.create()``, admin, shell, migration code) the DB
    partial unique constraint refuses two approved rows against
    the same identity (§17.3.b).
    """
    _, ws, identity = _make_setup("conc-orm-bypass@t")
    v1 = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    _satisfy_floor(ws, v1)
    CharacterIdentityVersion.objects.filter(pk=v1.pk).update(
        state=CharacterIdentityVersion.State.APPROVED,
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CharacterIdentityVersion.objects.create(
                identity=identity,
                revision=2,
                state=CharacterIdentityVersion.State.APPROVED,
                spec={},
                spec_schema_version=1,
            )
