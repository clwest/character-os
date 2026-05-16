"""
Stability portrait orchestrator
================================

SESSION 171 — ties ``stability_ai_service`` (low-level API client)
together with ``style_library`` (42 prompt presets) to produce a
``PortraitResult``-shaped output that can drop into the existing
Runway ``create_avatar`` call.

Provider seam: Runway's ``POST /v1/avatars/`` accepts any base64
data URI as its ``referenceImage`` — it doesn't care if the image
came from Runway gen4_image, Stability SD3, DALL-E, or a hand-drawn
JPG. This module fills the same slot as
``character_studio_client.generate_portrait`` but uses Stability
under the hood.

Public API:
    * ``generate_stability_portrait(subject, *, style_preset, model,
       template, negative_prompt)`` — returns the rendered image
       bytes + the composed prompt + Stability cost in credits

Input shape mirrors the existing /internal/portrait/ endpoint
(template + subject + style) so swapping providers is a single
config flip in the Django rebake action.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.services.stability_ai_service import (
    calculate_adaptive_timeout,
    get_stability_api_key,
    stability_request_with_retry,
)
from app.services.style_library import get_style_by_name

logger = logging.getLogger(__name__)


# Stability v2beta endpoints. ``sd3`` covers sd3-large; the API
# auto-selects the model variant based on credit budget unless
# overridden via the ``model`` form field.
_ENDPOINTS = {
    "sd3": "https://api.stability.ai/v2beta/stable-image/generate/sd3",
    "core": "https://api.stability.ai/v2beta/stable-image/generate/core",
    "ultra": "https://api.stability.ai/v2beta/stable-image/generate/ultra",
}

# Cost in Stability credits per image (canonical pricing per
# https://platform.stability.ai/pricing — single source of truth
# lives in u-d-b's ``core/services/api_cost_config.py``).
_COST_CREDITS = {
    "sd3": 6.5,
    "core": 3.0,
    "ultra": 8.0,
    # sd3 sub-models: explicit selection via the SD3 endpoint's
    # ``model`` form field.
    "sd3-large": 6.5,
    "sd3-large-turbo": 4.0,
    "sd3-medium": 3.5,
}


# Per-template anchor + negative-prompt cues. The mascot path
# emphasizes anthropomorphic creatures (the SESSION 169 → SESSION 171
# operator complaint was that Runway's mascot output kept producing
# part-human results — human arms, no fur). Stability's negative
# prompt mechanic is the right lever here, plus a positive anchor.
_TEMPLATE_PROMPT_PREFIX = {
    "mascot": (
        "Stylized character portrait of an anthropomorphic creature "
        "spokesperson, fully formed with creature anatomy "
        "(fur, paws, hooves, snout as appropriate) — NOT a human in a "
        "costume."
    ),
    "founder": "Polished commercial headshot of",
    "coach": "Energetic commercial portrait of",
    "local_guide": "Welcoming neighborhood-business portrait of",
}

# Negative prompt by template. The mascot path explicitly rejects
# human anatomy bleeding through; the human templates explicitly
# reject cartoon/anime styling.
_TEMPLATE_NEGATIVE_PROMPT = {
    "mascot": (
        "human face, human hands, human arms, human anatomy, "
        "person in costume, mascot suit with visible zipper, "
        "back view, rear view, turned away, looking away, "
        "side profile only, face obscured, "
        "low quality, deformed, mutated, multiple subjects, "
        "watermark, text"
    ),
    "founder": (
        "cartoon, anime, illustration, 3d render, mascot, animal, "
        "back view, rear view, turned away, looking away, "
        "side profile only, face obscured, "
        "low quality, deformed, watermark, text"
    ),
    "coach": (
        "cartoon, anime, illustration, 3d render, mascot, animal, "
        "back view, rear view, turned away, looking away, "
        "side profile only, face obscured, "
        "low quality, deformed, watermark, text"
    ),
    "local_guide": (
        "cartoon, anime, illustration, 3d render, mascot, animal, "
        "back view, rear view, turned away, looking away, "
        "side profile only, face obscured, "
        "low quality, deformed, watermark, text"
    ),
}

# W11.6.1 — purpose-aware prompt prefixes for non-avatar surfaces.
# The avatar path keeps its template-driven prefix above
# (mascot/founder/coach/local_guide). The new purposes target
# different operator journeys (Journeys 1-4 in MEDIA_GENERATION_V1).
#
# Each prefix sits where the template prefix sits in the
# avatar prompt — operator's subject text is appended directly
# after a single space.
_PURPOSE_PROMPT_PREFIX = {
    "scene": "A detailed scene illustration of",
    "broll": "A supplementary establishing shot of",
    "product": "A high-quality product image of",
    "ad": "A striking advertising visual of",
}

# Purpose-specific framing — replaces the tight-portrait framing
# the avatar path uses. Avatar framing optimizes for Runway's
# deterministic centre-crop (eyes / mouth must land in a fixed
# region); the non-avatar purposes have no such constraint and
# benefit from broader compositions.
_PURPOSE_FRAMING = {
    "scene": (
        "Wide environmental composition. Clear focus on the subject "
        "within its surroundings. Thoughtful lighting that suits the "
        "scene's mood."
    ),
    "broll": (
        "Establishing-shot framing with environmental context. "
        "The subject is clearly visible. Cinematic composition "
        "appropriate for cutaway footage."
    ),
    "product": (
        "Centered product composition on a clean, uncluttered "
        "background. Studio lighting. The product is the sole "
        "focus of the frame."
    ),
    "ad": (
        "Bold advertising composition. Strong visual hierarchy "
        "with a striking subject and eye-catching framing."
    ),
}

# Negative prompts for non-avatar purposes. Shorter than the
# avatar negatives — the avatar set is heavy on "no back view /
# face obscured" anti-patterns specific to Runway's rig, which
# don't apply outside avatars.
_PURPOSE_NEGATIVE_PROMPT = {
    "scene": (
        "low quality, deformed, blurry, watermark, text, "
        "amateurish, distorted composition"
    ),
    "broll": (
        "low quality, deformed, blurry, watermark, text, "
        "amateurish, distorted composition"
    ),
    "product": (
        "low quality, deformed, blurry, watermark, text, "
        "clutter, multiple products, distracting background, "
        "people in frame"
    ),
    "ad": (
        "low quality, deformed, blurry, watermark, text, "
        "amateurish, low resolution"
    ),
}

# v1 purpose enum — Contract rule 1 (single image surface,
# purpose-routed). ``avatar`` routes through the existing
# template path; the rest route through the purpose path.
VALID_PURPOSES = frozenset({"avatar", "scene", "broll", "product", "ad"})


@dataclass(slots=True)
class StabilityPortraitResult:
    """What ``generate_stability_portrait`` returns. Shape mirrors
    ``character_studio_client.PortraitResult`` enough that the
    consumer can save the image then re-encode as a data URI for
    Runway's ``create_avatar`` call.
    """
    status: str  # "ok" | "failed"
    portrait_path: Optional[Path] = None
    prompt: Optional[str] = None
    model: Optional[str] = None
    style_preset: Optional[str] = None
    cost_credits: float = 0.0
    elapsed_ms: int = 0
    error: Optional[str] = None
    mock_mode: bool = False


class StabilityPortraitError(RuntimeError):
    """Internal — caught by the public entry point."""


def build_stability_prompt(
    subject: str,
    *,
    purpose: str = "avatar",
    template: str = "mascot",
    style_preset: Optional[str] = None,
) -> str:
    """Compose a Stability prompt from (purpose, template, subject, style_preset).

    Two branches:

    * ``purpose="avatar"`` (default) uses the template-driven
      prefix + Runway-rig-tuned portrait framing (locked
      SESSION 171). ``template`` selects between mascot /
      founder / coach / local_guide.
    * ``purpose`` ∈ {scene, broll, product, ad} — non-avatar
      surfaces. The avatar template is ignored; purpose-specific
      prefix + framing apply. No anthropomorphic auto-inject
      (Contract rule 5 — drop mascot-anatomy guidance outside
      the avatar surface).
    """
    subject_clean = (subject or "").strip()
    if not subject_clean:
        raise StabilityPortraitError("subject is required")

    purpose_clean = (purpose or "avatar").lower()
    if purpose_clean not in VALID_PURPOSES:
        raise StabilityPortraitError(
            f"unknown purpose {purpose!r} "
            f"(expected one of {sorted(VALID_PURPOSES)})"
        )

    if purpose_clean == "avatar":
        tmpl = (template or "mascot").lower()
        prefix = _TEMPLATE_PROMPT_PREFIX.get(tmpl) or _TEMPLATE_PROMPT_PREFIX["mascot"]
    else:
        prefix = _PURPOSE_PROMPT_PREFIX[purpose_clean]

    parts = [f"{prefix} {subject_clean}."]
    if style_preset:
        style = get_style_by_name(style_preset)
        if style:
            parts.append(f"{style.example_prompt_suffix}.")
        else:
            logger.warning(
                "unknown style_preset=%r — skipping suffix", style_preset,
            )

    if purpose_clean == "avatar":
        # Composition framing. SESSION 171 — avatar-purpose framing
        # arrived at by iteration:
        #   1st attempt: "Head-and-shoulders" → Runway over-cropped
        #      face, lost ornament (horn) + speaking area.
        #   2nd attempt: "Medium shot + body context + breathing room"
        #      → Stability rendered figure from BEHIND.
        #   3rd attempt: "Front-facing + medium shot" → figure too
        #      low in the frame, face dropped below Runway's crop
        #      center.
        #   Landing: tight portrait framing where the face dominates
        #   the upper-center of the frame so Runway's deterministic
        #   center-crop catches the face cleanly, with mouth + eyes
        #   as explicit landmarks (avatar rig needs both). No body
        #   below shoulders (body context is the wrong purpose for
        #   avatars — that's W11.6's "scene" purpose).
        parts.append(
            "Tight portrait composition. The face fills the central "
            "portion of the frame with the eyes positioned slightly "
            "above center. Both eyes and the full mouth are clearly "
            "visible and unobstructed. Only the head and the top of "
            "the shoulders are in frame — no hands, no torso, no body "
            "below the shoulders. Generous headroom above the head. "
            "Front-facing, looking directly at the camera. Clean "
            "studio background. Centered solo subject, one character only."
        )
    else:
        parts.append(_PURPOSE_FRAMING[purpose_clean])

    return " ".join(parts)


def build_stability_negative_prompt(
    template: str = "mascot",
    *,
    purpose: str = "avatar",
) -> str:
    """Return the negative prompt for the given (purpose, template).

    Avatar purpose — selects per ``template`` (drops human anatomy
    for mascots, drops cartoon/illustration for photoreal humans).

    Non-avatar purposes — uses the purpose-specific negative; the
    avatar-only "back view / face obscured" anti-patterns don't
    apply outside the Runway rig.
    """
    purpose_clean = (purpose or "avatar").lower()
    if purpose_clean != "avatar":
        return _PURPOSE_NEGATIVE_PROMPT.get(
            purpose_clean, _PURPOSE_NEGATIVE_PROMPT["scene"],
        )
    tmpl = (template or "mascot").lower()
    return _TEMPLATE_NEGATIVE_PROMPT.get(tmpl) or _TEMPLATE_NEGATIVE_PROMPT["mascot"]


def generate_stability_portrait(
    subject: str,
    *,
    purpose: str = "avatar",
    template: str = "mascot",
    style_preset: Optional[str] = None,
    model: str = "sd3-large",
    aspect_ratio: str = "16:9",
    cache_dir: Optional[Path] = None,
    negative_prompt: Optional[str] = None,
) -> StabilityPortraitResult:
    """Generate an image via Stability AI.

    Originally avatar-only (SESSION 171); W11.6.1 extended to
    cover the workspace-wide non-avatar image surface (scene /
    broll / product / ad).

    Args:
        subject: Free-text subject (the operator's
            ``visual_subject`` — e.g. "battle unicorn in lorica
            segmentata", or "a small craft brewery owner at
            sunrise" for a scene). Required.
        purpose: One of ``avatar`` / ``scene`` / ``broll`` /
            ``product`` / ``ad``. ``avatar`` keeps the
            template-driven prompt + Runway-rig-tuned portrait
            framing; the other purposes use purpose-specific
            prefix + framing. Defaults to ``avatar`` for backward
            compatibility with the existing rebake flow.
        template: One of ``mascot`` / ``founder`` / ``coach`` /
            ``local_guide``. Only consulted when ``purpose="avatar"``.
            Defaults to ``mascot``.
        style_preset: Optional style preset name from
            ``style_library`` (e.g. ``"pixar"``, ``"oil_painting"``,
            ``"cyberpunk"``). Adds aesthetic guidance to the prompt.
        model: Stability model — ``sd3-large`` (default, 6.5
            credits), ``sd3-large-turbo`` (4), ``sd3-medium`` (3.5),
            ``ultra`` (8, premium), ``core`` (3, fastest).
        aspect_ratio: Stability output ratio. Default 16:9 matches
            Runway gen4_image's portrait shape; non-avatar
            purposes commonly use 1:1, 9:16, or 21:9.
        cache_dir: Where to write the PNG. Defaults to
            ``<data_dir>/_internal/images_stability/`` for
            non-avatar purposes; ``portraits_stability/`` for
            avatar purpose.
        negative_prompt: Override the default negative prompt
            (per purpose + template).

    Returns:
        ``StabilityPortraitResult`` with ``status="ok"``, the on-disk
        PNG path, the composed prompt, and the credit cost.
        ``status="failed"`` with ``error`` populated on failure;
        ``mock_mode=True`` when ``STABILITY_API_KEY`` is unset.
    """
    started = time.time()
    settings = get_settings()

    # Mock-mode short-circuit — mirrors the runway_mock pattern in
    # character_studio_client. Returns a deterministic placeholder
    # path so dev/test workflows don't burn credits.
    if settings.stability_mock:
        logger.info(
            "stability mock-mode (no STABILITY_API_KEY) — skipping API call",
        )
        return StabilityPortraitResult(
            status="ok",
            portrait_path=None,
            prompt=build_stability_prompt(
                subject, purpose=purpose, template=template,
                style_preset=style_preset,
            ),
            model=model,
            style_preset=style_preset,
            cost_credits=0.0,
            elapsed_ms=int((time.time() - started) * 1000),
            mock_mode=True,
        )

    api_key = get_stability_api_key()
    if not api_key:
        return StabilityPortraitResult(
            status="failed",
            error="STABILITY_API_KEY not set",
        )

    prompt = build_stability_prompt(
        subject, purpose=purpose, template=template,
        style_preset=style_preset,
    )
    neg = (negative_prompt or build_stability_negative_prompt(
        template, purpose=purpose,
    ))

    # Resolve endpoint. sd3-large / sd3-large-turbo / sd3-medium all
    # go through the SD3 endpoint with the ``model`` form field
    # selecting the variant.
    if model.startswith("sd3"):
        endpoint = _ENDPOINTS["sd3"]
        sd3_model_field = model  # 'sd3-large' | 'sd3-medium' | 'sd3-large-turbo'
    elif model == "ultra":
        endpoint = _ENDPOINTS["ultra"]
        sd3_model_field = None
    elif model == "core":
        endpoint = _ENDPOINTS["core"]
        sd3_model_field = None
    else:
        return StabilityPortraitResult(
            status="failed",
            error=f"unknown stability model {model!r}",
            prompt=prompt,
        )

    headers = {
        "authorization": f"Bearer {api_key}",
        "accept": "image/*",
    }
    form = {
        "prompt": prompt,
        "negative_prompt": neg,
        "output_format": "png",
        "aspect_ratio": aspect_ratio,
    }
    if sd3_model_field:
        form["model"] = sd3_model_field

    # 4-minute timeout cap; the helper exponential-backoffs internally.
    timeout = calculate_adaptive_timeout(
        "sd3" if model.startswith("sd3") else model, num_images=1,
    )

    result = stability_request_with_retry(
        url=endpoint,
        headers=headers,
        files={"none": ""},  # forces multipart/form-data per Stability's contract
        data=form,
        timeout=timeout,
        max_retries=3,
        accept_type="image/*",
    )

    if not result["success"]:
        return StabilityPortraitResult(
            status="failed",
            error=f"stability api: {result.get('error', 'unknown error')[:300]}",
            prompt=prompt,
            model=model,
            style_preset=style_preset,
            elapsed_ms=int((time.time() - started) * 1000),
        )

    image_bytes = result["content"]
    if not image_bytes:
        return StabilityPortraitResult(
            status="failed",
            error="stability returned zero bytes",
            prompt=prompt,
            model=model,
            style_preset=style_preset,
            elapsed_ms=int((time.time() - started) * 1000),
        )

    # Write to disk under data_dir for parity with the Runway path.
    # Avatar purpose lands under ``portraits_stability/`` (preserves
    # the SESSION 171 layout); other purposes land under
    # ``images_stability/`` so cache files don't mix surfaces.
    if cache_dir is not None:
        target_dir = cache_dir
    elif (purpose or "avatar").lower() == "avatar":
        target_dir = settings.data_path / "_internal" / "portraits_stability"
    else:
        target_dir = settings.data_path / "_internal" / "images_stability"
    target_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:20]
    target = target_dir / f"{digest}.png"
    try:
        target.write_bytes(image_bytes)
    except OSError as exc:
        return StabilityPortraitResult(
            status="failed",
            error=f"write failed: {exc!s}",
            prompt=prompt,
            model=model,
            style_preset=style_preset,
            elapsed_ms=int((time.time() - started) * 1000),
        )

    logger.info(
        "stability portrait ready model=%s style=%s bytes=%d path=%s",
        model, style_preset, len(image_bytes), target.name,
    )

    return StabilityPortraitResult(
        status="ok",
        portrait_path=target,
        prompt=prompt,
        model=model,
        style_preset=style_preset,
        cost_credits=_COST_CREDITS.get(model, 6.5),
        elapsed_ms=int((time.time() - started) * 1000),
        mock_mode=False,
    )


def portrait_to_data_uri(portrait_path: Path) -> str:
    """Encode a PNG file as a base64 data URI for Runway's
    ``create_avatar`` reference image. Mirrors
    ``character_studio_client._portrait_to_data_uri``.
    """
    raw = portrait_path.read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
