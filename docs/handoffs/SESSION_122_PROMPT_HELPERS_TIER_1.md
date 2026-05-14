---
title: "Session 122 — Tier 1 port: prompt helpers from unified-donkey-betz"
date: 2026-05-13
status: complete
session: 122
previous_handoff: ./SESSION_121_MAKE_A_VIDEO_FLOW.md
---

# Session 122 — u-d-b prompt helpers, Tier 1

## TL;DR

- **What shipped:** Three pure-utility modules under
  `shell/character_os/prompts/` (sharpening + brand + creative)
  plus 31 unit tests. ~650 LOC total. Ported / adapted from
  unified-donkey-betz's `core/prompts/sharpening.py` and the data
  dicts buried inside u-d-b's BrandIdentityAgent /
  CreativeDirectorAgent. No Django app — these are pure data +
  pure functions. No wiring yet: future slices (wizard,
  make-a-video script generation) will compose them.
- **What's blocking next:** Two operator decisions before the
  wizard scope-lock doc can land. **Q2** — spokesperson
  archetypes: fixed list (Authority / Friend / Expert /
  Performer / Local Guide) or dynamically inferred from the
  brief? **Q5** — operator UX: template-driven fill-in-the-blank
  or conversational (system asks clarifying questions)? Both
  shape the wizard's surface area more than anything else.
- **What's in a weird state:** None. SESSION 122 is purely
  additive — no models changed, no migrations, no API surface,
  no SPA changes. All 8 Playwright specs + 3 vitest specs +
  4 backend smokes still pass.

---

## What changed (file-by-file)

### `shell/character_os/prompts/__init__.py` (new)

Re-exports the public surface so consumers can write
`from character_os.prompts import sharpen_prompt, ...` without
caring about file organisation.

### `shell/character_os/prompts/sharpening.py` (new — ~250 LOC)

Verbatim port of u-d-b's `core/prompts/sharpening.py`:

- `SHARPENING_REPLACEMENTS` — 30+ hedge → decisive pairs.
- `SHARP_DEBATE_RULES` / `SHARP_SYNTHESIS_RULES` /
  `SHARP_ANALYSIS_RULES` — pre-built rule blocks for agent
  system prompts.
- `sharpen_prompt(text)` — aggressive ALL-CAPS replacement.
  For internal system prompts only (Runway / OpenAI input).
- `add_sharpening_rules(prompt, rules_type)` — prepend a
  SHARP_*_RULES block.
- `check_prompt_sharpness(text)` — score 0-100, useful for
  post-generation validation.

**character-os addition:** `clean_business_brief(text)` — a
gentler pass tuned for user-typed copy. Strips fillers
("honestly", "basically", "literally") and softens
"I think we should probably" → "we". Preserves casing,
doesn't shout. Orphan-punctuation cleanup so deletions don't
leave ", ," fragments.

### `shell/character_os/prompts/brand.py` (new — ~170 LOC)

Extracted from u-d-b's `brand_identity_agent.py` class
attributes:

- `COLOR_PALETTES` — 6 named palettes (tech_modern,
  creative_bold, professional_corporate, eco_natural,
  luxury_elegant, startup_energetic). Each has 5 hex values:
  primary, secondary, accent, background, text.
- `BRAND_STYLES` — 6 named styles (minimalist, modern,
  playful, professional, artistic, tech). Each has
  characteristics + avoid + fonts lists. The `avoid` list is
  the critical piece for negative prompting in image-gen
  models.
- `INDUSTRY_PALETTE_MAP` — short alias keys (`tech` →
  `tech_modern`) for ergonomic lookup.

Helper functions added:

- `get_palette(name)` — accepts either internal key or
  industry alias. Returns the palette dict or None.
- `get_style(name)` — straightforward lookup.
- `suggest_palette_from_brief(brief)` — **the headline helper
  for the wizard.** Pattern-matches keywords in the brief
  against a tunable hints table; falls back to
  `professional_corporate` (the safest neutral default for the
  SMB audience). 7 parametrised test cases cover each industry
  signal.

### `shell/character_os/prompts/creative.py` (new — ~210 LOC)

Extracted from u-d-b's `creative_director_agent.py`
`CREATIVE_PRINCIPLES` class attribute. **Adapted** for
character-os: replaced u-d-b's `logo` key (not relevant to a
spokesperson-driven video product) with character-os-shaped
keys matching `apps.videos.models.Video.Kind`:

- `spokesperson_ad` — shipped (SESSION 121 video pipeline).
- `cinematic_video` — planned subsequent slice.
- `dialogue_scene` — planned subsequent slice.
- `long_ad` — planned subsequent slice.

Plus `thumbnail` + `social` kept from u-d-b for Phase 4+ uses.

Each kind has three lists: `key_principles` (positive signals),
`common_mistakes` (negative signals for negative prompting),
`enhancement_tips` (concrete operator nudges). All written
character-os-specifically: e.g., spokesperson_ad's
key_principles include "Direct address — the spokesperson
speaks to one viewer, not a crowd" and "One claim, one CTA — no
buried lede."

Helper: `principles_for_kind(kind)` — returns dict or None for
unknown kinds.

### `shell/character_os/prompts/test_prompts.py` (new — ~190 LOC)

Pytest tests, 31 in total. Class-based organisation:

- `TestSharpenPrompt` — replacement correctness, case-
  insensitivity, word boundaries (`maybe` doesn't munge
  `maybelline`), longer-phrase precedence.
- `TestCleanBusinessBrief` — filler stripping, voice
  preservation, capitalisation preservation, orphan-comma
  cleanup.
- `TestCheckPromptSharpness` — scoring at the extremes.
- `TestPalettes` — every palette has required keys, lookup by
  alias works, unknown returns None.
- `TestStyles` — every style has required keys, lookup works.
- `TestSuggestPalette` — **7 parametrised cases** covering each
  industry signal + empty-brief fallback + drift-guard test
  (every `INDUSTRY_PALETTE_MAP` value points at a real palette).
- `TestCreativePrinciples` — shipped kind is present, every
  kind has all three sections with ≥3 items, lookup works, all
  four video kinds named in `MEDIA_ENGINE_INTERNAL_API.md` are
  covered.

### `docs/design/PROMPT_HELPERS.md` (new)

Public-surface doc. Cites the u-d-b provenance file-by-file.
Documents the **planned wiring points** (wizard step 1 brief
cleaning + palette suggestion; render-flow script augmentation;
LLM-output validation) without committing to specific
implementations. Lists what's deliberately out of scope (Tier
2 `DynamicPromptBuilder`, Tier 3 agent harness). Explains how
to extend each dict.

### `shell/pyproject.toml` (unchanged, but dev deps now installed)

`pytest>=8.0` + `pytest-django>=4.9` were in the `[project.optional-
dependencies] dev` group already; installed for this session so
the new tests can run. No source change.

---

## Verification gates

- `python manage.py check` — 0 issues.
- `python manage.py migrate --check` — clean (no schema changes).
- `python -m pytest character_os/prompts/` — **31 passed in 0.07 s**.
- `python manage.py smoke_headless_auth` — PASS.
- `python manage.py inventory` — clean regen.
- `pnpm build` — no SPA changes; previous build still valid.
- `pnpm test` — 3 vitest passes.
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### Pure-utility modules vs Django apps

Whether to put helpers in a Django app (`apps.prompts`) or a
plain Python module (`character_os/prompts/`) is a real
decision. Rules of thumb:

| Need | Pick |
|---|---|
| Django models | App |
| Migrations | App |
| API endpoints (DRF viewsets, custom views) | App |
| Settings consumers | App (so settings_ready hook fires correctly) |
| Pure functions + data | Module |
| Cross-app reusable utilities | Module under `character_os/` |

Tier 1 is the second case all the way down — pure functions,
zero state, no I/O. Module under `character_os/` was the right
call. If Tier 2 lands later (`DynamicPromptBuilder` with
context-dependent state), that might warrant an app. Don't
preemptively make this one.

### Three-way replacement table > one-way "improver"

u-d-b's sharpening rules ship aggressive ALL-CAPS replacements
because their use case is agent-vs-agent debate where decisive
language wins. character-os's use case is broader: some prompts
go to models (aggressive sharpening is fine), some prompts get
rendered as user-facing copy (aggressive sharpening would
mangle the brand).

The fix: keep both. `sharpen_prompt` is the aggressive version,
`clean_business_brief` is the gentle version, callers pick the
right one. Same data table, different replacement strategies.

This is the right pattern when porting from a sibling project
that has slightly different opinions than ours. Don't fight the
source; layer on top.

### Keyword-pattern → palette inference is "good enough" v1

`suggest_palette_from_brief` uses a hard-coded keyword hints
table. It's not ML, it's not embedding lookup, it's not LLM-
backed. It's regex.

That's fine for v1. The wizard surfaces the suggestion as a
**default** the operator can override. If the keyword table
mis-classifies, the operator picks something else; the misclass
isn't a hard failure.

When (if) we want better inference: swap the implementation
behind the same function signature. Embed the brief, find the
nearest palette description, return it. The callers don't
change. That's the win of keeping the public surface narrow.

### CREATIVE_PRINCIPLES is the highest-leverage adaptation

The other two dicts (palettes, styles) were verbatim copies.
`CREATIVE_PRINCIPLES` got the most attention: u-d-b's `logo`
key was useless for character-os, the `thumbnail` + `social`
keys were kept but not adapted, and four NEW keys
(`spokesperson_ad`, `cinematic_video`, `dialogue_scene`,
`long_ad`) were written from scratch to match character-os's
video kinds.

The writing was the easy part once the SHAPE was clear from
u-d-b. The shape: each kind has three lists (positive, negative,
nudges), each list has 3-4 short imperative bullets. That shape
is what makes the data composable into Runway prompts later.

### Tests as drift guards

The drift-guard tests
(`test_industry_map_covers_all_known_industries`,
`test_covers_all_video_kinds_we_plan`) are the load-bearing
piece of the test suite. If a future SESSION adds a new entry
to one dict and forgets the matching entry in another, the
tests fail loudly. This is more useful than testing the
specific contents (those will drift legitimately).

---

## SESSION 123 — entry point (blocked on operator)

The natural next slice is the Spokesperson create wizard scope-
lock doc. It's blocked on two questions:

**Q2 — Spokesperson archetypes.** Two options:
  - **Fixed list** (5 named archetypes — Authority, Friend,
    Expert, Performer, Local Guide). Operator picks one in the
    wizard; the choice drives portrait generation defaults +
    voice preset hints + brand style suggestion.
  - **Dynamic inference** from the brief. No archetype picker;
    the system reads the brief and decides.

  Recommendation: fixed list for v1. SMB owners don't know
  what an archetype is; the picker frames the abstract idea
  in 5 concrete options. Dynamic inference is Phase 4 once
  we have data on which archetype each customer actually
  picked.

**Q5 — Operator UX.** Two options:
  - **Template-driven** — fill-in-the-blank form, the system
    shows palette / brand-style / tone suggestions inline as
    the operator types. Operator can accept or override every
    suggestion.
  - **Conversational** — system asks clarifying questions
    ("what makes your business different?", "who's your typical
    customer?") and assembles the brief from the answers.

  Recommendation: template-driven for v1. Conversational adds
  scope (chat-style UI, multi-turn state, follow-up question
  generation) and the audience is non-marketers who probably
  want to type fast and move on, not have a conversation.
  Conversational is a great Phase 4 upgrade.

Once those land, the wizard scope-lock doc is straightforward
to write.

---

## AI notes

- The hardest part of the slice was deciding WHAT NOT to port.
  The Explore agent's research was thorough; the temptation was
  to port everything. Discipline: ship Tier 1 only, wire it in
  one slice at a time, see what's needed before adding Tier 2.
- The `clean_business_brief` helper is the character-os-
  specific addition I'm most confident about. It's the
  difference between u-d-b's "shout at the model" approach and
  character-os's "preserve the operator's voice" approach. Same
  source, different downstream.
- The orphan-comma bug in `clean_business_brief` was the only
  real failure across 31 tests. Caught in one rerun, fixed in
  three lines. Worth flagging: when chaining text-replacement
  passes, always test the deletion-leaves-orphan-punctuation
  edge case.
- The CREATIVE_PRINCIPLES adaptation took longer than expected
  because writing good per-kind principles is real work. Each
  bullet has to be specific enough to feed into a Runway prompt
  but general enough to apply across briefs. Worth keeping in
  mind that data dicts can be the high-leverage part of a port
  — and they can require domain knowledge u-d-b doesn't have.
