"""Runway realtime provider — R2 implementation.

Implements the create_session + poll_session methods on the
RealtimeProvider Protocol. The remaining four methods raise
`NotImplementedError` — they're R4 (documents), R5
(transcripts), R3 (end_session) work. Splitting them across
slices keeps R2 bounded.

The HTTP surface against Runway mirrors the hackathon
implementation in `realtime_avatar_client.py`, but stripped
of the `Campaign` coupling — this version takes primitives
(`avatar_id`, `personality`, `start_script`, etc) the way
the R0 scope-lock Protocol specifies.

Secrets handling: `provider_session_key` is the JWT-shaped
SDK token. NEVER logged. The `_redact` helper scrubs Bearer
tokens + JWT-like strings from any upstream response we log.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone

import httpx

from ...config import Settings
from . import (
    DocumentCreate,
    RealtimeProviderError,
    SessionCreate,
    SessionState,
    ToolDef,
    TranscriptResult,
)

logger = logging.getLogger(__name__)


_REALTIME_MODEL = "gwm1_avatars"
_PERSONALITY_MAX = 9500
_START_SCRIPT_MAX = 280
# Runway 400s the whole session-create when any tool description
# exceeds 1024 chars (`{path: ["tools", "[N]", ".description"],
# message: "Too big"}`). The SAFE cap leaves a small margin so the
# truncation lands cleanly on a sentence boundary.
_DESCRIPTION_MAX = 1024
_DESCRIPTION_SAFE = 1000

# Runway's session create returns NOT_READY initially; sessionKey
# only lands in the GET payload once the upstream session reaches
# READY (~1.5s typical, occasionally longer under load). Block in
# create_session until READY so the broker can persist the key on
# the DRAFT → CREATING → READY transition. Matches the working
# hackathon broker (`backend/app/services/realtime_avatar_client.py`).
_READY_POLL_INTERVAL_S = 0.5
_READY_POLL_TIMEOUT_S = 150.0


def _redact(text: str, limit: int = 200) -> str:
    """Scrub Bearer tokens + JWT-shaped strings before logging."""
    if not text:
        return ""
    cleaned = re.sub(r"Bearer\s+[A-Za-z0-9._\-]+", "Bearer <redacted>", text)
    cleaned = re.sub(
        r"\b(?:sk_|rwk_|key_|sessionKey)[A-Za-z0-9._\-]+",
        "<redacted>",
        cleaned,
    )
    cleaned = re.sub(r"\beyJ[A-Za-z0-9._\-]{20,}", "<redacted-jwt>", cleaned)
    return cleaned.replace("\n", " ").strip()[:limit]


class RunwayRealtimeProvider:
    """Runway-backed realtime provider. Implements create +
    poll for R2; raises on the deferred methods."""

    def __init__(self, settings: Settings) -> None:
        if not settings.runway_api_key:
            raise RealtimeProviderError(
                "RunwayRealtimeProvider requires RUNWAY_API_KEY. "
                "Either set the env var or use the mock provider."
            )
        self.settings = settings

    # ---- create_session -----------------------------------------

    def create_session(
        self,
        avatar_id: str,
        personality: str,
        start_script: str,
        document_ids: list[str],
        tools: list[ToolDef],
    ) -> SessionCreate:
        if not avatar_id:
            raise RealtimeProviderError("avatar_id is required")

        # Clip to Runway's documented ceilings. Sentence-boundary
        # trimming lives in the broker (R3) — at the provider
        # layer we just truncate to keep the wire safe.
        personality = (personality or "")[:_PERSONALITY_MAX]
        start_script = (start_script or "")[:_START_SCRIPT_MAX]

        # Runway's /v1/realtime_sessions requires `avatar` as a
        # nested object with `type` + `avatarId`. The earlier
        # flat `avatarId` shape returns
        # `{"path": ["avatar"], "message": "Invalid input: expected object,
        # received undefined"}`. Matches the working shape used by the
        # an earlier hackathon prototype broker.
        body: dict = {
            "model": _REALTIME_MODEL,
            "avatar": {"type": "custom", "avatarId": avatar_id},
        }
        if personality:
            body["personality"] = personality
        if start_script:
            body["startScript"] = start_script
        if document_ids:
            body["documentIds"] = list(document_ids)
        if tools:
            # Each tool entry needs the `client_event` discriminator;
            # `parameters` is held client-side by the SDK and is not
            # accepted in the create-session payload. Description is
            # capped at Runway's 1024-char limit to avoid a Too big
            # rejection silently dropping the entire tool catalog.
            wire_tools: list[dict] = []
            for t in tools:
                name = (t.name or "").strip()
                description = (t.description or "").strip()
                if not name or not description:
                    continue
                if len(description) > _DESCRIPTION_MAX:
                    logger.warning(
                        "tool %s description over Runway's %d-char cap "
                        "(%d chars); truncating to %d",
                        name, _DESCRIPTION_MAX, len(description),
                        _DESCRIPTION_SAFE,
                    )
                    cutoff = description[:_DESCRIPTION_SAFE]
                    last_period = cutoff.rfind(". ")
                    if last_period > _DESCRIPTION_SAFE // 2:
                        description = cutoff[: last_period + 1].rstrip()
                    else:
                        description = cutoff.rstrip()
                wire_tools.append({
                    "type": "client_event",
                    "name": name,
                    "description": description,
                })
            if wire_tools:
                body["tools"] = wire_tools

        url = f"{self.settings.runway_api_base}/v1/realtime_sessions"
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    url, headers=_headers(self.settings), json=body,
                )
        except httpx.HTTPError as exc:
            raise RealtimeProviderError(
                f"runway POST /v1/realtime_sessions failed: "
                f"{type(exc).__name__}"
            ) from exc

        if resp.status_code >= 400:
            logger.warning(
                "runway realtime create rc=%s body=%s",
                resp.status_code, _redact(resp.text),
            )
            raise RealtimeProviderError(
                f"runway returned {resp.status_code} on session create"
            )

        payload = resp.json()
        session_id = payload.get("id") or payload.get("sessionId") or ""
        if not session_id:
            raise RealtimeProviderError(
                "runway realtime create returned malformed payload "
                "(missing id)"
            )

        # Poll until READY. sessionKey lands in the GET payload only
        # once the upstream session is live; without the poll loop we
        # return an empty key and the broker can't pass it to the SPA.
        detail_url = f"{url}/{session_id}"
        deadline = time.time() + _READY_POLL_TIMEOUT_S
        last_status = "(unknown)"
        poll_count = 0
        try:
            with httpx.Client(timeout=15.0) as client:
                while time.time() < deadline:
                    poll_resp = client.get(detail_url, headers=_headers(self.settings))
                    if poll_resp.status_code >= 400:
                        raise RealtimeProviderError(
                            f"runway poll returned {poll_resp.status_code} "
                            f"after session create: {_redact(poll_resp.text)}"
                        )
                    payload = poll_resp.json()
                    last_status = (payload.get("status") or "").upper()
                    poll_count += 1
                    if last_status == "READY":
                        break
                    if last_status in {"FAILED", "CANCELLED"}:
                        raise RealtimeProviderError(
                            f"runway realtime create reached terminal "
                            f"status {last_status.lower()} (id={session_id})"
                        )
                    time.sleep(_READY_POLL_INTERVAL_S)
                else:
                    raise RealtimeProviderError(
                        f"runway realtime session {session_id} did not "
                        f"reach READY within {int(_READY_POLL_TIMEOUT_S)}s "
                        f"(last status: {last_status}; {poll_count} polls)"
                    )
        except httpx.HTTPError as exc:
            raise RealtimeProviderError(
                f"runway GET /v1/realtime_sessions/{session_id} failed during "
                f"create poll: {type(exc).__name__}"
            ) from exc

        session_key = (
            payload.get("sessionKey")
            or payload.get("session_key")
            or payload.get("clientSecret")
            or ""
        )
        if not session_key:
            raise RealtimeProviderError(
                "runway realtime create reached READY but no sessionKey in "
                "payload"
            )

        status = _normalize_status(payload.get("status"))
        expires_at = _coerce_iso(
            payload.get("expiresAt") or payload.get("expires_at"),
        )

        # Deliberately log session_id only — never session_key.
        logger.info(
            "runway realtime create session_id=%s avatar=%s status=%s",
            session_id, avatar_id, status,
        )

        return SessionCreate(
            session_id=session_id,
            session_key=session_key,
            status=status,
            expires_at=expires_at,
            avatar_id=avatar_id,
        )

    # ---- poll_session -------------------------------------------

    def poll_session(self, session_id: str) -> SessionState:
        if not session_id:
            raise RealtimeProviderError("session_id is required")
        url = (
            f"{self.settings.runway_api_base}"
            f"/v1/realtime_sessions/{session_id}"
        )
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, headers=_headers(self.settings))
        except httpx.HTTPError as exc:
            raise RealtimeProviderError(
                f"runway GET /v1/realtime_sessions/{session_id} failed: "
                f"{type(exc).__name__}"
            ) from exc

        if resp.status_code == 404:
            raise RealtimeProviderError(
                f"runway has no session {session_id}"
            )
        if resp.status_code >= 400:
            logger.warning(
                "runway realtime poll session=%s rc=%s body=%s",
                session_id, resp.status_code, _redact(resp.text),
            )
            raise RealtimeProviderError(
                f"runway returned {resp.status_code} on session poll"
            )

        payload = resp.json()
        return SessionState(
            session_id=session_id,
            status=_normalize_status(payload.get("status")),
            expires_at=_coerce_iso(
                payload.get("expiresAt") or payload.get("expires_at"),
            ),
            error_message=(payload.get("errorMessage") or "")[:500],
        )

    # ---- deferred methods (R3+ / R4 / R5) ----------------------

    def attach_documents(
        self, avatar_id: str, document_ids: list[str],
    ) -> None:
        """Attach knowledge documents to an avatar so future
        sessions pick them up by default.

        R4 — implemented but not used in the R4 session-
        create flow (documents are passed via
        ``document_ids`` on session_create directly). This
        method is the surface for the "attach docs to a
        running avatar" path that lands when the SPA
        surface (R8) supports doc swapping mid-session.
        """
        if not avatar_id:
            raise RealtimeProviderError("avatar_id is required")
        url = (
            f"{self.settings.runway_api_base}"
            f"/v1/avatars/{avatar_id}/documents"
        )
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(
                    url,
                    headers=_headers(self.settings),
                    json={"documentIds": list(document_ids or [])},
                )
        except httpx.HTTPError as exc:
            raise RealtimeProviderError(
                f"runway POST {url} failed: {type(exc).__name__}"
            ) from exc
        if resp.status_code >= 400:
            logger.warning(
                "runway attach_documents avatar=%s rc=%s body=%s",
                avatar_id, resp.status_code, _redact(resp.text),
            )
            raise RealtimeProviderError(
                f"runway returned {resp.status_code} on attach_documents"
            )

    def create_document(self, name: str, content: str) -> DocumentCreate:
        """Push a knowledge document body to Runway's
        ``/v1/documents``. Returns the upstream document_id
        the broker persists on
        ``RealtimeSession.provider_document_id``.

        Content cap is the caller's responsibility — see
        ``compose_realtime_document`` (shell side) which
        caps at Runway's 40k-char ceiling and reports
        ``truncated``."""
        if not name:
            raise RealtimeProviderError("name is required")
        if not content:
            raise RealtimeProviderError("content is required")

        url = f"{self.settings.runway_api_base}/v1/documents"
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    url,
                    headers=_headers(self.settings),
                    json={"name": name[:200], "content": content},
                )
        except httpx.HTTPError as exc:
            raise RealtimeProviderError(
                f"runway POST /v1/documents failed: {type(exc).__name__}"
            ) from exc

        if resp.status_code >= 400:
            logger.warning(
                "runway create_document name=%r rc=%s body=%s",
                name, resp.status_code, _redact(resp.text),
            )
            raise RealtimeProviderError(
                f"runway returned {resp.status_code} on create_document"
            )

        payload = resp.json()
        doc_id = (
            payload.get("id")
            or payload.get("documentId")
            or payload.get("document_id")
            or ""
        )
        if not doc_id:
            raise RealtimeProviderError(
                "runway create_document returned malformed payload "
                "(missing id)"
            )
        logger.info(
            "runway create_document doc_id=%s name=%r chars=%d",
            doc_id, name, len(content),
        )
        return DocumentCreate(document_id=doc_id)

    def fetch_transcript(self, session_id: str) -> TranscriptResult:
        """R5 — pull the post-session transcript.

        Runway's session id doubles as the conversation id
        for transcript retrieval (`GET
        /v1/avatar_conversations/<id>`). Returns the
        normalized transcript shape so the Django broker
        can persist it as a TRANSCRIPT Asset (contract
        rule 4 — same shape as V1's transcribe primitive
        output).

        Empty / 404 responses don't raise — they return an
        empty TranscriptResult so the broker can mark the
        transcript fetch as "no content recorded yet"
        without flipping the session to failed.
        """
        if not session_id:
            raise RealtimeProviderError("session_id is required")
        url = (
            f"{self.settings.runway_api_base}"
            f"/v1/avatar_conversations/{session_id}"
        )
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, headers=_headers(self.settings))
        except httpx.HTTPError as exc:
            raise RealtimeProviderError(
                f"runway GET /v1/avatar_conversations/{session_id} "
                f"failed: {type(exc).__name__}"
            ) from exc

        if resp.status_code == 404:
            # Conversation not recorded yet — empty result is
            # not a failure mode; operator can re-fetch later.
            logger.info(
                "runway fetch_transcript session=%s 404 (not recorded)",
                session_id,
            )
            return TranscriptResult(text="", segments=[])
        if resp.status_code >= 400:
            logger.warning(
                "runway fetch_transcript session=%s rc=%s body=%s",
                session_id, resp.status_code, _redact(resp.text),
            )
            raise RealtimeProviderError(
                f"runway returned {resp.status_code} on fetch_transcript"
            )

        try:
            payload = resp.json()
        except ValueError as exc:
            raise RealtimeProviderError(
                f"non-json transcript response: {exc!s}"[:200]
            ) from exc

        # Runway's session-level status can be "failed" with a
        # populated failureCode + empty transcript array — the same
        # response shape as a legitimately-short empty session, but
        # fundamentally different: the failed session is permanently
        # dead (`endedAt` null, no `recordingUrl`), so no retry /
        # wait / re-fetch will produce turns. Surface this as an
        # upstream error so the broker can flip the session to
        # FAILED instead of leaving the operator staring at a
        # "waiting for transcript…" UI forever. Mirrors the
        # hackathon broker's PR ER guard.
        upstream_status = (payload.get("status") or "").lower()
        if upstream_status == "failed":
            fcode = payload.get("failureCode") or "UNKNOWN"
            fmsg = payload.get("failure") or "session failed"
            logger.warning(
                "runway fetch_transcript session=%s upstream_failed "
                "code=%s msg=%s",
                session_id, fcode, _redact(str(fmsg)),
            )
            raise RealtimeProviderError(
                f"runway session marked failed [code={fcode}]: {fmsg}"
            )

        # Normalize. Runway's actual response shape uses the
        # `transcript` key (verified May 2026 against the
        # `/v1/avatar_conversations/<id>` endpoint). Earlier R5 code
        # only looked at `turns`/`messages`, which never matched —
        # every real session returned an empty transcript silently.
        # Accept all three keys for forward-compat.
        turns_raw = (
            payload.get("transcript")
            or payload.get("turns")
            or payload.get("messages")
            or []
        )
        segments: list[dict] = []
        text_parts: list[str] = []
        for raw in turns_raw:
            role = str(raw.get("role") or raw.get("speaker") or "")
            content = str(raw.get("text") or raw.get("content") or "").strip()
            ts = raw.get("timestamp") or raw.get("ts") or raw.get("createdAt")
            if not content:
                continue
            segments.append({"role": role, "text": content, "ts": ts})
            speaker = role.title() if role else "Speaker"
            text_parts.append(f"{speaker}: {content}")

        text = "\n".join(text_parts)
        logger.info(
            "runway fetch_transcript session=%s turns=%d chars=%d",
            session_id, len(segments), len(text),
        )
        return TranscriptResult(text=text, segments=segments)

    def end_session(self, session_id: str) -> None:
        """R3 — explicit session teardown. Best-effort; the
        broker marks the Django row ENDED regardless of
        upstream response. Most session lifecycles end via
        Runway's own expiry timer; this endpoint exists for
        the operator-initiated close path."""
        if not session_id:
            raise RealtimeProviderError("session_id is required")
        url = (
            f"{self.settings.runway_api_base}"
            f"/v1/realtime_sessions/{session_id}"
        )
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.delete(url, headers=_headers(self.settings))
        except httpx.HTTPError as exc:
            raise RealtimeProviderError(
                f"runway DELETE /v1/realtime_sessions/{session_id} failed: "
                f"{type(exc).__name__}"
            ) from exc

        # 404 + 410 are fine — session already gone is success
        # for our purposes.
        if resp.status_code in (200, 204, 404, 410):
            logger.info(
                "runway realtime end session_id=%s rc=%s",
                session_id, resp.status_code,
            )
            return
        logger.warning(
            "runway realtime end session=%s rc=%s body=%s",
            session_id, resp.status_code, _redact(resp.text),
        )
        raise RealtimeProviderError(
            f"runway returned {resp.status_code} on session end"
        )


# ---- helpers ----------------------------------------------------


def _headers(settings: Settings) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.runway_api_key}",
        "X-Runway-Version": settings.runway_api_version,
        "Content-Type": "application/json",
    }


def _normalize_status(value: object) -> str:
    """Normalize Runway's various status spellings to the
    DocumentStatus shape used by the Django broker."""
    raw = str(value or "").strip().lower()
    if raw in {"ready", "live"}:
        return "ready"
    if raw in {"creating", "pending"}:
        return "creating"
    if raw in {"not_ready", "notready", "preparing"}:
        return "not_ready"
    if raw in {"failed", "error"}:
        return "failed"
    if raw in {"ended", "closed", "expired"}:
        return "ended"
    return raw or "creating"


def _coerce_iso(value: object) -> str | None:
    """Best-effort ISO-8601 normalization."""
    if not value:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)
