---
title: "Session 171 — W11.2 dogfood + Tier 1 fixes + Stability port + Mascot auto-inject"
date: 2026-05-16
status: complete
session: 171
previous_handoff: ./SESSION_170_W11_2_VOICE_REBAKE.md
---

# Session 171 — W11.2 dogfood + Tier 1 fixes + Stability port + Mascot auto-inject

## TL;DR

Wide-ranging session driven by operator dogfood of the W11.2
voice-swap + avatar-rebake surfaces shipped in SESSION 170.
Multiple bugs surfaced, multiple slices shipped:

* **W11.2 dogfood validated** end-to-end against real Runway —
  voice swap action + rebake action both fire cleanly from the
  SPA. Operator drove the UI; AI tailed DB / media-engine logs.
* **Tier 1 visual_template fix** (W11.3 pre-work) — re-bake was
  hardcoded to ``template="coach"`` if the rebake body lacked an
  override, which silently flipped Marcus from a mascot battle
  unicorn to a photorealistic human business coach on his first
  rebake. Added ``visual_template`` field to ``Spokesperson``,
  migration + backfill, wizard wiring, default-from-row in
  rebake action, surfaced in rebake modal.
* **K6.6.1 fix** — Marcus's first real-Runway render leaked
  ``business_brief`` content into the generated script
  ("I'm Marcus, your AP history teacher who..."). Fixed three
  ways in ``_system_prompt``: fenced the brief as tone-only
  guidance, dropped "grounds them in who you are" opener
  framing, added explicit anti-recitation rule.
* **gpt-5 family migration** — K6 / K9 / R6 promoted from
  ``gpt-5-mini`` to ``gpt-5`` (full). ``script_splitter`` +
  transcription stayed on mini (structured-output, no
  generation quality gain). K6's ``MAX_OUTPUT_TOKENS`` raised
  500 → 2000 to accommodate gpt-5's reasoning-token budget;
  ``reasoning_effort`` held at ``low`` after experimenting
  with ``medium`` (consumed full budget on reasoning, returned
  empty output_text).
* **W11.3 — Stability port** — ``stability_ai_service.py`` +
  ``style_library.py`` (42 style presets) + new
  ``stability_portrait.py`` orchestrator copied over from
  ``unified-donkey-betz``. Tested end-to-end against Marcus.
  **Outcome**: Stability portraits bake into Runway avatars
  cleanly but mis-lip-sync — Runway's avatar rig is tuned for
  gen4_image's face geometry, not Stability's. **Reframed**:
  Stability is the right provider for non-avatar image
  generation (scenes, b-roll, product); Runway gen4_image
  stays the avatar path. W11.6 work.
* **Mascot anthropomorphic auto-inject (Tier 1)** — operators
  shouldn't have to know the magic word "anthropomorphic" to
  get a creature-anatomy render. New
  ``_MASCOT_CREATURE_CLAUSE`` + ``_subject_implies_creature_intent``
  helper auto-inject the clause as a second sentence when
  ``template=="mascot"`` AND the operator's subject lacks the
  keyword. Cast-seed subjects (which all contain "anthropomorphic")
  bypass the inject — existing test contracts preserved.
* **Tier 2 attempt + revert** — replaced ``"Polished {anchor}
  portrait"`` with ``"Character illustration of"`` + dropped
  ``"Professional advertising character design."`` for mascot
  template. Operator visual judgment: still plasticy.
  Investigation revealed the hackathon prompts are
  **bit-identical** to character-os's pre-SESSION-171 state
  (subtree migration brought them over verbatim). Donny / Riggs
  / Maya were baked with the EXACT same template that Sasha /
  Marcus use; the difference is variance + subject complexity
  (Marcus's elaborate armor + Sasha's "sleek...subtle branding"
  push the commercial anchor harder than Donny's casual
  hoodie). Reverted Tier 2; kept Tier 1.

Tests: Django **718 → 727** (+9). Media-engine **108 → 111**
(+3). SPA vitest **53** (unchanged; fixture updated for the
new ``visual_template`` field).

## What shipped — slice by slice

### W11.2 dogfood (operator-driven)

Operator opened Marcus's edit modal in the SPA, swapped voice
from ``marcus`` → ``clara`` → ``felix`` exploring the surface,
then exercised the Re-bake button. The voice swap fires
``POST /api/spokespeople/<id>/change-voice/`` which PATCHes the
live Runway avatar; the DB persists ``voice_id`` regardless of
whether the live PATCH succeeds.

**Calibration finding from this exercise**: the SPA currently
discards the ``voice_patch: {status, error}`` envelope returned
by the change-voice action. Modal closes silently regardless
of whether Runway accepted the PATCH. Worth surfacing as part
of a future W11 polish slice.

### Tier 1 — visual_template persistence

W11.2's rebake action hardcoded ``template = "coach"`` as the
fallback when the request body didn't include a ``template``
field. The SPA rebake modal never passed one. Marcus's first
rebake of the day used ``coach`` template (photorealistic
human) on a row whose original creation used ``mascot``
template (stylized creature). Operator got a "Marcus the human
Gen X history teacher" instead of "Marcus the battle unicorn."

**Fix**: persist the wizard's template choice on the row so
rebake can default to it.

* ``shell/apps/spokespeople/models.py`` — new
  ``VisualTemplate`` TextChoices + ``visual_template``
  CharField (default ``mascot``).
* ``shell/apps/spokespeople/migrations/0004_spokesperson_visual_template.py``
  — adds field; Django's default-backfill correctly assigns
  ``mascot`` to all 5 existing cast rows (seed cast + Marcus
  all originally baked with ``mascot``).
* ``shell/apps/spokespeople/serializers.py`` — exposes
  ``visual_template`` as writable so wizard's create payload
  round-trips.
* ``shell/apps/spokespeople/views.py`` — rebake action's
  ``template`` default flipped from hardcoded ``"coach"`` to
  ``spokesperson.visual_template or "mascot"``. Explicit body
  override still wins; new value persists back to the row.
  Validation against ``SUPPORTED_PORTRAIT_TEMPLATES`` added.
* ``shell/apps/spokespeople/tests/test_rebake_avatar.py`` — NEW
  file, 6 tests pinning: (1) rebake without body uses
  ``spokesperson.visual_template``, (2) explicit body override
  wins + persists, (3) invalid template raises 400, (4) row
  intent persists before media-engine call, (5) serializer
  round-trip for ``visual_template`` on create, (6) defaults
  to ``mascot`` when create omits it.
* SPA: ``web/src/lib/api/spokespeople.ts`` adds
  ``visual_template`` to the schema + ``CreateSpokespersonInput``;
  ``spokesperson-wizard.tsx`` sends it in the create payload;
  ``spokesperson-rebake-modal.tsx`` displays it in the
  confirm-spend grid so operators see which template they're
  about to use before clicking "Confirm + spend".

### K6.6.1 — system prompt business_brief leak

Operator's SESSION 169 Marcus render produced:
> *"I'm Marcus, a Gen X AP history teacher—short lesson on the
> Nerva–Antonine dynasty..."*

The opener was reciting Marcus's ``business_brief`` verbatim.
Cause was two lines in ``script_synthesis._system_prompt``:

1. ``f"Their business brief is: {brief}"`` — fenced no
   distinction between "use this for tone" and "use this as
   content".
2. K6.6's opener instruction (added SESSION 168) said *"grounds
   them in who you are and what this video is about"* — the
   "who you are" half was a near-explicit invitation to
   self-introduction.

**Fix** in ``shell/character_os/script_synthesis.py:322-365``:

* Brief now framed as ``"Context about the speaker (use this
  ONLY to shape tone and perspective — do NOT recite,
  paraphrase, or describe this in the script): {brief}"``.
* Opener instruction reduced to *"grounds the viewer in what
  this video is about"* (removed "who you are and").
* New explicit anti-recitation rule: *"Do NOT introduce
  yourself, name your role, describe your audience, or recite
  your background — the viewer cares about the topic, not your
  resume."*

3 new tests in
``shell/apps/compositions/tests/test_claim_verifier.py``:

* ``test_system_prompt_business_brief_fenced_as_tone_only_k6_6_1``
* ``test_system_prompt_drops_who_you_are_opener_framing_k6_6_1``
* ``test_system_prompt_includes_anti_recitation_rule_k6_6_1``

**Calibration finding**: the K6.6.1 fix removed the explicit
*"I'm Marcus, your tutor"* leak but gpt-5-mini still produced
"I'm Marcus, your AP Roman tutor" on its first post-fix render.
Negative instructions ("Do NOT introduce yourself") get
overridden when there's a strong positive pattern in the brief
(Marcus's brief contains a literal quoted opener and a role
description). The model swap to gpt-5 fixed it — better
instruction following.

### gpt-5 family migration

Promoted 3 generative call sites from ``gpt-5-mini`` to
``gpt-5``:

* ``character_os/script_synthesis.py`` (K6 brief synthesis)
* ``character_os/conversation_synthesis.py`` (K9 reply)
* ``character_os/realtime_memory.py`` (R6 session memory)

Kept ``gpt-5-mini`` for two structured-output call sites where
capability gain doesn't justify the 5x cost:

* ``apps/compositions/script_splitter.py`` (returns JSON array
  of integers)
* ``apps/compositions/transcription.py`` (returns one integer
  index)

**Calibration finding (memory updated)**: split model choice by
call-site type. Generative → gpt-5; structured-output →
gpt-5-mini. Per-render cost stays under $0.01 even on the
upgraded sites.

**Two operational gotchas captured in code comments**:

1. ``max_output_tokens`` on Responses API counts BOTH reasoning
   tokens AND actual output tokens. K6's old 500 cap was too
   tight for gpt-5; raised to 2000. Unused tokens cost nothing.
2. ``reasoning_effort="medium"`` on gpt-5 expands to consume
   the full budget on reasoning, returning empty
   ``output_text``. K6 stays on ``"low"`` — capability gain
   from the model swap alone is what closed the leak.

Updated test: ``shell/apps/realtime/tests/test_r6_session_memory.py``
— relaxed hardcoded ``"gpt-5-mini"`` assertion to read from
``MEMORY_MODEL`` constant.

### W11.3 — Stability port (reframed for W11.6)

Operator's premise: 10K+ unused Stability AI credits could be
the right provider for character-os image generation.

**Ported from unified-donkey-betz**:

* ``media-engine/app/services/stability_ai_service.py`` — low-
  level API client (adaptive timeout, exponential-backoff
  retry). Adapted from u-d-b's Django-coupled version to use
  FastAPI Settings + ``httpx`` (matches existing media-engine
  conventions; u-d-b used ``requests``).
* ``media-engine/app/services/style_library.py`` — verbatim
  copy. 42 style presets across 8 categories (photography,
  animation, digital_art, traditional_art, artistic_movements,
  genre, 3d_rendering, cultural, special). Pure data + lookup
  helpers.
* ``media-engine/app/services/stability_portrait.py`` — NEW
  orchestrator. Ties the two together with template-aware
  prompt construction + creature-anatomy negative prompts +
  Runway-friendly framing. Returns ``StabilityPortraitResult``
  with PNG path + cost in credits.
* ``media-engine/app/config.py`` — added
  ``stability_api_key`` + ``stability_base_url`` +
  ``stability_mock`` property.
* ``.env`` — ``STABILITY_API_KEY`` added (copied from u-d-b's
  .env).

**End-to-end test ran**: 5 Stability portraits generated for
Marcus across 3 iterations of the orchestrator's framing rules
(``concept_art`` → ``pixar`` style; "head-and-shoulders" →
"medium shot" → "tight headshot"). Each portrait baked
successfully into a Runway avatar via the existing
``create_avatar`` data-URI seam. Final pixar-style bake
rendered as a $0.25 video.

**Outcome — calibration finding saved as memory**:
Stability portraits **bake cleanly** but **lip-sync mis-maps**.
On Marcus specifically (long unicorn snout), Runway's rig
animated the nose tip instead of the mouth. Multiple style
presets tested; the mouth-vs-nose problem persisted. Root
cause hypothesis: Runway's avatar rig is trained on the face
geometry + proportions gen4_image produces; Stability's
output distribution is close enough to pass the avatar-bake
gate but different enough to confuse landmark detection.

**Reframed scope**: Stability is the right provider for
**non-avatar image generation** (scene illustrations, b-roll,
product shots, ad imagery) where the output won't be
face-animated by Runway. Avatars stay on Runway gen4_image.
W11.6 will formalize this as a "media generation purpose
registry" — ``purpose=avatar`` → Runway, ``purpose=scene`` /
``broll`` / ``product`` → Stability with the 42-preset
library.

### Mascot anthropomorphic auto-inject (Tier 1, shipped)

Same calibration insight that drove the K6.6.1 fix applied to
the portrait-prompt composer: operators shouldn't have to know
the magic word ``"anthropomorphic"`` to get a creature-anatomy
render. The seed cast subjects all contain it
("an anthropomorphic donkey founder character..."); a normal
operator typing "battle unicorn in Roman armor" wouldn't.
gen4_image then leans humanoid by default — Marcus repeatedly
rendered as "human with horse face in armor".

**Fix** in
``media-engine/app/services/character_studio_client.py``:

* New ``_MASCOT_CREATURE_CLAUSE`` — *"The character is a fully
  anthropomorphic creature with creature anatomy (fur, snout,
  hooves, paws, fangs as appropriate) — not a human in a
  costume, not a human in a mask."*
* New ``_subject_implies_creature_intent(subject)`` helper —
  conservative match on ``"anthropomorphic"`` / ``"anthro-"``.
* ``_compose_clean_prompt`` injects the clause as a SECOND
  sentence (immediately after the subject anchor, where the
  model weights it most) when ``template == "mascot"`` AND
  the helper returns False.
* Cast-seed subjects already contain ``"anthropomorphic"``,
  so the inject correctly SKIPS for them — existing test
  contracts preserved.

3 new regression tests in
``media-engine/tests/test_create_avatar_mock.py``:

* ``test_mascot_auto_injects_anthropomorphic_when_keyword_absent``
* ``test_mascot_no_double_inject_when_anthropomorphic_already_present``
* ``test_non_mascot_templates_never_auto_inject``

**End-to-end validation**: reset Marcus's stored
``visual_subject`` to a clean operator-intent form *("battle
unicorn in full Roman Centurions armor — bronze lorica
segmentata, red tunic, crimson cloak, holding a spear")* with
no manual creature-anatomy words. Re-baked. The composed
prompt's second sentence was the auto-inject clause;
operator's visual verdict: clean anthropomorphic creature, no
"human with horse face" leak. **Auto-inject is production-ready.**

### Tier 2 attempt + revert

Operator surfaced a second product complaint: even with
correct anthropomorphic anatomy, Marcus + Sasha "look plasticy"
while Donny / Riggs / Maya "look natural." Initial hypothesis:
``"Polished commercial portrait"`` opening + ``"Professional
advertising character design."`` trailing line anchor
gen4_image toward the plastic 3D-mascot product-render
aesthetic.

**Attempted Tier 2 fix**: replaced opening with ``"Character
illustration of"`` for mascot template; dropped the trailing
advertising-character-design line. 2 locked tests updated;
all 111 media-engine tests passed.

**Operator visual judgment**: still plasticy.

**Investigation**: diffed
``runway-hackathon/backend/app/services/character_studio_client.py``
against the character-os version. Result: **bit-identical**
prompt construction (the subtree migration brought it over
verbatim; only the SESSION-171-introduced auto-inject + Tier 2
changes differ in character-os). Donny / Riggs / Maya were
baked with the EXACT same prompt template that Sasha /
Marcus use.

**Conclusion**: Tier 2 hypothesis was wrong. The plastic-vs-
natural difference between Donny/Riggs/Maya (natural) and
Sasha/Marcus (plastic) is **variance + subject complexity**,
not the prompt template. Donny/Riggs/Maya have simple casual
outfits (hoodies); Sasha has "sleek...subtle branding"; Marcus
has elaborate armor + spear. Complex subjects push the
commercial anchor harder.

**Reverted Tier 2; kept Tier 1.** Re-baked Marcus + Sasha on
the restored hackathon-equivalent prompts. Operator visual
verdict on the re-bakes: **"Those nailed it!"** Final dogfood
videos rendered at session close:

* **Marcus**: avatar ``aa270223-...``, voice ``marcus``, script
  Attempt 1 (Nerva-Antonine dynasty perspective)
* **Sasha**: avatar ``9e40084d-...``, voice ``clara``, script
  pitch-deck guidance (new operator-supplied Sasha script)

## Calibration moments worth carrying

### 1. Human/AI testing split

When operator and AI co-dogfood a feature, operator drives the
SPA (visual / auditory judgment); AI drives the parallel API /
DB / log verification. Don't propose curl as an *alternative*
to the SPA path during dogfood — the SPA flow is part of what's
being tested. AI's job is the verification work that doesn't
need human eyes.

Saved as
``~/.claude/projects/.../memory/feedback_human_ai_testing_split.md``.

### 2. Runway avatar rig needs Runway-generated portraits

External-provider portraits (Stability SD3, pixar, etc.) bake
into Runway avatars cleanly but mis-lip-sync. Use Runway
gen4_image for any portrait that will be face-animated; use
external providers only for non-avatar image generation
(scenes, b-roll, products).

Saved as
``~/.claude/projects/.../memory/feedback_runway_avatar_rig_needs_runway_portraits.md``.

### 3. gpt-5 family split by call-site purpose

Generative call sites (K6 brief synthesis, K9 reply, R6
memory summary) → gpt-5 (full). Structured-output call sites
(split_script, transcription hook picker) → gpt-5-mini. The 5x
cost difference is rounding error for generative calls
(~$0.001/render) where capability gain is real, and
unjustified for structured-output where mini works fine.

Updated the existing
``~/.claude/projects/.../memory/feedback_openai_gpt5_responses_api.md``
to reflect the split.

### 4. reasoning_effort=medium consumes full output_token budget on gpt-5

On gpt-5 specifically, ``reasoning_effort="medium"`` expands
to fill whatever ``max_output_tokens`` budget you give it on
non-trivial prompts, often returning empty ``output_text``
with all tokens spent on reasoning. K6 tested this: 500-cap
hit immediately; 2000-cap also hit immediately. K6 stays on
``"low"`` for now. Documented in
``script_synthesis.py:54-77`` code comments.

### 5. max_output_tokens includes reasoning tokens on Responses API

Surprising default for anyone coming from chat.completions.
Worth checking if existing K9 / R6 calls have headroom; raised
K6 cap from 500 → 2000 prophylactically.

### 6. Hackathon prompts ARE character-os prompts

When operator instinct says "go back to how the hackathon did
it", verify the actual file diffs first. The
``character_studio_client.py`` was subtree-migrated from
runway-hackathon verbatim. Bit-identical prompt construction.
Donny / Riggs / Maya look natural because they were variance-
lucky bakes on simple casual subjects; Sasha / Marcus look
plasticy because their subjects are more complex (sleek
styling, elaborate armor). The "plastic" failure mode is
subject-driven and Runway-rig-driven, not a prompt-template
gap.

### 7. The auto-inject pattern generalizes

The Tier 1 mascot auto-inject (silently anchor creature-intent
when operator didn't type the magic word) is the same shape as
the K6.6.1 anti-recitation rule (silently steer model away
from reciting brief content). Both fix product UX by removing
"you need to know the magic word" friction. Worth as a
calibration template for other prompt surfaces.

## What's next (SESSION 172)

* **W11.6 — multi-purpose image generation registry.** The
  ported ``stability_portrait.py`` + ``style_library.py``
  become the foundation. New ``purpose`` field on portrait
  generation calls: ``avatar`` → Runway, ``scene`` /
  ``broll`` / ``product`` → Stability. SPA exposes the 42-
  preset library for non-avatar image generation throughout
  the platform (recipe templates, b-roll generation, ad
  imagery).
* **F8.1 — K10 seed corpus.** Still queued; waiting on
  operator-authored markdown.
* **K6.4 v3 — embedding-similarity fallback.** Holds until a
  real paraphrase miss surfaces during operator dogfood.
* **K7.x — YouTube ingest fix.** Queued.
* **K6.3 — Brief length cap.** Queued (likely moot now that
  K6 produces clean briefs).
* **K7.1 — Cost telemetry surface in SPA.** Queued.
* **W11.x — surface voice_patch.status in the edit modal.**
  Calibration finding from this session's dogfood: the SPA
  silently discards the live PATCH result envelope.

## Files changed

### Django (shell/)
* ``apps/spokespeople/models.py`` — ``VisualTemplate`` choices +
  ``visual_template`` CharField.
* ``apps/spokespeople/migrations/0004_spokesperson_visual_template.py``
  — NEW.
* ``apps/spokespeople/serializers.py`` — expose
  ``visual_template``.
* ``apps/spokespeople/views.py`` — rebake default from row +
  validation.
* ``apps/spokespeople/tests/__init__.py`` + ``test_rebake_avatar.py``
  — NEW (6 tests).
* ``character_os/script_synthesis.py`` — K6.6.1 leak fix + gpt-5
  + max_output_tokens 500 → 2000.
* ``character_os/conversation_synthesis.py`` — gpt-5 swap.
* ``character_os/realtime_memory.py`` — gpt-5 swap.
* ``apps/compositions/tests/test_claim_verifier.py`` — 3 new
  K6.6.1 regression tests.
* ``apps/realtime/tests/test_r6_session_memory.py`` — relax
  hardcoded model assertion.

### Media-engine
* ``app/config.py`` — Stability settings.
* ``app/services/stability_ai_service.py`` — NEW (httpx-based
  port).
* ``app/services/style_library.py`` — NEW (verbatim port from
  u-d-b; 42 presets).
* ``app/services/stability_portrait.py`` — NEW (orchestrator).
* ``app/services/character_studio_client.py`` — Tier 1
  auto-inject + helper.
* ``tests/test_create_avatar_mock.py`` — 3 new auto-inject
  tests.

### SPA (web/)
* ``src/lib/api/spokespeople.ts`` — ``visual_template`` in
  schema + ``CreateSpokespersonInput``.
* ``src/components/spokesperson-wizard.tsx`` — send
  ``visual_template`` in create payload.
* ``src/components/spokesperson-rebake-modal.tsx`` — show
  template in confirm-spend grid.
* ``src/components/spokesperson-edit-modal.test.tsx`` —
  fixture updated + pre-existing TS6133 fixed.

### Memory / docs
* ``memory/feedback_human_ai_testing_split.md`` — NEW.
* ``memory/feedback_runway_avatar_rig_needs_runway_portraits.md``
  — NEW.
* ``memory/feedback_openai_gpt5_responses_api.md`` — updated
  for the gpt-5 vs mini split.
* ``memory/MEMORY.md`` — index updated.
* ``.env`` — ``STABILITY_API_KEY`` added.
* ``docs/CHARACTER_OS_INVENTORY.md`` — regenerated.
* ``00-START-NEXT-SESSION.md`` — SESSION 172 priorities.

## Tests

| Suite | Before | After | Δ |
|---|---|---|---|
| Django | 718 | 727 | +9 (6 rebake + 3 K6.6.1) |
| Media-engine | 108 | 111 | +3 (auto-inject regression) |
| SPA vitest | 53 | 53 | 0 (one fixture updated) |

## Cost ledger (real spend this session)

* **Runway credits**: roughly 46,969 → operator's session-end
  balance check welcome. ~10 portrait bakes + ~7 video
  renders accross all iterations.
* **Stability credits**: 32.5 (5 portraits × 6.5 — sd3-large).
* **OpenAI**: ~$0.10 across all K6 probes + model-swap tests
  + final renders' synthesis calls.

## Closing dogfood videos

These two renders capture the SESSION 171 end-state for the
Marcus + Sasha cast members — operator-approved bakes on
hackathon-equivalent prompts (Tier 1 auto-inject active;
Tier 2 reverted).

* **Marcus** — composition ``5878fa8a-...``, avatar
  ``aa270223-...``, voice ``marcus``, Attempt 1 script
  (Nerva-Antonine dynasty perspective). Validates: Tier 1
  auto-inject lands creature-anatomy correctly; K6.6.1 fix +
  gpt-5 produce clean script; mascot template + Runway
  gen4_image + Runway rig = clean lip-sync.
* **Sasha** — composition ``6f4baaad-...``, avatar
  ``9e40084d-...``, voice ``clara``, fresh operator-supplied
  pitch-deck script. Validates: same hackathon-equivalent
  prompt produces a clean Sasha bake on retry (the SESSION
  170 voice swap dogfood target also closed cleanly).

---

*Handoff written end-of-SESSION 171. Tier 1 auto-inject is
production-ready; Tier 2 hypothesis disproved by hackathon-
prompt comparison; Stability port reframed for W11.6
non-avatar image gen.*
