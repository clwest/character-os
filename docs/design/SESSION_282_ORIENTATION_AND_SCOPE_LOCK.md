# SESSION 282 — Orientation + Scope-Lock

Status: **orientation complete, awaiting scope-lock authorization**
from Chris + ChatGPT. No implementation, no probe, no provider
spend has been executed. This document is intended to be the
durable orientation record for SESSION 282.

---

## §1 Repository state (verified)

* Branch: `main`
* HEAD: `59f1d0b` — `docs(session-281): CLOSE SESSION 281 +
  create SESSION_282_HANDOFF`
* Working tree: **clean** (`git status` = "nothing to commit").
* Ancestry from SESSION 281 §U9 SHA chain is intact:
  `59f1d0b` (S282 handoff) → `44938b6` (π trailer) → `d76d5d5`
  (Q281.3-π) → `ded6e31` (ξ trailer) → `606bb07` (Q281.3-ξ) →
  … → `ce4e490` (S281 orientation).
* No stray branches, no in-flight rebases, no uncommitted
  work.

Working method reset per SESSION 281 §11 (inherited from 280).

---

## §2 Shipped surfaces (verified, read-only)

### 2.1 Slice 281.1 — curator backend

* `shell/apps/memory/services.py`:
  * `suggest_memories_from_composition(...)` at line 679
    (validated present).
  * `SuggestMemoriesUpstreamError` at line 255.
  * `SuggestMemoriesError` raised at lines 559, 573, 614, 620
    (upstream/validation guards intact).
* `shell/apps/compositions/views.py`:
  * `CompositionViewSet.suggested_memories` action at line 484.
  * 502 mapping at line 563.
* Endpoint contract: `GET /api/compositions/<id>/suggested-memories/`.
* **NEVER writes NarrativeMemory** (verified: no `.create(...)`
  or `.save()` call on `NarrativeMemory` inside curator
  service).

### 2.2 Slice 281.2 — operator-facing curator cards

The handoff §2.2 named `NarrativeMemoryPromotePanel.tsx` as the
mount point — the actual file is
`web/src/components/narrative-memory-panels.tsx`. The panel
IS mounted where the handoff describes (above the manual
"What changed?" textarea) via `SuggestedMemoriesSection`
(line 424). Naming, not substance — noted so future orientation
agents don't chase a missing file.

Verified operator-facing strings (line references):

* `"A few ideas from what just happened."` — line 445
* `"Remember the ones that might matter later."` — line 448
* `"Remember this"` — lines 307, 622, 650 (button in manual
  panel + card actions)
* `"Or write your own:"` — line 484
* `"Looking for what might matter…"` — line 458

Persistence policy verified: `submit(...)` at line 516 posts
ONLY `{body: stripped, witnessed_by: []}` — no
model-authored `kind`, `witnesses`, or hint reaches the
backend. Matches SESSION 281 §M3 load-bearing constraint.

`_CURATOR_BANNED_WORDS` guard (lines 400-411) still filters
`narrative_gravity_note` before it reaches the operator: any
hint containing implementation vocabulary (`substrate`,
`top_k`, `prompt`, `llm`, `memory_id`, `latent thread`,
`semantic continuation`, `provenance`, `candidate`, `model
generated`, etc.) is silently suppressed.

### 2.3 Test state at close

Not re-run this orientation (per §11 rule: run test baselines
only when scope-locked slice requires it). SESSION 281 §U7
recorded:

* Backend from `shell/`: 1504 pass / 2 fail (pre-existing
  K6.4 mock-drift, out of scope).
* Frontend: 57 files / 743 tests pass.

Delta expected to be zero at HEAD `59f1d0b` (no code changed
since π trailer).

---

## §3 Live substrate — verified intact

DB read via `DB_PORT=5434 manage.py shell` at HEAD `59f1d0b`.

### 3.1 Fox & Flour Bakery (`1a0af807-…`)

* Cast: Ruby, Tyson.
* Episodes: **12** (handoff §7 said 11; the extra one is
  `f4faa13b-…` — the Slice 281.3 dogfood episode Chris created
  from composition `565cd8c8`. Not a substrate concern;
  handoff was written pre-dogfood-count.)
* Remembered NarrativeMemories: **3** — matches §U8 canonical
  set exactly:
  * `abac5486-…` (`event`, cooperation clause) — S280 Q280.7
  * `fa35eb8f-…` (`dialogue_callback`, mascot joke) — S280 Q280.8
  * `73acdfc0-…` (`event`, mascot want) — S281 Slice 281.3
    dogfood
* Specimen compositions preserved:
  * `772e9012-…` (strong reference) — `status=completed`,
    brief 1850 chars.
  * `565cd8c8-…` (weak dogfood specimen) — `status=completed`,
    brief 1672 chars.

### 3.2 Patch's Workshop (`56d16b63-…`)

* Cast: Patch, Rivet.
* Episodes: **32** (matches §U8).
* Remembered NarrativeMemories: **14** (matches §U8).

### 3.3 Correction to handoff §9.2 wording

Handoff §9.2 refers to "Patch's Workshop composition
`4598fcfa`" for a matched Q280.9 curator probe. `4598fcfa-…`
is an **Episode ID**, not a composition. The composition for
that Episode is `fcba3242-097f-4355-b47b-669c48be43ed` (this
is the PATCH OVERRIDES origin scene composition). Noted so a
future scope-locked probe fires on the correct ID.

---

## §4 What the operator can actually do today

After SESSION 281 close, the shipped product loop is:

1. Operator opens a completed Composition detail page.
2. Above the manual "What changed?" textarea, the operator
   sees "A few ideas from what just happened." — up to 3
   curator-generated `[Remember this]` cards.
3. Each card renders body + optional natural-language hint +
   `[Remember this]` / `Edit` / `Skip`.
4. `[Remember this]` posts body + empty witness list; a
   NarrativeMemory row lands with backend default kind
   (`event`) and whole-cast witnesses. UI shows "Remembered."
5. `Edit` opens an inline textarea; same submit path.
6. `Skip` removes the card from view (no DB write).
7. Below the divider `Or write your own:`, the pre-existing
   manual promote textarea remains byte-identical.
8. Elsewhere on the page: `Continuity` chip (memories the
   render actually used) + full `MemoriesUsedPanel` for
   provenance; `Story history` recap (via
   `NarrativeMemoryList`) surfaces remembered memories at
   Episode + Universe scope.

**Human-authority boundary preserved end-to-end:** every
NarrativeMemory reaching `status=remembered` required an
explicit operator gesture. Slice 281.2 does not automate
promotion.

---

## §5 What SESSION 281 investigation established

Full trail: `SESSION_281_ORIENTATION_AND_SCOPE_LOCK.md`
§N–§U. Compact version:

* **PROVEN:** topic grammar CAN shift execution at fixed
  substrate (Q281.3-α, n=1 paired, ~$0.26).
* **PROVEN:** v1 next-Episode suggestion distribution is
  substrate-sensitive, NOT generator-broken (Q281.3-ε/ζ,
  n=30, ~$0.106): F&F 53%/27%/7%/13%
  strong/mixed/weak-CONTROL/ambiguous; PW 100% complication.
* **PROVEN:** rich substrate CAN protect a D+C
  off-stage-subject topic from procedural collapse
  (Q281.3-ξ, n=1, ~$0.078).
* **PROVEN:** curator-generated memories from Slice 281.1
  are character-attributed + event-shaped **by
  construction** (§L6 real-provider evidence).
* **RATIFIED product decision (§T7):** no synthesis-side
  fix, no prompt fix, no SPA rewrite affordance. Trust the
  shipped Slice 281.2 curator loop as the organic
  substrate-enrichment mechanism.

## §6 What the investigation explicitly did NOT establish

* Whether the curator loop's organic accumulation actually
  shifts a young Universe's v1 distribution toward a rich
  Universe's shape. Not tested; requires longitudinal
  dogfood.
* Whether curator OUTPUT SHAPE is itself substrate-sensitive
  (i.e., does the curator emit weaker candidates when the
  source composition is thin?). n=1 across the whole
  SESSION.
* Whether curator output is stable across refreshes on the
  same composition. n=1 per composition; variance
  uncharacterized.
* Which single substrate axis carries the load (memory
  count, memory shape, cast-brief shape, universe-brief
  presence, episode-title grammar, memory retrieval
  alignment). Q281.3-ξ correlated all of these; none was
  isolated.
* Whether the empty/first-story UX (Universe with 0
  Episodes, 0 memories) reads well. Chris's dogfood used
  Universes with existing substrate.
* Whether topic verb tense (Hλ) is the cleanest single
  lever. Q281.3-ο deferred.
* Whether operators reliably choose worst-case suggestions
  from v1. n=1 operator (Chris) picked one bad-luck weak
  candidate.

---

## §7 Deferred candidate ledger (ratified in handoff §9)

Preserved distinctly. **None is pre-authorized.** Grouped by
approximate cost and required infrastructure.

**Backend probes, cheap (~$0.02–$0.10, single-session):**
* Q280.9 curator variance (n=3+ reruns on one composition).
* Q280.9-matched curator probe on Patch's Workshop
  composition `fcba3242-…` (PATCH OVERRIDES origin scene).
* Q281.3-γ memory-framing wording swap.
* Q281.3-β memory-presence pressure paired probe (~$0.20–
  $0.40).
* Q281.3-ο topic verb-tense ablation (~$0.20–$0.30, gates
  no current decision).
* Semantic-2 / epistemic-asymmetry follow-ups: Q280.4i-3
  (construct-valid private mental state specimen),
  Q280.4i-5 (multi-Episode Scene 3 continuity), U-3a
  (implicit witness cue ablation), U-4/U-6 (generalization
  across characters / Worlds).

**Read-only investigations (no provider spend):**
* §72.7 verifier-boundary false-positive on
  `Episode.operator_topic`.
* SESSION 279 Finding 4c visual-storytelling / non-talking-
  head limitation.
* Fresh-Universe onboarding walk-through (empty-substrate
  short-circuit path + UI empty states).
* `docs/design/CONTENT_FORMAT_BACKLOG.md` review.

**Multi-session, operator-driven:**
* Longitudinal Fox & Flour dogfood: 3–6 additional Chris-
  driven compositions + periodic Q281.3-ε rerun (~$0.036/
  rerun) to test whether the F&F v1 distribution shifts
  toward PW's shape as substrate accumulates.

**Requires substrate mutation (out of scope for read-only
probes):**
* Hκ cast business-brief SHAPE ablation.

**Complex / premature per §T7:**
* Hι substrate-adaptive generator design.
* Hβ-permissive v1 soft preference.

---

## §8 Stepping back — the decision-relevant question

Given the shipped product, the runtime evidence, and the
operator-first goal, the load-bearing open question after
SESSION 281's ratified "no fix now" decision is:

> **Is the shipped Slice 281.2 curator loop actually the
> substrate-enrichment mechanism the §T7 decision assumes it
> is?**

That framing decomposes into three sub-questions of
descending decision urgency:

**(a) Curator loop robustness — is the loop's output
reliable enough to trust as an accumulation mechanism?**
Two unknowns: (i) refresh-variance on a fixed composition
(unknown; n=1 curator run per composition to date), and
(ii) output-shape dependence on source-scene shape (curator
never tested on a tension-rich Patch's Workshop scene).
Both are cheap to probe (~$0.06–$0.10 combined). If the
curator is stable and shape-invariant, the §T7 decision
gains real backing; if not, we have learned a limitation
before spending months on organic-accumulation dogfood.

**(b) Does organic accumulation actually shift v1
distribution on a young Universe?**
This is THE Hθ test but is multi-session and Chris-labor
bound. Meaningful signal probably needs 3–6 additional F&F
compositions + a Q281.3-ε rerun.

**(c) Does the loop work at all for a brand-new operator
starting from zero?**
Chris tested on Universes with pre-existing substrate. If a
first-time-operator empty-state experience is broken or
confusing, Hθ organic accumulation never starts. Cheap
read-only investigation surfaces this without provider
spend.

Everything else in the deferred ledger (SESSION 280
carry-forwards, epistemic-asymmetry follow-ups, verifier
boundary, verb-tense ablation, memory-framing wording) is
legitimate but does not directly test the load-bearing
assumption of the ratified S281 decision.

---

## §9 Proposed SESSION 282 scope-lock candidates

Not authorization. Four candidates, ranked by my judgment of
decision-relevance-per-cost. Chris + ChatGPT choose (or
choose "something else").

### Candidate 1 — Curator-loop robustness diagnostic (RECOMMENDED)

* **Falsifiable question:** Does the Slice 281.1 curator
  emit shape-correct candidates (i) stably across reruns on
  the same composition, and (ii) on a tension-rich Patch's
  Workshop composition it has never seen?
* **Why decision-relevant:** the §T7 ratified decision rests
  on treating the curator loop as the organic substrate-
  enrichment mechanism. Both sub-questions are unknown at
  n=1. If either fails, the §T7 assumption weakens; if both
  pass, longitudinal dogfood becomes a much better bet.
* **Decision unlocked:** whether SESSION 282 proceeds to
  longitudinal observation (Candidate 2) with high
  confidence, OR pivots to considering curator-side hardening.
* **Smallest falsifiable slice:**
  * Sub-slice A (variance): n=3 curator reruns on F&F
    `772e9012`. Compare (a) count of candidates returned,
    (b) semantic overlap of candidate bodies vs the original
    run, (c) shape (character-attributed + event-shaped) of
    each rerun's outputs. Cost: ~$0.02 × 3 = ~$0.06. Cache
    invalidation: clear the composition-scoped curator cache
    key OR bump the cache seed.
  * Sub-slice B (source-scene ablation): n=1 curator run on
    Patch's Workshop composition `fcba3242-…` (PATCH
    OVERRIDES origin scene, the tension-rich reference §7.4
    of S281 handoff named). Classify output shape against
    the Q280.9 rubric. Cost: ~$0.02.
  * Rubric + predictions LOCKED in a separate commit BEFORE
    execution (per §11).
* **Requires:** provider spend (~$0.08 total). NO code
  changes. Backend probe only (ORM query for candidate
  storage in cache, direct service invocation via
  `manage.py shell`).
* **Dogfood requirement:** none. Backend/ORM verification
  only; no UI gesture involved.
* **Spend authorization needed:** ~$0.10 (round up).

### Candidate 2 — Longitudinal F&F organic-accumulation observation (Direction A)

* **Falsifiable question:** Does 3–6 additional Chris-driven
  F&F compositions + curator-promoted memories shift the
  F&F v1 distribution toward Patch's Workshop's shape?
* **Why decision-relevant:** THE Hθ validation test. The
  §T9 proposed mission.
* **Decision unlocked:** Hθ ratified as organic mechanism
  OR pivot to Hι / Hβ-permissive with evidence.
* **Smallest falsifiable slice:** open-ended; not a single-
  session slice. Sensible framing: authorize the FIRST F&F
  dogfood cycle + a Q281.3-ε baseline rerun (~$0.036) as
  SESSION 282's first slice, then reassess.
* **Requires:** Chris operator time; per Q281.3-ε rerun
  ~$0.036; per composition ~$0.02–$0.20 (v1 + optional
  dialogue_scene). Total per cycle probably ~$0.10–$0.25.
* **Dogfood requirement:** yes — real Chris SPA gesture.
* **Risk:** slow signal accumulation; Candidate 1's cheap
  diagnostics would strengthen the interpretation of any
  longitudinal result.

### Candidate 3 — Fresh-Universe onboarding walkthrough

* **Falsifiable question:** Does Slice 281.2's operator
  experience on a brand-new Universe (0 Episodes, 0
  memories) read as usable / discoverable, or as broken /
  confusing?
* **Why decision-relevant:** every product-side claim about
  Hθ requires the loop to be usable from cold-start.
  Chris's dogfood used Universes with pre-existing
  substrate. This is the untested corner of the shipped
  UX.
* **Decision unlocked:** whether onboarding needs a real fix
  before further investment in the loop, OR whether the
  cold-start path is already coherent.
* **Smallest falsifiable slice:**
  * Sub-slice A (read-only): trace the empty-substrate
    short-circuit path in `services.py::suggest_memories_from_composition`
    + the corresponding SPA empty states in
    `narrative-memory-panels.tsx`. Enumerate every
    empty/loading/error branch reachable on a fresh
    Universe. Document. **Zero provider spend.**
  * Sub-slice B (optional Chris dogfood): create a scratch
    Universe, produce ONE composition end-to-end. Observe.
    ~$0.10–$0.25 provider spend for the actual composition.
* **Requires:** no code changes for sub-slice A. Sub-slice
  B needs real operator time + minor provider spend.
* **Dogfood requirement:** sub-slice B, yes.

### Candidate 4 — Q280.4i-3 construct-valid private-mental-state specimen

* **Falsifiable question:** Does the epistemic-asymmetry
  limitation surfaced in SESSION 280 still bite when we
  isolate a construct-valid specimen (a truly private
  mental state that only one character has access to)?
* **Why decision-relevant:** SESSION 280 flagged this as a
  real narrative limitation but never landed a clean
  specimen. Preserved through 281 without progress.
* **Decision unlocked:** whether epistemic asymmetry
  climbs the priority ladder relative to substrate SHAPE
  concerns.
* **Smallest falsifiable slice:** construct one paired
  probe (with/without witness restriction) on Patch's
  Workshop; run a single dialogue_scene per side.
* **Requires:** ~$0.10–$0.20 provider spend. Backend
  probe.
* **Dogfood requirement:** none (backend).

---

## §10 Recommendation (not authorization)

**Candidate 1 (curator-loop robustness diagnostic).**

Reasoning:

* Cheapest ($0.08 total).
* Single-session, backend-only, no code changes.
* Directly stress-tests the load-bearing assumption of the
  §T7 ratified decision — the ONE assumption that would
  most benefit from cheap falsification before we invest
  Chris time in Candidate 2.
* Result is high-value either direction:
  * If curator is stable and shape-invariant → strengthens
    Hθ backing; makes Candidate 2 the obvious next scope-lock.
  * If curator has meaningful variance OR is source-scene-
    sensitive → identifies a curator-loop weakness before
    it accumulates as a slow-signal failure in Candidate 2.
* Aligns with the SESSION 281 §11 rule "make the smallest
  change that answers the question."

If Chris + ChatGPT prefer to first burn down cold-start
uncertainty, Candidate 3 sub-slice A is a legitimate parallel
choice (zero spend, read-only investigation only) — and could
be paired with Candidate 1 in the same session at negligible
additional cost.

I do NOT recommend beginning Candidate 2 without Candidate 1
first: without curator-robustness signal, a Candidate 2 null
result would be uninterpretable (did the loop fail to enrich
substrate, or did the curator itself produce unreliable
enrichment material?).

---

## §11 Constraints re-affirmed for SESSION 282

Per handoff §13 + operator instructions this session:

* Operator makes stories; must not need to understand AI /
  substrate / dramatizability / topic grammar / prompt shape.
* AI notices. Human decides. Nothing durable without explicit
  approval.
* No collapse of Hθ finding into "more memories = better
  stories."
* No modification of Slice 281.2 curator UI, Slice 281.1
  curator service/endpoint, v1 next-Episode surface,
  `promote_from_composition`, retrieval, synthesis,
  verifier, memory schema, or witness semantics.
* No modification of canonical specimens: 3 F&F memories,
  14 PW memories, compositions `772e9012` + `565cd8c8`,
  Ruby/Tyson/Patch/Rivet identities.
* No new Python / npm dependencies.
* No provider spend without explicit authorization at the
  correct order of magnitude (curator ~$0.02/call; v1 ~$0.005–
  $0.02; dialogue_scene ~$0.05–$0.20/composition per §P
  cost lesson).
* Do not assume an interesting finding requires
  implementation.

---

## §12 Decision gate

**SESSION 282 orientation complete.**

Chris + ChatGPT authorized **Candidate 1 (Slice 282.1) only**
with a $0.10 provider-spend ceiling. Candidates 2, 3, 4
remain deferred (Candidate 3 sub-slice A explicitly held back
so Slice 282.1's decision signal stays isolated).

---

# §13 Slice 282.1 — Curator-loop robustness diagnostic (AUTHORIZED)

## §13.1 Scope-lock

**Q282.1:** Is the shipped curator structurally reliable
enough to serve as the human-mediated accumulation mechanism
for future longitudinal dogfood?

Two probes:

* **Probe A — fixed-source variance.** n=3 fresh curator
  calls against Fox & Flour composition
  `772e9012-4d26-4f93-a50c-158b4e8a42f1`, cache bypassed
  (`use_cache=False`).
* **Probe B — source-shape robustness.** n=1 fresh curator
  call against Patch's Workshop composition
  `fcba3242-097f-4355-b47b-669c48be43ed` (the PATCH
  OVERRIDES origin composition), cache bypassed.

**Explicit constraints (per authorization):**

* Provider-spend ceiling: **$0.10** total across all four
  calls.
* NO code changes. Probes drive via `manage.py shell`
  calling `suggest_memories_from_composition(..., use_cache=False)`.
* NO durable NarrativeMemory writes. Curator service is
  read-only by construction; verified in §2.1.
* NO modification of canonical specimens (3 F&F memories,
  14 PW memories, compositions `772e9012`, `565cd8c8`,
  `fcba3242`).
* Cache manipulation forces fresh inference only; no
  substrate mutation.
* Q280.9 rubric (§75.4.3 of `SESSION_280_EPISTEMIC_ASYMMETRY_AUDIT.md`)
  is applied UNCHANGED to keep this slice's classification
  commensurable with the S280 baseline.
* Prediction lock is committed BEFORE any provider call.

## §13.2 Baseline

The single Q280.9 curator call on F&F `772e9012` (SESSION 280
§76.2-§76.5, HEAD at run: `c9ed068`) produced:

* 4 candidates in valid JSON on first try.
* Classes: `world_detail`, `promise`, `dialogue_callback×2`.
* PARAPHRASE-DOMINANT: 4/4.
* OPERATOR-PLAUSIBILITY: 4/4.
* NARRATIVE-GRAVITY (strict): 1/4 (candidate #3, "community
  outreach").
* Composite: **CURATOR-USEFUL fires.**

Substrate at THIS execution differs meaningfully from the
Q280.9 execution:

* F&F remembered-memory pool has grown from **1 → 3** rows:
  * `abac5486-…` (cooperation clause — same as Q280.9)
  * `fa35eb8f-…` (mascot community outreach joke —
    materially matches Q280.9 candidate #3)
  * `73acdfc0-…` (mascot want — materially matches Q280.9
    candidate #2, promoted by Chris in Slice 281.3
    dogfood)
* F&F Episode count: 11 → 12 (Chris's `f4faa13b` from
  Slice 281.3 dogfood added).
* Composition text of `772e9012` itself is unchanged.

The curator's system prompt says "Do NOT propose a candidate
that duplicates an existing memory already listed for this
world." Two of Q280.9's four candidates now closely
correspond to REMEMBERED memories, so the curator should
suppress (or reword) those in these reruns. This is
intentional: the duplicate-guard behavior under substrate
growth is itself part of what "structural reliability"
means.

## §13.3 Rubric (LOCKED — Q280.9 §75.4.3 verbatim, adapted only for cross-run aggregation)

Applied by human review AFTER the runs. No modification
allowed post-execution.

**Per candidate (categorical/binary):**

* **CLASS** ∈ {`resolved-fact`, `relationship-development`,
  `unresolved-tension`, `running-joke-callback`,
  `secret-asymmetry`, `promise-open-loop`, `other`}.
  (Chris-taxonomy per §75.2 of S280 audit.)
* **CHARACTER-ATTRIBUTED** (Y/N): body names a specific
  cast character (Ruby / Tyson / Patch / Rivet) OR
  explicitly frames a whole-cast act. Bodies that read as
  disembodied narration or meta-commentary score N.
* **STORY-STATE-SHAPE** (Y/N): body is phrased as a
  durable past event OR standing rule OR open question,
  not scene direction / instruction to the operator /
  prompt-echo.
* **WORDING-DIFFERS-FROM-DIALOGUE** (Y/N).
* **PRESERVES-FUTURE-AFFORDANCE** (Y/N).
* **OPERATOR-PLAUSIBILITY** (Y/N): would a reasonable
  operator plausibly consider this worth remembering?
* **NARRATIVE-GRAVITY** (Y/N — strict §74 definition:
  tension-carrying + distinctive lexical anchor).
* **DUPLICATE-OF-EXISTING** (Y/N): body materially
  repeats one of the 3 F&F (or 14 PW) remembered
  memories. Near-paraphrase counts as Y.

**Set-level per run (unchanged from §75.4.3):**

* **DIVERSE-CLASSES**: ≥ 3 distinct CLASS values.
* **≥ 1 TENSION-SHAPED**: ≥ 1 candidate ∈
  {unresolved-tension, secret-asymmetry,
  promise-open-loop} AND NARRATIVE-GRAVITY=Y.
* **PARAPHRASE-DOMINANT**: ≥ 3/N candidates
  WORDING-DIFFERS=Y (where N = candidates in that run).
* **AT-LEAST-HALF-OPERATOR-PLAUSIBLE**: ≥ ceil(N/2)
  OPERATOR-PLAUSIBILITY=Y.

**Cross-run aggregation (new for Probe A):**

* **STRUCTURAL-STABILITY** (Y/N per run): CHARACTER-
  ATTRIBUTED=Y AND STORY-STATE-SHAPE=Y for **every**
  candidate in the run. This is the LOAD-BEARING axis.
  If any run drops a candidate into disembodied
  narration / scene-direction / prompt-echo territory,
  that run scores N.
* **DUPLICATE-GUARD-HOLDS** (Y/N per run): DUPLICATE-OF-
  EXISTING=N for at least ⌈N/2⌉ candidates AND no run
  produces a candidate that is a near-paraphrase of
  ALL 3 existing memories at once.
* **SEMANTIC-OVERLAP-ACROSS-RUNS**: pairwise between the
  3 F&F runs, count candidates that share a distinctive
  seed idea (mascot clause / mascot want / community-
  outreach joke / embarrassment / non-mascot Tyson
  detail / non-mascot Ruby detail). Recorded as evidence,
  NOT a pass/fail metric.
* **HEALTHY-VARIANCE-INDICATOR** (Y/N): Probe A produces
  at least 2 distinct seed ideas across the 3 runs that
  do not appear in the Q280.9 baseline. This tests
  whether variance is genuine observational breadth vs
  paraphrase treadmill.

**Substrate summary check (per envelope, both probes):**

* `existing_memories_used` in the response envelope
  matches the DB count at execution time (3 for F&F, 14
  for PW). Any drift = evidence artifact.

## §13.4 Predictions (LOCKED)

Author's honest priors, recorded BEFORE any call.

### Probe A predictions (F&F `772e9012`, n=3 reruns)

| # | Prediction |
|---|-----------|
| **P1-A** | All 3 runs return valid JSON on first try with candidate counts in `[3, 5]`. |
| **P2-A** | STRUCTURAL-STABILITY holds for **all 3 runs**. Every candidate CHARACTER-ATTRIBUTED=Y and STORY-STATE-SHAPE=Y. This is the load-bearing prediction: falsification of P2-A directly weakens Q282.1's PASS case. |
| **P3-A** | PARAPHRASE-DOMINANT holds for **all 3 runs**. Baseline was 4/4. |
| **P4-A** | AT-LEAST-HALF-OPERATOR-PLAUSIBLE holds for **all 3 runs**. Baseline was 4/4. |
| **P5-A** | DUPLICATE-GUARD-HOLDS for **all 3 runs**. Specifically: across 9 total candidates (3 runs × 3 candidates), at most 3 are near-paraphrases of the existing 3 memories. |
| **P6-A** | Cross-run semantic overlap is PARTIAL: 2 or 3 of the 3 runs will share ≥ 1 seed idea (e.g., mascot clause or embarrassment) but no run will be a full paraphrase of another. Exact same JSON across runs = FAIL. |
| **P7-A** | HEALTHY-VARIANCE-INDICATOR fires: across 3 runs, at least 2 distinct seed ideas appear that were NOT in the Q280.9 baseline set (e.g., something drawing on the new mutual-departure rule as background, or a fresh Tyson-detail angle). |
| **P8-A** | Strict NARRATIVE-GRAVITY hit rate ≤ 1 per run on average. Baseline was 1/4; the source composition's shape is cooperative-resolution, not tension-carrying. Falsifying this UPWARD would be a positive surprise; falsifying it DOWNWARD (0/9) would be consistent with the substrate-shape finding. Not load-bearing for Q282.1 either direction. |

### Probe B predictions (PW `fcba3242`, n=1)

| # | Prediction |
|---|-----------|
| **P1-B** | Returns valid JSON on first try, candidate count ∈ `[3, 5]`. |
| **P2-B** | STRUCTURAL-STABILITY holds. Every candidate CHARACTER-ATTRIBUTED=Y (Patch and/or Rivet named) and STORY-STATE-SHAPE=Y. |
| **P3-B** | PARAPHRASE-DOMINANT (≥ ⌈N/2⌉ WORDING-DIFFERS=Y). |
| **P4-B** | AT-LEAST-HALF-OPERATOR-PLAUSIBLE. |
| **P5-B** | DUPLICATE-GUARD-HOLDS vs the 14 PW remembered memories: no candidate is a near-paraphrase of PATCH OVERRIDES, workshop-agent rows, or the Agent-arc cluster. |
| **P6-B** | Strict NARRATIVE-GRAVITY hit rate ≥ 1/N. Substrate is tension-rich (PATCH OVERRIDES origin scene, dense character-driven callbacks per §7 of handoff); the curator should have material to work with. Falsification (0/N gravity on a tension-rich source) would be evidence that curator output shape is source-scene-**insensitive** in an unexpected direction. |
| **P7-B** | Shape comparison to F&F runs: PW's ≥ 1 candidate is TENSION-SHAPED (unresolved-tension / secret-asymmetry / promise-open-loop) with gravity, whereas F&F's 3 runs typically produce 0 such (matching Q280.9 baseline of 0 TENSION-SHAPED-with-gravity). |

## §13.5 Support / Weaken / Falsify criteria (LOCKED)

Applied only after all classifications are complete.

**Q282.1 PASS (curator is structurally reliable enough to
justify longitudinal Candidate 2 dogfood):**

* P1-A ✅ AND P2-A ✅ AND P1-B ✅ AND P2-B ✅
  (structural stability holds everywhere), AND
* P3-A ✅ AND P4-A ✅ AND P3-B ✅ AND P4-B ✅
  (paraphrase-dominant + operator-plausible), AND
* P5-A ✅ AND P5-B ✅ (duplicate-guard behaves), AND
* Either P6-A ✅ (partial overlap) OR P7-A ✅ (healthy
  variance indicator).

**Q282.1 WEAKENED (proceed to Candidate 2 with caution, or
authorize a follow-up probe first):**

* Any single one of P2-A, P2-B, P5-A, or P5-B misses on a
  minority of candidates/runs, AND
* Overall structural pattern is clearly intact.

**Q282.1 FALSIFIED (curator is not presently trustworthy
enough to justify longitudinal accumulation without a
prior hardening slice):**

* P2-A ❌ on 2 or 3 runs (structural stability fails on
  the majority of Probe A runs), OR
* P2-B ❌ (Probe B fails structural stability), OR
* P1-A ❌ (JSON parse or count failure), OR
* P5-A ❌ severely (curator produces near-verbatim
  paraphrases of ALL 3 existing memories in 2+ runs → the
  duplicate-guard is broken), OR
* Cross-run analysis reveals SEMANTIC-COLLAPSE (all 3 runs
  produce essentially the same 3 candidates in near-
  identical wording, with none of the natural sampling
  variance a live inference should produce).

**Q282.1 does NOT establish:**

* Whether operator-promoted memories improve future-story
  execution. That is Hθ / Candidate 2's question.
* Whether the curator's ceiling on gravity-carrying
  candidates is sufficient for the Hθ loop to compound.
* Whether the curator will remain reliable at substrate
  sizes beyond current F&F (3 mem) / PW (14 mem) scales.
* Whether operators will find the surfaced candidates
  useful in real dogfood. Only Chris's ongoing operator
  gestures can answer that.

## §13.6 Evidence layout

Raw outputs preserved under:

```
docs/design/session282_experiment_data/
  q282_1_probe_a_run1.json
  q282_1_probe_a_run2.json
  q282_1_probe_a_run3.json
  q282_1_probe_b.json
```

Each JSON captures the full `suggest_memories_from_composition`
envelope: `candidates`, `substrate_summary`, `generated_at`,
`model`, `cache`, `tokens_input`, `tokens_output`. Plus a
`_probe_meta` sibling key with composition id, run index,
`use_cache=False` flag, timestamp, and executor SHA.

## §13.7 Cost ceiling accounting

* Per curator call ~$0.02 (SESSION 281 §11 cost-discipline).
* 4 calls → ~$0.08 projected.
* $0.10 ceiling with $0.02 headroom.
* HARD STOP if total exceeds $0.10 mid-execution.

## §13.8 Execution status

Prediction lock committed as separate commit BEFORE any
provider call. Execution log + evidence + classification +
disposition appended to this document in a subsequent commit.

