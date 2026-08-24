"""SESSION 280 v1 — possible-next-Episode suggestion service +
endpoint tests.

Covers:

* Empty Universe (0 non-archived Episodes) → 200 with empty
  ``suggestions`` list; no LLM call.
* Populated Universe → 200 with 3 suggestion strings;
  ``substrate_summary`` reflects counts.
* Cache hit vs miss — refresh=true bypasses; second identical
  call within TTL uses cache.
* n query param clamped to [1, 5]; invalid ``n`` falls back
  silently.
* LLM upstream failure → 502 with human-readable detail.
* Non-member gets 404 (Universe is not visible in queryset).
* Archived Universe is invisible without ``?include_archived``
  — same behavior as list/detail routes.

No real OpenAI calls — all provider hops are mocked at the
service layer.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace
from apps.universe.models import Episode, Universe

from django.contrib.auth import get_user_model

User = get_user_model()


# ---- fixtures -------------------------------------------------


@pytest.fixture
def owner_user(db):
    return User.objects.create_user(email="nes-owner@u.test", password="x")


@pytest.fixture
def workspace(owner_user):
    ws = Workspace.objects.filter(owner=owner_user).first()
    if ws is None:
        ws = Workspace.objects.create(name="NES Owner WS", owner=owner_user)
    Membership.objects.get_or_create(
        user=owner_user,
        workspace=ws,
        defaults={"role": Membership.Role.OWNER},
    )
    return ws


@pytest.fixture
def stranger_user(db):
    return User.objects.create_user(email="nes-stranger@u.test", password="x")


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
def universe_empty(workspace):
    return Universe.objects.create(
        workspace=workspace,
        name="NES Empty World",
        brief="",
    )


@pytest.fixture
def universe_with_episodes(workspace):
    u = Universe.objects.create(
        workspace=workspace,
        name="NES Bakery",
        brief=(
            "A neighborhood bakery. Warm mornings, sourdough, "
            "coffee, occasional strangeness."
        ),
    )
    Episode.objects.create(
        universe=u,
        title="Tyson is convinced the bakery is haunted.",
        operator_topic="Tyson is convinced the bakery is haunted.",
    )
    Episode.objects.create(
        universe=u,
        title="Ruby finds something strange in the bakery freezer.",
        operator_topic=(
            "Ruby finds something strange in the bakery freezer."
        ),
    )
    return u


@pytest.fixture(autouse=True)
def _clear_cache():
    """Cache is Redis-backed in prod; ensure test isolation by
    clearing before + after each test."""
    cache.clear()
    yield
    cache.clear()


# ---- helpers --------------------------------------------------


def _mock_openai_response(texts):
    """Build a fake OpenAI Responses-API response object that
    exposes .output_text (JSON) + .usage.input_tokens/output_tokens."""

    class _Usage:
        input_tokens = 500
        output_tokens = 60

    class _Response:
        usage = _Usage()

        def __init__(self, payload_json: str) -> None:
            self.output_text = payload_json

    import json as _json
    return _Response(_json.dumps({"suggestions": list(texts)}))


# ---- service-layer tests --------------------------------------


@pytest.mark.django_db
def test_service_empty_universe_returns_empty_no_llm_call(universe_empty):
    from apps.universe.services import suggest_next_episodes

    with patch(
        "apps.universe.services.next_episode_suggestions._call_openai"
    ) as mock_llm:
        payload = suggest_next_episodes(universe_empty)

    # Empty-substrate short-circuit — no LLM call at all.
    mock_llm.assert_not_called()
    assert payload["suggestions"] == []
    assert payload["substrate_summary"]["episodes_used"] == 0
    assert payload["cache"]["hit"] is False


@pytest.mark.django_db
def test_service_populated_universe_generates_three_suggestions(
    universe_with_episodes,
):
    from apps.universe.services import suggest_next_episodes

    faked = _mock_openai_response(
        [
            "Ruby and Tyson investigate whether the freezer discovery is connected to the haunting.",
            "Tyson stays late to record whatever is making the noises.",
            "A regular customer asks about a pastry that was never on the menu.",
        ]
    )
    with patch(
        "apps.universe.services.next_episode_suggestions._call_openai",
        return_value=(faked.output_text, 500, 60),
    ):
        payload = suggest_next_episodes(universe_with_episodes)

    assert len(payload["suggestions"]) == 3
    assert all(isinstance(s["text"], str) and s["text"] for s in payload["suggestions"])
    assert payload["substrate_summary"]["episodes_used"] == 2
    assert payload["cache"]["hit"] is False


@pytest.mark.django_db
def test_service_cache_hit_on_second_call(universe_with_episodes):
    from apps.universe.services import suggest_next_episodes

    faked_payload = _mock_openai_response(
        ["A", "B", "C"]
    ).output_text
    with patch(
        "apps.universe.services.next_episode_suggestions._call_openai",
        return_value=(faked_payload, 500, 60),
    ) as mock_llm:
        first = suggest_next_episodes(universe_with_episodes)
        second = suggest_next_episodes(universe_with_episodes)

    assert mock_llm.call_count == 1  # cached second call
    assert first["cache"]["hit"] is False
    assert second["cache"]["hit"] is True
    assert [s["text"] for s in first["suggestions"]] == [s["text"] for s in second["suggestions"]]


@pytest.mark.django_db
def test_service_refresh_bypasses_cache(universe_with_episodes):
    from apps.universe.services import suggest_next_episodes

    faked_payload = _mock_openai_response(["A", "B", "C"]).output_text
    with patch(
        "apps.universe.services.next_episode_suggestions._call_openai",
        return_value=(faked_payload, 500, 60),
    ) as mock_llm:
        suggest_next_episodes(universe_with_episodes)
        suggest_next_episodes(universe_with_episodes, use_cache=False)

    assert mock_llm.call_count == 2


@pytest.mark.django_db
def test_service_upstream_error_raises(universe_with_episodes):
    from apps.universe.services import (
        NextEpisodeSuggestionUpstreamError,
        suggest_next_episodes,
    )

    with patch(
        "apps.universe.services.next_episode_suggestions._call_openai",
        side_effect=NextEpisodeSuggestionUpstreamError("boom"),
    ):
        with pytest.raises(NextEpisodeSuggestionUpstreamError):
            suggest_next_episodes(universe_with_episodes)


@pytest.mark.django_db
def test_service_never_pads_below_n(universe_with_episodes):
    """If the LLM returns only 1 suggestion, service returns
    ``suggestions=[{"text": ...}]``. It NEVER invents extras
    to guarantee ``n``."""
    from apps.universe.services import suggest_next_episodes

    faked_payload = _mock_openai_response(["only one"]).output_text
    with patch(
        "apps.universe.services.next_episode_suggestions._call_openai",
        return_value=(faked_payload, 500, 60),
    ):
        payload = suggest_next_episodes(universe_with_episodes, n=3)

    assert len(payload["suggestions"]) == 1


@pytest.mark.django_db
def test_service_drops_empty_strings_from_llm(universe_with_episodes):
    from apps.universe.services import suggest_next_episodes

    faked_payload = _mock_openai_response(["real", "", "  ", "also real"]).output_text
    with patch(
        "apps.universe.services.next_episode_suggestions._call_openai",
        return_value=(faked_payload, 500, 60),
    ):
        payload = suggest_next_episodes(universe_with_episodes)

    assert [s["text"] for s in payload["suggestions"]] == ["real", "also real"]


# ---- endpoint tests -------------------------------------------


@pytest.mark.django_db
def test_endpoint_empty_universe_returns_200_with_empty_suggestions(
    client, universe_empty,
):
    with patch(
        "apps.universe.services.next_episode_suggestions._call_openai"
    ) as mock_llm:
        resp = client.get(
            f"/api/universes/{universe_empty.id}/next-episode-suggestions/"
        )
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body["suggestions"] == []
    assert body["substrate_summary"]["episodes_used"] == 0
    mock_llm.assert_not_called()


@pytest.mark.django_db
def test_endpoint_populated_universe_returns_suggestions(
    client, universe_with_episodes,
):
    faked_payload = _mock_openai_response(
        ["one direction", "another direction", "a third direction"]
    ).output_text
    with patch(
        "apps.universe.services.next_episode_suggestions._call_openai",
        return_value=(faked_payload, 500, 60),
    ):
        resp = client.get(
            f"/api/universes/{universe_with_episodes.id}/next-episode-suggestions/"
        )
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert len(body["suggestions"]) == 3
    assert body["suggestions"][0]["text"] == "one direction"


@pytest.mark.django_db
def test_endpoint_refresh_query_param_bypasses_cache(
    client, universe_with_episodes,
):
    faked_payload = _mock_openai_response(["a", "b", "c"]).output_text
    with patch(
        "apps.universe.services.next_episode_suggestions._call_openai",
        return_value=(faked_payload, 500, 60),
    ) as mock_llm:
        # First call — miss.
        r1 = client.get(
            f"/api/universes/{universe_with_episodes.id}/next-episode-suggestions/"
        )
        # Second call — hit.
        r2 = client.get(
            f"/api/universes/{universe_with_episodes.id}/next-episode-suggestions/"
        )
        # Third with refresh — miss.
        r3 = client.get(
            f"/api/universes/{universe_with_episodes.id}/next-episode-suggestions/?refresh=true"
        )

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200
    assert r1.json()["cache"]["hit"] is False
    assert r2.json()["cache"]["hit"] is True
    assert r3.json()["cache"]["hit"] is False
    assert mock_llm.call_count == 2  # first + refresh


@pytest.mark.django_db
def test_endpoint_upstream_error_returns_502(
    client, universe_with_episodes,
):
    from apps.universe.services import NextEpisodeSuggestionUpstreamError

    with patch(
        "apps.universe.services.next_episode_suggestions._call_openai",
        side_effect=NextEpisodeSuggestionUpstreamError("upstream boom"),
    ):
        resp = client.get(
            f"/api/universes/{universe_with_episodes.id}/next-episode-suggestions/"
        )
    assert resp.status_code == 502, resp.content
    body = resp.json()
    assert body["error"] == "suggestion_provider_unavailable"
    # Operator-facing detail — no implementation vocabulary.
    assert "shortly" in body["detail"].lower() or "try again" in body["detail"].lower()


@pytest.mark.django_db
def test_endpoint_non_member_gets_404(
    stranger_client, universe_with_episodes,
):
    """Stranger has no membership in the Universe's workspace →
    Universe queryset excludes it → ``get_object`` raises 404.
    Same pattern as UniverseViewSet.destroy / retrieve."""
    resp = stranger_client.get(
        f"/api/universes/{universe_with_episodes.id}/next-episode-suggestions/"
    )
    assert resp.status_code == 404, resp.content


@pytest.mark.django_db
def test_endpoint_archived_universe_returns_404(
    client, universe_with_episodes,
):
    """Archived Universe is filtered by default queryset."""
    universe_with_episodes.archived_at = timezone.now()
    universe_with_episodes.save()
    resp = client.get(
        f"/api/universes/{universe_with_episodes.id}/next-episode-suggestions/"
    )
    assert resp.status_code == 404, resp.content


@pytest.mark.django_db
def test_endpoint_n_query_param_respected(client, universe_with_episodes):
    faked_payload = _mock_openai_response(
        ["one", "two", "three", "four", "five"]
    ).output_text
    with patch(
        "apps.universe.services.next_episode_suggestions._call_openai",
        return_value=(faked_payload, 500, 60),
    ):
        resp = client.get(
            f"/api/universes/{universe_with_episodes.id}/next-episode-suggestions/?n=2"
        )
    assert resp.status_code == 200
    assert len(resp.json()["suggestions"]) == 2


@pytest.mark.django_db
def test_endpoint_n_query_param_out_of_range_falls_back_to_default(
    client, universe_with_episodes,
):
    """n=99 is silently clamped to default (3). Non-int strings
    are silently ignored. Neither returns a 400 — a stray query
    param must not break the suggestions surface."""
    faked_payload = _mock_openai_response(
        ["one", "two", "three", "four", "five"]
    ).output_text
    with patch(
        "apps.universe.services.next_episode_suggestions._call_openai",
        return_value=(faked_payload, 500, 60),
    ):
        r1 = client.get(
            f"/api/universes/{universe_with_episodes.id}/next-episode-suggestions/?n=99"
        )
        r2 = client.get(
            f"/api/universes/{universe_with_episodes.id}/next-episode-suggestions/?n=banana&refresh=true"
        )
    assert r1.status_code == 200
    assert len(r1.json()["suggestions"]) == 3
    assert r2.status_code == 200
    assert len(r2.json()["suggestions"]) == 3


@pytest.mark.django_db
def test_endpoint_never_leaks_implementation_vocabulary_in_operator_facing_fields(
    client, universe_with_episodes,
):
    """Load-bearing UX invariant (SESSION 280 §56 HARD UX
    CONSTRAINT): operator-facing strings must not expose
    substrate vocabulary (memory kind names, retrieval, latent
    thread, etc.). This test guards the SERVICE-CONTROLLED
    strings (error detail, prompt-relevant labels the LLM sees
    are internal; only the operator-facing HTTP response body is
    checked)."""
    from apps.universe.services import NextEpisodeSuggestionUpstreamError

    with patch(
        "apps.universe.services.next_episode_suggestions._call_openai",
        side_effect=NextEpisodeSuggestionUpstreamError("bad"),
    ):
        resp = client.get(
            f"/api/universes/{universe_with_episodes.id}/next-episode-suggestions/"
        )
    body = resp.json()
    banned = {
        "narrativememorykind",
        "promise",
        "dialogue_callback",
        "retrieval",
        "substrate",
        "provenance",
        "memory_id",
        "top_k",
        "latent thread",
        "semantic continuation",
    }
    detail_lower = body["detail"].lower()
    for word in banned:
        assert word not in detail_lower, (
            f"operator-facing detail leaked implementation "
            f"vocabulary: {word!r}"
        )
