---
title: "Session 125 — Wizard slice 2: POST /internal/portrait/"
date: 2026-05-13
status: complete
session: 125
previous_handoff: ./SESSION_124_PORTRAIT_CAMERA_CAPTURE.md
---

# Session 125 — `/internal/portrait/` backend endpoint (wizard slice 2 / 11)

## TL;DR

- **What shipped:** `POST /internal/portrait/` on the media-engine
  + `MediaEngineClient.create_portrait()` wrapper on the Django
  shell + `python manage.py smoke_portrait` covering all four
  inherited `PORTRAIT_TEMPLATES` (mascot / founder / coach /
  local_guide). Wraps the legacy
  `character_studio_client.generate_portrait()` so prompt
  composition + Runway gen4_image model + deterministic mock
  placeholder all match the legacy `/api/characters/{id}/generate-
  portrait` route. Stateless on the media-engine — no
  CharacterStore touch.
- **What's blocking next:** Nothing. SESSION 126 picks up either
  wizard slice 3 (voice tabs scaffold) or slice 4 (tone archetype
  field). Both parallel-safe; pick by preference.
- **What's in a weird state:** None. Half-session of backend-only
  work. The 10 Playwright specs are unaffected (this slice
  doesn't touch the SPA yet — SPA wiring lands in slice 7 when
  the wizard's Portrait step gets built).

---

## What changed (file-by-file)

### `media-engine/app/routers/internal.py`

Two changes:

1. **Imports** — added `PORTRAIT_TEMPLATES`,
   `_atomic_write_bytes`, `_generate_portrait_real`,
   `_mock_color_for`, `_solid_png`, `build_prompt` from
   `character_studio_client`. All public-by-convention helpers
   (`_`-prefixed but tested + stable in the inherited codebase).
2. **`POST /internal/portrait/`** — new endpoint, ~95 LOC. Same
   shape as the other `/internal/*` verbs:
   - `InternalPortraitCreate` Pydantic body model
     (`template`, optional `subject`, optional `style`).
   - `InternalPortraitResponse` (`portrait_data_uri`, `template`,
     `prompt`, `mock_mode`).
   - Validates `template ∈ PORTRAIT_TEMPLATES`.
   - Calls `build_prompt(template, subject, style)` — the same
     prompt composer the legacy character_studio_client uses.
   - Caches the result at
     `data/_internal/portraits/<sha256(prompt)>.png`
     (content-addressed; same inputs reuse the file).
   - Mock mode: `_solid_png(512, 512, _mock_color_for(prompt))` —
     deterministic placeholder coloured by prompt hash.
   - Real mode: `_generate_portrait_real(prompt, target, settings)`
     — same Runway gen4_image call the legacy route makes.
   - Read-back as `data:image/png;base64,...`.

Error codes follow the contract: 400 `unsupported_template`, 502
`upstream_runway_error`, 500 `internal_error`. Same normalisation
pattern as the avatar / voice / video endpoints.

### `shell/character_os/clients/media_engine.py`

Two additions:

1. **`PortraitCreateResult` dataclass** — `portrait_data_uri`,
   `template`, `prompt`, `mock_mode`.
2. **`MediaEngineClient.create_portrait()` method** — accepts
   `template`, optional `subject` + `style`. zod-equivalent
   strict shape parsing on the response (KeyError / TypeError /
   ValueError all collapse to `MediaEngineError`).

### `shell/apps/spokespeople/management/commands/smoke_portrait.py` (new)

`python manage.py smoke_portrait`. Probes the media-engine,
exercises every template (or just one via `--template`), asserts
each response has the expected MIME prefix + a non-trivial
payload (≥ 32 chars of base64). `--subject` + `--style` flags
support tailored exercises (e.g.
`--subject "armored battle unicorn warrior"`).

Run output:

```
  ✓ media engine reachable (runway_mock=True)
  ✓ mascot: data_uri=1,996 chars · prompt_len=277 · mock=True
  ✓ founder: data_uri=1,996 chars · prompt_len=318 · mock=True
  ✓ coach: data_uri=1,996 chars · prompt_len=296 · mock=True
  ✓ local_guide: data_uri=1,996 chars · prompt_len=297 · mock=True
✓ smoke test PASSED
```

Same payload size across templates is the deterministic mock
placeholder (`_solid_png` produces a fixed-size PNG); different
`prompt_len` confirms the composer is producing template-specific
prompts.

### `docs/design/MEDIA_ENGINE_INTERNAL_API.md`

Three additions:

1. **URL surface table** — added the new row:
   ```
   | POST | /internal/portrait/ | Generate a portrait via Runway gen4_image | SESSION 125 |
   ```
2. **New section** between voice and "Relationship to the legacy
   `/api/*` surface": full `POST /internal/portrait/` spec —
   request/response shapes, error codes, stateless contract
   description, mock-mode behaviour, smoke-test reference.
3. **Change log** — entry for SESSION 125.

---

## Verification gates

- `python manage.py check` — clean (allauth deprecation warnings
  unchanged from SESSION 119).
- `python manage.py smoke_portrait` — PASSED for all 4 templates.
- `python manage.py smoke_avatar` — PASSED (after clearing a
  stale `Smoke Test Spokesperson` row from earlier this session
  — the SESSION 119-noted smoke-test transaction discipline
  issue).
- `python manage.py smoke_voice` — PASSED.
- `python manage.py smoke_headless_auth` — PASSED.
- `python -m pytest character_os/prompts/` — 31 passed.
- `python manage.py inventory` — clean regen (FastAPI routes
  93 → 94).
- `pnpm e2e` — **10 of 10 still pass.** No SPA changes this
  slice.
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### The "extract from a real-mode-tested service" pattern compounds

Wizard slice 2 follows the same recipe as SESSIONS 108/109/110:
take a real public-entry function in the inherited media-engine
(`character_studio_client.generate_portrait`), identify the
load-bearing internal helpers (`build_prompt`,
`_generate_portrait_real`, `_solid_png`, `_mock_color_for`,
`_atomic_write_bytes`), and assemble them under the
`/internal/*` JSON contract. The legacy route stays untouched;
the new route uses the same prompt composer + same Runway model
+ same mock placeholder. **Behaviour parity is automatic** —
no duplication of Runway-side logic.

This is the third time the pattern's worked cleanly (avatar,
voice, portrait). When wizard slice 3 lands the voice tabs UI,
the underlying `/internal/voices/` it calls is the same
backend SESSION 110 shipped. Pattern reuse the whole way down.

### Content-addressed filename = idempotent without explicit cache

Caching the portrait at
`data/_internal/portraits/<sha256(prompt)>.png` means two
identical posts hit the same file. No explicit cache layer; the
filesystem IS the cache. The smoke test exercises this — re-
running the command writes nothing new on subsequent runs.

Useful for the wizard's UX: an operator who types a subject,
sees the result, doesn't like it, edits the subject, re-fires —
the second post is fresh because the prompt changed. An operator
who fires the same post twice (e.g. browser retry) gets the
same image without burning a second Runway credit.

### The 4-template smoke is a real contract guard

Every template hits the same code path (build_prompt → write →
read-back → return data URI). But each template carries
different `TEMPLATE_DEFAULTS` (subject) + `PORTRAIT_TEMPLATES`
(expression cue), so the composed prompt differs per template.
Running the smoke against all four catches drift: if someone
adds a new template to `PORTRAIT_TEMPLATES` but forgets a
`TEMPLATE_DEFAULTS` entry, the smoke fails on that template.

### Half-session shape worth keeping

This slice was deliberately small: one endpoint, one wrapper,
one smoke. ~200 LOC across all files. Half a session of work.
The wizard's 11-slice plan has more like this coming (slice 4
— tone archetype field is similarly bounded). Resist the
temptation to combine half-slices into "while we're here, let's
also..." — keep them atomic, commit them separately, let each
one stand on its own gate run.

---

## SESSION 126 — entry point

`00-START-NEXT-SESSION.md`. Two parallel-safe options:

- **Wizard slice 3 — Voice tabs scaffold** (session). Build
  `<VoiceCapture>` component with three tabbed input modes:
  Preset (dropdown), Upload (file), Record (MediaRecorder).
  Lands on the existing `/api/spokespeople/{id}/clone-voice/`
  action (SESSION 110 backend); operator gets voice clone UI
  on the detail page setup checklist BEFORE the wizard ships.
- **Wizard slice 4 — Tone archetype field** (half-session).
  Add `Spokesperson.tone_archetype` field + migration +
  `suggest_tone_from_brief` helper in `character_os/prompts/`.
  Pure backend.

Pick whichever feels right. Slice 3 unblocks a more visible
detail-page feature; slice 4 is foundation prep for the wizard's
Step 1.

---

## AI notes

- The slice landed in ~20 minutes start-to-smoke-pass. The
  `extract-from-legacy` pattern is now well-rehearsed; the only
  judgement calls were where to cache the file (content-
  addressed under `data/_internal/portraits/`) and what to
  include in the response (`prompt` for diagnostics + auditing).
- The 4-template smoke is a stronger contract guard than a
  single-template test would be. Worth following the same shape
  for any future endpoint that takes a categorical input.
- The smoke_avatar / smoke_voice transaction discipline issue
  (still queued, never fixed) bit again this session — stale
  rows in the test DB collide on the next run's auto-create.
  Worth doing the tiny fix soon; it's mostly a quality-of-life
  improvement but it'll save a couple minutes per multi-smoke
  session.
- Real-mode notes for future operators: the legacy
  `_generate_portrait_real` includes single-retry on transient
  Runway INTERNAL.* failures, downloads the result to disk,
  raises CharacterStudioError on real failure. All of that
  inherited behaviour ports through `/internal/portrait/`
  without changes. When Runway credits eventually land, this
  endpoint's real-mode path should work first-try.
