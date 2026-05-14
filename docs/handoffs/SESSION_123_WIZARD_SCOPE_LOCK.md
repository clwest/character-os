---
title: "Session 123 — Create-Spokesperson Wizard scope-lock"
date: 2026-05-13
status: complete
session: 123
previous_handoff: ./SESSION_122_PROMPT_HELPERS_TIER_1.md
---

# Session 123 — Wizard scope locked, no code yet

## TL;DR

- **What shipped:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`
  (~750 lines). Locks the 4-step create-spokesperson wizard
  scope: step inventory, two-axis archetype model (visual + tone),
  3-mode voice input (preset/upload/record), template-pick-or-fresh
  entry point, hide-on-completion pattern, backend additions
  needed, prompt-helper wiring points, camera/audio capture
  browser-API contract, out-of-scope list, recommended
  implementation slice order. Same role for the wizard that
  `SPA_ARCHITECTURE.md` plays for the SPA as a whole.
- **What's blocking next:** Nothing. SESSION 124 starts the
  implementation. The recommended first slice is **camera capture
  for the existing `<PortraitUpload>`** — half-session, pure SPA,
  doesn't depend on the wizard scaffold and immediately improves
  the SESSION 120 create flow.
- **What's in a weird state:** None. SESSION 123 is doc-only;
  all 8 Playwright specs + 3 vitest + 4 backend smokes + 31
  prompts tests still pass unchanged.

---

## What changed (file-by-file)

### `docs/design/CREATE_SPOKESPERSON_WIZARD.md` (new — ~750 lines)

The scope-lock doc. Six load-bearing contract rules at the top
(wizard is for new spokespeople only; v1 floor is name + brief +
portrait; pure JSON in/out; no conversational chat; templates
pre-fill, archetypes default; no silent failure). Step-by-step
inventory follows.

**The four steps:**

1. **Identity** — entry point branches: template pick (Riggs /
   Sasha / Donny / possibly Maya) → all fields pre-filled, OR
   "Start from scratch" → name + brief + optional tone archetype.
2. **Portrait** — three tabbed input modes: upload, camera
   capture (`getUserMedia` → `<canvas>.toDataURL`), or generate
   via Runway gen4_image (fresh-path only; requires new
   `/internal/portrait/` endpoint).
3. **Voice** — three tabbed input modes: Runway preset dropdown,
   audio file upload, or in-browser recording via `MediaRecorder`.
   Safari/iOS fallback hides Record tab when `MediaRecorder` is
   unavailable.
4. **Confirm** — review + orchestrate creation. POSTs
   `/api/spokespeople/` first (creates row + binds avatar via
   existing SESSION 116 backend); if Upload or Record voice
   chosen, also POSTs `/api/spokespeople/{id}/clone-voice/`.
   Navigates to `/spokespeople/{id}` on success.

### Two-axis archetype model (locked)

Out of the SESSION 122 discussion: visual and tone are
**orthogonal** axes, motivated by the operator's friend James (HS
history teacher, wants a battle unicorn that's mascot-visual +
tutor-tone).

- **Visual archetype (4):** `mascot / founder / coach /
  local_guide`. Already exists in inherited
  `media-engine/.../character_studio_client.py::PORTRAIT_TEMPLATES`.
  Drives `gen4_image` portrait generation. No DB field yet —
  stored implicitly via the resulting portrait. Adding the field
  deferred until a future regenerate-portrait slice needs it.
- **Tone archetype (5):** `tutor / authority / friend / expert /
  performer`. **NEW field** `Spokesperson.tone_archetype` (one
  migration, ~10 lines). Drives voice selection + future render-
  flow prompt augmentation. Defaults to `expert` when not picked.

James's battle unicorn = visual `mascot` + tone `tutor`. Per-
lesson costumes (Caesar's Roman armor, etc.) live in the
**per-video brief**, not on the Spokesperson — the existing
data model already supports this.

### Templates (3–4 named spokespeople)

Provisional slate documented:

| Template | Visual | Tone | Audience |
|---|---|---|---|
| Riggs | `founder` | `authority` | SMB owners |
| Sasha | `coach` | `friend` | Creators |
| Donny | `local_guide` | `expert` | Local businesses |
| Maya? | `mascot` | `tutor` | Educators (James-shaped) |

Templates are **collaborative content work** — the operator
helps design the actual portraits + voices + briefs. The
wizard's job is to lock the data shape; the identities are
content.

### Backend additions documented

Two new endpoints required for the wizard:

- **`POST /internal/portrait/`** — wraps the inherited
  `character_studio_client.generate_portrait()` with the
  `/internal/*` JSON contract. Synchronous, returns the
  generated portrait as a data URI. Mock-mode safe.
- **`POST /api/spokespeople/{id}/regenerate-portrait/`** —
  detail-page action for re-rolling the portrait without
  recreating the spokesperson. Deferred to a post-wizard
  slice.

### Prompt-helper wiring (SESSION 122 → wizard)

Four wiring points documented:

1. Step 1 brief save → `clean_business_brief()` strips fillers
2. Step 1 palette suggestion → `suggest_palette_from_brief()`
3. Step 1 tone suggestion → **NEW helper needed**
   (`suggest_tone_from_brief`, mirrors palette shape)
4. Step 4 confirm summary → `principles_for_kind('spokesperson_ad')`
   surfaces the top key_principle in editorial copy

### Implementation order (recommended)

11 slices, parallel-safe in places. First 4 are foundational
(camera capture, `/internal/portrait/` backend, voice tabs
scaffold, tone archetype field + helper). Slices 5-9 build the
wizard. Slice 10 is operator-led template content. Slice 11
reworks the detail page for hide-on-completion. Estimated 6-8
sessions total.

### `docs/CHARACTER_OS_WHAT_IT_IS.md`

Updated navigation table to cite `BRAND_IDENTITY_V1.md`,
`PROMPT_HELPERS.md`, and the new `CREATE_SPOKESPERSON_WIZARD.md`
explicitly. Frontmatter bumped: `last_revised: 2026-05-13
(SESSION 123)`, `covers_sessions: "106-123"`.

---

## Verification gates

Doc-only slice; runtime gates unchanged. What was checked:

- `docs/design/CREATE_SPOKESPERSON_WIZARD.md` exists at the
  documented path.
- Cross-references resolve (every linked design doc exists).
- No code changes; runtime gates not applicable.
- `git status` reflects only the expected additions.

---

## Architectural notes worth remembering

### The wizard isn't a single slice — it's a series

Six-to-eight sessions of work from "scaffold" to "fully shipped."
The doc breaks it into 11 ordered slices, mostly half-session to
session-sized each. Slices 1-4 are foundational and parallel-safe;
they can land in any order before the wizard scaffold lands in
slice 5. This is the right shape for a feature this big — avoid
trying to land the full wizard in one heroic slice.

### The two-axis archetype model came from a real customer

James-the-history-teacher's battle unicorn use case forced the
visual + tone separation. Before that conversation, "Tutor" was
in `PORTRAIT_TEMPLATES` — a visual archetype. But James's tutor
is shaped like a mascot, not a sweater-vest human. The fix:
treat visual and tone as orthogonal.

This is the second time real-customer signal (James wants a
tutor; James wants a unicorn) shaped the product more than the
abstract design doc did. Worth keeping in mind: **the operator's
calibration profile prioritises right-shaping foundations, and
the foundation conversations get sharper when there's a real
customer use case to anchor against.** The unicorn anecdote
shifted the data model decisively.

### Hide-on-completion = SESSION 118's setup-checklist extended

The SESSION 118 spokesperson-detail-page setup-checklist
pattern already does most of what hide-on-completion needs.
Fully configured spokespeople just don't render the checklist.
Partially configured ones render only the skipped/optional items.
The wizard extends the existing item-builder rather than
inventing new UI. **Pattern compounding** — SESSION 118's slice
made SESSION 123's slice cheaper.

### Templates are content, not code

The 3-4 named templates (Riggs / Sasha / Donny / Maya) need real
work: portrait design + voice clone + business brief writing.
That work doesn't belong in a development session — it's
collaborative product/content work between operator and AI.
Surface it as a queued item; the wizard data model handles any
identities the operator ships.

### Q-wiz open questions

Four smaller decisions deferred:

- **Template portrait storage.** Pre-render + commit to
  `web/public/templates/` recommended.
- **Tone archetype labels.** Placeholder copy; content pass
  before ship.
- **Wizard step persistence.** Start over on refresh for v1;
  sessionStorage adds complexity for an unusual case.
- **`regenerate-portrait` placement.** Detail page identity
  panel as inline edit affordance.

None block implementation. Resolve as the implementation slices
land.

---

## SESSION 124 — entry point

`00-START-NEXT-SESSION.md` recommends **camera capture for the
existing `<PortraitUpload>`** as the smallest natural starting
slice. It's:

- Pure SPA work — no backend changes
- Reusable — the existing SESSION 120 create-spokesperson flow
  gets camera capture for free, before the wizard ships
- The Browser API foundation for both wizard Step 2 + the
  future audio recording in Step 3 (same permission flow, same
  cleanup pattern, same fallback shape)

Half a session of work.

Alternative slices documented in the start-here.

---

## AI notes

- This was the third "scope-lock first, code later" doc in the
  project (after `SPA_ARCHITECTURE.md` and `PROMPT_HELPERS.md`).
  The pattern is settling: when a feature touches >1 service or
  >1 existing slice, lock the shape in a doc before writing
  code. This doc took ~25 minutes; the implementation it gates
  is 6-8 sessions. That ratio is the right one.
- The discussion that produced this doc was the most
  consequential conversation of the project so far. Q2 alone
  pivoted on the unicorn anecdote; without that real-customer
  signal, I would have shipped a single-axis archetype model
  and never noticed the gap until James actually used it.
- The 11-slice implementation order isn't load-bearing; it's a
  suggestion. The operator can reshuffle based on what feels
  most useful to demo or what unblocks the most. Slice 1 (camera
  capture) is genuinely the smallest natural starting point.
- Tutor as a tone archetype + Maya as a possible 4th template
  came from the same conversation. Worth flagging: the
  operator's friend network IS a research signal. James's
  feedback shaped scope; whoever's next will too.
- The "Q-wiz" prefix on open questions is intentional — it
  distinguishes them from the SPA_ARCHITECTURE.md's "Q" prefix
  for global scope questions. Each scope-lock doc gets its own
  prefix so future sessions can grep without ambiguity.
