"""W11.6.1 — tests for the Stability AI non-avatar image surface.

Covers:

* ``stability_portrait.build_stability_prompt`` purpose routing:
  - ``purpose="avatar"`` still uses template prefix + tight
    portrait framing (backwards-compat with SESSION 171 path).
  - Non-avatar purposes (scene / broll / product / ad) use
    purpose prefix + purpose framing; no anthropomorphic
    auto-inject; no portrait framing.
* ``build_stability_negative_prompt`` purpose vs template routing.
* Style preset suffix is appended; unknown preset is skipped
  with a warning (not a hard error).
* Subject required.
* ``POST /internal/image_stability/`` happy path in mock mode
  for every valid purpose. Returns valid data URI + composed
  prompt + zero credits + mock_mode=True.
* Validation: unsupported purpose / aspect_ratio / model all
  surface as 400 with the contract error shape.
* Backwards-compat: ``generate_stability_portrait`` called with
  default args (no ``purpose=``) keeps the avatar / mascot
  prompt shape used by the SESSION 170 rebake flow.

Mock mode is the primary test surface (matches the avatar /
realtime / images endpoints). Real-mode against Stability is
exercised manually before launch.
"""
from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.services.stability_portrait import (
    StabilityPortraitError,
    VALID_PURPOSES,
    build_stability_negative_prompt,
    build_stability_prompt,
    generate_stability_portrait,
)


# ---- fixtures ---------------------------------------------------


@pytest.fixture
def mock_client(tmp_path: Path) -> Iterator[TestClient]:
    """TestClient with forced Stability mock-mode + isolated data dir.

    ``stability_api_key=""`` flips ``settings.stability_mock`` to
    True; the endpoint short-circuits to the mock branch via the
    injected settings (so the lru_cached ``get_settings()`` inside
    services can't bypass us with a populated .env).
    """
    settings = Settings(
        runway_api_key="",
        stability_api_key="",
        data_dir=str(tmp_path),
    )
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)


# ---- build_stability_prompt: purpose routing --------------------


def test_avatar_purpose_keeps_template_prefix_and_portrait_framing():
    """Backwards-compat with SESSION 170/171 rebake flow — the
    avatar path uses the mascot prefix + the tight-portrait
    framing locked SESSION 171."""
    prompt = build_stability_prompt(
        "battle unicorn in lorica segmentata",
        purpose="avatar",
        template="mascot",
    )
    assert "anthropomorphic creature" in prompt
    assert "Tight portrait composition" in prompt
    assert "eyes" in prompt and "mouth" in prompt
    # Non-avatar framing should NOT appear in the avatar prompt.
    assert "Wide environmental composition" not in prompt
    assert "establishing shot" not in prompt.lower()


def test_scene_purpose_uses_scene_prefix_not_anthropomorphic():
    """``purpose="scene"`` drops the mascot-anatomy auto-inject
    (Contract rule 5) and uses scene-specific framing."""
    prompt = build_stability_prompt(
        "a small craft brewery owner tapping a fresh keg at sunrise",
        purpose="scene",
    )
    assert prompt.startswith("A detailed scene illustration of")
    assert "Wide environmental composition" in prompt
    # Mascot-only inject must not appear for non-avatar purposes.
    assert "anthropomorphic" not in prompt.lower()
    # Avatar portrait framing must not appear.
    assert "Tight portrait composition" not in prompt
    assert "eyes positioned slightly above center" not in prompt


@pytest.mark.parametrize(
    "purpose,expected_prefix",
    [
        ("broll", "A supplementary establishing shot of"),
        ("product", "A high-quality product image of"),
        ("ad", "A striking advertising visual of"),
    ],
)
def test_non_avatar_purpose_prefixes(purpose: str, expected_prefix: str):
    prompt = build_stability_prompt("a single hand-blown glass mug", purpose=purpose)
    assert prompt.startswith(expected_prefix)
    assert "anthropomorphic" not in prompt.lower()
    assert "Tight portrait composition" not in prompt


def test_unknown_purpose_raises():
    with pytest.raises(StabilityPortraitError, match="unknown purpose"):
        build_stability_prompt("subject", purpose="bogus")


def test_empty_subject_raises():
    with pytest.raises(StabilityPortraitError, match="subject is required"):
        build_stability_prompt("   ", purpose="scene")


def test_style_preset_suffix_is_appended():
    prompt = build_stability_prompt(
        "city skyline at dusk", purpose="scene", style_preset="cyberpunk",
    )
    assert "neon" in prompt.lower() or "cyberpunk" in prompt.lower()


def test_unknown_style_preset_is_skipped_with_warning(caplog):
    caplog.set_level(logging.WARNING, logger="app.services.stability_portrait")
    prompt = build_stability_prompt(
        "city skyline", purpose="scene", style_preset="not_a_real_preset",
    )
    # Prompt still composed (no exception).
    assert prompt.startswith("A detailed scene illustration of")
    assert any("unknown style_preset" in rec.message for rec in caplog.records)


# ---- build_stability_negative_prompt ----------------------------


def test_negative_prompt_avatar_mascot_rejects_human_anatomy():
    neg = build_stability_negative_prompt("mascot", purpose="avatar")
    assert "human" in neg


def test_negative_prompt_scene_does_not_inherit_avatar_face_clauses():
    """Non-avatar negatives are tuned for the surface; the avatar
    'no back view / face obscured' clauses don't apply outside
    the Runway rig."""
    neg = build_stability_negative_prompt(purpose="scene")
    assert "face obscured" not in neg
    assert "back view" not in neg
    assert "low quality" in neg


def test_negative_prompt_product_includes_clutter_reject():
    neg = build_stability_negative_prompt(purpose="product")
    assert "clutter" in neg


# ---- backwards-compat: existing rebake call shape ---------------


def test_generate_stability_portrait_default_args_preserves_avatar_shape(
    tmp_path, monkeypatch,
):
    """The SESSION 170 rebake action calls
    ``generate_stability_portrait(subject, template=...)`` without
    a ``purpose=`` argument. After W11.6.1 the default
    (``purpose="avatar"``) must keep that call producing an
    avatar-shaped prompt.

    Service code calls the lru_cached ``get_settings()`` directly,
    so a dependency override on ``app`` doesn't reach it. Monkeypatch
    the module-level reference instead — this is the only way to
    keep the real STABILITY_API_KEY (if present in .env) from
    triggering a real Stability call during this unit test.
    """
    fake_settings = Settings(stability_api_key="", data_dir=str(tmp_path))
    monkeypatch.setattr(
        "app.services.stability_portrait.get_settings",
        lambda: fake_settings,
    )
    result = generate_stability_portrait(
        "a friendly raccoon sales mascot",
        template="mascot",
    )
    assert result.mock_mode is True
    assert result.prompt is not None
    assert "anthropomorphic creature" in result.prompt
    assert "Tight portrait composition" in result.prompt


# ---- POST /internal/image_stability/ : happy path per purpose ---


@pytest.mark.parametrize("purpose", sorted(VALID_PURPOSES - {"avatar"}))
def test_post_image_stability_mock_per_purpose(mock_client: TestClient, purpose: str):
    resp = mock_client.post(
        "/internal/image_stability/",
        json={
            "purpose": purpose,
            "subject": "subject text for testing",
            "model": "sd3-large",
            "style_preset": "minimalist",
            "aspect_ratio": "16:9",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["purpose"] == purpose
    assert body["model"] == "sd3-large"
    assert body["style_preset"] == "minimalist"
    assert body["aspect_ratio"] == "16:9"
    assert body["mock_mode"] is True
    assert body["cost_credits"] == 0.0
    assert body["mime_type"] == "image/png"
    # Image data URI is a valid base64 PNG.
    assert body["image_data_uri"].startswith("data:image/png;base64,")
    raw_b64 = body["image_data_uri"].split(",", 1)[1]
    # Should decode without error.
    decoded = base64.b64decode(raw_b64)
    assert len(decoded) > 0
    # Composed prompt reflects the purpose.
    assert body["prompt"]
    assert body["prompt"] != "subject text for testing"  # composer added framing


def test_post_image_stability_mock_avatar_purpose(mock_client: TestClient):
    """Avatar purpose is allowed on this endpoint (operator
    iterates cheaply before committing to a Runway bake — Journey 5
    in MEDIA_GENERATION_V1)."""
    resp = mock_client.post(
        "/internal/image_stability/",
        json={
            "purpose": "avatar",
            "subject": "an anthropomorphic donkey marketing mascot",
            "template": "mascot",
            "model": "core",
            "aspect_ratio": "1:1",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["purpose"] == "avatar"
    assert "anthropomorphic creature" in body["prompt"]
    assert "Tight portrait composition" in body["prompt"]
    assert body["aspect_ratio"] == "1:1"


# ---- POST /internal/image_stability/ : validation ----------------


def test_post_image_stability_unsupported_purpose_400(mock_client: TestClient):
    resp = mock_client.post(
        "/internal/image_stability/",
        json={
            "purpose": "skyline",
            "subject": "subject text",
        },
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "unsupported_purpose"


def test_post_image_stability_invalid_aspect_ratio_400(mock_client: TestClient):
    resp = mock_client.post(
        "/internal/image_stability/",
        json={
            "purpose": "scene",
            "subject": "subject text",
            "aspect_ratio": "42:17",
        },
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "invalid_aspect_ratio"


def test_post_image_stability_unsupported_model_400(mock_client: TestClient):
    resp = mock_client.post(
        "/internal/image_stability/",
        json={
            "purpose": "scene",
            "subject": "subject text",
            "model": "dall-e-99",
        },
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "unsupported_model"


def test_post_image_stability_missing_subject_422(mock_client: TestClient):
    """Pydantic ``min_length=1`` on subject — empty string is a 422
    validation error, not the 400 path."""
    resp = mock_client.post(
        "/internal/image_stability/",
        json={"purpose": "scene", "subject": ""},
    )
    assert resp.status_code == 422
