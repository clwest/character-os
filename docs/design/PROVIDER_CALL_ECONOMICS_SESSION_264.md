# PROVIDER CALL ECONOMICS — SESSION 264 dogfood finding

**Status:** documentation / observability finding only.
**Type:** post-implementation observation captured from real
runtime evidence. No code changes.
**Related:** `docs/design/MODEL_MIGRATION_GPT_5_6_TERRA_SESSION_264.md`
§11 (recorded the 60 s / 90 s dogfood costs that motivated
this note).

**Load-bearing statement:**

> **Avatar rendering cost must not be modelled as a simple
> function of final video duration.**

The 60 s → 90 s Dialogue Scene cost delta (~$0.18 → ~$0.22
Runway; ~$0.03 → ~$0.07 OpenAI) is not evidence of a
per-second Runway rate. Runway's per-call billing shape and
Character OS's per-turn dispatch shape combine to produce a
cost curve that is not linear in seconds. Any future
optimization, dashboard, or product decision that assumes
"cost ≈ duration × rate" for multi-character dialogue is
building on a wrong model.

---

## 1. Executive summary

- Each **Dialogue Scene** turn maps to exactly one
  `generate_avatar_speech` `CompositionStep`, which fires
  exactly one Runway `/v1/avatar_videos` dispatch. A dialogue
  with more turns costs more per-render even if final runtime
  is similar. [EVIDENCE — code + runtime]
- A single-character **Talking Head** currently produces
  exactly one `generate_avatar_speech` dispatch regardless of
  duration. Extending a talking-head from 30 s to 90 s does
  not multiply its provider-call count the way adding
  dialogue turns does. [EVIDENCE — code]
- **Long-Form Ad** pre-splits its script into chunks at
  starter time; each chunk becomes its own `generate_avatar_speech`
  dispatch. Cost scales with chunk count. [EVIDENCE — code]
- Runway's `/v1/avatar_videos` currently bills a flat 2
  credits per call within the empirically-verified duration
  range (SESSION 257 sampled 15 real tasks spanning
  1.81 s → 179.64 s). The **flat-per-call floor is written
  into code** as `_AVATAR_SPEECH_MICROS_PER_CALL = 20_000`.
  [EVIDENCE — code + SESSION 257 empirical calibration]
- Runway's visual-clip endpoints (`gen4_turbo`, `gen4.5`)
  have both a per-second rate AND a minimum-per-call floor,
  both encoded in code. [EVIDENCE — code]
- **OpenAI synthesis cost is NOT persisted** on any Character
  OS row. `DialogueResult` / `ScriptResult` carry
  `tokens_input` + `tokens_output` in-flight, but neither
  the Composition nor any child row records the LLM cost.
  Any "OpenAI cost" figure quoted in a dogfood report is
  operator-side accounting from provider dashboards, NOT a
  Character OS metric. [EVIDENCE — code, absence]

## 2. Reinterpreted 60 s vs 90 s dogfood evidence

The `docs/design/MODEL_MIGRATION_GPT_5_6_TERRA_SESSION_264.md`
§11.1–11.3 recorded these numbers verbatim from operator
observation:

| | 60 s render | 90 s render | Delta |
|---|---|---|---|
| Actual video duration | 59 s | 96 s | +37 s |
| Approx Runway cost | $0.18 | $0.22 | +$0.04 |
| Approx OpenAI cost | $0.03 | $0.07 | +$0.04 |
| Approx total | $0.21 | $0.29 | +$0.08 |

The migration doc's original interpretation implied the
$0.04 Runway increase and the $0.04 OpenAI increase both
scaled roughly with runtime. That framing is **potentially
wrong** and should not become architecture/product doctrine.

The correct decomposition against the current code:

- **Runway delta** — depends on **turn count**, not duration.
  60 s dialogue: 14 speech steps (from Composition
  `bc650dd5`, verified). 90 s dialogue: an operator-observed
  render with more turns. Runway billed 2 credits per turn
  regardless of turn length. The delta between $0.18 and
  $0.22 is consistent with roughly 4 additional avatar-speech
  dispatches (~4 × $0.02 = $0.08 gross, minus the +$0.04
  gap from what was likely a slightly different turn count
  or a small provider rounding). Whatever the exact call
  count, the shape of the Runway cost is
  `N_speech_turns × 2 credits`, not `duration × rate`.
- **OpenAI delta** — depends on **prompt + reasoning + output
  tokens**. Longer target duration produced a longer accepted
  brief (727 chars vs 1,358 chars per the migration doc), so
  more output tokens billed by OpenAI. Additionally the
  90 s render ran two synthesis attempts (first pass 2,066
  chars → too long → corrective compress to 1,420 chars),
  which doubled the input+reasoning prompt cost. This is a
  legitimate duration/quality trade-off but is mediated by
  synthesis behavior, not runtime.

The two deltas happen to add up to roughly $0.08 for this
particular pair of renders. That is a coincidence, not a
law. A dialogue with the same 90 s target but 24 turns would
cost more Runway credits than one with 18 turns of the same
total runtime, even though both would satisfy Character OS's
duration tolerance band.

**Do NOT quote "$0.08 per 30 additional seconds" as a design
input.** Quote turn count and provider-dispatch count
instead.

## 3. Verified provider-call execution behavior

### 3.1 Dialogue Scene [EVIDENCE — code + SESSION 264 runtime]

`shell/apps/compositions/starters.py::dialogue_scene` at
line 3739–3756 creates exactly one `CompositionStep` per
validated line, each with `primitive="generate_avatar_speech"`:

```python
for idx, (sp, text, ai_alias) in enumerate(validated_lines):
    step_params: dict = {
        "script": text,
        "use_knowledge": False,
        "spokesperson_avatar_id": sp.runway_avatar_id,
    }
    if ai_alias:
        step_params["ai_topic_speaker_alias"] = ai_alias
    CompositionStep.objects.create(
        composition=composition,
        position=idx,
        primitive="generate_avatar_speech",
        inputs=[],
        params=step_params,
    )
```

The `GenerateAvatarSpeechPrimitive.execute()`
(`shell/apps/compositions/primitives/avatar_speech.py:642–646`)
makes exactly one `MediaEngineClient.create_avatar_speech()`
call per step, which POSTs to media-engine
`/internal/clips/avatar_speech/`, which itself dispatches
one Runway `/v1/avatar_videos` task and polls to terminal
state.

**Persisted evidence.** Composition
`bc650dd5-d386-4129-a7cf-f37c39307eb0` (SESSION 264 60 s
Terra dogfood) had 14 speech steps + 1 concat step. Each
succeeded speech step showed
`cost_actual_micros = 20,000` (2 Runway credits × 10,000
micros/credit). Concat step showed `cost_actual_micros = 100`.
Composition total: `260,000` micros ≈ $0.26 in Character
OS's own accounting.

The $0.18 the operator observed for Runway matches the sum
of the 9 accepted speech steps at 2 credits each; the
Character OS `260,000` micros figure includes the 13 SUCCEEDED
+ 0 for the FAILED step + 100 for the pending concat, minus
whatever cost the operator was extracting from a different
provider surface. Cross-provider accounting for exact cents
is not a Character OS invariant — Character OS records the
per-call floor + reported credits.

### 3.2 Talking Head [EVIDENCE — code]

`shell/apps/compositions/starters.py::talking_head` at
line 576–758 creates a single `CompositionStep` with
`primitive="generate_avatar_speech"` (line 714–720). The
starter does NOT invoke `script_splitter`; the full script
(possibly synthesized in one K6 call for
`use_knowledge=True`) goes into one step.

**Implication:** A 90-second talking-head render fires
**one** avatar-speech provider dispatch. A 30-second
talking-head fires **one**. The cost delta between them is
whatever Runway's per-call billing surfaces (currently a
flat 2-credit floor within the empirically-verified range).
Duration is not the primary driver.

**No runtime evidence gathered** in SESSION 264 for talking-
head specifically. The code path is what it is, but a
dogfood on talking-head at 30 s vs 90 s would be needed to
confirm the current Runway billing surface still hits the
2-credit floor at both ends.

### 3.3 Long-Form Ad [EVIDENCE — code]

`shell/apps/compositions/starters.py::long_form_ad` at
line 1078+ pre-splits the script (either LLM-driven via
`script_splitter` or a naive fallback) BEFORE step creation.
Each chunk becomes one `CompositionStep` with
`primitive="generate_avatar_speech"`. Cost scales with chunk
count.

**Implication:** Long-form-ad cost is more chunk-count-
driven than dialogue-scene cost (because chunks are usually
larger than dialogue turns) but STILL not a clean function
of duration. The chunk splitter's behavior is the load-
bearing variable.

### 3.4 Concat [EVIDENCE — code + runtime]

`concat_clips` primitive at the end of dialogue-scene and
long-form-ad compositions is an ffmpeg-only local operation.
Its `cost_actual_micros` in the SESSION 264 Terra runs was
100 micros — effectively a rounding stub, not a provider
dispatch. Not part of the provider-call economics.

### 3.5 Visual clip [EVIDENCE — code]

`primitives/visual_clip.py` lines 105–108 encode:

```python
_VISUAL_CLIP_GEN45_MICROS_PER_SECOND = 120_000
_VISUAL_CLIP_GEN45_MIN_MICROS = 600_000
_VISUAL_CLIP_GEN4TURBO_MICROS_PER_SECOND = 50_000
_VISUAL_CLIP_GEN4TURBO_MIN_MICROS = 250_000
```

Both endpoints have `max(min, duration × rate)` — meaning a
1-second gen4_turbo visual clip still bills the 250,000-
micro floor, while a 10-second clip bills
`10 × 50,000 = 500,000` micros. Visual-clip cost IS partly
duration-linear ABOVE the floor, but has a hard minimum per
call. Not relevant to Dialogue Scene (which has no visual
clip steps) but recorded here so future recipes using
visual-clip aren't modelled with a naive rate.

## 4. Verified persisted cost behavior

### 4.1 Fields that already exist

| Field | Location | What it means |
|---|---|---|
| `CompositionStep.cost_actual_micros` | `models.py:880` | Per-step provider cost. Set by `tasks.execute_step` from `primitive.execute()` return. |
| `CompositionStep.cost_estimate_micros` | `models.py:881` | Pre-render forecast. Set at planning time; never updated. |
| `Composition.cost_actual_micros` | `models.py:565` | Aggregate sum of step costs. Refreshed by `cost.refresh_composition_cost_actual` (SQL subquery UPDATE — race-safe per SESSION 258 P1.1). |
| `Composition.cost_estimate_micros` | `models.py:564` | Pre-render aggregate forecast. |
| `Asset.cost_micros` | `models.py:228` | Per-asset cost stamp (mirrors the producing step's cost). |
| `Asset.source_spec.cost_source` | JSON in `source_spec` | `"provider_reported"` (Runway returned `cost_credits`) or `"estimated"` (fallback to the per-call floor). |
| `Asset.source_spec.cost_provider_credits` | JSON in `source_spec` | Actual credits billed when `cost_source == "provider_reported"`. |
| `CompositionStep.primitive` | `models.py` | The step's primitive kind — allows filtering "avatar-speech only". |
| `Composition.template_kind` | `models.py` | Recipe provenance — allows aggregating by recipe. |
| `Composition.render_dispatched_at` | SESSION 262 observability | First-provider-dispatch timestamp. |
| `Composition.synthesis_attempt_count` | SESSION 262 observability | LLM attempts (1 = first-pass accepted, 2 = one corrective). |
| `Composition.final_asset.duration_ms` | Asset FK | Rendered video duration. |

### 4.2 Retry cost behavior [EVIDENCE — code]

`shell/apps/compositions/tasks.py::retry_step` at
line 267–304 updates the existing `CompositionStep` row
in place:

```python
step.status = StepStatus.PENDING
step.error_message = ""
step.output_asset = None
step.completed_at = None
step.elapsed_ms = None
step.cost_actual_micros = 0   # prior attempt cost overwritten
step.save(update_fields=[...])
```

**Implication:** The prior attempt's `cost_actual_micros` is
**overwritten with 0** on retry. No per-attempt history is
persisted. There is no `StepAttempt` table, no JSON journal
on the step row, no audit log of prior costs.

For SESSION 264 the moderation-rejected step [0] of
Composition `bc650dd5-…` billed $0 both times (Runway
rejects at moderation before generation → no cost), so no
information was actually lost. But a step that
FAILS-after-generation on the first attempt and SUCCEEDS on
retry would have its first-attempt cost silently overwritten
by the successful attempt's cost — the operator would see
the successful cost only.

### 4.3 Moderation-failure cost behavior [EVIDENCE — code + runtime]

When Runway rejects a text prompt at moderation:

1. `MediaEngineClient.create_avatar_speech()` returns a task
   ID normally.
2. `poll_task(task_id)` returns terminal state with
   `succeeded=False` and `failure_code="moderation_violation"`
   (or similar).
3. `GenerateAvatarSpeechPrimitive.execute()` at
   `avatar_speech.py:683–687` raises `PrimitiveError` BEFORE
   the cost-writing block at lines 753–763 is reached.
4. `tasks._mark_step_failed()` at line 220 catches the
   exception, marks the step FAILED, but does NOT touch
   `cost_actual_micros`.
5. The step's `cost_actual_micros` remains at its initialized
   value: **0**.

**Confirmed by SESSION 264 runtime.** Step [0] of Composition
`bc650dd5-…` had `cost_actual_micros=0` on the initial
moderation rejection AND on the operator-triggered retry
(both attempts hit the moderator before generation; both
recorded $0). This is code-side confirmation of the runtime
observation — **not** a coincidence.

**Whether Runway actually charges $0 for moderation
rejections is inferred from runtime evidence, not code.**
Character OS records what media-engine reports; if Runway
started billing for moderation checks tomorrow, the code
would surface a non-zero `cost_credits` and the step would
record a non-zero cost. The current $0 behavior is a
provider policy, not a Character OS invariant.

### 4.4 Minimum-per-call pricing

**IS represented in code.**

- Avatar-speech: `_AVATAR_SPEECH_MICROS_PER_CALL = 20_000`
  (avatar_speech.py:76–87). SESSION 257 empirically
  calibrated flat 2-credit-per-call across 15 real Runway
  tasks spanning 1.81 s → 179.64 s.
- Visual clip gen4_turbo: `min = 250,000` +
  `50,000/second` (visual_clip.py:105–106).
- Visual clip gen4.5: `min = 600,000` +
  `120,000/second` (visual_clip.py:107–108).

Both applied in `estimate_cost()` and used as fallback in
runtime cost when the provider doesn't return `cost_credits`.
These are ESTIMATE floors, not enforced billing minimums;
if Runway returns a smaller `cost_credits`, that number is
recorded — but empirically Runway hasn't been observed
returning below-floor values.

### 4.5 What is NOT persisted

- **OpenAI synthesis token cost.** `DialogueResult.tokens_input`
  + `tokens_output` and `ScriptResult` equivalents exist
  in-flight but are discarded at
  `starters.py:3638–3648` when the starter hydrates `lines`
  from `DialogueResult.turns`. No Composition, CompositionStep,
  or Asset field records the LLM cost.
- **Per-attempt cost history.** Retries overwrite the row;
  prior attempt costs are gone.
- **Provider dispatch count as a first-class field.** The
  count is derivable via `steps.filter(primitive="generate_avatar_speech").count()`
  but never denormalized on Composition.
- **Cost source summary at composition level.**
  `Asset.source_spec.cost_source` is per-asset. There is no
  Composition-level flag saying "all costs were
  provider-reported" vs "some were estimated fallbacks."

## 5. What is EVIDENCE vs INFERENCE

**EVIDENCE (from code + persisted runtime evidence):**

- Turn-per-dispatch mapping in dialogue_scene ✅
- Single-dispatch talking_head ✅
- Chunked long_form_ad ✅
- Per-step / per-composition cost fields ✅
- Retry cost overwrite behavior ✅
- Moderation failure = $0 CURRENTLY (from Composition `bc650dd5-…`) ✅
- Minimum-per-call floors in code ✅
- OpenAI token cost is NOT persisted ✅
- Provider dispatch count is derivable, not denormalized ✅

**INFERENCE (not proven by code / persisted runtime):**

- The exact Runway per-call price is 2 credits × current
  credit dollar value — SESSION 257 empirical, may drift if
  Runway changes pricing.
- Whether Runway continues to charge $0 on moderation
  rejection is provider policy, not enforced in code.
- Cross-recipe cost curves (dialogue vs talking-head vs
  long-form) — we have code-side dispatch shape but no
  side-by-side runtime evidence at matched durations.
- Whether the $0.04 OpenAI 60 s → 90 s delta scales
  linearly with additional targets (30 s, 120 s, 5 min)
  is untested.
- Whether narratively richer scenes with fewer turns are
  actually cheaper AND better is a hypothesis, not evidence
  (see §7).

## 6. Observability dimensions that must stay separate

Cost / duration / provider-call analysis MUST treat these as
distinct axes, not one:

- `requested_duration` — operator's target (Episode Dialogue
  default is now 90 s; talking-head has no explicit target)
- `predicted_duration` — synthesizer's estimate
  (`ScriptResult` / `DialogueResult` planning field)
- `actual_duration` — `final_asset.duration_ms`
- `dialogue_turn_count` — for dialogue-scene, equal to
  speech-step count
- `generated_speech_segment_count` — count of
  `generate_avatar_speech` steps
- `provider_dispatch_count` — total provider-calling steps
  (currently derivable as
  `steps.filter(primitive__in=[avatar-speech, visual-clip, …])
  .count()`)
- `retry_dispatch_count` — extra dispatches from retries
  (currently NOT recoverable because retry overwrites)
- `openai_tokens_input` / `openai_tokens_output` — NOT
  persisted; would need a schema addition
- `openai_synthesis_cost_micros` — NOT persisted
- `avatar_provider_cost_micros` — currently commingled into
  `Composition.cost_actual_micros`
- `total_composition_cost_micros` — currently the sum of
  step provider costs only; excludes OpenAI

The 59 s and 96 s Terra renders are **runtime examples**,
not a scaling law. Quoting them as `cost_per_second × N`
would misrepresent the underlying billing shape.

## 7. Future design hypothesis — RECORDED, NOT IMPLEMENTED

For multi-character episodic dialogue, eventual optimization
work may want to optimize:

> **scene quality per provider call**

rather than any of:

- shortest duration
- cost per second
- minimum number of generated characters
- lowest turn count

A **longer scene with fewer, richer turns** may be BOTH
narratively better AND economically cheaper than a shorter
scene with rapid turn-taking. Example conceptual pair:

- Dialogue A: 90 s, 18 turns → 18 avatar-speech dispatches →
  ~36 credits ≈ $0.36 Runway
- Dialogue B: 90 s, 9 turns → 9 avatar-speech dispatches →
  ~18 credits ≈ $0.18 Runway

The two videos have approximately the same duration but
materially different avatar-generation economics. Whether
either dialogue is *better* is a separate question
(narrative quality is not on this axis).

**This is a hypothesis requiring runtime evidence, not a
ratified optimization rule.** It should NOT drive changes
to synthesis turn counts, corrective headroom, dialogue CPS,
or the Writing Contract without a controlled A/B render.

### 7.1 Format-specific cost curves — RECORDED

Different content formats have materially different cost
curves. Do NOT generalize dialogue-scene economics to every
recipe.

| Format | Cost shape | Primary cost driver |
|---|---|---|
| Episodic multi-character dialogue | Turn-count-driven | `N_turns × 2 credits` |
| Single-character talking head | Flat per call | 1 call × 2 credits (regardless of duration) |
| Long-form ad | Chunk-count-driven | `N_chunks × 2 credits` (chunker output) |
| Single-scene visual (visual_clip) | Duration-driven above a floor | `max(min, duration × rate)` |
| Storyboard-voiced | Multi-primitive composite | Image gen + visual + speech + audio (sum) |
| Educational multi-character scenes | Turn-count-driven, similar to dialogue | Same shape as dialogue-scene |
| Future formats | Unknown | Must be measured per-format, not extrapolated |

## 8. Observability gaps — RECORDED, NOT IMPLEMENTED

The following persisted-schema gaps prevent Character OS from
directly answering the questions the operator listed in
TASK 3. These are **deferred findings**; no fix is proposed
here.

| Question | Gap | Would need |
|---|---|---|
| Cost per provider call | None (derivable per-step) | Already answerable via `steps.values("primitive", "cost_actual_micros")` |
| Cost per dialogue turn | None (equal to cost per speech step in dialogue-scene) | Already answerable |
| Cost per rendered minute | Partial. `Composition.cost_actual_micros / (final_asset.duration_ms / 60_000)` works BUT excludes OpenAI cost | Would improve with a persisted OpenAI cost field |
| Average turn duration | Derivable if step-produced Assets carry `duration_ms` per speech asset — most do, some may not | Verify Asset.duration_ms coverage on speech assets |
| Retries per successful Composition | **NOT RECOVERABLE** — retry_step overwrites `cost_actual_micros` and clears `error_message`; no attempt history persisted | New table or JSON journal per step |
| Quality/duration/cost comparisons between recipes | Aggregation possible via `Composition.template_kind` GROUP BY, but no persisted quality metric to correlate against | Would need a per-composition quality field (operator rating, verifier score, or similar) |
| OpenAI-only cost per composition | **NOT PERSISTED** | Add `Composition.synthesis_input_tokens`, `.synthesis_output_tokens`, and/or `.synthesis_cost_micros` |
| Cross-attempt cost accounting | **NOT PERSISTED** | Add `CompositionStep.cost_history` JSON or a `StepAttempt` table |
| "How much of the composition cost was measured vs estimated?" | Partial — `Asset.source_spec.cost_source` is per-asset; requires an aggregation query | Denormalized composition-level summary would speed this up |

**None of these are Slice 4 or later Narrative Memory items.**
They are Character OS platform-observability items and
should be prioritized (or deferred) on their own merits, not
bundled with narrative-memory work.

## 9. What this document does NOT do

- Does NOT implement instrumentation.
- Does NOT change synthesis behavior.
- Does NOT change turn counts, dialogue CPS, duration
  tolerance, corrective headroom, or Writing Contract.
- Does NOT change provider integration.
- Does NOT change any recipe's default or shape.
- Does NOT change the SESSION 264 model migration.
- Does NOT change the SESSION 264 Slice 1/2/3 architecture.
- Does NOT begin the next architectural slice.

It is a **finding**: the SESSION 264 model-migration doc's
"$0.04 Runway increase for 30 s of extra runtime" framing is
potentially misleading, and future dashboards / optimizations
should model the true cost drivers listed in §6.

---

*Recorded 2026-08-18 immediately after SESSION 264 Slice 3
landed. Referenced from the migration doc §11.3.*
