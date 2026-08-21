"""SESSION 275 — Slice 3 regression contract.

Guards the audience invariant from Slice 2 §23:

    A removal or deletion action must never broaden the audience
    of surviving knowledge unless the operator explicitly chooses
    that broader audience.

Test matrix (§32 of the audit doc, extended with the ingestion
revival gate + the atomicity failure-injection case added after
Chris + ChatGPT review of Slice 3 flagged §50 as reasoned-only):

  1. Last spokesperson delete — legacy scope → KD archived
  2. Last spokesperson delete — Universe scope → KD archived
  3. Multi-spokesperson delete-one → KD stays active
  4. Sequential delete-final → last delete archives
  5. Born-empty Class C canon survives Universe member delete
  6. Born-empty Class A canon survives unrelated legacy delete
  7. Chunks + embeddings survive orphan archive
  8. Composition provenance resolves after orphan archive
  9. Bulk QuerySet.delete triggers per-row orphan archive
 10. deactivated_reason distinguishes operator vs orphan paths
 11. Ingestion revival rejects orphan-archived KD without new sp
 12. Ingestion revival of operator-deleted KD works unchanged
 13. Atomicity: archive-step failure rolls back the whole delete

SESSION 276 Slice 8 / Delta Stage 3A (Q-276-18) extends the archive
step so a true final-character orphan is stamped
``audience_scope=AudienceScope.NONE`` in the SAME bulk ``.update(...)``
call. Tests are extended in place — same test IDs, additional
audience_scope assertions — so a future regression against either
SESSION 275's original contract OR Delta's audience-invariant
extension fires on the same row.

If any assertion fails, the audience invariant is broken. Do not
"fix" the tests. Fix the model, the migration, the signal, or the
ingestion gate. See
``docs/design/SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md`` +
``docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md`` §99-§121.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.models import Composition
from apps.embeddings.ingestion import (
    OrphanRevivalRejected,
    ingest_text,
)
from apps.embeddings.models import (
    AudienceScope,
    DeactivationReason,
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeChunk,
    KnowledgeDocument,
)
from apps.embeddings.retrieval import (
    resolve_chunk_ids_to_docs,
    retrieve_for_teammate,
)
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe

User = get_user_model()

pytestmark = pytest.mark.django_db


EMBEDDING_DIM = 1536


# ---- fixtures --------------------------------------------------------


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None, "auto-created workspace missing"
    return ws


def _vec(seed: float) -> list[float]:
    v = [0.0] * EMBEDDING_DIM
    v[0] = seed
    return v


def _make_kd(
    ws: Workspace,
    title: str,
    *,
    spokespeople: list[Teammate] | None = None,
    universe: Universe | None = None,
    content_seed: str = "",
    with_chunk: bool = True,
    chunk_vector_seed: float = 1.0,
) -> KnowledgeDocument:
    """Create a processed KD with one chunk. Chunks include a real
    pgvector vector so retrieval assertions work end-to-end."""
    kd = KnowledgeDocument.objects.create(
        workspace=ws,
        universe=universe,
        title=title,
        document_type=DocumentType.TEXT,
        raw_content=title,
        processed_content=title,
        content_hash=f"hash-{title}-{content_seed}",
        ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )
    if spokespeople:
        kd.spokespeople.set(spokespeople)
    if with_chunk:
        KnowledgeChunk.objects.create(
            document=kd,
            chunk_index=0,
            chunk_text=title,
            chunk_size=len(title),
            embedding_vector=_vec(chunk_vector_seed),
        )
    return kd


# ---- 1. last spokesperson delete — legacy scope -----------------------


def test_last_spokesperson_delete_legacy_inactivates_kd():
    """Case 1 (§26 row 1): universe=None, spokespeople={A}.
    Deleting A must archive the KD and remove it from any other
    legacy teammate's retrieval.

    SESSION 276 Slice 8 extension: the archive write also stamps
    ``audience_scope=NONE`` — the true orphan has no safe surviving
    audience.
    """
    ws = _make_workspace("s275-1@t")
    a = Teammate.objects.create(workspace=ws, name="Alpha")
    other = Teammate.objects.create(workspace=ws, name="Other")
    kd = _make_kd(ws, "private-to-alpha", spokespeople=[a])
    assert kd.is_active is True
    assert kd.deactivated_reason == ""
    # Fixture default: Stage 3 mutation-surface pass hasn't happened;
    # test-factory-created KDs still start with audience_scope=None.
    assert kd.audience_scope is None

    a.delete()

    kd.refresh_from_db()
    assert kd.is_active is False
    assert kd.deactivated_reason == DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE
    assert kd.audience_scope == AudienceScope.NONE  # SESSION 276 Slice 8
    assert kd.spokespeople.count() == 0  # through-row cascaded

    # And it must not surface to any other legacy teammate.
    hits = retrieve_for_teammate(other, _query_vector=_vec(1.0), top_k=10)
    assert kd.id not in {c.document_id for c in hits}


# ---- 2. last spokesperson delete — Universe scope ---------------------


def test_last_spokesperson_delete_universe_inactivates_kd():
    """Case 2 (§26 row 2): universe=U, spokespeople={A}.
    Deleting A must archive the KD and NOT promote it to Class C
    Universe-shared for other teammates in U.

    SESSION 276 Slice 8 extension: same NONE stamp as Case 1.
    """
    ws = _make_workspace("s275-2@t")
    u = Universe.objects.create(workspace=ws, name="World")
    a = Teammate.objects.create(workspace=ws, name="A", universe=u)
    other = Teammate.objects.create(workspace=ws, name="B", universe=u)
    kd = _make_kd(ws, "private-in-U", universe=u, spokespeople=[a])

    a.delete()

    kd.refresh_from_db()
    assert kd.is_active is False
    assert kd.deactivated_reason == DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE
    assert kd.audience_scope == AudienceScope.NONE  # SESSION 276 Slice 8
    assert kd.universe_id == u.id  # Universe untouched
    assert kd.spokespeople.count() == 0

    hits = retrieve_for_teammate(other, _query_vector=_vec(1.0), top_k=10)
    assert kd.id not in {c.document_id for c in hits}


# ---- 3. multi-spokesperson: delete-one leaves KD active --------------


def test_multi_spokesperson_delete_one_leaves_kd_active():
    """Case 3 (§26 rows 3/4): spokespeople={A,B}. Deleting A
    narrows the audience to {B} — safe. KD stays active; B still
    retrieves it.

    SESSION 276 Slice 8 extension: narrowing deletes must NOT stamp
    NONE — the signal filter (``sp_count=0``) already excludes this
    KD from the archive set. ``audience_scope`` is preserved from
    its pre-delete value (None in the current transitional fixture;
    would be CHARACTER after Stage 3B).
    """
    ws = _make_workspace("s275-3@t")
    a = Teammate.objects.create(workspace=ws, name="A")
    b = Teammate.objects.create(workspace=ws, name="B")
    kd = _make_kd(ws, "shared-ab", spokespeople=[a, b])
    pre_delete_audience_scope = kd.audience_scope

    a.delete()

    kd.refresh_from_db()
    assert kd.is_active is True
    assert kd.deactivated_reason == ""
    # SESSION 276 Slice 8: narrowing preserves audience_scope; must
    # NOT be NONE.
    assert kd.audience_scope == pre_delete_audience_scope
    assert kd.audience_scope != AudienceScope.NONE
    assert list(kd.spokespeople.values_list("pk", flat=True)) == [b.pk]

    hits = retrieve_for_teammate(b, _query_vector=_vec(1.0), top_k=10)
    assert kd.id in {c.document_id for c in hits}


# ---- 4. sequential delete-final archives ------------------------------


def test_multi_spokesperson_delete_sequential_final_archives():
    """Case 4 (§26 row 5): after A→{B}, deleting B must archive.

    SESSION 276 Slice 8 extension: intermediate delete preserves
    ``audience_scope``; final delete stamps NONE.
    """
    ws = _make_workspace("s275-4@t")
    a = Teammate.objects.create(workspace=ws, name="A")
    b = Teammate.objects.create(workspace=ws, name="B")
    kd = _make_kd(ws, "shared-ab-seq", spokespeople=[a, b])
    pre_delete_audience_scope = kd.audience_scope

    a.delete()
    kd.refresh_from_db()
    assert kd.is_active is True
    assert kd.audience_scope == pre_delete_audience_scope  # narrowing preserves
    assert kd.audience_scope != AudienceScope.NONE

    b.delete()
    kd.refresh_from_db()
    assert kd.is_active is False
    assert kd.deactivated_reason == DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE
    assert kd.audience_scope == AudienceScope.NONE  # SESSION 276 Slice 8
    assert kd.spokespeople.count() == 0


# ---- 5. Class C canon survives Universe-member delete -----------------


def test_born_empty_class_c_canon_survives_universe_member_delete():
    """Case 5 (§26 row 7): KD born with spokespeople=∅ inside a
    Universe is Universe-shared canon. Deleting any Universe
    member must NOT touch it — the deleted member was never in
    the M2M.

    SESSION 276 Slice 8 extension: intentional canon must NOT be
    stamped NONE. The pre-delete snapshot excludes this KD from
    the archive candidate set (Ruby was never in the M2M), so the
    signal's ``.update()`` never touches it.
    """
    ws = _make_workspace("s275-5@t")
    u = Universe.objects.create(workspace=ws, name="Bakery")
    ruby = Teammate.objects.create(workspace=ws, name="Ruby", universe=u)
    witness = Teammate.objects.create(workspace=ws, name="Witness", universe=u)
    canon = _make_kd(ws, "bakery-hours-canon", universe=u)  # spokespeople=∅
    assert canon.spokespeople.count() == 0
    pre_delete_audience_scope = canon.audience_scope

    ruby.delete()

    canon.refresh_from_db()
    assert canon.is_active is True, "born-empty Class C canon must survive"
    assert canon.deactivated_reason == ""
    # SESSION 276 Slice 8: canon must remain unchanged; NOT stamped NONE.
    assert canon.audience_scope == pre_delete_audience_scope
    assert canon.audience_scope != AudienceScope.NONE
    assert canon.universe_id == u.id
    hits = retrieve_for_teammate(witness, _query_vector=_vec(1.0), top_k=10)
    assert canon.id in {c.document_id for c in hits}


# ---- 6. Class A canon survives unrelated legacy delete ---------------


def test_born_empty_class_a_canon_survives_unrelated_delete():
    """Case 6 (§26 row 6): universe=None, spokespeople=∅ from
    intentional authoring. Deleting an unrelated legacy teammate
    must NOT touch it.

    SESSION 276 Slice 8 extension: same as Case 5 — canon must
    NOT be stamped NONE by an unrelated teammate delete.
    """
    ws = _make_workspace("s275-6@t")
    unrelated = Teammate.objects.create(workspace=ws, name="Unrelated")
    canon = _make_kd(ws, "workspace-canon")  # universe=None, spokespeople=∅
    pre_delete_audience_scope = canon.audience_scope

    unrelated.delete()

    canon.refresh_from_db()
    assert canon.is_active is True
    assert canon.deactivated_reason == ""
    assert canon.audience_scope == pre_delete_audience_scope
    assert canon.audience_scope != AudienceScope.NONE


# ---- 7. chunks + embeddings survive orphan archive -------------------


def test_chunks_and_embeddings_survive_orphan_archive():
    """Case 7: the archive step must NOT drop chunks or vectors.

    SESSION 276 Slice 8 extension: also confirms the archive stamps
    NONE while preserving chunk data.
    """
    ws = _make_workspace("s275-7@t")
    a = Teammate.objects.create(workspace=ws, name="A")
    kd = _make_kd(ws, "keep-my-chunks", spokespeople=[a])
    KnowledgeChunk.objects.create(
        document=kd, chunk_index=1, chunk_text="second",
        chunk_size=6, embedding_vector=_vec(0.5),
    )
    KnowledgeChunk.objects.create(
        document=kd, chunk_index=2, chunk_text="third",
        chunk_size=5, embedding_vector=_vec(0.25),
    )
    assert kd.chunks.count() == 3

    a.delete()

    kd.refresh_from_db()
    assert kd.is_active is False
    assert kd.audience_scope == AudienceScope.NONE  # SESSION 276 Slice 8
    assert kd.chunks.count() == 3
    for chunk in kd.chunks.all():
        assert chunk.embedding_vector is not None
        assert len(chunk.embedding_vector) == EMBEDDING_DIM


# ---- 8. Composition provenance resolves after orphan archive ---------


def test_composition_provenance_resolves_after_orphan_archive():
    """Case 8: ``resolve_chunk_ids_to_docs`` does NOT filter
    ``is_active``. Historical composition provenance must still
    return the archived KD's chunks + title after an orphan
    archive."""
    ws = _make_workspace("s275-8@t")
    a = Teammate.objects.create(workspace=ws, name="A")
    kd = _make_kd(ws, "provenance-source", spokespeople=[a])
    chunk_ids = [str(c.id) for c in kd.chunks.all()]
    comp = Composition.objects.create(
        workspace=ws,
        spokesperson=a,
        name="Historical render",
        template_kind="talking_head",
        knowledge_chunk_ids=chunk_ids,
    )

    a.delete()

    kd.refresh_from_db()
    assert kd.is_active is False
    assert kd.audience_scope == AudienceScope.NONE  # SESSION 276 Slice 8
    # Composition survives (SET_NULL from SESSION 251) and its
    # provenance list still holds the same chunk UUIDs.
    comp.refresh_from_db()
    assert comp.spokesperson_id is None
    assert comp.knowledge_chunk_ids == chunk_ids
    # Resolver returns the doc + chunk_count despite is_active=False.
    # Output shape: [{"id", "title", "chunk_count"}] per
    # ``shell/apps/embeddings/retrieval.py:111-115``.
    resolved = resolve_chunk_ids_to_docs(chunk_ids, workspace=ws)
    assert len(resolved) == 1
    assert resolved[0]["id"] == str(kd.id)
    assert resolved[0]["title"] == kd.title
    assert resolved[0]["chunk_count"] == len(chunk_ids)


# ---- 9. bulk QuerySet.delete triggers per-row archive ---------------


def test_bulk_queryset_delete_triggers_orphan_archive_per_row():
    """Case 11 (§28 concern): admin's ``delete_selected`` uses
    ``QuerySet.delete()`` — Django fires pre_delete PER ROW. The
    archive must happen for every affected teammate, not just one."""
    ws = _make_workspace("s275-9@t")
    a = Teammate.objects.create(workspace=ws, name="A")
    b = Teammate.objects.create(workspace=ws, name="B")
    kd_a = _make_kd(ws, "solo-a", spokespeople=[a])
    kd_b = _make_kd(ws, "solo-b", spokespeople=[b])
    kd_shared = _make_kd(ws, "shared-both", spokespeople=[a, b])

    Teammate.objects.filter(pk__in=[a.pk, b.pk]).delete()

    kd_a.refresh_from_db()
    kd_b.refresh_from_db()
    kd_shared.refresh_from_db()
    assert kd_a.is_active is False
    assert kd_a.deactivated_reason == DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE
    assert kd_a.audience_scope == AudienceScope.NONE  # SESSION 276 Slice 8
    assert kd_b.is_active is False
    assert kd_b.deactivated_reason == DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE
    assert kd_b.audience_scope == AudienceScope.NONE  # SESSION 276 Slice 8
    # kd_shared: last-teammate-standing depends on Django delete
    # order. Regardless of order, after both teammates are gone the
    # M2M is empty and one of the two pre_delete signals must have
    # observed sp_count==1 and archived it.
    assert kd_shared.is_active is False
    assert (
        kd_shared.deactivated_reason
        == DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE
    )
    # SESSION 276 Slice 8: all three orphaned KDs — including the
    # last-teammate-standing shared one — must be stamped NONE.
    assert kd_shared.audience_scope == AudienceScope.NONE


# ---- 10. deactivated_reason distinguishes operator vs orphan ---------


def test_deactivated_reason_distinguishes_operator_delete_from_orphan():
    """Case 10: operator-triggered DELETE via API sets
    reason=OPERATOR_DELETE; teammate-triggered signal sets
    reason=ORPHANED_BY_TEAMMATE_DELETE. Both flip is_active=False,
    but the reason field records intent."""
    from rest_framework.test import APIClient

    ws = _make_workspace("s275-10@t")
    user = User.objects.get(email="s275-10@t")
    client = APIClient()
    client.force_login(user)

    a = Teammate.objects.create(workspace=ws, name="A")

    # KD1: operator soft-delete via API
    kd_op = _make_kd(ws, "will-be-op-deleted", spokespeople=[a])
    pre_op_audience_scope = kd_op.audience_scope
    r = client.delete(f"/api/knowledge/{kd_op.id}/")
    assert r.status_code == 204
    kd_op.refresh_from_db()
    assert kd_op.is_active is False
    assert kd_op.deactivated_reason == DeactivationReason.OPERATOR_DELETE
    # SESSION 276 Slice 8: the operator-delete API path is NOT modified
    # in this slice — it belongs to the Stage 3B mutation-surface pass.
    # audience_scope must be preserved unchanged (NULL under current
    # transitional fixtures; would be preserved to whatever it was
    # after Stage 3B ships). Only orphan-archive stamps NONE.
    assert kd_op.audience_scope == pre_op_audience_scope
    assert kd_op.audience_scope != AudienceScope.NONE

    # KD2: orphan-archived via teammate delete
    kd_orphan = _make_kd(ws, "will-be-orphaned", spokespeople=[a])
    a.delete()
    kd_orphan.refresh_from_db()
    assert kd_orphan.is_active is False
    assert (
        kd_orphan.deactivated_reason
        == DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE
    )
    assert kd_orphan.audience_scope == AudienceScope.NONE  # SESSION 276 Slice 8


# ---- 11. ingestion revival rejects orphan without new spokespeople ---


def test_ingestion_revival_rejects_orphan_without_spokespeople():
    """§29 hazard: an orphan-archived KD has spokespeople=∅. The
    dedup revival path must NOT flip it back to is_active=True
    while leaving the M2M empty — that would recreate the exact
    broadcast-promotion hazard the archive prevents."""
    ws = _make_workspace("s275-11@t")
    a = Teammate.objects.create(workspace=ws, name="A")

    # Ingest, get archived by teammate delete.
    result = ingest_text(
        workspace=ws,
        title="content-x",
        content="body-of-content-x",
        spokespeople=[a],
    )
    kd = result.document
    a.delete()
    kd.refresh_from_db()
    assert kd.is_active is False
    assert kd.deactivated_reason == DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE
    # SESSION 276 Slice 8: archive stamps NONE.
    assert kd.audience_scope == AudienceScope.NONE

    # Attempt to re-ingest identical content with NO new spokespeople.
    with pytest.raises(OrphanRevivalRejected):
        ingest_text(
            workspace=ws,
            title="content-x-retry",
            content="body-of-content-x",
            spokespeople=[],  # empty — the hazard
        )

    kd.refresh_from_db()
    assert kd.is_active is False, "KD must remain archived after rejected revival"
    assert (
        kd.deactivated_reason
        == DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE
    ), "reason must be preserved on rejected revival"
    # SESSION 276 Slice 8: audience_scope must also be preserved on
    # rejected revival — the revival gate short-circuits before any
    # mutation.
    assert kd.audience_scope == AudienceScope.NONE

    # Now revive WITH an explicit new teammate — must succeed and
    # clear the deactivation reason.
    #
    # SESSION 276 Slice 8 known transitional state: this slice does
    # NOT extend the ingestion revival path (Stage 3B territory), so
    # audience_scope remains NONE post-revival even though is_active
    # returns to True. That leaves a CHARACTER-shape row (M2M non-
    # empty) carrying audience_scope=NONE — a Slice 4 §51 row-3
    # malformed shape that will fail closed under retrieval today
    # (safe) and be cleaned up when Stage 3B extends ingestion. This
    # test intentionally does NOT assert audience_scope post-revival
    # so it doesn't lock in transitional behavior.
    c = Teammate.objects.create(workspace=ws, name="C")
    result2 = ingest_text(
        workspace=ws,
        title="content-x-owned",
        content="body-of-content-x",
        spokespeople=[c],
    )
    kd.refresh_from_db()
    assert result2.document.id == kd.id
    assert kd.is_active is True
    assert kd.deactivated_reason == ""
    assert list(kd.spokespeople.values_list("pk", flat=True)) == [c.pk]


# ---- 12. ingestion revival of operator-deleted KD unchanged ---------


def test_ingestion_revival_of_operator_deleted_kd_still_works():
    """The safe-revival gate must ONLY block orphan-archived KDs.
    Operator-deleted KDs (reason=OPERATOR_DELETE) must revive
    exactly as before — with or without new spokespeople.

    Uses ``ingest_text`` for the initial create (not the ``_make_kd``
    helper) so the content_hash matches the SHA-256 the revival
    path recomputes; otherwise dedup misses and a fresh KD is made
    instead of reviving the target row.
    """
    ws = _make_workspace("s275-12@t")
    a = Teammate.objects.create(workspace=ws, name="A")
    original = ingest_text(
        workspace=ws,
        title="operator-content",
        content="body-of-operator-content",
        spokespeople=[a],
    ).document

    # Operator soft-delete (simulate the API destroy path directly on
    # the row — same field writes, avoids APIClient login setup).
    original.is_active = False
    original.deactivated_reason = DeactivationReason.OPERATOR_DELETE
    original.save(update_fields=[
        "is_active", "deactivated_reason", "updated_at",
    ])

    # Re-ingest without new spokespeople — should revive and
    # preserve prior M2M {A}.
    ingest_text(
        workspace=ws,
        title="operator-content",
        content="body-of-operator-content",
        spokespeople=None,
    )
    original.refresh_from_db()
    assert original.is_active is True
    assert original.deactivated_reason == ""
    assert list(original.spokespeople.values_list("pk", flat=True)) == [a.pk]


# ---- 13. atomic rollback if orphan-archive step fails ---------------


def test_teammate_delete_atomic_if_orphan_archive_update_fails(monkeypatch):
    """Case 13 — atomicity contract (added after Chris + ChatGPT
    reviewed Slice 3 and flagged §50 as reasoned-only).

    Force the archive-step DB update inside
    ``_archive_orphaned_kds_on_teammate_delete`` (post_delete) to
    raise a deterministic exception. Assert that the ENTIRE delete
    plan rolls back — teammate row still exists, the through-row
    is not gone, the KD is still active, and no ``deactivated_reason``
    stamp survived. Either all three (teammate delete + through
    cascade + KD archive) commit, or NONE commit.

    Injection method: patch ``QuerySet.update`` at the class level,
    but only raise for updates whose model is ``KnowledgeDocument``.
    Django's Collector uses ``sql.UpdateQuery`` directly for
    SET_NULL cascades (not ``QuerySet.update``), so this patch does
    NOT interfere with the SET_NULL fan-out (Composition / Script /
    Asset etc.). The archive step in ``signals.py`` DOES use
    ``KnowledgeDocument.objects.filter(...).update(...)``, so the
    injection hits exactly the archive write.

    The test wraps ``a.delete()`` in an explicit
    ``transaction.atomic()`` savepoint so the ``django_db`` outer
    transaction can observe the rollback without contaminating
    the fixture state. Inside the savepoint,
    ``Collector.delete()`` wraps its own operations in
    ``mark_for_rollback_on_error`` — the raise propagates, the
    connection is marked for rollback, and the atomic exit rolls
    back the savepoint. Assertions post-with-block see the
    pre-delete state.
    """
    from django.db import transaction
    from django.db.models.query import QuerySet

    from apps.embeddings.models import (
        KnowledgeDocument as KDModel,
        KnowledgeDocumentSpokesperson,
    )

    ws = _make_workspace("s275-13-atomic@t")
    a = Teammate.objects.create(workspace=ws, name="Atomic")
    kd = _make_kd(ws, "atomic-source", spokespeople=[a])
    original_is_active = kd.is_active
    original_reason = kd.deactivated_reason
    original_audience_scope = kd.audience_scope  # SESSION 276 Slice 8
    original_chunk_count = kd.chunks.count()
    assert original_is_active is True
    assert original_reason == ""

    class InjectedArchiveFailure(RuntimeError):
        """Marker so we can uniquely assert we caught OUR raise."""

    original_update = QuerySet.update
    call_hits = {"count": 0}

    def failing_update(self, **kwargs):
        # Only intercept updates on KnowledgeDocument — the exact
        # write the archive step performs. Every other QuerySet
        # update in the delete plan runs unchanged. (SET_NULL
        # cascades don't route through this path — Django uses
        # ``sql.UpdateQuery.update_batch`` directly for those.)
        if self.model is KDModel:
            call_hits["count"] += 1
            raise InjectedArchiveFailure(
                "simulated archive-step DB update failure"
            )
        return original_update(self, **kwargs)

    monkeypatch.setattr(QuerySet, "update", failing_update)

    with pytest.raises(InjectedArchiveFailure):
        with transaction.atomic():
            a.delete()

    # The archive UPDATE must have been attempted (otherwise we
    # haven't proven the invariant we care about).
    assert call_hits["count"] >= 1, (
        "archive .update() must have been attempted"
    )

    # Every piece of state must be exactly as it was before the
    # failed delete: no partial commit anywhere.
    assert Teammate.objects.filter(pk=a.pk).exists(), (
        "Teammate delete must have rolled back"
    )
    assert KDModel.objects.filter(pk=kd.pk).exists(), (
        "KnowledgeDocument must still exist"
    )
    kd.refresh_from_db()
    assert kd.is_active is original_is_active, (
        "is_active must be unchanged (no partial archive commit)"
    )
    assert kd.deactivated_reason == original_reason, (
        "deactivated_reason must be unchanged (no partial archive commit)"
    )
    # SESSION 276 Slice 8 / Q-276-18 — the same failure-injection
    # atomicity contract must hold for the new audience_scope field.
    # If the archive .update() raises, the audience_scope stamp must
    # roll back alongside is_active and deactivated_reason. Because
    # all three fields ship in the same .update() call, this is
    # inherited from the SESSION 275 atomicity guarantee — but it is
    # asserted explicitly here so a future regression that split
    # the writes across separate .update() calls would fail
    # deterministically.
    assert kd.audience_scope == original_audience_scope, (
        "audience_scope must be unchanged (no partial NONE stamp)"
    )
    assert KnowledgeDocumentSpokesperson.objects.filter(
        teammate=a, knowledgedocument=kd,
    ).exists(), "M2M through-row must still exist (cascade rolled back)"
    assert kd.chunks.count() == original_chunk_count, (
        "chunks must be unchanged"
    )
