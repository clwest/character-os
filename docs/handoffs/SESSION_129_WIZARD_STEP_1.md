---
title: "Session 129 — Wizard slice 6: Step 1 (Identity) body"
date: 2026-05-14
status: complete
session: 129
previous_handoff: ./SESSION_128_WIZARD_SCAFFOLD.md
---

# Session 129 — Wizard Step 1 (Identity) body (wizard slice 6 / 11)

## TL;DR

- **What shipped:** Wizard Step 1's real Identity form — name +
  business_brief + tone_archetype select — plus an inline tone
  suggestion powered by a new
  `GET /api/prompts/suggest-tone/?brief=...` endpoint. Tightened
  `canAdvance` to require name AND brief (≥ 8 chars) matching the
  legacy form's `createSchema`. Removed the SliceCallout/DebugState
  scaffolding from Step 1; kept them on Steps 2-4. Template-tile
  picker deferred to slice 10 (operator-collaborative content).
- **What's blocking next:** Nothing. SESSION 130 picks up wizard
  slice 7 (Step 2 — Portrait body, including the deferred
  `visual_subject` → `/internal/portrait/` → `/internal/avatars/`
  orchestration from SESSION 127).
- **What's in a weird state:** None. 17 of 17 Playwright specs
  pass (was 15 — slice added 2). 46/46 pytest prompt tests.

---

## What changed (file-by-file)

### Backend

#### `shell/character_os/api_prompts.py` (new)

Thin DRF wrapper around the pure
`character_os.prompts.suggest_tone_from_brief` helper. The
`character_os.prompts` package stays Django-free (per its
`__init__.py` docstring); this file is the Django-aware glue
layer.

Single endpoint:

- **`suggest_tone(request)`** — `@api_view(["GET"])`,
  `IsAuthenticated`. Reads `?brief=...`, returns
  `{tone: "<archetype>"}`. Caps inbound brief at 8 000 chars
  (the wizard caps at 4 000; this gives headroom for paste-bombs).
  Always returns 200 with one of the 5 archetypes, or 400
  `brief_too_long`.

#### `shell/character_os/urls.py`

Added one path:

```python
path("api/prompts/suggest-tone/", suggest_tone, name="suggest-tone"),
```

The view is a function-based DRF view rather than a viewset — this
is a single thin endpoint, not a resource. Doesn't justify a full
app.

### SPA

#### `web/src/lib/api/prompts.ts` (new)

Two surfaces:

1. **`suggestTone(brief)`** — bare async function. URL-encodes the
   brief, GETs the endpoint, zod-parses the response, returns the
   archetype string.
2. **`useSuggestTone(brief, {minChars=30})`** — reactive hook.
   Disabled until the trimmed brief crosses `minChars`; uses
   TanStack Query's `staleTime: 10min` so typing then deleting back
   to the same prefix doesn't re-fetch.

#### `web/src/components/spokesperson-wizard.tsx`

Three notable edits:

1. **`canAdvance` for Step 1** — now requires both name (≥ 1 char
   trimmed) AND business_brief (≥ 8 chars trimmed, matches the
   legacy `createSchema`). `MIN_BRIEF_CHARS` constant pulled to
   module scope so the e2e spec + the form + the gate all agree.
2. **`Step1Identity` body** — replaced the placeholder name input
   with the full form:
   - Name (`<Input>`, max 120, autocomplete off)
   - Business brief (`<textarea>`, max 4 000, 5 rows, full
     placeholder from the legacy form)
   - Inline `brief-too-short` error when the operator's typed
     something but it's < 8 chars
   - Tone select (`<select>` over `TONE_ARCHETYPES`)
3. **`<ToneSuggestion>`** — new inline component, renders the
   suggested-tone banner under the brief textarea. Sparkles icon
   from lucide-react. Auto-hides when the suggested tone matches
   the currently-selected tone (acceptance feedback).

Removed the SliceCallout from Step 1. Steps 2/3/4 keep theirs
(they're still placeholder bodies that slices 7-9 fill in).

### Tests

#### `web/e2e/wizard-step-1.spec.ts` (new)

Two specs:

1. **`brief triggers a tone suggestion → click → select flips`** —
   types a tutor-shaped brief ("High school history teacher
   building lesson plans for ninth-grade students learning about
   ancient Rome.") → asserts the banner appears with `tutor` →
   clicks accept → asserts the select flips to `tutor` →
   asserts the banner disappears (suggested tone now matches
   selected tone) → manually selecting `performer` still works.
2. **`brief too short surfaces an inline validation error`** —
   types "Hi" → asserts the inline error renders → fills past the
   floor → asserts the error clears.

#### `web/e2e/wizard-shell.spec.ts`

Updated the existing `4-step navigation + state preservation` spec
to also fill the brief (the gate now requires it). Tests that the
brief alone (just 5 chars in the test) keeps Next disabled, then
filling past 8 chars enables Next.

### Docs / inventory

- `docs/CHARACTER_OS_INVENTORY.md` regenerated. URL routes
  `/api/*` went from 37 to 38 (one new endpoint).

---

## Verification gates

- `python manage.py check` — clean.
- `python manage.py smoke_avatar` — PASSED.
- `python -m pytest character_os/prompts/` — 46 passed.
- `python manage.py inventory` — clean regen.
- `pnpm tsc --noEmit` — clean.
- `pnpm build` — clean (bundle 485.19 kB; +4 kB from SESSION 128).
- `pnpm e2e` — **17 of 17 pass** (was 15 — slice added 2).
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### The pure-prompts package stays pure

`character_os.prompts.__init__` docstring says:

> Stateless utility module. No Django models, no migrations, no
> API endpoints (yet).

When this slice needed HTTP access to `suggest_tone_from_brief`,
the obvious-but-wrong path was to drop a `views.py` inside the
prompts package. That would couple it to Django (DRF imports, etc.)
and break the "compose freely" promise the docstring makes.

The right path was `character_os/api_prompts.py` — a sibling file
that's Django-aware and imports the pure helpers. Same project,
distinct concerns. If the project grows to need more
prompt-helper-as-API endpoints, this file is the home; if we want
to add palette suggestion or sharpening helpers as endpoints
later, they land here next to `suggest_tone`.

### Tone suggestion uses query for free debouncing

The brief textarea fires `onChange` on every keystroke, so naïve
binding would hammer `/api/prompts/suggest-tone/` 60+ times per
brief. Two ways to handle:

A. Debounce with `setTimeout` in a useEffect.
B. Let TanStack Query's caching take care of it.

Picked B. The hook's `queryKey` includes the trimmed brief, so
identical briefs share a cached response. `staleTime: 10min` means
typos that get corrected don't trigger a refetch. The only
overhead is one query *function call* per keystroke (cache lookup),
which is essentially free.

Functional consequence: typing fast still fires multiple requests
(once for each distinct brief substring as the user types). With
the endpoint being a pure keyword scan it's well under a millisecond
server-side. If observability surfaces this as a problem, dropping
to A is a one-useEffect addition.

### Suggestion banner hides when accepted

The banner appears when `suggestion.data !== state.identity.tone_archetype`
— so the moment the operator clicks "Pick tutor →" and the select
flips, the banner disappears. This is intentional UX feedback
(acceptance is immediate; no toast or confirmation needed) AND a
clean technical guard (no infinite "still suggesting tutor" loop
when tutor is now selected).

### Why a function-based view, not a viewset

A list-only viewset would force a `/api/prompts/suggest-tones/`
collection shape, which doesn't match the operation (this is a
single-prompt query, not a list resource). Function-based DRF
views are the right shape when the endpoint isn't a resource.
First in the project — flag the pattern in `dev_notes` if it
catches on.

### Template tiles deferred to slice 10

The scope-lock and START doc both mentioned a "Start from template"
tile picker on Step 1 (Riggs / Sasha / Donny / Maya). Skipped:

- The mechanism (tile click → reducer dispatch with pre-filled
  identity) is trivial to add when slice 10's content lands.
- Without real template content, the tiles would render lorem-ipsum
  placeholders that feel worse than no tiles at all.
- Slice 10 is explicitly operator-collaborative; landing the
  mechanism today + the content later in two places (tiles render
  + tiles populate) splits responsibility cleanly.

### Removed scaffolding from Step 1, kept on others

The wizard now has uneven scaffolding visible — Step 1 is the
"real thing," Steps 2-4 still show ScaffoldBlock + SliceCallout +
DebugState placeholders. This is exactly how the wizard should
read while slices 7-9 land: clear progress signal ("Step 1 is
done") via the absence of placeholder copy.

Slice 9 ships the final DebugState removal across all 4 steps as
part of the "wizard is the default" flip.

---

## SESSION 130 — entry point

`00-START-NEXT-SESSION.md`. Slice 7 — Step 2 (Portrait) body:

1. **Three-mode input** — wire `<PortraitUpload>` (SESSION 124's
   Upload + Camera tabs) into Step 2 via `SET_PORTRAIT` dispatches.
2. **Generate tab** — third option alongside Upload + Camera. Inputs:
   visual template select (`mascot / founder / coach / local_guide`),
   `visual_subject` text input, optional `style` text. On submit,
   POSTs to a new `/api/spokespeople/generate-portrait/` endpoint
   that wraps `MediaEngineClient.create_portrait()` (the SESSION
   125 backend). Preview → "Use this portrait" commits as if
   uploaded.
3. **Persist `visual_subject`** — whichever path the operator
   takes (Upload / Camera / Generate), the typed `visual_subject`
   text from the Generate path persists on Step 4's submit. (Slice
   9 wires the submit; this slice just routes the field through
   the reducer.)
4. **Tighten `canAdvance` for Step 2** — require a portrait
   chosen (any of the 3 modes).
5. **Remove ScaffoldBlock + SliceCallout from Step 2** (keep on
   Steps 3 + 4).
6. **Playwright spec** — `wizard-step-2.spec.ts`. Upload path
   (simplest), Generate path (using the existing `smoke_portrait`
   pattern to exercise mock-mode generation).

This is the biggest remaining slice — the Generate orchestration
brings together SESSION 125's `/internal/portrait/` + SESSION 127's
`visual_subject` field. Session-sized, not half-session.

---

## AI notes

- Slice landed in ~30 minutes start-to-gates-pass. The endpoint +
  hook pattern was straightforward; the wizard form changes took
  most of the time (placeholder→real with the tone-suggestion
  banner overlay).
- One e2e flake bit: the existing `wizard-shell` spec used "Too
  short" (9 chars) as a brief that should fail the gate — but the
  gate floor is 8, so 9 chars is enough. Fixed by using "Short"
  (5 chars). Test-data length-counting is a fresh hazard now that
  the gate has a numeric threshold.
- The full e2e run hit a 429 rate-limit from allauth's signup
  endpoint (default 20/m per IP). 17 sequential signups across the
  full spec sweep crossed the limit. Polled until it cleared (60s
  window) and the second run passed cleanly. Worth flagging as a
  potential ops issue when the suite grows further — could be
  fixed with a per-session `ACCOUNT_RATE_LIMITS = {}` override in
  test settings, but that's scope-creep for this slice.
- The decision to defer template tiles felt right. The mechanism
  is trivial; the content is the hard (operator-collaborative)
  part. Splitting them keeps each slice atomic.
- The `DebugState` block stays on Steps 2-4. Useful visual signal
  that those steps are still scaffolding — when the operator
  clicks through, they see "real form" on Step 1 vs "debug
  panel" on Step 2-4. Clear progress narrative.
