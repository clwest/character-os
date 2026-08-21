"""Integration tests for the ingestion + embed_document path.

Covers the full slice K3 ships:
* ingest_text persists a KnowledgeDocument and dedups via
  ``(workspace, content_hash)``.
* embed_document chunks + embeds + persists chunks + marks
  the doc processed.
* The cross-workspace cross-attach check in
  ``apps.embeddings.signals`` triggers when ingestion tries
  to set spokespeople from another workspace.
"""
from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.embeddings.ingestion import ingest_text
from apps.embeddings.models import (
    AudienceScope,
    DeactivationReason,
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeDocument,
)
from apps.embeddings.tasks import embed_document
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe
from django.contrib.auth import get_user_model

User = get_user_model()


# ---- fixtures (reused from the privacy test pattern) -----


def _make_workspace(email: str, name: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws


def _make_teammate(ws: Workspace, name: str) -> Teammate:
    return Teammate.objects.create(workspace=ws, name=name)


# ---- ingest_text + dedup ---------------------------------


@pytest.mark.django_db
def test_ingest_text_creates_pending_document() -> None:
    ws = _make_workspace("ingest1@test.local", "Ingest WS 1")
    result = ingest_text(
        workspace=ws,
        title="hello",
        content="Some content here.\n\nSecond paragraph.",
        document_type=DocumentType.TEXT,
        workspace_shared_intent=True,  # SESSION 276 Slice 20 positive audience
    )
    assert result.deduped is False
    assert result.document.status == DocumentStatus.PENDING
    assert result.document.workspace == ws
    assert result.document.ingested_via == IngestedVia.PASTE
    assert result.document.content_hash  # populated


@pytest.mark.django_db
def test_ingest_text_dedups_same_content_in_workspace() -> None:
    ws = _make_workspace("ingest2@test.local", "Ingest WS 2")
    text = "Same exact content.\n\nMore content."

    first = ingest_text(workspace=ws, title="A", content=text, workspace_shared_intent=True)
    second = ingest_text(workspace=ws, title="B", content=text, workspace_shared_intent=True)

    assert first.deduped is False
    assert second.deduped is True
    assert first.document.pk == second.document.pk


@pytest.mark.django_db
def test_ingest_text_dedup_is_per_workspace() -> None:
    ws_a = _make_workspace("ingestA@test.local", "WS A")
    ws_b = _make_workspace("ingestB@test.local", "WS B")
    text = "Shared content across workspaces.\n\nMore."

    doc_a = ingest_text(workspace=ws_a, title="A", content=text, workspace_shared_intent=True)
    doc_b = ingest_text(workspace=ws_b, title="B", content=text, workspace_shared_intent=True)

    assert doc_a.deduped is False
    assert doc_b.deduped is False
    # Same content_hash, different rows
    assert doc_a.document.content_hash == doc_b.document.content_hash
    assert doc_a.document.pk != doc_b.document.pk


@pytest.mark.django_db
def test_ingest_text_empty_content_raises() -> None:
    ws = _make_workspace("empty@test.local", "Empty WS")
    with pytest.raises(ValueError):
        ingest_text(workspace=ws, title="empty", content="   \n  ")


@pytest.mark.django_db
def test_ingest_text_with_spokespeople_m2m_works() -> None:
    ws = _make_workspace("attach@test.local", "Attach WS")
    sp1 = _make_teammate(ws, "Sp1")
    sp2 = _make_teammate(ws, "Sp2")
    result = ingest_text(
        workspace=ws,
        title="visible to sp1",
        content="content",
        spokespeople=[sp1],
    )
    attached = set(result.document.spokespeople.values_list("pk", flat=True))
    assert attached == {sp1.pk}
    assert sp2.pk not in attached


@pytest.mark.django_db
def test_ingest_text_restores_soft_deleted_row() -> None:
    """K4.2 — re-ingesting the same content as a soft-deleted
    row should restore (flip ``is_active=True``, reset to
    PENDING, clear error) and return ``deduped=False`` so the
    caller re-fires ``embed_document``. Otherwise dedup hands
    back a row the operator can't see and never re-embeds."""
    ws = _make_workspace("restore@test.local", "Restore WS")
    text = "Content that will get soft-deleted then restored."

    first = ingest_text(workspace=ws, title="original", content=text, workspace_shared_intent=True)
    assert first.deduped is False

    # Operator soft-deletes (mirrors the viewset's destroy).
    doc = first.document
    doc.is_active = False
    doc.status = DocumentStatus.FAILED
    doc.error_message = "stale failure"
    doc.save()

    # Re-ingest — same content, new title.
    second = ingest_text(workspace=ws, title="restored", content=text, workspace_shared_intent=True)
    assert second.deduped is False, "restored row should re-fire embed"
    assert second.document.pk == first.document.pk, "same row, not a new one"
    assert second.document.is_active is True
    assert second.document.status == DocumentStatus.PENDING
    assert second.document.error_message == ""
    assert second.document.title == "restored", "new title wins"


@pytest.mark.django_db
def test_ingest_text_restore_preserves_title_when_new_is_blank() -> None:
    """K4.2 — when restoring, an empty new title shouldn't
    clobber the operator's original title."""
    ws = _make_workspace("restore-title@test.local", "Restore Title WS")
    text = "Content to test title preservation."

    first = ingest_text(workspace=ws, title="keep me", content=text, workspace_shared_intent=True)
    first.document.is_active = False
    first.document.save(update_fields=["is_active"])

    # URL-ingest path passes title="" when nothing supplied.
    second = ingest_text(workspace=ws, title="", content=text, workspace_shared_intent=True)
    assert second.deduped is False
    assert second.document.title == "keep me"


@pytest.mark.django_db
def test_ingest_text_rejects_cross_workspace_spokesperson_attach() -> None:
    ws_a = _make_workspace("x1@test.local", "X1")
    ws_b = _make_workspace("x2@test.local", "X2")
    foreign_sp = _make_teammate(ws_b, "Foreign")
    with pytest.raises(ValidationError):
        ingest_text(
            workspace=ws_a,
            title="cross-attach",
            content="content",
            spokespeople=[foreign_sp],
        )


# ---- embed_document --------------------------------------


@pytest.mark.django_db
@override_settings(EMBEDDING_FORCE_MOCK=True)
def test_embed_document_processes_to_completion() -> None:
    ws = _make_workspace("embed1@test.local", "Embed WS 1")
    result = ingest_text(
        workspace=ws,
        title="doc",
        content=("Paragraph one with content.\n\n" * 5),
        workspace_shared_intent=True,  # SESSION 276 Slice 20 positive audience
    )
    out = embed_document.apply(args=[str(result.document.pk)]).get()
    assert out["status"] == "processed"
    assert out["chunks_created"] >= 1

    result.document.refresh_from_db()
    assert result.document.status == DocumentStatus.PROCESSED
    assert result.document.chunks.count() == out["chunks_created"]


@pytest.mark.django_db
@override_settings(EMBEDDING_FORCE_MOCK=True)
def test_embed_document_chunks_have_correct_dim() -> None:
    from apps.embeddings.models import EMBEDDING_DIMENSION

    ws = _make_workspace("embed2@test.local", "Embed WS 2")
    result = ingest_text(
        workspace=ws, title="dim doc", content="just one chunk worth of text",
        workspace_shared_intent=True,  # SESSION 276 Slice 20 positive audience
    )
    embed_document.apply(args=[str(result.document.pk)])

    chunk = result.document.chunks.first()
    assert chunk is not None
    # pgvector returns the vector as a numpy array-like; just
    # confirm the dimension matches the model.
    assert len(list(chunk.embedding_vector)) == EMBEDDING_DIMENSION


@pytest.mark.django_db
@override_settings(EMBEDDING_FORCE_MOCK=True)
def test_embed_document_is_idempotent() -> None:
    """Re-running ``embed_document`` against an already-processed
    document wipes existing chunks and re-creates them. Used
    when re-embedding after content edits or model swaps."""
    ws = _make_workspace("idem@test.local", "Idem WS")
    result = ingest_text(
        workspace=ws, title="idem", content="some content to chunk",
        workspace_shared_intent=True,  # SESSION 276 Slice 20 positive audience
    )
    embed_document.apply(args=[str(result.document.pk)])
    first_count = result.document.chunks.count()

    # Run again — should wipe + re-create.
    embed_document.apply(args=[str(result.document.pk)])
    result.document.refresh_from_db()
    second_count = result.document.chunks.count()
    assert first_count == second_count


@pytest.mark.django_db
def test_embed_document_handles_missing_doc() -> None:
    """An ID that doesn't exist returns a not_found result
    rather than raising — Celery tasks should be defensive."""
    import uuid

    out = embed_document.apply(args=[str(uuid.uuid4())]).get()
    assert out["status"] == "not_found"
    assert out["chunks_created"] == 0


# =====================================================================
# SESSION 276 Slice 10 / Delta Stage 3B-2 (Q-276-24) — fresh CREATE
# with explicit spokespeople stamps ``audience_scope=CHARACTER`` at
# creation time. No transitional NULL bridge state for character-
# specific KDs. See docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md
# §146-§163.
#
# Scope guard: this slice handles ONLY the "explicit spokespeople →
# CHARACTER" case. Fresh no-spokespeople creation (UNIVERSE / WORKSPACE
# inference) is deferred to Q-276-25.
# =====================================================================


@pytest.mark.django_db
def test_fresh_create_with_single_spokesperson_stamps_character() -> None:
    """Slice 10 Test A — single explicit spokesperson at create time
    lands the new KD at ``audience_scope=CHARACTER`` directly."""
    ws = _make_workspace(
        "slice10-a@test.local", "Slice10 WS A",
    )
    a = _make_teammate(ws, "Alpha")

    result = ingest_text(
        workspace=ws,
        title="single-sp-create",
        content="Content owned by Alpha only.",
        spokespeople=[a],
    )

    kd = result.document
    kd.refresh_from_db()
    assert result.deduped is False
    assert kd.is_active is True
    assert kd.deactivated_reason == ""
    assert kd.audience_scope == AudienceScope.CHARACTER
    assert list(kd.spokespeople.values_list("pk", flat=True)) == [a.pk]
    # Adversarial invariant: fresh CHARACTER row must have M2M ≥ 1.
    assert kd.spokespeople.count() >= 1
    assert not (
        kd.is_active is True
        and kd.audience_scope == AudienceScope.CHARACTER
        and kd.spokespeople.count() == 0
    ), "fresh CHARACTER create must not produce empty-M2M active row"


@pytest.mark.django_db
def test_fresh_create_with_multiple_spokespeople_stamps_character() -> None:
    """Slice 10 Test B — multi-character fresh create still maps to
    CHARACTER. Multi-character is a shape variant of CHARACTER, not a
    distinct audience type (Slice 4 §48)."""
    ws = _make_workspace(
        "slice10-b@test.local", "Slice10 WS B",
    )
    a = _make_teammate(ws, "A")
    b = _make_teammate(ws, "B")

    result = ingest_text(
        workspace=ws,
        title="multi-sp-create",
        content="Content shared by A and B from creation.",
        spokespeople=[a, b],
    )

    kd = result.document
    kd.refresh_from_db()
    assert kd.audience_scope == AudienceScope.CHARACTER
    m2m = set(kd.spokespeople.values_list("pk", flat=True))
    assert m2m == {a.pk, b.pk}


@pytest.mark.django_db
def test_fresh_create_universe_scoped_character_still_maps_to_character() -> None:
    """Slice 10 Test C — a character-specific KD inside a Universe
    (``universe=U`` + ``spokespeople=[A in U]``) is still CHARACTER
    scope; the Universe is scope context, not audience type. Verifies
    Slice 4 §51 row #2 shape produced at create time.
    """
    ws = _make_workspace(
        "slice10-c@test.local", "Slice10 WS C",
    )
    u = Universe.objects.create(workspace=ws, name="Slice10 Universe")
    a = Teammate.objects.create(workspace=ws, name="A", universe=u)

    result = ingest_text(
        workspace=ws,
        title="universe-char-create",
        content="Character-specific content inside Universe U.",
        spokespeople=[a],
        universe=u,
    )

    kd = result.document
    kd.refresh_from_db()
    assert kd.universe_id == u.pk
    assert kd.audience_scope == AudienceScope.CHARACTER
    assert list(kd.spokespeople.values_list("pk", flat=True)) == [a.pk]


@pytest.mark.django_db
def test_fresh_create_without_spokespeople_or_universe_leaves_audience_scope_null() -> None:
    """Slice 10 Test D (SUPERSEDED by Slice 20 Q-276-36) — fresh create
    with NO spokespeople AND no Universe AND no workspace_shared_intent
    marker must now FAIL CLOSED. Previously (Slice 11/12) the row was
    permitted to land at ``audience_scope=NULL`` as a transitional
    state. Slice 20 (§345/§346) closes that loophole at the deeper
    ingestion boundary — the ``_persist`` else branch raises
    ``ValidationError`` instead of persisting a NULL row.

    The API-level guard (serializer 4xx) is verified separately in
    ``test_slice20_serializer_rejects_create_without_audience_signal``.
    """
    ws = _make_workspace(
        "slice10-d@test.local", "Slice10 WS D",
    )

    with pytest.raises(ValidationError) as exc_info:
        ingest_text(
            workspace=ws,
            title="no-sp-no-universe-create",
            content="Content with no explicit spokespeople + no Universe.",
            # spokespeople NOT supplied; universe NOT supplied
        )
    assert "audience_scope" in str(exc_info.value)
    assert (
        KnowledgeDocument.objects.filter(
            workspace=ws, title="no-sp-no-universe-create",
        ).exists()
        is False
    ), "no KD row must persist when ingestion fails closed"



@pytest.mark.django_db
def test_fresh_create_no_spokespeople_with_explicit_universe_stamps_universe() -> None:
    """Slice 11 Test F — fresh create with NO spokespeople but WITH
    an explicit Universe stamps ``audience_scope=UNIVERSE`` at
    creation time. This is the Q-276-25 answer A: explicit Universe
    supplied at ``_persist`` is positive operator intent for
    UNIVERSE-shared canon.

    Evidence: every SPA create surface uses UniverseScopePicker which
    forces an explicit pick; scripts creating UNIVERSE canon rows
    (session272_slice_b_setup.py, session273_slice_alpha_ingest_kd.py)
    document the audience intent explicitly. See
    docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md §164-§180.
    """
    ws = _make_workspace(
        "slice11-f@test.local", "Slice11 WS F",
    )
    u = Universe.objects.create(workspace=ws, name="Slice11 Universe F")

    result = ingest_text(
        workspace=ws,
        title="universe-canon-create",
        content="Content shared across all teammates in Universe F.",
        # NO spokespeople supplied — explicit UNIVERSE-shared intent.
        universe=u,
    )

    kd = result.document
    kd.refresh_from_db()
    assert kd.is_active is True
    assert kd.deactivated_reason == ""
    assert kd.audience_scope == AudienceScope.UNIVERSE
    assert kd.universe_id == u.pk
    assert kd.spokespeople.count() == 0
    # Adversarial invariant — UNIVERSE requires universe non-null (Slice 4 §52 #2).
    assert not (
        kd.audience_scope == AudienceScope.UNIVERSE
        and kd.universe_id is None
    ), "fresh UNIVERSE create must never produce universe=NULL malformed shape"


@pytest.mark.django_db
def test_fresh_create_universe_inference_asymmetric_with_workspace() -> None:
    """Slice 11 Test G — deliberate asymmetry guard. Verifies that
    Slice 11 implemented ONLY the UNIVERSE inference branch, NOT the
    WORKSPACE inference branch.

    * (no sp, universe=U)  → UNIVERSE  (Slice 11 stamps)
    * (no sp, universe=None) → NULL   (still transitional)

    Guards against a future slice accidentally coupling the two
    inference branches. WORKSPACE inference requires an explicit
    intent-payload contract per Q-276-25 answer B.
    """
    ws = _make_workspace(
        "slice11-g@test.local", "Slice11 WS G",
    )
    u = Universe.objects.create(workspace=ws, name="Slice11 Universe G")

    # (no sp, universe=U) branch → UNIVERSE
    result_universe = ingest_text(
        workspace=ws,
        title="asym-universe",
        content="Universe-scoped content G.",
        universe=u,
    )
    kd_universe = result_universe.document
    kd_universe.refresh_from_db()
    assert kd_universe.audience_scope == AudienceScope.UNIVERSE
    assert kd_universe.universe_id == u.pk

    # (no sp, no universe) branch — SUPERSEDED by Slice 20 Q-276-36
    # fresh-write NULL closure. Previously landed at NULL; now the
    # ingestion path raises ValidationError instead.
    with pytest.raises(ValidationError):
        ingest_text(
            workspace=ws,
            title="asym-null",
            content="No-scope content G.",
            # neither spokespeople nor universe supplied
        )


@pytest.mark.django_db
def test_fresh_create_rolls_back_atomically_if_m2m_set_fails() -> None:
    """Slice 10 Test E — atomicity. If M2M ``.set()`` fails during a
    fresh CHARACTER create (e.g. cross-workspace signal veto), the
    whole ``KnowledgeDocument.objects.create()`` must roll back so no
    active-CHARACTER row with empty M2M can persist.

    Exercises the pre-existing ``transaction.atomic()`` block at
    ``ingestion.py:220-244`` — Slice 10 relies on that boundary for
    the same atomicity guarantee Slice 9 added to the revival branch.
    """
    ws_a = _make_workspace(
        "slice10-e-a@test.local", "Slice10 WS E A",
    )
    ws_b = _make_workspace(
        "slice10-e-b@test.local", "Slice10 WS E B",
    )
    # Foreign spokesperson — different workspace triggers the
    # existing cross-workspace m2m_changed guard at
    # apps/embeddings/signals.py:31.
    foreign = _make_teammate(ws_b, "ForeignSP")

    pre_count = KnowledgeDocument.objects.filter(workspace=ws_a).count()
    with pytest.raises(ValidationError):
        ingest_text(
            workspace=ws_a,
            title="atomic-cross-workspace",
            content="Content that must not persist without its M2M.",
            spokespeople=[foreign],
        )

    # Assert the KD was NOT created — atomic block rolled back the
    # KnowledgeDocument.objects.create() when the M2M .set() raised.
    post_count = KnowledgeDocument.objects.filter(workspace=ws_a).count()
    assert post_count == pre_count, (
        "M2M failure must roll back the KD create (atomic block)"
    )
    # And of course no orphan active-CHARACTER + empty-M2M row exists.
    assert not KnowledgeDocument.objects.filter(
        workspace=ws_a,
        title="atomic-cross-workspace",
    ).exists()


# =====================================================================
# SESSION 276 Slice 12 / Delta Stage 3B-4 (Q-276-26) — explicit
# WORKSPACE fresh-create marker. See §186-§204 of the audit doc.
# =====================================================================


@pytest.mark.django_db
def test_slice12_A_explicit_workspace_marker_stamps_workspace() -> None:
    """Slice 12 Test A — the SPA "None (legacy)" gesture reaches
    ``_persist`` via ``workspace_shared_intent=True`` and stamps
    ``audience_scope=WORKSPACE``. This is the primary Q-276-26
    assertion."""
    ws = _make_workspace(
        "slice12-a@test.local", "Slice12 WS A",
    )
    result = ingest_text(
        workspace=ws,
        title="explicit-workspace",
        content="Content marked explicitly as workspace-shared.",
        # NO spokespeople, NO universe, WITH the positive marker.
        workspace_shared_intent=True,
    )
    kd = result.document
    kd.refresh_from_db()
    assert kd.is_active is True
    assert kd.deactivated_reason == ""
    assert kd.audience_scope == AudienceScope.WORKSPACE
    assert kd.universe_id is None
    assert kd.spokespeople.count() == 0
    # Adversarial: WORKSPACE requires universe=NULL (Slice 4 §52 #3).
    assert not (
        kd.audience_scope == AudienceScope.WORKSPACE
        and kd.universe_id is not None
    ), "WORKSPACE row must not have a Universe FK"


@pytest.mark.django_db
def test_slice12_B_omission_remains_null() -> None:
    """Slice 12 Test B (SUPERSEDED by Slice 20 Q-276-36) — a non-SPA
    caller that omits spokespeople AND universe AND the marker now
    fails closed instead of landing at NULL. Slice 12 preserved the
    NULL branch as a transitional state so absence-means-broadcast
    regressions could be tested; Slice 20 closes that branch at the
    ingestion boundary and the API surface (§345/§346)."""
    ws = _make_workspace(
        "slice12-b@test.local", "Slice12 WS B",
    )
    with pytest.raises(ValidationError):
        ingest_text(
            workspace=ws,
            title="omitted-everything",
            content="Non-SPA caller-style content without marker.",
            # No spokespeople, no universe, no workspace_shared_intent.
        )
    # No KD row should persist when ingestion fails closed.
    assert (
        KnowledgeDocument.objects.filter(
            workspace=ws, title="omitted-everything",
        ).exists()
        is False
    )


@pytest.mark.django_db
def test_slice12_C_universe_pick_still_stamps_universe() -> None:
    """Slice 12 Test C — Universe fresh-create unaffected by the
    workspace marker addition. When the marker is absent but a
    Universe is supplied, precedence produces UNIVERSE."""
    ws = _make_workspace(
        "slice12-c@test.local", "Slice12 WS C",
    )
    u = Universe.objects.create(workspace=ws, name="Slice12 Universe C")
    result = ingest_text(
        workspace=ws,
        title="universe-pick",
        content="Universe-scoped canon content.",
        universe=u,
        # workspace_shared_intent NOT supplied — precedence yields UNIVERSE
    )
    kd = result.document
    kd.refresh_from_db()
    assert kd.audience_scope == AudienceScope.UNIVERSE
    assert kd.universe_id == u.pk


@pytest.mark.django_db
def test_slice12_D_character_creation_unaffected() -> None:
    """Slice 12 Test D — CHARACTER fresh-create unaffected. Explicit
    spokespeople still stamp CHARACTER regardless of the marker."""
    ws = _make_workspace(
        "slice12-d@test.local", "Slice12 WS D",
    )
    a = _make_teammate(ws, "Alpha")
    result = ingest_text(
        workspace=ws,
        title="character-pick",
        content="Character-scoped content.",
        spokespeople=[a],
    )
    kd = result.document
    kd.refresh_from_db()
    assert kd.audience_scope == AudienceScope.CHARACTER
    assert list(kd.spokespeople.values_list("pk", flat=True)) == [a.pk]


@pytest.mark.django_db
def test_slice12_E_precedence_when_marker_conflicts_with_spokespeople() -> None:
    """Slice 12 Test E1 — direct ``_persist``-level defensive
    precedence check. When both spokespeople and the marker reach
    ``_persist`` (bypassing the serializer contradiction guard),
    CHARACTER precedence wins. Logs a warning; does NOT silently
    broaden to WORKSPACE.

    Rationale: the serializer's ``validate()`` normally rejects
    this combination with HTTP 400. But if a non-DRF caller ever
    bypasses the serializer, ``_persist`` must not silently produce
    a wrong-audience row.
    """
    ws = _make_workspace(
        "slice12-e1@test.local", "Slice12 WS E1",
    )
    a = _make_teammate(ws, "Alpha")
    result = ingest_text(
        workspace=ws,
        title="conflicting-payload-character",
        content="Content with both spokespeople and workspace marker.",
        spokespeople=[a],
        workspace_shared_intent=True,  # contradiction — CHARACTER wins
    )
    kd = result.document
    kd.refresh_from_db()
    assert kd.audience_scope == AudienceScope.CHARACTER
    assert list(kd.spokespeople.values_list("pk", flat=True)) == [a.pk]


@pytest.mark.django_db
def test_slice12_E_precedence_when_marker_conflicts_with_universe() -> None:
    """Slice 12 Test E2 — defensive precedence when Universe + marker
    both reach ``_persist``. UNIVERSE precedence wins; marker ignored."""
    ws = _make_workspace(
        "slice12-e2@test.local", "Slice12 WS E2",
    )
    u = Universe.objects.create(workspace=ws, name="Slice12 Universe E2")
    result = ingest_text(
        workspace=ws,
        title="conflicting-payload-universe",
        content="Content with Universe and workspace marker.",
        universe=u,
        workspace_shared_intent=True,  # contradiction — UNIVERSE wins
    )
    kd = result.document
    kd.refresh_from_db()
    assert kd.audience_scope == AudienceScope.UNIVERSE
    assert kd.universe_id == u.pk


@pytest.mark.django_db
def test_slice12_F_pdf_ingestion_threads_marker() -> None:
    """Slice 12 Test F1 — ``ingest_pdf`` also carries the marker.

    Uses a minimal valid PDF payload so ``pdf.extract_text`` yields
    non-empty text without provider spend. Only asserts the audience-
    scope propagation; other PDF-ingestion behavior is covered by
    existing tests."""
    from apps.embeddings import pdf as pdf_module
    import unittest.mock

    ws = _make_workspace(
        "slice12-f-pdf@test.local", "Slice12 WS F PDF",
    )

    class _FakeExtract:
        text = "Fake PDF text content for Slice 12 F."
        page_count = 1

    with unittest.mock.patch.object(
        pdf_module, "extract_text", return_value=_FakeExtract(),
    ):
        from apps.embeddings.ingestion import ingest_pdf

        result = ingest_pdf(
            workspace=ws,
            title="slice12-pdf",
            payload=b"%PDF-1.4 fake",
            workspace_shared_intent=True,
        )

    kd = result.document
    kd.refresh_from_db()
    assert kd.audience_scope == AudienceScope.WORKSPACE
    assert kd.document_type == "pdf"


@pytest.mark.django_db
def test_slice12_F_url_ingestion_threads_marker() -> None:
    """Slice 12 Test F2 — ``ingest_url`` also carries the marker."""
    from apps.embeddings import url_fetch as url_fetch_module
    import unittest.mock

    ws = _make_workspace(
        "slice12-f-url@test.local", "Slice12 WS F URL",
    )

    class _FakeUrlExtract:
        text = "Fake URL-extracted content for Slice 12 F."
        title = "Fake page title"
        metadata: dict = {}

    with unittest.mock.patch.object(
        url_fetch_module, "fetch_url", return_value=_FakeUrlExtract(),
    ):
        from apps.embeddings.ingestion import ingest_url

        result = ingest_url(
            workspace=ws,
            url="https://example.test/slice12",
            title="slice12-url",
            workspace_shared_intent=True,
        )

    kd = result.document
    kd.refresh_from_db()
    assert kd.audience_scope == AudienceScope.WORKSPACE
    assert kd.document_type == "url"


@pytest.mark.django_db
def test_slice12_G_workspace_marker_cannot_bypass_orphan_revival_gate() -> None:
    """Slice 12 Test G — the workspace marker must NOT provide an
    alternate route to revive an orphan-archived KD. The SESSION 275
    ``OrphanRevivalRejected`` gate still requires explicit non-empty
    spokespeople for an orphan revival, regardless of any marker
    supplied on the payload.

    This is a load-bearing invariant: without this guard, an operator
    could revive a former-character orphan by simply picking "None
    (legacy)" — which would formalize a broadcast-broadening recovery
    path the SESSION 275/276 arc explicitly forbids.
    """
    from apps.embeddings.ingestion import OrphanRevivalRejected

    ws = _make_workspace(
        "slice12-g@test.local", "Slice12 WS G",
    )
    a = _make_teammate(ws, "Alpha")
    # 1. Create a KD attached to A.
    original = ingest_text(
        workspace=ws,
        title="slice12-g-content",
        content="Content that will become an orphan.",
        spokespeople=[a],
    ).document
    # 2. Delete A — orphan-archive stamps NONE.
    a.delete()
    original.refresh_from_db()
    assert original.audience_scope == AudienceScope.NONE
    assert original.is_active is False

    # 3. Attempt to revive by re-ingesting the same content with the
    #    workspace marker but NO spokespeople. Must be rejected.
    with pytest.raises(OrphanRevivalRejected):
        ingest_text(
            workspace=ws,
            title="slice12-g-content-retry",
            content="Content that will become an orphan.",
            workspace_shared_intent=True,  # cannot bypass gate
        )

    # 4. State must be preserved.
    original.refresh_from_db()
    assert original.is_active is False
    assert original.audience_scope == AudienceScope.NONE
    assert original.deactivated_reason == DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE
