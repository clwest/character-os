"""SESSION 276 / Slice 21 / Delta Stage 8 — DB constraint regression.

Q-276-37. Verifies migration 0009's scalar CheckConstraints reject
malformed Delta shapes at the DB layer AND that valid shapes succeed.

Test taxonomy A-G:

  * A — UNIVERSE + universe_id=NULL → DB rejects
        (session276_universe_requires_universe_fk)
  * B — WORKSPACE + universe_id non-NULL → DB rejects
        (session276_workspace_forbids_universe_fk)
  * C — NONE + is_active=True → DB rejects
        (session276_none_requires_inactive)
  * D — UNIVERSE + universe_id non-NULL → succeeds
  * E — WORKSPACE + universe_id=NULL → succeeds
  * F — NONE + is_active=False → succeeds
  * G — audience_scope=NULL → DB rejects (NOT NULL column)

Plus reference to the CHARACTER→M2M-non-empty invariant, which is
INTENTIONALLY app-layer-only (not encoded here). See
docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md §361.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.accounts.models import Workspace
from apps.embeddings.models import (
    AudienceScope,
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeDocument,
)
from apps.universe.models import Universe

User = get_user_model()

pytestmark = pytest.mark.django_db


def _mk_ws(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _base(ws: Workspace, title: str, **overrides) -> dict:
    """Base valid KD kwargs; caller overrides specific fields to
    exercise each constraint."""
    return dict(
        workspace=ws,
        title=title,
        document_type=DocumentType.TEXT,
        raw_content=title,
        processed_content=title,
        content_hash=f"hash-{title}",
        ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
        **overrides,
    )


# ---- A — UNIVERSE + universe_id=NULL rejected ----------------------


def test_slice21_A_universe_requires_universe_fk():
    ws = _mk_ws("s21a@t.test")
    with pytest.raises(IntegrityError) as exc:
        with transaction.atomic():
            KnowledgeDocument.objects.create(
                **_base(ws, "univ-nofk", audience_scope=AudienceScope.UNIVERSE),
                # universe=None omitted → NULL
            )
    assert "session276_universe_requires_universe_fk" in str(exc.value)


# ---- B — WORKSPACE + universe_id non-NULL rejected -----------------


def test_slice21_B_workspace_forbids_universe_fk():
    ws = _mk_ws("s21b@t.test")
    u = Universe.objects.create(workspace=ws, name="U")
    with pytest.raises(IntegrityError) as exc:
        with transaction.atomic():
            KnowledgeDocument.objects.create(
                **_base(ws, "ws-withfk", audience_scope=AudienceScope.WORKSPACE, universe=u),
            )
    assert "session276_workspace_forbids_universe_fk" in str(exc.value)


# ---- C — NONE + is_active=True rejected ----------------------------


def test_slice21_C_none_requires_inactive():
    ws = _mk_ws("s21c@t.test")
    with pytest.raises(IntegrityError) as exc:
        with transaction.atomic():
            KnowledgeDocument.objects.create(
                **_base(ws, "none-active", audience_scope=AudienceScope.NONE, is_active=True),
            )
    assert "session276_none_requires_inactive" in str(exc.value)


# ---- D — UNIVERSE + universe_id non-NULL succeeds ------------------


def test_slice21_D_universe_with_universe_fk_succeeds():
    ws = _mk_ws("s21d@t.test")
    u = Universe.objects.create(workspace=ws, name="U")
    doc = KnowledgeDocument.objects.create(
        **_base(ws, "univ-ok", audience_scope=AudienceScope.UNIVERSE, universe=u),
    )
    assert doc.audience_scope == AudienceScope.UNIVERSE
    assert doc.universe_id == u.pk


# ---- E — WORKSPACE + universe_id=NULL succeeds ---------------------


def test_slice21_E_workspace_without_universe_fk_succeeds():
    ws = _mk_ws("s21e@t.test")
    doc = KnowledgeDocument.objects.create(
        **_base(ws, "ws-ok", audience_scope=AudienceScope.WORKSPACE, universe=None),
    )
    assert doc.audience_scope == AudienceScope.WORKSPACE
    assert doc.universe_id is None


# ---- F — NONE + is_active=False succeeds ---------------------------


def test_slice21_F_none_inactive_succeeds():
    ws = _mk_ws("s21f@t.test")
    doc = KnowledgeDocument.objects.create(
        **_base(ws, "none-inactive", audience_scope=AudienceScope.NONE, is_active=False),
    )
    assert doc.audience_scope == AudienceScope.NONE
    assert doc.is_active is False


# ---- G — audience_scope=NULL rejected (NOT NULL) -------------------


def test_slice21_G_audience_scope_not_null():
    """The Slice-21 AlterField migration made ``audience_scope`` NOT
    NULL. Direct ORM creates that pass ``audience_scope=None`` should
    raise IntegrityError at commit time.

    (Omitting the field entirely lets Django fall back to a blank
    string default; explicit ``None`` bypasses that and reaches the
    NOT NULL check directly.)
    """
    ws = _mk_ws("s21g@t.test")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            KnowledgeDocument.objects.create(
                **_base(ws, "no-audience", audience_scope=None),
            )


# ---- CHARACTER-M2M invariant note ----------------------------------


def test_slice21_character_m2m_invariant_lives_at_application_layer():
    """The CHARACTER → non-empty M2M invariant is NOT encoded as a DB
    constraint. A row-level ``CheckConstraint`` on ``KnowledgeDocument``
    cannot inspect the ``embeddings_knowledgedocument_spokespeople``
    through-table. The invariant is instead enforced by SESSION 276
    Slices 8/10/13/14/15/20 at every mutation surface:

      * Fresh CREATE (Slice 10) — CHARACTER only stamped when
        spokespeople is supplied.
      * Fresh CREATE (Slice 20) — no-signal CREATE fails closed.
      * Orphan revival (Slice 9) — rejects revival without positive
        audience.
      * Final-character detach (Slice 13) — rejects POST /detach/
        that would empty CHARACTER's M2M.
      * PATCH ``spokesperson_ids=[]`` (Slice 14) — rejects.
      * Universe reassignment (Slice 15) — shape guards.

    This test is a documentation / meta-assertion: it verifies that
    the DB permits an active CHARACTER row with empty M2M (which the
    APPLICATION layer prohibits). The absence of a matching
    IntegrityError proves the constraint is intentionally not at the
    DB layer.

    See docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md §361 for
    the full enforcement-layer distinction.
    """
    ws = _mk_ws("s21-char-note@t.test")
    doc = KnowledgeDocument.objects.create(
        **_base(ws, "char-empty-m2m", audience_scope=AudienceScope.CHARACTER),
        # No spokespeople attached. The DB permits this; the app layer
        # rejects it via the guards documented above.
    )
    assert doc.audience_scope == AudienceScope.CHARACTER
    assert doc.spokespeople.count() == 0
