"""NarrativeMemory Slice 1 — model + endpoint tests.

SESSION 264 Slice 1. Covers:

  * Model invariants — Universe / Workspace consistency,
    supersede-in-same-Episode, blank body rejection.
  * Signal invariants — witnessed_by pre_add rejects
    cross-Universe / cross-Workspace / not-in-cast Teammates.
  * RESTRICT on Composition / Episode delete when memories
    attached (blocks direct hard-delete but permits Workspace
    cascade — same shape as Composition.episode).
  * Promote-from-composition endpoint — 201 with created rows,
    400 on invalid witness, 400 on wrong Episode.
  * Archive / unarchive lifecycle.
  * Supersede chain — later row promotes older to SUPERSEDED.

No provider calls; no synthesis. Only DB + view-layer proofs.
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import RestrictedError
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace
from apps.compositions.models import Composition
from apps.memory.models import (
    NarrativeMemory,
    NarrativeMemoryKind,
    NarrativeMemoryStatus,
)
from apps.spokespeople.models import Teammate
from apps.universe.models import Episode, Universe

User = get_user_model()

pytestmark = pytest.mark.django_db


def _unwrap(resp) -> list:
    """Normalize list-endpoint responses: DRF paginated ({results: [...]})
    or bare list."""
    body = resp.json()
    if isinstance(body, dict) and "results" in body:
        return body["results"]
    return body


# ============================================================
# Fixtures
# ============================================================


def _mkworkspace(email: str, name: str) -> tuple[User, Workspace]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    if ws is None:
        ws = Workspace.objects.create(name=name, owner=user)
    Membership.objects.get_or_create(
        user=user, workspace=ws,
        defaults={"role": Membership.Role.OWNER},
    )
    return user, ws


@pytest.fixture
def scene():
    """Patch/Rivet fixture with an Episode + one accepted Composition.
    Zero provider calls."""
    owner, ws = _mkworkspace("owner@nm.test", "NM-WS")
    universe = Universe.objects.create(workspace=ws, name="workshop")
    patch = Teammate.objects.create(
        workspace=ws, universe=universe, name="Patch",
        runway_avatar_id="av-patch",
        portrait_path="https://fake/patch.png",
        business_brief="Workshop inventor.",
    )
    rivet = Teammate.objects.create(
        workspace=ws, universe=universe, name="Rivet",
        runway_avatar_id="av-rivet",
        portrait_path="https://fake/rivet.png",
        business_brief="Counterweight.",
    )
    episode = Episode.objects.create(
        universe=universe,
        title="AI took over the lab",
        operator_topic="The printer decided to make Patch royalty.",
    )
    episode.cast.add(patch)
    episode.cast.add(rivet)
    # Minimal Composition — we don't need a real synthesis pipeline
    # for Slice 1 tests; just a workspace+episode-anchored row.
    comp = Composition.objects.create(
        workspace=ws,
        spokesperson=patch,
        name="AI-lab v1",
        template_kind="dialogue_scene",
        mock_mode=True,
        created_by=owner,
        operator_topic=episode.operator_topic,
        episode=episode,
    )
    return {
        "owner": owner,
        "workspace": ws,
        "universe": universe,
        "patch": patch,
        "rivet": rivet,
        "episode": episode,
        "composition": comp,
    }


@pytest.fixture
def api(scene):
    client = APIClient()
    client.force_authenticate(user=scene["owner"])
    return client


# ============================================================
# Model invariants
# ============================================================


def test_model_universe_mismatch_rejected(scene):
    """workspace / universe must match episode.universe.workspace."""
    other_owner, other_ws = _mkworkspace("other@nm.test", "OTHER-WS")
    other_universe = Universe.objects.create(
        workspace=other_ws, name="elsewhere",
    )
    mem = NarrativeMemory(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=other_universe,  # WRONG
        kind=NarrativeMemoryKind.EVENT,
        body="cross-universe",
    )
    with pytest.raises(ValidationError):
        mem.full_clean()


def test_model_workspace_mismatch_rejected(scene):
    """workspace must match episode.universe.workspace."""
    _, other_ws = _mkworkspace("wsx@nm.test", "OTHER-WS-2")
    mem = NarrativeMemory(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=other_ws,  # WRONG
        universe=scene["universe"],
        kind=NarrativeMemoryKind.EVENT,
        body="cross-workspace",
    )
    with pytest.raises(ValidationError):
        mem.full_clean()


def test_model_blank_body_rejected(scene):
    mem = NarrativeMemory(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="   ",
    )
    with pytest.raises(ValidationError):
        mem.full_clean()


def test_model_supersedes_wrong_episode_rejected(scene):
    """supersedes must point to a row in the same Episode."""
    other_episode = Episode.objects.create(
        universe=scene["universe"],
        title="Other story",
        operator_topic="unrelated",
    )
    other_episode.cast.add(scene["patch"])
    prior = NarrativeMemory.objects.create(
        episode=other_episode,
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="prior in other episode",
    )
    mem = NarrativeMemory(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="tries to retcon across episodes",
        supersedes=prior,
    )
    with pytest.raises(ValidationError):
        mem.full_clean()


# ============================================================
# Signal invariants (witnessed_by M2M)
# ============================================================


def test_witness_must_be_in_episode_cast(scene):
    """A Teammate not in Episode.cast cannot be a witness."""
    mem = NarrativeMemory.objects.create(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="printer went rogue",
    )
    outsider = Teammate.objects.create(
        workspace=scene["workspace"], universe=scene["universe"],
        name="Outsider",
        runway_avatar_id="av-x",
        portrait_path="https://fake/x.png",
        business_brief="Not in cast.",
    )
    with pytest.raises(ValidationError):
        mem.witnessed_by.add(outsider)


def test_cross_universe_witness_rejected(scene):
    other_owner, other_ws = _mkworkspace("otr@nm.test", "OTR-WS")
    other_universe = Universe.objects.create(
        workspace=other_ws, name="elsewhere-uni",
    )
    other_tm = Teammate.objects.create(
        workspace=other_ws, universe=other_universe, name="Elsewhere",
        runway_avatar_id="av-e",
        portrait_path="https://fake/e.png",
        business_brief="From another world.",
    )
    mem = NarrativeMemory.objects.create(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="cross-universe test",
    )
    with pytest.raises(ValidationError):
        mem.witnessed_by.add(other_tm)


def test_cast_witness_allowed(scene):
    mem = NarrativeMemory.objects.create(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="the printer started a job Patch did not queue",
    )
    mem.witnessed_by.set([scene["patch"], scene["rivet"]])
    assert set(mem.witnessed_by.values_list("id", flat=True)) == {
        scene["patch"].id, scene["rivet"].id,
    }


# ============================================================
# RESTRICT on delete
# ============================================================


def test_restrict_blocks_episode_hard_delete_with_memories(scene):
    NarrativeMemory.objects.create(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="blocking memory",
    )
    with pytest.raises(RestrictedError):
        scene["episode"].delete()


def test_restrict_blocks_composition_hard_delete_with_memories(scene):
    NarrativeMemory.objects.create(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="blocking memory",
    )
    with pytest.raises(RestrictedError):
        scene["composition"].delete()


def test_workspace_cascade_still_wipes_memories(scene):
    """Shared-CASCADE-parent rule: Workspace deletion cascades
    through Universe + Episode + Composition + memory, satisfying
    RESTRICT because all four descend from the same cascading
    ancestor."""
    NarrativeMemory.objects.create(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="cascade-cleared",
    )
    ws_id = scene["workspace"].id
    scene["workspace"].delete()
    assert NarrativeMemory.objects.filter(workspace_id=ws_id).count() == 0


# ============================================================
# Promote endpoint
# ============================================================


def _promote_url(comp_id) -> str:
    return f"/api/compositions/{comp_id}/promote-narrative-memory/"


def test_promote_defaults_apply_when_spa_omits_kind_and_weight(api, scene):
    """SESSION 264 dogfood correction — the creator-facing UI no
    longer sends ``kind`` or ``weight``. The backend serializer
    must apply ``kind='event'`` + ``weight='peripheral'`` defaults
    so the wire contract for the corrected UX stays intact.

    The UI also submits ``witnessed_by=[]`` to mean "Everyone in
    this episode" (empty M2M = whole cast convention). The row
    must be created with an empty witness M2M in that case.
    """
    r = api.post(
        _promote_url(scene["composition"].id),
        {
            "episode": str(scene["episode"].id),
            "memories": [
                {"body": "the printer went rogue", "witnessed_by": []},
            ],
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    payload = r.json()
    assert len(payload["memories"]) == 1
    row = NarrativeMemory.objects.get(pk=payload["memories"][0]["id"])
    assert row.kind == NarrativeMemoryKind.EVENT
    assert row.weight == "peripheral"
    assert list(row.witnessed_by.all()) == []


def test_promote_creates_rows(api, scene):
    r = api.post(
        _promote_url(scene["composition"].id),
        {
            "episode": str(scene["episode"].id),
            "memories": [
                {
                    "body": "Patch connected an AI agent to workshop tools",
                    "kind": "event",
                    "weight": "central",
                    "witnessed_by": [
                        str(scene["patch"].id),
                        str(scene["rivet"].id),
                    ],
                },
                {
                    "body": "Rivet paused tokens",
                    "kind": "action",
                    "witnessed_by": [str(scene["patch"].id), str(scene["rivet"].id)],
                },
            ],
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    payload = r.json()
    assert len(payload["memories"]) == 2
    rows = NarrativeMemory.objects.filter(
        source_composition=scene["composition"],
    )
    assert rows.count() == 2
    for row in rows:
        assert row.episode_id == scene["episode"].id
        assert row.workspace_id == scene["workspace"].id
        assert row.universe_id == scene["universe"].id
        assert row.promoted_by_id == scene["owner"].id
        assert row.status == NarrativeMemoryStatus.REMEMBERED


def test_promote_rejects_non_cast_witness(api, scene):
    outsider = Teammate.objects.create(
        workspace=scene["workspace"], universe=scene["universe"],
        name="Outsider",
        runway_avatar_id="av-x",
        portrait_path="https://fake/x.png",
        business_brief="Not in cast.",
    )
    r = api.post(
        _promote_url(scene["composition"].id),
        {
            "episode": str(scene["episode"].id),
            "memories": [
                {
                    "body": "outsider-witnessed",
                    "witnessed_by": [str(outsider.id)],
                },
            ],
        },
        format="json",
    )
    assert r.status_code == 400, r.content
    assert NarrativeMemory.objects.count() == 0  # atomic rollback


def test_promote_rejects_wrong_workspace_episode(api, scene):
    _, other_ws = _mkworkspace("other2@nm.test", "OTHER-WS-3")
    other_universe = Universe.objects.create(
        workspace=other_ws, name="foreign",
    )
    other_episode = Episode.objects.create(
        universe=other_universe,
        title="Foreign",
        operator_topic="not accessible",
    )
    r = api.post(
        _promote_url(scene["composition"].id),
        {
            "episode": str(other_episode.id),
            "memories": [{"body": "foreign attempt"}],
        },
        format="json",
    )
    assert r.status_code == 400, r.content
    assert NarrativeMemory.objects.count() == 0


def test_promote_bad_uuid_episode_404_shape(api, scene):
    r = api.post(
        _promote_url(scene["composition"].id),
        {
            "episode": str(uuid.uuid4()),
            "memories": [{"body": "phantom"}],
        },
        format="json",
    )
    assert r.status_code == 400
    assert NarrativeMemory.objects.count() == 0


def test_promote_empty_batch_rejected(api, scene):
    r = api.post(
        _promote_url(scene["composition"].id),
        {"episode": str(scene["episode"].id), "memories": []},
        format="json",
    )
    assert r.status_code == 400


# ============================================================
# List + filters
# ============================================================


def test_list_by_episode(api, scene):
    NarrativeMemory.objects.create(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="ep-scoped",
    )
    other_ep = Episode.objects.create(
        universe=scene["universe"],
        title="Other",
        operator_topic="other",
    )
    other_ep.cast.add(scene["patch"])
    NarrativeMemory.objects.create(
        episode=other_ep,
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="different-ep",
    )
    r = api.get(f"/api/narrative-memories/?episode={scene['episode'].id}")
    assert r.status_code == 200
    items = _unwrap(r)
    ids = {m["id"] for m in items}
    bodies = {m["body"] for m in items}
    assert "ep-scoped" in bodies
    assert "different-ep" not in bodies


def test_list_by_universe(api, scene):
    NarrativeMemory.objects.create(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="uni-scoped-1",
    )
    NarrativeMemory.objects.create(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="uni-scoped-2",
    )
    r = api.get(f"/api/narrative-memories/?universe={scene['universe'].id}")
    assert r.status_code == 200
    bodies = {m["body"] for m in _unwrap(r)}
    assert {"uni-scoped-1", "uni-scoped-2"}.issubset(bodies)


def test_cross_workspace_list_isolation(scene):
    """A user in a different workspace sees zero rows."""
    NarrativeMemory.objects.create(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="private",
    )
    other_owner, _ = _mkworkspace("otx@nm.test", "OTX-WS")
    client = APIClient()
    client.force_authenticate(user=other_owner)
    r = client.get("/api/narrative-memories/")
    assert r.status_code == 200
    assert _unwrap(r) == []


# ============================================================
# Archive / unarchive
# ============================================================


def test_archive_then_unarchive(api, scene):
    mem = NarrativeMemory.objects.create(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="to be archived",
    )
    # Archive
    r = api.delete(f"/api/narrative-memories/{mem.id}/")
    assert r.status_code == 204
    mem.refresh_from_db()
    assert mem.archived_at is not None
    assert mem.status == NarrativeMemoryStatus.ARCHIVED
    # Default list excludes archived
    r_list = api.get(
        f"/api/narrative-memories/?episode={scene['episode'].id}"
    )
    bodies = {m["body"] for m in _unwrap(r_list)}
    assert "to be archived" not in bodies
    # include_archived=true shows it
    r_list2 = api.get(
        f"/api/narrative-memories/?episode={scene['episode'].id}"
        f"&include_archived=true"
    )
    bodies2 = {m["body"] for m in _unwrap(r_list2)}
    assert "to be archived" in bodies2
    # Unarchive
    r_ua = api.post(f"/api/narrative-memories/{mem.id}/unarchive/")
    assert r_ua.status_code == 200
    mem.refresh_from_db()
    assert mem.archived_at is None
    assert mem.status == NarrativeMemoryStatus.REMEMBERED


# ============================================================
# Supersede chain
# ============================================================


def test_supersede_flips_prior_to_superseded(api, scene):
    prior = NarrativeMemory.objects.create(
        episode=scene["episode"],
        source_composition=scene["composition"],
        workspace=scene["workspace"],
        universe=scene["universe"],
        body="printer once tried to make Patch royalty",
    )
    r = api.post(
        _promote_url(scene["composition"].id),
        {
            "episode": str(scene["episode"].id),
            "memories": [
                {
                    "body": "printer was ordered to sandbox afterward",
                    "supersedes": str(prior.id),
                    "superseded_reason": "clarified outcome",
                },
            ],
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    prior.refresh_from_db()
    assert prior.status == NarrativeMemoryStatus.SUPERSEDED
    assert prior.superseded_at is not None
    # Default list excludes superseded
    r_list = api.get(
        f"/api/narrative-memories/?episode={scene['episode'].id}"
    )
    bodies = {m["body"] for m in _unwrap(r_list)}
    assert "printer once tried to make Patch royalty" not in bodies
    assert "printer was ordered to sandbox afterward" in bodies
