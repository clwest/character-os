"""V11 tests — style_remix primitive + style_remix_pass starter.

The hackathon shipped Aleph style remix with five named presets
and used them in production. V11 restores the capability under
the V0+ composition architecture. The chunked path (Aleph's ~5s
output cap workaround) is hidden from the primitive — it's
entirely server-side in the media-engine endpoint. From the
composition runtime's perspective, style_remix is just another
CLIP → CLIP synchronous primitive.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Asset,
    AssetType,
    Composition,
    CompositionStatus,
    CompositionStep,
)
from apps.compositions.primitives.mock import PrimitiveError
from apps.compositions.primitives.style_remix import (
    SUPPORTED_STYLE_PRESETS,
    StyleRemixPrimitive,
)
from apps.compositions.starters import style_remix_pass
from apps.compositions.tasks import execute_composition
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    MediaEngineError,
    StyleRemixResult,
)

User = get_user_model()

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.usefixtures("_celery_eager"),
]


@pytest.fixture
def _celery_eager():
    with override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


# ---- helpers --------------------------------------------------------


def _make_workspace(email: str, name: str = "WS") -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws


def _make_spokesperson(ws: Workspace) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name="Sp",
        runway_avatar_id="fake",
        portrait_path="https://fake/p.png",
        business_brief="b",
    )


def _make_clip(
    ws,
    file_path: str = "/data/_assets/clip.mp4",
    duration_ms: int | None = 5000,
    width: int | None = 1280,
    height: int | None = 720,
) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path=file_path, duration_ms=duration_ms,
        width=width, height=height,
        mime_type="video/mp4",
    )


def _comp(ws, sp, *, mock_mode: bool = False) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="t",
        mock_mode=mock_mode,
    )


def _fake_remix(
    output_url: str = "/data/_internal/style_remixes/x.mp4",
    *,
    chunked: bool = False,
    task_ids: list[str] | None = None,
) -> StyleRemixResult:
    return StyleRemixResult(
        output_url=output_url,
        duration_seconds=5.0,
        size_bytes=2048,
        style_preset="noir",
        chunked=chunked,
        task_ids=task_ids if task_ids is not None else ["runway_aleph_xyz"],
        mock_mode=False,
    )


def _patched_client(return_value):
    fake = MagicMock()
    fake.style_remix.return_value = return_value
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm, fake


# ---- StyleRemixPrimitive ------------------------------------------


def test_style_remix_supports_five_hackathon_presets() -> None:
    """SUPPORTED_STYLE_PRESETS must match the hackathon's five
    preset ids exactly — operators who used a preset in
    production keep using the same id under V11."""
    assert SUPPORTED_STYLE_PRESETS == {
        "noir", "anime", "chrome", "watercolor", "cyberpunk",
    }


def test_style_remix_mock_mode_returns_stub_clip() -> None:
    ws = _make_workspace("v11sr1@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    src = _make_clip(ws, duration_ms=8000)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="style_remix",
        params={"style_preset": "anime"},
    )
    r = StyleRemixPrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "source", "asset": src}],
        mock_mode=True,
    )
    assert r.asset_type == AssetType.CLIP
    assert r.extra_source_spec["mock"] is True
    assert r.extra_source_spec["style_preset"] == "anime"
    assert r.extra_source_spec["chunked"] is False
    assert r.duration_ms == src.duration_ms


def test_style_remix_rejects_unknown_preset() -> None:
    ws = _make_workspace("v11sr2@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="style_remix",
        params={"style_preset": "vaporwave"},
    )
    with pytest.raises(PrimitiveError) as exc:
        StyleRemixPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": src}],
            mock_mode=False,
        )
    assert "vaporwave" in str(exc.value)


def test_style_remix_requires_preset_param() -> None:
    ws = _make_workspace("v11sr3@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="style_remix",
        params={},
    )
    with pytest.raises(PrimitiveError):
        StyleRemixPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": src}],
            mock_mode=False,
        )


def test_style_remix_rejects_non_clip_input() -> None:
    ws = _make_workspace("v11sr4@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    audio = Asset.objects.create(
        workspace=ws, asset_type=AssetType.AUDIO,
        file_path="/data/a.mp3",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="style_remix",
        params={"style_preset": "noir"},
    )
    with pytest.raises(PrimitiveError):
        StyleRemixPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": audio}],
            mock_mode=False,
        )


def test_style_remix_real_mode_call_shape() -> None:
    ws = _make_workspace("v11sr5@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws, "/data/source.mp4", duration_ms=5000)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="style_remix",
        params={"style_preset": "noir", "seed": 12345},
    )
    cm, fake = _patched_client(_fake_remix("/data/_internal/style_remixes/noir.mp4"))
    with patch(
        "apps.compositions.primitives.style_remix.MediaEngineClient",
        return_value=cm,
    ):
        r = StyleRemixPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": src}],
            mock_mode=False,
        )
    fake.style_remix.assert_called_once()
    kwargs = fake.style_remix.call_args.kwargs
    assert kwargs["clip_url"] == "/data/source.mp4"
    assert kwargs["style_preset"] == "noir"
    assert kwargs["seed"] == 12345

    assert r.file_path == "/data/_internal/style_remixes/noir.mp4"
    assert r.extra_source_spec["chunked"] is False


def test_style_remix_client_passes_generous_timeout_to_request() -> None:
    """Aleph is the slowest media-engine call: chunked + parallel
    for clips >5.5s, each chunk a separate ~30-60s Runway gen4_aleph
    invocation. The default 60s ``MediaEngineClient.request()``
    timeout fired the SESSION 181 dogfood failure (10s source ->
    2 chunks -> ~3 min wall-clock) before Aleph could respond.
    Regression guard: ``style_remix`` MUST pass a per-call timeout
    override (same pattern as V16 remove_avatar_background).
    """
    from character_os.clients.media_engine import (
        MediaEngineClient,
        StyleRemixResult,
    )

    client = MediaEngineClient()
    captured: dict = {}

    def fake_request(method, path, *, params=None, json=None, timeout=None):
        captured["method"] = method
        captured["path"] = path
        captured["timeout"] = timeout
        return {
            "output_url": "/data/_internal/style_remixes/x.mp4",
            "duration_seconds": 5.0,
            "size_bytes": 1024,
            "style_preset": "noir",
            "chunked": False,
            "task_ids": [],
            "mock_mode": False,
        }

    with patch.object(client, "request", side_effect=fake_request):
        client.style_remix(clip_url="/data/source.mp4", style_preset="noir")

    assert captured["method"] == "POST"
    assert captured["path"] == "/internal/clips/style_remix/"
    assert captured["timeout"] is not None, (
        "style_remix MUST override the default 60s client timeout — "
        "Aleph chunked rendering routinely exceeds it"
    )
    # 5+ minute ceiling required to cover real Aleph chunked
    # renders on multi-segment sources.
    assert captured["timeout"] >= 300


def test_style_remix_propagates_chunked_flag_in_source_spec() -> None:
    """The chunked-path metadata reaches the output Asset's
    source_spec so audits can identify multi-fire remixes."""
    ws = _make_workspace("v11chunked@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws, duration_ms=25000)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="style_remix",
        params={"style_preset": "cyberpunk"},
    )
    cm, fake = _patched_client(
        _fake_remix(
            "/data/_internal/style_remixes/cp.mp4",
            chunked=True,
            task_ids=[f"runway_aleph_{i}" for i in range(5)],
        ),
    )
    with patch(
        "apps.compositions.primitives.style_remix.MediaEngineClient",
        return_value=cm,
    ):
        r = StyleRemixPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": src}],
            mock_mode=False,
        )
    spec = r.extra_source_spec
    assert spec["chunked"] is True
    assert len(spec["task_ids"]) == 5
    assert spec["style_preset"] == "cyberpunk"


def test_style_remix_propagates_media_engine_failure() -> None:
    ws = _make_workspace("v11fail@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="style_remix",
        params={"style_preset": "noir"},
    )
    fake = MagicMock()
    fake.style_remix.side_effect = MediaEngineError(
        "aleph rejected", status_code=502,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.compositions.primitives.style_remix.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError):
            StyleRemixPrimitive.execute(
                step=step,
                resolved_inputs=[{"slot": "source", "asset": src}],
                mock_mode=False,
            )


def test_style_remix_invalid_seed_raises() -> None:
    ws = _make_workspace("v11seed@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="style_remix",
        params={"style_preset": "noir", "seed": "not-an-int"},
    )
    with pytest.raises(PrimitiveError) as exc:
        StyleRemixPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": src}],
            mock_mode=False,
        )
    assert "seed" in str(exc.value).lower()


# ---- starter: style_remix_pass -----------------------------------


def test_style_remix_pass_starter_creates_composition_with_preset() -> None:
    ws = _make_workspace("v11starter1@test")
    sp = _make_spokesperson(ws)
    src = _make_clip(ws)
    c = style_remix_pass(
        workspace=ws, spokesperson=sp,
        source_clip=src, style_preset="watercolor",
        mock_mode=True,
    )
    assert c.template_kind == "style_remix_pass"
    step = c.steps.first()
    assert step.primitive == "style_remix"
    assert step.params["style_preset"] == "watercolor"
    assert step.inputs[0]["asset_id"] == str(src.id)


def test_style_remix_pass_starter_propagates_seed() -> None:
    ws = _make_workspace("v11starter_seed@test")
    sp = _make_spokesperson(ws)
    src = _make_clip(ws)
    c = style_remix_pass(
        workspace=ws, spokesperson=sp,
        source_clip=src, style_preset="chrome",
        seed=42, mock_mode=True,
    )
    step = c.steps.first()
    assert step.params["seed"] == 42


def test_style_remix_pass_normalizes_preset_to_lowercase() -> None:
    ws = _make_workspace("v11starter_case@test")
    sp = _make_spokesperson(ws)
    src = _make_clip(ws)
    c = style_remix_pass(
        workspace=ws, spokesperson=sp,
        source_clip=src, style_preset="ANIME",
        mock_mode=True,
    )
    step = c.steps.first()
    assert step.params["style_preset"] == "anime"


def test_style_remix_pass_rejects_unknown_preset() -> None:
    ws = _make_workspace("v11starter_unk@test")
    sp = _make_spokesperson(ws)
    src = _make_clip(ws)
    with pytest.raises(ValueError):
        style_remix_pass(
            workspace=ws, spokesperson=sp,
            source_clip=src, style_preset="renaissance",
            mock_mode=True,
        )


def test_style_remix_pass_rejects_audio_input() -> None:
    ws = _make_workspace("v11starter_audio@test")
    sp = _make_spokesperson(ws)
    audio = Asset.objects.create(
        workspace=ws, asset_type=AssetType.AUDIO,
        file_path="/data/a.mp3",
    )
    with pytest.raises(ValueError):
        style_remix_pass(
            workspace=ws, spokesperson=sp,
            source_clip=audio, style_preset="noir",
            mock_mode=True,
        )


def test_style_remix_pass_rejects_cross_workspace_clip() -> None:
    ws_a = _make_workspace("v11x_a@test", "A")
    ws_b = _make_workspace("v11x_b@test", "B")
    sp_a = _make_spokesperson(ws_a)
    foreign = _make_clip(ws_b)
    with pytest.raises(ValueError):
        style_remix_pass(
            workspace=ws_a, spokesperson=sp_a,
            source_clip=foreign, style_preset="noir",
            mock_mode=True,
        )


def test_style_remix_pass_executes_end_to_end_in_mock_mode() -> None:
    ws = _make_workspace("v11e2e@test")
    sp = _make_spokesperson(ws)
    src = _make_clip(ws, duration_ms=5000)
    c = style_remix_pass(
        workspace=ws, spokesperson=sp,
        source_clip=src, style_preset="cyberpunk",
        mock_mode=True,
    )
    execute_composition.apply(args=[str(c.pk)]).get()
    c.refresh_from_db()
    assert c.status == CompositionStatus.COMPLETED
    assert c.final_asset is not None
    assert c.final_asset.asset_type == AssetType.CLIP
    assert c.final_asset.source_spec["style_preset"] == "cyberpunk"


# ---- cost --------------------------------------------------------


def test_style_remix_cost_estimate_is_realistic() -> None:
    """Aleph is a real provider-billed operation; estimate
    should sit above the mock primitives' 100-micro floors."""
    assert StyleRemixPrimitive.estimate_cost({}) >= 100_000
