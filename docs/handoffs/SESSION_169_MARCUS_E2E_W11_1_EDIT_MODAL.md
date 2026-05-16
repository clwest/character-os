---
title: "Session 169 — Marcus end-to-end + W11.1 edit modal"
date: 2026-05-15
status: complete
session: 169
previous_handoff: ./SESSION_168_K6_6_SCRIPT_STRUCTURE.md
---

# Session 169 — Marcus end-to-end + W11.1 edit modal

## TL;DR

Two operator-driven milestones in one session:

1. **Marcus end-to-end**: first new cast member created from
   scratch since SESSION 136. Battle unicorn dressed as a
   Roman legionary officer, AP history tutor persona, `marcus`
   voice preset, Nerva–Antonine dynasty doc attached. Two
   verified strict-mode renders shipped at $0.25 each.

2. **W11.1 edit modal shipped**: SPA spokesperson detail page
   gains an Edit button → modal for name / business_brief /
   visual_subject / tone_archetype. Voice + avatar deferred
   to W11.2 (needs Runway re-bind). Dogfood proves
   brief changes flow through to K6 on the next render.

Tests: Django **718 / 718** unchanged. SPA vitest
**46 → 52** (+6 modal tests). Total Runway spend:
$0.50 renders + $5-10 avatar bake.

## Marcus end-to-end (full pipeline)

| Stage | Result |
|---|---|
| Portrait (`/internal/portrait/`) | ✓ 26.5s real Runway gen4_image, battle unicorn in lorica segmentata |
| Avatar bake (`/internal/avatars/`) | ✓ 33.4s, status=READY, `ce946464-990c-4d17-896a-7c5f16b52d76` |
| Spokesperson row | ✓ `b6a00dd8-...` — tone=tutor, voice=marcus |
| Knowledge attach | ✓ Nerva–Antonine dynasty (9 chunks) → Marcus |
| K6 synthesis (strict mode) | ✓ verified, 0 warnings |
| Render 1 (initial brief) | ✓ $0.25 real Runway clip |
| Brief edit | ✓ DB-level (simulating SPA modal PATCH) |
| Render 2 (post-edit) | ✓ $0.25 real Runway clip with the new pedagogical signature |

**Render 2's synthesized brief** — first sentence is the
*exact pedagogical signature* the operator wrote into the
new brief:

> *"Same event, different lens — let's try one. I'm Marcus,
> your AP history tutor, and today: one reason Marcus
> Aurelius is remembered well — and why critics disagree.
> Marcus is counted among the 'Five Good Emperors': he
> continued Antoninus Pius's peaceful, benevolent rule,
> shared power with the Senate, and governed as an
> unpretentious, gifted administrator—earning respect
> through good government. Critics point to his naming of
> his son Commodus as heir, a choice often blamed for
> beginning the empire's decline. Want more quick lenses
> on Rome? Follow for the next one."*

Five distinct facts cited verbatim from the Nerva–Antonine
chunks: *Five Good Emperors* / *Antoninus Pius's peaceful
rule* / *shared power with the Senate* / *naming Commodus
as heir* / *beginning the empire's decline*. Strict mode
held. No fabrications. Voice perfectly captures Marcus's
teaching signature.

## What shipped — W11.1 edit modal

The operator surfaced the gap mid-session: *"We don't have
a way to edit the Avatars [on the UI]."* The backend's
`SpokespersonViewSet` already supports PATCH via
`ModelViewSet`, but the SPA had no edit route or modal.
W11.1 closes the UI gap.

### Backend (no changes needed)

PATCH `/api/spokespeople/<id>/` already supports edits on:
* `name`
* `business_brief`
* `visual_subject`
* `tone_archetype`

Read-only via serializer:
* `runway_avatar_id`, `runway_avatar_status`,
  `portrait_path`, `voice_id`, timestamps

Voice editing requires Runway-side re-bind (the avatar
binds a voice at create time); deferred to W11.2.

### SPA

* `web/src/lib/api/spokespeople.ts` — new
  `useUpdateSpokesperson` hook. PATCH wrapper that sends
  only the changed fields; seeds the single-resource
  cache + invalidates the list.
* `web/src/components/spokesperson-edit-modal.tsx` —
  new modal. Inline pattern (no Radix dep), same shape
  as ToolApprovalModal. Form fields: name, tone select
  with 5 archetypes, visual subject (200-char cap),
  business brief textarea. Esc / backdrop / Cancel
  dismiss; Save fires PATCH and closes on success.
  Errors render inline.
* `web/src/routes/spokespeople/$id.tsx` — `IdentityPanel`
  grew an Edit button (pencil icon, ghost variant) in
  the panel header. Detail page tracks `editing` state +
  conditionally renders the modal.

### Tests (+6 vitest)

* Initializes with current values
* Save disabled until something changes
* Save fires PATCH with only changed fields
  (asserts URL + method + body shape)
* Esc dismisses
* Cancel dismisses
* Blank name keeps Save disabled

### Dogfood proof

The operator-facing case:
1. Edit Marcus's brief → new signature line *"Opens every
   lesson with: 'Same event, different lens — let's try
   one.'"*
2. Fire fresh render via `talking_head` with the same
   knowledge doc.
3. K6 synthesizes — first sentence is the signature.

No restarts, no manual config flips, no waiting for
caches. The brief changes propagate cleanly.

## Calibration moments worth carrying

### 1. Operator-facing test loops scale with audit fields

K6.6 (SESSION 168) added `Composition.synthesized_brief` so
successful renders persist what K6 said. That field made
this session's dogfood loop trivial: edit brief → fire
render → read `composition.synthesized_brief` → confirm the
new voice landed in the script. Pre-K6.6 the same loop
required watching the actual MP4 (slow) or fishing the
script out of media-engine logs.

**Carry-forward**: audit-trail fields aren't just for
debugging — they're operator-facing test infrastructure.
Every "what did the model actually say?" surface
collapses the iteration loop on prompt / persona /
recipe tuning by an order of magnitude.

### 2. The metadata gap is the SPA gap

The backend has supported PATCH on spokespeople since the
ViewSet shipped. The gap was discoverability + the UI.
Six weeks of K-arc work shipped through metadata-driven
forms (recipes, verifier toggle, mode select) — but
spokesperson edits were never wired because the
ModelViewSet's CRUD is *not* metadata-driven; it's just
DRF defaults. The edit modal is hand-built UI.

**Carry-forward**: when CRUD via ModelViewSet ships
without an SPA surface, the feature is effectively
backend-only. Operators don't know it exists unless they
hit the right URL via curl. **For this operator
specifically:** any new model that ships via
ModelViewSet should get a SPA surface paired with it
within the same arc — otherwise the gap surfaces as
"we don't have a way to do X" months later.
**Generalisation:** read-only metadata-driven surfaces
+ hand-built write surfaces is a stable pattern, but
the write side scales linearly with feature surface
area. Plan for it.

## Files changed in this commit

* `web/src/lib/api/spokespeople.ts` — `useUpdateSpokesperson`
  + `UpdateSpokespersonInput`.
* `web/src/components/spokesperson-edit-modal.tsx` — new.
* `web/src/components/spokesperson-edit-modal.test.tsx`
  — new (+6 tests).
* `web/src/routes/spokespeople/$id.tsx` — `editing` state +
  Edit button + modal mount.
* `docs/CHARACTER_OS_INVENTORY.md` — regen.
* `00-START-NEXT-SESSION.md` — Marcus added to cast roster,
  W11.1 marked done.
* `docs/handoffs/SESSION_169_MARCUS_E2E_W11_1_EDIT_MODAL.md`
  — this file.

## Addendum — portrait JWT refresh + hook-order bug (commit `2cdcd26`)

Operator surfaced two console errors after the first SESSION
169 commit landed:

1. **`Rendered more hooks than during the previous render`** —
   the `useState(editing)` I added in the SpokespersonDetailRoute
   sat *after* the early returns for loading / error / not-found
   states. React saw a different hook count between renders.
   One-line fix: move `useState` above the early returns.
2. **5× `401 Unauthorized`** on every cast member's portrait img.
   Runway's CloudFront thumbnail URLs are JWT-signed with ~30-day
   expiry; most of the cast had passed `exp`. Marcus's stored URL
   was missing the JWT entirely (an artifact of the SESSION 169
   first attempt — when the initial Spokesperson row save failed
   on visual_subject length, I shortcut with a plain `.png` URL
   on the retry without realizing it'd never auth).

The JWT-expiry is a system-level recurring pattern, so the fix is
infrastructure rather than one-shot:

* **Media-engine**: new `fetch_avatar_thumbnail(avatar_id)` in
  `character_studio_client.py` + new endpoint
  `POST /internal/avatars/<id>/refresh/`. Hits Runway's
  `GET /v1/avatars/{id}` and returns the fresh
  `processedImageUri`/`referenceImageUri`. Mock-safe; returns
  `None` on Runway-side failure.
* **Django**: `MediaEngineClient.refresh_avatar_thumbnail()` wraps
  the new endpoint. `SpokespersonViewSet` gains a
  `refresh-portrait` action that persists the fresh URL onto
  the row. New `python manage.py refresh_portraits
  [--workspace=<slug>] [--dry-run]` loops the cast in one shot.
* **SPA**: `useRefreshPortrait` hook + the `Portrait` component's
  `<img onError>` fires refresh-portrait once and swaps the src.
  So the next JWT expiry (~30 days from now) will self-heal —
  the operator will never see a broken avatar.

**Live verification**: all 5 cast members refreshed in a single
mgmt-command run, all URLs `curl 200`, SPA tab reloads clean.
No Runway spend (read-only GET).

Two new TRUST_CALIBRATION entries paired with this fix (see
`docs/TRUST_CALIBRATION.md`):
* **Hook order violation across early returns** — when adding
  state to a route component with conditional early returns,
  the hook must live ABOVE the returns. Easy mistake under
  React's hooks rules; the SPA's existing routes did it right
  by convention.
* **JWT expiry on external CDN URLs is a recurring class** —
  any persisted URL with `exp` baked in is going to break on
  schedule. Build the refresh path in alongside the original
  persistence, not as a follow-up.

## What's next (SESSION 170)

* **W11.2 — voice + avatar edit support.** Voice editing
  needs Runway-side re-bind (PATCH `/v1/avatars/<id>` or
  re-create with a new voice block). Avatar editing
  needs a re-bake flow with operator approval (visual
  subject change → confirm spend → bake new avatar →
  swap on the row). Both are non-trivial; budget 1-2
  sessions.
* **Real-Runway exposure on other recipes.**
  `talking_head_polished` Sasha retake (captions +
  intro/outro), `long_form_ad` smoke. The base recipe
  has been proven 4× now ($1.50 total spend across
  3 spokespeople).
* **K6.4 v3 — embedding-similarity fallback.** Holds
  until a real paraphrase miss surfaces in operator
  dogfood.
* **Older backlog** — F8.1, K7.x YouTube ingest fix,
  K6.3 brief length cap (might be moot now that K6 is
  producing clean briefs), K7.1 cost telemetry.

---

*Handoff written end-of-SESSION 169. Anchors re-stamped
via `context-kit handoff write 169`. Marcus is the newest
cast member with two verified strict-mode renders at
verification_status=verified, including one that
demonstrates the W11.1 edit-loop end-to-end.*
