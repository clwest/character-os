"""Character Studio routes (PR K).

Eight V1 endpoints under ``/api/characters/*`` plus the integration
point ``POST /api/campaigns/{id}/attach-character`` which lives in
the campaigns router.

Locked design in
``docs/research/CHARACTER_STUDIO_SPIKE.md`` §§4-6.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..config import Settings, get_settings
from ..models import Character, CharacterCreate, CharacterList, KnowledgeSourceCreate
from ..services.character_store import CharacterStore
from ..services.character_studio_client import (
    create_avatar as studio_create_avatar,
    generate_portrait as studio_generate_portrait,
    PORTRAIT_TEMPLATES,
)
from ..services.character_host_client import SUPPORTED_VOICE_PRESETS
from ..services.voice_clone_client import (
    MAX_AUDIO_BYTES,
    SUPPORTED_AUDIO_MIMES,
    apply_voice_to_avatar,
    clone_voice_from_audio,
    compute_voice_drift_status,
    fetch_avatar_voice,
    fetch_voice_preview,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/characters", tags=["characters"])


def _store(settings: Settings = Depends(get_settings)) -> CharacterStore:
    return CharacterStore(settings.data_path)


# ---- PR AS — introspection helper shared by clone + apply routes ----


def _verify_avatar_voice_after_patch(
    record: Character,
    expected_voice_id: Optional[str],
    settings: Settings,
    apply_status: str,
):
    """PR AS — run `GET /v1/avatars/{id}` to confirm the freshly-
    patched voice binding actually landed. Returns
    ``(AvatarVoiceState, verified_at | None, drift_status)``. The
    caller persists every field; a verification failure is logged
    but never blocks the clone or apply flows.

    PR AT — also computes ``drift_status`` (match / drift / unknown)
    from the resolved id vs the expected (cloned) voice id so the
    UI can render a single drift-aware pill.

    When the prior PATCH was ``pending_avatar`` (no avatar bound
    yet) we skip the GET entirely — there's nothing to introspect.
    """
    from ..services.voice_clone_client import (  # noqa: WPS433 lazy-import
        AvatarVoiceState,
    )
    if apply_status == "pending_avatar":
        state = AvatarVoiceState(status="failed", error="no avatar bound")
        return state, None, "unknown"
    state = fetch_avatar_voice(
        record.runway_avatar_id,
        settings,
        avatar_is_mock=(record.runway_avatar_status == "mock"),
        expected_voice_id=expected_voice_id,
    )
    verified_at = (
        datetime.now(timezone.utc)
        if state.status in {"verified", "mock_verified"}
        else None
    )
    drift_status = compute_voice_drift_status(
        expected_voice_id, state.resolved_id, state.status,
    )
    return state, verified_at, drift_status


# ---- request bodies ----------------------------------------------


class GeneratePortraitBody(BaseModel):
    template: Optional[str] = Field(default=None, description="mascot|founder|coach|local_guide")
    subject: Optional[str] = Field(default=None, max_length=300)
    style: Optional[str] = Field(default=None, max_length=300)
    prompt_override: Optional[str] = Field(default=None, max_length=1000)
    # PR CS — safe-retry preset bypasses character.style and fills a
    # simpler `_SAFE_RETRY_TEMPLATES` entry. Operator-triggered after
    # BAD_OUTPUT failures (style chip stacks + IP references like
    # "indiana jones style hat" are the historical trigger). Has no
    # effect when `prompt_override` is also supplied — explicit
    # operator-typed text always wins.
    safe_retry: bool = Field(default=False)


class CreateAvatarBody(BaseModel):
    voice_preset: Optional[str] = Field(default=None)
    personality_override: Optional[str] = Field(default=None, max_length=600)


class ApplyVoiceBody(BaseModel):
    """PR BB — optional body for ``POST /apply-voice``.

    The frontend's PR AU "Repair voice drift" button passes
    ``mode: "repair"`` so the appended audit-trail entry is labeled
    ``action="repair"`` instead of the default ``"apply"``. Both
    code paths share the same backend handler — ``mode`` is purely
    for the audit trail label.
    """

    mode: Optional[Literal["apply", "repair"]] = None


class IdentityPatchBody(BaseModel):
    """PR EN — request body for the identity-patch route.

    Partial update of the user-visible identity fields on a Character.
    The v2 Identity panel needs the operator to edit ``personality``
    (system-prompt cue that flows into every realtime session via
    ``_build_session_overrides``), ``voice_preset`` (Runway preset id
    bound on the next avatar create / apply), and ``subject`` (the
    one-line description rendered under the header).

    Semantics:
    - Missing keys are left alone.
    - Empty strings are normalised to ``None`` for ``personality``
      and ``subject`` so an operator can clear them.
    - ``voice_preset`` validates against ``SUPPORTED_VOICE_PRESETS``;
      ``None`` is not a valid clear value (every character must have
      a preset).
    """

    personality: Optional[str] = Field(default=None, max_length=600)
    voice_preset: Optional[str] = Field(default=None)
    subject: Optional[str] = Field(default=None, max_length=300)


class MetadataPatchBody(BaseModel):
    """PR CK — request body for the metadata-patch route.

    ``Character.metadata`` is a free-form ``dict`` (PR CG used it
    for ``demo: True`` flags via a direct store update). The v2
    multi-step Create Spokesperson flow needs to write
    ``audience_vibe`` / ``creation_flow`` / ``visual_style_chips``
    / ``speaking_energy`` from the browser without inventing per-
    field columns; this route is the smallest possible HTTP path
    that lets it.

    Semantics:
    - Missing keys are left alone (merge, not replace).
    - Pass ``null`` for a key to delete it.
    - Cap the patch dict at 32 keys + 4 KB serialised so a
      pathological client can't fill the JSON record.
    """

    metadata: dict = Field(
        default_factory=dict,
        description=(
            "Partial metadata patch. Existing keys not mentioned "
            "stay; explicit nulls delete; new keys are added."
        ),
    )


# ---- PR BB — history helper -------------------------------------
#
# Centralised so every route appends entries with a consistent shape.
# Best-effort: callers wrap this in ``try/except`` so an audit
# failure never aborts the underlying clone / apply / refresh flow.


def _append_voice_history_safe(
    store: CharacterStore,
    character_id: str,
    *,
    action: str,
    before_voice_id: Optional[str] = None,
    after_voice_id: Optional[str] = None,
    resolved_voice_id: Optional[str] = None,
    drift_status: Optional[str] = None,
    status: Optional[str] = None,
    error: Optional[str] = None,
    mock_mode: Optional[bool] = None,
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "before_voice_id": before_voice_id,
        "after_voice_id": after_voice_id,
        "resolved_voice_id": resolved_voice_id,
        "drift_status": drift_status,
        "status": status,
        "error": error,
        "mock_mode": mock_mode,
    }
    try:
        store.append_voice_history(character_id, entry)
    except Exception as exc:  # pragma: no cover - audit is best-effort
        logger.warning(
            "voice history append failed for character %s action=%s: %s",
            character_id, action, exc,
        )


# ---- routes -------------------------------------------------------


@router.get("", response_model=CharacterList)
def list_characters(store: CharacterStore = Depends(_store)) -> CharacterList:
    return CharacterList(characters=store.list())


@router.post("", response_model=Character)
def create_character(
    payload: CharacterCreate,
    store: CharacterStore = Depends(_store),
) -> Character:
    if payload.template not in PORTRAIT_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"unsupported template '{payload.template}'. "
                f"supported: {sorted(PORTRAIT_TEMPLATES)}"
            ),
        )
    if payload.voice_preset and payload.voice_preset.lower() not in SUPPORTED_VOICE_PRESETS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"unsupported voice_preset '{payload.voice_preset}'. "
                f"supported: {sorted(SUPPORTED_VOICE_PRESETS)}"
            ),
        )
    record = store.create(payload)
    logger.info("character created id=%s name=%s template=%s", record.id, record.name, record.template)
    return record


@router.get("/{character_id}", response_model=Character)
def get_character(
    character_id: str,
    store: CharacterStore = Depends(_store),
) -> Character:
    record = store.get(character_id)
    if not record:
        raise HTTPException(status_code=404, detail="character not found")
    return record


@router.post("/{character_id}/generate-portrait", response_model=Character)
def post_generate_portrait(
    character_id: str,
    body: Optional[GeneratePortraitBody] = None,
    settings: Settings = Depends(get_settings),
    store: CharacterStore = Depends(_store),
) -> Character:
    record = store.get(character_id)
    if not record:
        raise HTTPException(status_code=404, detail="character not found")

    template = (body.template if body else None) or record.template
    if template not in PORTRAIT_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"unsupported template '{template}'. "
                f"supported: {sorted(PORTRAIT_TEMPLATES)}"
            ),
        )

    portrait_path = store.portrait_path(character_id)
    safe_retry = bool(body.safe_retry) if body else False
    result = studio_generate_portrait(
        record,
        portrait_path,
        settings,
        template=template,
        subject=body.subject if body else None,
        style=body.style if body else None,
        prompt_override=body.prompt_override if body else None,
        safe_retry=safe_retry,
    )

    if result.status == "ok":
        # PR EP — if an avatar was already built before this portrait
        # generation, the cached avatar now binds the OLD portrait. Set
        # `portrait_drift_from_avatar` so the Identity panel can surface
        # a stale-avatar banner with a Rebuild Avatar CTA. First-time
        # portrait generations (no avatar yet) keep the flag at False.
        portrait_drift_from_avatar = bool(record.runway_avatar_id)
        updated = store.update(
            character_id,
            portrait_url=result.portrait_url,
            portrait_source=result.portrait_source,
            portrait_prompt=result.portrait_prompt,
            portrait_last_error=None,  # PR CS — clear on success
            portrait_drift_from_avatar=portrait_drift_from_avatar,
            template=template,
            subject=(body.subject if body else None) or record.subject,
            style=(body.style if body else None) or record.style,
            mock_mode=result.mock_mode,
        )
    else:
        # PR CS — capture the failed prompt + error on the Character
        # record so the workspace audit `<details>` (and any UI
        # failure banner) can surface what was sent without a
        # log dive. Style-chips + prompt_override flag are
        # logged here for diagnosis; the persisted prompt itself
        # carries the resolved text.
        style_chips = []
        if isinstance(record.metadata, dict):
            chips = record.metadata.get("visual_style_chips") or []
            if isinstance(chips, list):
                style_chips = [c for c in chips if isinstance(c, str)]
        logger.warning(
            "portrait failed character=%s name=%r template=%s "
            "style_chips=%s prompt_override_used=%s safe_retry=%s "
            "prompt_len=%d err=%s prompt=%r",
            character_id,
            record.name,
            template,
            style_chips,
            bool((body.prompt_override or "").strip()) if body else False,
            safe_retry,
            len(result.portrait_prompt or ""),
            result.error,
            (result.portrait_prompt or "")[:600],
        )
        store.update(
            character_id,
            portrait_prompt=result.portrait_prompt,
            portrait_last_error=result.error,
        )
        raise HTTPException(
            status_code=502 if not result.mock_mode else 500,
            detail=result.error or "portrait generation failed",
        )
    return updated or record


@router.post("/{character_id}/create-avatar", response_model=Character)
def post_create_avatar(
    character_id: str,
    body: Optional[CreateAvatarBody] = None,
    settings: Settings = Depends(get_settings),
    store: CharacterStore = Depends(_store),
) -> Character:
    record = store.get(character_id)
    if not record:
        raise HTTPException(status_code=404, detail="character not found")
    if not store.has_portrait(character_id):
        raise HTTPException(
            status_code=409,
            detail=(
                "Generate the portrait first. "
                "POST /api/characters/{id}/generate-portrait."
            ),
        )
    # PR CR — additional belt-and-braces: an empty / zero-byte portrait
    # file slipped through `has_portrait()` would lead to an avatar
    # request with an empty referenceImage. Catch it here.
    portrait_path = store.portrait_path(character_id)
    portrait_size = portrait_path.stat().st_size if portrait_path.exists() else 0
    if portrait_size <= 0:
        raise HTTPException(
            status_code=409,
            detail="portrait cache is empty; regenerate the portrait first.",
        )

    voice_preset = body.voice_preset if body else None
    if voice_preset and voice_preset.lower() not in SUPPORTED_VOICE_PRESETS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"unsupported voice_preset '{voice_preset}'. "
                f"supported: {sorted(SUPPORTED_VOICE_PRESETS)}"
            ),
        )

    logger.info(
        "create-avatar character=%s portrait_bytes=%d portrait_mtime=%s "
        "voice_preset=%s has_custom_voice=%s",
        character_id,
        portrait_size,
        int(portrait_path.stat().st_mtime),
        (voice_preset or record.voice_preset or "vincent"),
        bool(record.custom_voice_id),
    )

    result = studio_create_avatar(
        record,
        portrait_path,
        settings,
        voice_preset=voice_preset,
        personality_override=(body.personality_override if body else None),
    )

    if result.status in {"ready", "mock"}:
        updated = store.update(
            character_id,
            runway_avatar_id=result.avatar_id,
            runway_avatar_status=result.status,
            runway_avatar_thumbnail_url=result.thumbnail_url,
            runway_avatar_error=None,
            voice_preset=(voice_preset or record.voice_preset).lower(),
            # PR EP — avatar just rebuilt, clear the drift flag so the
            # stale-avatar banner disappears.
            portrait_drift_from_avatar=False,
            mock_mode=result.mock_mode,
        )
        return updated or record

    # PR CR — persist the failed state so the workspace pill shows
    # `avatar · failed` next time the record is read, AND raise 502 so
    # the immediate caller (v2 stepper / workspace button) can surface
    # the specific error to the operator. The previous code returned
    # 200 with persisted-failed flags, so the frontend treated avatar
    # failures as success and silently navigated past them.
    store.update(
        character_id,
        runway_avatar_status="failed",
        runway_avatar_error=result.error,
    )
    logger.warning(
        "create-avatar failed character=%s err=%s",
        character_id, result.error,
    )
    raise HTTPException(
        status_code=502,
        detail=result.error or "avatar processing failed",
    )


# ---- PR AN — Custom voice cloning foundation ----------------------
#
# Multipart upload of a 10 s – 5 min audio sample. POST /v1/voices
# with from.type=audio creates a Runway voice id; Character OS persists it
# on the Character record and prefers it over the runway-live-preset
# binding the next time an avatar is created. Mock mode short-circuits
# with a deterministic ``mock_voice_<sha>`` id keyed off the character
# + sample bytes so re-uploads are idempotent and re-recordings yield
# a fresh id.


@router.post("/{character_id}/clone-voice", response_model=Character)
async def post_clone_voice(
    character_id: str,
    audio: UploadFile = File(..., description="10 s – 5 min audio sample (≤ 10 MB)"),
    name: Optional[str] = Form(default=None),
    settings: Settings = Depends(get_settings),
    store: CharacterStore = Depends(_store),
) -> Character:
    """PR AN — clone a voice from an uploaded audio sample. Returns the
    updated Character with ``custom_voice_*`` fields populated.

    Real mode: ``POST /v1/voices`` with ``from.type=audio`` (audio is
    embedded as a base64 data URI). Mock mode: deterministic
    ``mock_voice_<sha256(name + bytes)[:16]>``.

    Failure modes:
    - 404 — character not found.
    - 415 — unsupported audio mime type.
    - 413 — audio sample exceeds the local 15 MB cap.
    - 422 — empty / unreadable audio body.
    - 502 — Runway upstream rejection (real mode only).
    """
    record = store.get(character_id)
    if not record:
        raise HTTPException(status_code=404, detail="character not found")

    mime = (audio.content_type or "").lower().strip()
    if mime not in SUPPORTED_AUDIO_MIMES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"unsupported audio mime type '{mime or audio.filename or ''}'. "
                f"accepted: {sorted(set(SUPPORTED_AUDIO_MIMES))}"
            ),
        )

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="audio sample is empty")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"audio sample is {len(audio_bytes):,} bytes "
                f"(cap: {MAX_AUDIO_BYTES:,}); Runway's documented limit is 10 MB."
            ),
        )

    voice_name = (
        (name or "").strip()
        or f"Character OS — {(record.name or 'Character')[:60]}"
    )
    result = clone_voice_from_audio(voice_name, audio_bytes, mime, settings)

    if result.status == "failed" or not result.voice_id:
        store.update(
            character_id,
            custom_voice_id=None,
            custom_voice_name=voice_name,
            custom_voice_status="failed",
            custom_voice_error=result.error,
            custom_voice_mock_mode=result.mock_mode,
        )
        # PR BB — record the failed clone in the audit trail so the
        # operator can see it tried and what went wrong even after a
        # 502 surfaces in the UI.
        _append_voice_history_safe(
            store,
            character_id,
            action="clone",
            before_voice_id=record.custom_voice_id,
            after_voice_id=None,
            status="failed",
            error=result.error,
            mock_mode=result.mock_mode,
        )
        raise HTTPException(
            status_code=502,
            detail=f"voice clone failed: {result.error or 'unknown error'}",
        )

    # PR AQ — auto-PATCH the existing Runway avatar so the cloned
    # voice swaps in without an avatar recreate. Best-effort: a
    # patch failure preserves the cloned voice id and surfaces a
    # friendly error on the character record. The next
    # Create Runway Avatar click would still bind the voice via the
    # PR AN create-avatar payload.
    apply_result = apply_voice_to_avatar(
        record.runway_avatar_id,
        result.voice_id,
        settings,
        avatar_is_mock=(record.runway_avatar_status == "mock"),
    )
    patched_at = (
        datetime.now(timezone.utc)
        if apply_result.status in {"applied", "mock_patched"}
        else None
    )

    # PR AS — introspect the avatar resource so the operator can
    # confirm the bind actually landed (rather than trusting the
    # 2xx alone). Best-effort: a verify failure never blocks the
    # cloned voice or the patch state.
    # PR AT — also computes drift_status from the resolved id vs
    # the cloned voice id so the UI renders a single drift-aware pill.
    verify_state, verified_at, drift_status = _verify_avatar_voice_after_patch(
        record, result.voice_id, settings, apply_result.status,
    )

    updated = store.update(
        character_id,
        custom_voice_id=result.voice_id,
        custom_voice_name=voice_name,
        custom_voice_status=result.status,
        custom_voice_error=None,
        custom_voice_mock_mode=result.mock_mode,
        # PR AR — surface the Runway voice previewUrl when the clone
        # path captured one. ``None`` in mock mode + when polling
        # didn't expose a URL; the UI handles both cases gracefully.
        custom_voice_preview_url=result.preview_url,
        custom_voice_avatar_patch_status=apply_result.status,
        custom_voice_avatar_patch_error=apply_result.error,
        custom_voice_avatar_patched_at=(patched_at.isoformat() if patched_at else None),
        # PR AS — resolved voice fields from the avatar GET.
        avatar_voice_resolved_type=verify_state.resolved_type,
        avatar_voice_resolved_id=verify_state.resolved_id,
        avatar_voice_resolved_label=verify_state.resolved_label,
        avatar_voice_verify_status=verify_state.status,
        avatar_voice_verified_at=(
            verified_at.isoformat() if verified_at else None
        ),
        avatar_voice_verify_error=verify_state.error,
        # PR AT — drift detection.
        avatar_voice_drift_status=drift_status,
    )
    logger.info(
        "character %s voice cloned -> %s (status=%s mock=%s; patch=%s; drift=%s)",
        character_id, result.voice_id, result.status,
        result.mock_mode, apply_result.status, drift_status,
    )
    # PR BB — log the successful clone in the audit trail. We surface
    # the apply + verify outcomes via the same entry's drift / status
    # fields so the operator gets a single row that captures the
    # whole clone-then-bind-then-verify cycle.
    _append_voice_history_safe(
        store,
        character_id,
        action="clone",
        before_voice_id=record.custom_voice_id,
        after_voice_id=result.voice_id,
        resolved_voice_id=verify_state.resolved_id,
        drift_status=drift_status,
        status=result.status,
        error=None,
        mock_mode=result.mock_mode,
    )
    return updated or record


# ---- PR AQ — manual retry for the avatar voice swap ---------------
#
# The clone route auto-PATCHes the avatar after a successful clone.
# This route lets the operator retry the swap manually when the auto
# attempt failed (real-mode upstream blip, network, etc) without
# re-uploading the audio sample.


@router.post("/{character_id}/apply-voice", response_model=Character)
def post_apply_voice_to_avatar(
    character_id: str,
    body: Optional[ApplyVoiceBody] = Body(default=None),
    settings: Settings = Depends(get_settings),
    store: CharacterStore = Depends(_store),
) -> Character:
    """PR AQ — apply the character's already-cloned ``custom_voice_id``
    to the bound Runway avatar via ``PATCH /v1/avatars/{id}``.

    PR BB — accepts an optional ``mode`` body field (``"apply"`` |
    ``"repair"``). The frontend's PR AU "Repair voice drift" button
    passes ``mode: "repair"`` so the audit-trail entry is labeled
    accordingly; both code paths share the same backend behaviour.

    Failure modes:
    - 404 — character not found.
    - 409 — character has no cloned voice yet.
    - 502 — Runway upstream rejection.
    """
    record = store.get(character_id)
    if not record:
        raise HTTPException(status_code=404, detail="character not found")
    if not record.custom_voice_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "no custom voice cloned for this character yet — "
                "upload or record an audio sample first."
            ),
        )

    apply_result = apply_voice_to_avatar(
        record.runway_avatar_id,
        record.custom_voice_id,
        settings,
        avatar_is_mock=(record.runway_avatar_status == "mock"),
    )
    patched_at = (
        datetime.now(timezone.utc)
        if apply_result.status in {"applied", "mock_patched"}
        else None
    )
    # PR AS — verify the bind landed. PR AT — also compute drift.
    verify_state, verified_at, drift_status = _verify_avatar_voice_after_patch(
        record, record.custom_voice_id, settings, apply_result.status,
    )
    updated = store.update(
        character_id,
        custom_voice_avatar_patch_status=apply_result.status,
        custom_voice_avatar_patch_error=apply_result.error,
        custom_voice_avatar_patched_at=(patched_at.isoformat() if patched_at else None),
        avatar_voice_resolved_type=verify_state.resolved_type,
        avatar_voice_resolved_id=verify_state.resolved_id,
        avatar_voice_resolved_label=verify_state.resolved_label,
        avatar_voice_verify_status=verify_state.status,
        avatar_voice_verified_at=(
            verified_at.isoformat() if verified_at else None
        ),
        avatar_voice_verify_error=verify_state.error,
        avatar_voice_drift_status=drift_status,
    )
    # PR BB — record the apply/repair attempt in the audit trail so
    # the operator can see who patched the avatar, when, and what
    # the resolved voice + drift state ended up as. Distinguish
    # repair from apply via the optional body ``mode`` flag (frontend
    # PR AU repair button passes "repair"; default flow is "apply").
    audit_action = "repair" if (body and body.mode == "repair") else "apply"
    _append_voice_history_safe(
        store,
        character_id,
        action=audit_action,
        before_voice_id=record.avatar_voice_resolved_id,
        after_voice_id=record.custom_voice_id,
        resolved_voice_id=verify_state.resolved_id,
        drift_status=drift_status,
        status=apply_result.status,
        error=apply_result.error,
        mock_mode=(apply_result.status == "mock_patched"),
    )
    if apply_result.status == "failed":
        raise HTTPException(
            status_code=502,
            detail=f"avatar voice PATCH failed: {apply_result.error or 'unknown'}",
        )
    return updated or record


# ---- PR AV — Avatar status manual refresh -------------------------
#
# Read-only counterpart to PR AQ's apply-voice. Re-runs the PR AS
# avatar introspection + PR AT drift recompute against the existing
# avatar resource without ever calling PATCH. Useful when an operator
# wants to re-check Runway state (e.g. after waiting for a queued
# upstream change) without mutating the binding.


@router.post("/{character_id}/refresh-avatar-voice", response_model=Character)
def post_refresh_avatar_voice(
    character_id: str,
    settings: Settings = Depends(get_settings),
    store: CharacterStore = Depends(_store),
) -> Character:
    """PR AV — re-run avatar voice introspection + drift recompute
    without applying the PATCH. Calls only ``fetch_avatar_voice`` +
    ``compute_voice_drift_status``; the PR AQ apply path is never
    invoked from here so this route has no PATCH side effects.

    Failure modes:
    - 404 — character not found.
    - 409 — character has no avatar bound yet (cannot introspect).
    - 409 — character has no cloned voice yet (drift comparison
      requires both ids to exist).

    Real-mode HTTP / network failures persist as ``failed`` /
    ``unverified`` on the character; the route still returns 200 so
    the UI can render the new failure state. Mock mode short-circuits
    via PR AS's existing helper to ``mock_verified`` + ``match``.
    """
    record = store.get(character_id)
    if not record:
        raise HTTPException(status_code=404, detail="character not found")
    if not record.runway_avatar_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "no Runway avatar bound to this character yet — "
                "create the avatar before refreshing its status."
            ),
        )
    if not record.custom_voice_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "no custom voice cloned for this character yet — "
                "drift comparison requires both ids."
            ),
        )

    state = fetch_avatar_voice(
        record.runway_avatar_id,
        settings,
        avatar_is_mock=(record.runway_avatar_status == "mock"),
        expected_voice_id=record.custom_voice_id,
    )
    verified_at = (
        datetime.now(timezone.utc)
        if state.status in {"verified", "mock_verified"}
        else None
    )
    drift_status = compute_voice_drift_status(
        record.custom_voice_id, state.resolved_id, state.status,
    )
    updated = store.update(
        character_id,
        # NOTE: the PR AQ patch fields are intentionally not touched
        # — this route is verify-only. patch_status / patched_at
        # remain whatever the prior PATCH set them to.
        avatar_voice_resolved_type=state.resolved_type,
        avatar_voice_resolved_id=state.resolved_id,
        avatar_voice_resolved_label=state.resolved_label,
        avatar_voice_verify_status=state.status,
        avatar_voice_verified_at=(verified_at.isoformat() if verified_at else None),
        avatar_voice_verify_error=state.error,
        avatar_voice_drift_status=drift_status,
    )
    logger.info(
        "character %s refresh-avatar-voice -> verify=%s drift=%s",
        character_id, state.status, drift_status,
    )
    # PR BB — record the refresh in the audit trail. ``before`` is
    # the prior resolved id (so the operator can see drift before
    # vs after); ``after_voice_id`` stays None because refresh never
    # mutates the bind itself.
    _append_voice_history_safe(
        store,
        character_id,
        action="refresh",
        before_voice_id=record.avatar_voice_resolved_id,
        after_voice_id=None,
        resolved_voice_id=state.resolved_id,
        drift_status=drift_status,
        status=state.status,
        error=state.error,
        mock_mode=(state.status == "mock_verified"),
    )
    return updated or record


# ---- PR AX — Refresh missing cloned voice preview ------------------
#
# Wires the existing PR AR `fetch_voice_preview` helper to a small
# operator-facing route so a missing `custom_voice_preview_url` can
# be re-fetched without re-uploading audio. Read-only relative to
# the avatar binding (no PATCH); only the character's preview URL
# field is touched, and only when Runway returns a fresh value.


@router.post("/{character_id}/refresh-voice-preview", response_model=Character)
def post_refresh_voice_preview(
    character_id: str,
    settings: Settings = Depends(get_settings),
    store: CharacterStore = Depends(_store),
) -> Character:
    """PR AX — re-fetch the cloned voice's `previewUrl` from Runway
    without cloning again.

    Failure modes:
    - 404 — character not found.
    - 409 — character has no cloned voice yet.
    - 200 with unchanged record — Runway returned no preview URL
      (mock mode short-circuits here; real-mode failures also do).
      The existing URL (if any) is preserved.
    """
    record = store.get(character_id)
    if not record:
        raise HTTPException(status_code=404, detail="character not found")
    if not record.custom_voice_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "no custom voice cloned for this character yet — "
                "upload or record an audio sample first."
            ),
        )

    fresh_url = fetch_voice_preview(record.custom_voice_id, settings)
    if fresh_url:
        # Persist the freshly-fetched preview URL.
        updated = store.update(
            character_id,
            custom_voice_preview_url=fresh_url,
        )
        logger.info(
            "character %s voice preview refreshed -> %s",
            character_id, fresh_url,
        )
        return updated or record

    # No URL surfaced (mock mode, real-mode network/upstream failure,
    # or Runway hasn't generated one yet). Preserve the existing URL
    # rather than clearing it; return the unchanged record so the UI
    # can render a friendly "still unavailable" state without losing
    # whatever audio was already playable.
    logger.info(
        "character %s voice preview refresh: no URL surfaced (existing preserved)",
        character_id,
    )
    return record


@router.post("/{character_id}/metadata", response_model=Character)
def post_character_metadata(
    character_id: str,
    body: MetadataPatchBody,
    store: CharacterStore = Depends(_store),
) -> Character:
    """PR CK — merge a metadata patch onto an existing Character.

    The new multi-step Create Spokesperson flow uses this to
    persist ``audience_vibe`` / ``creation_flow`` /
    ``visual_style_chips`` / ``speaking_energy`` into the
    Character.metadata free-form dict without per-field columns.
    Existing keys not mentioned in the patch stay; explicit
    ``null`` values delete; new keys are added.

    Failure modes:
    - 404 — character not found.
    - 422 — pydantic validation (max payload size).
    - 413 — patch too large (>32 keys or >4 KB serialised).
    """
    record = store.get(character_id)
    if not record:
        raise HTTPException(status_code=404, detail="character not found")

    patch = body.metadata or {}
    if len(patch) > 32:
        raise HTTPException(
            status_code=413,
            detail=f"metadata patch too large ({len(patch)} keys; max 32)",
        )
    # Deep-ish guard: serialised size cap.
    import json as _json  # noqa: WPS433
    if len(_json.dumps(patch, default=str)) > 4 * 1024:
        raise HTTPException(
            status_code=413,
            detail="metadata patch too large (>4 KB serialised)",
        )

    merged = dict(record.metadata or {})
    for k, v in patch.items():
        if v is None:
            merged.pop(k, None)
        else:
            merged[k] = v

    updated = store.update(character_id, metadata=merged)
    if not updated:
        raise HTTPException(status_code=404, detail="character not found")
    logger.info(
        "character %s metadata patched (%d keys)",
        character_id,
        len(patch),
    )
    return updated


@router.post("/{character_id}/identity", response_model=Character)
def post_character_identity(
    character_id: str,
    body: IdentityPatchBody,
    store: CharacterStore = Depends(_store),
) -> Character:
    """PR EN — partial update of the editable Identity fields.

    Surfaced by the v2 Identity panel so the operator can revise the
    spokesperson's ``personality`` cue (highest-leverage field — it
    flows straight into the realtime session's system prompt),
    ``voice_preset`` (bound on the next avatar create / apply), or
    ``subject`` (one-line description) without a full character
    recreate.

    Failure modes:
    - 404 — character not found.
    - 400 — voice_preset not in SUPPORTED_VOICE_PRESETS.
    - 422 — pydantic validation (max lengths).
    """
    record = store.get(character_id)
    if not record:
        raise HTTPException(status_code=404, detail="character not found")

    patch: dict[str, Any] = {}
    if body.personality is not None:
        patch["personality"] = body.personality.strip() or None
    if body.subject is not None:
        patch["subject"] = body.subject.strip() or None
    if body.voice_preset is not None:
        preset = body.voice_preset.strip().lower()
        if not preset:
            raise HTTPException(
                status_code=400,
                detail="voice_preset cannot be empty",
            )
        if preset not in SUPPORTED_VOICE_PRESETS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"unsupported voice_preset '{body.voice_preset}'. "
                    f"supported: {sorted(SUPPORTED_VOICE_PRESETS)}"
                ),
            )
        patch["voice_preset"] = preset

    if not patch:
        return record

    updated = store.update(character_id, **patch)
    if not updated:
        raise HTTPException(status_code=404, detail="character not found")
    logger.info(
        "character %s identity patched (%s)",
        character_id,
        ", ".join(sorted(patch.keys())),
    )
    return updated


@router.get("/{character_id}/portrait")
def get_character_portrait(
    character_id: str,
    store: CharacterStore = Depends(_store),
) -> FileResponse:
    path = store.portrait_path(character_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="no portrait for this character")
    return FileResponse(
        str(path),
        media_type="image/png",
        filename=f"adspark-character-{character_id}.png",
    )


# ---- PR EX — Act-Two character_performance probe ------------------
#
# Wraps the CLI probe (`scripts/probe-character-performance.py`) as
# a real backend route so the frontend can record + fire + display
# the result without round-tripping through the terminal. Operator
# records a 5-10s performance video in the browser, POSTs it here,
# the route fires `POST /v1/character_performance` with the
# character's cached portrait as the `character.uri` and the
# uploaded video as the `reference.uri`, polls to completion, and
# downloads the output to `backend/data/characters/<id>-act-two-
# <ts>.mp4`. Returned `output_url` is a same-origin path the
# frontend can plug into `<video src>` directly.

_MAX_PERFORMANCE_BYTES = 8 * 1024 * 1024  # 8 MB cap on the upload
_ACT_TWO_POLL_DEADLINE_S = 300


class ActTwoProbeResult(BaseModel):
    """Response from the Act-Two probe route."""

    status: str  # "succeeded" | "failed"
    task_id: Optional[str] = None
    output_url: Optional[str] = None  # same-origin /api/characters/{id}/act-two-output/{name}
    output_filename: Optional[str] = None
    output_duration_s: Optional[float] = None
    output_bytes: Optional[int] = None
    elapsed_s: Optional[float] = None
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None


@router.post(
    "/{character_id}/act-two-probe", response_model=ActTwoProbeResult,
)
async def post_act_two_probe(
    character_id: str,
    performance: UploadFile = File(..., description="5-10s performance video (≤8 MB)"),
    settings: Settings = Depends(get_settings),
    store: CharacterStore = Depends(_store),
) -> ActTwoProbeResult:
    """PR EX — fire `POST /v1/character_performance` against the
    character's cached portrait and an operator-recorded performance
    video. The route handles upload, base64 encoding, task polling,
    and result download. Returns a same-origin URL the frontend can
    plug straight into `<video src>`.

    Failure modes:
    - 404 — character not found.
    - 409 — character has no cached portrait.
    - 413 — performance video exceeds the 8 MB upload cap.
    - 422 — empty / unreadable performance body.
    - 502 — Runway upstream task failure (returns ActTwoProbeResult
      with status="failed" + failure_code).
    - 503 — mock mode (no real Runway key to probe with).
    """
    if settings.runway_mock:
        raise HTTPException(
            status_code=503,
            detail=(
                "Act-Two probe requires a real Runway API key. "
                "Mock mode is unsupported (no deterministic placeholder)."
            ),
        )

    record = store.get(character_id)
    if not record:
        raise HTTPException(status_code=404, detail="character not found")

    portrait = store.portrait_path(character_id)
    if not portrait.exists() or portrait.stat().st_size == 0:
        raise HTTPException(
            status_code=409,
            detail=(
                "character has no cached portrait — generate one first "
                "via POST /generate-portrait."
            ),
        )

    perf_bytes = await performance.read()
    if not perf_bytes:
        raise HTTPException(status_code=422, detail="performance video is empty")
    if len(perf_bytes) > _MAX_PERFORMANCE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"performance video is {len(perf_bytes):,} bytes "
                f"(cap {_MAX_PERFORMANCE_BYTES:,}). Trim to ≤10 seconds "
                f"or lower resolution."
            ),
        )

    mime = (performance.content_type or "").lower().strip() or "video/webm"

    import base64 as _b64
    import subprocess as _sp
    import tempfile as _tmp
    import time as _time
    import httpx as _httpx

    # PR EX follow-up — browser MediaRecorder produces WebM files
    # whose EBML duration header is UNKNOWN (the spec doesn't require
    # the recorder to seek back and patch it at stop time). Browser
    # video players infer duration by seeking to the end; Runway's
    # `character_performance` validator reads the header field
    # directly and 400s with "Video duration could not be determined."
    # Fix: transcode the upload to MP4 via ffmpeg before forwarding.
    # ffmpeg's writer fills in the moov atom + duration correctly.
    # Same pattern as the storyboard / dialogue finishing layer.
    perf_to_send_bytes = perf_bytes
    perf_to_send_mime = mime
    if "webm" in mime or "matroska" in mime:
        try:
            with _tmp.NamedTemporaryFile(suffix=".webm", delete=False) as src:
                src.write(perf_bytes)
                src_path = src.name
            with _tmp.NamedTemporaryFile(suffix=".mp4", delete=False) as dst:
                dst_path = dst.name
            # Transcode H.264 + (no audio — we requested video-only
            # getUserMedia in the modal). `-movflags +faststart`
            # writes the moov atom up front so Runway can read
            # duration without scanning the whole file.
            # PR EX follow-up — quality-tuned transcode. The previous
            # `-preset veryfast` produced low-bitrate output that
            # appears to lose enough facial detail for Runway's face
            # detector to reject (NO_FACE_FOUND even on recordings
            # where the operator's face is clearly visible in the
            # source). High-quality preset + visually-lossless CRF +
            # standard 30fps + High profile / Level 4.0 (broadest
            # compatibility) should give the detector everything it
            # needs. Trade: ~3-5s more transcode time for a 8-10s
            # source. Acceptable since the operator is already
            # waiting 30-90s for Runway anyway.
            _sp.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-i", src_path,
                    "-c:v", "libx264",
                    "-preset", "slow",         # was: veryfast
                    "-crf", "18",              # visually-lossless (default 23 was too lossy)
                    "-pix_fmt", "yuv420p",
                    "-profile:v", "high",
                    "-level", "4.0",
                    "-r", "30",                # force 30fps (webcam timing can be uneven)
                    "-an",                     # video-only
                    "-movflags", "+faststart",
                    dst_path,
                ],
                check=True, capture_output=True, text=True, timeout=60,
            )
            perf_to_send_bytes = Path(dst_path).read_bytes()
            perf_to_send_mime = "video/mp4"
            # Log the transcoded dimensions/duration via ffprobe so
            # we can correlate Runway failures with what we actually
            # sent. Best-effort — failure here doesn't block.
            transcoded_meta = "(ffprobe failed)"
            try:
                meta_out = _sp.run(
                    [
                        "ffprobe", "-v", "error",
                        "-select_streams", "v:0",
                        "-show_entries", "stream=width,height,r_frame_rate,duration",
                        "-of", "default=noprint_wrappers=1",
                        dst_path,
                    ],
                    check=True, capture_output=True, text=True, timeout=10,
                )
                transcoded_meta = meta_out.stdout.strip().replace("\n", " ")
            except Exception:
                pass
            logger.info(
                "act-two transcode webm→mp4 character=%s in=%d bytes out=%d bytes meta=[%s]",
                character_id, len(perf_bytes), len(perf_to_send_bytes), transcoded_meta,
            )
            # Cleanup temp files (best-effort).
            for p in (src_path, dst_path):
                try:
                    Path(p).unlink(missing_ok=True)
                except Exception:
                    pass
        except _sp.CalledProcessError as exc:
            logger.warning(
                "act-two transcode failed character=%s err=%s",
                character_id, exc.stderr[:300] if exc.stderr else exc,
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    f"ffmpeg transcode of performance video failed: "
                    f"{(exc.stderr or '').strip()[:300]}"
                ),
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=500,
                detail=(
                    "ffmpeg not on PATH — required to transcode browser "
                    "WebM uploads so Runway can read the duration."
                ),
            )

    portrait_b64 = _b64.b64encode(portrait.read_bytes()).decode("ascii")
    portrait_uri = f"data:image/png;base64,{portrait_b64}"
    perf_b64 = _b64.b64encode(perf_to_send_bytes).decode("ascii")
    perf_uri = f"data:{perf_to_send_mime};base64,{perf_b64}"

    body = {
        "model": "act_two",
        "character": {"type": "image", "uri": portrait_uri},
        "reference": {"type": "video", "uri": perf_uri},
    }

    headers = {
        "Authorization": f"Bearer {settings.runway_api_key}",
        "X-Runway-Version": settings.runway_api_version,
        "Content-Type": "application/json",
    }
    create_url = f"{settings.runway_api_base}/v1/character_performance"

    logger.info(
        "act-two-probe character=%s portrait_bytes=%d performance_bytes=%d mime=%s",
        character_id, portrait.stat().st_size, len(perf_bytes), mime,
    )

    fire_t0 = _time.time()
    with _httpx.Client(timeout=60.0) as client:
        resp = client.post(create_url, headers=headers, json=body)
    if resp.status_code != 200:
        logger.warning(
            "act-two create failed character=%s status=%s body=%s",
            character_id, resp.status_code, resp.text[:400],
        )
        raise HTTPException(
            status_code=502,
            detail=(
                f"character_performance create failed: "
                f"{resp.status_code} {resp.text[:400]}"
            ),
        )
    created = resp.json()
    task_id = created.get("id")
    if not task_id:
        raise HTTPException(
            status_code=502,
            detail=f"character_performance missing task id: {created}",
        )
    logger.info("act-two task created character=%s task=%s", character_id, task_id)

    # Poll until terminal
    poll_url = f"{settings.runway_api_base}/v1/tasks/{task_id}"
    deadline = _time.time() + _ACT_TWO_POLL_DEADLINE_S
    payload: dict = created
    last_status = ""
    with _httpx.Client(timeout=20.0) as client:
        while _time.time() < deadline:
            r = client.get(poll_url, headers=headers)
            r.raise_for_status()
            payload = r.json()
            status = (payload.get("status") or "").upper()
            if status != last_status:
                logger.info("act-two task %s -> %s", task_id, status)
                last_status = status
            if status in {"SUCCEEDED", "FAILED", "CANCELED"}:
                break
            _time.sleep(5)
        else:
            raise HTTPException(
                status_code=502,
                detail=f"act-two task {task_id} timed out after {_ACT_TWO_POLL_DEADLINE_S}s",
            )

    elapsed = _time.time() - fire_t0
    status = (payload.get("status") or "").upper()
    if status != "SUCCEEDED":
        failure_message = payload.get("failure") or payload.get("error") or "unknown failure"
        failure_code = payload.get("failureCode") or "UNKNOWN"
        logger.warning(
            "act-two task %s terminal=%s code=%s msg=%s",
            task_id, status, failure_code, failure_message,
        )
        return ActTwoProbeResult(
            status="failed",
            task_id=task_id,
            elapsed_s=round(elapsed, 1),
            failure_code=str(failure_code),
            failure_message=str(failure_message),
        )

    # Download the output to a local cache so it survives the
    # presigned URL expiry. Same pattern as the portrait + host clip
    # caches (PR F).
    output_urls = payload.get("output") or []
    out_url = next((u for u in output_urls if isinstance(u, str)), None)
    if not out_url:
        raise HTTPException(
            status_code=502,
            detail=f"act-two SUCCEEDED but no output URL: {payload}",
        )

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_filename = f"{character_id}-act-two-{ts}.mp4"
    out_path = Path(settings.data_path) / "characters" / out_filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    downloaded_bytes = 0
    with _httpx.stream("GET", out_url, timeout=120.0, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(out_path, "wb") as fh:
            for chunk in resp.iter_bytes():
                downloaded_bytes += len(chunk)
                fh.write(chunk)

    # ffprobe-derive the output duration so the frontend can render
    # a "5.2s · 4.1 MB" caption without doing it itself.
    out_duration: Optional[float] = None
    try:
        import subprocess as _sp
        result = _sp.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(out_path),
            ],
            check=True, capture_output=True, text=True, timeout=10,
        )
        out_duration = float(result.stdout.strip() or 0.0)
    except Exception as exc:  # pragma: no cover — ffprobe diagnostic
        logger.warning("ffprobe failed on act-two output: %s", exc)

    output_url = f"/api/characters/{character_id}/act-two-output/{out_filename}"
    logger.info(
        "act-two probe success character=%s task=%s elapsed=%.1fs out=%s (%d bytes, %.2fs)",
        character_id, task_id, elapsed, out_filename, downloaded_bytes,
        out_duration or 0.0,
    )
    return ActTwoProbeResult(
        status="succeeded",
        task_id=task_id,
        output_url=output_url,
        output_filename=out_filename,
        output_duration_s=out_duration,
        output_bytes=downloaded_bytes,
        elapsed_s=round(elapsed, 1),
    )


@router.get("/{character_id}/act-two-output/{filename}")
def get_act_two_output(
    character_id: str,
    filename: str,
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    """PR EX — serve a cached Act-Two probe output back to the
    frontend's `<video src>`. Same pattern as the portrait route.
    Path-traverse guarded by Pydantic-validated filename + prefix
    check below.
    """
    # Defensive: only serve files matching the expected name pattern.
    if "/" in filename or ".." in filename or not filename.endswith(".mp4"):
        raise HTTPException(status_code=400, detail="invalid filename")
    if not filename.startswith(character_id):
        raise HTTPException(status_code=403, detail="filename / character mismatch")
    path = Path(settings.data_path) / "characters" / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="no such act-two output")
    return FileResponse(
        str(path),
        media_type="video/mp4",
        filename=filename,
    )


@router.delete("/{character_id}", response_model=dict)
def delete_character(
    character_id: str,
    store: CharacterStore = Depends(_store),
) -> dict:
    """Local delete only — does NOT call Runway DELETE /v1/avatars.
    Cached portrait + thumbnail files are removed; the user can run
    DELETE /v1/avatars/{id} via the Runway dashboard if they want
    the avatar entirely gone.
    """
    if not store.delete(character_id):
        raise HTTPException(status_code=404, detail="character not found")
    store.portrait_path(character_id).unlink(missing_ok=True)
    store.thumbnail_path(character_id).unlink(missing_ok=True)
    return {"ok": True, "id": character_id}


# ---- PR CX — Knowledge sources (manual paste, no embeddings) -----
#
# The Knowledge tab in the Spokesperson workspace persists short
# operator-pasted notes (brand voice, product details, FAQs, audience
# facts) on the Character record. The lane surfaces them next to
# the script editor as a reference panel — no RAG, no embeddings, no
# Runway calls. Two routes: append + delete. Both return the updated
# Character so the UI's local slice stays in sync without re-fetch.


@router.post("/{character_id}/knowledge", response_model=Character)
def post_knowledge_source(
    character_id: str,
    body: KnowledgeSourceCreate,
    store: CharacterStore = Depends(_store),
) -> Character:
    record = store.get(character_id)
    if not record:
        raise HTTPException(status_code=404, detail="character not found")
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "id": uuid.uuid4().hex[:12],
        "title": body.title.strip(),
        "source_type": body.source_type,
        "content": body.content.strip(),
        "created_at": now,
        "updated_at": now,
    }
    updated = store.append_knowledge_source(character_id, entry)
    if not updated:
        raise HTTPException(status_code=404, detail="character not found")
    logger.info(
        "character %s knowledge source added id=%s title=%r type=%s content_len=%d",
        character_id, entry["id"], entry["title"][:40],
        entry["source_type"], len(entry["content"]),
    )
    return updated


@router.delete(
    "/{character_id}/knowledge/{source_id}", response_model=Character
)
def delete_knowledge_source(
    character_id: str,
    source_id: str,
    store: CharacterStore = Depends(_store),
) -> Character:
    record = store.get(character_id)
    if not record:
        raise HTTPException(status_code=404, detail="character not found")
    updated = store.delete_knowledge_source(character_id, source_id)
    if not updated:
        raise HTTPException(status_code=404, detail="knowledge source not found")
    logger.info(
        "character %s knowledge source removed id=%s",
        character_id, source_id,
    )
    return updated


# ---- PR EM-b — Cross-session memory routes ----------------------------
#
# Three operator-facing routes on top of the PR EM-a foundation:
#   - GET    /memory               list current entries
#   - POST   /memory/ingest        fire every registered source
#   - DELETE /memory/{entry_id}    operator cleanup
#   - POST   /memory/compose       compose Markdown body, optionally
#                                  publish to Runway as a document
#
# Routes here are deliberately thin — they just dispatch into
# `MemoryOrchestrator` (PR EM-a). All the architecture lives in
# `services/memory/`; the routes are an API skin over it.


class MemoryEntryView(BaseModel):
    """API projection of `MemoryEntry`. Same shape as the model but
    excludes `embedding` (large, not useful to clients today) so the
    JSON payloads stay light. Add back when Phase 3 wants to expose
    embedding diagnostics."""

    id: str
    character_id: str
    campaign_id: Optional[str]
    source_type: str
    source_id: Optional[str]
    title: str
    content: str
    tags: list[str]
    metadata: dict
    created_at: str
    updated_at: str


class MemoryIngestBody(BaseModel):
    """Optional body for `POST /memory/ingest`. When `campaign_id` is
    set the orchestrator scopes campaign-only sources (e.g.
    TranscriptMemorySource which reads the campaign's transcript
    history) to that campaign."""

    campaign_id: Optional[str] = None


class MemoryIngestResponse(BaseModel):
    added: int
    per_source: dict
    errors: list


class MemoryListResponse(BaseModel):
    character_id: str
    entries: list[MemoryEntryView]
    total_chars: int


class MemoryComposeBody(BaseModel):
    """Body for `POST /memory/compose`. `publish` defaults to False
    so dry-run preview is the safe operation; the operator opts in to
    Runway upload explicitly. `campaign_id` scopes which entries are
    included (character-wide + campaign-scoped)."""

    campaign_id: Optional[str] = None
    publish: bool = False


class MemoryComposeResponse(BaseModel):
    character_id: str
    campaign_id: Optional[str]
    body: str
    included_count: int
    body_chars: int
    document_id: Optional[str] = None
    published: bool = False
    error: Optional[str] = None


def _to_view(entry) -> MemoryEntryView:
    return MemoryEntryView(
        id=entry.id,
        character_id=entry.character_id,
        campaign_id=entry.campaign_id,
        source_type=entry.source_type,
        source_id=entry.source_id,
        title=entry.title,
        content=entry.content,
        tags=list(entry.tags or []),
        metadata=dict(entry.metadata or {}),
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


@router.get("/{character_id}/memory", response_model=MemoryListResponse)
def get_character_memory(
    character_id: str,
    campaign_id: Optional[str] = None,
    source_type: Optional[str] = None,
    settings: Settings = Depends(get_settings),
    store: CharacterStore = Depends(_store),
) -> MemoryListResponse:
    """List the current memory entries for a character. Supports two
    optional query filters: `campaign_id` (scope to character-wide +
    matching campaign), `source_type` (filter to one source).

    Returns entries sorted by `updated_at` descending — most recent
    first. Each entry's char_count contributes to `total_chars` so
    the UI can show a budget bar against Runway's 50K-token doc cap.
    """
    if not store.get(character_id):
        raise HTTPException(status_code=404, detail="character not found")

    from ..services.memory import get_orchestrator
    orch = get_orchestrator(settings)
    entries = orch.store.list(
        character_id=character_id,
        campaign_id=campaign_id,
        source_type=source_type,
    )
    return MemoryListResponse(
        character_id=character_id,
        entries=[_to_view(e) for e in entries],
        total_chars=orch.store.total_chars(character_id),
    )


@router.post(
    "/{character_id}/memory/ingest", response_model=MemoryIngestResponse,
)
def post_character_memory_ingest(
    character_id: str,
    body: Optional[MemoryIngestBody] = None,
    settings: Settings = Depends(get_settings),
    store: CharacterStore = Depends(_store),
) -> MemoryIngestResponse:
    """Fire every registered MemorySource for this character.

    Phase 2 default sources (per PR EM-a):
      - OperatorNoteSource   — mirrors Character.knowledge_sources
      - TranscriptMemorySource — past realtime transcripts (per-campaign)

    Each source dedups its own entries via `(source_type, source_id)`
    so this route is safe to call repeatedly; re-ingest of the same
    upstream record replaces the prior entry, doesn't duplicate.
    """
    if not store.get(character_id):
        raise HTTPException(status_code=404, detail="character not found")
    from ..services.memory import get_orchestrator
    orch = get_orchestrator(settings)
    result = orch.ingest_from_all_sources(
        character_id,
        campaign_id=(body.campaign_id if body else None),
        settings=settings,
    )
    logger.info(
        "memory ingest character=%s campaign=%s added=%d errors=%d",
        character_id,
        body.campaign_id if body else None,
        result["added"],
        len(result["errors"]),
    )
    return MemoryIngestResponse(**result)


@router.delete(
    "/{character_id}/memory/{entry_id}", response_model=dict,
)
def delete_character_memory_entry(
    character_id: str,
    entry_id: str,
    settings: Settings = Depends(get_settings),
    store: CharacterStore = Depends(_store),
) -> dict:
    """Operator cleanup. Idempotent — returns `{deleted: false}` when
    the entry was already gone, matching the campaign delete shape."""
    if not store.get(character_id):
        raise HTTPException(status_code=404, detail="character not found")
    from ..services.memory import get_orchestrator
    orch = get_orchestrator(settings)
    deleted = orch.store.delete(entry_id)
    logger.info(
        "memory entry deleted character=%s entry=%s deleted=%s",
        character_id, entry_id, deleted,
    )
    return {"deleted": deleted, "entry_id": entry_id}


class MemoryAttachBody(BaseModel):
    """Body for `POST /memory/attach`. Operator picks an existing
    memory-published document_id + a campaign owned by this
    character; the route updates the campaign's
    `runway_document_id` so the next realtime session attaches the
    memory document as RAG.

    Lives on the characters router (next to the other memory routes)
    for cohesion, even though the mutation lands on a Campaign row.
    """

    campaign_id: str = Field(..., min_length=8, max_length=64)
    document_id: str = Field(..., min_length=1, max_length=200)


class MemoryAttachResponse(BaseModel):
    character_id: str
    campaign_id: str
    document_id: str
    attached: bool
    campaign_business: Optional[str] = None


@router.post(
    "/{character_id}/memory/attach", response_model=MemoryAttachResponse,
)
def post_character_memory_attach(
    character_id: str,
    body: MemoryAttachBody,
    settings: Settings = Depends(get_settings),
    store: CharacterStore = Depends(_store),
) -> MemoryAttachResponse:
    """PR EM-d — attach a memory-published document to one of this
    character's campaigns. Sets `Campaign.runway_document_id` so the
    next realtime session attaches the memory as RAG via
    `documentIds`.

    Validates:
      - character exists
      - campaign exists AND is bound to this character (no cross-
        character contamination)

    Idempotent — re-attaching the same document_id is a no-op write.
    """
    if not store.get(character_id):
        raise HTTPException(status_code=404, detail="character not found")

    from ..services.storage import CampaignStore
    cs = CampaignStore(settings.data_path)
    camp = cs.get(body.campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail="campaign not found")
    if camp.character_id != character_id:
        raise HTTPException(
            status_code=403,
            detail=(
                f"campaign {body.campaign_id!r} is not bound to "
                f"character {character_id!r}; attach refused"
            ),
        )

    updated = cs.update_realtime_document_fields(
        body.campaign_id,
        runway_document_id=body.document_id,
        runway_document_status="ready",
        runway_document_error=None,
        runway_document_mock_mode=False,
    )
    logger.info(
        "memory document attached character=%s campaign=%s doc_id=%s",
        character_id, body.campaign_id, body.document_id,
    )
    return MemoryAttachResponse(
        character_id=character_id,
        campaign_id=body.campaign_id,
        document_id=body.document_id,
        attached=bool(updated),
        campaign_business=(updated.business if updated else camp.business),
    )


@router.post(
    "/{character_id}/memory/compose", response_model=MemoryComposeResponse,
)
def post_character_memory_compose(
    character_id: str,
    body: Optional[MemoryComposeBody] = None,
    settings: Settings = Depends(get_settings),
    store: CharacterStore = Depends(_store),
) -> MemoryComposeResponse:
    """Compose the accumulated memory into a Runway document body.

    `publish=false` (default): preview-only. Returns the Markdown
    body the composer produced + how many entries made the cut. No
    Runway upload, no campaign mutation.

    `publish=true`: also uploads the body to Runway as a document
    via the existing `documents_client.create_document` (PR AI),
    returns the new document id. The caller is responsible for
    attaching that id to the campaign's `runway_document_id` field
    via the campaigns router — the memory layer stays storage-only
    and doesn't reach into the campaign store.
    """
    record = store.get(character_id)
    if not record:
        raise HTTPException(status_code=404, detail="character not found")
    body = body or MemoryComposeBody()
    from ..services.memory import get_orchestrator
    orch = get_orchestrator(settings)

    composed_body, included = orch.compose_document_body(
        character_id,
        campaign_id=body.campaign_id,
        character_label=record.name,
    )
    response = MemoryComposeResponse(
        character_id=character_id,
        campaign_id=body.campaign_id,
        body=composed_body,
        included_count=len(included),
        body_chars=len(composed_body),
    )

    if body.publish:
        from ..services.documents_client import create_document
        result = create_document(
            name=f"memory:{character_id}",
            content=composed_body,
            settings=settings,
        )
        if result.status in {"ready", "mock"} and result.document_id:
            response.document_id = result.document_id
            response.published = True
        else:
            response.error = result.error or "publish failed"
        logger.info(
            "memory compose+publish character=%s status=%s doc_id=%s",
            character_id, result.status, result.document_id,
        )
    else:
        logger.info(
            "memory compose preview character=%s included=%d body_chars=%d",
            character_id, len(included), len(composed_body),
        )
    return response
