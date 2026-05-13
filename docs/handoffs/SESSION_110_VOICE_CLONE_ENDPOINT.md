---
title: "Session 110 — Voice clone endpoint (/internal/voices/)"
date: 2026-05-13
status: complete
session: 110
previous_handoff: ./SESSION_109_VIDEO_PIPELINE_CELERY_REDIS.md
---

# Session 110 — Voice clone endpoint

## TL;DR

- **What shipped:** `POST /internal/voices/` on the media-engine,
  `MediaEngineClient.clone_voice(...)` on the Django shell, and a
  new `POST /api/spokespeople/{id}/clone-voice/` action on
  `SpokespersonViewSet` that ties them together. Inline /
  synchronous — Runway voice clones return in <10 s, so no Celery
  needed. Smoke test (`python manage.py smoke_voice`) passes in
  mock mode using a hermetic in-line silent WAV.
- **What's blocking next:** Nothing. The three major `/internal/*`
  verbs (avatars, videos, voices) are now all shipped — the
  contract is feature-complete enough for Phase 3 (SPA work) to
  start without further backend changes. Optional follow-ups:
  additional video kinds, stuck-row janitor, voice-preview re-fetch.
- **What's in a weird state:** Same pyright noise as the last four
  sessions (cross-app import resolution + DRF stub drift). The
  `pyrightconfig.json` slice is overdue — bumped to the top of the
  queued investigations list in `00-START-NEXT-SESSION.md`.

---

## What changed (file-by-file)

### `docs/design/MEDIA_ENGINE_INTERNAL_API.md`

Added the `POST /internal/voices/` section: pure JSON contract
(audio data URI in, voice id out), 15 MB cap matching the legacy
multipart route, mime allowlist, stateless contract (no local
cache — voices are cheap to re-clone, unlike portraits), mock-mode
behaviour. Updated the status table (`/internal/voices/` flagged
SESSION 110), the open questions (replaced "voice clone is next"
with a poll-route discussion for later), and the change log.

### `media-engine/app/routers/internal.py`

Added `POST /internal/voices/`. Reuses the existing
`voice_clone_client.clone_voice_from_audio` service so Runway-side
behaviour matches the legacy `POST /api/characters/{id}/clone-voice`
multipart route exactly — the only difference is transport (JSON
data URI vs multipart). Audio data URI parser tolerant of the wider
mime set Runway accepts: mp3, wav, m4a, webm, ogg, aac.

Same `{error, code}` error normalisation as the avatar + video
endpoints. New error codes: `invalid_data_uri`, `audio_too_large`,
`empty_audio`, `upstream_runway_error`.

### `shell/character_os/clients/media_engine.py`

Added `VoiceCloneResult` dataclass + `MediaEngineClient.clone_voice(
audio_data_uri, name?)`. Errors normalise through `MediaEngineError`.
Strict shape parsing — contract drift fails loud.

### `shell/apps/spokespeople/views.py`

New `clone_voice` DRF action at `POST /api/spokespeople/{id}/clone-voice/`.
Takes `{audio_data_uri, name?}`, forwards to the media-engine,
persists the returned `voice_id` onto the Spokesperson, returns
both the updated spokesperson and the Runway-hosted `preview_url`
so the SPA can play back the cloned voice. Preview URL is **not**
persisted on the Spokesperson — it's derived from Runway and
cheap to re-fetch via a future poll route.

### `shell/apps/spokespeople/management/commands/smoke_voice.py` (new)

`python manage.py smoke_voice`. Hermetic — builds a minimal RIFF
WAV header + 1 second of 16-bit mono silence at 8 kHz inline (no
fixture file). Auto-creates a spokesperson with a mock avatar if
the workspace doesn't have one (reuses the SESSION 108 path).
Calls the `clone_voice` action via a stub request, asserts the
voice id was persisted, reverts the change unless `--keep`.

Run output:

```
  ✓ media engine reachable (runway_mock=True)
  ✓ using spokesperson 'Smoke Test Spokesperson' (initial voice_id='vincent')
  ✓ clone_voice response status='mock' voice_id='mock_voice_...' preview_url=None
  ✓ Spokesperson row voice_id='mock_voice_...'
  ✓ reverted voice_id to 'vincent'
✓ smoke test PASSED
```

---

## Verification gates

- `python manage.py check` — 0 issues.
- `python manage.py migrate --check` — exit 0 (no schema changes;
  reuses existing `Spokesperson.voice_id`).
- FastAPI route count — 105 → 106 (added `POST /internal/voices/`).
- `python manage.py show_urls | grep clone-voice` — registers as
  `spokesperson-clone-voice`.
- `python manage.py smoke_voice` — PASSED.
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### The contract surface is feature-complete

After SESSION 110 the `/internal/*` surface covers the three verbs
the launch product needs:

- `POST /internal/avatars/` — synchronous, ~20 s real mode.
- `POST /internal/voices/` — synchronous, ~10 s real mode.
- `POST /internal/videos/` + `GET /internal/videos/{task_id}/` —
  fire-then-poll, 60-120 s real mode.

Phase 3 (SPA) can start without further backend changes. Optional
extensions (other video kinds, poll routes for avatar / voice when
async paths become useful) are additive — they don't reshape the
contract.

### The "preview URL not persisted" decision

The Runway voice clone response sometimes includes a `previewUrl`,
sometimes doesn't (race against Runway's voice preview rendering).
The legacy `Character` model persisted it as
`custom_voice_preview_url` + had a dedicated refresh route. The
new `Spokesperson` model deliberately doesn't — preview URLs are
derived state cheap enough to re-fetch when the SPA needs them,
and persisting them creates a stale-cache problem (Runway can
invalidate URLs over time).

If the SPA renders preview audio constantly, we'll need to
revisit. For now: return the URL in the action response, let the
SPA cache it client-side if it wants to.

### Why `voice_clone_client` reuse was the right move

The legacy multipart route already handles all the Runway edge
cases (audit trail, drift detection, voice apply to avatar,
retry semantics). Wrapping its `clone_voice_from_audio` public
entry rather than reimplementing means the Runway-side behaviour
is **identical** between the legacy `/api/*` SPA flow and the new
`/internal/*` Django flow. When Runway changes a response shape
or adds a status code, one fix updates both surfaces.

---

## SESSION 111 — entry point

See `00-START-NEXT-SESSION.md`. The major contract slices are
done; what's next depends on what the SPA actually needs first.

---

## AI notes

- Smallest slice in this Phase 2 run. Could have shipped in less
  than half the lines of SESSION 108 (avatar) or SESSION 109
  (video + Celery) — the contract pattern is now well-established
  and reuse of `voice_clone_client.clone_voice_from_audio` was
  obvious.
- Pyright noise has crossed the threshold from "annoying" to
  "actively misleading" — the unreachable-code warnings after
  `sys.exit(1)` are mathematically true but operationally pointless
  noise. `pyrightconfig.json` should land before SESSION 111
  ships anything substantial, or the next session will spend
  cognitive bandwidth deciding whether each new warning is real.
- The smoke test pattern is calcifying: in-line stub request, drive
  the viewset method directly, assert on the response + the
  persisted row, revert on exit. Worth canonicalising into a
  shared test helper if a fourth smoke command lands.
