---
title: "Composition Observability v1 — Persisted Provenance for Synthesis Attempts"
status: design — smallest observability slice before Episode (no schema, no code, no migrations)
date: 2026-08-17
depends_on:
  - "handoffs/SESSION_259_OBSERVABILITY_BACKLOG.md"
  - "handoffs/SESSION_259_CLOSEOUT.md"
  - "design/EPISODE_VS_COMPOSITION_V1.md"
  - "design/EPISODE_LIFECYCLE_V1.md"
  - "design/UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md"
scope: >
  Enumerate what synthesis provenance is persisted vs transient on Composition today,
  identify the gaps that repeatedly blocked SESSION 259 audits, and design the smallest
  additive schema slice that closes those gaps WITHOUT conflicting with the deferred
  Episode primitive. Design-only; no schema DDL, no migrations, no code.
---

# Composition Observability v1 — Persisted Provenance for Synthesis Attempts

## Purpose

`UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md §Model-implementation-sequencing`
(lines 1030–1077) sequences the next durable slice as
**EPISODE_SCHEMA_V1**, and names the SESSION 259 backlog fixes
(`operator_topic` per-attempt, retry count, first-pass output,
corrective hint, retrieval snapshot on failure) as work that "can
land in the same slice or as a SESSION 259 backlog cleanup." This
document takes the position that the observability slice must land
**first**, as a standalone deployable slice, because:

1. `EPISODE_LIFECYCLE_V1.md §Q3, §Q9, §Where-operator_topic-lives`
   asserts that Composition owns `operator_topic` **always** — even
   for legacy / Episode-less rows — and owns the per-attempt log
   (first_pass, corrective_hint, retry_count,
   retrieval_snapshot_on_failure) regardless of whether Episode ever
   exists. The Episode row inherits a story-level `operator_topic`
   ON TOP, but never replaces the Composition-level one.
2. `EPISODE_VS_COMPOSITION_V1.md §Intentionally-deferred` (line
   1043–1050) already excises these fields as
   "SESSION 259 fixes that should ship independently — this doc
   identifies which are Composition-level (all of them, at the
   render-attempt layer)."
3. The Episode row's own promise-ledger / event-log surfaces
   (`UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md` deferred item 1,
   line 1123–1125) will depend on being able to answer questions
   like "which corrective hint made this render acceptable?" from
   DB state — impossible today.
4. Landing the observability slice first also means the Episode
   schema slice has one less migration to bundle and one less
   set of fields to reason about at Composition-create time.

Design-only. Every load-bearing claim is cited to file:line or to
prior design docs. No schema DDL. No migrations. No code.

## Scope of this slice

**In scope.**

- Audit of what synthesis provenance is persisted today on
  `Composition`, `CompositionStep`, and adjacent tables.
- Enumeration of what is only present transiently in synthesis code
  paths and lost when the request completes.
- Identification of which gaps repeatedly blocked SESSION 259
  audits.
- Position on which fields belong on `Composition` versus a
  subordinate attempt/audit record.
- Position on which persisted values are immutable-after-write.
- Design of the smallest additive-only schema that closes the gaps
  without conflicting with the deferred Episode primitive.

**Explicitly deferred.**

- Any schema DDL, migration plan, Django field additions.
- Any code change to `dialogue_synthesis.py`, `duration_contract.py`,
  `script_synthesis.py`, `apps/compositions/starters.py`, or
  `apps/compositions/views.py`.
- Any change to the writing-contract, verifier, or retrieval paths.
- `Composition.episode` FK (deferred to `EPISODE_SCHEMA_V1`).
- Episode substrate itself (deferred to `EPISODE_SCHEMA_V1`).
- Multi-corrective-pass retry (v1 remains "one bounded corrective
  pass").
- Per-turn K6.4 warnings persistence beyond current aggregate shape.
- Per-LLM-call token / cost breakdown as a separate observability
  model.

## Persisted vs transient — current state

### What `Composition` persists today

Confirmed by `shell/apps/compositions/models.py:357–511`:

| Field | Type | Populated when | Notes |
|---|---|---|---|
| `id`, `workspace`, `spokesperson` FKs, `created_by`, `created_at`, `updated_at` | — | always | Standard identity + audit. |
| `name` | Char(200) | at create | Overloaded — sometimes topic prefix, sometimes opener; SESSION 259 backlog documented the inconsistency. |
| `template_kind` | Char(80) | at create | `talking_head`, `dialogue_scene`, `long_form_ad`, … |
| `status` | Choice | at create; updated by runtime | draft / planning / running / partial / completed / failed. |
| `final_asset` FK | — | last-step completion | SET_NULL. |
| `knowledge_chunk_ids` | JSON list | success paths only | **Empty on dialogue and long-form failure paths** (`starters.py:1256, 3463, 3489`). |
| `verification_warnings` | JSON list | K6.4 verifier ran | Aggregate; per-turn shape flattened at dialogue starter (`starters.py:3557–3572`). |
| `rejected_synthesis` | TextField | **Strict-mode rejection only** | For dialogue AI-Topic path, populated with `exc.raw_llm_json` (`starters.py:3459`) — the LATER raw response (corrective pass if fired, else first pass; NEVER both). |
| `verification_status` | Choice | verifier ran or explicit fail | verified / trusted_passthrough / skipped / rejected / "". |
| `synthesized_brief` | TextField | successful K6 real-mode with chunks + key | Empty for mock, degraded, passthrough, and every dialogue-failure path (`starters.py:3464, 3490`). Empty for LongForm too-short/too-long rejections that populate via `exc.synthesized_text` (`starters.py:1255`). |
| `writing_contract_version` | PositiveSmallInt | synthesis ran under contract | 0 for pre-contract or degraded. |
| `cost_estimate_micros`, `cost_actual_micros` | PositiveInt | pre-render / post-run | Not per-attempt inside a single Composition. |
| `mock_mode` | Bool | at create | Composition-level per contract rule 9. |
| `error_message` | TextField | failure paths | Human-readable; not machine-classifiable. |

### What `CompositionStep` persists today

Confirmed by `shell/apps/compositions/models.py:551–711`:

- `primitive`, `inputs`, `params` (per-step JSON — dialogue turn
  text ends up in `params.script` per-line at
  `starters.py:3577–3594`).
- `output_asset`, `status`, `cost_estimate_micros`,
  `cost_actual_micros`, `elapsed_ms`, `error_message`.
- `media_engine_task_id`, `started_at`, `completed_at`.

### What is **only present transiently** (never persisted)

The below all live as local variables inside
`shell/character_os/dialogue_synthesis.py::synthesize_dialogue`
(lines 1210–1485) and
`shell/character_os/duration_contract.py::synthesize_with_duration_gate`
(lines 402–632), and vanish when the request completes:

| Item | Location | Why it vanishes |
|---|---|---|
| Verbatim operator topic string | `dialogue_synthesis.py:1214` (`topic:str`); `duration_contract.py:404` (`operator_prompt:str`) | Consumed into prompt via `_build_task_section(topic=…)` and `build_render_brief(operator_prompt=…)`; never written to any row. |
| `target_duration_seconds` | dialogue & duration-contract signatures | Threaded into prompt + validator math; not persisted. |
| `opener` string | both signatures | Threaded into prompt only. |
| `use_knowledge`, `verifier_mode` flags | both signatures | Consumed then discarded. |
| First-pass raw LLM JSON | `dialogue_synthesis.py:1346–1355`, local `raw_json` | Overwritten by corrective-pass `raw_json_2` if retry fires; on success only the final `raw_llm_json` lives on the returned `DialogueResult` dataclass (never persisted to a Composition column). |
| Corrective hint fed to LLM on retry | `dialogue_synthesis.py:1356–1382`, local `corrective_hint` (produced by `_parse_and_validate`) | Discarded after use. |
| Corrective-pass raw LLM JSON | `dialogue_synthesis.py:1375–1384`, local `raw_json_2` | On failure only the LATER response reaches `Composition.rejected_synthesis` via `DialogueSynthesisError.raw_llm_json` (`dialogue_synthesis.py:1397–1401`, starter `starters.py:3459`); the first-pass text is lost. |
| Compression / expansion hint for duration contract | `duration_contract.py:335–396` (`_expansion_hint`, `_compression_hint`) | Same shape; discarded. |
| Retry-attempt count | Implicit in synthesis code (either retry ran or didn't) | Not counted anywhere; inferable only from `error_message` tail on failures. |
| Validation failure reason string | `dialogue_synthesis.py::_parse_and_validate` return values | Returned as `corrective_hint`; on final rejection surfaced only through `error_message`. |
| Per-character retrieved chunk IDs | `dialogue_synthesis.py:1290–1313` (`per_character_chunks` dict); `DialogueResult.per_character_chunk_ids` | Only the aggregated flat list reaches `Composition.knowledge_chunk_ids` on success, and even that is `[]` on every dialogue / long-form failure path (`starters.py:1256, 3463, 3489`). |
| Predicted synthesis duration seconds | `DialogueResult.predicted_seconds`; `_measure()` output in duration contract | Not persisted. |
| LLM model, tokens_input, tokens_output | `DialogueResult.model` / `tokens_input` / `tokens_output`; `ScriptResult.tokens_*` | Not persisted. Composition cost is single aggregate at render time. |
| Whether synthesis reached provider/render dispatch | Implicit only via `CompositionStep` row existence + `media_engine_task_id` populated | No direct field; brittle to reconstruct because a Composition may exist with steps that never fired. |

## Gaps that repeatedly blocked SESSION 259 audits

From `handoffs/SESSION_259_OBSERVABILITY_BACKLOG.md` §37–46 and
`handoffs/SESSION_259_CLOSEOUT.md` "Deferred findings" §DF-2:

1. **Verbatim operator topic invisible.** SESSION 259 could not
   verify the operator topic across compositions `9e4601c7`,
   `8345779c`, `b75a9dba`, `3c24689c` — recovery via truncated
   `name` prefix (~40 chars) was unreliable and produced a false
   inference (v4 duration-overrun blamed on "topic difference"
   that did not actually exist; retracted after operator
   correction).
2. **Retry firing unobservable.** For the accepted final dogfood
   `d79ab53c-5f8b-4587-b5c9-f6bcac535a1b`, whether the corrective
   retry fired was **inferred** from turn shape / char count vs
   prior attempts ("likely yes"). DB state cannot answer.
3. **First-pass output lost on success.** Could not tell whether
   v4 densification appeared on the first pass or only after the
   corrective retry's "tighten" instruction was ignored.
4. **Chunk-ID snapshot missing on failure paths.** Could not
   compare retrieved chunks between `b75a9dba` (accepted) and
   `3c24689c` (rejected) because `knowledge_chunk_ids=[]` on
   `3c24689c` — the current dialogue & long-form failure
   persistence paths pass an empty list (`starters.py:1256, 3463,
   3489`).
5. **Corrective-hint content lost.** The concrete numeric
   compression/expansion hint the retry actually received cannot be
   inspected — critical to understanding why a retry did or did not
   converge.
6. **Rejected-synthesis field carries only one attempt.** When both
   passes fail, `Composition.rejected_synthesis` holds only the
   LATER (corrective-pass) response (`dialogue_synthesis.py:1400`).
   The first-pass response — the one that motivated the retry — is
   discarded. Auditors cannot see what the model corrected FROM.

All six repeated across every SESSION 259 investigation and
directly caused the false inference documented in the observability
backlog file.

## Q1–Q8 answered

### Q1. What is already persisted today?

Enumerated above under §"What `Composition` persists today" and
§"What `CompositionStep` persists today." Sufficient for:

- Reconstructing render-time execution (steps + primitives + task
  IDs + cost + timing).
- Reconstructing the **final** accepted or rejected LLM output
  (via `synthesized_brief` OR `rejected_synthesis`; never both,
  never any intermediate attempt).
- Reconstructing the final verifier verdict + warnings.
- Reconstructing the writing-contract version that shaped the
  final attempt.
- Reconstructing which knowledge chunks fed a **successful**
  synthesis.

Insufficient for the six SESSION 259 blockers above.

### Q2. What is only present transiently?

Enumerated above under §"What is only present transiently." Key
items: verbatim operator topic, target duration, opener flag,
first-pass raw output, corrective hint, corrective-pass raw
output, retry count, validation failure reason, per-character
retrieval snapshot on failure paths, predicted synthesis duration,
per-attempt token counts, render-dispatch reached-or-not.

### Q3. What has repeatedly blocked audits in SESSION 259–260?

The six blockers enumerated above. Root cause is the same for
every one: the synthesis code path treats the first-pass output,
retry hint, corrective-pass output, retrieval snapshot, and
attempt count as **in-flight state that only surfaces on final
rejection**. Success paths keep only the final accepted text +
final aggregate chunk list. Failure paths keep only the LATER
raw LLM response.

### Q4. Which fields belong on Composition versus a subordinate attempt/audit record?

**Position: fields on Composition. No subordinate attempt table
in v1.**

Reasoning:

- The current synthesis loop is **bounded to one corrective
  pass** (`dialogue_synthesis.py:1368–1403`,
  `duration_contract.py:530–562`). That is a load-bearing
  discipline documented in `DIALOGUE_SCENE_AI_TOPIC_V1.md` Rule 6
  and echoed in `SESSION_259_CLOSEOUT.md` §D. Inside a single
  Composition row there are AT MOST two synthesis attempts — one
  first-pass and one optional corrective. Two attempts is a
  fixed-cardinality schema, which maps cleanly to a small set of
  paired fields (`first_pass_*` + `corrective_pass_*`) rather than
  a subordinate table.
- Operator-level "retry" is not a within-Composition concept — it
  creates a **new Composition** row (per
  `EPISODE_LIFECYCLE_V1.md §Q3` "New Composition under the existing
  Episode"; per today's behavior even without Episode). Each
  Composition owns its own bounded attempt log.
- A `CompositionSynthesisAttempt` child model was the "fuller
  option" in `SESSION_259_OBSERVABILITY_BACKLOG.md §Not-proposing-
  implementation-now`; both options were offered but the smallest
  slice was fields on Composition. This slice takes that position.
- If the retry policy ever expands beyond one bounded corrective
  pass (not planned; if it happens it will be its own scope-lock
  slice), migration path is (a) add `synthesis_attempts_extra`
  JSON list on Composition and append, or (b) promote to a child
  table then. Both remain open.

**Subordinate table remains an option later.** It is not designed
here.

### Q5. Which provenance must remain immutable once written?

**Immutable-after-first-write.** These fields describe a specific
synthesis attempt at a specific moment. Overwriting them silently
would destroy the audit trail we are creating.

- `operator_topic` (verbatim)
- `target_duration_seconds`
- `synthesis_attempt_count`
- `first_pass_synthesis`
- `corrective_hint`
- `corrective_pass_synthesis`
- `validation_failure_reason`
- `render_dispatched_at`
- `knowledge_chunk_ids_used_at_synthesis` (see Q6 for why this is
  distinct from the existing `knowledge_chunk_ids`)
- `synthesis_predicted_seconds`

**Enforcement posture (design; not implementation):**

- Convention: populated exactly once at Composition create (or at
  first render-dispatch for `render_dispatched_at`), never on
  updates.
- Serializer-level: `read_only=True` after non-empty.
- Model-level: no built-in immutability in Django; a
  defense-in-depth `save()` override that rejects mutation is
  recommended but out of scope for v1 (would land with the
  schema slice).
- Test-level: at minimum one regression test per field asserting
  that updating a persisted value raises. Same shape as the
  existing K2 M2M cross-workspace / cross-Universe rejection tests
  (`apps/embeddings/tests/test_retrieval_universe.py`).

**Not immutable (existing fields, unchanged).** `status`,
`error_message`, `synthesized_brief`, `rejected_synthesis`,
`verification_*`, `writing_contract_version` retain today's
lifecycle — set once at Composition create or at runtime
completion, but the schema does not enforce it. Leave alone.

### Q6. What is the smallest schema that supports the five behaviors?

The five behaviors from the brief:

1. **failed synthesis before steps exist** — today the FAILED
   composition row already lands via
   `starters.py:1279–1305` (LongForm) and `views.py:538–563`
   (dialogue AI-Topic). The new fields populate on the SAME
   `Composition.objects.create()` call. No new failure path is
   required; the existing exception → view-persistence bridge
   carries the additional payload. Populating
   `knowledge_chunk_ids_used_at_synthesis` on the dialogue-failure
   path also fixes blocker #4 above (currently `[]` at
   `starters.py:3463`).
2. **corrective retry** — `synthesis_attempt_count`,
   `first_pass_synthesis`, `corrective_hint`,
   `corrective_pass_synthesis`, `validation_failure_reason` all
   populate at synthesis end (before Composition.create returns
   in the success path; before the exception is raised in the
   failure path).
3. **accepted synthesis** — existing `synthesized_brief` holds
   the accepted text. On a corrective-accepted case,
   `corrective_pass_synthesis == synthesized_brief`. On a first-
   pass-accepted case, `corrective_pass_synthesis` is empty and
   `synthesis_attempt_count = 1`.
4. **later Episode linkage** — `EPISODE_SCHEMA_V1` will add
   `Composition.episode` nullable FK (per
   `EPISODE_VS_COMPOSITION_V1.md §Decision`,
   `EPISODE_LIFECYCLE_V1.md §H3`). None of the fields added here
   collide with that FK; both are Composition-local. Episode-
   level `operator_topic` (added later) becomes story-
   authoritative; Composition-level `operator_topic` (added now)
   remains the per-attempt record — per
   `EPISODE_LIFECYCLE_V1.md §Where-operator_topic-lives` "on
   Composition ALWAYS; on Episode when Episode exists" (line 583).
5. **debugging without terminal logs** — every fact SESSION 259
   had to reconstruct from Celery logs / Runway responses /
   truncated `name` prefixes is a first-class DB column after
   this slice.

**Proposed minimum fields on `Composition`** (types are design-
suggestions; the schema slice will finalize):

| Field | Suggested type | Populated | Immutable | Rationale |
|---|---|---|---|---|
| `operator_topic` | TextField, blank default `""` | at Composition-create for K6 / dialogue AI-Topic / duration-contract paths; empty for legacy operator-typed-script paths | Y | The verbatim string the operator sent. SESSION 259 blocker #1. |
| `target_duration_seconds` | PositiveSmallIntegerField, nullable | at Composition-create when the recipe is duration-driven (long_form_ad, talking_head duration-driven, dialogue_scene ai_topic); NULL otherwise | Y | Restates the operator's ask; already accepted by every duration-driven recipe kwarg. |
| `synthesis_attempt_count` | PositiveSmallIntegerField, default 0 | at Composition-create; 0 = synthesis never ran (mock / degraded / operator-typed script), 1 = first-pass only, 2 = first + corrective | Y | Fixes blocker #2 (retry firing unobservable). Cap at 2 given the one-bounded-corrective policy. |
| `first_pass_synthesis` | TextField, blank default `""` | at Composition-create when synthesis fired; the RAW LLM output (dialogue: JSON string; long-form: script text) | Y | Fixes blockers #3 + #6. |
| `corrective_hint` | TextField, blank default `""` | when a corrective pass fired; the exact descriptive hint fed to the LLM | Y | Fixes blocker #5. |
| `corrective_pass_synthesis` | TextField, blank default `""` | when a corrective pass fired; the RAW LLM output of the corrective pass | Y | Fixes blocker #6. |
| `validation_failure_reason` | TextField, blank default `""` | when synthesis was rejected (either by parse / duration / verifier), free-form human-readable, `< 500 chars` recommended | Y | Structured version of the tail-of-`error_message` inference in use today. |
| `synthesis_predicted_seconds` | FloatField, nullable | at Composition-create when synthesis fired and produced a measurable prediction (`DialogueResult.predicted_seconds`, duration-contract `_measure()`) | Y | Distinguishes "planning estimator said X" from "render actually took Y" — needed to close DF-3 (cps recalibration audit). |
| `render_dispatched_at` | DateTimeField, nullable | first-render-primitive-fires time; NULL means synthesis rejected / composition failed pre-dispatch | Y | Distinguishes "reached provider" from "never dispatched." Cheaper than joining on `CompositionStep.started_at`. |

**Two existing fields need populate-fixes** (schema unchanged;
behavior change only):

- `knowledge_chunk_ids` — extend the dialogue-failure persistence
  path (`starters.py:3463, 3489`) and the long-form failure path
  (`starters.py:1256`) to pass the actual retrieved chunk IDs
  instead of `[]`. When the failure was pre-retrieval (e.g. missing
  OpenAI key raised before `retrieve_for_teammate` fired), `[]` is
  correct. When retrieval succeeded and synthesis or verifier
  rejected, the retrieval snapshot MUST persist. Blocker #4.
- `rejected_synthesis` — keep its current semantics (final rejected
  output). The new `first_pass_synthesis` and
  `corrective_pass_synthesis` fields cover the per-attempt shape
  that `rejected_synthesis` alone cannot.

**Zero new tables.** Zero FK changes. Zero index changes (no query
pattern in the observability slice requires a new index; the
existing `workspace + status` and `spokesperson + created_at`
indexes remain sufficient). Zero cascade / on_delete changes.

**Every field is additive-nullable-or-empty-default.** Legacy
Composition rows populate to the schema default and behave as
today. Same posture as UNIVERSE_BOUNDARY_V1's Q6 (no bulk
migration).

### Q7. Should `operator_topic` live on Composition even after Episode later gains its own creative-intent/premise field?

**Yes. On Composition ALWAYS; on Episode when Episode exists.**

This position was stated in `EPISODE_LIFECYCLE_V1.md §Where-
operator_topic-lives` (line 583–605) and this slice ratifies it as
the operating assumption:

- Composition's copy is the **per-attempt record** — the exact
  string that drove THIS render. Populated for every Composition
  regardless of Episode existence, regardless of legacy status.
  This is the SESSION 259 backlog fix; it stands whether or not
  Episode ever ships.
- Episode's copy (added later by `EPISODE_SCHEMA_V1`) is the
  **story-authoritative** intent — the operator's story-level
  premise, inherited by attached Compositions at create time and
  re-inherited on retry unless the operator explicitly modifies
  the render's topic.
- The two copies answer different questions ("what did we try to
  render this time?" vs "what is the story about?") and both are
  correct. They may drift for legitimate reasons (operator tweaks
  a single variant's topic while leaving the Episode's story-level
  intent unchanged); the SPA is the arbiter (per
  `EPISODE_LIFECYCLE_V1.md §Q4`, three cases three outcomes).

**Corollary for this slice:** naming the Composition-level field
`operator_topic` is safe. Once Episode exists, the field on
Episode will be named the same and there is no name collision
across models. If a future doc argues Episode's should be renamed
(e.g. `premise`, `story_intent`), Composition's Composition-local
name does not change — it is a per-attempt observability field, not
a narrative field.

### Q8. How should retry/re-render provenance behave if multiple Compositions later belong to one Episode?

Under `EPISODE_LIFECYCLE_V1.md §Q3` and `§Retry-decision-table`
(line 526–544):

- **Operator retry** = new Composition row FKing the same Episode.
- **Cutdown / aspect variant / alternate backdrop / translation** =
  new Composition row FKing the same Episode.
- No provenance data flows between the two Compositions. Each
  Composition owns its own bounded attempt log.

This slice preserves that property by construction: every field
proposed above is Composition-local. There is no aggregation, no
"attempt history across renders," no cross-Composition provenance
graph. Episode later reads its per-Composition provenance via the
reverse relation (`episode.compositions.all()`); each Composition
answers its own audit questions from its own row.

**Consequence:** operators asking "which retry attempt made the
difference?" get an answer that lives on individual Composition
rows. `Composition A` (failed) has its
`first_pass_synthesis`, `corrective_hint`, `corrective_pass_synthesis`,
`validation_failure_reason`. `Composition B` (accepted retry after
operator tweaked the topic) has ITS own first-pass /
corrective-pass / final-accepted `synthesized_brief`. The Episode
row itself never accumulates attempt history; it only owns
`operator_topic` (story-authoritative) and cast (per
`EPISODE_LIFECYCLE_V1.md §Q7`, line 280–323).

**Positive corollary for Episode design.** Because Composition-
level provenance is self-contained after this slice, Episode's
schema does not need any observability fields whatsoever. Its
minimum boundary per `EPISODE_LIFECYCLE_V1.md §Smallest-proposed-
Episode-v1-boundary` (line 545–568) — `id`, `universe` FK,
`workspace` FK (denormalized), `title`, `operator_topic`, `cast`
M2M, `state`, `created_by`, timestamps — stands unchanged.

## Interface constraints Episode must not violate

For the `EPISODE_SCHEMA_V1` slice that follows:

1. `Composition.operator_topic` continues to be written on every
   new Composition, whether or not `composition.episode` is set.
2. `Composition.first_pass_synthesis`,
   `Composition.corrective_hint`, and
   `Composition.corrective_pass_synthesis` never migrate to
   Episode. They describe a specific render attempt.
3. Episode's `operator_topic` may be inherited by attached
   Compositions at Composition-create time, but the inheritance is
   a **copy at that moment** — subsequent edits to
   `episode.operator_topic` do NOT retroactively update prior
   Compositions' `operator_topic`. That immutability is by
   invariant (Q5) and by design intent.
4. `synthesis_attempt_count` is bounded 0..2 today. If Episode's
   arrival changes retry semantics (it does not, per
   `EPISODE_LIFECYCLE_V1.md §Q3`), that is a separate slice.

## Trivial-and-fully-specified? No

Per the operator's brief, "STOP before implementation unless the
audit proves the slice is trivial and already fully specified by
prior docs." Assessment:

- **Named in prior docs:** SESSION 259 backlog names
  `operator_topic` (field or subordinate model), `first_pass`,
  `corrective_hint`, `retry_count`, `retrieval_snapshot_on_failure`.
  `EPISODE_LIFECYCLE_V1.md §Q9` echoes the same set.
- **Not named in prior docs:** the `knowledge_chunk_ids` populate-
  fix on failure paths (currently `[]` at `starters.py:1256, 3463,
  3489`); the `render_dispatched_at` signal; the
  `synthesis_predicted_seconds` field (needed to close the
  SESSION 259 DF-3 CPS-calibration audit); the two-existing-field
  vs eight-new-fields split; the immutability discipline; the
  populate-on-failure-path bridge through
  `DialogueSynthesisFailedError` / `LongFormDurationError` /
  `DurationContractError`.
- **Ambiguities resolved here:** fields-on-Composition vs subordinate
  table (Q4); operator_topic naming stability post-Episode (Q7);
  interaction with Episode retry semantics (Q8).

Not trivial. STOP.

## Recommended next-slice framing (for the operator's decision)

If the operator elects to proceed with implementation, the slice
should be scoped as:

- **`COMPOSITION_OBSERVABILITY_SCHEMA_V1`** — one Django app change
  under `shell/apps/compositions/`. One migration (additive,
  nullable / empty-default on all new columns; no data backfill).
  One synthesis-code-path change per synthesis entry point
  (`dialogue_synthesis.py`, `duration_contract.py`,
  `script_synthesis.py`) to plumb the new fields at Composition
  create. One view-layer change in
  `apps/compositions/views.py::CompositionRecipeViewSet` to plumb
  the new fields on the FAILED-composition rescue paths for
  `LongFormDurationError` and `DialogueSynthesisFailedError`.
  Serializer-level `read_only` after non-empty for the immutable
  fields. Regression tests: one per field asserting persist +
  immutability; one covering the dialogue AI-Topic failure path
  populates `knowledge_chunk_ids` non-empty when retrieval
  succeeded pre-rejection; one covering `first_pass_synthesis`
  non-empty on a successful first-pass path; one covering
  `corrective_pass_synthesis` populated on a successful corrective
  path.

That framing keeps the slice atomic, unblocks `EPISODE_SCHEMA_V1`,
and closes the six SESSION 259 audit blockers in one deploy.

## STOP

Design-only. No schema DDL. No migrations. No code. Every load-
bearing claim is cited to file:line or to
`SESSION_259_OBSERVABILITY_BACKLOG.md`,
`EPISODE_VS_COMPOSITION_V1.md`, `EPISODE_LIFECYCLE_V1.md`, or
`UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md`.
