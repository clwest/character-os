"""§19 Step 4.b — Prequalification-authoring value objects.

The three frozen dataclasses here are the caller's input to
``services.record_prequalification_representation`` (§17.10.a
Amendment 4). Each carries the factual result of one provider call
that produced a portrait / voice / realtime representation.

Discipline held here:

* **Provenance literal.** Each value object records what the provider
  actually returned — provider name, provider-side identifiers,
  execution mode used, whether the call was mock, and the raw
  response payload (for evidence preservation). Nothing is
  synthesized; nothing is disguised.
* **Provider-neutrality preserved.** These value objects cross the
  compatibility boundary into canonical writes. Provider-side
  identifiers stay inside ``GenerationRecord`` provenance fields
  when the orchestration lands them; no canonical model gains a
  provider-specific column.
* **Bounded lifetime.** Together with ``apps/identity/compat.py``,
  these dataclasses exist only during the growth window. Step 13
  of the ratified §19 sequence removes the three compatibility
  fields on ``Teammate`` and this module alongside them.

Callers in Step 4.d construct these from the media-engine client
result dataclasses (``AvatarCreateResult``, ``VoiceCloneResult``,
``PortraitCreateResult``, etc.) — one representation per input
that the authoring event actually touched. Slots the caller did
not touch pass ``None`` and are carried forward from the
current-approved canonical state per Amendment 4.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PortraitRepresentation:
    """A portrait produced by a real provider call.

    ``portrait_uri`` becomes the synthesized ``Asset.file_path`` on
    the canonical portrait reference. The compatibility mirror
    ``Teammate.portrait_path`` derives from that ``Asset.file_path``
    at sync time — no separate ``provider_portrait_id`` key is
    needed because the URI itself is the mirror value (Amendment 4
    provider-output convention).

    ``provider_response`` preserves the raw provider return for
    evidence. Recorded verbatim into
    ``GenerationRecord.prompt_snapshot['provider_response']``.
    """

    portrait_uri: str
    provider: str
    provider_model: str
    execution_mode: str
    execution_mode_actual: str
    mock_mode: bool
    provider_response: dict = field(default_factory=dict)


@dataclass(frozen=True)
class VoiceRepresentation:
    """A voice produced by a real provider call.

    ``provider_voice_id`` is what the compatibility adapter reads
    from ``GenerationRecord.prompt_snapshot['provider_voice_id']``
    to derive the ``Teammate.voice_id`` mirror. Recorded verbatim.

    ``voice_kind`` distinguishes preset selection (``'preset'``)
    from cloned voices (``'clone'``) — the Runway TTS provider
    handles both but the distinction is factually preserved for
    audit / evidence.
    """

    provider_voice_id: str
    provider: str
    provider_model: str
    execution_mode: str
    execution_mode_actual: str
    mock_mode: bool
    voice_kind: str  # "preset" | "clone" — factual, not derived
    provider_response: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RealtimeRepresentation:
    """A realtime avatar produced by a real provider call.

    ``provider_realtime_id`` is what the compatibility adapter
    reads from
    ``GenerationRecord.prompt_snapshot['provider_realtime_id']``
    to derive the ``Teammate.runway_avatar_id`` mirror. Recorded
    verbatim.

    Note: §17.10.a explicitly bars ``runway_avatar_id`` from
    permanent canonical schema. It lives here as a value-object
    field (used to build ``GenerationRecord`` provenance) and
    never appears on ``CharacterIdentity`` /
    ``CharacterIdentityVersion`` /
    ``CanonicalRealtimeReference`` /
    ``ApprovedRepresentationBundle`` columns.
    """

    provider_realtime_id: str
    provider: str
    provider_model: str
    execution_mode: str
    execution_mode_actual: str
    mock_mode: bool
    provider_response: dict = field(default_factory=dict)


__all__ = [
    "PortraitRepresentation",
    "VoiceRepresentation",
    "RealtimeRepresentation",
]
