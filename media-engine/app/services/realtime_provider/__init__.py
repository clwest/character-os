"""Realtime avatar provider abstraction — R2 (realtime arc).

Single named adapter per the R0 scope-lock contract rule 8.
The media-engine exposes one Protocol; v1 has one
implementation (Runway). Future providers (Synthesia,
HeyGen, etc.) drop in as one new file + a registry entry.
No code outside this package's ``get_provider`` should
branch on provider name.

R2 scope: implement ``create_session`` + ``poll_session``.
The remaining four methods (``attach_documents``,
``create_document``, ``fetch_transcript``,
``end_session``) have type stubs here and raise
``NotImplementedError`` in the v1 Runway impl until later
R-slices wire them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ...config import Settings


# ---- Provider-shared dataclasses --------------------------------


@dataclass(slots=True)
class ToolDef:
    """A tool the avatar may invoke during a session. Shape
    mirrors Runway's tool catalog spec."""

    name: str
    description: str
    parameters: dict = field(default_factory=dict)


@dataclass(slots=True)
class SessionCreate:
    """Result of ``create_session``. Carries the SDK-safe
    payload the browser needs to connect via WebRTC."""

    session_id: str
    # JWT-shaped opaque token. NEVER logged. The router
    # passes this through to Django which persists it on
    # ``RealtimeSession.provider_session_key``.
    session_key: str
    status: str  # 'creating' | 'not_ready' | 'ready' | 'failed'
    expires_at: str | None = None
    avatar_id: str | None = None


@dataclass(slots=True)
class SessionState:
    """Result of ``poll_session`` — same shape as
    ``SessionCreate`` minus ``session_key`` because the SDK
    already holds it from the create response."""

    session_id: str
    status: str
    expires_at: str | None = None
    error_message: str = ""


@dataclass(slots=True)
class DocumentCreate:
    """Result of ``create_document``. Returned to the Django
    broker which persists ``provider_document_id`` on the
    session."""

    document_id: str


@dataclass(slots=True)
class TranscriptResult:
    """Result of ``fetch_transcript``. Returned post-session
    and persisted as a TRANSCRIPT Asset (R5)."""

    text: str
    segments: list[dict] = field(default_factory=list)


# ---- Protocol ---------------------------------------------------


@runtime_checkable
class RealtimeProvider(Protocol):
    """Single named adapter — contract rule 8."""

    def create_session(
        self,
        avatar_id: str,
        personality: str,
        start_script: str,
        document_ids: list[str],
        tools: list[ToolDef],
    ) -> SessionCreate:
        """Create a live session. Returns SDK-safe payload."""
        ...

    def poll_session(self, session_id: str) -> SessionState:
        """Check session status — drives the
        creating → not_ready → ready transition."""
        ...

    def attach_documents(
        self, avatar_id: str, document_ids: list[str],
    ) -> None:
        """R4 — attach knowledge documents to an avatar so a
        future session_create picks them up."""
        ...

    def create_document(self, name: str, content: str) -> DocumentCreate:
        """R4 — push a knowledge document to the provider."""
        ...

    def fetch_transcript(self, session_id: str) -> TranscriptResult:
        """R5 — pull the post-session transcript."""
        ...

    def end_session(self, session_id: str) -> None:
        """R3 — explicit session teardown."""
        ...


# ---- Errors -----------------------------------------------------


class RealtimeProviderError(RuntimeError):
    """Wraps upstream / configuration failures. Routers map
    to HTTP error responses; the Django broker (R3) turns
    these into ``RealtimeSession.status='failed'`` rows."""


class RealtimeUnavailableError(RealtimeProviderError):
    """Configuration says realtime can't run right now —
    mock-mode without explicit allow, missing API key, etc.
    Maps to HTTP 503; operator can retry later or check
    config."""


# ---- Registry ---------------------------------------------------


def get_provider(name: str, settings: Settings) -> RealtimeProvider:
    """Look up a provider by name. v1 ships Runway + a mock.

    The mock returns deterministic stubs without hitting any
    upstream — used in tests + when ``settings.runway_mock``
    is True (no ``RUNWAY_API_KEY`` set).
    """
    if settings.runway_mock:
        from .mock import MockRealtimeProvider

        return MockRealtimeProvider()
    if name == "runway":
        from .runway import RunwayRealtimeProvider

        return RunwayRealtimeProvider(settings)
    raise RealtimeProviderError(
        f"unknown realtime provider {name!r}. "
        f"Registered: ['runway']"
    )


__all__ = [
    "DocumentCreate",
    "RealtimeProvider",
    "RealtimeProviderError",
    "RealtimeUnavailableError",
    "SessionCreate",
    "SessionState",
    "ToolDef",
    "TranscriptResult",
    "get_provider",
]
