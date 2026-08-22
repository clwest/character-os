"""SESSION 277 Slice 8 (Q-277-8) — Universe.brief contract + wiring.

Load-bearing behaviors:

- ``Universe.brief`` accepts blank (default) and up to 2000 chars.
- Serializer round-trips brief on GET / POST / PATCH.
- Slice-5 name-only POST still works (brief remains optional).
- ``Universe.brief`` does NOT auto-create a KnowledgeDocument.
- ``Universe.brief`` does NOT mutate any Teammate.business_brief.
- Teammate CRUD does NOT mutate Universe.brief.
- Synthesis wiring:
  - ``script_synthesis._build_factual_basis_section`` emits ``WORLD SHAPE:``
    when Universe.brief is populated.
  - Same section OMITS ``WORLD SHAPE:`` cleanly when brief is blank.
  - Same section OMITS cleanly when spokesperson has ``universe=NULL``.
  - ``dialogue_synthesis._build_factual_basis_section`` emits exactly ONE
    ``WORLD SHAPE`` block for a same-Universe cast (never once-per-character).
  - Cross-Universe cast defensively suppresses ``WORLD SHAPE``.
  - ``claim_verifier.build_factual_corpus`` includes Universe.brief as
    evidence.

Not tested here: real provider synthesis or retrieval (no provider spend).
Prompt composition is inspected at the section-builder boundary.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe
from apps.embeddings.models import KnowledgeDocument
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="s277-slice8@test.local", password="x")


@pytest.fixture
def workspace(user):
    ws = Workspace.objects.filter(owner=user).first() or Workspace.objects.create(
        name="S277 Slice8 WS", owner=user
    )
    Membership.objects.get_or_create(
        user=user, workspace=ws, defaults={"role": Membership.Role.OWNER}
    )
    return ws


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ---- field contract ----------------------------------------------------


def test_universe_defaults_brief_to_empty_string(client, workspace):
    """Slice-5 minimum POST (workspace+name only) remains valid; brief
    defaults to empty string."""
    resp = client.post(
        "/api/universes/",
        data={"workspace": str(workspace.id), "name": "Bakery A"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["brief"] == ""
    u = Universe.objects.get(id=body["id"])
    assert u.brief == ""


def test_universe_create_accepts_brief(client, workspace):
    resp = client.post(
        "/api/universes/",
        data={
            "workspace": str(workspace.id),
            "name": "Bakery B",
            "brief": "A neighborhood artisan bakery.",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["brief"] == "A neighborhood artisan bakery."
    u = Universe.objects.get(id=body["id"])
    assert u.brief == "A neighborhood artisan bakery."


def test_universe_patch_updates_brief(client, workspace):
    u = Universe.objects.create(workspace=workspace, name="Bakery C")
    resp = client.patch(
        f"/api/universes/{u.id}/",
        data={"brief": "Now with brief"},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    u.refresh_from_db()
    assert u.brief == "Now with brief"


def test_universe_get_returns_brief(client, workspace):
    u = Universe.objects.create(
        workspace=workspace, name="Bakery D", brief="Compact identity."
    )
    resp = client.get(f"/api/universes/{u.id}/")
    assert resp.status_code == 200, resp.content
    assert resp.json()["brief"] == "Compact identity."


def test_universe_list_returns_brief(client, workspace):
    Universe.objects.create(
        workspace=workspace, name="Bakery E", brief="Enduring context."
    )
    resp = client.get(f"/api/universes/?workspace={workspace.id}")
    assert resp.status_code == 200, resp.content
    rows = resp.json()
    if isinstance(rows, dict):
        rows = rows.get("results", [])
    briefs = [r["brief"] for r in rows]
    assert "Enduring context." in briefs


def test_universe_brief_rejects_overlength_at_model_layer(workspace):
    """Model enforces max_length=2000. Django TextField's max_length is
    enforced by full_clean(), not by save() — but the DRF serializer
    surfaces it as a 400 automatically since TextField uses CharField
    validation in DRF. Belt-and-braces guard: full_clean rejects."""
    from django.core.exceptions import ValidationError as DjangoValidationError

    u = Universe(
        workspace=workspace, name="Bakery Length", brief="x" * 2001,
    )
    with pytest.raises(DjangoValidationError):
        u.full_clean()


# ---- non-interference invariants ---------------------------------------


def test_universe_brief_does_not_create_knowledge_document(client, workspace):
    """Populating Universe.brief must NOT create any KnowledgeDocument
    row — brief is deterministically injected, not chunked/embedded."""
    kd_before = KnowledgeDocument.objects.count()
    resp = client.post(
        "/api/universes/",
        data={
            "workspace": str(workspace.id),
            "name": "Bakery Iso",
            "brief": "Should not become a KD.",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert KnowledgeDocument.objects.count() == kd_before


def test_universe_brief_does_not_mutate_teammate_business_brief(
    client, workspace
):
    """PATCH-ing Universe.brief must NOT touch any Teammate.business_brief.
    Ownership stays where it is (Slice 5 §T no decomposition)."""
    u = Universe.objects.create(workspace=workspace, name="Bakery Team")
    tm = Teammate.objects.create(
        workspace=workspace,
        universe=u,
        name="Alice",
        business_brief="Alice-owned character context.",
    )
    resp = client.patch(
        f"/api/universes/{u.id}/",
        data={"brief": "World-level shared identity"},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    tm.refresh_from_db()
    assert tm.business_brief == "Alice-owned character context."


def test_teammate_create_does_not_touch_universe_brief(client, workspace):
    """Creating a new character inside a World must NOT mutate the
    World's brief."""
    u = Universe.objects.create(
        workspace=workspace, name="Bakery Preserve", brief="Fixed.",
    )
    resp = client.post(
        "/api/spokespeople/",
        data={
            "workspace": str(workspace.id),
            "universe": str(u.id),
            "name": "Bob",
            "business_brief": "Bob character brief.",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    u.refresh_from_db()
    assert u.brief == "Fixed."


def test_teammate_update_does_not_touch_universe_brief(client, workspace):
    u = Universe.objects.create(
        workspace=workspace, name="Bakery Preserve 2", brief="Fixed.",
    )
    tm = Teammate.objects.create(
        workspace=workspace, universe=u, name="Cara",
        business_brief="Cara.",
    )
    resp = client.patch(
        f"/api/spokespeople/{tm.id}/",
        data={"business_brief": "Updated character brief"},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    u.refresh_from_db()
    assert u.brief == "Fixed."


# ---- synthesis wiring: script_synthesis --------------------------------


def test_script_synthesis_emits_world_shape_when_brief_present(workspace):
    """When spokesperson.universe.brief is populated, single-character
    K6 §1 FACTUAL BASIS emits a ``WORLD SHAPE:`` block."""
    from character_os.script_synthesis import _build_factual_basis_section

    u = Universe.objects.create(
        workspace=workspace, name="ScriptFB", brief="Enduring World context.",
    )
    sp = Teammate.objects.create(
        workspace=workspace, universe=u, name="Ryder",
        business_brief="Ryder is a character.",
    )
    section = _build_factual_basis_section(sp, chunks=[])
    assert "WORLD SHAPE:\nEnduring World context." in section
    # BUSINESS SHAPE still present (character brief unchanged).
    assert "BUSINESS SHAPE:\nRyder is a character." in section


def test_script_synthesis_omits_world_shape_when_brief_blank(workspace):
    from character_os.script_synthesis import _build_factual_basis_section

    u = Universe.objects.create(
        workspace=workspace, name="ScriptFB2", brief="",
    )
    sp = Teammate.objects.create(
        workspace=workspace, universe=u, name="Sasha",
        business_brief="Sasha.",
    )
    section = _build_factual_basis_section(sp, chunks=[])
    assert "WORLD SHAPE:" not in section
    assert "BUSINESS SHAPE:\nSasha." in section


def test_script_synthesis_omits_world_shape_for_null_universe(workspace):
    """Legacy universe=NULL teammates: no WORLD SHAPE block, no crash."""
    from character_os.script_synthesis import _build_factual_basis_section

    sp = Teammate.objects.create(
        workspace=workspace, name="Legacy",
        business_brief="Legacy character.",
    )
    section = _build_factual_basis_section(sp, chunks=[])
    assert "WORLD SHAPE:" not in section
    assert "BUSINESS SHAPE:\nLegacy character." in section


# ---- synthesis wiring: dialogue_synthesis ------------------------------


def test_dialogue_synthesis_emits_world_shape_once_for_shared_cast(
    workspace,
):
    """Two characters in the same Universe: WORLD SHAPE block appears
    EXACTLY ONCE, not once per character."""
    from character_os.dialogue_synthesis import _build_factual_basis_section

    u = Universe.objects.create(
        workspace=workspace, name="DialogueFB",
        brief="Shared World identity for cast.",
    )
    a = Teammate.objects.create(
        workspace=workspace, universe=u, name="A",
        business_brief="A brief.",
    )
    b = Teammate.objects.create(
        workspace=workspace, universe=u, name="B",
        business_brief="B brief.",
    )
    section = _build_factual_basis_section(
        [("primary", a, []), ("secondary", b, [])],
        use_knowledge=True,
    )
    assert section.count("WORLD SHAPE") == 1
    assert "Shared World identity for cast." in section
    # Per-character BUSINESS SHAPE blocks still present, distinct.
    assert "BUSINESS SHAPE:\nA brief." in section
    assert "BUSINESS SHAPE:\nB brief." in section


def test_dialogue_synthesis_omits_world_shape_for_blank_brief(workspace):
    from character_os.dialogue_synthesis import _build_factual_basis_section

    u = Universe.objects.create(
        workspace=workspace, name="DialogueFB2", brief="",
    )
    a = Teammate.objects.create(
        workspace=workspace, universe=u, name="C", business_brief="C.",
    )
    b = Teammate.objects.create(
        workspace=workspace, universe=u, name="D", business_brief="D.",
    )
    section = _build_factual_basis_section(
        [("primary", a, []), ("secondary", b, [])],
        use_knowledge=True,
    )
    assert "WORLD SHAPE" not in section


def test_dialogue_synthesis_suppresses_world_shape_for_mixed_universe(
    workspace,
):
    """Defensive: mixed-Universe cast must not pick one World's brief
    arbitrarily. Suppress WORLD SHAPE entirely — the canon lane's
    cast-Universe check already returns empty in this case."""
    from character_os.dialogue_synthesis import _build_factual_basis_section

    u1 = Universe.objects.create(
        workspace=workspace, name="MixedU1", brief="World 1 brief.",
    )
    u2 = Universe.objects.create(
        workspace=workspace, name="MixedU2", brief="World 2 brief.",
    )
    a = Teammate.objects.create(
        workspace=workspace, universe=u1, name="MixedA",
        business_brief=".",
    )
    b = Teammate.objects.create(
        workspace=workspace, universe=u2, name="MixedB",
        business_brief=".",
    )
    section = _build_factual_basis_section(
        [("primary", a, []), ("secondary", b, [])],
        use_knowledge=True,
    )
    assert "WORLD SHAPE" not in section


# ---- claim_verifier evidence corpus ------------------------------------


def test_claim_verifier_includes_universe_brief_as_evidence(workspace):
    from character_os.claim_verifier import build_factual_corpus

    u = Universe.objects.create(
        workspace=workspace, name="ClaimFB",
        brief="Fox & Flour is an artisan neighborhood bakery.",
    )
    sp = Teammate.objects.create(
        workspace=workspace, universe=u, name="ClaimTM",
        business_brief="Character-owned brief.",
    )
    corpus = build_factual_corpus([], spokesperson=sp)
    assert "Fox & Flour is an artisan neighborhood bakery." in corpus
    assert "Character-owned brief." in corpus


def test_claim_verifier_omits_universe_brief_when_blank(workspace):
    from character_os.claim_verifier import build_factual_corpus

    u = Universe.objects.create(workspace=workspace, name="ClaimFB2", brief="")
    sp = Teammate.objects.create(
        workspace=workspace, universe=u, name="ClaimTM2",
        business_brief="Only character brief.",
    )
    corpus = build_factual_corpus([], spokesperson=sp)
    # No literal empty-brief noise; only character-owned content.
    assert corpus.strip() == "Only character brief."


def test_claim_verifier_no_universe_no_world_brief(workspace):
    """Legacy universe=NULL teammate: no crash, corpus is just the
    character-owned fields."""
    from character_os.claim_verifier import build_factual_corpus

    sp = Teammate.objects.create(
        workspace=workspace, name="LegacyClaim",
        business_brief="Legacy fact.",
    )
    corpus = build_factual_corpus([], spokesperson=sp)
    assert corpus.strip() == "Legacy fact."
