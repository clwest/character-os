# UNIVERSE CANON RETRIEVAL LANE AUDIT — SESSION 263

**Status:** research/audit only. No code, database, or provider change
made or proposed for immediate landing. Companion to
`docs/design/PATCH_RIVET_RUNTIME_CONTENT_ARCHITECTURE_AUDIT_SESSION_263.md`
(the "prior audit"). Motivated by the empirical preflight in this same
session that confirmed U1 of the prior audit.

**Problem framing (from operator):** persistent world context —
"canon" — must be able to participate reliably in synthesis without
being crowded out by topical retrieval, and without flooding the
prompt when canon isn't relevant. Do not require the operator to
rephrase their topic string ("workshop" instead of "lab"). Do not
simply increase the global `top_k`.

**Goal of this audit:** determine the smallest architecture change
that gives Universe-scoped shared canon a *reliable* retrieval lane
whose behaviour is: intentional-when-relevant, silent-when-irrelevant,
budget-predictable, and generalisable across customer Universes.
Explicitly not: guarantee the SESSION 263 canon document surfaces
regardless of the query.

---

## 1. Preflight evidence being addressed

From the SESSION 263 canon ingest + retrieval probe, using the
persisted canon document
`f309469c-8167-434e-ad10-54c4ec1dc86f` (title
"PATCH'S WORKSHOP — SHARED CANON") scoped to the Patch's Workshop
Universe (M2M scope: Patch + Rivet):

| Query | Patch canon rank | Rivet canon rank |
| --- | --- | --- |
| `"AI took over the lab"` (Episode operator_topic) | 17 | 9 |
| `"AI took over the workshop"` | 3 | 0 |
| `"an experiment in the workshop went sideways"` | 1 | 0 |
| `"the 3D printer"` | 0 | 1 |
| `"Patch and Rivet workshop history"` | 0 | 0 |

With `top_k=5` at `dialogue_synthesis.py:1352`, canon does not enter
the assembled prompt on the exact Episode topic. The canon IS well-
embedded and dominates any workshop-anchored query. The wedge is
lexical: `"lab"` clusters with AI-agent methodology; `"workshop"`
clusters with the canon. The operator has ruled out rephrasing the
topic string.

---

## 2. Current retrieval architecture (audit map)

### 2.1 The one retrieval surface

`apps/embeddings/retrieval.py` — two public functions per the K2
scope lock:

* `retrieve_for_teammate(spokesperson, query, top_k=5)`
  * SESSION 261 Universe filter (line 199): universe of
    spokesperson must match universe of doc; legacy (universe=NULL)
    docs invisible to Universe-scoped teammates and vice versa.
  * M2M visibility filter (line 205): `document.spokespeople IS NULL
    OR document.spokespeople contains this teammate`.
  * Cosine ordering (line 210): `CosineDistance(embedding_vector, q)
    ASC`.
  * `LIMIT top_k` (line 214).
* `retrieve_for_thread(thread, query, top_k_docs=3, top_k_history=5)`
  — delegates to `retrieve_for_teammate` for docs; adds
  same-thread-only conversational history. Not exercised by dialogue
  synthesis today.

**Every retrieval consumer calls the same function with a single
integer budget.** No differentiated scope query paths exist.

### 2.2 Effective per-consumer `top_k` values

Verified inventory (paths cited relative to `shell/`):

| Consumer | Default `top_k` | Notes |
| --- | --- | --- |
| `character_os/script_synthesis.py:273` (talking-head) | 5 | per-call |
| `character_os/teammate_ask.py:158` (ask) | 5 | per-call |
| `character_os/dialogue_synthesis.py:1352` (dialogue) | **5, hardcoded** | per character, once per synthesis |
| `character_os/realtime_document.py:66` (avatar doc bake) | 50 | up-front bake, not per-request |
| `apps/realtime/tools/recall_knowledge.py:32` (realtime tool) | 3 default / 5 max | per tool call |

Dialogue is the only consumer where the budget is not
caller-configurable; the others expose `top_k` as a parameter.

### 2.3 SHARED-block detection (post-hoc, not scope-driven)

`_build_factual_basis_section` at
`character_os/dialogue_synthesis.py:391` builds the §1 prompt block.
Its SHARED detection (lines 434-457):

```
chunk_id_appearances = Counter(chunk.id for each_character's_chunks)
shared_ids = {cid for cid, n in chunk_id_appearances.items() if n > 1}
# a chunk appears in SHARED iff it was retrieved by ≥2 characters
```

Two consequences worth naming:

1. **SHARED status is derived from retrieval outcome, not from doc
   scope.** A canonically-shared doc (M2M-null or M2M-many) that
   makes only one character's top-5 stays in that character's
   SCOPED block only.
2. **Existing prompt semantics mislabel scope in that case.** A
   M2M-null canon chunk retrieved by Patch alone is emitted under
   "PATCH'S SCOPED KNOWLEDGE (only 'patch' may cite these as their
   own)", and the §1 SCOPE RULE explicitly tells Rivet he cannot
   cite Patch's scoped facts. Rivet is being denied a fact that IS
   in his own retrieval scope by the scope filter — he just missed
   it on cosine ordering. This is a latent bug independent of the
   canon-lane question; noted here for reference.

### 2.4 What the storage layer already supports

`KnowledgeDocument` fields inspected at
`apps/embeddings/models.py:111-247`. No pin/priority/lane/tier field
exists. `source_metadata` is a `JSONField` — a metadata carrier
usable without schema change, but nothing reads it for retrieval
routing today. Universe scope is a first-class FK
(`apps/embeddings/models.py:140`). M2M scope on `spokespeople` is a
first-class through model
(`KnowledgeDocumentSpokesperson`, line 70).

**The scope-storage layer already distinguishes three visibility
tiers:** legacy (universe=NULL), Universe-broadcast (universe set +
M2M null), Universe-shared-canon (universe set + M2M count > 1),
Universe-character-scoped (universe set + M2M count = 1). These
tiers are testable — see `apps/embeddings/tests/test_retrieval_universe.py`
rows 6, 7, 8 which cover exactly the visible/invisible boundaries
for each tier.

**No code today discriminates between these tiers at ranking
time.** They all flow through a single `Q(...)` filter into a single
cosine sort into a single `LIMIT top_k`.

---

## 3. Options for a canon lane

For each option below: mechanism, code surface, budget shape,
prompt effect, generalisation notes.

Design axes recurring across all options:

* **Reliability** — will canon appear when it's relevant on-topic?
* **Bounded bloat** — how many chunks worst-case?
* **Silent-when-irrelevant** — does canon show up when the topic
  clearly doesn't intersect it?
* **Universe-generalisation** — does the same mechanism work for a
  plumber Universe, a bakery Universe, an ensemble Universe?
* **Interaction with `use_knowledge=False`** — does the lane still
  degrade gracefully?
* **Interaction with K6.4 verification** — does the canon get
  factually verified per character?

### Option A — Reserved shared-canon slot(s) inside the per-character retrieval call

**Mechanism.** `retrieve_for_teammate` grows a `shared_top_k`
parameter. Internally the query splits: one predicate for shared-
tier docs (Universe + M2M count > 1 OR M2M null), one predicate for
character-tier docs (Universe + M2M includes this teammate). Each
sub-query gets its own `LIMIT`. Results concatenated (or returned as
two lists).

**Two sub-variants:**

* **A.1 — reserve OUT OF the existing budget**: `top_k=5` becomes 2
  shared + 3 character. Total chunks per character unchanged; canon
  displaces some character content.
* **A.2 — reserve ON TOP of the existing budget**: 2 shared + 5
  character. Total chunks per character grows to 7; prompt grows.

**Code surface.**
* Change one function signature (backwards compatible if
  `shared_top_k=0` default).
* Every caller with `top_k=` needs to opt in.
* SHARED-block detector in
  `_build_factual_basis_section` continues to work (shared chunks
  now appear in both characters' returns → detector groups them).

**Silent-when-irrelevant.** Shared slots are cosine-ordered against
the query within the shared pool. Canon still competes on
relevance; if canon is a poor semantic match, its top-1 still
enters the SHARED block. This is the interesting failure mode:
Option A guarantees shared slot(s) are FILLED whenever any shared
doc exists, whether relevant or not.

* Mitigation: add a distance ceiling (see §4.2). If canon top-1
  exceeds ceiling, leave the shared slot empty. Ceiling tuning is
  the tricky part — the SESSION 263 canon's distance on "AI took
  over the lab" was 0.76; canonical high-relevance queries land at
  0.26-0.65.

**Universe-generalisation.** Works trivially. Any Universe with
canon docs gets the same lane behaviour.

**Interaction with K6.4.** Verifier operates per-turn against the
speaking character's corpus (see
`dialogue_synthesis.py:1491`). Shared chunks enter both characters'
corpora → both can cite → K6.4 accepts. Same shape as today's
SHARED behaviour.

**Cost.** Two DB queries per character per synthesis instead of
one, or one query with a UNION. Marginal (~1-2 ms).

### Option B — Separate shared-canon retrieval pass (universe-level, once per synthesis)

**Mechanism.** New function
`retrieve_universe_canon(universe, query, top_k=N)` that queries
shared-tier docs (Universe + M2M null OR M2M count > 1) once.
Independent of any teammate.

`synthesize_dialogue` runs this once *before* per-character
retrieval:

```
shared = retrieve_universe_canon(workspace, universe, topic, top_k=2)
for tm in cast:
    per_character[tm] = retrieve_for_teammate(tm, topic, top_k=5)
```

`_build_factual_basis_section` grows a `shared_chunks` parameter and
uses it deterministically to fill SHARED, ignoring the post-hoc
detector.

**Code surface.**
* One new retrieval function.
* `synthesize_dialogue` gains one call + one parameter.
* `_build_factual_basis_section` grows one parameter; the existing
  post-hoc detector becomes complementary or is removed.
* No change to the general `retrieve_for_teammate` API — other
  consumers untouched.

**Silent-when-irrelevant.** Same as A: relevance floor optional.

**Universe-generalisation.** Same — Universe-level function
generalises for free.

**Interaction with K6.4.** Same shape — shared chunks feed into
each character's `corpus_by_alias[alias]` at
`dialogue_synthesis.py:1492`. Requires the K6.4 corpus build to
receive the shared chunks explicitly.

**Cost.** One additional DB query per synthesis (not per character).
Cheaper than A.

**Advantage over A.** `retrieve_for_teammate` remains a single
scope-preserving function; canon-lane behaviour is a
synthesis-layer concern, not a K2-layer one. Preserves the K2
scope-lock discipline ("one retrieval function per surface, not
one per feature").

**Disadvantage over A.** A single shared pool can't express
per-character-shared-with-Rivet-but-not-Repo-Red in an
N > 2 cast Universe. All shared chunks are visible to all cast
members. This is arguably correct semantics for "canon" — but
different from Option A which routes through per-character scope
filters that could enforce more nuanced visibility.

### Option C — Reuse existing architecture (post-hoc detector variants)

**C.1 — Scope-aware SHARED detector.** Modify
`_build_factual_basis_section` so a chunk is emitted under SHARED
when EITHER `n > 1` in per-character retrievals OR the chunk's
document has `spokespeople` count > 1 OR spokespeople null.

* Fixes the §2.3 latent mislabel bug for free.
* Does NOT solve the SESSION 263 case: canon never reached either
  character's top-5, so it isn't in the return set at all. No
  detector reshuffle can surface what wasn't retrieved.

**C.2 — Force-inject M2M-shared chunks.** Modify
`retrieve_for_teammate` to append the top-1 chunk of every M2M-null
(or M2M-many) doc in the Universe to the return set, regardless of
cosine order.

* Solves the SESSION 263 case: canon lands regardless of query.
* Explodes bloat: a Universe with 10 canon docs injects 10 extra
  chunks per character per synthesis.
* Ignores relevance floor entirely.
* Falsifies the operator's "silent-when-irrelevant" requirement.

**C.3 — Raise `top_k` in dialogue synthesis only.** Change the
hardcoded 5 at `dialogue_synthesis.py:1352` to, say, 10, and rely
on the existing SHARED detector to bubble up chunks that appear in
both characters' now-deeper returns.

* Doubles per-character prompt bloat unconditionally, most of it
  low-relevance methodology tail.
* Does not guarantee canon appears — canon at Patch rank 17, Rivet
  rank 9 still misses top-10.
* Explicitly named by operator as the naive option to avoid. Listed
  here for completeness.

**Verdict on C.** C.1 is a free win regardless of which of A/B/C.2
lands (it fixes a real mislabel bug). C.2 solves the wrong problem.
C.3 is ruled out.

### Option D — Metadata-carried priority using `source_metadata` (no schema change)

**Mechanism.** Ingest sets `source_metadata = {"canon_tier": "shared",
"canon_priority": 1}`. Retrieval reads it and constructs a bonus
scoring: `effective_distance = cosine_distance - priority_bonus`.

**Code surface.** Retrieval query reads JSONField at DB layer
(pgvector doesn't easily combine with JSONField in a single ORDER
BY without raw SQL) — requires either a materialised column or a
Python-layer re-sort.

**Advantage.** No schema change. Priority is per-doc.

**Disadvantage.** Introduces a per-doc numeric bias with no
principled way to set the number — a config bikeshed. The
priority-bonus knob mixes ranking (cosine) with lane (canon vs
character) in one dimension where the two concerns should be
distinct.

**Verdict on D.** Reject — bad separation of concerns.

### Option E (operator-ruled-out) — Raise global `top_k`

Included only to document rejection. Rebalances nothing;
proportional bloat across all consumers.

---

## 4. Comparison matrix

Scoring: ✓ (positive), — (neutral), ✗ (negative). "Change budget"
lists new chunks-per-synthesis worst-case for the 2-cast case.

| Axis | A.1 (reserve out) | A.2 (reserve on top) | B (separate pass) | C.1 (detector fix) | C.2 (force-inject) |
| --- | --- | --- | --- | --- | --- |
| Solves the SESSION 263 case | ✓ | ✓ | ✓ | ✗ | ✓ |
| Silent-when-irrelevant | Needs floor | Needs floor | Needs floor | ✓ (no change) | ✗ |
| Bounded bloat | ✓ (cap = shared_top_k) | ✓ (cap = shared_top_k + 5) | ✓ (cap = shared_top_k + 2*5) | ✓ (no change) | ✗ (unbounded) |
| Preserves character retrieval depth | ✗ (loses 2/5 char slots) | ✓ | ✓ | ✓ | ✓ |
| Preserves single-retrieval-surface discipline | — (retrieval grows one param) | — (same) | ✓ (canon lane lives in synthesis) | ✓ | ✗ (retrieval bloated) |
| Cost per synthesis | +1 subquery per char | +1 subquery per char | +1 query total | 0 | 0 |
| Change surface (files) | 2 (retrieval + synthesis) | 2 (retrieval + synthesis) | 2 (new retrieval fn + synthesis) | 1 (synthesis) | 1 (retrieval) |
| Other consumers affected | opt-in via param | opt-in via param | 0 (dialogue-only) | 0 (dialogue-only) | ALL (retrieval semantics change) |
| Fixes §2.3 latent mislabel | via B-like path | via B-like path | ✓ if detector removed | ✓ | ✓ (accidentally) |
| N-cast generalisation | ✓ | ✓ | ✓ | ✓ | ✓ |
| K6.4 corpus wiring impact | minimal | minimal | small (feed corpus explicitly) | 0 | minimal |

**Interpretation.**

* **A.1** shrinks character depth to feed canon — bad in low-canon
  Universes where a shared slot might be empty.
* **A.2** and **B** are close on capability. B is cheaper per query
  and keeps the K2 module contract clean.
* **C.1** is a bug fix, not a canon-lane fix. Should ship anyway.
* **C.2** solves too much and violates operator's silent-when-
  irrelevant rule.

**Preferred candidate: B + C.1 in one slice**, with a distance
ceiling on the canon retrieval. B provides the intentional lane;
C.1 corrects the SHARED-labelling bug that already exists.

---

## 5. Additional design axes (any option must decide these)

### 5.1 Budget shape (`shared_top_k` sizing)

Options:

* **Fixed small integer** (e.g. 2) — simplest, universe-agnostic.
* **Fixed as a fraction of character budget** (e.g. `min(2,
  ceil(top_k/3))`) — scales if `top_k` moves later.
* **Universe-configurable** (a new field on `Universe`) — schema
  change; probably premature.

Recommendation for first landing: **fixed = 2**. Trivial to tune
later; keeps prompt bloat predictable.

### 5.2 Relevance floor (silent-when-irrelevant)

Without a floor: canon at cosine distance 0.85 still enters SHARED.
With a floor: canon that fails to reach floor is dropped from
SHARED.

Empirical anchor points (from SESSION 263 probes, cosine distance):

* Canon on workshop-anchored queries: 0.26-0.65.
* Canon on the dogfood "AI took over the lab" query: 0.76.
* Character K2 top-1 distances on the same dogfood query: 0.62-0.66.
* Existing character retrievals show top-5 distances of 0.62-0.71
  for the SESSION 263 dogfoods — no floor exists today.

**Empirical suggestion:** floor at 0.80 for a first landing. Would
have dropped canon on the exact `"AI took over the lab"` query (0.76
< 0.80 — passes) but dropped it on a completely off-topic query
(e.g. "tax law reform" would land >0.9).

Wait — reread. Canon distance on `"AI took over the lab"` was 0.76,
which is BELOW 0.80. So floor=0.80 would ADMIT canon on this query.
That contradicts the operator's rule that this specific test should
now demonstrate canon effect. If the goal of the first landing IS
to admit canon on the dogfood query, floor=0.80 works.

But floor tuning is empirical and Universe-specific; canon corpora
of different lexical density will produce different distance
distributions. Alternative: **no floor in first landing**, monitor,
add floor if bloat becomes real. Bloat cap already exists via
`shared_top_k=2`.

Recommendation: **no floor in the first slice; ship a
`shared_top_k=2` cap and revisit if operator observes canon
appearing on off-topic renders**.

### 5.3 Interaction with K6.4 verification corpus

Rule 7 of AI-D2 (`dialogue_synthesis.py:1487-1494`): per-turn K6.4
verifies against the SPEAKING character's corpus. Corpora are built
per-alias from `per_character_chunks[alias]`. Under B, the shared
canon chunks need to be added to BOTH `corpus_by_alias[patch]` and
`corpus_by_alias[rivet]` explicitly, else K6.4 will flag any
canon-cited fact as unsupported.

This is one line of code but is load-bearing — a canon fact spoken
by Rivet must verify against the corpus that includes it.

### 5.4 Interaction with `use_knowledge=False`

`use_knowledge=False` currently skips retrieval entirely
(`dialogue_synthesis.py:1346`). Canon lane must obey the same flag —
if the operator explicitly disabled knowledge, canon does not
sneak in via a separate pass.

### 5.5 Interaction with the SESSION 262 observability schema

`Composition.knowledge_chunk_ids` currently aggregates all retrieved
chunk IDs (see `dialogue_synthesis.py:1533`). Canon chunks should
appear here on the same footing as character chunks so the audit
trail remains complete. Under B, this is a one-line concatenation.

### 5.6 Interaction with the existing SHARED-block detector

Under B, the post-hoc detector at
`_build_factual_basis_section:434` becomes strictly weaker than the
new deterministic path. Two options:

* **Remove the detector** — canonical SHARED = the B pass output.
  Simpler code path.
* **Keep both** — SHARED = union of (B pass output) + (chunks that
  appeared in ≥2 character returns). Preserves accidental-SHARED
  behaviour for docs that legitimately reach both characters.

C.1 makes the detector scope-aware; combined with B this becomes:

* SHARED = union of (B pass output) + (chunks whose doc is M2M-null
  or M2M-many, regardless of retrieval count).

Recommendation for the first slice: **remove the post-hoc detector**
because B + C.1 together render it redundant, and reducing
duplicate paths reduces test surface.

### 5.7 What "shared-tier" means at the query level

The audit's tier definition in §2.4:

* **Universe-broadcast** (universe set + M2M null) — visible to any
  teammate in that Universe.
* **Universe-shared-canon** (universe set + M2M count > 1) — visible
  to specifically-listed teammates in that Universe.
* **Universe-character-scoped** (universe set + M2M count = 1) —
  visible to exactly one teammate.

Two of the three are shared. The canon-lane query in Option B
targets: `universe = <this-universe> AND (spokespeople IS NULL OR
spokespeople-M2M-count > 1)`. The count > 1 predicate needs a
subquery — either an annotated queryset or a raw
`HAVING COUNT(*) > 1` on the through table.

The SESSION 263 canon uses M2M count = 2. Both flavours resolve
correctly under the proposed predicate.

---

## 6. Recommendation (smallest justified next experiment)

**Slice B + C.1 as one landing:**

1. New function `apps/embeddings/retrieval.py::retrieve_universe_canon(
   workspace, universe, query, top_k=2)` returning shared-tier chunks
   in cosine order. No relevance floor in first landing.
2. `character_os/dialogue_synthesis.py::synthesize_dialogue` calls it
   once per synthesis; result feeds a new `shared_chunks` parameter
   on `_build_factual_basis_section`.
3. `_build_factual_basis_section` emits `shared_chunks`
   deterministically under SHARED; retains the post-hoc detector
   OR removes it (see §5.6 — recommend remove).
4. K6.4 corpus build adds shared chunks to both characters'
   corpora.
5. `use_knowledge=False` skips canon retrieval identically.
6. `Composition.knowledge_chunk_ids` includes canon chunk IDs.

**Scope explicitly excluded from the first landing:**

* Any change to `retrieve_for_teammate`'s signature or semantics.
* Any change to `top_k` for character retrieval.
* Any change to non-dialogue consumers (talking-head, ask,
  realtime, etc.).
* Any schema addition to `KnowledgeDocument` or `Universe`.
* Any Writing Contract v4 change.
* Any change to Episode.

**Acceptance criteria for the follow-up dogfood:**

1. Re-run `"AI took over the lab"` 60 s render. Persisted
   observability shows the canon chunk ID in
   `Composition.knowledge_chunk_ids`.
2. The assembled prompt (retrievable from the raw synthesis input
   via SESSION 262 fields or a debug endpoint) contains the canon
   text under a SHARED block.
3. At least one accepted turn's language reflects the canon
   content (e.g. explicit reference to the workshop as a place, or
   the printer as an established asset, or the calling-Rivet habit).
4. No accepted turn contradicts the canon.
5. A second render on the same Episode topic reproduces #1-3 (the
   lane is deterministic, not one-shot).

**Falsification test to include:** synthesize an off-topic prompt in
the same Universe (e.g. topic string that has no lexical or
semantic overlap with the canon). Confirm the shared block IS
emitted but the model does not incoherently drag canon into an
unrelated topic. This tests silent-when-irrelevant behaviour and
informs whether §5.2's distance floor becomes justified.

**Estimated code change size (informational, not a plan):** ~80-120
lines total including tests; touches 2 modules; adds 1 module test
file; no migration.

---

## 7. Unresolved questions

* **U1.** Distance floor policy. Recommend deferring until the first
  bloat/irrelevance signal appears in dogfood; §5.2 lays out the
  empirical anchors needed to set one.
* **U2.** `shared_top_k` shape. Recommend fixed = 2. Any evidence
  for larger canon budgets should come from post-landing dogfood.
* **U3.** Whether talking-head / ask / realtime consumers should
  gain a canon lane too. Deferred — dialogue was the venue where the
  problem surfaced; add later per real evidence.
* **U4.** Whether the SESSION 262 observability schema should carry
  a separate `canon_chunk_ids` list for provenance clarity, or
  whether commingling with `knowledge_chunk_ids` is sufficient.
* **U5.** Whether canon retrieval should be query-independent
  entirely (i.e., always inject the same top-N canon chunks
  regardless of query, using recency or a `pinned` field). This
  would falsify option D by reframing it; deferred.
* **U6.** Interaction with the K7 URL ingest pipeline and any
  future canon-authoring UX affordance. Out of scope here.
* **U7.** Whether Universe should carry a `canon_document` or
  `canonical_documents` M2M for operator-facing clarity, or whether
  the scope-tier definition (Universe + M2M-null-or-many) is enough
  metadata. Deferred; the tier definition works for the machine
  without new schema.

---

## 8. Non-goals reaffirmed

* This audit does not commit to landing B + C.1. It documents them
  as the smallest justified next slice IF the operator elects to
  proceed.
* This audit does not propose a rewrite of Patch or Rivet K2.
* This audit does not propose Writing Contract v4 changes.
* This audit does not propose an Episode schema change.
* This audit does not itself change code, database, or provider
  behaviour.

---

## 9. Source citations index

* `apps/embeddings/retrieval.py` — the one retrieval surface;
  Universe filter (line 199); M2M filter (line 205); cosine sort
  (line 210); LIMIT (line 214).
* `apps/embeddings/models.py` — KnowledgeDocument fields, no
  priority/pin/lane fields exist today.
* `apps/embeddings/tests/test_retrieval_universe.py` — 9-row truth
  table encoding the visible/invisible boundaries for each tier.
* `character_os/dialogue_synthesis.py:1348-1363` — the fixed
  `top_k=5` call site.
* `character_os/dialogue_synthesis.py:391-493` —
  `_build_factual_basis_section` and the post-hoc SHARED detector.
* `character_os/dialogue_synthesis.py:1487-1526` — K6.4 corpus wiring
  per-character.
* `docs/design/PATCH_RIVET_RUNTIME_CONTENT_ARCHITECTURE_AUDIT_SESSION_263.md`
  — prior audit whose U1 this report addresses.
* Preflight probe evidence — persisted in commit and this session's
  probe outputs; canon doc `f309469c-8167-434e-ad10-54c4ec1dc86f`,
  chunk `da7e6553-a5ea-463f-994f-354289ab9b5b`.
