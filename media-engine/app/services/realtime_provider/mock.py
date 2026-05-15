"""Deterministic mock realtime provider — R2.

Mirrors the V0 / V14 mock-mode pattern. Returns stub
payloads that the Django broker can persist + the SPA can
render against without hitting any external API. Useful for:

* Tests (`runway_mock=True` via empty API key fixture).
* Local dev workflows that don't want to burn Runway credits.
* CI runs that need deterministic output for snapshot
  comparisons.

The mock implements all six Protocol methods so R3-R5 slices
can wire them without re-touching this file. Each method
returns a payload structurally identical to what the real
Runway provider would return; only the values are fake.
"""
from __future__ import annotations

import hashlib
import time
from datetime import datetime, timedelta, timezone

from . import (
    DocumentCreate,
    SessionCreate,
    SessionState,
    ToolDef,
    TranscriptResult,
)


def _digest(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _iso_future(seconds: int = 600) -> str:
    return (
        datetime.now(tz=timezone.utc) + timedelta(seconds=seconds)
    ).isoformat()


class MockRealtimeProvider:
    """Deterministic stubs. Same key inputs → same outputs so
    tests can assert on session_id round-trip."""

    def create_session(
        self,
        avatar_id: str,
        personality: str,
        start_script: str,
        document_ids: list[str],
        tools: list[ToolDef],
    ) -> SessionCreate:
        digest = _digest(
            avatar_id, personality, start_script,
            ",".join(document_ids), ",".join(t.name for t in tools),
        )
        return SessionCreate(
            session_id=f"mock_session_{digest}",
            session_key=f"mock_session_key_{digest}",
            status="ready",  # mock skips creating → not_ready
            expires_at=_iso_future(),
            avatar_id=avatar_id,
        )

    def poll_session(self, session_id: str) -> SessionState:
        # Mock sessions are always immediately ready.
        return SessionState(
            session_id=session_id,
            status="ready",
            expires_at=_iso_future(),
        )

    def attach_documents(
        self, avatar_id: str, document_ids: list[str],
    ) -> None:
        # No-op in mock.
        return None

    def create_document(self, name: str, content: str) -> DocumentCreate:
        digest = _digest(name, content)
        return DocumentCreate(document_id=f"mock_doc_{digest}")

    def fetch_transcript(self, session_id: str) -> TranscriptResult:
        return TranscriptResult(
            text=f"[mock transcript for session {session_id}]\n"
                 "User: Hello.\n"
                 "Spokesperson: Hi! This is a mock-mode reply.\n",
            segments=[
                {"role": "user", "text": "Hello.", "ts": time.time() - 5},
                {
                    "role": "spokesperson",
                    "text": "Hi! This is a mock-mode reply.",
                    "ts": time.time() - 3,
                },
            ],
        )

    def end_session(self, session_id: str) -> None:
        return None
