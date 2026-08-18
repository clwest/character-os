# EPISODIC CONTINUITY & CANON PROMOTION — SESSION 264 AUDIT

**Status:** READ-ONLY audit. No implementation. No schema change proposed for
this session.
**Author:** SESSION 264 audit.
**Repo state at audit:** `main` @ `6138234` (SESSION 263 closeout), origin
clean, working tree clean.
**Cross-references:** `UNIVERSE_BOUNDARY_V1.md`, `UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md`,
`EPISODE_SCHEMA_V1.md`, `EPISODE_LIFECYCLE_V1.md`, `EPISODE_VS_COMPOSITION_V1.md`,
`COMPOSITION_OBSERVABILITY_V1.md`, `COMPOSITION_OBSERVABILITY_SCHEMA_V1.md`,
`UNIVERSE_CANON_RETRIEVAL_LANE_AUDIT_SESSION_263.md`,
`UNIVERSE_CANON_RETRIEVAL_LANE_IMPLEMENTATION_SESSION_263.md`,
`RELATIONSHIP_BOUNDARY_V1.md`, `KNOWLEDGE_LAYER.md`,
`docs/handoffs/SESSION_261_UNIVERSE_SUBSTRATE_IMPLEMENTATION.md`,
`docs/handoffs/SESSION_262_CLOSEOUT.md`, `docs/handoffs/SESSION_263_CLOSEOUT.md`.

**Provenance tags used throughout this document:**

- **[REPO]** — verified against current source at audit time.
- **[RATIFIED]** — decided in a prior slice, design + implementation both
  landed.
- **[DEFERRED]** — named as future work in a prior slice; no code.
- **[INFERENCE]** — this audit's synthesis of repo evidence into a claim
  not verbatim in any prior doc.
- **[NEW RECOMMENDATION]** — this audit is proposing it; nothing prior
  ratifies it.

---

## 1. Executive Conclusion

Character OS already has enough substrate to state the operator's authored
premise for a story and to produce durably observable renders of that
story. It has zero substrate for what happened *inside* the story, and
zero substrate for whether what happened *may be remembered* by the
Universe or its cast.

Specifically:

1. **Episode** [RATIFIED, SESSION 262] owns the operator-authored premise
   (`operator_topic`) and the operator-declared cast. It is deliberately
   thin. It does NOT own an accepted synthesis, canonical composition
   pointer, occurrence log, memory, or any concept of "the story ended
   like this."
2. **Composition** [RATIFIED, SESSION 262 observability v1] owns the
   render attempt: `first_pass_synthesis`, `corrective_pass_synthesis`,
   `synthesis_attempt_count`, `render_dispatched_at`, `verification_status`,
   `synthesized_brief`. These fields are immutable-once-populated and
   describe a single render attempt. They do not describe narrative
   history.
3. **Universe canon retrieval** [RATIFIED, SESSION 263] returns
   *pre-authored* shared-tier knowledge documents. It is a read path over
   `KnowledgeDocument`. There is no write path that promotes render
   output back into canon.
4. **`shell/apps/memory/`** [REPO] is a bare Django scaffold: `models.py`,
   `views.py`, `admin.py`, `urls.py` all have 0 lines; `apps.py` is a
   6-line AppConfig stub; there are no migrations that define a table.
   Treating it as an existing memory substrate would be wrong.
5. **`shell/apps/conversations/`** stores real-time chat transcripts
   with per-message K6.4 verification and per-thread embeddings. It is
   used by realtime avatar retrieval within a thread, not by
   Composition synthesis, and it never generalizes across threads or
   into narrative memory.
6. **No canon-promotion, narrative-memory, occurrence-log, promise
   ledger, WorldEntity, Relationship, or "final Composition" surface
   exists.** All four are explicitly named as deferred in prior sessions.

The load-bearing question this session must answer — *how does something
that happened in an Episode become persistent narrative history without
allowing synthesis inventions to silently become canon* — has never been
answered by any prior slice. The primitives to answer it exist. The
answer itself does not.

**Recommendation:** The smallest useful next slice is a **NarrativeMemory
substrate** owned by Episode, populated **only by explicit operator
promotion of a specific Composition attempt**, retrieved through its
own thin lane behind the existing SESSION 263 canon lane. It requires
no changes to Composition, no changes to KnowledgeDocument, no changes
to KnowledgeChunk, and no changes to `retrieve_universe_canon`. It
explicitly does NOT introduce Relationship or WorldEntity. Details in
§13–15.

**Recommendation does NOT propose** a state machine on Episode, a state
machine on Composition, canon promotion of `KnowledgeDocument`, automatic
memory extraction from synthesis, or a general "world history" model.
Those are §16 non-goals.

---

## 2. Current-State Substrate Inventory

### 2.1 Universe [RATIFIED, SESSION 261]

`shell/apps/universe/models.py:33`. Fields: `id`, `workspace` (FK
CASCADE, required), `name`, `slug` (per-workspace unique with
auto-suffix on collision), `description`, `archived_at`, `created_by`
(SET_NULL), timestamps. No state enum; `archived_at NULL` = active.
Semantic scope is `retrieve_for_teammate`'s Universe filter branch
(nine-row truth table — `UNIVERSE_BOUNDARY_V1.md` §Q10; enforcement in
`shell/apps/embeddings/retrieval.py:186–206`).

### 2.2 Episode [RATIFIED, SESSION 262]

`shell/apps/universe/models.py:241`. Fields: `id`, `universe` (FK
CASCADE, required — DEV-1 versus `EPISODE_SCHEMA_V1.md` §Q7's original
RESTRICT proposal; API preflight + `Composition.episode = RESTRICT`
DB backstop preserve the "populated Universe cannot silently wipe
stories" guarantee), `title` (per-Universe unique via meta constraint),
`operator_topic` (TextField, mutable at the Episode level; distinct
from and never propagated into `Composition.operator_topic` — comment
at `models.py:300–310`), `cast` (M2M through EpisodeCast), `archived_at`,
`created_by`, timestamps.

Explicit creation only (H3 ratified, H5 rejected — `EPISODE_LIFECYCLE_V1.md:96,110,156,183`).
No `state` enum, no `final_composition` FK, no `canonical_composition`
FK, no `occurrence_log`, no `referenced_entities`, no `continues_from`,
no `narrative_memory`, no `promise_ledger`.

### 2.3 EpisodeCast [RATIFIED, SESSION 262]

`shell/apps/universe/models.py:399`. Through model; `episode`, `teammate`,
`added_at`. Both FKs CASCADE; loss of a cast row does not destroy render
provenance. `clean()` enforces `teammate.universe_id ==
episode.universe_id`. Design comment (`EPISODE_COMPOSITION_WORKFLOW_V1_IMPLEMENTATION.md`
line 41) explicitly notes: `added_at` ordering is a UI default only, not
a protagonist/lead/narrator schema role.

### 2.4 Composition [RATIFIED render substrate; SESSION 262 observability]

`shell/apps/compositions/models.py:357`. Load-bearing narrative fields:

| Field | Line | Immutable-once-populated? | Role |
|---|---|---|---|
| `operator_topic` | 502 | Yes | Per-attempt copy of the operator's brief. Design comment 498–501 explicitly says Episode owns story-level `operator_topic`; the Composition copy remains authoritative for the render attempt in every case. |
| `target_duration_seconds` | 503 | Yes | Operator-requested spoken duration. |
| `synthesis_attempt_count` | 506 | Yes (once > 0) | 0 = synthesis never fired; 1 = first-pass only; 2 = first + bounded corrective. |
| `first_pass_synthesis` | 507 | Yes | Raw first-pass LLM output. |
| `corrective_hint` | ~509 | Yes | Descriptive hint fed into the corrective pass. |
| `corrective_pass_synthesis` | ~510 | Yes | Raw corrective LLM output. |
| `validation_failure_reason` | ~511 | Yes | Structured reason a synthesis failed validation. |
| `synthesis_predicted_seconds` | ~512 | Yes | Planner estimate. |
| `render_dispatched_at` | 512 | Yes (idempotent `mark_render_dispatched()`; `models.py:701–719`) | First-provider-dispatch moment. |
| `episode` | 534 | Mutable (attach/detach affordance) | `on_delete=RESTRICT`; DEV-2 vs design's PROTECT. `attach_episode` view at `views.py:333` moves/detaches, saving `update_fields=["episode","updated_at"]` so the immutability guard skips. |
| `synthesized_brief` | ~478 | Mutable | K6-synthesized script only on successful renders. |
| `verification_status` | ~453 | Mutable | VERIFIED / TRUSTED_PASSTHROUGH / SKIPPED / REJECTED. |
| `verification_warnings` | ~439 | Mutable | JSONField list of K6.4 verifier findings. |
| `rejected_synthesis` | ~447 | Mutable | Strict-mode blocked LLM output. |
| `knowledge_chunk_ids` | ~427 | Mutable | Canon-first ordered chunk-id list; SESSION 259 fix ensures failure paths carry the retrieval snapshot, not `[]`. |
| `status` | ~407 | Mutable | DRAFT / PLANNING / RUNNING / PARTIAL / COMPLETED / FAILED. |
| `writing_contract_version` | mutable | Mutable | Stamp of contract version used. |

Immutability enforcement mechanism: `Composition.save()` snapshots
`_IMMUTABLE_OBSERVABILITY_FIELDS` via `from_db()` at load time; any
divergent write raises `ValidationError`. Legitimate lifecycle writes
that use `update_fields=[...]` bypass the guard automatically for the
mutable set. This is production-grade [REPO, `models.py:599–699`].

### 2.5 KnowledgeDocument + KnowledgeChunk [RATIFIED read substrate]

`shell/apps/embeddings/models.py:111` (Document) and `:306` (Chunk).
Document fields relevant to continuity: `workspace` (required),
`universe` (optional; RESTRICT on delete, `UNIVERSE_BOUNDARY_V1.md`
correction 75d17f5), `spokespeople` (M2M visibility), `status`
(PENDING / PROCESSING / PROCESSED / FAILED), `is_active` (soft-delete).
The four canon tiers (`UNIVERSE_CANON_RETRIEVAL_LANE_AUDIT_SESSION_263.md`
§2.4):

- **legacy** — `universe=NULL`. Visible only to legacy teammates.
- **Universe-broadcast** — `universe != NULL` AND M2M count = 0.
- **Universe-shared-canon** — `universe != NULL` AND M2M count > 1
  AND covers the full cast.
- **Universe-character-scoped** — `universe != NULL` AND M2M count = 1.

Contract rule 2 (`retrieval.py:19–23`): no code outside
`apps.embeddings.retrieval` may import `KnowledgeChunk` or
`ConversationEmbedding`. Enforced by a repo-level test.

### 2.6 SESSION 263 Universe canon retrieval lane [RATIFIED]

`retrieve_universe_canon(workspace, universe, cast, query, top_k=2)`
(`retrieval.py:274`). Returns shared-tier chunks (M2M-null OR M2M
covering the full cast). Called once per synthesis from
`synthesize_dialogue()` (`shell/character_os/dialogue_synthesis.py:1389`
region). Chunks land ahead of per-character K2 chunks in
`Composition.knowledge_chunk_ids`. Slice C.1
(`_is_scope_shared_document`, `dialogue_synthesis.py:391`) promotes
scope-shared per-character chunks into the SHARED block to preserve
the SCOPE RULE. `top_k=2` is fixed for v1 — U2 in the SESSION 263
audit's deferred list.

### 2.7 Character K2 retrieval [RATIFIED, SESSION 138]

`retrieve_for_teammate(spokesperson, query, top_k=5)`
(`retrieval.py:151`). Workspace + Universe scoped; per-character M2M
filter applied last. `top_k=5` is locked. No override parameter for
workspace; cross-tenant leak is structurally impossible.

### 2.8 Teammate [RATIFIED]

`shell/apps/spokespeople/models.py`. Not restated here; relevant only
because `teammate.universe` scopes retrieval and `EpisodeCast.teammate`
scopes participation.

### 2.9 `shell/apps/memory/` [REPO — SCAFFOLD ONLY]

`ls` + `wc -l`: `__init__.py` 0, `models.py` 0, `views.py` 0,
`admin.py` 0, `urls.py` 0, `apps.py` 6, `migrations/__init__.py` 0.
There is no model, no migration that defines a table, no service, no
view, no admin, no URL. The app label exists and nothing else. Treat
as an unclaimed namespace, not an existing substrate.

### 2.10 `shell/apps/conversations/` [REPO — TRANSCRIPT, NOT NARRATIVE MEMORY]

Models: `ConversationThread`, `ConversationMessage` (turn transcripts
with per-message `verification_status`, `verification_warnings`,
`rejected_synthesis`; SESSION 138 K6.4 parity), `ConversationEmbedding`
(pgvector on message chunks; separate table from `KnowledgeChunk` per
K2 privacy contract). Retrieval: `retrieve_for_thread()` reads
same-thread `ConversationEmbedding` + `retrieve_for_teammate` docs.
**Consumed only by realtime avatar sessions.** Not consumed by
`synthesize_dialogue()`; not consumed by `synthesize_script()`; not
cross-thread; not summarized durably; not narrative-scoped.

`shell/character_os/realtime_memory.py::build_memory_projection()`
summarizes the prior three RealtimeSessions' TRANSCRIPT assets via
gpt-5 into a markdown blob that is injected into the *next* session's
Runway document. The summary is ephemeral per session; nothing is
persisted to the database. This is the closest thing the repo has to
"memory across sessions," and it does not feed the Composition
synthesis path at all.

### 2.11 Approval / audit / evidence substrates already in place

- `shell/apps/bootstrap_review/` [RATIFIED, SESSION 249] — decision
  journal (append-only JSONL, immutable, supersedes chain,
  amendment_reason required), promotion service (five-phase workflow,
  race-safe via `BootstrapEvidenceIndex.frozen_candidate_id` unique
  constraint, retry-idempotent via `PromotionAudit.decision_id`
  unique), five-phase materialization: validate → copy bytes → DB
  transaction → publish immutable revision folder → mark
  `evidence_published_at_utc`. Currently scoped to identity-reference
  promotion (portrait / avatar fixtures). Pattern shape is directly
  reusable.
- `shell/apps/identity/services.py` [RATIFIED, SESSION 241 / 243] —
  transactional approval state machine (`draft → approved → superseded`
  or `→ rejected`), enforced by Postgres partial unique constraint
  `one_approved_per_character_identity`, protected by `select_for_update()`.
  `approve_version()`, `approve_reference()`, `approve_bundle()` with
  cascade-supersede and idempotent re-approval.
- `shell/apps/publish/` [RATIFIED] — bundle/variant state machines
  (DRAFT → LAUNCHING → IN_FLIGHT → COMPLETED / PARTIAL / FAILED).
  Publication is an act, not a narrative acceptance; it is a fan-out
  to platform variants.
- `shell/apps/transcripts/` — `TranscriptHighlight` state machine
  (PENDING → APPROVED → RENDERED, or PENDING → REJECTED). Workspace
  scoped. Transcript-mining approval only.

None of the above touches narrative memory; all are pattern shapes
that a future narrative-memory promotion could imitate.

### 2.12 Absent substrates

Searched exhaustively [REPO — Explore agents, this audit]:

- No `WorldEntity`, `Relationship`, `Location`, `Place`, `Organization`,
  `Business`, `Event`, `Promise`, `Retcon`, `Occurrence`, `NarrativeMemory`,
  `EpisodeHistory`, `WorldHistory`, or `MemoryClaim` model anywhere in
  `shell/apps/`.
- No `canon` model. `retrieve_universe_canon` is a function, not a
  table.
- No `final_composition` / `canonical_composition` / `accepted_composition`
  FK on Episode.
- No `TODO` / `FIXME` / `DEFERRED` comments in production code
  referencing memory, canon, promotion, narrative, or history. The
  deferrals are in the design docs, not in the code.

---

## 3. Prior Ratified Decisions

### 3.1 Universe substrate [SESSION 261 — RATIFIED]

Universe is the inner wall inside Workspace. Retrieval isolation is
enforced by the nine-row truth table
(`UNIVERSE_BOUNDARY_V1.md` §Q10) in `retrieve_for_teammate` at
`retrieval.py:186–206`. Cross-Universe access is not exposed as a
primitive; explicit crossover is deferred
(`UNIVERSE_BOUNDARY_V1.md:665–669`). Hard-delete of a populated
Universe is blocked via child `RESTRICT` FKs.

### 3.2 Episode substrate [SESSION 262 — RATIFIED]

Episode owns story-authoritative `operator_topic`, `title`, and
operator-declared `cast`. Explicit creation only (H3;
`EPISODE_LIFECYCLE_V1.md:156`). Auto-creation on Composition create
(H5) was explicitly considered and rejected by the same argument
`UNIVERSE_BOUNDARY_V1.md §Q8` used against auto-default Universe.
Cardinality is 1:N (`EPISODE_VS_COMPOSITION_V1.md:80–92`). Episode
close, acceptance, or canonicalization was not specified.

Design deviations ratified in code: DEV-1 (`Episode.universe = CASCADE`
vs design RESTRICT — required for Workspace cascade), DEV-2
(`Composition.episode = RESTRICT` vs design PROTECT — RESTRICT
participates in Django shared-CASCADE-parent). Both preserve the
operator-facing "populated stories can't be silently wiped" guarantee
via API preflight + DB backstop.

### 3.3 Composition observability [SESSION 262 — RATIFIED]

Nine immutable-once-populated fields (§2.4). Enforcement: `from_db()`
snapshot + `save()` guard that respects `update_fields`, so legitimate
lifecycle writes (status, cost, verification, final_asset,
synthesized_brief, knowledge_chunk_ids, writing_contract_version)
remain freely mutable while the observability set becomes
immutable-once-populated. `EPISODE_SCHEMA_V1.md` explicitly notes that
this immutability set is designed to survive future Episode-attach /
detach mutations — attach/detach must not disturb them, and it doesn't.

### 3.4 Universe canon retrieval lane [SESSION 263 — RATIFIED, DOGFOOD-VERIFIED]

Slice B (separate shared-canon pass) + Slice C.1 (scope-aware SHARED
promotion). Verified on Episode `f90ce54f-07f9-4511-aaba-9078dc232446`
"AI took over the lab" @ 60 s, producing Composition
`3e44b728-34d0-4b14-9b3a-cfb0167d243e` in which canon chunk
`da7e6553-a5ea-463f-994f-354289ab9b5b` (doc `f309469c-...`) entered
`Composition.knowledge_chunk_ids` ahead of the five Patch and five
Rivet K2 chunks. All three acceptance criteria met (canon in
chunk_ids, canon language in accepted turns, no accepted turn
contradicts canon).

Deferred inside the SESSION 263 audit:
- U1: distance floor / relevance ceiling — deferred until bloat is
  observed.
- U2: configurable `shared_top_k` — currently fixed at 2.
- U3: canon lane in non-dialogue consumers (talking-head, ask,
  realtime).
- U4: separate `canon_chunk_ids` observability field (canon-first
  ordering in `knowledge_chunk_ids` gives ordering-based provenance
  today).
- U5: query-independent canon injection.
- U6: canon-authoring SPA affordance.
- U7: Universe schema field for explicit canon listing.

### 3.5 Relationship [DEFERRED — DESIGN COMPLETE, NO CODE]

`RELATIONSHIP_BOUNDARY_V1.md` establishes the Patch/Rivet/Ruby/Mason
stress-test (lines 109–150). Position taken: R2 (Universe-owned
canonical rows, pre-Episode). Explicit deferrals include narrative
memory, Location/Place, Organization/Business, canon promotion for
Relationships, and automatic relationship inference from Episode
co-occurrence. `SESSION_263_CLOSEOUT.md:303–310` reaffirms the
deferral pending Episode dogfood evidence.

### 3.6 WorldEntity [DEFERRED — NO DESIGN DOC]

Named as future work in `UNIVERSE_BOUNDARY_V1.md` and
`SESSION_261_UNIVERSE_SUBSTRATE_IMPLEMENTATION.md:246–256`. Companion
concept `Episode.referenced_entities` M2M is also deferred.

### 3.7 Narrative memory / event log / promise ledger / canon promotion [DEFERRED]

All four named in `SESSION_261_UNIVERSE_SUBSTRATE_IMPLEMENTATION.md`
lines 246–256 and `SESSION_262_CLOSEOUT.md:192–214`. No design started.
`SESSION_263_CLOSEOUT.md:303–310` states: *"Narrative memory /
callback design is deferred, but the Episode boundary must not
preclude this."* This session (SESSION 264) is the first to open the
question.

### 3.8 Multi-tenant isolation [RATIFIED — ENFORCED IN RETRIEVAL]

Workspace privacy invariant preserved (`UNIVERSE_BOUNDARY_V1.md:642`).
Universe privacy invariant new-and-enforced (`UNIVERSE_BOUNDARY_V1.md:649–656`).
No implicit crossing primitive (`UNIVERSE_BOUNDARY_V1.md:665–669`).
Enforcement point is the branching predicate in
`retrieve_for_teammate` — same enforcement point applies to the SESSION
263 canon lane.

### 3.9 Conflicts noted

`shell/apps/universe/models.py:270–277` docstring on `Episode.universe`
refers to `Composition.episode = PROTECT`, but the actual on_delete is
`RESTRICT` (DEV-2). The docstring is stale relative to the migration
`0016_composition_episode_restrict.py`. Not blocking; noted for future
cleanup. Semantics of RESTRICT vs PROTECT are equivalent for the
operator-facing guarantee.

No other current-runtime-vs-design conflicts identified.

---

## 4. Truth-Boundary Model

Prior sessions did not enumerate the truth categories. This audit
proposes the following as evidence-based distinctions [INFERENCE +
NEW RECOMMENDATION for the vocabulary; underlying substrates are all
[RATIFIED] or [DEFERRED]]:

| # | Category | Authored by | Substrate today | Substrate need |
|---|---|---|---|---|
| 1 | **Operator truth** | Human | `KnowledgeDocument` corpus, `Teammate.business_brief`, identity fields, `Episode.operator_topic`, `Composition.operator_topic` | None new. |
| 2 | **Static Universe canon** | Human via `KnowledgeDocument` (Universe-broadcast or shared-tier) | `KnowledgeDocument` + `retrieve_universe_canon` | None new. |
| 3 | **Character truth** | Human via K2 (per-Teammate M2M) | `KnowledgeDocument` + `retrieve_for_teammate` | None new. |
| 4 | **Episode premise** | Human | `Episode.operator_topic` (story-level), `Composition.operator_topic` (per-attempt copy) | None new. |
| 5 | **Episode occurrence** | Synthesis (LLM) + operator acceptance | `Composition.first_pass_synthesis`, `Composition.corrective_pass_synthesis`, `Composition.synthesized_brief`, `Composition.render_dispatched_at`, `Composition.status`, `Composition.verification_status` | An operator-acceptance signal on a *specific* Composition attempt. See §6. |
| 6 | **Writer invention** | Synthesis (LLM) | Same as 5 | Must be **inert by default** — never persists beyond the Composition attempt unless promoted. |
| 7 | **Narrative memory** | Operator promotion of a category-6 detail from a specific Composition attempt | **None.** | New substrate — see §13. |
| 8 | **Canon (static)** | Human via `KnowledgeDocument` | Same as 2. | None new; but see §8 for the rule that Category-7 does not silently become Category-8. |

**Key claim (Categories 7 vs 8):** narrative memory is distinct from
canon, and this distinction is load-bearing.

- **Canon** is a stable world fact the operator maintains as a
  `KnowledgeDocument`. A canon change is a document write. It is
  authored, versioned via document revisions, and retrieved in the
  SHARED block of every future Composition in that Universe.
- **Narrative memory** is a "this happened in the story of this
  Universe" fact promoted from a specific accepted Composition. It is
  not a world rule; it is an event or a callback. It should NOT be
  retrieved in the SHARED block by default because it is subordinate
  to canon and voluntary rather than mandatory.

Collapsing them into a single "canon" table would be a category error:
promoting jokes and one-off events to the same tier as author-authored
world rules would flood the SHARED block over time (Audit 11), and
would make it impossible for the operator to distinguish "the workshop
has a 3D printer" (durable canon) from "the printer once tried to make
Patch a throne" (a callback that may or may not survive the next
retcon).

---

## 5. Printer-Episode Fact Classification

Using SESSION 263's actual accepted Composition `3e44b728-...`
("AI took over the lab") as the concrete example. Facts named in the
SESSION 264 prompt classified against §4:

| # | Fact | Category | Was it known pre-Episode? | Should be Narrative Memory candidate? | Should be Canon candidate? |
|---|---|---|---|---|---|
| A | Patch and Rivet work in the workshop. | 1 + 2 (operator + static canon) | Yes — `Teammate` + shared canon doc (`f309469c…`). | Redundant. | Already is (implicit in K2 + shared canon). |
| B | The workshop has a 3D printer. | 2 (static canon) | Yes — asserted in the shared canon doc. | Redundant. | Already is. |
| C | Patch connected an AI agent to workshop tools. | 6 → 7 (writer invention, promotable) | No. Not in pre-Episode canon. Introduced by synthesis. | Eligible — this is the *inciting circumstance* the story turns on. Callback-worthy. | **No, not automatically.** Canonizing this would assert as durable world-truth that "Patch has AI-connected workshop tools." Operator authority required. |
| D | The printer started a job Patch did not queue. | 6 → 7 | No. Writer-invented occurrence within the story. | Eligible — this is the "printer incident." Compact-memory candidate. | No — this is an event, not a durable rule. |
| E | Two agents coordinated ("formed a committee"). | 6 → 7 | No. Writer-invented backstory reveal inside the accepted turn. | Eligible — high callback value. | No. |
| F | Patch joked the printer might print him a throne. | 6 (writer invention, dialogue color) | No. | **Weakly eligible.** Great callback material; but this is dialogue color, not an event that happened in-world. See §6 on the "was said" vs "happened" distinction. | No. |
| G | Rivet revoked access / paused tokens. | 6 → 7 | No. Writer-invented action. | Eligible — a definite action, not just talk. | No. |
| H | Patch enabled a sandbox afterward. | 6 → 7 | No. Writer-invented outcome. | Eligible — outcome/promise for future episodes. | No. |

Two observations:

1. **Everything eligible for memory is a category-6 writer invention.**
   Facts already in canon (A, B) do not need memory because they are
   already retrieved as canon. This is why narrative memory does not
   compete with canon at the fact level — it competes at the retrieval
   surface (§10).
2. **The "was said" vs "happened" distinction (F vs D, E, G, H).**
   Some inventions are dialogue color (a joke); others are asserted
   in-world events (an agent was connected; the printer job started;
   Rivet paused tokens). If a future Episode's Rivet references the
   throne joke, that is a callback to *what was said*. If a future
   Episode says "the printer is acting weird again," that is a
   callback to *what happened*. Both need to be representable in the
   memory tier, but they carry different weight and should be labeled
   as such by the operator at promotion time.

**Nothing on this list should be automatically promoted.** All of C
through H are candidates only. The operator promotes what they want
the world to remember.

---

## 6. Episode-Authority Findings

Question: what artifact is authoritative today for the claim "this
Episode happened"?

**Answer today [REPO]: nothing is.** Episode has no state field. No
Composition has an `accepted` flag from an operator. `render_dispatched_at`
means a Composition sent to media-engine, not that the operator liked
it. `verification_status = VERIFIED` means the K6.4 verifier passed on
generated turns; it does not mean the operator accepted the render as
the story's occurrence. `status = COMPLETED` means the render pipeline
finished; it means nothing narratively. `PublishBundle` and
`PublishVariant` are act-of-publication state machines for platform
distribution; they are not narrative acceptance either.

Consider the case the SESSION 264 prompt describes:

> Episode → Composition attempt 1 fails → Composition attempt 2
> succeeds → Composition attempt 3 produces a different version.

Today: attempt 1 is a FAILED row; attempts 2 and 3 are COMPLETED rows
with different `synthesized_brief` values. No field on Episode says
which one is "the story." No field on Composition says "this is the
one." The 1:N cardinality is intentional
(`EPISODE_VS_COMPOSITION_V1.md:80–92`) and it was ratified without a
"which one wins" affordance.

**This is the load-bearing gap SESSION 264 exposes.** Any narrative
memory pipeline requires a signal that says "this specific Composition
is the version of the story we're extracting memory from." The signal
does not exist today.

Ways this could be modeled (audit reviews, does not choose here):

1. **Episode owns a nullable `accepted_composition` FK.** Simple. One
   accepted per Episode. Aligns with the identity-versioning shape
   (`CharacterIdentityVersion.state = APPROVED` — one at a time).
2. **Composition owns a nullable `narrative_status` enum** — for
   example: `PROVISIONAL / ACCEPTED / SUPERSEDED / REJECTED`. Aligns
   with `IdentityReference.state`.
3. **A separate `EpisodeAcceptance` row (append-only journal)** —
   mirror of `bootstrap_review.PromotionAudit`. Records "operator X at
   time T accepted Composition Y for Episode Z, superseding
   acceptance A."

§13 recommends option 3 for the smallest slice because it decouples
narrative acceptance from the immutability discipline on Composition
observability, keeps Composition ignorant of narrative promotion, and
inherits the bootstrap-review append-only pattern the repo already
runs.

Additionally clarify:
- **Does rendering imply narrative acceptance?** No. Render is
  machinery. `render_dispatched_at` and `status=COMPLETED` are
  automation signals.
- **Does verification imply narrative acceptance?** No. `VERIFIED`
  means claims-verifier didn't reject; it does not mean the operator
  approved the arc, cast performance, tone, or truth of the story.
- **Does publication imply narrative acceptance?** No. Publication is
  a distribution act (`PublishBundle`), orthogonal to whether the
  operator wants the story to matter narratively next time.

---

## 7. Existing Memory-System Suitability

Question: can any existing surface be repurposed for narrative memory?

| Candidate | Suitability | Why / why not |
|---|---|---|
| `shell/apps/memory/` | **Namespace only.** | Empty scaffold — no cost to claim the label, no substrate to reuse. If a NarrativeMemory model lands, this is where it should live, matching the app-per-concern shape. |
| `shell/apps/conversations/` (`ConversationMessage`, `ConversationEmbedding`) | **Not suitable.** | Turn transcripts for realtime avatar sessions; per-spokesperson, per-thread. Not linked to Episode or Composition. Not consumed by dialogue synthesis. Overloading it would confuse "chat memory" (Runway avatar) with "story memory" (episode dogfood). |
| `shell/character_os/realtime_memory.py::build_memory_projection()` | **Wrong scope.** | Summarizes 3 prior avatar sessions into next Runway document. Ephemeral string, not DB-persisted, per Teammate not per Episode/Universe. Its pattern (LLM-summarize-N-into-projection) is worth studying for §13 but the code itself is not reusable. |
| `bootstrap_review.PromotionAudit` / `BootstrapEvidenceIndex` | **Pattern reusable; row not reusable.** | Append-only decision journal + race-safe evidence dedup + retry idempotency via unique key. The exact shape a narrative-memory promotion needs. Do not reuse the row; imitate the pattern. |
| `identity.services.approve_version()` and friends | **Pattern reusable; row not reusable.** | Transactional approval with `select_for_update()`, cascade supersede, Postgres partial unique. The exact shape a "one accepted Composition per Episode" acceptance needs. Do not reuse the row; imitate the pattern. |
| `Composition.knowledge_chunk_ids` | **Cite-provenance only.** | Records which chunks fed a render. Not writable for memory purposes. |
| `Composition.synthesized_brief` | **Rendering output; not memory.** | Immutable-per-render text of accepted synthesis. Fine as the *source* of a memory extraction, not as the memory itself (see §12). |
| `Composition.first_pass_synthesis` / `corrective_pass_synthesis` | **Provenance only.** | Same — source, not memory. |
| `KnowledgeDocument` (Universe-broadcast or shared-tier) | **Wrong tier.** | Promoting narrative to `KnowledgeDocument` would blur the canon vs memory distinction (§4) and would cause narrative to compete with static canon in the SHARED retrieval block (§10). Also, unlike `KnowledgeDocument`, memory needs to reference a specific Composition and record an acceptance decision. |

Conclusion: the pattern shapes exist; the concept-owning substrate
does not. `shell/apps/memory/` is the right namespace.

---

## 8. Canon-Promotion Boundary

**Rule proposed [NEW RECOMMENDATION]:** synthesis-generated dialogue
MUST NEVER mutate a `KnowledgeDocument`. Ever. Automatically or
otherwise.

Rationale:

1. `KnowledgeDocument` is the substrate the operator directly authors.
   It has status transitions, embedding batches, and downstream
   invariants (Universe consistency, M2M consistency at
   `models.py:279–303`). It participates in the SHARED retrieval block
   which becomes the assumed factual basis of *every* future
   Composition in the Universe.
2. Once a synthesized claim enters the SHARED block, the K6.4 verifier
   will validate future claims against it, and future synthesis passes
   will treat it as ground truth. If a joke ("the printer might print
   him a throne") accidentally enters this tier, every future Rivet
   turn is subject to a factual basis that includes a joke — and the
   verifier can license further inventions against it, compounding
   the drift.
3. `KnowledgeDocument` is also the tier the vet, teacher, plumber, and
   entertainment customer cases (Audit 8) *most need protected*.
   Silent auto-canonization of a synthesis-invented "we replaced Mrs.
   Carter's water heater last Tuesday" would create real customer
   history that the operator neither authored nor approved. That is
   an unacceptable safety property to sacrifice for any convenience.

The narrative memory tier proposed in §13 is deliberately a *different
tier* from canon. Even at maximum operator authority, a memory
promotion does NOT write a `KnowledgeDocument`. It records "this thing
happened / was said in the story of this Universe," attached to
Episode + Composition, retrievable through a separate lane. If the
operator wants a memory to graduate into durable world truth, that is
a second, explicit authoring act: they open the canon document and
write the fact themselves. Two-step promotion is not friction; it is
the safety property.

---

## 9. Operator-Authority Boundary

Given §7 (approval pattern shape available) and §8 (memory ≠ canon),
the following authority model is proposed [NEW RECOMMENDATION,
imitating RATIFIED patterns]:

| Action | Automatic? | Operator required? |
|---|---|---|
| Composition attempt is created / renders. | Auto. | No. Machinery. |
| Composition attempt is marked `render_dispatched_at`, `status`, `verification_status`. | Auto. | No. Machinery. |
| A candidate memory row is created from an accepted Composition's turns. | **Not proposed for auto in v1.** | Yes. Operator explicitly says "extract candidate memories from this Composition." |
| A candidate memory is promoted to `remembered` (durable, retrievable next Episode). | **Never auto.** | Yes. Operator explicitly promotes. |
| A `remembered` memory becomes `superseded` because a later Episode contradicts it. | **Never auto.** | Yes. Operator explicitly supersedes. |
| A `remembered` memory is deleted or the operator retcons it. | **Never auto.** | Yes. Operator explicitly deletes / retcons. |
| Synthesis mutates a `KnowledgeDocument` (canon). | **NEVER, EVER.** | See §8. Canon is authored by the operator directly, always. |

Corrections and deletion:

- **Corrections** are new promotions that supersede prior memories via
  a chain (imitate `bootstrap_review` supersedes pattern; append-only
  journal, current derived by walking the chain).
- **Deletion** should soft-delete (mirror `archived_at` on Universe /
  Episode), never hard-delete, so audits can reconstruct what was
  once remembered.
- **Conflicts with later canon:** if `KnowledgeDocument` is edited such
  that a durable memory now contradicts canon, the memory does not
  auto-invalidate. It stays retrievable with a stale flag that the
  operator can review. Canon always wins in the SHARED block (§8).

**"Can canon EVER be created from synthesis without approval?"** No.
This is the audit's single unequivocal rule.

**"Can a memory be true-for-story but not static canon?"** Yes. That
distinction is exactly why narrative memory exists as a separate tier.
See the entertainment vs vet/plumber/teacher analysis in §12.

---

## 10. Retrieval Architecture Analysis

The SESSION 263 audit established a **two-lane architecture** —
per-character K2 (top_k=5) + Universe shared canon (top_k=2) — with
strict SCOPE RULE separation and canon-first ordering in
`Composition.knowledge_chunk_ids`.

The question: where does narrative memory retrieval belong?

**Options considered:**

- **Fold into `retrieve_universe_canon`.** Rejected. Memory would
  displace canon (only top_k=2 slots) or force `shared_top_k` inflation
  (a SESSION 263 U2 deferral). More importantly, memory and canon
  answer different questions (§4) and should not compete for the same
  budget.
- **Fold into `retrieve_for_teammate`.** Rejected. K2 is per-character;
  memory needs to be visible to some-but-not-all-cast configurations
  and needs Episode scoping, which K2 does not have. Would break the
  contract rule 2 privacy boundary.
- **Add a third lane, `retrieve_universe_memory(workspace, universe,
  cast, episode?, query, top_k)`.** [NEW RECOMMENDATION] Its own thin
  function, its own budget (proposed top_k=1 or 2 for v1), its own
  prompt block (`--- EPISODE / NARRATIVE MEMORY (may cite past
  events; canon wins on conflict) ---`), rendered between SHARED
  WORLD KNOWLEDGE and CHARACTER SCOPED KNOWLEDGE in the factual basis
  section. Ordering-based provenance in `Composition.knowledge_chunk_ids`
  can be extended (canon → memory → per-character) or a separate
  `memory_chunk_ids` field can be added if U4 lands.

**Contamination risks and mitigations:**

- **Memory bleeding into SHARED block via C.1.** The
  `_is_scope_shared_document` promotion only inspects
  `KnowledgeDocument.spokespeople` M2M count. Since narrative memory
  is NOT a `KnowledgeDocument` (§8), the C.1 helper cannot see it.
  The lane stays clean.
- **Cross-cast leakage.** Memory carries per-Episode cast context. The
  retrieval filter should enforce Episode.universe ==
  <this-universe> AND (memory cast subset overlaps this cast). See
  §13 for the concrete predicate.
- **Prompt bloat.** Top_k=1 for v1. If bloat is observed, tune (U1
  from SESSION 263).
- **K6.4 verifier participation.** Memory chunks entering the factual
  basis are grounds for citation, so K6.4 must see them. Same
  treatment as canon chunks — pass through to each speaker's factual
  corpus. Weight: canon wins if they conflict; memory is subordinate.

**Multi-tenant scope enforcement.** Same enforcement point as
`retrieve_for_teammate` and `retrieve_universe_canon`:
Workspace-derivation from a required parameter, Universe filter as an
unconditional branch, cross-Universe cast rejected defensively. No
override, no bypass. Mirror the SESSION 263 lane precisely.

**Load-bearing:** memory retrieval must NOT run over dialogue that
was never operator-accepted. That is the entire point of the
promotion boundary in §9.

---

## 11. Growth / Lifecycle Risks

Static canon grows slowly and is human-authored. Universe canon
retrieval today observes at most a handful of shared-tier docs per
Universe.

Narrative memory has a different growth profile:

- **Per-Episode multiplication.** Every accepted Episode produces
  candidate memories. Even if only 10–20% promote, a Universe that
  runs 100 Episodes/year yields 100–500 durable memory rows in year
  one alone.
- **Contradictions.** Later Episodes will contradict older memories.
  Retcons need to be first-class (§9: supersede pattern, journal-driven).
- **Duplicates.** The printer incident may be memory-worthy multiple
  times if operators promote from multiple Episodes' recaps. Dedup by
  `(episode_id, chunk_text_hash)` or similar.
- **Stale memories.** A memory promoted early may be effectively
  forgotten later (nobody ever calls back to it). Retrieval must
  distance-rank against the current query; low-frequency retrieval is
  fine, but bloat in the corpus is not.
- **Character-specific awareness.** Some memories are witnessed by
  only part of the cast. Mason approached Patch (Episode A);
  subsequent Patch+Rivet Episode B may reference Mason; Rivet was
  never there, but *knows* because Patch told him — or does not know,
  because Patch did not. That is a *narrative* fact ("who knows what")
  the operator must be able to encode when promoting a memory.

For v1 the recommendation (§13) intentionally keeps this simple: memory
rows carry an optional `witnessed_by` cast subset (nullable = the
whole Episode cast). Retrieval filters against the *current* cast's
overlap. Growth risks (staleness, contradictions, duplicates) are
addressable but should not block v1; they should be measured on the
first real dogfood corpus.

**Do we eventually need separate WORLD HISTORY vs CHARACTER MEMORY
concepts?** Not for v1. The `witnessed_by` subset carries character-
specific awareness in the row itself, without introducing a second
substrate. Only if promotion volume outstrips retrieval quality
should this be revisited.

---

## 12. Customer Reproducibility Test

The recommendation in §13 was designed to pass all four cases
simultaneously. Testing:

### Case A — Education (Ms. Mole and the moon)

A generated Episode says "Ms. Mole blew up the moon yesterday."
Under the recommendation:
- The Composition renders. `synthesized_brief` contains the joke.
- Nothing is auto-promoted. No memory row is created without the
  operator's explicit act.
- The teacher opens the accepted Composition, looks at the recap,
  and decides not to promote the joke.
- Even if the teacher clicked "promote" on this line, it would land
  in the *memory tier* (not canon). It would surface in the memory
  block of future Compositions with the flag "past event, canon
  wins," and the teacher can supersede or retract it. It would
  never enter the canon corpus (`KnowledgeDocument`), which the
  teacher would author separately.

Pass.

### Case B — Plumbing business (Mrs. Carter's water heater)

An Episode invents "We replaced Mrs. Carter's water heater last
Tuesday." Under the recommendation:
- Nothing is auto-promoted. No customer history is written silently.
- The plumber sees the invented fact, decides it is dangerous
  (Mrs. Carter is a real customer or a hypothetical one and either
  way this cannot enter their books), and does not promote.
- No `KnowledgeDocument` ever mutates.

Pass.

### Case C — Veterinary practice (invented pet diagnosis)

Same shape as B. Nothing durable. Promotion is opt-in and lands only
in memory tier, not in canon or in any customer-facing artifact.

Pass.

### Case D — Entertainment creator (dragon destroys the bakery)

The creator produces an Episode where a dragon destroys the bakery.
They love it. They want future Episodes to remember it.
- The creator opens the accepted Composition, marks turns as
  memory-worthy, and promotes.
- Memory rows land in the Episode's memory tier, visible to the cast
  who witnessed it.
- Next Episode: the memory surfaces in the memory retrieval block.
  The synthesizer can produce a callback naturally.
- If the creator later decides the dragon-bakery event should become
  durable world canon (e.g., the bakery is now permanently gone),
  they open the canon doc and author it — a deliberate second act.

Pass. All four cases pass because the automatic behavior is: nothing
is promoted, ever, without explicit operator action; and promotion
lands in memory, never in canon.

---

## 13. Minimum Viable Continuity Architecture

The smallest addition that lets the operator prove episodic
continuity end-to-end while preserving §8 and §9 [NEW RECOMMENDATION;
sequencing in §15]:

### 13.1 One new substrate: `apps.memory.NarrativeMemory`

Owned by Episode; ties to a specific Composition attempt; records
promoted text + provenance + operator decision.

Sketch of the fields (not a schema proposal; a shape):

```
NarrativeMemory
    id (UUID)
    episode (FK → universe.Episode, RESTRICT)
    source_composition (FK → compositions.Composition, RESTRICT)
    workspace (FK → accounts.Workspace, CASCADE) [denormalized for tenant filter]
    universe (FK → universe.Universe, CASCADE) [denormalized for retrieval filter]

    kind: enum {EVENT, ACTION, PROMISE, DIALOGUE_CALLBACK, WORLD_DETAIL}
    body: TextField           # the compact memory text (operator authors from turn)
    witnessed_by: M2M(Teammate) blank=True # subset of cast; empty = whole cast
    weight: enum {CENTRAL, PERIPHERAL}    # optional; hint for retrieval scoring
    embedding_vector (pgvector, populated by background job)

    promoted_by (FK → User, SET_NULL)
    promoted_at (auto)
    supersedes (self FK nullable)          # retcon chain
    superseded_at (nullable)
    superseded_reason (TextField, blank)
    archived_at (nullable)                 # soft-delete
    created_at / updated_at
```

- **Never touches `KnowledgeDocument`.** Ever.
- **Immutable body** after promotion (imitate SESSION 262
  observability guard).
- **Supersede via journal** (imitate `bootstrap_review`).
- **Universe-scoped tenant filter** (imitate `retrieve_for_teammate`).

### 13.2 One new retrieval function: `retrieve_universe_memory`

```
retrieve_universe_memory(workspace, universe, cast, query="", top_k=1)
    filter: workspace=<given>, universe=<given>,
            archived_at IS NULL,
            superseded_at IS NULL,
            (witnessed_by is empty OR witnessed_by ∩ cast is non-empty),
            embedding cosine-ranked to query,
            LIMIT top_k
```

Called once per synthesis from `synthesize_dialogue` alongside
`retrieve_universe_canon`. Non-fatal on failure — degrade to no
memory chunks and log a warning (same shape as SESSION 263 canon
lane's degradation).

### 13.3 One new prompt block

Between SHARED WORLD KNOWLEDGE and CHARACTER SCOPED KNOWLEDGE in
`_build_factual_basis_section`:

```
--- EPISODE / NARRATIVE MEMORY (past events in this Universe; canon wins on conflict) ---
[memory rows in cosine order, up to top_k=1 or 2]
```

Add `memory_chunk_ids` to `Composition.knowledge_chunk_ids` as a
third-tier ordering (canon → memory → per-character), or add a
separate `Composition.memory_ids` observability field (mirrors U4
from SESSION 263).

### 13.4 One new operator action: promote turns from an accepted Composition

- Operator opens an accepted Composition detail page.
- Marks turns (or arbitrary text spans) as memory-worthy, picks
  `kind` + optional `witnessed_by`.
- Backend creates `NarrativeMemory` rows tied to `episode` +
  `source_composition`, kicks a background job to embed.

### 13.5 One new operator authority signal: Episode acceptance

Because §6 exposed that Episode acceptance is not currently
represented, memory promotion needs a "which Composition is this
Episode's accepted version" concept. Two forms:

- **Minimal:** the promotion action itself is the acceptance. If the
  operator promoted from Composition X, then Composition X is
  implicitly the accepted one for this Episode. Add
  `Episode.accepted_composition` nullable FK, set on first promotion,
  can be moved by operator.
- **Deferred to later slice if we do not want to change Episode
  schema in v1:** encode acceptance inside `NarrativeMemory` rows via
  `source_composition` alone. Retrieval never surfaces memories from
  non-accepted Compositions because non-accepted ones have no memory
  rows. This is the tightest coupling and does not require an Episode
  schema change.

§15 recommends the deferred form for the first slice.

### 13.6 What the printer scenario looks like end-to-end

**Episode 1** ("AI took over the lab"). Composition
`3e44b728-...` renders successfully. Operator opens the Composition
detail page, sees turns from Patch and Rivet, marks:

- "Patch connected an AI agent to the workshop tools" → EVENT,
  witnessed_by = {Patch, Rivet}
- "The printer started a job Patch did not queue" → EVENT,
  witnessed_by = {Patch, Rivet}
- "Two agents coordinated / formed a committee" → EVENT,
  witnessed_by = {Patch, Rivet}
- "Rivet paused tokens" → ACTION, witnessed_by = {Patch, Rivet}
- "Patch enabled a sandbox afterward" → ACTION, witnessed_by =
  {Patch, Rivet}
- (Optionally the throne joke as DIALOGUE_CALLBACK.)

Five to six `NarrativeMemory` rows land in `apps.memory`. Nothing
mutates in `KnowledgeDocument`. Static canon (`da7e6553-...`,
`f309469c-...`) is untouched.

**Episode 2** ("The printer is acting weird again"). Operator creates
an Episode with `operator_topic = "The printer is acting weird again"`,
cast = {Patch, Rivet}. Composition attempt fires. `synthesize_dialogue`
calls:

- `retrieve_universe_canon(...)` — returns the static workshop canon
  chunk as before.
- `retrieve_universe_memory(...)` — returns 1–2 memory rows most
  cosine-relevant to "printer acting weird": the "printer started a
  job Patch did not queue" and possibly the throne joke.
- `retrieve_for_teammate(Patch)` / `retrieve_for_teammate(Rivet)` —
  returns per-character K2 as usual.

Prompt factual basis section shows:
- SHARED: workshop canon.
- MEMORY: printer incident + throne joke (with the "canon wins on
  conflict" note).
- Patch SCOPED: Patch's K2.
- Rivet SCOPED: Rivet's K2.

The LLM has natural material for Rivet to say the "define weird…
last time it tried to make you royalty" callback the SESSION 264
prompt hopes for. It has this material because the operator
promoted it — not because the model invented it a second time.

---

## 14. Alternatives Considered

- **Auto-extract memory from every rendered Composition.** Rejected —
  fails all four Audit 8 cases (education, plumbing, vet), and
  violates §9. If any variant of this is ever wanted, it must be
  behind a Universe-level opt-in with a review queue, not the default.
- **Fold memory into `KnowledgeDocument` (write synthesis output as a
  new canon doc).** Rejected — violates §8 unconditionally.
- **Fold memory into `Composition.synthesized_brief` retrieval.** No
  substrate change but forces the retriever to embed every accepted
  synthesis and rank against them; produces exactly the "stuff old
  transcripts into future prompts" outcome Audit 6 explicitly rejects.
- **State-machine Episode without adding a memory substrate.** Adds
  the acceptance signal (§6) but does not answer §5 promotion or
  §10 retrieval — leaves the load-bearing question unsolved.
- **Introduce Relationship and WorldEntity before NarrativeMemory.**
  Would be premature per SESSION 263 closeout guidance
  (`SESSION_263_CLOSEOUT.md:303–310`). Relationship and WorldEntity
  address a different question (referenced but absent characters,
  structured world facts). Memory is the load-bearing continuity
  primitive; Relationship / WorldEntity become natural extensions
  once the memory shape is proven. See §16 non-goals.
- **Approach the problem in the dialogue synthesis code alone
  (retrieve accepted compositions' briefs at runtime).** Would work
  for exactly one scene, then break because there is no acceptance
  signal, no promotion, no operator authority, and no `witnessed_by`
  concept. Rejected — same objection as "fold into
  `Composition.synthesized_brief`."

---

## 15. Recommended Implementation Sequencing

Everything below is a proposal for future sessions. This session
implements nothing.

**Slice 1 — NarrativeMemory substrate (minimal).**

- New model `apps.memory.NarrativeMemory` per §13.1.
- Migration adds table + indexes + Universe-consistency `clean()`.
- No changes to Composition, KnowledgeDocument, or Episode schemas.
- No retrieval integration yet.
- Operator-side write path is a DRF endpoint on Composition (POST
  `/api/compositions/<id>/promote-narrative-memory/`) that accepts a
  list of (body, kind, witnessed_by, weight) tuples and creates rows.
- Background job embeds the row body into `embedding_vector`.
- Test coverage: cross-Universe rejection, cross-Workspace rejection,
  supersedes chain, soft-delete.

**Slice 2 — Retrieval lane.**

- New `retrieve_universe_memory` function in `apps.embeddings.retrieval`
  (keeps the retrieval-privacy contract intact).
- `synthesize_dialogue` calls it alongside `retrieve_universe_canon`
  with default `top_k=1`.
- `_build_factual_basis_section` grows a MEMORY block between SHARED
  and per-character SCOPED.
- K6.4 corpus adds memory chunks per speaker (same treatment as
  canon).
- `Composition.knowledge_chunk_ids` ordering: canon → memory →
  per-character (dedup preserved).
- Test coverage: memory chunk in SHARED-adjacent block, retrieval
  respects `witnessed_by`, memory does not enter K2 SCOPED,
  cross-Universe blocked.

**Slice 3 — Operator UI for promotion.**

- Composition detail page grows a "Promote to narrative memory" panel
  listing turns from `synthesized_brief` with per-turn kind + witness
  pickers.
- Episode detail page grows a "Memories" tab listing rows for this
  Episode.
- Universe detail page grows a "World memories" tab (index across
  Episodes in Universe).

**Slice 4 — Dogfood on the printer scenario.**

- Promote memories from `3e44b728-...`.
- Create Episode 2 "The printer is acting weird again" with cast =
  {Patch, Rivet}.
- Render. Confirm memory chunk enters `knowledge_chunk_ids` and the
  MEMORY block; confirm at least one turn references the prior
  incident naturally; confirm canon is not contradicted.
- Publish audit as SESSION XXX_NARRATIVE_MEMORY_IMPLEMENTATION.

**Slice 5 (deferred pending Slice 4 evidence) — Episode acceptance
first-class.**

- If Slice 4 reveals that operators repeatedly promote from the wrong
  Composition or want to designate "the version" independent of
  promotion, add `Episode.accepted_composition` nullable FK per §13.5
  "minimal" form.

**Slices later than 5:** Relationship, WorldEntity, per-Episode
promise ledger, cross-Episode arc grouping, distance-floor tuning
(SESSION 263 U1), configurable `shared_top_k` (U2), canon lane in
non-dialogue consumers (U3), separate `canon_chunk_ids` (U4), canon
authoring SPA (U6). All deferred until Slice 4 dogfood produces
falsifiable evidence.

---

## 16. Explicit Non-Goals

This audit does NOT propose, and future NarrativeMemory work must
NOT include, any of the following without a separate slice-scoped
audit:

- Any `state` enum on Episode.
- Any `state` enum on Composition (verification / status remain).
- Any change to `_IMMUTABLE_OBSERVABILITY_FIELDS`.
- Auto-canonization or auto-memory-promotion from synthesized output.
- Any write path from synthesis to `KnowledgeDocument`.
- Extending `retrieve_universe_canon` to also return memory.
- Extending `retrieve_for_teammate` to also return memory.
- Cross-Universe or cross-Workspace memory.
- Relationship model.
- WorldEntity model.
- `Episode.referenced_entities` M2M.
- `Episode.continues_from` self-FK.
- Global world-history feed.
- Character-owned personal memory that is not Universe-scoped.
- Ephemeral "chat memory" persistence to NarrativeMemory (that is
  what `apps.conversations` remains for — realtime avatar sessions,
  not story synthesis).
- Cleanup / migration of any legacy `KnowledgeDocument` into memory.
- Opportunistic fixes to the stale `Episode.universe` docstring
  reference to `Composition.episode = PROTECT` (§3.9). This is
  correct behavior with a stale comment; noted for a future
  hygiene commit.

---

## 17. Unresolved Questions

1. **Should the promoted memory body be operator-authored (paraphrase)
   or verbatim excerpt from `synthesized_brief`?** Verbatim is
   simpler and preserves provenance. Paraphrase is more compact and
   more retrievable. Slice 1 recommends verbatim excerpt with
   operator-editable body override; Slice 4 dogfood should surface
   which one operators prefer.
2. **Should `witnessed_by` default to the whole Episode cast or to
   empty?** Different UX implications. Suggest default = whole cast
   (matches "everyone in the room saw it"); operator narrows manually
   for offstage-events.
3. **How does memory decay?** No decay in v1. If bloat is observed,
   consider promotion-timestamp weighting in cosine ranking.
4. **How does memory interact with talking-head / realtime / ask
   consumers?** Slice 2 wires only dialogue synthesis (matches
   SESSION 263's Slice B/C.1 scope). Non-dialogue consumers are U3
   from SESSION 263 and inherit the same deferral.
5. **What is the retrieval prompt-budget in the presence of both
   canon (top_k=2) and memory (top_k=1)?** Empirically fine given
   K2 already ships 5 chunks/character; total shared+memory is 3
   entries. But test with dogfood before deciding to raise.
6. **How does the operator retract a promotion after publishing?**
   Soft-delete via `archived_at`. Retrieval already excludes archived.
   No cascade to `Composition` (Composition is unchanged; the memory
   simply stops surfacing). Verified pattern.
7. **Should NarrativeMemory participate in K6.4 verification of
   future Composition turns?** Yes for v1 (memory chunks pass into
   each speaker's factual corpus). If a future memory contradicts a
   later canon edit, the operator sees a `stale` flag rather than an
   auto-invalidation; K6.4 handles the resolution at synthesis time.
8. **Is the `weight` enum needed for v1?** Debatable. It is a hint
   for future retrieval tuning. Can be defaulted to PERIPHERAL and
   ignored by v1 retrieval; kept for forward compatibility.
9. **How does memory interact with future Relationship / WorldEntity
   substrates?** Not decided. When those land, memory rows may gain
   nullable FKs to Relationship or WorldEntity to record "this event
   involves these entities / this relationship." NarrativeMemory's
   shape does not preclude either.
10. **Does the "one accepted Composition per Episode" concept
    (§13.5) belong on Episode or on Composition?** Left open. Slice 5
    revisits after Slice 4 dogfood.

---

## 18. Proposed Dogfood Acceptance Criteria

The NarrativeMemory architecture is verified iff:

1. **Promotion works.** Operator can select turns from an accepted
   Composition and create `NarrativeMemory` rows tied to
   Episode + Composition without any change to `KnowledgeDocument`.
2. **Retrieval fires without disturbing canon.** In a new Composition,
   `retrieve_universe_canon` still returns the same static canon
   chunks it did on `3e44b728-...`. `retrieve_universe_memory`
   returns memory chunks in a separate list.
3. **The MEMORY block is present in the factual basis.** Landing
   between SHARED and per-character SCOPED, labeled with the "canon
   wins on conflict" note.
4. **`Composition.knowledge_chunk_ids` reflects the new ordering.**
   Canon → memory → per-character, no duplicates.
5. **Callback fires naturally.** In the Episode 2 "printer is acting
   weird again" render, at least one synthesized turn references the
   prior incident (a fact from a promoted memory row), and no turn
   contradicts static canon.
6. **Safety cases still pass.** In a Universe with zero promoted
   memories, retrieval + synthesis behave identically to today. In a
   Universe with memories promoted from a Composition later
   soft-deleted, memories still surface (they are decoupled) — or
   the operator can archive them independently.
7. **Multi-tenant isolation.** A separate Universe in the same
   Workspace with its own memories retrieves zero rows from the
   printer Universe. A separate Workspace retrieves zero rows across.
8. **Falsification test.** A synthesized-but-not-promoted invention
   (e.g., a turn where "Rivet made pancakes for lunch" that was
   NEVER promoted) MUST NOT appear in any future Composition's
   retrieval, prompt, or `knowledge_chunk_ids`. If it does, the
   architecture is broken.

Success = 1–8 all met. Failure = any one broken; audit revisits.

---

## Appendix A — Answers to the 20 questions in the prompt

1. **What continuity/memory/canon substrates already exist?** §2 —
   Universe, Episode, EpisodeCast, Composition observability,
   KnowledgeDocument (four canon tiers), `retrieve_universe_canon`,
   `retrieve_for_teammate`, `bootstrap_review` (approval pattern),
   `identity.services` (approval pattern), realtime `build_memory_projection`
   (ephemeral). No dedicated memory or canon-promotion substrate.
2. **What did Sessions 261–263 ratify?** §3.
3. **Authoritative representation of "an Episode happened" today?**
   §6 — nothing. Explicit gap.
4. **Rendered/verified Composition = narrative acceptance?** No. §6.
5. **Narrative memory distinct from static canon?** Yes. §4 + §8.
6. **What is safe to persist automatically?** Nothing narrative. §9.
7. **What requires operator approval?** All memory promotion, all
   canon writes. §9.
8. **Should synthesized dialogue ever directly mutate canon?** Never.
   §8 (the audit's single unequivocal rule).
9. **How should candidate historical events be represented?** As
   `NarrativeMemory` rows tied to a specific accepted Composition,
   promoted explicitly by the operator. §13.
10. **Where should compact Episode callbacks live?** In
    `apps.memory.NarrativeMemory`, keyed by Episode + Composition,
    embedded. §13.1.
11. **How should they be retrieved?** Through
    `retrieve_universe_memory`, a third retrieval lane parallel to
    canon and K2. §13.2, §10.
12. **Should narrative memory have a separate retrieval lane?** Yes.
    §10.
13. **How should character-specific awareness eventually work?** For
    v1, via `witnessed_by` M2M on each memory row (subset of cast,
    empty = whole cast). §13.1, §11.
14. **What happens when memories conflict with later canon?** Canon
    wins in the SHARED block. Memory gets a `stale` flag for operator
    review, no auto-invalidation. §9, §17 Q7.
15. **Dependencies on Relationship?** None for v1. §14, §16.
16. **Dependencies on WorldEntity?** None for v1. §14, §16.
17. **Dependencies on Episode lifecycle?** Minimal. §13.5 offers two
    forms; the "acceptance-implicit" form requires no Episode schema
    change. Slice 5 revisits.
18. **Smallest useful implementation slice?** Slice 1 in §15 —
    `NarrativeMemory` substrate only, no retrieval integration, no
    Composition change, no Episode change.
19. **What should explicitly NOT be built yet?** §16.
20. **What dogfood experiment would falsify the proposed
    architecture?** §18.6 (safety cases still pass), §18.8
    (falsification test — unpromoted invention must never surface in
    future retrieval). If either fails, the design is falsified.

---

*End of SESSION 264 audit. Nothing implemented. Awaiting review.*
