---
title: "Session 127 — Foundation fields: visual_subject + tone_archetype"
date: 2026-05-14
status: complete
session: 127
previous_handoff: ./SESSION_126_VOICE_TABS_SCAFFOLD.md
---

# Session 127 — Wizard slices 3.5 + 4 (foundation fields)

## TL;DR

- **What shipped:** Two new fields on the `Spokesperson` model
  (`visual_subject` + `tone_archetype`), the
  `suggest_tone_from_brief()` keyword-heuristic helper, full
  serializer + zod surfacing, and a quick UI surface in the
  detail-page MetadataGrid. Plus the doc-edits the operator
  queued previously: the inserted `W3.5` slice in `00-START-
  NEXT-SESSION.md` and the visual-archetype clarification in
  `CREATE_SPOKESPERSON_WIZARD.md`.
- **What's blocking next:** Nothing. SESSION 128 is open for
  wizard slice 5 (wizard scaffold), or any parallel-safe queued
  item.
- **What's in a weird state:** None. 12/12 Playwright specs still
  pass. 46/46 pytest cases (was 31 — slice added 15 tone tests).
  All smokes green.

---

## What changed (file-by-file)

### Backend (Django)

#### `shell/apps/spokespeople/models.py`

Two new fields + a `Tone` TextChoices nested class on `Spokesperson`.

1. **`visual_subject`** — `CharField(max_length=200, blank=True,
   default="")`. Free-text "what this spokesperson looks like." Empty
   means "use the visual template's built-in default subject" (e.g.
   `mascot` → "a friendly brand mascot"). Wizard Step 2 (W7) will
   thread this into `/internal/portrait/`'s `subject` parameter on
   the generate path.
2. **`tone_archetype`** — `CharField(max_length=20, choices=Tone.choices,
   default=Tone.EXPERT)`. Five options
   (`tutor / authority / friend / expert / performer`).
   Defaults to `expert` — the safest neutral for SMBs.

Help text on both fields documents the intended use + where they'll
be threaded into the rendering pipeline.

#### `shell/apps/spokespeople/migrations/0002_spokesperson_tone_archetype_and_more.py`

Auto-generated. Two `AddField` operations, both with safe defaults
(`""` / `expert`), so the migration is backwards-compatible against
existing rows.

#### `shell/apps/spokespeople/serializers.py`

`SpokespersonSerializer` now includes both new fields in `fields`.
Neither is in `read_only_fields` — both are writable on create + edit.
DRF's default handling treats `tone_archetype` as a choice field (only
the 5 archetype keys accept) and `visual_subject` as a free-text up
to 200 chars.

#### `shell/character_os/prompts/brand.py`

New helper + supporting data:

- **`TONE_ARCHETYPES`** — tuple constant listing the 5 archetype keys
  in canonical order. Mirrored on the SPA side.
- **`_BRIEF_TONE_HINTS`** — keyword hint table per archetype. Ordered
  so distinctive archetypes (`tutor`, `performer`) win when overlapping
  with generic ones (`expert`).
- **`suggest_tone_from_brief(brief: str) -> str`** — mirrors
  `suggest_palette_from_brief`. Pure keyword scan, falls back to
  `"expert"` when nothing matches. Returns a key always in
  `TONE_ARCHETYPES`.

#### `shell/character_os/prompts/__init__.py`

Re-exports `TONE_ARCHETYPES` + `suggest_tone_from_brief` so
`from character_os.prompts import suggest_tone_from_brief` works.

#### `shell/character_os/prompts/test_prompts.py`

15 new pytest cases under `TestSuggestTone`:

- 11 parametrized brief → tone mappings (2-3 per archetype + 2
  fallback cases including empty string).
- `test_returned_tone_is_always_in_archetypes` — guards against
  hint-table typos that'd return a non-canonical archetype.
- `test_distinctive_keyword_beats_generic` — locks the
  ordering contract: "expert teacher" → `tutor` (the more
  distinctive archetype), not `expert`.

### SPA

#### `web/src/lib/api/spokespeople.ts`

Three additions:

1. **`TONE_ARCHETYPES` const** — `as const`-typed tuple mirroring the
   Django side. `ToneArchetype` type derived from it.
2. **`spokespersonSchema`** — extended with `visual_subject: z.string()`
   + `tone_archetype: z.enum(TONE_ARCHETYPES)`.
3. **`CreateSpokespersonInput`** — both fields surfaced as optional
   inputs (`visual_subject?` + `tone_archetype?`), with JSDoc pointing
   at the wizard slice that'll wire the UI.

#### `web/src/routes/spokespeople/$id.tsx`

Two new rows in `MetadataGrid` (top of the grid, ahead of
`Avatar id` / `Voice id`):

- `Tone` — always shown (the field has a non-empty default).
- `Visual subject` — shown as `—` when empty, the subject text
  otherwise.

This makes the new fields immediately visible on the detail page even
though no creation UI surfaces them yet (W6 + W7 do the wizard UI work).

### Docs

#### `00-START-NEXT-SESSION.md`

- Inserted `W3.5` row in the slice table (now DONE).
- Rewrote the SESSION 128 entry-point block: scaffold (slice 5) is
  now the next priority; foundation fields are off the list.
- Renumbered the queued-investigations list.
- Updated "What's working end-to-end" to mention the new fields.

#### `docs/design/CREATE_SPOKESPERSON_WIZARD.md`

- Flipped the "Decision deferred" note in §"Visual archetypes" to
  confirm `visual_subject` lands as slice 3.5.
- Updated Step 2 Generate path description to mention
  `Spokesperson.visual_subject` as the persistence target.

(These doc edits were drafted at the end of SESSION 126 and held per
operator instruction; they ship in this commit alongside the field
landing.)

#### `docs/CHARACTER_OS_INVENTORY.md`

Regenerated. Model count drift expected: `Spokesperson` field count
shifts as the schema grows.

---

## Verification gates

- `python manage.py check` — clean (deprecation warnings unchanged).
- `python manage.py migrate --check` — clean (0002 already applied).
- `python manage.py smoke_headless_auth` — PASSED.
- `python manage.py smoke_avatar` — PASSED (Spokesperson default
  values handle gracefully).
- `python manage.py smoke_voice` — PASSED.
- `python manage.py smoke_video` — PASSED.
- `python manage.py smoke_portrait` — PASSED for all 4 templates.
- `python -m pytest character_os/prompts/` — **46 passed** (was 31).
- `python manage.py inventory` — clean regen.
- `pnpm tsc --noEmit` — clean.
- `pnpm build` — clean (bundle 471.47 kB).
- `pnpm e2e` — **12 of 12 pass** (unchanged from SESSION 126).
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### Two foundation slices, one session

The slice plan in SESSION 126 had W3.5 + W4 as separately-numbered
half-sessions. They landed together because the shapes are nearly
identical: each adds a field, a migration, serializer + zod surface,
and one helper (or no helper). Lumping was reasonable here:

- Both fields are foundation-only (no UI flow depends on them yet).
- Both have safe defaults — the migration applies cleanly to
  existing rows without backfill code.
- The `TestSuggestTone` test class mirrors `TestSuggestPalette`,
  so the same pytest patterns extend without thought.

When two slices share file boundaries this tightly, bundling them
keeps the commit narrative cleaner ("foundation fields") than two
mechanical "add a field" commits.

### Tone-hint ordering is load-bearing

The hint table is ordered tutor → performer → friend → authority →
expert. The `test_distinctive_keyword_beats_generic` test pins this:
"expert teacher with credentials" → `tutor`, because tutor's hint
list contains `"teach"` and is tested first. If the order ever
shifts, the test fails loudly — exactly the kind of contract guard
that prevents silent UX drift.

Reasoning for the ordering: `expert` is the fallback default. If a
brief mentions BOTH tutor and expert signals, the operator's intent
is almost certainly the educator path (specific use case) rather
than the generic-credentialed path (default). Same logic for
performer vs expert ("PhD comedian" → performer wins).

### The metadata grid landed UI ahead of the wizard

I surfaced `Tone` + `Visual subject` in the detail-page MetadataGrid
even though no creation flow writes them yet. Reasoning:

- The values exist on every row (defaults), so showing them isn't
  hypothetical.
- It validates the zod surface end-to-end — if the API or schema
  drifts, the detail page breaks visibly.
- W6 (Wizard Step 1) gets a stable visual target: "these rows
  already exist on the detail page; the wizard just needs to write
  them."

A cleaner-purist would have left UI for W6. I prefer the small
validation surface today.

### `visual_subject` doesn't auto-generate yet

The most-asked-about question post-SESSION 126 was "where do I say
my spokesperson is a raccoon?" Today the answer is "the field
exists; the UI surfaces it on the detail page; W7 wires creation."

The two-step orchestration (subject → `/internal/portrait/` →
data URI → `/internal/avatars/` → avatar id) is a meaningful slice
on its own. Wedging it into SESSION 127 would have grown the slice
unboundedly. The W7 scope already covers it — the only delta is
that `visual_subject` is now a real field rather than a wizard-only
client-state value, which is the right shape for a regenerate-
portrait affordance that lives outside the wizard.

---

## SESSION 128 — entry point

`00-START-NEXT-SESSION.md`. The recommended next slice:

- **Wizard slice 5 — Wizard scaffold** (session-sized). Build the
  4-step wizard shell (Identity / Portrait / Voice / Confirm),
  empty bodies, full navigation. Replaces the current single-form
  on `/spokespeople/new` (gated behind a feature flag or query
  param if needed to keep the existing e2e suite green during the
  transition).

Slices 6-9 then fill in each step, in order. Slice 10 (template
content) becomes operator-collaborative as it's content work.
Slice 11 (hide-on-completion full rework) builds on what shipped
in SESSION 126.

---

## AI notes

- The slice landed in ~25 minutes start-to-gates-pass. Both halves
  are similar shape (field + migration + serializer + zod). The
  pytest scaffolding (parametrize + guard tests) doubled the test
  count without much marginal effort — well-shaped pattern from
  SESSION 122.
- The tone-hint ordering took two iterations to get right. First
  pass had `expert` second, which made "PhD tutor" → expert
  instead of tutor. The `test_distinctive_keyword_beats_generic`
  test caught it on the first pytest run.
- The metadata-grid surface was a judgement call (cleaner-purist
  would defer to W6). I prefer the small validation surface today
  — the wizard scope is fixed enough that adding `Tone` and
  `Visual subject` rows now doesn't preempt any future decision.
- The smoke_avatar / smoke_voice transaction discipline issue
  (queued #14) didn't bite this session. Conditions for it to
  recur are still present.
- One thing not done that the START doc mentioned: a
  `regenerate-portrait` endpoint. Decided against — it's a
  meaningful slice on its own and W7 will need it anyway.
  Worth flagging in the SESSION 128 → W7 path that the regen
  endpoint is now firmly in W7's scope.
