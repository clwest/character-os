---
title: "Composition Observability Schema v1 — Implementation Report"
status: implemented — schema landed; nine behavioral tests green
date: 2026-08-17
depends_on:
  - "design/COMPOSITION_OBSERVABILITY_V1.md"
  - "handoffs/SESSION_259_OBSERVABILITY_BACKLOG.md"
  - "handoffs/SESSION_259_CLOSEOUT.md"
  - "design/EPISODE_VS_COMPOSITION_V1.md"
  - "design/EPISODE_LIFECYCLE_V1.md"
supersedes: []
scope: >
  Implementation record for the SESSION 262 Composition observability
  slice ratified by COMPOSITION_OBSERVABILITY_V1.md. Ships nine
  additive-nullable-or-empty-default Composition columns, the fix that
  preserves the K2 retrieval snapshot on dialogue synthesis failure
  paths, immutability enforcement, and behavioral test coverage. No
  Episode primitive; no Composition.episode FK; no bulk backfill.
---

# Composition Observability Schema v1 — Implementation Report

## Purpose

Persist Composition-local synthesis provenance so post-hoc audits can
answer "what happened to this render attempt" from DB state alone,
without reconstructing behavior from Celery / Runway / OpenAI logs.
Closes six repeated audit blockers documented in
`handoffs/SESSION_259_OBSERVABILITY_BACKLOG.md` §37–46 and
`handoffs/SESSION_259_CLOSEOUT.md` §DF-2. Does NOT implement Episode
(deferred to `EPISODE_SCHEMA_V1`); every field added here is
Composition-local and pre-earns the operator-topic split
`EPISODE_LIFECYCLE_V1.md §Where-operator_topic-lives` describes.

## Exact schema landed

Nine additive columns on `Composition`, all nullable / empty-default:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `operator_topic` | TextField | `""` | Verbatim operator topic / brief that drove synthesis. Empty for operator-typed-script and legacy paths. |
| `target_duration_seconds` | PositiveSmallIntegerField | NULL | Operator-requested spoken duration for duration-driven recipes (long_form_ad, talking_head AI-topic with duration, dialogue_scene ai_topic). |
| `synthesis_attempt_count` | PositiveSmallIntegerField | `0` | `0` = synthesis never fired; `1` = first-pass only; `2` = first + one bounded corrective pass. Bounded at 2 by the one-corrective-pass policy documented in `DIALOGUE_SCENE_AI_TOPIC_V1.md` Rule 6. |
| `first_pass_synthesis` | TextField | `""` | Raw first-pass LLM output. Persisted even on rejection paths — SESSION 259 audit blocker #3 + #6. |
| `corrective_hint` | TextField | `""` | Exact descriptive hint fed to the one bounded corrective pass. Empty when no retry fired. SESSION 259 audit blocker #5. |
| `corrective_pass_synthesis` | TextField | `""` | Raw LLM output of the corrective pass. Empty when no retry fired. On corrective-accepted paths equals `synthesized_brief` shape. |
| `validation_failure_reason` | TextField | `""` | Structured human-readable rejection reason. Empty on accepted synthesis. Prefixes: `dialogue_synthesis:`, `duration_contract:`, `k6_4_strict:`. |
| `synthesis_predicted_seconds` | FloatField | NULL | Synthesis-time predicted spoken duration from the planning estimator. Populates DF-3 CPS-calibration audit. |
| `render_dispatched_at` | DateTimeField | NULL | Moment the first real render primitive dispatched to a provider. NULL when synthesis rejected before provider dispatch. Populated once; immutable. |

Zero new tables. Zero index changes. Zero FK changes. Zero cascade
changes.

## Migration

`shell/apps/compositions/migrations/0014_session262_composition_observability.py`
— nine `AddField` operations. Depends on
`0013_session253_writing_contract_version`. Additive; no data
migration; legacy rows populate to the field defaults on migrate.

## Write paths changed

| Path | File:Line | Change |
|---|---|---|
| Model schema + immutability + `mark_render_dispatched()` helper | `apps/compositions/models.py:487–605` | Added 9 fields, `_IMMUTABLE_OBSERVABILITY_FIELDS` tuple, `from_db()` snapshot hook, `save()` immutability guard, `_observability_value_is_populated()` classifier, `mark_render_dispatched()` helper. |
| DialogueResult observability fields | `character_os/dialogue_synthesis.py:263–279` | Added `attempt_count`, `first_pass_raw`, `corrective_hint`, `corrective_pass_raw` fields (all default-safe). |
| DialogueSynthesisError observability payload | `character_os/dialogue_synthesis.py:190–220` | Extended kwargs: `first_pass_raw`, `corrective_hint`, `corrective_pass_raw`, `attempt_count`, `predicted_seconds`, `chunk_ids`. All optional. |
| synthesize_dialogue attempt tracking + retrieval snapshot on error | `character_os/dialogue_synthesis.py:1364–1420` | Freeze `first_pass_raw_persisted` before retry; freeze `corrective_hint_persisted` at hint construction; freeze `corrective_pass_raw_persisted` after retry response; bump `attempt_count`; on both-passes-failed raise the exception with the retrieval `chunk_ids` snapshot captured from `per_character_chunks`. |
| DialogueResult mock populates observability | `character_os/dialogue_synthesis.py:1197–1216` | Mock branch stamps `attempt_count=1` and a JSON-shaped mock `first_pass_raw` so the audit trail is consistent with real-mode. |
| `_estimate_predicted_seconds_from_raw` helper | `character_os/dialogue_synthesis.py:1503–1531` | Best-effort predicted-seconds estimator from a raw LLM response — populates `predicted_seconds` on the rejection path when parseable. |
| DurationContractError observability payload | `character_os/duration_contract.py:184–241` | Added `first_pass_synthesis`, `corrective_hint`, `corrective_pass_synthesis`, `attempt_count`, `predicted_seconds` optional kwargs. |
| synthesize_with_duration_gate attempt tracking | `character_os/duration_contract.py:503–635` | Freeze `first_pass_brief`, `corrective_hint_used`, `corrective_pass_brief`, `attempt_count`; every `DurationContractError` raise carries them via `_observability_kwargs()`; on accepted return, attached to the ScriptResult. |
| ScriptResult carries per-attempt provenance | `character_os/script_synthesis.py:210–252` | Widened dataclass with `attempt_count`, `first_pass_brief`, `corrective_hint_used`, `corrective_pass_brief`, `predicted_seconds`. Necessary because the class is `@dataclass(slots=True)` — attribute-style attachment would fail. |
| LongFormDurationError observability passthrough | `apps/compositions/starters.py:119–176` | Extended kwargs mirror DialogueSynthesisFailedError; view rescue writes them onto the FAILED composition row. |
| DialogueSynthesisFailedError observability passthrough | `apps/compositions/starters.py:186–260` | Same shape. |
| long_form_ad success Composition create | `apps/compositions/starters.py:1367–1400` | Stamps `operator_topic` (verbatim script), `target_duration_seconds`, `synthesis_attempt_count`, `first_pass_synthesis`, `corrective_hint`, `corrective_pass_synthesis`, `synthesis_predicted_seconds` from the ScriptResult. |
| long_form_ad DurationContractError → LongFormDurationError conversion | `apps/compositions/starters.py:1257–1276` | Forwards `first_pass_synthesis`, `corrective_hint`, `corrective_pass_synthesis`, `attempt_count`, `predicted_seconds`, `operator_topic=script`, `validation_failure_reason=duration_contract:<reason>` onto the wrapper exception. |
| long_form_ad ClaimVerifierError composition create | `apps/compositions/starters.py:1305–1325` | Stamps `operator_topic`, `target_duration_seconds`, `validation_failure_reason=k6_4:strict_rejected:...` on the persisted FAILED row. |
| dialogue_scene AI-Topic DialogueSynthesisError branch | `apps/compositions/starters.py:3454–3477` | Passes retrieval `chunk_ids` snapshot AND all observability fields onto DialogueSynthesisFailedError. Fixes SESSION 259 blocker #4 — `knowledge_chunk_ids` no longer forced to `[]` on the rescue path. |
| dialogue_scene AI-Topic ClaimVerifierError branch | `apps/compositions/starters.py:3487–3502` | Stamps `operator_topic` + `target_duration_seconds` + `validation_failure_reason=k6_4_strict:...` on the exception. |
| dialogue_scene AI-Topic success Composition create | `apps/compositions/starters.py:3591–3617` | Stamps every observability field from the DialogueResult onto the Composition row. |
| talking_head starter Composition create | `apps/compositions/starters.py:642–655` | Stamps `operator_topic` (script when `use_knowledge=True`; empty otherwise) + `target_duration_seconds` at composition-create time. Attempt fields populate later inside the primitive. |
| views.py LongFormDurationError rescue | `apps/compositions/views.py:502–541` | Passes all nine observability fields from the exception to `Composition.objects.create()`. |
| views.py DialogueSynthesisFailedError rescue | `apps/compositions/views.py:553–591` | Same pattern. |
| avatar_speech primitive: mark render + persist attempt log | `apps/compositions/primitives/avatar_speech.py:430–540` | ClaimVerifierError branch stamps `first_pass_synthesis`, `synthesis_attempt_count`, `validation_failure_reason` on the composition. DurationContractError branch stamps `first_pass_synthesis`, `corrective_hint`, `corrective_pass_synthesis`, `synthesis_attempt_count`, `synthesis_predicted_seconds`, `validation_failure_reason`. Accepted path stamps any missing observability fields from the ScriptResult (guarded so first-write-wins). |
| avatar_speech primitive: render_dispatched_at mark points | `apps/compositions/primitives/avatar_speech.py:566–635` | Mock branch calls `composition.mark_render_dispatched()` right before the deterministic PrimitiveResult return. Real branch calls it AFTER `_maybe_synthesize_script` succeeds and BEFORE `client.create_avatar_speech` — the exact "first provider dispatch" moment. Placement satisfies brief §Test #7 ("synthesis fails before provider dispatch" → NULL). |
| visual_clip primitive: render_dispatched_at | `apps/compositions/primitives/visual_clip.py:154–192` | Mock + real paths both call `mark_render_dispatched()` at their dispatch moment. |

## Failure-path behavior

| Failure path | operator_topic | target | first_pass | hint | corrective | attempt_count | predicted | knowledge_chunk_ids | render_dispatched_at |
|---|---|---|---|---|---|---|---|---|---|
| Dialogue AI-Topic both passes fail | ✓ | ✓ | ✓ | ✓ | ✓ | 2 | ✓ (best-effort) | **✓ (retrieval snapshot)** | NULL |
| Dialogue AI-Topic first-pass fail; corrective never fired (invariant impossibility today) | — | — | — | — | — | — | — | — | — |
| Dialogue AI-Topic K6.4 strict rejection | ✓ | ✓ | — (K6.4 post-parse) | — | — | 0 | — | `[]` (unavailable at exception scope) | NULL |
| Dialogue AI-Topic pre-retrieval fail (missing key / cast validation) | ✓ | ✓ | `""` | `""` | `""` | 0 | NULL | `[]` (never retrieved) | NULL |
| Long-form duration contract fail | ✓ (script) | ✓ | ✓ | ✓ (if fired) | ✓ (if fired) | 1 or 2 | ✓ | `[]` (existing behavior; retrieval snapshot not carried to LongFormDurationError; future slice) | NULL |
| Long-form K6.4 strict rejection | ✓ (script) | ✓ | — | — | — | 0 | — | `[]` | NULL |
| Talking-head duration contract fail (in-primitive) | ✓ (from starter) | ✓ (from starter) | ✓ | ✓ (if fired) | ✓ (if fired) | 1 or 2 | ✓ | `[]` (existing behavior) | **NULL** — critical: primitive raised BEFORE `mark_render_dispatched()` |
| Talking-head K6.4 strict rejection (in-primitive) | ✓ (from starter) | ✓ (from starter) | ✓ (`exc.synthesized_text`) | `""` | `""` | 1 | NULL | `[]` | **NULL** |
| Talking-head accepted (duration-driven) | ✓ (from starter) | ✓ (from starter) | ✓ | ✓ (if fired) | ✓ (if fired) | 1 or 2 | ✓ | ✓ (existing behavior) | ✓ (populated pre-client) |
| Talking-head accepted (non-duration K6) | ✓ (from starter) | NULL | ✓ (build_render_brief single pass) | `""` | `""` | 1 | NULL | ✓ (existing behavior) | ✓ (populated pre-client) |
| Talking-head operator-typed script (`use_knowledge=False`) | `""` | NULL | `""` | `""` | `""` | 0 | NULL | `[]` | ✓ (populated at dispatch) |
| Mock composition (any recipe) | (varies) | (varies) | (varies) | (varies) | (varies) | (varies) | (varies) | (varies) | ✓ (populated at mock dispatch) |
| Provider/render failure AFTER dispatch | (persisted) | (persisted) | (persisted) | (persisted) | (persisted) | (persisted) | (persisted) | (persisted) | **✓ (unchanged; immutable)** |

## Immutability enforcement decision

**Chosen mechanism: `from_db()` snapshot + `save()` guard, respecting `update_fields`.**

Alternatives considered and rejected:
- **DB-level trigger / check constraint.** Overkill for a per-render
  audit contract; leaks Django-model semantics into the DB layer;
  fights `update_fields`-based partial writes.
- **DRF serializer read-only after non-empty.** Only covers writes
  that go through the API surface; leaves the runtime executor,
  primitives, and management commands unprotected.
- **Blind `save()` override that always compares in-memory to DB.**
  Would flag legitimate lifecycle writes (`status`, `error_message`,
  `cost_actual_micros`, `verification_*`, etc.) as violations because
  the runtime executor uses `save(update_fields=[...])` on those
  fields without touching the observability set. Rejected because it
  fights the runtime's normal write path.

**As landed** (`apps/compositions/models.py:487–605`):

1. Only nine fields are immutable-once-populated:
   `operator_topic`, `target_duration_seconds`,
   `synthesis_attempt_count`, `first_pass_synthesis`,
   `corrective_hint`, `corrective_pass_synthesis`,
   `validation_failure_reason`, `synthesis_predicted_seconds`,
   `render_dispatched_at`. All other columns (`status`,
   `error_message`, `final_asset`, `cost_actual_micros`,
   `verification_*`, `synthesized_brief`, `rejected_synthesis`,
   `knowledge_chunk_ids`, `writing_contract_version`, `updated_at`)
   retain their existing lifecycles and remain freely mutable.
2. `from_db()` snapshots the persisted values into
   `_loaded_observability` on every instance loaded from DB. New
   (never-loaded) instances have no snapshot and may set any value
   at first write.
3. `save()` walks the immutable set. For each field:
   - If `update_fields` was passed AND excludes this field → no-op
     (save won't touch it; no violation possible).
   - Otherwise, if the previously-persisted value was populated
     (`_observability_value_is_populated()` returns True — non-empty
     string, positive `synthesis_attempt_count`, or non-None
     numeric / datetime) AND the current value differs → raise
     `ValidationError` naming the field.
4. `_observability_value_is_populated` respects the schema defaults:
   `""` for text fields, `0` for `synthesis_attempt_count`, `None`
   for the numeric / datetime fields count as "not yet written."
   The very first real write is always accepted; only subsequent
   divergence is rejected.
5. After every successful `save()`, the snapshot refreshes to the
   just-written state so a second write on the same instance sees
   the current values as the new baseline.
6. `mark_render_dispatched()` is a purpose-built helper that
   render primitives call at the exact provider-dispatch moment. It
   is idempotent (second call is a no-op because
   `render_dispatched_at` is non-NULL) and uses
   `save(update_fields=["render_dispatched_at", "updated_at"])`
   so it never touches other observability fields.

**Adversarial tests proving the invariant:**

- `test_immutable_field_cannot_be_silently_changed` — parametrized
  over all 8 non-datetime immutable fields; each proves that
  attempting to overwrite a persisted non-default value raises
  `ValidationError`.
- `test_immutable_render_dispatched_at_cannot_be_silently_changed`
  — same guarantee for the datetime field.
- `test_same_value_reassignment_is_a_noop_not_a_violation` — writing
  the SAME persisted value does NOT raise (no spurious violations on
  idempotent flows).
- `test_empty_default_values_do_not_lock_the_field` — a row created
  without setting `operator_topic` (defaulting to `""`) can accept
  its first real write; subsequent divergence is then rejected.

**Adversarial tests proving lifecycle writes still work:**

- `test_lifecycle_writes_remain_functional_after_provenance_persisted`
  — creates a Composition with all 9 observability fields populated,
  then exercises the runtime executor's exact save patterns
  (`status`, `error_message`, `cost_actual_micros`,
  `knowledge_chunk_ids`, `verification_status`, `verification_warnings`,
  `synthesized_brief`, `writing_contract_version`) via
  `save(update_fields=[...])`. Every write succeeds; observability
  fields remain intact.

## Test evidence

### Focused SESSION 262 tests

`apps/compositions/tests/test_session262_composition_observability.py`
— **23 tests, all passing**:

| Test | Coverage |
|---|---|
| `test_first_pass_accepted_dialogue_persists_correct_provenance` | Test #1 — first-pass accepted |
| `test_corrective_pass_accepted_dialogue_persists_full_attempt_log` | Test #2 — corrective-pass accepted |
| `test_final_synthesis_rejection_persists_full_attempt_log_and_no_steps` | Test #3 — final rejection with zero steps |
| `test_retrieval_snapshot_survives_synthesis_rejection` | Test #4 — retrieval-before-rejection |
| `test_pre_retrieval_failure_keeps_chunk_ids_empty` | Test #5 — pre-retrieval failure |
| `test_duration_provenance_target_and_predicted_persist` | Test #6 — duration provenance |
| `test_render_dispatched_at_null_when_synthesis_fails_before_dispatch` | Test #7a — NULL on pre-dispatch reject |
| `test_render_dispatched_at_populated_by_primitive_dispatch` | Test #7b — populated on dispatch |
| `test_render_dispatched_at_immutable_after_first_dispatch` | Test #7c — immutable post-dispatch |
| `test_operator_typed_script_leaves_topic_and_attempt_empty` | Test #8a — legacy typed-script |
| `test_talking_head_use_knowledge_records_operator_topic_at_create` | Test #8b — topic-at-create |
| `test_immutable_field_cannot_be_silently_changed` (×8, parametrized) | Test #9a — immutability adversarial |
| `test_immutable_render_dispatched_at_cannot_be_silently_changed` | Test #9b — dispatch-time immutability |
| `test_lifecycle_writes_remain_functional_after_provenance_persisted` | Test #9c — lifecycle writes preserved |
| `test_same_value_reassignment_is_a_noop_not_a_violation` | Test #9d — same-value writes OK |
| `test_empty_default_values_do_not_lock_the_field` | Test #9e — first real write accepted |

Result: **23 passed in 5.03s**.

### Regression suite comparison

Test environment: `DB_PORT=5434 EMBEDDING_FORCE_MOCK=1 pytest ...`
(same pre-existing dev-env convention as SESSION 261).

- **Compositions app** — 1096 passed / 0 failed in 86.33s.
- **Embeddings + spokespeople + realtime + conversations** —
  509 passed / 0 failed in 48.33s.
- **Full backend suite** — **2478 passed / 80 failed / 1 skipped**
  in 208.01s.

### Baseline comparison

| Metric | SESSION 261 baseline | SESSION 262 result | Delta |
|---|---|---|---|
| Full-suite total | 2536 | 2559 | +23 (my new tests) |
| Passed | 2455 | 2478 | +23 |
| Failed | 80 | 80 | 0 |
| Skipped | 1 | 1 | 0 |

Every one of the 80 failures is in the pre-existing failing set:

- 79× `apps/bootstrap_review/tests/*` (fixture-path 404s + tampered-
  byte tests, per SESSION 261 closeout §Test-totals).
- 1× `character_os/clients/tests/test_media_engine_timeouts.py`
  (`test_downstream_deadlines_covers_every_client_method`).

**Zero new failures introduced by SESSION 262.**

## Discoveries and deferred findings

### DF-262-1. K6.4 strict rejection carries no per-attempt provenance

The `ClaimVerifierError` raised by `run_verifier()` inside
`dialogue_synthesis.py` (Rule 7 per-turn verification, per
`DIALOGUE_SCENE_AI_TOPIC_V1.md`) fires post-parse. By the time it
bubbles up, the code path that constructs the exception has already
exited the attempt-tracking scope. As a result, dialogue K6.4-strict
rejections land with `first_pass_synthesis=""`, `attempt_count=0`,
`synthesis_predicted_seconds=NULL` (see failure-path table above).
Same shape for the long-form K6.4 path.

The rejected LLM output is still captured (`rejected_synthesis` /
`exc.synthesized_text`), so the K6.4 rejection is fully
reconstructable — the missing piece is the first-pass provenance
labels. Not a blocker; recorded here as a candidate for a future
½-slice that plumbs the per-attempt scope through `run_verifier`'s
raise site.

### DF-262-2. Long-form failure paths leave retrieval snapshot at `[]`

Only the dialogue AI-Topic exception path was widened to carry the
K2 retrieval snapshot (SESSION 259 blocker #4 was diagnosed on the
dialogue path). `synthesize_with_duration_gate` delegates to
`build_render_brief`; the chunk IDs live inside the ScriptResult but
the `DurationContractError` raise sites do not currently forward
them. Long-form K6.4-strict + duration-contract rejections
therefore still land with `knowledge_chunk_ids=[]`.

Recorded as a symmetric ½-slice: thread `chunk_ids` through
`DurationContractError` and populate on the LongFormDurationError
rescue path in views.py. Not blocking.

### DF-262-3. Non-render primitives leave `render_dispatched_at` NULL

Only `avatar_speech` and `visual_clip` call `mark_render_dispatched()`.
Other primitives (`voiceover`, `voice`, `generate_image`, `transcribe`,
`extend_visual_clip`, `remove_avatar_background`, `style_remix`,
`polish`) all dispatch to the media-engine but do not yet mark the
composition. Compositions whose FIRST primitive is one of these
would land with `render_dispatched_at=NULL` even though the provider
was called.

Two of these (`avatar_speech`, `visual_clip`) are the load-bearing
render primitives for the recipes with in-primitive synthesis and
the recipes without any starter-time synthesis respectively — they
cover the important cases named in the brief. The rest are candidate
½-slices; recorded rather than expanded now to keep the SESSION 262
slice atomic.

### DF-262-4. Composition observability is Composition-local by design

Every field added here lives on `Composition`. The interface
constraints for `EPISODE_SCHEMA_V1` are preserved:

- Composition retains its per-attempt `operator_topic` regardless of
  Episode.
- Episode will add a story-authoritative `operator_topic` layer per
  `EPISODE_LIFECYCLE_V1.md §Where-operator_topic-lives`; Composition's
  copy is unaffected.
- `first_pass_synthesis`, `corrective_hint`,
  `corrective_pass_synthesis` never migrate to Episode — they
  describe a render attempt.
- `synthesis_attempt_count` is bounded 0..2 today; retry semantics
  change under Episode would be a separate slice.

No conflict with the deferred `EPISODE_SCHEMA_V1` slice.

### DF-262-5. `first_pass_brief`/`predicted_seconds` attributes on ScriptResult

`ScriptResult` is a `@dataclass(slots=True)` — attribute-style
attachment (as originally sketched in the design doc) fails at
runtime. Fields were widened directly on the dataclass with
defaults, preserving the pre-SESSION-262 constructor shape (all
existing callers ignore the new fields).

## Interface constraints inherited by `EPISODE_SCHEMA_V1`

1. `Composition.operator_topic` continues to be written on every new
   Composition regardless of Episode attachment. The story-level
   `Episode.operator_topic` is a separate concept
   (`EPISODE_LIFECYCLE_V1.md §Where-operator_topic-lives`).
2. `Composition.first_pass_synthesis` /
   `Composition.corrective_hint` /
   `Composition.corrective_pass_synthesis` describe render attempts;
   they are Composition-scoped forever.
3. `Composition.synthesis_attempt_count` is bounded 0..2. If Episode
   ever changes the retry policy, that's a separate slice — the
   observability contract does NOT prevent it.
4. `Composition.render_dispatched_at` is immutable once populated.
   Deletion + re-attach to a new Episode does not reset it.
5. `Composition._IMMUTABLE_OBSERVABILITY_FIELDS` is closed-set for
   v1. Episode's own model must not extend this list on Composition
   without an explicit design revisit.

## STOP

Implemented, tested, documented. Next step per
`UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md §Model-implementation-sequencing`
is `EPISODE_SCHEMA_V1` — Episode row + `Composition.episode` nullable
FK + cast M2M + DRAFT/ACTIVE/ARCHIVED state machine.
