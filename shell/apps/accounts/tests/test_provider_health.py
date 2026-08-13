"""Tests for ``GET /api/health/providers/`` (P1 slice 2.2).

Truthfulness invariants under test:

* ``configured=true`` does not imply ``reachable=true``.
* ``mode="real"`` does not imply any provider call succeeded.
* A reachable media-engine process does NOT imply that any
  downstream provider (Runway, OpenAI, image gen, realtime) is
  reachable. Provider ``reachable`` stays ``null`` unless that
  specific provider was probed.
* Media-engine unreachable produces a partial-but-useful report
  with ``status="degraded"`` (not ``"unavailable"``) — shell-side
  providers + engine-bridge remain truthful.
* No secrets, no key lengths, no key prefixes, no token previews,
  and no provider exception bodies appear anywhere in the response.
* ``image_gen`` accurately exposes its ``runway_mock`` derivation
  in ``detail`` and never fabricates an independent mock flag.
* ``engine_bridge`` resolver dry-runs only; ``test_ping`` is not
  invoked from this endpoint.
* Public response omits ``media_engine.base_url`` — internal
  topology is not disclosed to authenticated clients.
"""
from __future__ import annotations

import json
import os
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace
from character_os.clients.media_engine import HealthStatus, MediaEngineError

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------- test doubles -------------------------------------------


class _FakeClientCtx:
    """Context-manager shape matching ``MediaEngineClient(...)`` usage."""

    def __init__(self, health: HealthStatus | None = None,
                 error: Exception | None = None):
        self._health = health
        self._error = error

    def __enter__(self) -> "_FakeClientCtx":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def health_check(self) -> HealthStatus:
        if self._error is not None:
            raise self._error
        assert self._health is not None
        return self._health


def _install_fake_client(monkeypatch, *, health=None, error=None) -> None:
    """Replace ``MediaEngineClient`` in the provider_status module."""
    def factory(*_a, **_kw):
        return _FakeClientCtx(health=health, error=error)

    monkeypatch.setattr(
        "character_os.clients.media_engine.MediaEngineClient",
        factory,
    )


def _mock_health(*, runway_mock=True, openai_mock=True, image_gen_mock=True,
                 llm_provider="openai", llm_model="gpt-4o-mini",
                 status="ok") -> HealthStatus:
    return HealthStatus(
        status=status,
        service="adspark-studio",
        openai_mock=openai_mock,
        runway_mock=runway_mock,
        image_gen_mock=image_gen_mock,
        extras={"llm_provider": llm_provider, "llm_model": llm_model,
                "any_mock": openai_mock or runway_mock},
    )


def _clear_env(monkeypatch) -> None:
    for name in (
        "OPENAI_API_KEY", "RUNWAY_API_KEY", "STABILITY_API_KEY",
        "ELEVENLABS_API_KEY", "SERPER_API_KEY",
        "UDB_PA_API_URL", "UDB_PA_API_TOKEN",
        "EMBEDDING_FORCE_MOCK", "RENDER_SCRIPT_FORCE_MOCK",
        "CONVERSATION_REPLY_FORCE_MOCK", "REALTIME_MEMORY_FORCE_MOCK",
        "TRANSCRIPT_MINER_FORCE_MOCK", "SERPER_FORCE_MOCK",
        "VOICEOVER_TTS_FORCE_MOCK", "VOICEOVER_TTS_DEFAULT_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)


def _make_user(email: str = "op@example.com") -> User:
    return User.objects.create_user(email=email, password="x")


# ---------- auth ----------------------------------------------------


def test_endpoint_requires_authentication():
    client = APIClient()
    resp = client.get("/api/health/providers/")
    assert resp.status_code in (http.HTTP_401_UNAUTHORIZED,
                                http.HTTP_403_FORBIDDEN)


# ---------- happy path: media-engine reachable, all mock ------------


def test_media_engine_reachable_all_mock(monkeypatch):
    _clear_env(monkeypatch)
    _install_fake_client(monkeypatch, health=_mock_health(
        runway_mock=True, openai_mock=True, image_gen_mock=True,
    ))
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)

    resp = client.get("/api/health/providers/")
    assert resp.status_code == http.HTTP_200_OK, resp.data

    body = resp.data
    assert body["media_engine"]["reachable"] is True
    assert body["providers"]["runway"]["mode"] == "mock"
    assert body["providers"]["runway"]["configured"] is False
    # A reachable media-engine does NOT imply Runway is reachable.
    assert body["providers"]["runway"]["reachable"] is None
    assert body["providers"]["runway"]["source"] == "media_engine_health"
    # Detail names both facts: media-engine reachable, provider not probed.
    assert "not probed" in (body["providers"]["runway"]["detail"] or "")

    # image_gen must expose its derivation from runway_mock.
    ig = body["providers"]["image_gen"]
    assert ig["mode"] == "mock"
    assert ig["reachable"] is None
    assert ig["detail"] is not None
    assert "runway_mock" in ig["detail"]

    # openai_shell with no key and no force-mock is unavailable.
    os_row = body["providers"]["openai_shell"]
    assert os_row["mode"] == "unavailable"
    assert os_row["configured"] is False
    assert "OPENAI_API_KEY" in (os_row["detail"] or "")

    # top-level status: degraded because ≥1 provider is unavailable.
    assert body["status"] == "degraded"


# ---------- media-engine reachable, real-mode -----------------------


def test_media_engine_real_mode_semantics(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    monkeypatch.setenv("STABILITY_API_KEY", "fake-key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-key")
    monkeypatch.setenv("SERPER_API_KEY", "fake-key")
    monkeypatch.setenv("UDB_PA_API_TOKEN", "fake-token")

    _install_fake_client(monkeypatch, health=_mock_health(
        runway_mock=False, openai_mock=False, image_gen_mock=False,
    ))
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)

    resp = client.get("/api/health/providers/")
    assert resp.status_code == http.HTTP_200_OK

    body = resp.data
    assert body["status"] == "ok"
    assert body["providers"]["runway"]["mode"] == "real"
    assert body["providers"]["runway"]["configured"] is True
    assert body["providers"]["openai_shell"]["mode"] == "real"
    assert body["providers"]["serper"]["mode"] == "real"
    assert body["providers"]["stability"]["mode"] == "real"
    # engine_bridge with only env fallback: mode=real, source=env_fallback.
    assert body["providers"]["engine_bridge"]["mode"] == "real"
    assert body["providers"]["engine_bridge"]["source"] == "env_fallback"

    # Real adapter selection does NOT imply the provider was probed.
    # Every provider row returns reachable=null in v1 — no provider-
    # specific probes are wired.
    for name in ("runway", "image_gen", "llm_provider", "realtime",
                 "openai_shell", "stability", "elevenlabs", "serper",
                 "engine_bridge"):
        assert body["providers"][name]["reachable"] is None, name


# ---------- media-engine unreachable degrades gracefully ------------


def test_media_engine_unreachable_degrades(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("SERPER_API_KEY", "fake-key")  # keep shell rows truthful
    _install_fake_client(monkeypatch,
                         error=MediaEngineError("connection refused"))
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)

    resp = client.get("/api/health/providers/")
    # Payload degrades — endpoint itself still returns 200.
    assert resp.status_code == http.HTTP_200_OK

    body = resp.data
    # Top-level status is "degraded" — the report was constructed
    # meaningfully (shell + bridge rows are truthful), just not fully.
    # "unavailable" is reserved for cases where the report itself
    # cannot be built.
    assert body["status"] == "degraded"
    assert body["media_engine"]["reachable"] is False
    assert body["media_engine"]["detail"] is not None

    # Runway/image_gen/llm/realtime become unknown when media-engine
    # is unreachable — they can't be resolved locally.
    for name in ("runway", "image_gen", "llm_provider", "realtime"):
        assert body["providers"][name]["mode"] == "unknown"
        assert body["providers"][name]["reachable"] is None
        assert body["providers"][name]["source"] == "none"

    # Shell-side providers stay truthful: serper key was set, so
    # it remains mode=real regardless of media-engine state.
    assert body["providers"]["serper"]["mode"] == "real"
    assert body["providers"]["serper"]["reachable"] is None


def test_media_engine_health_does_not_imply_provider_reachability(monkeypatch):
    """Regression test for the semantic invariant added SESSION 219.

    A successful media-engine ``/health`` proves the media-engine
    process is reachable. It does NOT prove that Runway, OpenAI,
    image gen, or the realtime provider is reachable. Every
    provider row must return ``reachable=None`` in v1 because no
    provider-specific probes are wired.
    """
    _clear_env(monkeypatch)
    # Every credential set, media-engine fully reachable, real mode.
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    monkeypatch.setenv("RUNWAY_API_KEY", "fake-key")
    monkeypatch.setenv("STABILITY_API_KEY", "fake-key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-key")
    monkeypatch.setenv("SERPER_API_KEY", "fake-key")
    monkeypatch.setenv("UDB_PA_API_TOKEN", "fake-token")
    _install_fake_client(monkeypatch, health=_mock_health(
        runway_mock=False, openai_mock=False, image_gen_mock=False,
        llm_provider="openai",
    ))
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)
    resp = client.get("/api/health/providers/")
    assert resp.status_code == http.HTTP_200_OK

    body = resp.data
    assert body["media_engine"]["reachable"] is True

    # THE INVARIANT: no provider row may set reachable=true without a
    # provider-specific probe having occurred. v1 wires no such probes
    # for the third-party providers (Runway / OpenAI / image gen /
    # realtime / etc.) — every one of those rows is null.
    #
    # F-07 (SESSION 224) introduced ``celery_worker`` which IS its own
    # provider-specific probe (broker roundtrip). Its truthful
    # reachable value is True / False / None depending on whether the
    # test env has a broker + workers. It is EXEMPT from this test
    # precisely because it does not overclaim — it has its own probe.
    THIRD_PARTY_ROWS = set(body["providers"].keys()) - {"celery_worker"}
    for name in THIRD_PARTY_ROWS:
        row = body["providers"][name]
        assert row["reachable"] is None, (
            f"{name} claims reachable={row['reachable']!r} without a "
            f"provider-specific probe — this overclaims. media-engine "
            f"/health only reports configuration."
        )


# ---------- media-engine malformed health payload -------------------


def test_media_engine_malformed_response_treated_as_unreachable(monkeypatch):
    _clear_env(monkeypatch)
    _install_fake_client(monkeypatch,
                         error=MediaEngineError(
                             "health response not in expected shape: {'foo': 'bar'}"))
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)

    resp = client.get("/api/health/providers/")
    assert resp.status_code == http.HTTP_200_OK
    body = resp.data
    assert body["media_engine"]["reachable"] is False


# ---------- ollama LLM path -----------------------------------------


def test_llm_provider_reports_ollama_when_selected(monkeypatch):
    _clear_env(monkeypatch)
    _install_fake_client(monkeypatch, health=_mock_health(
        openai_mock=False, llm_provider="ollama", llm_model="llama3.1:8b",
    ))
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)

    resp = client.get("/api/health/providers/")
    llm = resp.data["providers"]["llm_provider"]
    assert llm["mode"] == "real"
    assert llm["configured"] is True
    assert llm["reachable"] is None  # ollama not probed either
    assert "ollama" in (llm["detail"] or "")
    assert "llama3.1:8b" in (llm["detail"] or "")


# ---------- serper unavailable when key unset and no force-mock -----


def test_serper_unavailable_when_key_missing_and_no_force_mock(monkeypatch):
    _clear_env(monkeypatch)
    _install_fake_client(monkeypatch, health=_mock_health(runway_mock=True))
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)

    resp = client.get("/api/health/providers/")
    serper = resp.data["providers"]["serper"]
    assert serper["mode"] == "unavailable"
    assert serper["configured"] is False
    assert "SERPER_API_KEY" in (serper["detail"] or "")


def test_serper_mock_when_force_mock_set(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("SERPER_FORCE_MOCK", "1")
    _install_fake_client(monkeypatch, health=_mock_health(runway_mock=True))
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)

    resp = client.get("/api/health/providers/")
    serper = resp.data["providers"]["serper"]
    assert serper["mode"] == "mock"


# ---------- engine_bridge with workspace ---------------------------


def test_engine_bridge_reports_none_for_starter_workspace(monkeypatch):
    """Starter tier resolves to None regardless of env fallback."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("UDB_PA_API_TOKEN", "fake-token")
    _install_fake_client(monkeypatch, health=_mock_health())
    user = _make_user()
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    # starter tier is the default; no Subscription row needed.

    client = APIClient(); client.force_authenticate(user=user)
    resp = client.get(f"/api/health/providers/?workspace={ws.id}")
    bridge = resp.data["providers"]["engine_bridge"]
    assert bridge["mode"] == "unavailable"
    assert bridge["source"] == "none"
    assert "below Pro" in (bridge["detail"] or "")


def test_engine_bridge_reports_env_fallback_without_workspace(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("UDB_PA_API_TOKEN", "fake-token")
    _install_fake_client(monkeypatch, health=_mock_health())
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)

    resp = client.get("/api/health/providers/")
    bridge = resp.data["providers"]["engine_bridge"]
    assert bridge["mode"] == "real"
    assert bridge["source"] == "env_fallback"
    assert bridge["reachable"] is None  # test_ping NOT invoked


def test_engine_bridge_unavailable_without_workspace_or_env(monkeypatch):
    _clear_env(monkeypatch)
    _install_fake_client(monkeypatch, health=_mock_health())
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)

    resp = client.get("/api/health/providers/")
    bridge = resp.data["providers"]["engine_bridge"]
    assert bridge["mode"] == "unavailable"
    assert bridge["source"] == "none"


def test_workspace_param_rejects_non_member(monkeypatch):
    _clear_env(monkeypatch)
    _install_fake_client(monkeypatch, health=_mock_health())
    user = _make_user("me@example.com")
    other = _make_user("other@example.com")
    other_ws = Workspace.objects.filter(owner=other).first()
    assert other_ws is not None

    client = APIClient(); client.force_authenticate(user=user)
    resp = client.get(f"/api/health/providers/?workspace={other_ws.id}")
    assert resp.status_code == http.HTTP_403_FORBIDDEN


def test_workspace_param_404_for_unknown_workspace(monkeypatch):
    _clear_env(monkeypatch)
    _install_fake_client(monkeypatch, health=_mock_health())
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)
    # Well-formed UUID that no workspace has.
    resp = client.get(
        "/api/health/providers/?workspace=00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == http.HTTP_404_NOT_FOUND

    # Malformed UUID → also 404 (view collapses lookup-shape errors).
    resp2 = client.get("/api/health/providers/?workspace=not-a-uuid")
    assert resp2.status_code == http.HTTP_404_NOT_FOUND


# ---------- secret redaction ---------------------------------------


def test_response_contains_no_secrets(monkeypatch):
    """The response must not include env values, key lengths, key
    prefixes, or provider exception bodies verbatim."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-SECRETVALUE-abc123-xyz789")
    monkeypatch.setenv("RUNWAY_API_KEY", "runway-SECRETVALUE-abc123")
    monkeypatch.setenv("STABILITY_API_KEY", "stab-SECRETVALUE-def456")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el-SECRETVALUE-ghi789")
    monkeypatch.setenv("SERPER_API_KEY", "srp-SECRETVALUE-jkl012")
    monkeypatch.setenv("UDB_PA_API_URL", "http://SECRETVALUE.example/pa")
    monkeypatch.setenv("UDB_PA_API_TOKEN", "udb-SECRETVALUE-mno345")

    _install_fake_client(monkeypatch, health=_mock_health(
        runway_mock=False, openai_mock=False,
    ))
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)
    resp = client.get("/api/health/providers/")
    body = json.dumps(resp.data)

    # Full env values MUST NOT appear.
    assert "SECRETVALUE" not in body
    # No 4-char prefix leak from typical key shapes.
    for prefix in ("sk-", "srp-", "udb-", "el-", "stab-", "runway-"):
        assert prefix not in body, f"leaked prefix {prefix!r}"


def test_response_does_not_expose_env_var_lengths(monkeypatch):
    """No field on any provider row is a raw integer that could be
    an env-var length. (Redaction is by absence — no length is
    reported anywhere.)"""
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "abcdefghijklmnop")  # len=16
    _install_fake_client(monkeypatch, health=_mock_health(openai_mock=False))
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)
    resp = client.get("/api/health/providers/")
    for row in resp.data["providers"].values():
        for value in row.values():
            if isinstance(value, int) and not isinstance(value, bool):
                pytest.fail(f"integer value in provider row could leak length: {value!r}")


def test_response_shape_is_stable(monkeypatch):
    """Every provider row exposes the same 5 fields; every provider
    is present. This is the contract the SPA pill (2.3) will consume."""
    _clear_env(monkeypatch)
    _install_fake_client(monkeypatch, health=_mock_health())
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)
    resp = client.get("/api/health/providers/")
    body = resp.data

    assert set(body.keys()) == {"status", "generated_at", "media_engine", "providers"}
    # Internal topology (base_url) is deliberately NOT in the public
    # response. Only reachable + detail are exposed.
    assert set(body["media_engine"].keys()) == {"reachable", "detail"}

    expected_providers = {
        "runway", "image_gen", "llm_provider", "realtime",
        "openai_shell", "stability", "elevenlabs", "serper",
        "engine_bridge",
        # SESSION 224 F-07 — Celery worker liveness surfaced so a
        # dead worker is distinguishable from live generation.
        "celery_worker",
    }
    assert set(body["providers"].keys()) == expected_providers

    for name, row in body["providers"].items():
        assert set(row.keys()) == {"configured", "mode", "reachable",
                                    "source", "detail"}, name
        assert row["mode"] in {"mock", "real", "unavailable", "unknown"}
        assert row["reachable"] in {True, False, None}
        assert row["source"] in {
            "media_engine_health", "shell_env",
            "engine_connection_row", "env_fallback", "none",
        }


# ---------- SESSION 224 F-07: celery worker liveness ---------------


def _patch_celery_ping(monkeypatch, *, response, raises=None):
    """Replace ``character_os.celery.app.control.ping`` with a stub.

    ``response`` is the return value when ping is called (list-of-dicts
    like Celery's real shape, or ``None`` / ``[]`` when no workers).
    ``raises`` is an exception instance to raise instead — models
    broker-unreachable failure modes.
    """
    from character_os import celery as celery_module

    class _StubControl:
        def ping(self, timeout=None):
            if raises is not None:
                raise raises
            return response

    monkeypatch.setattr(celery_module.app, "control", _StubControl())


def test_celery_worker_row_present_when_worker_alive(monkeypatch):
    _clear_env(monkeypatch)
    _install_fake_client(monkeypatch, health=_mock_health())
    _patch_celery_ping(
        monkeypatch,
        response=[{"celery@testhost": {"ok": "pong"}}],
    )
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)
    resp = client.get("/api/health/providers/")
    row = resp.data["providers"]["celery_worker"]
    assert row["configured"] is True
    assert row["mode"] == "real"
    assert row["reachable"] is True
    assert row["source"] == "shell_env"
    assert "celery@testhost" in (row["detail"] or "")


def test_celery_worker_row_flags_dead_worker(monkeypatch):
    """Broker up but no worker responded — the F-07 originating scenario.

    Contract: mode='unavailable', reachable=False, detail explains
    the fix (start a worker). Top-level status must degrade so the
    SPA pill turns red — otherwise the user still can't tell the
    difference between "generating" and "silently queued."
    """
    _clear_env(monkeypatch)
    _install_fake_client(monkeypatch, health=_mock_health())
    _patch_celery_ping(monkeypatch, response=[])
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)
    resp = client.get("/api/health/providers/")
    body = resp.data
    row = body["providers"]["celery_worker"]
    assert row["configured"] is True
    assert row["mode"] == "unavailable"
    assert row["reachable"] is False
    assert "no workers responded" in (row["detail"] or "")
    # Top-level must degrade — this is load-bearing for the SPA pill.
    assert body["status"] == "degraded"


def test_celery_worker_row_flags_broker_unreachable(monkeypatch):
    """Redis (or whatever broker) itself unreachable. Distinguished
    from the dead-worker case by ``detail`` — same mode/reachable so
    the SPA doesn't have to fork logic."""
    _clear_env(monkeypatch)
    _install_fake_client(monkeypatch, health=_mock_health())
    _patch_celery_ping(
        monkeypatch, response=None,
        raises=ConnectionError("connection refused"),
    )
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)
    resp = client.get("/api/health/providers/")
    row = resp.data["providers"]["celery_worker"]
    assert row["mode"] == "unavailable"
    assert row["reachable"] is False
    assert "broker unreachable" in (row["detail"] or "")


def test_media_engine_base_url_not_in_public_response(monkeypatch):
    """Explicit regression: internal service topology stays out."""
    _clear_env(monkeypatch)
    _install_fake_client(monkeypatch, health=_mock_health())
    user = _make_user()
    client = APIClient(); client.force_authenticate(user=user)
    resp = client.get("/api/health/providers/")
    body = json.dumps(resp.data)
    assert "base_url" not in body
    # And, defensively, the actual settings value must not appear either.
    from django.conf import settings as dj_settings
    if getattr(dj_settings, "MEDIA_ENGINE_BASE_URL", None):
        assert dj_settings.MEDIA_ENGINE_BASE_URL not in body
