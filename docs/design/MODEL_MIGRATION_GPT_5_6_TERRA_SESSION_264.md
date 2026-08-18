# MODEL MIGRATION — gpt-5 → gpt-5.6-terra (SESSION 264 post-Slice-2)

**Scope:** Character OS dialogue writer + script writer only.
**Status:** implemented, tested, awaiting operator dogfood.
**Related audit:** `docs/design/EPISODIC_CONTINUITY_CANON_PROMOTION_AUDIT_SESSION_264.md`
(baseline Composition `ef11c810` recorded in the Slice 2 dogfood
addendum).

**Change one variable rule.** This session changes ONLY the model
constant on the two writer surfaces. Every calibration constant,
retrieval architecture, prompt, Writing Contract, reasoning
effort, API path, structured-output shape, and provider
integration is preserved so the operator dogfood can attribute
any observed delta directly to the model tier swap.

---

## 1. Pre-migration baseline (locked)

The operator's clean pre-change dogfood evidence — captured in
the SESSION 264 Slice 2 dogfood addendum — is the reference
point every post-migration render is compared against.

| Field | Value |
|---|---|
| Episode | `b8e228b8-3dfe-4e7b-84aa-a4a5bac6c9ba` — "The agent is acting weird again" |
| Composition | `ef11c810-d52c-4107-a5c4-ecb779d5797a` |
| Model | `gpt-5` |
| API | Responses API |
| `reasoning_effort` | `low` |
| `max_output_tokens` | 4000 |
| Structured output | `text={"format": {"type": "json_object"}}` |
| Writing Contract | v4 |
| Target duration | 60 s |
| Accepted synthesis | 727 chars, predicted ~56 s |
| Rendered final asset | `21bee00c-f0b3-4a20-97b8-17e68d660cc6` (mp4, **59,281 ms**) |
| Cost | 220,100 micros (~$0.22) |
| Synthesis attempts | 2 (first pass 2,066 c → corrective → 1,420 c → accepted 727 c body sum) |
| NarrativeMemory retrieval | PASS — `f25e53af-…` in `memory_ids` |
| Static canon retrieval | PASS — `da7e6553-…` first in `knowledge_chunk_ids` |
| K2 retrieval | PASS — 5 Patch + 5 Rivet chunks |
| Continuity | PASS — Rivet: "Define weird." + Patch turn 2 memory callback |
| Verification status | `verified` (K6.4 accepted every turn) |
| Archived-memory exclusion | PASS — `3d1ba9bc-…` did not participate |
| Canon invariant | HELD — zero KnowledgeDocuments touched |

This is the **falsification baseline**. If the post-migration
render fails NarrativeMemory retrieval, static canon retrieval,
K2 retrieval, continuity, or canon isolation — the model swap
regressed something that the audit predicted was orthogonal.

---

## 2. Audit findings (READ-ONLY, pre-change)

Full audit is in the SESSION 264 transcript. Summary:

**All 8 OpenAI model references in the codebase.** Only the two
below fall under the operator's "dialogue/script writer" scope.

| Surface | File:Line | Constant | Value (pre) | In migration scope? |
|---|---|---|---|---|
| Dialogue synthesis | `character_os/dialogue_synthesis.py:90` | `DIALOGUE_MODEL` | `gpt-5` | **YES** |
| Script synthesis | `character_os/script_synthesis.py:75` | `SCRIPT_MODEL` | `gpt-5` | **YES** |
| Conversation reply | `character_os/conversation_synthesis.py:49` | `REPLY_MODEL` | `gpt-5` | No — different product surface |
| Teammate ask | `character_os/teammate_ask.py:57` | `ASK_MODEL` | `gpt-5` | No — different product surface |
| Realtime memory | `character_os/realtime_memory.py:68` | `MEMORY_MODEL` | `gpt-5` | No — different product surface |
| Transcript miner | `character_os/transcript_miner.py:71` | `MINER_MODEL` | `gpt-5-mini` | No — separate mini tier |
| Script splitter | `apps/compositions/script_splitter.py:85` | `SCRIPT_SPLIT_MODEL` | `gpt-5-mini` | No — separate mini tier |
| Transcription hook | `apps/compositions/transcription.py:139` | inline | `gpt-5-mini` | No — separate mini tier |

**API contract:** all callers use the Responses API with kwargs
that GPT-5.6 also accepts:

- `model=<constant>`
- `input=<system + user text>`
- `reasoning={"effort": "low"}`
- `max_output_tokens=<int>`
- `text={"format": {"type": "json_object"}}` (dialogue only, for
  structured turns)

**No `temperature=`, no `verbosity=`, no legacy `max_tokens=`,
no other model-family-specific kwargs.**

**No per-model pricing tables** in synthesis code. Cost is
captured as `tokens_input` + `tokens_output` on
`ScriptResult` / `DialogueResult` for observability, not
multiplied by a per-model rate. No cost-accounting update is
required for this migration.

**Model selection:** all hard-coded string literals. No settings
entry, no env-var override, no DB-driven selection. Migration is
a two-constant swap.

**Corrective pass** shares `DIALOGUE_MODEL` — the same
`_call_dialogue_api` function serves first-pass and corrective.
Swapping the constant automatically covers both passes and the
`DialogueResult.model` stamp.

**No MIGRATION BLOCKERS** identified.

---

## 3. Facts about GPT-5.6 taken as operator-supplied

Per the operator brief (2026-08-18):

- `gpt-5.6-terra` is the GPT-5.6 balance-of-intelligence-and-cost
  tier.
- GPT-5.6 supports `reasoning_effort` values:
  `none | low | medium | high | xhigh | max`.
- GPT-5.6 tends to be more concise by default than previous
  generations.
- Both Responses API and Chat Completions are supported;
  Responses is recommended for reasoning / tool / multiturn
  workloads.

**Model-string existence has not been independently verified**
by this session (my knowledge cutoff predates the GPT-5.6
release). The operator's real dogfood is the verification.

---

## 4. What changed

Two lines of production code, plus documentation-tracking
edits in four test files that had hard-coded the previous model
string in mock fixtures.

### 4.1 Production changes

```python
# shell/character_os/dialogue_synthesis.py:90
DIALOGUE_MODEL = "gpt-5.6-terra"    # was "gpt-5"

# shell/character_os/script_synthesis.py:75
SCRIPT_MODEL = "gpt-5.6-terra"      # was "gpt-5"
```

Each site got a SESSION 264 migration comment above it
pointing to this document, preserving the SESSION 171 / SESSION
260 calibration commentary already present.

### 4.2 Test-fixture hygiene

Four test files hard-coded `"gpt-5"` (or `"gpt-5 (mock)"`) in
`DialogueResult` / `ScriptResult` fixture literals. Rather than
bumping the literal, each was refactored to import the constant
so future migrations don't require a test edit.

| File | Change |
|---|---|
| `apps/compositions/tests/test_dialogue_ai_topic_wiring.py` | Imports `DIALOGUE_MODEL`; fixture uses `model=DIALOGUE_MODEL` |
| `apps/compositions/tests/test_session262_composition_observability.py` | Imports `DIALOGUE_MODEL`; fixture uses `model=DIALOGUE_MODEL` |
| `apps/compositions/tests/test_long_form_ad_duration_contract.py` | Imports `SCRIPT_MODEL`; fixture uses `f"{SCRIPT_MODEL} (mock)"` |
| `apps/compositions/tests/test_long_form_ad_knowledge_ordering.py` | Same |

### 4.3 What did NOT change (per operator brief)

- Prompts (system + user + task section + precedence rules)
- Writing Contract v4
- `_DIALOGUE_CPS = 13`
- `_DURATION_TOLERANCE = 0.20`
- `DIALOGUE_DURATION_SYNTHESIS_TARGET_MULTIPLIER = 1.00`
- `_DIALOGUE_CORRECTIVE_HEADROOM_FRACTION = 0.92`
- `_MAX_OUTPUT_TOKENS = 4000`
- `_REASONING_EFFORT = "low"` (dialogue) / `REASONING_EFFORT = "low"` (script)
- Turn bands, opener behavior, corrective-hint mechanic
- SESSION 263 canon retrieval lane
- SESSION 264 Slice 2 NarrativeMemory retrieval lane
- Per-character K2 retrieval
- K6.4 claim verifier (rule-based; no LLM path)
- Universe / Episode / Composition observability
- Provider render configuration (Beyond Presence avatar path)
- Every `gpt-5` reference outside the writer surface (reply,
  ask, memory, miner, splitter, transcription)

---

## 5. Tests

### 5.1 New: `apps/compositions/tests/test_model_migration_gpt_5_6_terra.py`

Eight focused tests pinning the migration surface. Zero
provider calls; canonical SESSION 263/264 mock pattern.

| # | Test | Covers |
|---|---|---|
| 1 | `test_dialogue_model_is_gpt_5_6_terra` | Operator-facing lock — the single line to edit for future tier swaps. |
| 2 | `test_script_model_is_gpt_5_6_terra` | Same for script writer. |
| 3 | `test_reasoning_effort_preserved_at_low` | Guards against arbitrary reasoning bumps. |
| 4 | `test_dialogue_calibration_constants_unchanged_by_migration` | Writing Contract v4, CPS=13, tolerance=0.20, multiplier=1.00, headroom=0.92, max_output_tokens=4000. |
| 5 | `test_dialogue_first_pass_call_sends_gpt_5_6_terra` | Actually invokes `synthesize_dialogue`; asserts `client.responses.create` called with `model="gpt-5.6-terra"`, `reasoning={"effort":"low"}`, `text={"format":{"type":"json_object"}}`, `max_output_tokens=4000`. |
| 6 | `test_dialogue_corrective_pass_also_uses_gpt_5_6_terra` | Forces a corrective retry (too-long first pass); asserts BOTH calls use the new tier. |
| 7 | `test_dialogue_uses_responses_api_not_chat_completions` | Guards against silent API refactor. |
| 8 | `test_dialogue_does_not_send_temperature_or_verbosity` | Guards against a future edit adding kwargs GPT-5.x reasoning models reject. |

### 5.2 Regression sweep

```
DB_PORT=5434 EMBEDDING_FORCE_MOCK=1 python -m pytest \
  apps/compositions/tests/ apps/memory/ \
  apps/embeddings/tests/ apps/universe/tests/ \
  apps/videos/tests/test_script_synthesis.py -q
```

→ **1440 passed, 0 failed** (includes the 8 new migration tests
plus the pre-existing SESSION 262 observability tests, SESSION
263 canon-lane tests, and SESSION 264 Slice 1 + Slice 2 tests
whose hard-coded model strings were refactored to import the
constant).

### 5.3 Test infrastructure unchanged

The canonical mock pattern
(`mock_patch("openai.OpenAI", return_value=fake_client)` +
`fake_client.responses.create.side_effect = ...` returning
objects with `output_text` + `usage.input_tokens/output_tokens`)
is model-agnostic. No test infra edits needed.

---

## 6. Cost implications

Not computed here. Character OS captures token usage on
`ScriptResult` / `DialogueResult` for observability but does not
maintain per-model pricing tables in synthesis code, so no rate
constants require updating. Any per-tier cost analysis is a
post-dogfood observation.

The mini-tier surfaces (miner, splitter, transcription) are
unchanged and stay on `gpt-5-mini`; their cost profile is
untouched.

---

## 7. Deviations from the operator brief

None. All prompts, calibrations, retrieval architecture, K6.4
behavior, structured-output shape, API path, and reasoning
level preserved exactly. One-variable-changed discipline held.

---

## 8. Compatibility caveats

- **`text={"format": {"type": "json_object"}}`** is a Responses-
  API kwarg; not model-specific. Assumed compatible with
  `gpt-5.6-terra`. If the operator's dogfood surfaces a 400
  Bad Request from the provider on this kwarg, the corrective
  is a Responses-API-side change (not a model-swap issue).
- **Reasoning effort `"low"`** is on the GPT-5.6 supported
  ladder per operator-supplied facts. If GPT-5.6 rejects
  `"low"` (unlikely but possible), the corrective is a value
  swap in the same two files.
- **Concision default** — the operator brief notes GPT-5.6
  tends to be more concise. Our first-pass target character
  count is derived from `target_duration_seconds * _DIALOGUE_CPS`
  (60 × 13 = 780 chars). If GPT-5.6 systematically under-shoots
  the target, we may see MORE corrective passes (or the
  corrective may still under-shoot). The corrective-headroom
  mechanic (`0.92 × soft_max`) exists to compress overshoot,
  not to expand undershoot — that's a calibration observation
  for a follow-up session, NOT a change for this migration.

---

## 9. Rollback

Two-line revert. Change:

```python
DIALOGUE_MODEL = "gpt-5.6-terra"   # → back to "gpt-5"
SCRIPT_MODEL   = "gpt-5.6-terra"   # → back to "gpt-5"
```

Test-fixture hygiene changes (imports of `DIALOGUE_MODEL` /
`SCRIPT_MODEL` in four test files) can stay — they're
model-agnostic improvements. Existing 1440-test suite passes
identically before or after the constant value.

---

## 10. Operator dogfood expectation

Re-run the same Episode workflow:

> Episode: `b8e228b8-3dfe-4e7b-84aa-a4a5bac6c9ba` — "The agent
> is acting weird again"
> Cast: [Patch, Rivet]
> Target duration: 60 s

Expected outcomes (any deviation is signal about the model tier,
not about the retrieval architecture):

- Retrieval lanes fire identically (same 11 KnowledgeChunk IDs
  in `knowledge_chunk_ids`, same `f25e53af-…` in `memory_ids`,
  archived `3d1ba9bc-…` still absent).
- K6.4 verifies without regression on grounded facts.
- Duration lands within the ±20 % band (48 s – 72 s).
- Canon invariant holds (zero `KnowledgeDocument` updates
  after render).
- Cost differs from the $0.22 baseline (delta observation,
  not a target).
- Continuity + callback quality is the actual variable of
  interest; the baseline "Define weird." + "runs the workshop…
  Again." pattern is the reference point.

**Do NOT begin Slice 3 until this dogfood completes and the
delta is characterized.**

---

*Migration implemented, tested, and documented. Awaiting the
operator's re-run of the baseline Episode.*

---

## 11. Post-migration dogfood — ACCEPTED (2026-08-18)

Operator re-ran the same Episode ("The agent is acting weird
again", cast Patch + Rivet) under `gpt-5.6-terra` at two
durations. Both runs passed every retrieval invariant vs the
`ef11c810` baseline; dialogue quality materially improved.

**Verdict: gpt-5.6-terra ACCEPTED as the Character OS
dialogue/script writer.** Do not revisit unless implementation
evidence surfaces a concrete regression.

### 11.1 60-second Terra render

| Field | Value | vs `ef11c810` baseline |
|---|---|---|
| Target duration | 60 s | same |
| Actual rendered duration | ~59 s | ~equal (was 59.28 s) |
| Runway cost | ~$0.18 | (baseline lumped totals: $0.22 all-in; Terra split visible for the first time) |
| OpenAI cost | ~$0.03 | new visibility |
| Total | **~$0.21** | ~$0.01 lower than baseline |
| NarrativeMemory retrieval | PASS (`f25e53af-…` in `memory_ids`) | held |
| Universe canon retrieval | PASS (`da7e6553-…` in `knowledge_chunk_ids`) | held |
| K2 retrieval | PASS (5 Patch + 5 Rivet) | held |
| Continuity | PASS | held |
| Archived-memory exclusion | PASS (`3d1ba9bc-…` absent) | held |
| Canon invariant | HELD (zero `KnowledgeDocument` updates) | held |

**Quality observations (operator-supplied):**

- Rivet behaved more like a character and less like a
  methodology narrator.
- Patch/Rivet conversational causality improved (turn N picked
  up from turn N-1's specific verb / noun instead of resetting
  the topic each turn).
- Technical methodology appeared as *behavior* — Rivet doing
  the debugging move — instead of *exposition* — Rivet
  reciting the debugging move.
- Comedic callbacks improved.

### 11.2 90-second Terra render

| Field | Value |
|---|---|
| Same Episode + story context | (Patch + Rivet, "The agent is acting weird again") |
| Target duration | 90 s |
| Predicted duration (synthesizer estimate) | ~104 s |
| Synthesized brief | 1,358 characters |
| Actual rendered duration | ~96 s |
| Runway cost | ~$0.22 |
| OpenAI cost | ~$0.07 |
| Total | ~$0.29 |
| Incremental cost vs 60 s | **~$0.08** |
| All retrieval lanes | PASS |
| Continuity | PASS |
| Canon invariant | HELD |

**Quality observations (operator-supplied):**

- Sustained ONE conversational thread instead of filling
  runtime with methodology exposition.
- Rivet remained analytical without becoming a debugging
  manual.
- Patch retained character voice.
- Jokes/payoffs built from prior turns.
- *"A cable is not a promotion."* — a useful example of
  concise Rivet voice.
- Methodology such as *"change one thing"* appeared naturally
  in context, embedded in a turn, not as a lecture header.

### 11.3 Duration-default findings

> **REINTERPRETATION NOTE (added post-Slice-3):** The cost
> deltas quoted in §11.1 / §11.2 were originally framed as
> "$0.04 Runway increase for the longer video." Subsequent
> code + runtime analysis (see
> `docs/design/PROVIDER_CALL_ECONOMICS_SESSION_264.md`)
> showed that avatar-rendering cost is NOT primarily
> duration-driven — it is turn-count-driven for
> dialogue-scene renders because each turn maps to exactly
> one `generate_avatar_speech` provider dispatch. The
> $0.04 delta reflects a small increase in the number of
> avatar-speech dispatches at 90 s, not a per-second rate.
> The default-change decision below still stands (longer
> scenes produced better dialogue at acceptable incremental
> cost) but the underlying cost model is turn-count, not
> duration. See PROVIDER_CALL_ECONOMICS §2 for the corrected
> decomposition.

The 90-second render's quality delta over the 60-second
render was material and asymmetric:

- Under a 60-second target the model burns most of the runway
  on setup + one callback + closer. Room for maybe 12-14 short
  turns.
- Under a 90-second target the model can sustain a full
  cause → response → escalation → resolution → coda arc.
  Room for 18-22 turns with real callbacks between them.
- Incremental cost of ~$0.08 to move from 60 s to 90 s is
  small compared to the storytelling gain. Two-thirds of the
  extra cost is Runway avatar-speech time; only one-third is
  OpenAI (reasoning + output tokens).

**Decision: change the Episode Dialogue Scene workflow default
from 60 s to 90 s.** Scoped strictly to the Episode / Dialogue
Scene operator flow; NOT applied to talking-head, spokesperson,
long-form, or generic Composition infrastructure. The operator
can still explicitly pick 60 s or other supported durations
per-render. Implemented as its own commit; tests prove default,
explicit override, and non-regression on unrelated recipes.

### 11.3.1 Post-default-change Terra runs — duration calibration is adequate

Two additional 90-second Terra runs against the same Episode
("The agent is acting weird again", cast Patch + Rivet) landed
after the 60 s → 90 s default-change commit `b819633`. Recorded
here as evidence that the current dialogue CPS / tolerance /
corrective-hint calibration is sufficiently accurate for operator
use on Terra + 90 s targets. **These are runtime observations,
not a mandate to retune anything.**

| Run | Composition | Synth chars | Predicted | Actual | Attempts |
|---|---|---|---|---|---|
| A | `a119b064-b2f5-4c7d-85c0-45d03999845a` | 1,358 | ~104 s | 96 s | (post-Slice-3 dogfood; two attempts) |
| B | `79d0bbd5-e791-4962-8f7b-80988dbaec6c` | 1,353 | ~104 s | 95.41 s | **1** (first-pass accepted) |

Observations:

- Both actuals fall comfortably inside the ±20 % tolerance band
  for a 90 s target (72–108 s).
- Predictor systematically over-predicts by ~9 s on this shape.
  That's a safe direction — over-prediction protects the
  ceiling; under-prediction would cause more corrective retries
  or over-runs.
- Run B accepted on first pass (`synthesis_attempt_count = 1`),
  no corrective. Terra's default output length matches the 90 s
  target well enough on this Episode shape to skip the retry
  loop entirely.

**Explicitly recorded non-goals from the dogfood brief:**

- Do NOT retune `_DIALOGUE_CPS = 13`.
- Do NOT retune `_DURATION_TOLERANCE = 0.20`.
- Do NOT retune `_DIALOGUE_CORRECTIVE_HEADROOM_FRACTION = 0.92`.
- Do NOT retune `DIALOGUE_DURATION_SYNTHESIS_TARGET_MULTIPLIER = 1.00`.
- Do NOT rewrite the corrective-hint text.

These runs establish calibration adequacy for one recipe /
model / target-duration combination. Not evidence for or
against a general calibration change.

### 11.4 Invariants held on both Terra renders

- **Generated != Remembered** — synthesis output did not
  auto-create NarrativeMemory rows.
- **Remembered != Canon** — neither render mutated any
  `KnowledgeDocument`.
- **Provenance intact** — `memory_ids` and
  `knowledge_chunk_ids` persisted correctly.
- **Archived-memory exclusion** — `3d1ba9bc-…` did not
  participate in either render.
- **Cross-Universe / cross-Workspace isolation** — retrieval
  scope enforcement unchanged.
- **Immutability of Composition observability** — SESSION 262
  fields not disturbed.
- **Writing Contract v4 unchanged.**
- **Reasoning effort stayed at `"low"`.**

### 11.5 Nothing to revert

Both Terra renders produced correct behavior with the exact
API shape, calibration constants, and retrieval architecture
committed in `7d23270`. The single-variable-changed discipline
held. No rollback required.

---

*Migration accepted post-dogfood. Model constant continues at
`gpt-5.6-terra`. Duration default change to 90 s ships as its
own commit; Slice 3 (Composition detail memory-provenance
panel) ships after that.*
