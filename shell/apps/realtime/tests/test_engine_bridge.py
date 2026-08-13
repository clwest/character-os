"""EB.2 tests — `resolve_engine_connection` + bridge-tool refactor.

Twelve tests per the ENGINE_BRIDGE_V1 scope-lock plan:

Resolver layer (1-6, 11-12):
  1. DB row resolves when one exists.
  2. Env-var fallback when no DB row + env set.
  3. None when no DB row + no env.
  4. None when row exists but disabled + no env.
  5. None for Starter tier even with a row.
  6. Cross-workspace isolation — workspace A never resolves to B's row.
 11. ResolvedEngine.source == "env" for env path.
 12. ResolvedEngine.source == "db" for DB path.

Tool-integration layer (7-10):
  7. consult_engine reads from resolver + hits resolved URL.
  8. query_spider_data same shape.
  9. agent_consult same shape.
 10. Bridge tools return configured-but-unreachable when resolver = None.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.billing.models import Subscription
from apps.realtime.engine_bridge import (
    ENV_DEFAULT_BASE_URL,
    ResolvedEngine,
    resolve_engine_connection,
)
from apps.realtime.models import EngineConnection, RealtimeSession
from apps.realtime.tools.agent_consult import executor as agent_consult_exec
from apps.realtime.tools.consult_engine import executor as consult_engine_exec
from apps.realtime.tools.query_spider_data import (
    executor as query_spider_data_exec,
)
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_workspace(email: str, *, tier: str = "pro") -> Workspace:
    """Create a workspace for a fresh user and set its tier.

    Default is Pro because the resolver gates Starter to None;
    most tests need Pro to exercise the live paths.
    """
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    sub, _ = Subscription.objects.get_or_create(
        workspace=ws,
        defaults={"tier": tier, "status": Subscription.Status.ACTIVE},
    )
    sub.tier = tier
    sub.save()
    return ws


def _make_teammate(ws: Workspace) -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name="Sasha",
        runway_avatar_id="av_test",
        portrait_path="https://fake/p.png",
        business_brief="brief",
    )


def _make_session(ws: Workspace, sp: Teammate) -> RealtimeSession:
    return RealtimeSession.objects.create(
        workspace=ws,
        spokesperson=sp,
        status=RealtimeSession.Status.READY,
        provider_session_id="rt_x",
    )


def _make_connection(
    ws: Workspace,
    *,
    url: str = "https://eng.example/",
    token: str = "tok_db",
    enabled: bool = True,
) -> EngineConnection:
    return EngineConnection.objects.create(
        workspace=ws,
        engine_kind=EngineConnection.Kind.UDB_PA,
        engine_url=url,
        engine_token=token,
        enabled=enabled,
    )


@pytest.fixture
def clean_env(monkeypatch):
    """Clear UDB_PA_* env vars so each test controls its own state."""
    monkeypatch.delenv("UDB_PA_API_URL", raising=False)
    monkeypatch.delenv("UDB_PA_API_TOKEN", raising=False)
    yield monkeypatch


# ---------------------------------------------------------------------------
# resolver tests
# ---------------------------------------------------------------------------


def test_resolver_returns_db_row_when_present(clean_env):
    """1. DB row resolves when one exists. Trailing slash on the
    stored URL is stripped — bridge tools compose paths and would
    double-slash otherwise."""
    ws = _make_workspace("a@x.test")
    _make_connection(ws, url="https://eng.example/", token="tok_db")

    resolved = resolve_engine_connection(ws)

    assert resolved is not None
    assert resolved.url == "https://eng.example"
    assert resolved.token == "tok_db"
    assert resolved.kind == EngineConnection.Kind.UDB_PA
    assert resolved.source == "db"
    assert resolved.enabled is True


def test_resolver_falls_back_to_env_when_no_db_row(clean_env):
    """2. Env-var fallback path. With no DB row but env vars set,
    the resolver returns the env values with ``source == "env"``."""
    ws = _make_workspace("b@x.test")
    clean_env.setenv("UDB_PA_API_URL", "http://localhost:9000/")
    clean_env.setenv("UDB_PA_API_TOKEN", "tok_env")

    resolved = resolve_engine_connection(ws)

    assert resolved is not None
    assert resolved.url == "http://localhost:9000"
    assert resolved.token == "tok_env"
    assert resolved.source == "env"


def test_resolver_returns_none_when_no_row_and_no_env(clean_env):
    """3. None when neither source is configured. Bridge tools
    translate this into ``configured-but-unreachable``."""
    ws = _make_workspace("c@x.test")

    assert resolve_engine_connection(ws) is None


def test_resolver_skips_disabled_row_and_no_env(clean_env):
    """4. Disabled rows fail closed (rule 5). With env unset, the
    workspace resolves to None even though an EngineConnection
    row exists."""
    ws = _make_workspace("d@x.test")
    _make_connection(ws, enabled=False)

    assert resolve_engine_connection(ws) is None


def test_resolver_returns_none_for_starter_even_with_row(clean_env):
    """5. Pro+ tier gate at the resolver (rule 8). A Starter
    workspace with a stray EngineConnection row still resolves to
    None — the gate lives in the resolver, not just the SPA."""
    ws = _make_workspace("e@x.test", tier="starter")
    _make_connection(ws)

    assert resolve_engine_connection(ws) is None


def test_resolver_is_workspace_scoped(clean_env):
    """6. Cross-workspace isolation (rule 1). Workspace A's
    resolver never sees workspace B's row."""
    ws_a = _make_workspace("a-iso@x.test")
    ws_b = _make_workspace("b-iso@x.test")
    _make_connection(ws_b, url="https://b.example", token="tok_b")

    resolved = resolve_engine_connection(ws_a)
    assert resolved is None

    resolved_b = resolve_engine_connection(ws_b)
    assert resolved_b is not None
    assert resolved_b.token == "tok_b"


def test_resolver_env_uses_default_base_url_when_only_token_set(clean_env):
    """11 (companion to test 2). When UDB_PA_API_TOKEN is set but
    UDB_PA_API_URL is not, the resolver falls back to
    ``ENV_DEFAULT_BASE_URL`` (port 8020 — Q-eb-5 normalises this
    from the inconsistent 8000/8020 split across the three tools).

    Also implicitly proves source == "env" — this is the env path."""
    ws = _make_workspace("f@x.test")
    clean_env.setenv("UDB_PA_API_TOKEN", "tok_default_url")

    resolved = resolve_engine_connection(ws)

    assert resolved is not None
    assert resolved.url == ENV_DEFAULT_BASE_URL
    assert resolved.source == "env"


def test_resolver_db_source_marker(clean_env):
    """12. ResolvedEngine.source == "db" for the DB-row path.
    Companion to test 1; lives as a discrete assertion so a
    regression that swaps the marker fails this test specifically."""
    ws = _make_workspace("g@x.test")
    _make_connection(ws)

    resolved = resolve_engine_connection(ws)

    assert resolved is not None
    assert resolved.source == "db"


def test_resolver_prefers_db_row_over_env(clean_env):
    """Defense in depth — the DB row wins over the env fallback
    when both are configured. EB.2 will live alongside the env
    fallback for some time; this guarantees the deprecation path
    behaves consistently."""
    ws = _make_workspace("h@x.test")
    _make_connection(ws, url="https://db.example", token="tok_db")
    clean_env.setenv("UDB_PA_API_URL", "https://env.example")
    clean_env.setenv("UDB_PA_API_TOKEN", "tok_env")

    resolved = resolve_engine_connection(ws)

    assert resolved is not None
    assert resolved.source == "db"
    assert resolved.url == "https://db.example"
    assert resolved.token == "tok_db"


# ---------------------------------------------------------------------------
# bridge-tool integration tests
# ---------------------------------------------------------------------------


def _make_pa_chat_response(content: str = "answer", task_id: str = "t_1"):
    """Build a (post-response, status-response) pair the urlopen
    mock cycles through. Mirrors the sibling project's /api/pa/chat/ +
    /api/pa/chat/status/<task_id>/ shape."""
    post_resp = {"success": True, "task_id": task_id}
    status_resp = {
        "success": True,
        "status": "completed",
        "content": content,
        "conversation_id": "conv_1",
    }
    return post_resp, status_resp


def _patch_urlopen(post_resp, status_resp, captured_urls: list[str]):
    """Patch urllib.request.urlopen to record URLs called and
    return the canned POST + status responses."""

    def _fake_urlopen(req, timeout=None):  # noqa: ARG001
        captured_urls.append(req.full_url)
        body = post_resp if "status/" not in req.full_url else status_resp
        ctx = MagicMock()
        ctx.read.return_value = json.dumps(body).encode("utf-8")
        ctx.status = 200
        ctx.__enter__ = lambda self: self
        ctx.__exit__ = lambda *a: False
        return ctx

    return patch("urllib.request.urlopen", side_effect=_fake_urlopen)


def test_consult_engine_uses_resolved_url(clean_env):
    """7. consult_engine resolves via the new path and POSTs to
    the resolved URL (not the env default)."""
    ws = _make_workspace("ce@x.test")
    sp = _make_teammate(ws)
    session = _make_session(ws, sp)
    _make_connection(ws, url="https://customer-x.example", token="tok_x")

    captured: list[str] = []
    post_r, status_r = _make_pa_chat_response()
    with _patch_urlopen(post_r, status_r, captured), patch(
        "apps.realtime.tools.consult_engine.time.sleep"
    ):
        result = consult_engine_exec(session, {"question": "hi"})

    assert result["event"] == "engine_consulted"
    assert "answer" in result
    assert any("https://customer-x.example" in u for u in captured)


def test_query_spider_data_uses_resolved_url(clean_env):
    """8. query_spider_data same shape."""
    ws = _make_workspace("qs@x.test")
    sp = _make_teammate(ws)
    session = _make_session(ws, sp)
    _make_connection(ws, url="https://customer-y.example", token="tok_y")

    captured: list[str] = []
    post_r, status_r = _make_pa_chat_response()
    with _patch_urlopen(post_r, status_r, captured), patch(
        "apps.realtime.tools.query_spider_data.time.sleep"
    ):
        result = query_spider_data_exec(session, {"topic": "x"})

    assert result["event"] == "spider_queried"
    assert "answer" in result
    assert any("https://customer-y.example" in u for u in captured)


def test_agent_consult_uses_resolved_url(clean_env):
    """9. agent_consult same shape."""
    ws = _make_workspace("ac@x.test")
    sp = _make_teammate(ws)
    session = _make_session(ws, sp)
    _make_connection(ws, url="https://customer-z.example", token="tok_z")

    captured: list[str] = []
    post_r, status_r = _make_pa_chat_response()
    with _patch_urlopen(post_r, status_r, captured), patch(
        "apps.realtime.tools.agent_consult.time.sleep"
    ):
        result = agent_consult_exec(
            session, {"agent_name": "CTOAgent", "question": "x"}
        )

    assert result["event"] == "agent_consulted"
    assert "answer" in result
    assert any("https://customer-z.example" in u for u in captured)


@pytest.mark.parametrize(
    "tool_name,executor,args,event_name",
    [
        ("consult_engine", consult_engine_exec, {"question": "x"}, "engine_consulted"),
        ("query_spider_data", query_spider_data_exec, {"topic": "x"}, "spider_queried"),
        (
            "agent_consult",
            agent_consult_exec,
            {"agent_name": "CTOAgent", "question": "x"},
            "agent_consulted",
        ),
    ],
)
def test_bridge_tools_return_unreachable_when_resolver_none(
    clean_env, tool_name, executor, args, event_name
):
    """10. Bridge tools return the configured-but-unreachable
    error shape when the resolver returns None (no row, no env,
    or Starter tier). engine_url is empty because nothing
    resolved."""
    ws = _make_workspace("none@" + tool_name + ".test", tier="starter")
    sp = _make_teammate(ws)
    session = _make_session(ws, sp)

    result = executor(session, args)

    assert result["event"] == event_name
    assert "error" in result
    assert "not configured" in result["error"].lower()
    assert result["engine_url"] == ""


# ---------------------------------------------------------------------------
# C3 — bridge-answer Asset persistence (S2887 side-step)
# ---------------------------------------------------------------------------


def _empty_pa_chat_response(task_id: str = "t_empty"):
    """A completed engine reply with an empty ``content``. Used to
    verify the empty-answer no-Asset guard."""
    post_resp = {"success": True, "task_id": task_id}
    status_resp = {
        "success": True,
        "status": "completed",
        "content": "",
        "conversation_id": "conv_empty",
    }
    return post_resp, status_resp


def _failed_pa_chat_response(task_id: str = "t_failed"):
    """Engine reports task failure. Used to verify the failure-path
    no-Asset guard."""
    post_resp = {"success": True, "task_id": task_id}
    status_resp = {
        "success": True,
        "status": "failed",
        "error": "engine ran out of tokens",
    }
    return post_resp, status_resp


def test_consult_engine_success_creates_bridge_answer_asset(clean_env):
    """C3 — successful consult_engine call persists the answer as
    ``Asset(role=BRIDGE_ANSWER, asset_type=TRANSCRIPT)``. Return dict
    includes ``asset_id`` so both sync and async dispatch can link it."""
    from apps.compositions.models import Asset, AssetRole, AssetType

    ws = _make_workspace("c3-ce@x.test")
    sp = _make_teammate(ws)
    session = _make_session(ws, sp)
    _make_connection(ws, url="https://engine.example", token="tok")

    captured: list[str] = []
    post_r, status_r = _make_pa_chat_response(content="the answer body")
    with _patch_urlopen(post_r, status_r, captured), patch(
        "apps.realtime.tools.consult_engine.time.sleep"
    ):
        result = consult_engine_exec(session, {"question": "what?"})

    assert "asset_id" in result
    asset = Asset.objects.get(pk=result["asset_id"])
    assert asset.workspace_id == ws.id
    assert asset.role == AssetRole.BRIDGE_ANSWER
    assert asset.asset_type == AssetType.TRANSCRIPT
    assert asset.inline_content == "the answer body"
    assert asset.title.startswith("[consult_engine] ")
    assert asset.source_spec["tool_name"] == "consult_engine"
    assert asset.source_spec["question"] == "what?"
    assert asset.source_spec["engine_url"] == "https://engine.example"
    assert asset.source_spec["conversation_id"] == "conv_1"
    assert asset.cost_micros == 5_000
    assert asset.composition_id is None


def test_query_spider_data_success_creates_bridge_answer_asset(clean_env):
    """C3 — query_spider_data uses ``topic`` as the question surface."""
    from apps.compositions.models import Asset, AssetRole

    ws = _make_workspace("c3-qs@x.test")
    sp = _make_teammate(ws)
    session = _make_session(ws, sp)
    _make_connection(ws, url="https://engine.example", token="tok")

    post_r, status_r = _make_pa_chat_response(content="spider says: 42")
    with _patch_urlopen(post_r, status_r, []), patch(
        "apps.realtime.tools.query_spider_data.time.sleep"
    ):
        result = query_spider_data_exec(session, {"topic": "signals"})

    assert "asset_id" in result
    asset = Asset.objects.get(pk=result["asset_id"])
    assert asset.role == AssetRole.BRIDGE_ANSWER
    assert asset.inline_content == "spider says: 42"
    assert asset.title.startswith("[query_spider_data] ")
    assert asset.source_spec["tool_name"] == "query_spider_data"
    assert asset.source_spec["question"] == "signals"


def test_agent_consult_success_creates_bridge_answer_asset_with_intent(clean_env):
    """C3 — agent_consult records the routed ``agent_name`` in
    ``source_spec.intent`` so the library can filter by agent."""
    from apps.compositions.models import Asset, AssetRole

    ws = _make_workspace("c3-ac@x.test")
    sp = _make_teammate(ws)
    session = _make_session(ws, sp)
    _make_connection(ws, url="https://engine.example", token="tok")

    post_r, status_r = _make_pa_chat_response(content="CTO says: refactor")
    with _patch_urlopen(post_r, status_r, []), patch(
        "apps.realtime.tools.agent_consult.time.sleep"
    ):
        result = agent_consult_exec(
            session, {"agent_name": "CTOAgent", "question": "ship?"}
        )

    assert "asset_id" in result
    asset = Asset.objects.get(pk=result["asset_id"])
    assert asset.role == AssetRole.BRIDGE_ANSWER
    assert asset.source_spec["intent"] == "CTOAgent"
    assert asset.cost_micros == 7_500


@pytest.mark.parametrize(
    "tool_name,executor,args",
    [
        ("consult_engine", consult_engine_exec, {"question": "x"}),
        ("query_spider_data", query_spider_data_exec, {"topic": "x"}),
        (
            "agent_consult",
            agent_consult_exec,
            {"agent_name": "CTOAgent", "question": "x"},
        ),
    ],
)
def test_bridge_tools_no_asset_on_empty_answer(clean_env, tool_name, executor, args):
    """C3 — empty ``content`` from the engine skips Asset creation to
    avoid accreting blank library rows."""
    from apps.compositions.models import Asset

    before = Asset.objects.count()
    ws = _make_workspace(f"c3-empty-{tool_name}@x.test")
    sp = _make_teammate(ws)
    session = _make_session(ws, sp)
    _make_connection(ws, url="https://engine.example", token="tok")

    post_r, status_r = _empty_pa_chat_response()
    with _patch_urlopen(post_r, status_r, []), patch(
        f"apps.realtime.tools.{tool_name}.time.sleep"
    ):
        result = executor(session, args)

    assert "asset_id" not in result
    assert Asset.objects.count() == before


@pytest.mark.parametrize(
    "tool_name,executor,args",
    [
        ("consult_engine", consult_engine_exec, {"question": "x"}),
        ("query_spider_data", query_spider_data_exec, {"topic": "x"}),
        (
            "agent_consult",
            agent_consult_exec,
            {"agent_name": "CTOAgent", "question": "x"},
        ),
    ],
)
def test_bridge_tools_no_asset_on_failure(clean_env, tool_name, executor, args):
    """C3 — engine-side task failure skips Asset creation; no partial
    persistence of a broken answer."""
    from apps.compositions.models import Asset

    before = Asset.objects.count()
    ws = _make_workspace(f"c3-fail-{tool_name}@x.test")
    sp = _make_teammate(ws)
    session = _make_session(ws, sp)
    _make_connection(ws, url="https://engine.example", token="tok")

    post_r, status_r = _failed_pa_chat_response()
    with _patch_urlopen(post_r, status_r, []), patch(
        f"apps.realtime.tools.{tool_name}.time.sleep"
    ):
        result = executor(session, args)

    assert "error" in result
    assert "asset_id" not in result
    assert Asset.objects.count() == before


def test_bridge_answer_title_truncates_long_question(clean_env):
    """C3 — Asset.title CharField(max_length=120). The composed title
    is ``[<tool_name>] <question>``; the question is capped so the
    composed title always fits."""
    from apps.compositions.models import Asset

    ws = _make_workspace("c3-title@x.test")
    sp = _make_teammate(ws)
    session = _make_session(ws, sp)
    _make_connection(ws, url="https://engine.example", token="tok")

    long_q = "q" * 500  # far exceeds any conceivable title
    post_r, status_r = _make_pa_chat_response(content="a")
    with _patch_urlopen(post_r, status_r, []), patch(
        "apps.realtime.tools.consult_engine.time.sleep"
    ):
        result = consult_engine_exec(session, {"question": long_q})

    asset = Asset.objects.get(pk=result["asset_id"])
    assert len(asset.title) <= 120
    assert asset.title.startswith("[consult_engine] ")
    # Full question is preserved in source_spec (title truncation is
    # a rendering concern; provenance shouldn't lose data).
    assert asset.source_spec["question"] == long_q


def test_sync_dispatch_harvests_asset_id_from_result(clean_env):
    """C3 — ``_execute_inline`` mirrors the async wrapper: if the sync
    executor returns ``{asset_id: uuid}``, the invocation's
    ``produced_asset`` FK is linked. Uses a stand-in tool that returns
    a pre-created Asset row so the mechanism is exercised without
    depending on the bridge-tool HTTP path."""
    from apps.compositions.models import Asset, AssetRole, AssetType
    from apps.realtime.dispatch import dispatch_tool
    from apps.realtime.models import RealtimeToolInvocation
    from apps.realtime.tools import _TOOLS, register_tool

    ws = _make_workspace("c3-dispatch@x.test")
    sp = _make_teammate(ws)
    session = _make_session(ws, sp)

    # Precreate the Asset the stand-in tool will point at.
    asset = Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.TRANSCRIPT,
        role=AssetRole.BRIDGE_ANSWER,
        title="[test] harvest",
        inline_content="hi",
        cost_micros=1,
    )

    @register_tool(
        name="_c3_harvest_probe",
        description="stand-in sync tool that returns asset_id for the harvest test",
        cost_micros=1,
        workspace_scoped=True,
        is_async=False,
        tier_required="starter",
    )
    def _executor(session, args):  # noqa: ARG001
        return {"event": "probe", "asset_id": str(asset.id)}

    try:
        result = dispatch_tool(session, "_c3_harvest_probe", {})
        invocation = RealtimeToolInvocation.objects.get(pk=result.invocation_id)
        assert invocation.produced_asset_id == asset.id
    finally:
        # Remove the ad-hoc tool from the registry so it doesn't leak.
        _TOOLS.pop("_c3_harvest_probe", None)
