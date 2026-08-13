---
title: "Character OS — Portrait Qualification Scoring Schema"
status: ratified
generated: 2026-08-06
last_revised: 2026-08-06
companion_files: ["scoring.schema.json", "scoring-template.yaml", "../CANONICAL_IDENTITY_CONTRACT_V1.md"]
---

# Scoring Schema V1

Human-readable companion to
[`scoring.schema.json`](scoring.schema.json) (machine
validation) and [`scoring-template.yaml`](scoring-template.yaml)
(canonical reviewer template). The three files form one
contract per
[`../CANONICAL_IDENTITY_CONTRACT_V1.md`](../CANONICAL_IDENTITY_CONTRACT_V1.md)
§17.7.a.

**The JSON Schema enforces structure. The Markdown explains it.
The template is what reviewers start from.**

## 1. Record types

Scoring evidence uses three record types. Every record is
schema-validated, immutable once written, and carries the
same immutable metadata block.

- **`score`** — a reviewer's scored evaluation of a
  generation against Portrait Territory Study §4 weighted
  categories.
- **`observation`** — a Claude structured observation
  produced from evidence. **Never a score.** Observations
  are searchable input reviewers consult when scoring.
- **`operator_differed_from_observation`** — an explicit
  note when the reviewer's score differs from what an
  observation flagged. Recorded, not resolved (§17.7.b).

Every record starts from `scoring-template.yaml` and is
validated against `scoring.schema.json` at intake.

## 2. Immutable metadata

Every record — score, observation, or disagreement — carries
this metadata block, recorded once at record creation and
never mutated:

| Field | Meaning |
|---|---|
| `benchmark_round` | Which benchmark round produced this record (e.g., `round_one`) |
| `scoring_schema_version` | This schema's `schema_version` at write time |
| `pipeline_version` | Normalization pipeline version from the referenced manifest (§10.6) |
| `normalization_version` | Composition of enabled stage versions from the manifest |
| `fixture_id` | Which fixture (`fixture_h1` … `fixture_nh1`) |
| `fixture_version` | The fixture's identity-version revision |
| `provider` | Provider that produced the underlying generation |
| `direction_hypothesis` | Rendering direction being tested (per Portrait Territory Study §3) |
| `execution_mode` | From §9.4 (`forced_mock` / `auto` / `real_required` / `unavailable`) |
| `execution_mode_actual` | What actually ran (`real` / `mock` / `mock_fallback`) |
| `reviewer` | Named reviewer (round one: `chris`) |
| `timestamp` | ISO 8601 UTC |
| `generation_record_id` | Points at the underlying generation record |
| `manifest_id` | Points at the underlying Normalization Manifest |
| `tier` | `raw` or `normalized` (§17.6.a two-tier evidence) |

## 3. Scoring tier discipline

Every scoring record explicitly declares its `tier`:

- **`raw`** — scores the provider's raw output as returned.
  Reveals raw provider capability.
- **`normalized`** — scores the normalized output produced by
  the pipeline. Reveals combined provider + pipeline result.

A single generation typically produces **two scoring records
per reviewer** — one raw, one normalized. Reviewers score
both explicitly. Aggregation scripts separate the tiers; the
two must never be conflated.

## 4. Weighted categories (Portrait Territory Study §4)

Every `score` record uses these weighted categories. Weights
are fixed by Portrait Territory Study §4 and are not
adjustable per scoring record.

### 4.1 Critical (a candidate that fails any of these is removed)

- **`identity_continuity`** — does identity hold across
  surfaces and transitions?
- **`speech_stability`** — mouth, teeth, lip contour,
  identity during speaking (Portrait Language §10.1)
- **`trust_review`** — do the four trust questions from
  Portrait Territory Study §3.11 all pass?
- **`provider_reliability`** — is the candidate dependent
  on a single fragile vendor pipeline?

Each Critical dimension takes one of:

- `pass` — dimension holds. Explanation optional.
- `concern` — dimension holds but with observed friction.
  Explanation required.
- `fail` — dimension does not hold. Explanation required.
  **A `fail` on any Critical dimension disqualifies the
  candidate direction, regardless of Important or
  Nice-to-have scores.**

### 4.2 Important (strong influence on selection)

- **`warmth`**
- **`distinctness_as_character_os`** — not brand novelty
- **`aesthetic_character_consistent_with_brief`**
- **`long_term_familiarity`** — does not fatigue
- **`demographic_robustness`** — Portrait Territory Study §3.8
- **`cross_modal_continuity`** — Portrait Territory Study §3.1

Each Important dimension takes one of: `strong`, `neutral`,
`weak`, `not_applicable_unscored`.

`not_applicable_unscored` is a **first-class value**, not a
blank. Round-one `fixture_nh1` marks every aesthetic
Important dimension with `not_applicable_unscored` per
§17.2.b ratification.

### 4.3 Nice-to-have (tie-breakers only)

- **`artistic_uniqueness`**
- **`cinematic_grading_quality`**
- **`visual_novelty`**
- **`peer_product_comparability`**

Each Nice-to-have dimension takes one of: `notable`,
`not_notable`, `not_applicable_unscored`.

Nice-to-have scores may not tip a candidate that failed a
Critical or that scored uniformly `weak` on Important.

## 5. `not_applicable_unscored`

Per §17.2.b ratification, aesthetic dimensions on the
non-human fixture (`fixture_nh1`) are marked
`not_applicable_unscored`. This value:

- **Must be an explicit string**, not a blank field, not a
  zero, not `null`.
- **Must not be included in aggregate calculations.**
  Aggregation scripts filter `not_applicable_unscored`
  records out before averaging or comparing.
- **May appear on any category dimension**, not only on
  non-human fixture scores — reviewers may mark any
  dimension unscored when it genuinely does not apply
  (e.g., a fixture that tests only static portraits scoring
  `speech_stability` as `not_applicable_unscored`).

## 6. Observation record shape

Claude observations use this structured shape (§17.7.b
ratification). **Not free-form commentary.**

- **`observed_artifact`** — which artifact the observation
  concerns (generation record id, asset id, manifest id).
- **`observed_behavior`** — what was noticed, in factual
  language.
- **`potential_concern`** — what benchmark discipline this
  potentially violates or supports (referenced by category
  name from §4).
- **`supporting_evidence`** — pointers into the artifact
  (timestamps for motion, regions for stills, transcript
  spans for speech).
- **`confidence`** — `low`, `medium`, or `high`.
- **`affected_benchmark_dimensions`** — array of Portrait
  Territory Study §3 dimensions the observation informs.

**Observations do not carry scores.** They are searchable
input, not judgment. If the reviewer's score disagrees with
an observation, the record type is
`operator_differed_from_observation`, described next.

## 7. Disagreement record shape

Per §17.7.b: reviewer scores never overwrite observations,
and observations never override scores. When the reviewer
scores differently from what an observation flagged, a
disagreement record is appended:

- **`observation_id`** — which observation was disagreed with.
- **`score_id`** — the reviewer's scoring record.
- **`operator_rationale`** — the reviewer's reasoning.
- Standard immutable metadata block.

If later benchmark rounds show the same disagreement pattern
consistently, that pattern becomes examinable evidence at
territory-selection time (§17.7.b).

## 8. Append-only discipline

All evidence is append-only (§17.7.a ratification).

- Reviewer scores never overwrite previous scores.
- Amendments append as new records with a recorded reason.
- Observations never overwrite previous observations.
- Disagreement records never resolve — they persist as
  historical evidence.
- Amendment relationships are captured via `amends` fields
  pointing at prior record IDs.

## 9. Reviewer discipline (round one)

- Chris is the sole scoring reviewer.
- Claude produces observations only.
- No automated agent may write `score` records.
- External human review is engaged only at final territory-
  selection (post-round-one).

## 10. File storage layout

Scoring records live under fixture directories per §17.8.a:

```
fixtures/<fixture_id>/runs/<benchmark_run_id>/<direction>/<provider>/scores/
fixtures/<fixture_id>/runs/<benchmark_run_id>/<direction>/<provider>/observations/
```

Each file is named `<record_id>.yaml`. Record IDs are UUIDs.
`amends` chains are followed by walking `amends` pointers
across files within the same fixture's run tree.

## 11. Evolution rules

- Adding a category dimension to Important or Nice-to-have
  is an amendment (§17.7.a) and requires a
  `scoring_schema_version` bump. Existing records remain
  valid without the new dimension.
- Adding a Critical dimension is more consequential — every
  scored record's Critical evaluation is definitional. A
  Critical addition typically warrants a new schema version
  (V2) rather than an amendment.
- Renaming or removing dimensions requires migration.
- Adding a new record type is an amendment.

## 12. Aggregation script contract (informational)

Aggregation is scripted (§14.2). Scripts must:

- Filter `not_applicable_unscored` out before averaging.
- Segregate `raw` vs `normalized` tiers.
- Preserve amendment chains (score amendments supersede
  earlier scores from the same reviewer for aggregation;
  observations do not).
- Never automatically resolve
  `operator_differed_from_observation` records — they
  appear in reports as themselves, not folded into either
  the score or the observation.

Aggregation is a downstream tool; this schema defines the
data it aggregates over, not the aggregation itself.
