---
title: "Session 136 — Cast went live (real-mode Runway) + portrait_path bugfix"
date: 2026-05-14
status: complete
session: 136
previous_handoff: ./SESSION_135_TEMPLATE_CONTENT.md
---

# Session 136 — Cast went live

## TL;DR

- **What shipped:** Character OS's four cast members are now real
  Spokesperson rows in admin@mail.com's workspace with bound Runway
  avatars + correct voice presets — Riggs (donkey), Sasha
  (raccoon), Donny (sloth), Maya (panda). Two new management
  commands (`generate_cast`, `seed_cast`) provide CLI paths for
  cast generation + seeding. Three small bug fixes that surfaced
  during the cast-seeding work: MediaEngineClient default timeout
  bumped from 10s → 60s (real Runway gen4 takes 15-30s);
  `portrait_path` migrated to `TextField` + actually persisted from
  the avatar bind (was empty before, meaning the wizard ALSO
  silently lost portraits); `.gitignore` widened to `.env.*`.
- **What's blocking next:** Nothing. SESSION 137 is the **knowledge
  ingestion scope-lock** conversation — the cast can render videos
  now, but they have nothing to talk about. Big arc; needs design
  before any code.
- **What's in a weird state:** The e2e suite passes in mock mode
  (30/30) but breaks in real-mode (Runway latency >> spec
  timeouts). Workaround: `mv .env .env.real` before `pnpm e2e`,
  restore after. Queued as next-session prep — add a
  `RUNWAY_FORCE_MOCK=1` env override so tests can guarantee mock
  mode regardless of api_key presence.

---

## What changed (file-by-file)

### Backend

#### `shell/character_os/clients/media_engine.py`

Default timeout bumped from 10.0s → 60.0s. Affects every caller
(smokes, wizard's submit, the new cast commands). Surfaced when
`seed_cast --key maya` hit real Runway and timed out at 10s on
the portrait gen step. 60s is a safe ceiling for synchronous
Runway calls (avatar / voice / portrait are all 10-30s real);
video calls are fire-then-poll so the POST itself returns fast.

#### `shell/apps/spokespeople/models.py`

`Spokesperson.portrait_path` changed from
`CharField(max_length=512)` to `TextField`. Mock-mode data URIs
(~2KB) exceed 512 chars; real-mode Runway CDN URLs fit fine but
TextField removes the constraint without cost. Migration
0003_alter_spokesperson_portrait_path landed.

#### `shell/apps/spokespeople/views.py`

`SpokespersonViewSet.perform_create` now persists
`result.thumbnail_url` to `instance.portrait_path` after a
successful avatar bind. This was a **silent wizard bug** — every
wizard-submitted spokesperson got a bound Runway avatar but a
blank `portrait_path`, so the detail page rendered the initials
fallback instead of the actual portrait. Surfaced via the cast-
seeding work (same code path); fix lands for both flows.

#### `shell/apps/spokespeople/management/commands/generate_cast.py` (new)

Bulk portrait generation CLI. Loops `TEMPLATES`, calls
`MediaEngineClient.create_portrait()` per character, saves each
PNG to `<shell>/data/cast/<key>.png` for operator preview. Flags:
`--key <slug>` for one character; `--output-dir PATH` to
override. Loud warning when mock-mode is on (placeholder PNGs)
vs. live (real gen4_image output). Used for "see what the
portraits will look like" without committing to seeding rows.

#### `shell/apps/spokespeople/management/commands/seed_cast.py` (new)

Full seeding pipeline CLI — the companion to `generate_cast`.
For each cast member: generates portrait → creates Spokesperson
row → binds Runway avatar → persists `voice_id` from
`voice_preset` + (post-fix) `portrait_path` from
`thumbnail_url`. Mirrors `SpokespersonViewSet.perform_create`
exactly. Flags: `--workspace-slug` (defaults to first by
created_at), `--key` for single member, `--force` to recreate.
Idempotent: re-runs without `--force` skip existing rows by
`(workspace, name)` match.

### Config / repo

#### `.env` (repo root, gitignored)

Copied from `runway-hackathon/.env` to get `RUNWAY_API_KEY`
live. The media-engine reads `<repo-root>/.env` via
`pydantic-settings` (per `media-engine/app/config.py`).

#### `.gitignore`

Widened the env pattern from `.env` + `.env.local` +
`.env.*.local` to `.env` + `.env.*`. Catches `.env.real`,
`.env.dev`, `.env.staging`, etc. — anything env-shaped is
now uncommittable without explicit force.

### Tests

No new specs this session; existing 30 still pass in mock mode.

### Docs / inventory

- `docs/CHARACTER_OS_INVENTORY.md` regenerated multiple times
  (migration + seed_cast additions).

---

## Verification gates

Run in mock mode (real-mode breaks the suite due to Runway
latency — see "What's in a weird state" above):

- `python manage.py check` — clean.
- `python manage.py migrate --check` — clean (0003 applied).
- `python -m pytest character_os/prompts/` — 46 passed.
- `python manage.py inventory` — clean regen.
- `pnpm tsc --noEmit` — clean.
- `pnpm build` — clean.
- `pnpm e2e` — **30 of 30 pass in one shot** (mock mode only).
- Hygiene scan — clean.

Real-mode validation: `seed_cast --workspace-slug
admins-workspace` ran cleanly end-to-end, four cast rows landed
with real Runway avatar UUIDs + populated `portrait_path` (CDN
URLs).

---

## Architectural notes worth remembering

### The wizard had a silent portrait_path bug for *every* prior session

`SpokespersonViewSet.perform_create` (landed SESSION 116) bound
Runway avatars correctly but never persisted the resulting
thumbnail URL to `portrait_path`. The detail page reads
`portrait_path` directly into `<img src>`. **Every spokesperson
created via the wizard since SESSION 121 had a blank
portrait_path** and rendered the initials fallback instead of
the actual avatar image.

Nobody noticed because:
- Mock mode worked the same way (initials fallback either way —
  no visible difference)
- Real mode wasn't being exercised until this session
- The Playwright specs assert on the avatar pill (`/mock|ready/i`)
  + the metadata grid, NOT on the rendered image

This is calibration-worthy: **specs that check derived metadata
without checking the rendered output let visual bugs ship
silently.** Worth adding an e2e check on `<img src=...>` being
non-empty + URL-shaped for any avatar-bound spokesperson.

### Real-mode latency breaks the test suite

Once `RUNWAY_API_KEY` is set, the media-engine hits real Runway
for every call. Portrait gen + avatar bind = 30-60s combined.
The Playwright specs assume sub-second responses (mock mode).
Result: 7 specs failed when run against real Runway, all due
to timeouts.

Two paths forward for SESSION 137 (queue, not blocker):

1. **`RUNWAY_FORCE_MOCK=1` env override** — small change to
   `media-engine/app/config.py`'s `runway_mock` property: check
   the override first, fall through to the api_key check
   otherwise. Tests set it; CLI runs don't. Cleanest.
2. **Per-test mock mocking** via Playwright route interception.
   More work; doesn't help the smoke commands. Skip.

Current workaround: `mv .env .env.real` before `pnpm e2e`. Worth
fixing properly before the next big arc lands its specs.

### `seed_cast` mirrors the wizard's submit semantics

By design. Same:
- Field population order (portrait → row → avatar bind → persist)
- Partial-failure handling (row creates even if avatar bind fails;
  detail page's setup checklist catches the missing piece)
- voice_preset → voice_id (preset mode; no clone-voice fired
  because the cast all use presets, not uploaded clips)

The CLI path skips the SPA but runs the same backend code shape.
Useful both as a seeding utility AND as a verification probe
for the wizard's flow.

### The cast is now load-bearing operational data

Pre-SESSION 136, the cast was just template definitions in a
Python file — content, not data. Post-SESSION 136, the cast is
**four Spokesperson rows in admin@mail.com's workspace with
bound Runway avatars + CDN-hosted thumbnail URLs**. The template
file (`spokesperson_templates.py`) is still the source-of-truth
for the *definitions*; the rows are the *instances* generated
from those definitions.

If the operator wants to change a cast member's brief / tone /
visual subject / voice, the change has to flow through *both*
sides:
1. Edit `spokesperson_templates.py` (the definition)
2. Re-seed via `seed_cast --key <key> --force` (the instance)

Future workflow consideration: a "sync cast from templates"
command that updates existing rows in place where definitions
differ. Queued, not urgent.

---

## SESSION 137 — entry point

**The cast can render videos. They have nothing to talk about.**

`business_brief` (one paragraph per spokesperson) is a style
guide for HOW they sound, not WHAT they know. Without a
knowledge layer, every render is the LLM hallucinating
Character OS from scratch.

**Phase 1 scaffolded for this moment:**
- `apps/memory/` — empty app, name suggests per-character
  persistent memory
- `apps/embeddings/` — empty app, name suggests vector storage
- `apps/conversations/` — `ConversationThread` model exists, no
  UI yet

**Also worth knowing:** u-d-b (the project we've been porting
in tiers) had a real RAG / memory layer. Tier 2 helpers
(DynamicPromptBuilder) was queued in earlier sessions, and the
memory work is adjacent. Worth reading u-d-b's memory +
embeddings modules as prep before the scope-lock conversation.

**Five design axes to decide before any code lands:**

1. **What's the unit of knowledge?**
   - Document uploads (PDFs, markdown, transcripts)?
   - Structured facts (FAQ entries, feature lists)?
   - Conversational ingestion ("talk to your spokesperson to
     teach them")?
   - Pasted URLs that get crawled?
   - All / hybrid?
2. **Scope: per-spokesperson, per-workspace, or both?**
   - All cast members need to know Character OS exists
     (workspace level)
   - Each pulls different angles for their job
     (per-spokesperson framing on the same corpus)
3. **How does knowledge reach the render?**
   - RAG (vector search at render-time, inject top-k chunks)
   - LLM-summarize (compress corpus into a per-render brief at
     ingest time)
   - Operator-curated (operator picks which knowledge applies
     per video)
4. **How does the operator manage it?**
   - Dedicated knowledge tab on the spokesperson detail page?
   - Workspace-level "facts" surface?
   - Inline during render?
5. **Maya's tutor mode tie-in?**
   - Maya's brief mentions "answers the question when the
     student is stuck" — the `ConversationThread` surface that
     implies needs the SAME knowledge layer
   - Or different store?

**Recommendation for SESSION 137:**

1. **Read u-d-b's memory + embeddings modules first** (~30 min)
   — surface what's already designed.
2. **Scope-lock conversation** with operator on the 5 axes —
   converge on a shape.
3. **Write `docs/design/KNOWLEDGE_LAYER.md`** as the scope-lock
   doc (same pattern as `CREATE_SPOKESPERSON_WIZARD.md`).
4. **Break into slices** — knowledge arc is multi-session,
   probably 6-12 slices similar to the wizard arc.

Don't start coding until the scope-lock is signed off.

---

## Queued investigations (priority-ordered)

1. **Knowledge layer scope-lock** (SESSION 137; the framing arc).
2. **`RUNWAY_FORCE_MOCK=1` env override** — fix the e2e
   suite-breaks-in-real-mode issue. Tiny config change.
3. **Voice preset audit** — listen to vincent/clara/drew/victoria
   against the cast personalities once the operator hears them
   in real-mode renders.
4. **First marketing video** — naturally happens once the
   knowledge layer ships + the operator can give the cast
   something to talk about.
5. **W11.1 — Edit-spokesperson modal.**
6. **W12 — Legacy form retirement** (now ungated since real-
   mode validation happened).
7. **Cast sync command** — pull updates from
   `spokesperson_templates.py` into existing rows.
8. **Tier 2 prompt helpers** (`DynamicPromptBuilder` from u-d-b)
   — may be subsumed by the knowledge layer arc; revisit after
   scope-lock.
9. **Stuck-row janitor** — operational hardening.
10. **Additional video kinds** — cinematic / dialogue / long_ad.
11. **Act-Two performance capture.**
12. **`lesson` video kind** — pairs with conversational tutor.
13. **Real Google OAuth + dj-stripe.**
14. **Allauth legacy-settings cleanup.**
15. **smoke_voice / smoke_avatar transaction discipline.**
16. **Drift verifier** (`verify_doc_claims --only-drift`).
17. **Brand Identity v2 + dark mode.**

---

## AI notes

- Session arc was loose by design — the operator started with
  "create the crew" and we discovered three bugs in sequence
  (timeout / portrait_path / .env gitignore breadth) while the
  primary work happened. Worth noting as a pattern: **the first
  time real-mode is exercised against any new code path, expect
  bugs.** The mock mode's deterministic placeholders had been
  hiding silent failures since SESSION 116 (portrait_path).
- The portrait_path bug is the most-significant calibration
  event of this session. **A bug that's been silently shipping
  since SESSION 116 didn't surface until we hit real-mode in
  SESSION 136.** That's 11 sessions of mock-mode validation
  hiding a real-mode-only bug. Worth logging in TRUST_CALIBRATION:
  "mock-mode tests on visual surfaces hide rendering bugs.
  Add at least one e2e spec that asserts on rendered output
  (img src, audio src) when visual paths land."
- The cast-rows-are-instances-of-template-definitions split is
  going to bite again in the knowledge arc. When a spokesperson's
  knowledge corpus drifts from "what the template says they
  should know" (because the operator added a doc, edited a fact,
  whatever), how does that propagate? Worth flagging in the
  knowledge scope-lock.
- I spent more time than I should have on the .env.real ↔ .env
  swap dance. The proper fix (`RUNWAY_FORCE_MOCK=1`) is queued;
  next session should do it as a tiny standalone before tackling
  knowledge.
- Operator's instinct on "step back, what do they talk about" is
  the right framing call. Shipping a make-video flow with
  empty-brain spokespeople would have surfaced the gap publicly
  (every generated video sounding like generic AI puff). Better
  to design knowledge first, render videos second.
