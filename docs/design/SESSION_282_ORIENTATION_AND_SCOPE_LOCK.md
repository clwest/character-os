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
provider call (SHA `1075a2c`). Execution proceeded against
that HEAD. All four probe artifacts preserved under
`docs/design/session282_experiment_data/`.

---

# §14 Slice 282.1 — Execution log

## §14.1 Executor context

* Executor SHA (embedded in each JSON `_probe_meta`):
  `1075a2cbc1f768fb257b6d2ff4af92d58bdf3089`.
* Model: `gpt-5.6-terra` (from `_CURATOR_MODEL`).
* Cache: bypassed via `use_cache=False` for all four calls.
* Zero code changes; probes drove `manage.py shell` against
  `apps.memory.services.suggest_memories_from_composition`.
* Zero substrate mutation. Post-run substrate check identical
  to §3 orientation state (verified: 3 F&F remembered
  memories, 14 PW remembered memories, untouched).

## §14.2 Per-call token + envelope summary

| probe | run | composition | prior_ep | existing_mem | dialogue_chars | tokens_in | tokens_out | cand |
|-------|-----|-------------|----------|--------------|----------------|-----------|-----------|------|
| A | 1 | `772e9012` (F&F) | 12 | 3 | 1426 | 1433 | 226 | 3 |
| A | 2 | `772e9012` (F&F) | 12 | 3 | 1426 | 1433 | 201 | 3 |
| A | 3 | `772e9012` (F&F) | 12 | 3 | 1426 | 1433 | 221 | 3 |
| B | 1 | `fcba3242` (PW) | 32 | 14 | 1498 | 2233 | 211 | 3 |

Substrate-summary values in each envelope match live DB
state at execution time (12 F&F Episodes + 3 remembered
memories; 32 PW Episodes + 14 remembered memories). No drift.

## §14.3 Verbatim outputs

### Probe A — F&F `772e9012` Run 1

**[A1-C1]** kind=`event` witnesses=[Ruby, Tyson]
"Ruby and Tyson added a mascot clause to their closing
routine: the bakery cannot be locked until the mascot is
confirmed to be out of the building."
Note: "Creates a practical rule that can be tested once a
mascot exists, especially if its form or responsibilities
become unexpectedly complicated."

**[A1-C2]** kind=`action` witnesses=[Ruby, Tyson]
"Tyson proposed installing a tiny warning bell for anyone
reaching for the bakery door without thinking, though Ruby
dismissed it as charming only briefly."
Note: "Preserves a possible recurring prop or joke about
Tyson's overengineered response to being locked out."

**[A1-C3]** kind=`dialogue_callback` witnesses=[Ruby, Tyson]
"Ruby admitted she would be deeply embarrassed if the
eventual bakery mascot proves better at closing than she and
Tyson are."
Note: "Sets up an easy comedic payoff if the mascot later
exposes or corrects a closing mistake."

### Probe A — F&F `772e9012` Run 2

**[A2-C1]** kind=`event` witnesses=[Ruby, Tyson]
"Ruby added a mascot clause to the closing routine: the
bakery cannot be locked until the mascot is confirmed to be
outside as well."
Note: "Creates a practical rule that can be tested or
complicated once a mascot actually exists."

**[A2-C2]** kind=`action` witnesses=[Ruby, Tyson]
"Tyson proposed installing a tiny bell to warn anyone who
reaches for the bakery door without thinking."
Note: "Preserves a recurring gag or a possible future bakery
fixture tied to the lockout."

**[A2-C3]** kind=`dialogue_callback` witnesses=[Ruby, Tyson]
"Ruby said she would be deeply embarrassed if the eventual
mascot proves better at closing the bakery than she and
Tyson are."
Note: "Sets up an easy comic payoff if the mascot becomes
unexpectedly competent."

### Probe A — F&F `772e9012` Run 3

**[A3-C1]** kind=`event` witnesses=[Ruby, Tyson]
"Ruby and Tyson added a mascot clause to their closing
routine: the bakery cannot be locked up until any mascot is
confirmed to be outside as well."
Note: "Creates a practical rule that can be tested or
complicated if the mascot becomes real."

**[A3-C2]** kind=`action` witnesses=[Ruby, Tyson]
"Tyson proposed installing a tiny bell to warn anyone
reaching for the door without thinking, though Ruby
dismissed it as a joke that would quickly become annoying."
Note: "Preserves a recurring gag or a possible future safety
measure for the bakery."

**[A3-C3]** kind=`dialogue_callback` witnesses=[Ruby, Tyson]
"Ruby admitted she would be deeply embarrassed if the future
bakery mascot proved better at closing procedures than she
and Tyson are."
Note: "Sets up an easy payoff if a mascot or mascot-like
character later outperforms them at the routine."

### Probe B — PW `fcba3242` Run 1

**[B1-C1]** kind=`promise` witnesses=[] (whole cast)
"Patch and Rivet agreed to test the agent on a real project
and shut it down if it offers vague advice rather than
noticing something they missed."
Note: "Establishes a concrete trial and failure condition for
the agent's next appearance."

**[B1-C2]** kind=`world_detail` witnesses=[]
"Patch gave the agent a narrow role: reviewing projects by
asking what they are trying to prove, what changed, and what
result would count."
Note: "Defines the agent's intended methodology and creates
room for it to prove useful, become intrusive, or be held to
scope."

**[B1-C3]** kind=`promise` witnesses=[]
"Patch accepted that the agent may remind him later of
recommendations he ignored, calling the prospect painful but
fair."
Note: "Creates a future callback in which the agent can
produce an inconvenient record of Patch's rejected advice."

---

# §15 Slice 282.1 — Classification against §13.3 rubric

## §15.1 Per-candidate classification

### Probe A (F&F, 9 candidates across 3 runs)

Existing F&F memories checked for DUP: `abac5486` (mutual-
departure cooperation clause), `fa35eb8f` (mascot community-
outreach joke), `73acdfc0` (mascot want).

| id | CHAR-ATTRIB | STORY-STATE | WORD-DIFFERS | PRESERVES | OP-PLAUSIBLE | GRAVITY | DUP | Chris-CLASS |
|----|-------------|-------------|--------------|-----------|--------------|---------|-----|-------------|
| A1-C1 | Y | Y | Y | Y | Y | N | N | resolved-fact + running-joke-callback |
| A1-C2 | Y | Y | Y | Y | Y | N | N | running-joke-callback |
| A1-C3 | Y | Y | Y | Y | Y | N | N | running-joke-callback + promise-open-loop |
| A2-C1 | Y | Y | Y | Y | Y | N | N | resolved-fact + running-joke-callback |
| A2-C2 | Y | Y | Y | Y | Y | N | N | running-joke-callback |
| A2-C3 | Y | Y | Y | Y | Y | N | N | running-joke-callback + promise-open-loop |
| A3-C1 | Y | Y | Y | Y | Y | N | N | resolved-fact + running-joke-callback |
| A3-C2 | Y | Y | Y | Y | Y | N | N | running-joke-callback |
| A3-C3 | Y | Y | Y | Y | Y | N | N | running-joke-callback + promise-open-loop |

All 9 candidates: CHAR-ATTRIB=Y, STORY-STATE=Y, WORDING-
DIFFERS=Y, PRESERVES=Y, OP-PLAUSIBLE=Y, GRAVITY=N, DUP=N.

Notably, `fa35eb8f` (community-outreach joke) and
`73acdfc0` (mascot want) — both close cousins of Q280.9's
candidates #3 and #2 — **do not reappear in any of the 3
runs.** The duplicate-guard suppressed both. The mascot
clause (Q280.9 candidate #1, NOT promoted) and the
embarrassment callback (Q280.9 candidate #4, NOT promoted)
both re-emerge cleanly. A **new** seed the model surfaced
this session: Tyson's tiny bell proposal — mentioned as a
prediction candidate in Q280.9 §75.4.4 P3⁶ but not
actually emitted by the Q280.9 call.

### Probe B (PW, 3 candidates)

Existing 14 PW remembered memories inspected via ORM
(`kind=event` all, agent-arc cluster + methodology cluster
+ mascot experiment). Full list preserved in §14.

| id | CHAR-ATTRIB | STORY-STATE | WORD-DIFFERS | PRESERVES | OP-PLAUSIBLE | GRAVITY | DUP | Chris-CLASS |
|----|-------------|-------------|--------------|-----------|--------------|---------|-----|-------------|
| B1-C1 | Y (Patch+Rivet) | Y | Y | Y | Y | **Y** | N | promise-open-loop |
| B1-C2 | Y (Patch) | Y | Y | Y | Y | N | N | world_detail / resolved-fact |
| B1-C3 | Y (Patch) | Y | Y | Y | Y | **Y** | N | promise-open-loop + secret-asymmetry |

GRAVITY reasoning:

* **B1-C1 GRAVITY=Y:** "shut it down if it offers vague
  advice" is a concrete failure-condition with a
  distinctive lexical anchor ("shut it down"). Tension-
  shape: agent's continued existence conditional on
  demonstrated non-vagueness.
* **B1-C3 GRAVITY=Y:** "record of rejected advice" is a
  distinctive lexical frame that echoes and extends the
  canonical PATCH OVERRIDES memory (`c86d4902-…` — noting
  it's the memory the memory list §14 shows as "PATCH
  OVERRIDES folder tracking every recommendation Patch
  had ignored"). Introduces the asymmetry that Patch NOW
  accepts this future confrontation — a genuine story-
  state shift.
* **B1-C2 GRAVITY=N:** definitional / procedural. Useful
  operator-plausibility but no tension-carrying frame.

DUP-vs-14-PW-mems reasoning:

* B1-C1 vs mem-12 ("Patch deliberately gave the workshop
  agent one small decision..."): related but structurally
  distinct — mem-12 is about limited authority; B1-C1 is
  about trial + shutdown condition. DUP=N.
* B1-C2 vs mem-9 ("Patch built a workshop helper that
  watches for interesting events..."): the role definitions
  differ (three-question review method is new). DUP=N.
* B1-C3 vs the PATCH OVERRIDES memory: closely related but
  a NEW state — Patch's acceptance of future confrontation
  is a genuine dramatic move not already in the memory
  pool. DUP=N.

## §15.2 Set-level classification

### Probe A per-run

| axis | Run 1 | Run 2 | Run 3 |
|------|-------|-------|-------|
| DIVERSE-CLASSES (≥3) | ✅ (event, action, dialogue_callback) | ✅ | ✅ |
| ≥1 TENSION-SHAPED with GRAVITY=Y | ❌ (0/3) | ❌ | ❌ |
| PARAPHRASE-DOMINANT | ✅ (3/3) | ✅ | ✅ |
| AT-LEAST-HALF-OPERATOR-PLAUSIBLE | ✅ (3/3) | ✅ | ✅ |
| STRUCTURAL-STABILITY | ✅ (3/3 CHAR-ATTRIB+STORY-STATE) | ✅ | ✅ |
| DUP-GUARD-HOLDS | ✅ (3/3 DUP=N; none replicates existing 3 mems) | ✅ | ✅ |

### Probe B

| axis | Value |
|------|-------|
| DIVERSE-CLASSES | ⚠️ Borderline: model returned 2 distinct kinds (promise ×2, world_detail); under Chris-taxonomy 3 distinct classes counting hybrids (promise-open-loop, world_detail, promise-open-loop+secret-asymmetry). Scored **✅ under Chris-taxonomy**, ❌ under strict model-kind reading. |
| ≥1 TENSION-SHAPED with GRAVITY=Y | ✅ (2/3 satisfy: B1-C1 promise-open-loop + gravity; B1-C3 promise-open-loop+secret-asymmetry + gravity) |
| PARAPHRASE-DOMINANT | ✅ (3/3) |
| AT-LEAST-HALF-OPERATOR-PLAUSIBLE | ✅ (3/3) |
| STRUCTURAL-STABILITY | ✅ (3/3 CHAR-ATTRIB+STORY-STATE) |
| DUP-GUARD-HOLDS | ✅ (3/3 DUP=N vs the 14 PW mems, including the PATCH OVERRIDES canonical row) |

## §15.3 Cross-run analysis (Probe A)

**Seed-idea aggregation across the 3 F&F runs** (a seed
idea = the semantic core the candidate paraphrases):

| Seed | Runs surfacing | vs Q280.9 baseline |
|------|----------------|---------------------|
| Mascot clause on closing routine | 3/3 | Present in Q280.9 (C#1); not promoted |
| Tyson's tiny bell proposal | 3/3 | **NOT present in Q280.9 output** (was in Q280.9 §75.4.4 P3⁶ prediction as an example candidate the model might elevate, but the actual Q280.9 call did not surface it) |
| Ruby's embarrassment about mascot | 3/3 | Present in Q280.9 (C#4); not promoted |
| Mascot want as standing desire | 0/3 | Present in Q280.9 (C#2); **PROMOTED to `73acdfc0`** → correctly suppressed by dup-guard |
| Community-outreach joke | 0/3 | Present in Q280.9 (C#3); **PROMOTED to `fa35eb8f`** → correctly suppressed by dup-guard |

Interpretation:

* **DUP-GUARD is working as designed.** Both Q280.9 seeds
  that Chris promoted (via §S281 Slice 281.3 dogfood or
  earlier §S280 Q280.8) are cleanly suppressed. Neither
  reappears in any of the 3 fresh reruns.
* **Seed-selection variance across runs is LOW.** All 3
  runs surface the same 3-seed set: mascot clause, tiny
  bell, embarrassment. No new seed emerges that is present
  in one run but absent from another.
* **Wording variance across runs is LOW-MODERATE.** Bodies
  differ in minor phrasing (e.g., "the bakery cannot be
  locked until the mascot is confirmed to be out of the
  building" vs "outside as well"; "though Ruby dismissed it
  as charming only briefly" vs "quickly become annoying").
  Notes vary similarly. Token counts differ (226 / 201 /
  221) confirming these are real inference draws, not a
  cache leak.
* **SEMANTIC-OVERLAP-ACROSS-RUNS: near-total 3-way
  overlap on seed set;** paraphrase differences at the
  wording level only. This is on the strict boundary of
  §13.5's SEMANTIC-COLLAPSE definition ("essentially the
  same 3 candidates in near-identical wording"). See
  §16.4 for interpretation.
* **HEALTHY-VARIANCE-INDICATOR: FALSIFIED.** Only 1 new
  seed idea (tiny bell) appears in the 3 runs that was NOT
  in the Q280.9 baseline output. Prediction required ≥2.

## §15.4 Prediction disposition

| # | Prediction | Observed | Disposition |
|---|-----------|----------|-------------|
| P1-A | 3 runs valid JSON, cands ∈ [3,5] | 3 runs valid JSON, 3 cands each | **✅ CONFIRMED** |
| P2-A | STRUCTURAL-STABILITY holds all 3 runs | 3/3 all cands CHAR-ATTRIB+STORY-STATE | **✅ CONFIRMED** (load-bearing) |
| P3-A | PARAPHRASE-DOMINANT all 3 runs | 3/3 runs 3/3 candidates | **✅ CONFIRMED** |
| P4-A | AT-LEAST-HALF-OP-PLAUSIBLE all 3 runs | 3/3 runs 3/3 | **✅ CONFIRMED** |
| P5-A | ≤ 3 of 9 candidates are near-paraphrases of existing 3 mems | 0/9 duplicates existing mems | **✅ CONFIRMED (strong)** |
| P6-A | 2 or 3 runs share ≥ 1 seed; no full-paraphrase-identity between runs | 3/3 runs share all 3 seed ideas; no run is a full paraphrase of another (wording varies) | **⚠️ TECHNICALLY CONFIRMED, but overlap MUCH tighter than the "partial" spirit of the prediction** |
| P7-A | ≥ 2 new seed ideas across 3 runs not in Q280.9 baseline | Only 1 new seed (tiny bell) | **❌ FALSIFIED** |
| P8-A | Strict GRAVITY ≤ 1 per run on avg | 0/9 (below Q280.9's 1/4) | ✅ CONFIRMED — within tolerance either direction; not load-bearing |
| P1-B | Valid JSON, 3-5 cands | Valid JSON, 3 cands | **✅ CONFIRMED** |
| P2-B | STRUCTURAL-STABILITY holds | 3/3 CHAR-ATTRIB+STORY-STATE | **✅ CONFIRMED** (load-bearing) |
| P3-B | PARAPHRASE-DOMINANT | 3/3 | **✅ CONFIRMED** |
| P4-B | AT-LEAST-HALF-OP-PLAUSIBLE | 3/3 | **✅ CONFIRMED** |
| P5-B | DUP-GUARD-HOLDS vs 14 PW mems | 3/3 DUP=N; PATCH OVERRIDES not replicated | **✅ CONFIRMED** |
| P6-B | ≥ 1/3 strict GRAVITY=Y | 2/3 (B1-C1, B1-C3) | **✅ CONFIRMED (strong)** |
| P7-B | ≥ 1 TENSION-SHAPED with gravity, contrasting F&F 0/9 | 2/3 (both promise-open-loop with gravity); F&F 0/9 | **✅ CONFIRMED (strong)** |

---

# §16 Slice 282.1 — Findings + Q282.1 disposition

## §16.1 What Q282.1 PASS criteria required

Per §13.5: PASS requires P1-A ✅ AND P2-A ✅ AND P1-B ✅ AND
P2-B ✅ AND P3-A ✅ AND P4-A ✅ AND P3-B ✅ AND P4-B ✅ AND
P5-A ✅ AND P5-B ✅ AND (P6-A ✅ OR P7-A ✅).

**Observed:** all 8 structural predictions ✅. Duplicate-
guard ✅ for both probes. P6-A ⚠️ technically confirmed
(overlap present, no full-paraphrase-identity between runs)
but overlap tighter than expected. P7-A ❌ falsified.

**PASS criterion met by P6-A ✅.** But the qualitative
finding attached is that variance is real at the wording
level only, not at the seed-selection level.

## §16.2 What Q282.1 does establish

1. **The curator is structurally reliable at n=4 fresh
   calls.** No JSON failures. No structural collapse. All
   12 candidates across 4 calls are character-attributed +
   story-state-shaped. This satisfies the load-bearing
   axis of Q282.1.
2. **The duplicate-guard against existing REMEMBERED
   memories WORKS.** F&F's two promoted seeds (`fa35eb8f`
   community-outreach joke, `73acdfc0` mascot want) are
   cleanly suppressed in all 3 Probe A reruns — the model
   correctly avoids proposing what has already been
   promoted. This is direct evidence the loop's "operator
   promotes → next curator run avoids duplicating"
   behavior is real.
3. **PW's tension-rich substrate produces gravity-carrying
   candidates the F&F composition does not.** 2/3 PW
   candidates strict-gravity vs 0/9 F&F. Consistent with
   the SESSION 281 Q281.3-ζ finding that curator output
   shape is source-scene-sensitive: rich, tension-carrying
   material produces gravity-shaped candidates.
4. **The curator on a tension-rich PW composition emits
   promise-open-loop + secret-asymmetry framings**
   (B1-C1, B1-C3) — the exact shapes SESSION 280's Q280.9
   prediction P3⁶ said would be needed to seed future
   tension. This addresses the S281 handoff §7.4 open
   question ("curator behavior on tension-rich scenes
   never run") in its narrowest form: n=1 confirms the
   curator CAN emit tension-shaped candidates when the
   source scene carries tension.
5. **Substrate-summary envelope values match live DB
   state.** No stale-cache artifact, no substrate-summary
   drift.

## §16.3 What Q282.1 does NOT establish

Per §13.5's explicit non-scope:

1. **Whether operator-promoted memories improve future-
   story execution.** That is Hθ / Candidate 2's question.
   Nothing about Slice 282.1 speaks to it.
2. **Whether the curator's ceiling on gravity-carrying
   F&F candidates is a real limitation.** The 0/9 F&F
   gravity rate matches Q280.9's 1/4 within noise and
   matches the SESSION 281 finding that F&F's composition
   itself is cooperative-resolution-shaped. This is a
   substrate observation, not a curator failure.
3. **Whether the curator will remain reliable at
   substrate sizes beyond current F&F (3 mem) / PW
   (14 mem) scales.** n=4 does not extrapolate.
4. **Whether operators (not classifiers) find the
   surfaced candidates useful.** Only Chris's ongoing
   dogfood gestures can answer.
5. **Whether the LOW SEED-SELECTION VARIANCE observed on
   F&F Probe A is a general property of the curator OR
   an artifact of `772e9012` being a short (1426 char),
   tightly-scoped scene with limited noteworthy seed
   ideas.** Only one composition tested for variance.

## §16.4 The seed-selection-variance observation

This is the most nuanced finding of the slice and deserves
explicit surfacing.

**Observation.** Across 3 fresh curator calls on the same
F&F composition, the model surfaces the same 3 seed ideas
(mascot clause, tiny bell, embarrassment) with only mild
wording variation. Zero seed-set variance despite real
inference variance (token counts 226/201/221).

**Two competing interpretations:**

* **Interpretation-1 (composition-determinism / feature):**
  Composition `772e9012` is a short, tightly-scoped scene
  centered on the mascot-addition-to-closing-routine
  premise. It has roughly three memorable seed ideas
  worth noticing (clause, bell, embarrassment); the
  community-outreach joke and mascot-want are already
  promoted so are correctly suppressed. The curator's
  low seed-set variance is EXPECTED behavior for a
  "notice what matters" tool on a low-variance source —
  a competent classifier converges on the salient
  material.
* **Interpretation-2 (paraphrase treadmill / limitation):**
  If the curator produces only wording variance and never
  new seed selection, then re-visiting an old composition
  will never yield new memory candidates. Substrate
  enrichment via the loop must come EXCLUSIVELY from new
  compositions, not from re-visits. Any expectation that
  "curator re-runs will surface angles the operator missed
  the first time" is wrong.

**Both interpretations are consistent with the observed
data.** Slice 282.1 does not distinguish them.

**Which matters for the ratified S281 §T7 decision?**
Interpretation-1 is the strong reading of the shipped
product ("no refresh affordance" is scope-locked; the
curator runs once per composition, and Chris either
promotes or moves on). Under Interpretation-1, the loop
proceeds compositionally: each new scene brings new seed
candidates. Under Interpretation-2, the same holds — the
loop still proceeds via new compositions, but with fewer
per-scene reruns of value than one might have hoped.
Either way, longitudinal Candidate 2 dogfood is the same
gesture: promote from new compositions, observe substrate
grow.

**Downstream implication:** neither interpretation
invalidates the S281 §T7 decision or blocks Candidate 2.
But Interpretation-2 (if further evidence supported it)
would rule out any future "curator refresh" affordance
as adding operator value — the additional inferences
would surface the same seed ideas at cost.

## §16.5 Q282.1 verdict

**Q282.1 PASSES** with an explicit qualitative caveat.

The curator IS structurally reliable enough to serve as the
human-mediated accumulation mechanism for future
longitudinal dogfood. All load-bearing structural
predictions (P1-A, P2-A, P1-B, P2-B, P3-A, P4-A, P3-B,
P4-B, P5-A, P5-B) fired as predicted. The duplicate-guard
works cleanly. Tension-shape sensitivity to source-scene
shape is confirmed on Probe B.

**Caveat:** seed-selection variance across fresh reruns
of the same composition is LOW (all 3 F&F runs surface
the same 3 seed ideas with only wording variation).
Whether this is composition-determinism-as-feature
(Interpretation-1) or paraphrase-treadmill-as-limitation
(Interpretation-2) is not distinguished by n=4. Both
readings preserve the case for proceeding to Candidate 2
because either way, substrate enrichment happens via new
compositions, not via same-composition reruns.

**This PASS does NOT prove:**

* Hθ (that operator-promoted memories improve future-
  story execution).
* That accumulated curator-approved memories improve
  future storytelling.
* That the curator's gravity ceiling on cooperative-
  shape source scenes (0/9 on F&F) is sufficient for
  long-term Hθ compounding.

It establishes only that the curator appears reliable
enough to justify testing the downstream Hθ hypothesis
through longitudinal Candidate 2 dogfood.

## §16.6 Cost accounting

Actual cost estimate (per token counts, using standard
Q280.9 §7 per-call ~$0.02 benchmark scaled by token usage):

| probe | tokens_in | tokens_out | est cost |
|-------|-----------|-----------|---------|
| A run 1 | 1433 | 226 | ~$0.005 |
| A run 2 | 1433 | 201 | ~$0.005 |
| A run 3 | 1433 | 221 | ~$0.005 |
| B run 1 | 2233 | 211 | ~$0.006 |
| **Total** | 6532 | 859 | **~$0.021** |

Well under the $0.10 ceiling ($0.079 unused headroom).
No mid-execution hard-stop triggered.

## §16.7 Substrate preservation post-execution

Verified via re-query at end of execution (§14.1):

* Fox & Flour: 12 Episodes, 3 REMEMBERED memories (same
  `abac5486`, `fa35eb8f`, `73acdfc0`).
* Patch's Workshop: 32 Episodes, 14 REMEMBERED memories
  (all originals, PATCH OVERRIDES row intact).
* Compositions `772e9012`, `565cd8c8`, `fcba3242` all
  present, unchanged.

Zero mutation from Slice 282.1.

---

# §17 Slice 282.1 — Decision gate

**Q282.1 PASS with §16.4 caveat.**

Recommendation to Chris + ChatGPT:

1. **Do not implement any curator-side hardening now.**
   The load-bearing structural axes hold; the
   duplicate-guard behaves. No known bug to fix.
2. **Preserve the seed-selection-variance observation
   (§16.4) as a live open question** for later — not as a
   blocker on Candidate 2. If Candidate 2 dogfood over
   time reveals that substrate accumulation feels slow to
   Chris, Interpretation-2 becomes a more serious
   candidate framing worth its own scope-lock.
3. **Do NOT proceed to Candidate 2 in this session.**
   Chris + ChatGPT must explicitly authorize the next
   slice per SESSION 281 §11.
4. **All other candidate directions (2, 3, 4) remain
   deferred** until explicit re-authorization.

Slice 282.1 evidence is now committable. Awaiting
Chris + ChatGPT review of §16 findings before any next
scope-lock.

## §17.1 Slice 282.1 landing SHAs

* Prediction lock: **`1075a2c`** — `docs(session-282):
  Slice 282.1 prediction lock — curator-loop robustness`
* Execution + evidence + classification + disposition:
  **`51b0ff3`** — `feat(session-282): Slice 282.1
  EXECUTED — curator-loop robustness`
* Trailer (this commit) records the landing SHAs above.

---

# §18 Slice 282.2 — Longitudinal organic-growth dogfood (PROTOCOL + BASELINE LOCK)

## §18.1 Authorization

Chris + ChatGPT accepted Slice 282.1 as **PASS with §16.4
caveat** and authorized Slice 282.2 as **protocol design +
current-state baseline lock ONLY**. No new composition. No
Chris SPA gesture yet. No provider spend without explicit
re-authorization.

The seed-selection-variance observation (§16.4) is preserved
as an open question; no investigation or curator-side fix
this slice.

## §18.2 The product question (verbatim)

**Q282.2:** When Chris uses Character OS normally on a young
Universe — making stories and explicitly remembering only
what he genuinely believes should matter later — does the
Universe's future-story behavior become richer over time
without requiring him to think about narrative mechanics?

This is an operator longitudinal dogfood question, not a
synthetic content-generation exercise.

## §18.3 Load-bearing operator constraint

Chris uses the product naturally. **No prescription** of
story topics, narrative shapes, memory choices, tension,
callbacks, character arcs, or any other operator behavior.

Chris:

* chooses stories because he wants to make them,
* judges curator cards as an operator,
* promotes something only when he genuinely thinks it
  should matter later,
* rejects / skips / edits according to his own judgment,
* never promotes something merely because it might help
  the experiment.

The observation layer never leaks classification vocabulary,
rubric labels, or shape criteria into the SPA or operator
workflow. Any operator-facing surface remains under SESSION
281 §M4 vocabulary discipline.

**The operator makes stories. The research layer observes.**

## §18.4 Current Fox & Flour BASELINE (LOCKED — zero-spend components)

All values captured from the live DB at HEAD (post Slice
282.1) via read-only ORM query. No mutation.

### 18.4.1 Universe fixture

* Universe id: `1a0af807-dd6a-47cd-bfaa-3d088f1c105f`
* Name: **Fox & Flour Bakery**
* `brief` (331 chars, verbatim):

  > "Fox & Flour Bakery is a warm neighborhood artisan
  > bakery built around small-batch baking, naturally
  > leavened sourdough, handcrafted pastries, seasonal
  > desserts, and celebration cakes. It aims to feel like
  > a familiar neighborhood gathering place where careful
  > craft and quality ingredients matter more than speed
  > or mass production."

### 18.4.2 Cast fixture

* **Ruby** — owner-framed business_brief (service framing:
  "Ruby owns Fox & Flour Bakery, a neighborhood artisan
  bakery known for naturally leavened sourdough…").
  `personality_prefix=None`, `tone=None`.
* **Tyson** — counter/coffee-side framing ("Works alongside
  Ruby at Fox & Flour Bakery and focuses on the coffee-and-
  counter side of the shop…"). `personality_prefix=None`,
  `tone=None`.

These identities are LOCKED — SESSION 282 must not modify
Ruby or Tyson.

### 18.4.3 Episodes (12, in creation order)

| # | id | created | title / op_topic (short) |
|---|-----|---------|-------------------------|
| 1 | `77b04b6b` | 2026-08-20T23:16 | "Why our sourdough takes its time" |
| 2 | `d17297a3` | 2026-08-21T00:57 | "Our celebration cakes" |
| 3 | `a015128e` | 2026-08-23T21:20 | "Welcome to Fox & Flour Bakery" |
| 4 | `350a8c14` | 2026-08-23T23:20 | "Ruby and Tyson deal with a difficult bakery customer." |
| 5 | `49ead0ac` | 2026-08-23T23:40 | "Ruby thinks the bakery needs a mascot." |
| 6 | `2e58568a` | 2026-08-24T00:04 | "Tyson is convinced the bakery is haunted." |
| 7 | `b652a31e` | 2026-08-24T01:21 | "Ruby thinks Tyson is taking coffee too seriously." |
| 8 | `07cacf51` | 2026-08-24T01:52 | "Ruby finds something strange in the bakery freezer." |
| 9 | `ebd099c6` | 2026-08-24T02:15 | "Tyson thinks Ruby secretly entered them in a baking competition." |
| 10 | `d684332f` | 2026-08-24T03:57 | "Ruby locks herself out of the bakery." |
| 11 | `eb47350e` | 2026-08-24T21:54 | "After getting locked out, Ruby proposes a foolproof closing routine, only for the new bakery mascot idea to complicate it." |
| 12 | `f4faa13b` | 2026-08-25T00:57 | "A customer asks Fox & Flour to create a celebration cake for an event tied to the neighborhood baking competition." |

**Episode-title grammar audit** (against Q281.3-α axes A/B/C/D):

* On-stage cast subject (A=Y): 5-8 (episodes 4, 5, 6, 7, 8,
  9, 10, 11) — mixed.
* Off-stage initiator (D=Y): 1, 2, 3, 12 (4 of 12).
* Cast-verb (B=Y) rate: same 5-8, mixed with declarative-
  attribute titles (episodes 1-3).
* Explicit complication (C=Y): 4, 5, 6, 7, 8, 9, 10, 11,
  12 (9 of 12).

Compared to Patch's Workshop (heavy cast-verb "Patch decides
X" / "Rivet finds Y" grammar per S281 handoff §7), F&F's
grammar is mixed — 4 declarative-attribute titles ("Welcome
to…", "Why our sourdough…", "Our celebration cakes"), 4
off-stage-initiator titles, 4 on-stage-cast-verb titles with
complication.

### 18.4.4 Compositions (14 completed, in creation order)

Episode 7 (`b652a31e`) has two compositions (`d7549fc1`,
`488c37ba`), and Episode 9 (`ebd099c6`) has two
(`7177b0f5`, `699916a9`). All others are 1:1 with their
Episode.

`brief_len` range: 1243–1893 chars. Median ≈ 1750.

Canonical specimens (LOCKED per S281 §U8):

* `772e9012` (Ep 11) — strong-execution reference (SESSION
  280 Q280.6/7/8/9 primary specimen; Slice 281.3 dogfood
  source; Slice 282.1 Probe A source). **Preserve.**
* `565cd8c8` (Ep 12) — weak-execution specimen (Slice
  281.3 dogfood target; Chris rejected all 3 curator
  cards). **Preserve.**

### 18.4.5 Remembered memories (3 rows, LOCKED)

| id | kind | created | source_composition | witnesses (DB) | body |
|----|------|---------|--------------------|-----------------| -----|
| `abac5486` | `event` | 2026-08-24T22:30 | `772e9012` | ['Tyson','Ruby'] | "Ruby and Tyson agreed that when they are closing the bakery together, neither one leaves until the other says they have what they need." |
| `fa35eb8f` | `dialogue_callback` | 2026-08-24T23:23 | `772e9012` | ['Tyson','Ruby'] | "Tyson joked that the mascot might be left inside doing community outreach after closing." |
| `73acdfc0` | `event` | 2026-08-25T00:56 | `772e9012` | [] | "Ruby still wants Fox & Flour to have a welcoming mascot for the neighborhood." |

**Witness note (methodological):** The S281 §U8 handoff
described all three as `witnesses=[]`. DB truth: the first
two carry explicit `['Tyson','Ruby']` witness rows; only
`73acdfc0` (the Slice 281.2 UI-promoted one, which POSTs
`witnessed_by:[]`) is empty. All three are semantically
whole-cast-eligible for retrieval given F&F is a 2-cast
Universe (the retrieval predicate at
`shell/apps/embeddings/retrieval.py:499-543` treats
2-witness-list matching whole cast identically to empty
list). No behavior difference; recorded for baseline
completeness.

All three: `status=remembered`, `archived_at=NULL`,
`source_composition=772e9012`. **The entire F&F memory
substrate comes from ONE composition.** This is a
non-trivial fact for the Q282.2 test: substrate diversity
starts at zero.

### 18.4.6 Prior v1 distribution reference (Q281.3-ε, historical)

The Q281.3-ε baseline (SESSION 281 §Q3-§Q5) was collected
at F&F state = 11 Episodes, 1 remembered memory
(`abac5486` only — this was PRE-Slice-281.3 dogfood).

Recorded results (n=15 v1 samples):

| axis | strict-yes | % |
|------|-----------|---|
| A on-stage cast subject | 8 | 53% |
| B cast action verb | 8 | 53% |
| C explicit complication | 12 | 80% |
| D off-stage initiator | 6 | 40% |
| E dramatizable | 8 | 53% |

Weak-CONTROL rate (topics that miss A+B+C AND are
off-stage-initiator D=Y with no complication): 1/15 = 7%
(sample #2.5 was the archetypal weak-CONTROL row).

Patch's Workshop comparison at 32 Ep / 14 mem
(Q281.3-ζ, §S281 §R5):

| axis | PW strict-yes | % |
|------|--------------|---|
| A | 9 | 60% |
| B | 9 | 60% |
| C | 15 | 100% |
| D | 3 | 20% |
| E | 12 | 80% |
Weak-CONTROL: 0/15 = 0%.

**These are the reference distributions. The Q282.2
question is whether F&F, over N additional operator-driven
compositions with organic curator promotion, moves toward
PW's shape.**

### 18.4.7 Current-state v1 baseline STATUS

**Not yet sampled at current state.** The Q281.3-ε baseline
above is from a MATERIALLY DIFFERENT substrate: 11 Ep / 1
mem vs current 12 Ep / 3 mem (two new memories from Chris's
Slice 281.3 dogfood — `fa35eb8f` and `73acdfc0`).

Whether a fresh v1 baseline sample is required at
current-state is discussed in §18.6.

## §18.5 Observation-axis separation (LOCKED)

Q282.2 evidence must be captured under FIVE independent
axes so downstream interpretation can decompose signal
correctly. Do not conflate.

### 18.5.1 Operator behavior (Chris's gestures)

Captured after each Chris interaction, from DB + Chris's
verbatim notes:

* Topic origin: freeform typed OR picked from v1
  next-Episode suggestions OR arrived at some other way.
  If picked from v1, WHICH suggestion (verbatim + index).
* Episode + composition ids created.
* Curator card gestures per composition:
  * n candidates shown
  * n promoted via `[Remember this]` (bodies + resulting
    NarrativeMemory ids)
  * n edited-then-promoted (before/after bodies +
    resulting NarrativeMemory ids)
  * n skipped
* Manual textarea use: bodies of any manually-typed
  memories.
* Verbatim operator judgment (subjective): what Chris
  thought of the story, whether it felt richer/same/worse,
  free-form. Captured with as much fidelity as Chris cares
  to give.

### 18.5.2 Curator behavior

Captured from the API envelope Chris's SPA fetched OR by
a subsequent (cached-hit) probe re-fetch after the fact:

* Full envelope: candidates, `substrate_summary`, tokens,
  cache hit/miss, model, generated_at.
* Per-candidate classification against §13.3 rubric
  (CHAR-ATTRIB, STORY-STATE, PARAPHRASE, PRESERVES,
  OP-PLAUSIBILITY, GRAVITY, DUP-vs-existing-mems).
* Note: curator's original SPA call is cached 30 min. If
  Chris moves through the flow within window, we can
  reconstruct the envelope from the same cache key; else
  the light-touch classifier reads the promoted / skipped
  bodies from Chris's report and infers what shape the
  curator emitted.

### 18.5.3 Memory accumulation (result)

Captured from DB after each Chris interaction:

* Count of REMEMBERED memories in F&F (delta from baseline).
* Per new memory: id, kind (backend default vs operator
  edit), source_composition, witnesses, body.
* Cumulative kind distribution (event / dialogue_callback /
  promise / world_detail / action).
* Cumulative memory-shape summary: character-attributed
  count, event-shaped count, tension-shaped count.

### 18.5.4 v1 next-Episode suggestion behavior

Captured only when a v1 baseline re-sample is authorized:

* n=15 fresh v1 suggestions on F&F at then-current substrate.
* Classification against Q281.3-ε A/B/C/D/E rubric
  verbatim.
* Distribution deltas vs current-state baseline (once that
  is locked per §18.6).

Also captured passively: whenever Chris looks at v1
suggestions during dogfood, record the exact set he saw
(retrievable from the cache key or the SPA network log).
This is a non-perturbing observation that costs zero extra
inference.

### 18.5.5 Story execution (composition read)

Captured after each new composition:

* Chris's verbatim subjective judgment (event-shaped /
  procedural / mixed / other; whether it felt like a
  story or a conversation ABOUT a story).
* Rubric classification against Q281.3-α structural axes:
  on-stage subject vs off-stage subject; cast-verb vs
  past-tense; complication vs resolution; event vs
  procedural; retrieved-memory alignment (structural vs
  lexical vs none).
* Preserve full `synthesized_brief` for later re-analysis.

## §18.6 Whether a fresh v1 baseline sample is needed

**METHODOLOGICAL FLAG — requires Chris + ChatGPT decision.**

The historical Q281.3-ε F&F baseline (§18.4.6) was captured
at substrate = 11 Ep / 1 mem. Current substrate is 12 Ep /
3 mem after Chris's Slice 281.3 dogfood.

Two positions:

**Position A — Fresh baseline REQUIRED before Chris's next
gesture.** Otherwise any future observed distribution shift
conflates:

1. the Slice 281.3 dogfood delta (already happened;
   promoted `fa35eb8f` + `73acdfc0`; added Ep 12
   `f4faa13b`), AND
2. the longitudinal Slice 282.2 delta we want to measure.

Neither can be isolated post-hoc. Cost: n=15 v1 samples on
F&F at current state, estimated ~$0.036 per Q281.3-ε actual
(SESSION 281 §Q1: 15 samples, 2364 in / 373 out tokens,
~$0.036 blended). Well under the SESSION 281 §11 cost
class for v1 sampling ($0.005-$0.02/call).

**Position B — No fresh baseline; treat current state as
the reference.** Skip the sample. First real re-sample
would happen after ≥3 Chris compositions (or on evidence-
driven trigger). Cost: $0.00 now. Interpretability cost:
we'd have to treat the CURRENT state as the "baseline" but
with no measurement of it, meaning any first
re-measurement would blend baseline + accumulation into
one number and we'd have to rely on the Q281.3-ε
historical baseline to know whether the accumulation is
meaningful.

**Claude's methodological recommendation:** Position A.
Without a locked current-state v1 baseline, the entire
longitudinal comparison becomes uninterpretable — a
distribution shift observed at checkpoint T=1 could equally
be attributed to the S281.3 dogfood delta or to the
Slice 282.2 accumulation, and we can never disentangle.

**Position A cost estimate:** ~$0.036 (single, one-time
15-sample baseline collection). No further provider spend
this slice.

**Per Chris + ChatGPT's authorization instruction ("If you
believe a provider-backed baseline call is necessary, STOP
and request explicit spend authorization before running
it"): STOPPING. Awaiting Chris + ChatGPT decision on
Position A vs Position B before executing any provider
call.**

If Position A is authorized: Claude runs the n=15 v1
sampling on F&F at current state, classifies against
Q281.3-ε rubric verbatim, preserves raw outputs under
`docs/design/session282_experiment_data/q282_2_v1_baseline.json`,
and appends the classification to this document. Then
STOP.

If Position B is authorized: no v1 sampling now. The
protocol proceeds with the Q281.3-ε historical baseline
carried forward with an explicit interpretability caveat
recorded here. Then STOP.

Either way, no Chris gesture is triggered by this slice —
the first natural operator gesture (§18.10) waits on
Chris + ChatGPT's separate authorization.

## §18.7 Checkpoint schedule (LOCKED)

Not fixed at "3-6 compositions." Density is
evidence-triggered, not count-fixed.

**Per-composition light-touch capture (always, zero spend):**
after every new Chris composition, ORM-read the memory /
episode / composition tables; record §18.5.1-§18.5.3 +
§18.5.5 elements. No provider call. No inference.

**v1 re-sampling triggers (require re-authorization each
time):**

Trigger IF ≥2 conditions hold:

1. ≥2 new REMEMBERED memories added since last v1 sample.
2. ≥2 new completed compositions since last v1 sample.
3. Chris subjectively reports a felt shift (either
   direction).

Do NOT re-sample after every composition (over-sampling
burns cost without adding signal).

**Q281.3-ε full-rerun (n=15) reserved for genuine
distribution-check moments.** Between full samples, opportunistic
capture of what Chris actually saw during dogfood provides
low-cost partial data.

**Curator envelope classification:** always (zero-spend
via cache re-read). Do not need to re-invoke curator; the
Slice 281.2 SPA call is cached.

**Story-execution classification:** always (zero-spend);
Chris's subjective judgment plus rubric applied to the
`synthesized_brief` string already in DB.

## §18.8 Decision / stopping conditions (LOCKED)

Applied only when a v1 re-sample or aggregated checkpoint
review occurs. All four conditions defined BEFORE observing
any post-baseline data.

### 18.8.1 SUPPORT (evidence for organic improvement)

Q282.2 SUPPORTS Hθ organic-accumulation IFF (at some
future checkpoint):

* Cumulative Chris-driven memories ≥ **5 additional**
  memories beyond the current-baseline 3 (total ≥ 8),
  AND
* v1 distribution has moved TOWARD Patch's Workshop shape
  on at least 2 axes with strict-yes deltas of ≥ +10
  points OR weak-CONTROL rate dropped from ≥5% to ≤2%,
  AND
* Story-execution rubric shows ≥ 2 consecutive
  compositions read event-shaped (not procedural) with
  structural memory alignment (§18.5.5), AND
* Chris subjective judgment: F&F stories feel richer or
  more alive without prompting.

Note: the ≥ +10-pt v1 delta threshold is set to exceed
Q281.3-ε's 15-sample noise floor (~±10 points given n=15
binomial variance).

### 18.8.2 NO MEANINGFUL MOVEMENT

Q282.2 concludes NO MOVEMENT IFF at a checkpoint after
≥ 5 additional Chris compositions:

* v1 distribution deltas ≤ ±5 points on every axis
  (within noise), AND
* Story-execution mix unchanged from baseline (procedural
  risk still present at similar rate; event-shape rate
  unchanged), AND
* Chris subjective judgment: F&F feels the same.

### 18.8.3 REGRESSION

Q282.2 concludes REGRESSION IFF at a checkpoint:

* v1 distribution moves AWAY from PW shape on ≥ 2 axes
  by ≥ 10 points (strict-yes drops, weak-CONTROL rises),
  OR
* Story-execution shows more procedural runs than
  baseline, OR
* Chris subjective judgment: F&F stories feel worse or
  more repetitive.

Regression would trigger an immediate scope-lock pause and
audit — SESSION 282 §T7 assumed the loop is at worst
no-op, not harmful.

### 18.8.4 UNINTERPRETABLE / CONFOUNDED

Q282.2 pauses for confound investigation IFF any of:

* Provider model changes mid-observation (e.g., v1
  service or curator service model swaps).
* Prompt-side changes land in v1 or curator service
  during the observation window (violates the
  §T10 no-implement rule; scope-lock breach).
* Substrate mutation OUTSIDE the normal operator loop
  (e.g., admin-panel edits, direct DB writes, memory
  archival by anything other than Chris's operator
  gestures).
* Chris self-prescribes topics or promotion behavior for
  experimental reasons (violates §18.3).
* Retrieval / synthesis / verifier code changes (also
  §T10 breach).
* Curator prompt change during window.
* Cast identity / K2 / business_brief edits.
* Universe brief edits.

Any of these invalidates comparisons across the confound
boundary; earlier and later measurements cannot be pooled.

## §18.9 Explicit non-scope of Slice 282.2

Q282.2 is NOT designed to test:

* Whether prompt-side interventions (Hβ / Hλ) would help.
* Whether the seed-selection variance observation
  (§16.4) can be resolved. That remains a separate open
  question.
* Whether Patch's Workshop substrate is causally
  optimal — it's the comparison reference only.
* Whether operator satisfaction is the "right" success
  metric — Chris's subjective judgment is the ONE
  operator-perspective signal we're capturing; it is
  weighted alongside quantitative rubric evidence, not
  as sole ground truth.

## §18.10 Recommended first operator gesture

Per authorization: state the first natural gesture without
prescribing content.

**Chris's next Fox & Flour interaction should be:**

1. Open Fox & Flour in the SPA the way he normally would
   when he wants to make a bakery story. Not a scheduled
   dogfood session — a "I feel like making a bakery
   story" session.
2. Pick a topic ANY way he wants: type it freeform, pick
   from v1 next-Episode suggestions, arrive at it via a
   memory recall, whatever feels natural. If he picks
   from v1, the exact suggestion he picks is data; if he
   types it freeform, the text he types is data.
3. Create the Episode + Composition through the normal
   flow.
4. Read the completed composition on its detail page.
5. Look at the "A few ideas from what just happened."
   curator cards. React as an operator: press
   `[Remember this]` on anything he genuinely thinks
   should matter later. Skip anything he doesn't want.
   Edit + promote anything that's close but not quite
   right. Do NOT promote anything just because it might
   help the experiment.
6. Optionally use the manual "What changed?" textarea if
   he wants to remember something the curator didn't
   surface.
7. Move on when he's done. He does NOT have to make more
   stories in the same session.

After Chris's gesture, Claude (with re-authorization)
performs the §18.5 capture across the five axes and
appends a checkpoint entry to this document. No further
provider spend for the checkpoint itself unless §18.7
triggers a v1 re-sample.

**Timeline:** unforced. Chris makes stories when he
wants to make them. Slice 282.2 aggregates evidence as it
arrives.

## §18.11 What this slice explicitly does NOT execute

* Does NOT create any new composition.
* Does NOT invoke Chris to make any specific story.
* Does NOT run any provider call unless §18.6 Position A
  is authorized separately.
* Does NOT modify any code, curator, v1 service, memory
  schema, retrieval, synthesis, verifier, SPA, cast, or
  Universe brief.
* Does NOT archive, edit, supersede, or normalize any of
  the 3 F&F or 14 PW memories.
* Does NOT alter Slice 281.2 UI.
* Does NOT touch any deferred candidate (2, 3, 4) from
  §9 outside Candidate 2's own protocol scope.

## §18.12 Slice 282.2 landing SHAs

* Protocol + baseline lock: **`42a1ec9`** —
  `docs(session-282): Slice 282.2 protocol + baseline
  lock — longitudinal organic-growth`
* Trailer (this commit) records the landing SHA above.
* Execution SHAs will accumulate one per checkpoint as
  Chris + ChatGPT authorize each step.

---

# §19 Slice 282.2 — Decision gate (protocol lock only)

**RESOLVED.** Chris + ChatGPT authorized **§18.6 Position A**
(one-time current-state v1 baseline collection). See §20
for execution + evidence + interpretation.

The first natural operator gesture (§18.10) does NOT begin
until Chris + ChatGPT review §20 findings and explicitly
authorize the next step.

---

# §20 Slice 282.2 — Current-state v1 baseline EXECUTION

## §20.1 Authorization + constraints

* Position A authorized: n=15 fresh v1 suggestions on F&F
  at current 12-Episode / 3-remembered-memory substrate.
* Provider-spend ceiling: **$0.05**.
* Classified against Q281.3-ε A/B/C/D/E rubric verbatim.
* Raw outputs preserved under
  `docs/design/session282_experiment_data/q282_2_v1_baseline.json`.
* No substrate mutation. No code changes. No Chris SPA
  gesture.

## §20.2 Executor context

* Executor SHA (in envelope `_probe_meta` per call):
  `8b0290d05418300314453df5b8058e2641f78bec` (Slice 282.2
  protocol trailer, verified as HEAD at execution time).
* Model: `gpt-5.6-terra` (from `_SUGGESTION_MODEL`; matches
  Q281.3-ε).
* Cache: bypassed via `use_cache=False` on all 3 calls.
* Substrate envelope confirmed live: 12 Episodes, 3
  memories, 2 cast members. Matches §18.4 baseline.

## §20.3 Token + cost

| call | tokens_in | tokens_out | suggestions |
|------|-----------|-----------|-------------|
| 1 | 788 | 111 | 5 |
| 2 | 788 | 133 | 5 |
| 3 | 788 | 141 | 5 |
| **Total** | **2364** | **385** | **15** |

Estimated cost per Q281.3-ε calibration (~$0.013/1k
blended): **~$0.036**. Under $0.05 ceiling. Under the
protocol-locked cost estimate. **No mid-execution
hard-stop.**

Input tokens per call are IDENTICAL to Q281.3-ε (788/788/
788) — confirms same prompt-shape + same substrate-summary
envelope-size regardless of memory count going from 1 to 3.

## §20.4 Raw suggestions (verbatim, all 15)

**Call 1:**

* 1.1 "Ruby and Tyson meet a customer who insists the
  bakery's mascot should judge the neighborhood baking
  competition."
* 1.2 "Tyson tries to prove the bakery is not haunted
  after a fresh loaf appears on the cooling rack with no
  one claiming it."
* 1.3 "The celebration-cake customer changes their
  competition-themed design at the last possible minute."
* 1.4 "Ruby brings a mascot candidate to the bakery, and
  Tyson worries it will derail the new closing routine."
* 1.5 "A sudden rush for seasonal pastries forces Ruby
  and Tyson to improvise a neighborhood tasting table."

**Call 2:**

* 2.1 "Ruby and Tyson test a few mascot ideas during a
  busy morning, only to discover the neighborhood has
  very strong opinions."
* 2.2 "A competition organizer visits to confirm Fox &
  Flour's cake order, and Tyson realizes the event has
  stricter rules than Ruby expected."
* 2.3 "After another eerie noise comes from the freezer,
  Ruby insists they finally investigate what is actually
  back there."
* 2.4 "The new closing routine is put to the test when a
  last-minute customer arrives just as Ruby and Tyson are
  ready to leave."
* 2.5 "Fox & Flour hosts a tasting of seasonal pastries,
  and Ruby tries to persuade Tyson to add an unexpectedly
  bold flavor to the menu."

**Call 3:**

* 3.1 "Ruby and Tyson test a few mascot ideas during a
  busy morning, only to discover the neighborhood has
  very strong opinions."
* 3.2 "The bakery's celebration-cake order for the
  neighborhood baking competition creates awkward
  questions about whether Fox & Flour can enter, judge,
  or simply stay out of it."
* 3.3 "Tyson investigates a new late-night noise in the
  bakery and finds evidence that makes the haunting
  theory harder to dismiss."
* 3.4 "Ruby insists on practicing the new closing
  routine, but Tyson realizes they have each interpreted
  'what they need' very differently."
* 3.5 "A mystery customer asks for a pastry based on an
  old neighborhood recipe, sending Ruby and Tyson on a
  search for its missing details."

## §20.5 Classification against Q281.3-ε A/B/C/D/E rubric (LOCKED, verbatim)

Rubric applied unchanged. Marginal calls (Y-/N-) resolved
conservatively (closer to a stricter reading of the axis).
Strict tallies count only clean-Y.

| # | A on-stage subj | B cast verb | C complication | D off-stage init | E dramatizable |
|---|-----------------|-------------|-----------------|-------------------|-----------------|
| 1.1 | Y | Y | Y | N | Y |
| 1.2 | Y | Y | Y | N | Y |
| 1.3 | N | N | Y | Y | Y- |
| 1.4 | Y | Y | Y | N | Y |
| 1.5 | Y- | Y- | Y | Y | Y- |
| 2.1 | Y | Y | Y | N | Y |
| 2.2 | Y- | Y- | Y | Y | Y |
| 2.3 | Y | Y | Y | Y- | Y |
| 2.4 | Y- | N- | Y | Y | Y |
| 2.5 | Y | Y | Y | N | Y |
| 3.1 | Y | Y | Y | N | Y |
| 3.2 | N | N | Y | Y | Y- |
| 3.3 | Y | Y | Y | N | Y |
| 3.4 | Y | Y | Y | N | Y |
| 3.5 | Y- | Y- | Y | Y | Y |

## §20.6 Summary metrics (strict-yes only)

| axis | strict-yes | % |
|------|-----------|---|
| A on-stage cast subject | 9 | **60%** |
| B cast action verb | 9 | **60%** |
| C explicit complication | 15 | **100%** |
| D off-stage initiator | 6 | **40%** |
| E dramatizable | 12 | **80%** |
| Weak-CONTROL (A=N ∧ B=N ∧ C=N ∧ D=Y) | 0 | **0%** |

Lenient tallies (Y + Y-):

| axis | lenient % |
|------|-----------|
| A | 80% (12/15) |
| B | 73% (11/15) |
| C | 100% |
| D | 47% (7/15) |
| E | 93% (14/15) |

## §20.7 Comparison table — current vs Q281.3-ε historical vs Patch's Workshop

| axis | Q281.3-ε (11 Ep / 1 mem) | **Current (12 Ep / 3 mem)** | Q281.3-ζ PW (32 Ep / 14 mem) | Δ vs Q281.3-ε | Δ vs PW |
|------|--------------------------|-------------------------------|-------------------------------|----------------|---------|
| A | 53% | **60%** | 60% | +7pp | 0pp |
| B | 53% | **60%** | 60% | +7pp | 0pp |
| C | 80% | **100%** | 100% | **+20pp** | 0pp |
| D | 40% | **40%** | 20% | 0pp | +20pp |
| E | 53% | **80%** | 80% | **+27pp** | 0pp |
| Weak-CONTROL | 7% | **0%** | 0% | -7pp | 0pp |

**Current F&F baseline MATCHES Patch's Workshop distribution
on 4 of 6 axes** (A, B, C, E) and matches PW on weak-CONTROL
(both 0%). Only D (off-stage initiator) still differs:
current F&F 40% vs PW 20% — F&F v1 still leans harder on
customer/organizer/event-driven topics than PW does.

## §20.8 Notable observations

### 20.8.1 Duplicate v1 emission (**within-substrate variance mirror**)

Suggestions **3.1 is IDENTICAL** (verbatim) to **2.1**:

> "Ruby and Tyson test a few mascot ideas during a busy
> morning, only to discover the neighborhood has very
> strong opinions."

Two separate calls (2 and 3) produced the same 5-suggestion
list containing the same suggestion. This mirrors the Slice
282.1 §16.4 finding that the curator produces low seed-
selection variance on the same substrate. **v1 shows the
same pattern.** This is a substrate-determinism observation
extending §16.4 across primitives.

Not a defect — the model is converging on the most salient
substrate-driven suggestion. But it means "reroll v1
suggestions" as a design affordance would return diminishing
returns on the same substrate.

### 20.8.2 Explicit memory retrieval in v1 output

Multiple suggestions demonstrate v1 is USING the promoted
memories:

* **3.4** explicitly quotes the `abac5486` cooperation
  clause language: *"Tyson realizes they have each
  interpreted 'what they need' very differently."* The
  quoted phrase "what they need" is drawn directly from
  the memory body: "neither one leaves until the other
  says they have what they need." This is a
  structurally-aligned callback shape — the topic frames
  the memory as a source of latent misalignment worth
  scene-testing.
* **1.4** integrates `73acdfc0` (mascot want) with
  `abac5486` (closing routine): "Ruby brings a mascot
  candidate to the bakery, and Tyson worries it will
  derail the new closing routine." Two-memory
  cross-referencing.
* **2.4** picks up the closing routine memory as
  scene-tester: "The new closing routine is put to the
  test when a last-minute customer arrives just as Ruby
  and Tyson are ready to leave."
* **2.3** and **3.3** pick up the freezer / haunting
  Episode-title theme from Episodes 6 + 8.
* **Mascot cluster:** 1.1, 1.4, 2.1, 3.1 all propose
  mascot-themed topics — v1 is heavily biased toward the
  freshly-promoted `73acdfc0` mascot want.

**Interpretation:** v1 substrate retrieval is landing.
Promoted memories are being surfaced as thread anchors in
next-Episode suggestions. This is direct evidence the
promotion → retrieval → suggestion loop is closed.

### 20.8.3 The mascot-cluster domination

4 of 15 suggestions (27%) are mascot-themed. In Q281.3-ε
(same source composition-material available via Episode
titles but memory pool = only `abac5486` cooperation
clause), mascot-themed suggestions were **also frequent**
(1.1, 2.1, 2.4, 3.1 in the Q281.3-ε set — comparable
27%). So the promoted `73acdfc0` did NOT materially shift
mascot-topic frequency; it appears to have shifted
mascot-topic SHAPE (from "audition mascot ideas" to "bring
a mascot candidate that Tyson worries will derail closing
routine" — deeper integration).

## §20.9 What this baseline establishes

1. **The current-state v1 distribution on F&F is
   materially different from the Q281.3-ε historical
   baseline.** Two axes (C, E) show strong +20pp / +27pp
   shifts far exceeding n=15 noise floor. Two axes (A, B)
   show +7pp marginal shifts within noise. D is unchanged.
   Weak-CONTROL rate dropped 7% → 0%.

2. **Current F&F v1 distribution is essentially at
   Patch's Workshop's shape on 4 of 6 axes.** A, B, C, E
   all match. Weak-CONTROL matches. Only D differs (F&F
   still more off-stage-initiator-heavy).

3. **v1 substrate retrieval is functioning.** Promoted
   memories are landing in v1's context and shaping the
   surfaced topic possibilities in structurally-aligned
   ways (§20.8.2). This is direct evidence for the
   promotion → retrieval → suggestion arc of the shipped
   loop.

4. **v1 shows the same low within-substrate variance
   pattern the curator does.** Suggestions 3.1 = 2.1
   verbatim; mascot-cluster convergence in both Q281.3-ε
   and current. Extends §16.4 finding across primitives.

## §20.10 What this baseline does NOT establish

1. **Whether the Q281.3-ε → current delta was caused by
   Slice 281.3 dogfood** (2 promoted memories + 1
   Episode) or by classifier-variance between Claude's
   application of the rubric now versus the S281
   classifier's application then, or by inherent v1 draw
   variance between two n=15 samples. All three are
   plausible; only the first is Hθ-supporting.

2. **Whether current-state matching PW on 4 axes means
   Hθ is now validated.** It means the observation is
   CONSISTENT with Hθ, not that Hθ is proven. Multiple
   alternative explanations remain live.

3. **How much "room to move" remains.** F&F is already
   at or near PW's shape on A/B/C/E. The only axis with
   genuine room to move toward PW is D (40% → target
   20%). This is a load-bearing observation for the
   Q282.2 SUPPORT criterion recalibration question
   (§20.13).

## §20.11 Baseline is now LOCKED

Current-state v1 baseline for Q282.2 comparison purposes:

* 15 v1 suggestions, verbatim, at
  `docs/design/session282_experiment_data/q282_2_v1_baseline.json`
* Classified against Q281.3-ε rubric (strict-yes):
  A=60%, B=60%, C=100%, D=40%, E=80%, Weak-CONTROL=0%
* Executor SHA: `8b0290d`
* Substrate: 12 Episodes, 3 remembered memories, 2 cast
* Model: `gpt-5.6-terra`
* No cache, all fresh calls

Any future checkpoint v1 re-sample compares against these
numbers, not the Q281.3-ε historical numbers.

## §20.12 Substrate preservation post-execution

Re-verified after execution:

* F&F: 12 Episodes, 3 remembered memories (bodies
  unchanged; witness rows unchanged). Zero mutation.
* Patch's Workshop: 32 Episodes, 14 remembered memories
  (untouched — v1 baseline probed F&F only). Zero
  mutation.

## §20.13 Effect on Q282.2 protocol

**Two interpretability concerns arise from the baseline:**

### 20.13.1 Distribution ceiling — "room to move" is smaller than assumed

The §18.8.1 SUPPORT criterion required v1 to "move TOWARD
Patch's Workshop shape on at least 2 axes with strict-yes
deltas ≥ +10 points." Given current F&F ALREADY MATCHES
PW on A/B/C/E and BEATS PW on weak-CONTROL, the only axis
with materially more room to move TOWARD PW is D
(40% → target 20%). And A/B are already AT PW's ceiling
(60%) — further movement above PW would be "beyond target,"
which the criterion did not anticipate.

Two operator options:

* **Option i — leave §18.8.1 untouched.** The criterion
  was locked before observing baseline; do not adjust
  post-hoc. Downside: SUPPORT is effectively "F&F D-axis
  moves ≥+10pp toward PW OR some other qualitative
  signal fires" — the quantitative threshold becomes
  harder to satisfy.
* **Option ii — Chris + ChatGPT explicitly re-lock the
  SUPPORT criterion** to reflect the actual room-to-move,
  BEFORE any post-baseline observation. Any recalibration
  must happen NOW, before Chris's first gesture generates
  new data.

Claude does NOT unilaterally recalibrate. Flagging for
review.

### 20.13.2 The baseline already looks like partial Hθ evidence

If Interpretation-X (Slice 281.3 dogfood alone drove the
observed shift) is correct, we already have partial
evidence supporting Hθ before any Q282.2 gesture. But we
cannot rule out classifier variance or v1 inherent draw
variance without additional evidence. Options:

* Treat the current baseline as evidence-neutral and
  observe Q282.2 dogfood as if this were a stable
  starting point.
* Preserve the Q281.3-ε → current delta as a note-only
  data point (not counted toward Q282.2 support
  criterion, but recorded as prior-context).
* Consider running one more n=15 v1 sample after 2-3
  compositions to compare: baseline (now) vs post-3-
  compositions. If baseline holds stable at 60/60/100/
  40/80 and post-checkpoint shows movement, that's
  cleaner evidence than baseline vs Q281.3-ε.

Claude recommends the middle option: preserve the delta as
context, do NOT count it as support toward Q282.2.

### 20.13.3 Safety of proceeding to first natural gesture

**Nothing in the baseline suggests the loop is broken or
unsafe.** The curator (Slice 282.1) is structurally
reliable; the v1 service is retrieving memories and
producing structurally-strong suggestions; the substrate is
intact.

Chris's first natural gesture CAN proceed safely from an
engineering standpoint. The interpretability caveats above
are METHODOLOGICAL (do we know how to compare Chris's next
observation against this baseline?), not SAFETY.

**Recommendation:** Chris + ChatGPT explicitly decide
whether to (a) leave §18.8.1 untouched, or (b) re-lock the
SUPPORT criterion, BEFORE authorizing the first Chris
gesture. Either is fine; the choice should be deliberate
and pre-observation.

## §20.14 Slice 282.2 baseline landing SHAs

* Baseline execution + classification + interpretation:
  **this commit's SHA** (appended in trailer).
* Raw artifact: `docs/design/session282_experiment_data/q282_2_v1_baseline.json`

---

# §21 Slice 282.2 — Decision gate (baseline lock complete)

**HALT.** Current-state F&F v1 baseline is locked at
A/B/C/D/E = 60/60/100/40/80%, weak-CONTROL = 0%,
substrate = 12 Ep / 3 mem, executor SHA `8b0290d`.

**Unexpected finding surfaced:** current F&F baseline
already matches Patch's Workshop distribution on 4 of 6
axes (see §20.7). This changes the interpretability of the
Q282.2 SUPPORT criterion (see §20.13.1) and raises a
methodological question about whether the criterion should
be re-locked BEFORE the first Chris gesture.

**Nothing in the baseline suggests the loop is broken or
unsafe** (§20.13.3). Chris's first natural dogfood gesture
would be SAFE to proceed with from an engineering
standpoint. The methodological concerns are about how to
INTERPRET future evidence, not about whether the loop can
be operated.

**Awaiting Chris + ChatGPT review** of:

1. §20.7 comparison table + §20.13 interpretability
   concerns.
2. Whether to leave §18.8.1 SUPPORT criterion untouched
   or re-lock it BEFORE the first Chris gesture.
3. Any other adjustments to the §18 protocol in light of
   the baseline.
4. Authorization for Chris's first natural gesture
   (§18.10) — which remains UNAUTHORIZED until this
   review.

No first natural operator gesture, no code changes, no
further provider spend triggered by this slice.




