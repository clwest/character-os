"""Asset Library v1 (SESSION 186, A2) — shared primitive→role mapping.

Single source of truth for ``Asset.role`` derivation. Used by:

* **Production primitive emit sites** in ``apps.compositions.primitives.*``
  (and ``apps.realtime.tasks.capture_transcript``) — every primitive stamps
  ``role`` on its ``PrimitiveResult`` / ``Asset`` at emit time so new rows
  arrive role-tagged. Contract rule 20 enforced by the coverage test in
  ``tests/test_primitive_role_coverage.py``.
* **Backfill management command**
  ``apps.compositions.management.commands.backfill_asset_roles`` — applies
  the same mapping to legacy ``RAW_UPLOAD`` rows.

The mapping itself moved here in SESSION 186 (A2) so production code and
backfill share one definition. The backfill command re-exports these
symbols for backwards-compat with imports that pre-date the move.
"""
from __future__ import annotations

from apps.compositions.models import Asset, AssetRole


# Heuristic table: source_spec.primitive_kind → target role.
# Add a row here when a new primitive lands (contract rule 20 —
# no new primitive emits without a role).
PRIMITIVE_TO_ROLE: dict[str, str] = {
    # Avatar foreground
    "generate_avatar_speech": AssetRole.TALKING_HEAD.value,
    "remove_avatar_background": AssetRole.TALKING_HEAD.value,
    # Scene / backdrop
    "generate_visual_clip": AssetRole.BACKDROP.value,
    "extend_visual_clip": AssetRole.BACKDROP.value,
    "concat_clips": AssetRole.BACKDROP.value,
    # Composite combiners
    "composite_video": AssetRole.COMPOSITE_OUTPUT.value,
    "mix_audio": AssetRole.COMPOSITE_OUTPUT.value,
    # Polish / post-composite refinement
    "add_captions": AssetRole.POLISH_OUTPUT.value,
    "add_intro_outro": AssetRole.POLISH_OUTPUT.value,
    "trim_clip": AssetRole.POLISH_OUTPUT.value,
    "reformat_clip": AssetRole.POLISH_OUTPUT.value,
    "style_remix": AssetRole.POLISH_OUTPUT.value,
    # SESSION 256 — image overlay layered on a base clip. Same
    # role family as the other post-composite polish primitives;
    # the output IS the base clip with an image decoration.
    "image_overlay": AssetRole.POLISH_OUTPUT.value,
    # Image (for keyframes / reference)
    "generate_image": AssetRole.REFERENCE_IMAGE.value,
    # Text / transcript
    "transcribe": AssetRole.TRANSCRIPT.value,
    "split_script": AssetRole.TRANSCRIPT.value,
    "realtime_transcript": AssetRole.TRANSCRIPT.value,
    # Standalone audio
    "design_voice": AssetRole.AUDIO_TRACK.value,
    "dub_audio": AssetRole.AUDIO_TRACK.value,
    "audio_extract": AssetRole.AUDIO_TRACK.value,
    # VO.1 — voiceover synthesis (TTS-only, no avatar pipeline).
    # Distinct role from AUDIO_TRACK so Asset Library filters can
    # surface VO clips separately (rule 1 + Q-vo-7).
    "synthesize_voiceover_audio": AssetRole.VOICEOVER_AUDIO.value,
    # VO.2 — voiceover splice. Static fallback is COMPOSITE_OUTPUT
    # (same shape as mix_audio); the primitive overrides at runtime
    # to propagate the base CLIP's role per the VO.0 spec
    # (talking_head stays talking_head).
    "overlay_audio_at_offset": AssetRole.COMPOSITE_OUTPUT.value,
    # Sandbox / experimental
    "smoke_keyframes": AssetRole.EXPERIMENT.value,
}


# SESSION 184 manually-inserted smoke outputs that lack
# primitive_kind. Hard-coded per ASSET_LIBRARY_V1.md
# §In-scope clarifications.
KNOWN_EXPERIMENT_UUID_PREFIXES: tuple[str, ...] = (
    "c21fdeec",  # veo3.1_fast smoke output
    "89a1ce5f",  # gen3a_turbo smoke output
)


def role_for_primitive_kind(primitive_kind: str | None) -> str | None:
    """Return the registered role for ``primitive_kind`` or ``None`` if
    the kind is unknown. Used by primitive emit sites that want to look
    up their own role by name (keeps the mapping single-sourced)."""
    if not primitive_kind:
        return None
    return PRIMITIVE_TO_ROLE.get(primitive_kind)


def derive_role(asset: Asset) -> str | None:
    """Return the target role for ``asset``, or ``None`` if no
    heuristic matches (operator review required).

    Looks at:

    1. The SESSION 184 hard-coded smoke UUID prefixes (which lack
       ``primitive_kind`` but were back-stamped as ``EXPERIMENT``).
    2. ``asset.source_spec["primitive_kind"]`` against
       :data:`PRIMITIVE_TO_ROLE`.
    """
    asset_uuid = str(asset.id)
    for prefix in KNOWN_EXPERIMENT_UUID_PREFIXES:
        if asset_uuid.startswith(prefix):
            return AssetRole.EXPERIMENT.value

    source_spec = asset.source_spec or {}
    primitive_kind = source_spec.get("primitive_kind")
    if primitive_kind and primitive_kind in PRIMITIVE_TO_ROLE:
        return PRIMITIVE_TO_ROLE[primitive_kind]

    return None


__all__ = [
    "PRIMITIVE_TO_ROLE",
    "KNOWN_EXPERIMENT_UUID_PREFIXES",
    "role_for_primitive_kind",
    "derive_role",
]
