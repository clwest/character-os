---
title: "Dialogue Scene AI Topic Mode — scope lock"
status: active (scope-locked, no code yet)
generated: 2026-08-16 (SESSION 257)
companion_docs:
  - "UI_REDESIGN_V2.md"
  - "VIDEO_COMPOSITION_V1.md"
  - "KNOWLEDGE_LAYER.md"
  - "WORKSPACE_FABRIC_V1.md"
  - "MEDIA_ENGINE_INTERNAL_API.md"
phase: 4
---

# Dialogue Scene — AI Topic Mode

> **Read first:** `VIDEO_COMPOSITION_V1.md` (Dialogue Scene is one
> of the V-arc's shipped recipes; this doc adds a mode on top
> without touching the render graph), `KNOWLEDGE_LAYER.md` (K2
> retrieval + K6 synthesis + K6.4 verification are all reused
> per-character), and the SESSION 257 cost-correction commit
> `46f5efd` (turn count is a pacing lever, not a COGS lever).
>
> **Prior art:**
> - Existing `dialogue_scene` recipe (manual mode) at
>   `shell/apps/compositions/recipes.py:1386-1417` — the
>   render graph this doc reuses without modification.
> - Existing K6 synthesis path in
>   `shell/character_os/script_synthesis.py` — the 5-section
>   prompt shape (Factual Basis / Character Voice / Brand
>   Voice / Writing Contract / Task) this doc extends for two
>   characters.
> - Existing K6.4 verifier at
>   `shell/character_os/claim_verifier.py` — per-turn
>   verification against the speaking character's corpus,
>   unchanged.
> - Existing `WritingContract` at
>   `shell/character_os/writing_contract.py` — extended with
>   a `dialogue_scene` shape; version bumped 1 → 2.

---

## Purpose

Operators can render multi-character dialogue today by writing
every line themselves. That works and stays. But the manual
authoring surface asks the operator to be both the director and
the writer for every scene — and to hand-craft dialogue that
sounds like each Teammate speaking in their own voice, with
reactions, callbacks, and grounded facts. That's real work,
and most operators skip it.

**AI Topic mode** takes:

- two selected Teammates from the workspace
- a one-sentence topic
- an approximate target duration
- optionally: workspace knowledge on, an operator-pinned opener

…and produces a validated multi-character dialogue that runs
through the **existing** `dialogue_scene` render graph
unchanged. Each character stays recognizably themselves. They
react to each other rather than deliver alternating monologues.
Each character's factual claims stay grounded in that
character's scoped knowledge. Their established relationship
surfaces naturally.

The unit of generation is the **conversation**. Not
independently-synthesized turns per character stitched
together — that would break setup/payoff, callback, and
disagreement. One structured synthesis call sees the full
scene and writes the whole exchange.

### Why scope-lock first

This slice touches three subsystems:

1. **Prompt architecture.** The K6 5-section shape ships
   single-character today. Adding a second character block is
   a load-bearing structural extension — done badly, it
   silently flattens the two voices.
2. **Knowledge scoping.** Per-character K2 retrieval + K6.4
   verification must remain isolated. Patch's claims verify
   against Patch's corpus; Rivet's against Rivet's. Getting
   this wrong leaks scoped facts across the cast.
3. **Structured LLM output.** OpenAI Responses API JSON output
   with post-parse validation. Cast-membership + line-index
   ordering are load-bearing; a hallucinated third speaker or
   a re-indexed turn silently corrupts the render.

Locking scope now costs 30 minutes; unbuilding a wrong
architecture after the fact costs a session.

---

## Contract rules (load-bearing)

These bind every dialogue AI Topic slice the same way
`VIDEO_COMPOSITION_V1.md`'s rules bind every V-slice.

1. **Same recipe, same render graph.** AI Topic mode lives on
   the existing `dialogue_scene` recipe row. The manual path
   is unchanged. AI Topic produces the same normalized
   `lines = [{spokesperson_id, text}, …]` shape that the
   current manual editor produces, then hands off to the
   existing `starters.dialogue_scene` starter, which spins
   the same per-turn `generate_avatar_speech` + terminal
   `concat_clips` + optional `add_intro_outro` graph.

2. **AI owns writing; existing render owns rendering.** The
   AI Topic branch's ONLY responsibility is "who speaks when
   + what they say." Every downstream detail
   (avatar_id resolution, Runway task creation, ffprobe
   duration provenance, ffmpeg concat, outro card) reuses
   what already ships. New rendering behavior is out of
   scope.

3. **Manual mode is untouched.** `dialogue_mode = "manual"`
   (the default) preserves the current N-cast arbitrary
   operator-authored form + starter path bit-for-bit. Zero
   behavior change. A composition submitted with no
   `dialogue_mode` param at all is treated as manual for
   backwards-compat.

4. **One structured synthesis call per scene.** Not one call
   per character. Patch and Rivet must be visible to each
   other's turns for setup/payoff, callback, correction, and
   disagreement to work. The LLM receives the full topic,
   both character voice blocks, both factual corpora
   (labeled), the pinned opener (if any), and returns the
   whole scene in one JSON payload.

5. **Structured JSON output, stable aliases.** OpenAI
   Responses API with `response_format={"type": "json_object"}`
   (proven pattern — `character_os/transcript_miner.py`
   already ships this shape). The LLM emits stable
   Character-OS-generated aliases (`"patch"`, `"rivet"`),
   not UUIDs. Alias→Teammate resolution runs post-parse
   inside `character_os/dialogue_synthesis.py`.

6. **Post-parse validation is mandatory.** Cast membership,
   line-index contiguity, non-empty text, per-turn provider
   char cap, cast-only-no-third-speaker, aggregate duration
   inside acceptance band, turn count inside sane
   duration-specific bounds. Any failure rejects the whole
   synthesis, persists the raw LLM output to
   `Composition.rejected_synthesis`, and DOES NOT create
   any composition steps. One bounded corrective resynth is
   allowed with a targeted hint; no further retries.

7. **Per-character K2 retrieval, per-character K6.4
   verification.** `retrieve_for_teammate(patch, topic)` and
   `retrieve_for_teammate(rivet, topic)` are called
   independently. `build_factual_corpus` + `build_allowed_vocabulary`
   run per character. K6.4 verifies each turn against the
   speaking character's corpus + vocab only. Cross-character
   factual leakage is prevented by K2's existing M2M scope
   filter (see `apps/embeddings/retrieval.py:147-197`) —
   structurally, not by convention.

8. **Character voices stay independent.** The K6 prompt
   ships two labeled blocks (`--- CHARACTER A — {name} ---`
   / `--- CHARACTER B — {name} ---`) each carrying the full
   single-character voice section (tone axes, personality,
   POV, signature phrases). No blending, no flattening.
   Brand voice sections are also per-character; each
   character's `never_say` applies to that character's own
   lines only.

9. **Duration is aggregate, not per-character.** Target
   duration means total scene runtime, not per-character.
   The dialogue synthesis wrapper sums predicted char
   counts and checks against the same ±20% acceptance
   contract talking-head uses. `15 cps` estimator and
   `0.90 target multiplier` are reused verbatim in v1 —
   dialogue may recalibrate per-character delivery later
   without touching talking-head.

10. **Opener is a hard synthesis constraint, not a
    post-hoc replacement.** If the operator supplies an
    opener, it goes into the K6 prompt as a required first
    turn belonging to the primary spokesperson. The rest
    of the dialogue is written **in response** to that
    opener. Post-parse validation confirms the returned
    first turn preserves the opener per existing K6 opener
    semantics. Opener is not factual evidence and does not
    enter K6.4 corpus.

11. **Cost model: ~$0.02 per turn.** Per the SESSION 257
    empirically-verified Runway billing (`46f5efd`),
    `/v1/avatar_videos` = 2 credits = $0.02 flat per
    completed call. Cost forecasts and actuals reflect this.
    Turn count has NO cost-driven minimum or maximum in
    this arc; short reactions ("Define 'still.'") are
    explicitly valid.

12. **Writing Contract v2 is a global bump; existing
    shapes carry through unchanged.** `WRITING_CONTRACT_VERSION`
    goes 1 → 2 with the addition of the `dialogue_scene`
    shape. Compositions rendered via `standalone` / `long_form`
    shapes continue to emit the same contract text; only the
    version stamp changes on their `Composition.writing_contract_version`
    column. No re-rendering, no back-compat shim.

13. **AI Topic hides the manual editor.** When
    `dialogue_mode == "ai_topic"`, the SPA does NOT render
    `DialogueLinesEditor`. The operator never creates blank
    lines to fill. Turn count, speaker order, turn length,
    and exact wording are all dialogue-synthesis
    responsibilities — not operator UI decisions.

14. **No forced speaker alternation.** The writer may
    produce `A → B → B → A → B → A` when that improves the
    scene. Backend already permits consecutive-same-speaker
    turns (`starters.py:3195-3359` has no alternation
    check); this arc preserves that latitude for AI mode
    too. Manual mode's visual add-a-line flow is not an
    alternation contract — it never was.

15. **No fixed turn count.** Turn count emerges from
    target duration + pacing (see §Duration). Any
    reasoning that involves "the operator asked for N
    turns" is a bug — the operator asks for a duration
    and a topic. The pacing table is soft guidance;
    hard bounds are conservative.

---

## Product job

Given:
- two persistent Character OS Teammates in the same workspace
- their scoped knowledge (workspace-shared + per-teammate)
- their Character Voice + Brand Voice settings
- a one-sentence operator topic
- an approximate target duration
- optional pinned opener

Character OS can generate a short episode where:
- each Teammate remains recognizably themselves
- they genuinely react to one another
- each character's factual claims stay grounded in that
  character's scoped knowledge
- their established relationship (if any) surfaces naturally
- the operator does not have to write dialogue manually

Manual dialogue authoring remains untouched for operators
who want line-by-line control.

---

## Non-purpose (explicit)

- **NOT a new render pipeline.** The existing `dialogue_scene`
  starter is untouched. AI Topic writes normalized lines and
  hands off.
- **NOT a Runway provider change.** No new endpoints, no
  changed model routing, no changed billing shape.
- **NOT a talking-head calibration change.** `15 cps`,
  `0.90 multiplier`, `±20%` all preserved.
- **NOT a Character Voice schema change.** All Teammate fields
  are reused as-is.
- **NOT an N > 2 AI cast slice.** v1 is 2-character AI mode
  only; the backend interface accepts `Sequence[Teammate]`
  so future N-cast doesn't require redesign.
- **NOT a semantic K6.4 v2.** Existing verifier reused
  unchanged.
- **NOT an operator-editable AI draft.** Draft → validate →
  render is v1. DialogueResult serializes cleanly enough
  that a future draft-into-editor flow lands without
  redesign; not built now.
- **NOT an image-backed dialogue outro card.** Primitive
  supports it (SESSION 255 shipped `outro_image_asset_id`
  for talking_head recipes), but wiring to `dialogue_scene`
  is out of scope.
- **NOT a fix for the `voice_avoid_phrases` LLM injection
  gap** surfaced during audit. That's a Character Voice
  latent bug affecting single-character K6 today; logged
  as high-priority carry-forward. Patch/Rivet dialogue is
  expected to be a useful surface for exposing it.

---

## Data model

**No new columns. No migration required.**

Everything AI Topic mode needs already exists:
- `Composition.params` (JSON) — carries `dialogue_mode`,
  `topic`, `target_duration_seconds`, `primary_spokesperson_id`,
  `secondary_spokesperson_id`, `use_knowledge`, `verifier_mode`,
  `opener`, `name`, `mock_mode`.
- `Composition.synthesized_brief` (TEXT) — carries the
  human-readable rendering of the AI-produced dialogue
  (already used by knowledge-grounded talking_head).
- `Composition.rejected_synthesis` (TEXT) — carries the
  raw LLM JSON when validation rejects (already used by
  K6.4 rejection path).
- `Composition.verification_status` / `verification_warnings`
  — reused for K6.4 per-turn verification aggregation.
- `Composition.writing_contract_version` — stamped `2` on
  all newly-created compositions once the contract bumps.
- `Composition.knowledge_chunk_ids` (JSON) — union of
  `patch_chunks + rivet_chunks` IDs when knowledge is on
  (mirrors talking_head aggregation).

Backend interface signature:

```python
def synthesize_dialogue(
    *,
    workspace,
    cast: Sequence[Teammate],   # v1 caller passes 2; interface
                                # accepts N so future expansion
                                # doesn't churn signatures
    topic: str,
    target_duration_seconds: int,
    opener: str | None = None,
    use_knowledge: bool = True,
    verifier_mode: str = "warn",
    mock_mode: bool = False,
) -> DialogueResult: ...
```

`DialogueResult` (dataclass) carries:

```python
@dataclass
class DialogueTurn:
    speaker_teammate_id: UUID
    speaker_name: str            # for logs / analytics
    text: str
    verification_warnings: list[dict]  # per-turn K6.4 output
    verification_status: str    # "supported" | "warned" | "rejected"

@dataclass
class DialogueResult:
    turns: list[DialogueTurn]
    chunk_ids: list[str]         # union across both characters
    writing_contract_version: int
    overall_verification_status: str
    total_estimated_seconds: float
    total_estimated_chars: int
    raw_llm_json: str            # persisted on rejection
```

---

## Prompt architecture

### 5-section K6 shape, extended for two characters

The single-character K6 prompt today (per
`script_synthesis.py:502-534`) is:

```
§1 FACTUAL BASIS
§2 CHARACTER VOICE
§3 BRAND VOICE
§4 WRITING CONTRACT
§5 TASK
```

The dialogue variant lifts §2 and §3 into per-character
blocks and lifts §1 into per-character labeled blocks.
§4 gains the new `dialogue_scene` shape. §5 carries the
topic + duration + opener + cast list.

Layout (structure only; not final prose):

```
=== SECTION 1 — FACTUAL BASIS ===
[intro line about scope]

--- SHARED WORKSPACE KNOWLEDGE (both characters can use) ---
[chunks visible via both retrieve_for_teammate calls]

--- PATCH'S SCOPED KNOWLEDGE (only Patch may claim these) ---
[Patch's private chunks + business_brief / who_you_help /
 what_you_sell / never_say / desired_feeling — factual only]

--- RIVET'S SCOPED KNOWLEDGE (only Rivet may claim these) ---
[Rivet's private chunks + identity fields — factual only]

=== SECTION 2 — CHARACTER VOICES ===

--- CHARACTER A — PATCH ---
[current single-character §2 block, unchanged shape]

--- CHARACTER B — RIVET ---
[same shape, Rivet's values]

=== SECTION 3 — BRAND VOICES ===

--- PATCH'S BRAND CONSTRAINTS ---
[always_emphasize, never_say, desired_feeling — apply
 only to Patch's own lines]

--- RIVET'S BRAND CONSTRAINTS ---
[Rivet's; apply only to Rivet's own lines]

=== SECTION 4 — WRITING CONTRACT ===
[WritingContract.for_shape("dialogue_scene") text — the
 dialogue invariants block]

=== SECTION 5 — TASK ===
Topic: {topic}
Cast (use ONLY these speaker_alias values):
  - patch (Patch, the experimenting beaver inventor)
  - rivet (Rivet, Patch's robot helper in the lab)
Target duration: approximately {target_duration_seconds} s.
Turn count guidance: {n_min}–{n_max} turns (a pacing
suggestion, not a hard limit; short reactions welcome).
[if opener supplied:]
REQUIRED first turn (belongs to patch): {opener!r}

Return JSON matching this shape:
{
  "turns": [
    {"line_index": 0, "speaker_alias": "patch|rivet",
     "text": "..."},
    ...
  ]
}
```

### Prompt shape rationale

- **§1 splits three ways** (shared / A-only / B-only) so the
  LLM can construct interaction ("Rivet, you know I'm working
  on the pressure valve") without smuggling A's private
  knowledge into B's factual claims. K6.4 verification runs
  per-turn against the speaker's corpus and enforces the
  actual isolation post-generation.
- **§2 and §3 are cleanly labeled per-character** so the
  LLM can distinguish "how Patch sounds" from "how Rivet
  sounds" without a blended voice.
- **§4 carries the dialogue-specific invariants** (see
  Writing Contract v2 below).
- **§5 is the operator input** plus the cast alias mapping
  the LLM must use in its JSON output.

---

## Structured output schema

OpenAI Responses API call:

```python
response = client.responses.create(
    model="gpt-5",
    input=f"{system}\n\nUser: {user}",
    max_output_tokens=4000,  # dialogue may run ~2× longer
                             # than single-character
    reasoning={"effort": "low"},
    response_format={"type": "json_object"},
)
```

Response schema (validated after parse):

```json
{
  "turns": [
    {"line_index": 0, "speaker_alias": "patch", "text": "…"},
    {"line_index": 1, "speaker_alias": "rivet", "text": "…"},
    {"line_index": 2, "speaker_alias": "patch", "text": "…"}
  ]
}
```

No LLM-emitted duration / confidence / metadata — Character
OS computes those itself.

### Post-parse validation (mandatory, in order)

1. `turns` is a non-empty list.
2. Each turn has `line_index` (int), `speaker_alias` (str),
   `text` (str).
3. `line_index` sequence is `0, 1, 2, …` — no gaps, no
   duplicates, no out-of-order.
4. Each `text.strip()` is non-empty. Short is OK.
5. Each `speaker_alias` (case-insensitive) resolves to a
   Teammate in the approved cast. Unknown alias → reject.
6. Total turn count in `[min_turns, max_turns]` for the
   target duration band (see §Duration below). Outside →
   one bounded corrective resynth.
7. Each turn's `len(text) ≤ AVATAR_SPEECH_SAFE_MAX_CHARS`
   (currently 1900, from `duration_contract.py`). Exceeds
   → reject; provider will 400 anyway.
8. Aggregate `sum(len(text) for turns) / 15 cps` within
   ±20% of target duration. Outside → one bounded
   corrective resynth.
9. If opener supplied: turn 0's speaker resolves to primary,
   and text preserves opener per existing K6 opener
   semantics. Otherwise → reject (opener is a hard
   constraint).

### On rejection

- Persist raw LLM JSON (truncated at 4 KB) to
  `Composition.rejected_synthesis`.
- Stamp `verification_status = "rejected"` + `error_message`
  with the specific reason.
- Stamp `writing_contract_version = 2` (the contract WAS
  applied; the LLM output failed it).
- Do NOT create any CompositionSteps. Do NOT fire any
  Runway calls.
- Return `DialogueResult(...)` with empty turns so the
  view layer surfaces a clean 4xx to the SPA.

---

## Duration contract wrapper

Aggregate model in v1. Per-character delivery calibration
is deferred (each Teammate has voice/energy variations —
future recalibration lives here without touching talking-head).

Reuse from `duration_contract.py`:
- `_AVATAR_SPEECH_CHARS_PER_SECOND = 15` (unchanged)
- `K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER = 0.90` (unchanged)
- `AVATAR_SPEECH_SAFE_MAX_CHARS = 1900` (per-turn cap)
- `±20%` acceptance band (aggregate)

Turn count guidance (pacing, NOT cost):

| Target duration | Suggested turns | Hard min | Hard max |
|---|---|---|---|
| 30 s | 4–6 | 2 | 12 |
| 60 s | 6–9 | 2 | 18 |
| 90 s | 8–12 | 2 | 24 |
| 120 s | 10–15 | 2 | 30 |

Hard bounds are conservative; suggested range guides the
writer. Rejection outside hard bounds triggers one
bounded corrective resynth ("scene ran short — expand
with more back-and-forth" / "too many turns — consolidate
into fewer, more substantial exchanges").

Cost implication (informational): at $0.02/turn, a 30-turn
dialogue costs $0.60; a 6-turn dialogue costs $0.12. Both
are trivial. Turn count constraints exist for pacing,
seams, and watchability — not COGS.

---

## Operator UX

### Current operator UX (manual — shipped today, unchanged)

Rendered by the metadata-driven form at
`web/src/routes/recipes/$kind.tsx`:

```
Dialogue scene (multi-character)

Primary spokesperson (owner / narrator)
  [Patch ▾]

Dialogue lines
Ordered list of turns. Each turn: pick a spokesperson + write
what they say.

  Line 1
    [Patch ▾]
    [What this character says…                          ]

  Line 2
    [Rivet ▾]
    [What this character says…                          ]

  Line 3
    [Patch ▾]
    [What this character says…                          ]

  Line 4
    [Rivet ▾]
    [What this character says…                          ]

  Line 5
    [Patch ▾]
    [What this character says…                          ]

  [+ Add line]

Brand outro card (optional)
  [                                                     ]

Composition name (optional)
  [                                                     ]
```

The `DialogueLinesEditor` (`web/src/routes/recipes/$kind.tsx:826`)
renders the add/remove list. Arbitrary N cast, N turns.
Consecutive same-speaker turns already legal. This entire
workflow **stays exactly as-is** — no visual, behavioral, or
schema change.

### Target operator UX (AI Topic — new)

Rendered by the SAME form component, keyed on the new
`dialogue_mode` field:

```
Dialogue scene (multi-character)

Dialogue mode
  ( ) I'll write each line       ← default (manual)
  (•) Character OS writes it     ← selecting flips visible fields

Primary character
  [Patch ▾]

Second character
  [Rivet ▾]

Topic
  [ Patch tries to explain why he built Rivet to improve the ]
  [ workshop, while Rivet points out that he spends most of  ]
  [ his time fixing Patch's experiments.                     ]

Target duration
  [ ~60 seconds ▾ ]     (30 / 60 / 90 / 120)

Use workspace knowledge
  [x] enabled

K6.4 verifier mode
  [ Warn ▾ ]            (Warn / Strict / Off)

Opening line (optional)
  [                                                          ]
  Primary character owns the pinned opener.

Brand outro card (optional)
  [                                                          ]

Composition name (optional)
  [                                                          ]
```

**The manual `DialogueLinesEditor` is hidden entirely in AI
mode.** The operator does not create blank lines to fill —
Character OS produces the whole conversation from the topic.

Operator presses the existing create/run action. The
composition submits, `_dialogue_resolver` sees
`dialogue_mode == "ai_topic"`, calls `synthesize_dialogue()`,
hydrates `params["lines"]` from the returned turns, and hands
off to the existing `starters.dialogue_scene` — same starter,
same steps, same render graph.

### The operator does NOT decide

In AI Topic mode, Character OS owns:
- **Number of turns.** Emerges from target duration + pacing
  (see §Duration).
- **Speaker alternation.** Not forced. `Patch → Rivet → Rivet
  → Patch → Rivet → Patch` is a legal and often better shape
  than strict alternation. Consecutive same-speaker turns are
  already legal in the backend
  (`starters.py:3195-3359` — no alternation check) and
  remain legal here.
- **Turn lengths.** Short reactions (`"Define 'still.'"`)
  interleaved with longer explanatory turns. No per-turn
  minimum. No forced padding.
- **Exact wording.** The topic + Character Voice + scoped
  knowledge define the space; the writer picks the words.
- **Where reactions and punchlines fall.** Dialogue synthesis
  responsibility.

### Manual mode remains the escape hatch

Operators who want line-by-line control keep the current
editor with zero change. Any operator can flip
`dialogue_mode` back to "I'll write each line" at any point
before submitting. The two modes are equal citizens; AI
Topic is not the "recommended" default. Default is
`manual`.

### Deferred (out of v1)

A future slice may add: `Generate AI dialogue draft` →
populate `DialogueLinesEditor` → operator edits → render.
That's a UX layer on top of `DialogueResult`, not an
architectural change — the module ships with cleanly
serializable turns for exactly this purpose. Not built
now.

## Two-character v1 UI implementation

Same recipe row, new `dialogue_mode` field, conditional
field visibility.

### Recipe fields (proposed additions to `dialogue_scene`)

```python
RecipeField(
    name="dialogue_mode", type="select",
    label="How should Character OS build this?",
    required=False, default="manual",
    choices=(
        {"value": "manual",   "label": "I'll write each line"},
        {"value": "ai_topic", "label": "Character OS writes it from a topic"},
    ),
),
RecipeField(
    name="secondary_spokesperson_id", type="spokesperson_picker",
    label="Second character",
    required=False,  # required only when dialogue_mode="ai_topic";
                     # backend enforces the conditional required
),
RecipeField(
    name="topic", type="textarea",
    label="What's the scene about?",
    required=False, max_chars=800,
    help_text="Character OS writes both sides of the "
              "conversation from this. Manual mode ignores it.",
),
RecipeField(
    name="target_duration_seconds", type="select",
    label="Target duration",
    required=False, default=60,
    choices=(
        {"value": 30,  "label": "~30 seconds"},
        {"value": 60,  "label": "~60 seconds"},
        {"value": 90,  "label": "~90 seconds"},
        {"value": 120, "label": "~120 seconds"},
    ),
),
# Reused shared fields:
_OPENER_FIELD,          # optional pinned first line for primary
_VERIFIER_MODE_FIELD,   # default "warn"
# use_knowledge boolean (existing field on talking_head recipes)
```

### SPA field visibility

Metadata-driven renderer at `web/src/routes/recipes/$kind.tsx`
gets a per-field visibility rule keyed on `dialogue_mode`:

- `dialogue_mode == "manual"` (default): show current fields
  (`primary_spokesperson_id`, `lines`, `outro_text`, `name`,
  `mock_mode`). Hide `secondary_spokesperson_id`, `topic`,
  `target_duration_seconds`, `opener`, `verifier_mode`,
  `use_knowledge`.
- `dialogue_mode == "ai_topic"`: hide `lines`; show
  `primary_spokesperson_id`, `secondary_spokesperson_id`,
  `topic`, `target_duration_seconds`, `use_knowledge`,
  `verifier_mode`, `opener`, `outro_text`, `name`, `mock_mode`.

Both modes share: primary spokesperson, outro, name, mock mode.

The `use_knowledge` checkbox mode-toggle precedent already
ships on talking_head (`recipes.py:381-391`,
`$kind.tsx:334`) — same JSX pattern applies here.

### Cast size — N > 2 preserved for manual

Manual mode still supports arbitrary N via the existing
`DialogueLinesEditor`. AI Topic mode ships v1 as 2-cast
only. The backend `synthesize_dialogue` signature takes
`Sequence[Teammate]` (not a pair) so future N-cast AI
mode is a prompt + validation change, not a schema or
signature change.

---

## Slice breakdown

Suggested slice ordering — each shippable, testable,
committable independently.

### AI-D1 — Writing Contract v2 + shape addition

Files:
- `character_os/writing_contract.py` — add
  `_dialogue_scene_contract()`, extend `for_shape()`, bump
  `WRITING_CONTRACT_VERSION = 2`.
- `apps/compositions/tests/test_writing_contract.py` —
  assert `for_shape("dialogue_scene")` returns the new
  block; version stamp on all shapes is `2`; standalone /
  long_form contract text is unchanged (only version).

No migration; no runtime behavior change beyond the version
stamp on new compositions.

### AI-D2 — `dialogue_synthesis.py` module

Files:
- `character_os/dialogue_synthesis.py` — NEW.
  `synthesize_dialogue(cast, topic, target_duration_seconds,
  opener=None, use_knowledge=True, verifier_mode="warn",
  mock_mode=False) → DialogueResult`.
- Reuses `retrieve_for_teammate()`, `build_factual_corpus()`,
  `build_allowed_vocabulary()`, `run_verifier()`, and
  `WritingContract.for_shape("dialogue_scene")` verbatim.
- Prompt-building helpers (per-character §2/§3 block
  builders) may be extracted from `script_synthesis.py` if
  the refactor is <20 lines; otherwise inlined in the new
  module.
- OpenAI Responses API call with
  `response_format={"type": "json_object"}`.
- Post-parse validation + one bounded corrective resynth.
- Per-turn K6.4 verification against speaker's corpus.

Tests (mocked OpenAI):
- Structured output parsed + validated.
- Rejection paths: unknown alias, gapped `line_index`,
  empty text, per-turn cap, aggregate duration, invented
  third speaker, opener not preserved.
- Corrective resynth fires exactly once on aggregate
  duration failure; second failure rejects.
- Per-turn verifier invoked with correct corpus/vocab per
  speaker.
- Cross-workspace cast rejected before any LLM call.

### AI-D3 — Recipe wiring + resolver branch

Files:
- `apps/compositions/recipes.py` — extend `dialogue_scene`
  row with `dialogue_mode`, `secondary_spokesperson_id`,
  `topic`, `target_duration_seconds`, `use_knowledge`,
  `verifier_mode`, `opener`. `_dialogue_resolver` gains
  an early branch: `if dialogue_mode == "ai_topic":
  call synthesize_dialogue → hydrate params["lines"] →
  fall through to existing manual-path resolver`.
- Conditional required validation: `secondary_spokesperson_id`
  + `topic` required when `dialogue_mode == "ai_topic"`;
  ignored in manual.
- Cross-workspace cast rejection preserved.

Tests:
- Manual path unchanged (regression).
- AI path with mocked `synthesize_dialogue` produces
  correct `lines` shape + starter creates matching steps.
- Missing required AI fields rejected pre-synth.
- `dialogue_mode="ai_topic"` + rejected synthesis leaves
  no CompositionSteps + persists rejection metadata.

### AI-D4 — SPA field visibility

Files:
- `web/src/routes/recipes/$kind.tsx` — visibility rule
  keyed on `dialogue_mode`. Hide/show branches for each
  field. Same JSX pattern as talking_head's `use_knowledge`
  mode toggle.
- `web/src/lib/api/recipes.ts` — no shape change; zod
  parses new fields off `/api/recipes/`.

Tests (vitest):
- Visibility toggles correctly on `dialogue_mode` change.
- `lines` editor hidden in AI mode.
- AI-mode fields hidden in manual mode.
- Cast picker shows only workspace Teammates (existing
  behavior).

### AI-D5 — Real-Runway dogfood (Patch + Rivet)

Not code — operator-driven validation using the topic and
acceptance criteria in the "First real dogfood" section
below. Findings logged as calibration events per project
convention.

### AI-D6 — INVENTORY regen + handoff

Regenerate `docs/CHARACTER_OS_INVENTORY.md` after AI-D3
lands (new field types in recipe metadata). Handoff at
`docs/handoffs/SESSION_NNN_DIALOGUE_AI_TOPIC.md`.

---

## First real dogfood

Patch + Rivet only. **No substitutions.**

### Session 1 — 60 seconds

Topic: *"Patch tries to explain why he built Rivet to
improve the workshop, while Rivet points out that he spends
most of his time fixing Patch's experiments."*

Settings:
- `dialogue_mode = "ai_topic"`
- `primary_spokesperson = Patch`
- `secondary_spokesperson = Rivet`
- `target_duration_seconds = 60`
- `use_knowledge = True`
- `verifier_mode = "warn"`
- `opener` = (none for first pass)
- `outro_text` = (short brand card)
- Real mode (not mock).

Expected shape: 6–9 turns, ~60 s total, ~$0.12–$0.18
provider spend.

### Acceptance criteria

1. **Character identity.** Hide the labels; Patch/Rivet
   should still be distinguishable from wording alone.
2. **Genuine interaction.** Turns respond to previous
   turns instead of alternating speeches.
3. **Relationship.** Their established
   Patch-created-Rivet relationship appears naturally
   where relevant, without awkward narration
   ("As you know, Patch built me…").
4. **Knowledge isolation.** No cross-character factual
   leakage. Patch doesn't claim facts that live only in
   Rivet's scoped corpus, and vice versa. K6.4 warnings
   panel is empty or explainable.
5. **Pacing.** Mix of short/medium/long turns feels
   conversational. Not every turn ~90 chars; not every
   turn a monologue.
6. **Humor.** If funny, humor comes from their
   relationship/POVs rather than generic joke insertion.
7. **Render quality.** Hard cuts / seams are watchable.
   No jarring audio glitches at concat boundaries.
8. **Cost.** Provider-reported actual should be
   approximately `n_turns × 2 Runway credits` +
   negligible local concat + outro. Verify by checking
   `Composition.cost_actual_micros` post-render.
9. **Gestalt.** Feels like a small episode, not an
   AI-generated FAQ.

If any of 1–5 fails, calibrate the prompt / contract
before running Session 2. If 6–8 fails, calibrate more
narrowly (audio codec at concat / outro overlay /
per-render cost telemetry).

### Session 2 — 90 seconds (only if Session 1 passes)

Same or new topic. Same cast. Same acceptance criteria
scaled to ~8–12 turns.

### Session 3+ — cast swap sanity

Same topic, different pair of Teammates. Dialogue should
be **recognizably different** — different characters
producing different content from the same topic +
corpus. This is the load-bearing generalization test.

---

## Follow-up items (post-slice)

Ordered by priority. None block AI-D1.

1. **`voice_avoid_phrases` LLM injection gap.** Pre-existing
   Character Voice bug: the field feeds K6.4 vocabulary
   check but is not rendered into the LLM prompt as an
   anti-register constraint. `writing_contract.py:313-336`
   defines `merged_avoid_phrases()` but no active callsite.
   Patch/Rivet dialogue is expected to expose register
   failures. Fix is small (add one paragraph to §2 in
   `script_synthesis.py`) but orthogonal — do NOT bundle
   into this slice.
2. **N > 2 AI cast.** Prompt + validation extension only;
   `Sequence[Teammate]` signature already accommodates.
3. **AI draft → editor → render flow.** DialogueResult
   serializes cleanly; UI slice to route into
   `DialogueLinesEditor` for operator edit.
4. **Per-character delivery calibration.** Some
   Teammates speak faster/slower than others.
   `_AVATAR_SPEECH_CHARS_PER_SECOND` is a workspace
   constant today; may become per-Teammate.
5. **Image-backed dialogue outro card.**
   `add_intro_outro` primitive supports it; wiring to
   dialogue_scene is a recipe-field + resolver change.
6. **Opt other Runway primitives into provider-cost
   truth** (visual_clip, extend_visual_clip, style_remix).
   Plumbing landed SESSION 257; opt-in is per-primitive.
7. **Historical `cost_actual_micros` inflation.**
   Pre-SESSION 257 rows are estimator-derived; decide
   separately whether analytics needs a
   cutoff/provenance rule.

---

## Change log

- **SESSION 257 (2026-08-16)** — scope-locked. Cost model
  authoritative (SESSION 257 `46f5efd`: 2 credits =
  $0.02/turn flat). Turn count is a pacing lever, not a
  COGS lever. Patch + Rivet dogfood cast reaffirmed.
- **SESSION 257 amendment (2026-08-16)** — added §Operator
  UX with current-manual + target-AI mockups. Contract
  rules 13/14/15 added to make AI-hides-manual-editor,
  no-forced-alternation, and no-fixed-turn-count
  load-bearing rather than prose. Manual mode remains the
  escape hatch; deferred draft-into-editor flow explicitly
  named. No architectural change from the pre-amendment
  lock — this is UX clarification and rule elevation.

---
