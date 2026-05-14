---
title: "Prompt helpers — Tier 1 port"
status: active
generated: 2026-05-13 (SESSION 122)
companion_doc: SPA_ARCHITECTURE.md
phase: 3
---

# Prompt helpers

> **Read first:** the SESSION 122 research write-up in
> `docs/handoffs/SESSION_122_*.md`. That doc covers the three tiers
> in u-d-b's prompt-augmentation system and why SESSION 122 ports
> Tier 1 only.

---

## Purpose

Operators of character-os are small-business owners who don't
think of themselves as marketers (design lock §1.1). They type
loose business briefs; the system needs to translate those into
the strict prompts Runway / OpenAI / future LLMs handle well —
without making the operator do prompt engineering.

The prompt helpers live in `shell/character_os/prompts/`. They
are **pure utility modules**: no Django app, no models, no
migrations, no API endpoints. The wizard slice (and downstream
slices like make-a-video script generation) will import them
freely.

---

## Public surface

```python
from character_os.prompts import (
    # ---- sharpening ----
    sharpen_prompt,            # aggressive — for internal system prompts
    clean_business_brief,      # gentle — for user-typed copy
    check_prompt_sharpness,    # validate LLM output for hedging
    add_sharpening_rules,      # prepend SHARP_*_RULES block
    SHARP_DEBATE_RULES,        # constants
    SHARP_SYNTHESIS_RULES,
    SHARP_ANALYSIS_RULES,
    SHARPENING_REPLACEMENTS,

    # ---- brand identity ----
    COLOR_PALETTES,            # 6 named palettes (hex colors)
    BRAND_STYLES,              # 6 style descriptors (characteristics/avoid/fonts)
    INDUSTRY_PALETTE_MAP,      # industry → palette name
    get_palette,               # by name OR by industry alias
    get_style,
    suggest_palette_from_brief,  # the headline helper for the wizard

    # ---- creative principles per kind ----
    CREATIVE_PRINCIPLES,       # per video kind: key/mistakes/tips
    principles_for_kind,
)
```

Every function is pure — no Django, no I/O, no LLM calls,
deterministic. Easy to test, easy to compose.

---

## Provenance

Three source files in unified-donkey-betz were the basis:

| character-os file | u-d-b source | Notes |
|---|---|---|
| `prompts/sharpening.py` | `core/prompts/sharpening.py` | Verbatim port + character-os-specific `clean_business_brief` helper added. |
| `prompts/brand.py` | `core/agents/strategy/brand_identity_agent.py` (lines 211-298) | Extracted three class attributes (`COLOR_PALETTES`, `BRAND_STYLES`, `INDUSTRY_PALETTE_MAP`) into module-level data. Added `get_palette` / `get_style` / `suggest_palette_from_brief` helpers. |
| `prompts/creative.py` | `core/agents/executive/creative_director_agent.py` (lines 180-241) | Extracted `CREATIVE_PRINCIPLES` dict. **Adapted the keys** for character-os: replaced `logo` (not in our v1 product) with `spokesperson_ad` + `cinematic_video` + `dialogue_scene` + `long_ad` (matching `apps.videos.models.Video.Kind`). Kept `thumbnail` + `social` for Phase 4+ uses. Added `principles_for_kind` helper. |

The agent harness around the latter two was **not** ported —
those classes are tightly coupled to u-d-b's BaseAgent + OpenAI
client + Memory Palace + time-travel session recorder. ~500 LOC
of harness per agent, ~50 LOC of useful logic. Extraction was
the right call.

---

## Intended wiring points (planned, not yet built)

These are the slices that will consume the helpers. None of them
have been built yet — Tier 1 lands the infrastructure; subsequent
slices wire it in.

### 1. Spokesperson create wizard (next major slice)

The wizard collects a business brief on step 1. As soon as the
brief is non-empty:

- `clean_business_brief(brief)` strips fillers + obvious hedges
  without mangling the operator's voice. Stored as
  `Spokesperson.business_brief`.
- `suggest_palette_from_brief(brief)` returns a palette name.
  Used on subsequent wizard steps (e.g., to seed the portrait
  generation prompt with consistent colors).

The operator can override the suggestion at any time. The
helper is a "good default", not an authority.

### 2. Make-a-video script generation (later slice)

When the operator submits a render with a brief:

- `principles_for_kind(video.kind)` returns the key_principles
  + common_mistakes + enhancement_tips for that video kind.
- Backend composes a Runway script prompt: spokesperson context
  + brief + injected principles.
- `sharpen_prompt(internal_prompt)` aggressively de-hedges the
  composed string before it goes to Runway. The model never
  sees "we should probably make this dramatic" — it sees
  "WE MUST make this dramatic".

### 3. LLM-output validation (Phase 4+)

When the SPA gets back AI-generated copy (e.g., a generated
brief, a generated voice description), pass it through
`check_prompt_sharpness(text)` and surface a "this sounds wishy-
washy" hint if `is_sharp` is False. Optional UX nudge for the
operator.

---

## Out of scope (Tier 2 + Tier 3)

The SESSION 122 research surfaced two larger pieces. Both are
deliberately deferred:

### Tier 2 — `DynamicPromptBuilder` (u-d-b's prompt augmentation engine)

`core/super_platform/prompt_builder.py` (347 LOC) takes a
loose user query + Spokesperson context + recent activity + agent
mood → outputs a tailored system prompt. **This is the actual
"loose intent → polished prompt" mechanism.** Worth porting —
but only when the make-a-video flow needs richer scripts than
the Tier 1 helpers produce. Estimated 1-2 sessions of work.

### Tier 3 — full agent harness

u-d-b's `BaseAgent`, `agent_registry`, `Memory Palace`, mood
states, time-travel recording, spider network integration.
Tightly coupled to u-d-b infrastructure (~400 LOC of Django ORM
+ WebSocket plumbing). character-os would build its own
lightweight agent class when actually needed — not port
u-d-b's.

---

## How to extend

When a new content kind ships (e.g., when we add `cinematic_video`
to the SPA's render flow), the rule is:

1. Add the kind's principles to `CREATIVE_PRINCIPLES` in
   `prompts/creative.py`.
2. Add a test case to `prompts/test_prompts.py` confirming
   `principles_for_kind` returns it.
3. The backend's make-a-video pipeline picks it up automatically
   via `principles_for_kind(video.kind)`.

When a new brand style or color archetype lands (e.g., when the
operator's customers want a "vintage" or "noir" aesthetic):

1. Add to `BRAND_STYLES` / `COLOR_PALETTES`.
2. If it maps to an industry, add to `INDUSTRY_PALETTE_MAP`.
3. Add brief-detection hints to `_BRIEF_INDUSTRY_HINTS` in
   `prompts/brand.py` so `suggest_palette_from_brief` can find it.
4. Test cases for the new mapping.

The pattern: **data dicts are the public surface**. Helper
functions are thin wrappers that make consumption ergonomic.
Adding a new entry to a dict shouldn't require touching any
function code.

---

## Change log

- 2026-05-13 (SESSION 122) — Initial Tier 1 port.
  `sharpening.py` + `brand.py` + `creative.py` + 31 unit tests.
  No wizard yet; no make-a-video augmentation yet. Helpers
  available for future slices to compose.
