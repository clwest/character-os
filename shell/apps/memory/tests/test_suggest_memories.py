"""SESSION 281 Slice 281.1 — curator service + endpoint tests.

Covers:

* Completed Composition with realized dialogue → 200 with 3
  candidates; ``substrate_summary`` reflects counts.
* Empty realized dialogue (blank ``synthesized_brief``) → 200
  with ``candidates=[]``; NO LLM call.
* Non-completed Composition (DRAFT / RUNNING / FAILED) → 200
  with ``candidates=[]``; NO LLM call.
* Default ``n=3``; clamp ``[1, 5]``; out-of-range / non-int
  silently falls back to default.
* Cache miss → hit on identical second call.
* ``?refresh=true`` bypasses the cache.
* Cache-key rotates when a new same-composition
  ``NarrativeMemory`` lands (SESSION 281 scope-lock).
* LLM upstream failure → typed ``SuggestMemoriesUpstreamError``
  from service; endpoint maps to 502.
* Non-member caller → 404 (queryset scoping — no existence
  disclosure).
* Malformed / partial LLM output — drops junk entries, keeps
  valid ones, raises for structural JSON errors.
* Backend-owned error vocabulary invariant — 502 detail contains
  no banned implementation vocabulary.
* Curator NEVER writes to NarrativeMemory during suggestion
  generation.

No real OpenAI calls — all provider hops mocked at the service
layer via ``apps.memory.services._call_curator_openai``.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace
from apps.compositions.models import Composition, CompositionStatus
from apps.memory.models import (
    NarrativeMemory,
    NarrativeMemoryKind,
    NarrativeMemoryWeight,
)
from apps.spokespeople.models import Teammate
from apps.universe.models import Episode, Universe

User = get_user_model()


# ---- fixtures -------------------------------------------------


@pytest.fixture
def owner_user(db):
    return User.objects.create_user(email="curator-owner@u.test", password="x")


@pytest.fixture
def workspace(owner_user):
    ws = Workspace.objects.filter(owner=owner_user).first()
    if ws is None:
        ws = Workspace.objects.create(name="Curator WS", owner=owner_user)
    Membership.objects.get_or_create(
        user=owner_user,
        workspace=ws,
        defaults={"role": Membership.Role.OWNER},
    )
    return ws


@pytest.fixture
def stranger_user(db):
    return User.objects.create_user(
        email="curator-stranger@u.test", password="x",
    )


@pytest.fixture
def client(owner_user):
    c = APIClient()
    c.force_authenticate(user=owner_user)
    return c


@pytest.fixture
def stranger_client(stranger_user):
    c = APIClient()
    c.force_authenticate(user=stranger_user)
    return c


@pytest.fixture
def universe(workspace):
    return Universe.objects.create(
        workspace=workspace,
        name="Curator Test Bakery",
        brief="A small artisan bakery for curator-service tests.",
    )


@pytest.fixture
def cast(universe, workspace):
    ruby = Teammate.objects.create(
        workspace=workspace,
        universe=universe,
        name="Ruby",
        tone_archetype="warm",
        personality="warm baker who keeps the shop grounded.",
    )
    tyson = Teammate.objects.create(
        workspace=workspace,
        universe=universe,
        name="Tyson",
        tone_archetype="playful",
        personality="playful counterpart who tries out new ideas.",
    )
    return [ruby, tyson]


@pytest.fixture
def episode(universe, cast):
    ep = Episode.objects.create(
        universe=universe,
        title="After getting locked out",
        operator_topic="After getting locked out of the bakery.",
    )
    ep.cast.set(cast)
    return ep


@pytest.fixture
def completed_composition(workspace, cast, episode):
    """Completed composition with a realistic (non-empty) brief.

    The service strips leading `# ...` comment header lines
    exactly like the Q280.9 probe; both a comment header and
    dialogue turns are included so we exercise that stripping."""
    comp = Composition.objects.create(
        workspace=workspace,
        spokesperson=cast[0],
        name="Fox and Flour closing routine test",
        template_kind="dialogue_scene",
        status=CompositionStatus.COMPLETED,
        episode=episode,
        synthesized_brief=(
            "# Auto-generated dialogue scene\n"
            "# Duration target: 45s\n"
            "\n"
            "Ruby: Before we close, promise me you'll actually "
            "leave when I say I'm done.\n"
            "Tyson: I promise — unless the mascot's still out "
            "here, then I'm staying with the mascot.\n"
            "Ruby: Deal. Neither of us leaves until the other "
            "says they've got everything they need.\n"
        ),
        created_by=None,
    )
    return comp


@pytest.fixture
def draft_composition(workspace, cast, episode):
    """A non-completed composition — used to verify the
    empty-substrate short-circuit for the status axis."""
    return Composition.objects.create(
        workspace=workspace,
        spokesperson=cast[0],
        name="Draft composition",
        template_kind="dialogue_scene",
        status=CompositionStatus.DRAFT,
        episode=episode,
        synthesized_brief="",
    )


@pytest.fixture
def empty_dialogue_composition(workspace, cast, episode):
    """Completed but with an empty synthesized_brief — exercises
    the dialogue-axis short-circuit even when status is COMPLETED."""
    return Composition.objects.create(
        workspace=workspace,
        spokesperson=cast[0],
        name="Completed with empty brief",
        template_kind="dialogue_scene",
        status=CompositionStatus.COMPLETED,
        episode=episode,
        synthesized_brief="   \n # header only\n",
    )


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


# ---- helpers --------------------------------------------------


def _valid_candidate(**overrides) -> dict:
    base = {
        "body": "Ruby and Tyson agreed neither leaves until the "
                "other says they have what they need.",
        "kind": NarrativeMemoryKind.EVENT.value,
        "witnesses": ["Ruby", "Tyson"],
        "narrative_gravity_note": (
            "Could be tested if one of them ever has to leave "
            "early."
        ),
    }
    base.update(overrides)
    return base


def _mock_llm_return(candidates: list[dict]) -> tuple[str, int, int]:
    """Build a (raw_text, tokens_in, tokens_out) mock return."""
    return (json.dumps({"candidates": candidates}), 620, 180)


# ---- service-layer tests --------------------------------------


@pytest.mark.django_db
def test_service_completed_composition_returns_three_candidates(
    completed_composition,
):
    from apps.memory.services import suggest_memories_from_composition

    faked = _mock_llm_return([
        _valid_candidate(body="a", narrative_gravity_note="a-note"),
        _valid_candidate(
            body="b",
            kind=NarrativeMemoryKind.DIALOGUE_CALLBACK.value,
            narrative_gravity_note="b-note",
        ),
        _valid_candidate(body="c", narrative_gravity_note="c-note"),
    ])
    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=faked,
    ) as mock_llm:
        payload = suggest_memories_from_composition(completed_composition)

    mock_llm.assert_called_once()
    assert len(payload["candidates"]) == 3
    bodies = [c["body"] for c in payload["candidates"]]
    assert bodies == ["a", "b", "c"]
    assert payload["candidates"][1]["kind"] == "dialogue_callback"
    assert payload["substrate_summary"]["cast_count"] == 2
    assert payload["substrate_summary"]["dialogue_chars"] > 0
    assert payload["cache"]["hit"] is False
    assert payload["cache"]["ttl_seconds"] == 1800
    assert payload["model"] == "gpt-5.6-terra"


@pytest.mark.django_db
def test_service_empty_dialogue_short_circuits_no_llm(
    empty_dialogue_composition,
):
    from apps.memory.services import suggest_memories_from_composition

    with patch("apps.memory.services._call_curator_openai") as mock_llm:
        payload = suggest_memories_from_composition(
            empty_dialogue_composition,
        )

    mock_llm.assert_not_called()
    assert payload["candidates"] == []
    assert payload["substrate_summary"]["dialogue_chars"] == 0
    assert payload["cache"]["hit"] is False


@pytest.mark.django_db
def test_service_non_completed_composition_short_circuits(
    draft_composition,
):
    from apps.memory.services import suggest_memories_from_composition

    with patch("apps.memory.services._call_curator_openai") as mock_llm:
        payload = suggest_memories_from_composition(draft_composition)

    mock_llm.assert_not_called()
    assert payload["candidates"] == []


@pytest.mark.django_db
def test_service_default_n_is_three(completed_composition):
    from apps.memory.services import suggest_memories_from_composition

    faked = _mock_llm_return([
        _valid_candidate(body=f"c{i}") for i in range(5)
    ])
    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=faked,
    ):
        payload = suggest_memories_from_composition(completed_composition)

    assert len(payload["candidates"]) == 3


@pytest.mark.django_db
@pytest.mark.parametrize("requested,expected", [
    (1, 1),
    (5, 5),
    (0, 3),     # clamp to default
    (6, 3),     # clamp to default
    (-1, 3),    # clamp to default
])
def test_service_n_clamp(completed_composition, requested, expected):
    from apps.memory.services import suggest_memories_from_composition

    faked = _mock_llm_return([
        _valid_candidate(body=f"c{i}") for i in range(5)
    ])
    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=faked,
    ):
        payload = suggest_memories_from_composition(
            completed_composition, n=requested,
        )

    assert len(payload["candidates"]) == expected


@pytest.mark.django_db
def test_service_cache_miss_then_hit(completed_composition):
    from apps.memory.services import suggest_memories_from_composition

    faked = _mock_llm_return([
        _valid_candidate(body="only-once-a"),
        _valid_candidate(body="only-once-b"),
        _valid_candidate(body="only-once-c"),
    ])
    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=faked,
    ) as mock_llm:
        first = suggest_memories_from_composition(completed_composition)
        second = suggest_memories_from_composition(completed_composition)

    assert mock_llm.call_count == 1
    assert first["cache"]["hit"] is False
    assert second["cache"]["hit"] is True
    assert [c["body"] for c in first["candidates"]] == [
        c["body"] for c in second["candidates"]
    ]
    # Immutability — the stored payload should still read hit=False
    # if we bypass the cache-hit-flip logic. Sanity: the returned
    # dicts are distinct objects.
    assert first is not second


@pytest.mark.django_db
def test_service_refresh_bypasses_cache(completed_composition):
    from apps.memory.services import suggest_memories_from_composition

    faked = _mock_llm_return([
        _valid_candidate(body="A"),
        _valid_candidate(body="B"),
        _valid_candidate(body="C"),
    ])
    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=faked,
    ) as mock_llm:
        suggest_memories_from_composition(completed_composition)
        suggest_memories_from_composition(
            completed_composition, use_cache=False,
        )

    assert mock_llm.call_count == 2


@pytest.mark.django_db
def test_service_cache_key_rotates_on_new_same_composition_memory(
    completed_composition, workspace, universe, episode, cast, owner_user,
):
    """SESSION 281 scope-lock: a newly remembered item from the same
    composition should rotate the cache key. Prove it by observing
    that a second call after inserting a same-composition memory
    triggers a fresh LLM call."""
    from apps.memory.services import suggest_memories_from_composition

    faked_one = _mock_llm_return([
        _valid_candidate(body="round-one-a"),
        _valid_candidate(body="round-one-b"),
        _valid_candidate(body="round-one-c"),
    ])
    faked_two = _mock_llm_return([
        _valid_candidate(body="round-two-a"),
        _valid_candidate(body="round-two-b"),
        _valid_candidate(body="round-two-c"),
    ])

    call_side_effects = iter([faked_one, faked_two])

    def _mock_llm(*args, **kwargs):
        return next(call_side_effects)

    with patch(
        "apps.memory.services._call_curator_openai",
        side_effect=_mock_llm,
    ) as mock_llm:
        first = suggest_memories_from_composition(completed_composition)
        assert first["cache"]["hit"] is False

        # Immediate second call = cache HIT (baseline behavior).
        cached = suggest_memories_from_composition(completed_composition)
        assert cached["cache"]["hit"] is True
        assert mock_llm.call_count == 1

        # Now promote a memory from this composition via the real
        # promotion service — mirrors the Slice 281.2 code path.
        from apps.memory.views import promote_from_composition
        promote_from_composition(
            composition=completed_composition,
            episode=episode,
            memory_items=[{
                "body": "Ruby will lock up unless Tyson stays.",
                "kind": NarrativeMemoryKind.PROMISE.value,
                "weight": NarrativeMemoryWeight.PERIPHERAL.value,
                "witnessed_by": [],
            }],
            promoted_by=owner_user,
        )

        # Third call should MISS the cache (key rotated) and hit
        # the LLM again.
        third = suggest_memories_from_composition(completed_composition)
        assert third["cache"]["hit"] is False
        assert mock_llm.call_count == 2
        assert [c["body"] for c in third["candidates"]] == [
            "round-two-a", "round-two-b", "round-two-c",
        ]


@pytest.mark.django_db
def test_service_upstream_error_raises_typed(completed_composition):
    from apps.memory.services import (
        SuggestMemoriesUpstreamError,
        suggest_memories_from_composition,
    )

    with patch(
        "apps.memory.services._call_curator_openai",
        side_effect=SuggestMemoriesUpstreamError("provider down"),
    ):
        with pytest.raises(SuggestMemoriesUpstreamError):
            suggest_memories_from_composition(completed_composition)


@pytest.mark.django_db
def test_service_malformed_json_raises_upstream_error(completed_composition):
    from apps.memory.services import (
        SuggestMemoriesUpstreamError,
        suggest_memories_from_composition,
    )

    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=("this is not json", 500, 40),
    ):
        with pytest.raises(SuggestMemoriesUpstreamError):
            suggest_memories_from_composition(completed_composition)


@pytest.mark.django_db
def test_service_missing_candidates_key_raises(completed_composition):
    from apps.memory.services import (
        SuggestMemoriesUpstreamError,
        suggest_memories_from_composition,
    )

    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=(json.dumps({"unrelated": []}), 500, 40),
    ):
        with pytest.raises(SuggestMemoriesUpstreamError):
            suggest_memories_from_composition(completed_composition)


@pytest.mark.django_db
def test_service_drops_junk_but_keeps_valid(completed_composition):
    """Tolerant parser: entries without body, with unknown kinds,
    or wrong shape are dropped. Valid entries pass through."""
    from apps.memory.services import suggest_memories_from_composition

    faked = _mock_llm_return([
        {"body": "", "kind": "event", "witnesses": []},       # empty body
        {"body": "  ", "kind": "event", "witnesses": []},      # whitespace body
        {"body": "no-kind", "witnesses": []},                  # missing kind
        {"body": "bad-kind", "kind": "wisdom", "witnesses": []},  # unknown
        "just a string",                                       # wrong shape
        _valid_candidate(body="good-one"),
        _valid_candidate(
            body="second-good",
            kind=NarrativeMemoryKind.WORLD_DETAIL.value,
            witnesses="everyone",  # string -> [] (whole-cast)
        ),
    ])
    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=faked,
    ):
        payload = suggest_memories_from_composition(
            completed_composition, n=5,
        )

    bodies = [c["body"] for c in payload["candidates"]]
    assert bodies == ["good-one", "second-good"]
    # 'everyone' string collapses to empty witnesses list per the
    # promote_from_composition whole-cast convention.
    assert payload["candidates"][1]["witnesses"] == []


@pytest.mark.django_db
def test_service_never_writes_narrative_memory(completed_composition):
    """Load-bearing invariant per SESSION 281 scope-lock:
    curator NEVER creates, edits, archives, or supersedes a
    NarrativeMemory row."""
    from apps.memory.services import suggest_memories_from_composition

    before = NarrativeMemory.objects.count()

    faked = _mock_llm_return([
        _valid_candidate(body="never-persisted-a"),
        _valid_candidate(body="never-persisted-b"),
        _valid_candidate(body="never-persisted-c"),
    ])
    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=faked,
    ):
        payload = suggest_memories_from_composition(completed_composition)

    after = NarrativeMemory.objects.count()
    assert after == before, (
        "curator service must not create any NarrativeMemory rows"
    )
    assert len(payload["candidates"]) == 3


@pytest.mark.django_db
def test_service_existing_universe_memories_feed_the_prompt(
    completed_composition, workspace, universe, episode, cast, owner_user,
):
    """The prompt should carry existing REMEMBERED memories so the
    'do not propose duplicates' instruction has ground truth. We
    probe this by inspecting the substrate_summary rather than
    scraping the prompt string."""
    from apps.memory.services import suggest_memories_from_composition
    from apps.memory.views import promote_from_composition

    # Seed one non-source-composition memory (different composition,
    # same universe) so the "existing memories" set is non-empty
    # WITHOUT rotating our cache key.
    other_comp = Composition.objects.create(
        workspace=workspace,
        spokesperson=cast[0],
        name="Other completed comp",
        template_kind="dialogue_scene",
        status=CompositionStatus.COMPLETED,
        episode=episode,
        synthesized_brief="# hdr\nRuby: hi.\n",
    )
    promote_from_composition(
        composition=other_comp,
        episode=episode,
        memory_items=[{
            "body": "The oven has a habit of starting cold.",
            "kind": NarrativeMemoryKind.WORLD_DETAIL.value,
            "weight": NarrativeMemoryWeight.PERIPHERAL.value,
            "witnessed_by": [],
        }],
        promoted_by=owner_user,
    )

    faked = _mock_llm_return([
        _valid_candidate(body="a"),
        _valid_candidate(body="b"),
        _valid_candidate(body="c"),
    ])
    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=faked,
    ):
        payload = suggest_memories_from_composition(completed_composition)

    assert payload["substrate_summary"]["existing_memories_used"] == 1


# ---- endpoint tests -------------------------------------------


@pytest.mark.django_db
def test_endpoint_completed_composition_returns_200(
    client, completed_composition,
):
    faked = _mock_llm_return([
        _valid_candidate(body="one"),
        _valid_candidate(body="two"),
        _valid_candidate(body="three"),
    ])
    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=faked,
    ):
        resp = client.get(
            f"/api/compositions/{completed_composition.id}"
            f"/suggested-memories/"
        )
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert len(body["candidates"]) == 3
    assert body["candidates"][0]["body"] == "one"
    assert body["cache"]["ttl_seconds"] == 1800


@pytest.mark.django_db
def test_endpoint_empty_dialogue_returns_200_empty_no_llm(
    client, empty_dialogue_composition,
):
    with patch("apps.memory.services._call_curator_openai") as mock_llm:
        resp = client.get(
            f"/api/compositions/{empty_dialogue_composition.id}"
            f"/suggested-memories/"
        )
    assert resp.status_code == 200, resp.content
    assert resp.json()["candidates"] == []
    mock_llm.assert_not_called()


@pytest.mark.django_db
def test_endpoint_draft_composition_returns_200_empty_no_llm(
    client, draft_composition,
):
    with patch("apps.memory.services._call_curator_openai") as mock_llm:
        resp = client.get(
            f"/api/compositions/{draft_composition.id}"
            f"/suggested-memories/"
        )
    assert resp.status_code == 200, resp.content
    assert resp.json()["candidates"] == []
    mock_llm.assert_not_called()


@pytest.mark.django_db
def test_endpoint_refresh_query_param_bypasses_cache(
    client, completed_composition,
):
    faked = _mock_llm_return([
        _valid_candidate(body="x"),
        _valid_candidate(body="y"),
        _valid_candidate(body="z"),
    ])
    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=faked,
    ) as mock_llm:
        r1 = client.get(
            f"/api/compositions/{completed_composition.id}"
            f"/suggested-memories/"
        )
        r2 = client.get(
            f"/api/compositions/{completed_composition.id}"
            f"/suggested-memories/"
        )
        r3 = client.get(
            f"/api/compositions/{completed_composition.id}"
            f"/suggested-memories/?refresh=true"
        )

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200
    assert r1.json()["cache"]["hit"] is False
    assert r2.json()["cache"]["hit"] is True
    assert r3.json()["cache"]["hit"] is False
    assert mock_llm.call_count == 2


@pytest.mark.django_db
def test_endpoint_n_query_param_respected(client, completed_composition):
    faked = _mock_llm_return([
        _valid_candidate(body=f"c{i}") for i in range(5)
    ])
    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=faked,
    ):
        resp = client.get(
            f"/api/compositions/{completed_composition.id}"
            f"/suggested-memories/?n=2"
        )
    assert resp.status_code == 200
    assert len(resp.json()["candidates"]) == 2


@pytest.mark.django_db
def test_endpoint_n_out_of_range_falls_back_to_default(
    client, completed_composition,
):
    faked = _mock_llm_return([
        _valid_candidate(body=f"c{i}") for i in range(5)
    ])
    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=faked,
    ):
        r1 = client.get(
            f"/api/compositions/{completed_composition.id}"
            f"/suggested-memories/?n=99"
        )
        r2 = client.get(
            f"/api/compositions/{completed_composition.id}"
            f"/suggested-memories/?n=banana&refresh=true"
        )
    assert r1.status_code == 200
    assert len(r1.json()["candidates"]) == 3
    assert r2.status_code == 200
    assert len(r2.json()["candidates"]) == 3


@pytest.mark.django_db
def test_endpoint_upstream_error_returns_502(
    client, completed_composition,
):
    from apps.memory.services import SuggestMemoriesUpstreamError

    with patch(
        "apps.memory.services._call_curator_openai",
        side_effect=SuggestMemoriesUpstreamError("provider down"),
    ):
        resp = client.get(
            f"/api/compositions/{completed_composition.id}"
            f"/suggested-memories/"
        )
    assert resp.status_code == 502, resp.content
    body = resp.json()
    assert body["error"] == "suggestion_provider_unavailable"
    detail = body["detail"].lower()
    assert "try again" in detail or "shortly" in detail


@pytest.mark.django_db
def test_endpoint_non_member_gets_404(
    stranger_client, completed_composition,
):
    resp = stranger_client.get(
        f"/api/compositions/{completed_composition.id}"
        f"/suggested-memories/"
    )
    assert resp.status_code == 404, resp.content


@pytest.mark.django_db
def test_endpoint_error_detail_never_leaks_implementation_vocabulary(
    client, completed_composition,
):
    """Backend-owned operator-facing copy — the 502 detail string
    — MUST NOT contain implementation vocabulary. Candidate bodies
    + kinds + narrative_gravity_notes are model output and pass
    through unfiltered; that guarantee is enforced on the SPA
    render in Slice 281.2, not here."""
    from apps.memory.services import SuggestMemoriesUpstreamError

    with patch(
        "apps.memory.services._call_curator_openai",
        side_effect=SuggestMemoriesUpstreamError("bad"),
    ):
        resp = client.get(
            f"/api/compositions/{completed_composition.id}"
            f"/suggested-memories/"
        )
    body = resp.json()
    banned = {
        "narrativememorykind",
        "dialogue_callback",
        "world_detail",
        "retrieval",
        "substrate",
        "provenance",
        "memory_id",
        "top_k",
        "embedding",
        "vector",
        "latent thread",
        "promote_from_composition",
        "candidate",
        "prompt",
        "llm",
    }
    detail_lower = body["detail"].lower()
    for word in banned:
        assert word not in detail_lower, (
            f"operator-facing detail leaked implementation "
            f"vocabulary: {word!r}"
        )


@pytest.mark.django_db
def test_endpoint_does_not_write_narrative_memory(
    client, completed_composition,
):
    """Endpoint-level equivalent of the service-layer invariant.
    A curator fetch must not persist anything."""
    faked = _mock_llm_return([
        _valid_candidate(body="a"),
        _valid_candidate(body="b"),
        _valid_candidate(body="c"),
    ])
    before = NarrativeMemory.objects.count()
    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=faked,
    ):
        resp = client.get(
            f"/api/compositions/{completed_composition.id}"
            f"/suggested-memories/"
        )
    assert resp.status_code == 200
    assert NarrativeMemory.objects.count() == before


@pytest.mark.django_db
def test_endpoint_existing_promoted_memory_still_untouched(
    client, completed_composition, workspace, universe, episode, cast,
    owner_user,
):
    """Regression guard: even after a curator call, previously
    promoted rows remain byte-identical. Mirrors the SESSION 281
    handoff's 'leave Fox & Flour memories in place' invariant."""
    from apps.memory.views import promote_from_composition

    promoted = promote_from_composition(
        composition=completed_composition,
        episode=episode,
        memory_items=[{
            "body": "A pre-existing promise that must not be touched.",
            "kind": NarrativeMemoryKind.PROMISE.value,
            "weight": NarrativeMemoryWeight.PERIPHERAL.value,
            "witnessed_by": [],
        }],
        promoted_by=owner_user,
    )
    row = promoted[0]
    original_body = row.body
    original_kind = row.kind
    original_status = row.status
    original_updated = row.updated_at

    faked = _mock_llm_return([
        _valid_candidate(body="curator-a"),
        _valid_candidate(body="curator-b"),
        _valid_candidate(body="curator-c"),
    ])
    with patch(
        "apps.memory.services._call_curator_openai",
        return_value=faked,
    ):
        resp = client.get(
            f"/api/compositions/{completed_composition.id}"
            f"/suggested-memories/?refresh=true"
        )
    assert resp.status_code == 200

    row.refresh_from_db()
    assert row.body == original_body
    assert row.kind == original_kind
    assert row.status == original_status
    assert row.updated_at == original_updated
    assert row.archived_at is None
