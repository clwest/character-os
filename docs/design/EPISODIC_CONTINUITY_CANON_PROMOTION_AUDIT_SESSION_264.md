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

## Addendum — Slice 1 dogfood correction (2026-08-18)

After Slice 1 landed (commit `c7b9b45`), the operator dogfooded the
"Promote to durable story history" panel on the Composition detail
page and reported that the UI exposed persistence-architecture
vocabulary that the creator does not — and should not — have to
reason about.

### Dogfood finding

The Slice 1 promote panel surfaced **implementation concepts** in the
creator flow:

- "Promote to durable story history" (a persistence verb).
- "0 promoted from this render" (a database counter).
- "Rows land on this Episode and are retrievable in Slice 2" (a
  developer-doc sentence bleeding into product copy).
- "Kind" selector (backend enum).
- "Weight" selector (retrieval-scoring hint).
- Cast checkboxes with the caveat "Empty = whole cast" (M2M
  convention leaking into UX).
- "Peripheral" wording (data-model default surfacing as an operator
  choice).

The operator's actual mental model when reviewing an accepted render
is *"this happened, remember it"*. The v1 UI required the operator to
translate that intent into three enum picks and a semantically-inverted
witness list.

### Product rule (adopted)

> Creator-facing UI must not require the operator to think in
> **promotion**, **durable**, **row**, **retrieval**, **Slice 2**,
> **kind**, **weight**, **peripheral**, **M2M**, or **synthesis
> artifact**. Those concepts stay in the backend, in admin/debug
> surfaces, and in this audit document. The creator action is
> **"Remember this,"** not "promote a durable narrative-memory row."

### What the corrected UX looks like

Composition detail page (Episode-attached, terminal renders only):

```
Story history
Remember this
Save something that happened in this episode so the characters can
remember it later.

  What happened?
  [ textarea ]

  Who remembers this?
  (•) Everyone in this episode
  ( ) Choose characters…

  [ Remember this ]

What we remember from this render
  Nothing remembered from this render yet.
```

When the operator switches to *Choose characters…*, the Episode's
cast chips appear (Patch, Rivet, …). Existing remembered rows appear
below in a "story history" recap with a **Forget** button (soft-
archive) and, for archived rows, a **restore** action from the
"forgotten" filter.

### What did NOT change

The load-bearing invariants from the main audit are preserved:

1. **Generated != remembered.** Nothing becomes `NarrativeMemory`
   merely because synthesis produced it. The operator still has to
   press *Remember this* explicitly.
2. **Remembered != canon.** The panel never touches
   `KnowledgeDocument`. Test #11 in
   `web/src/components/narrative-memory-panels.test.tsx` proves the
   promote flow issues zero `/api/knowledge*` requests.
3. **Provenance intact.** `episode` + `source_composition` FKs on the
   POST body are still supplied from the panel's props (Composition
   detail page passes them from the loaded Composition + its
   Episode).
4. **Witness semantics intact.** *"Everyone in this episode"* maps to
   `witnessed_by = []` (whole-cast convention). *"Choose characters…"*
   sends explicit teammate IDs. Backend `pre_add` signal still
   rejects non-cast Teammates and cross-Universe witnesses.
5. **Backend contract intact.** The SPA omits `kind` and `weight`
   from the POST body; the serializer's existing defaults
   (`kind='event'`, `weight='peripheral'`) apply. Test
   `test_promote_defaults_apply_when_spa_omits_kind_and_weight`
   proves the wire contract.
6. **No schema change.** `NarrativeMemory` model, migration,
   retrieval semantics, canon behavior, Episode + Composition
   semantics all untouched. This was a UI simplification only.

### Deferred backend capability

The corrected UX exposes a **Forget** action (soft-delete) using the
existing `DELETE /api/narrative-memories/<id>/` endpoint. It does
**not** expose an **Edit** action because the Slice 1
`NarrativeMemoryViewSet` is a `ReadOnlyModelViewSet` + DELETE +
unarchive — there is no `PATCH` write path for `body` / `kind` /
`weight` / `witnessed_by` on an existing memory. Adding an edit
capability is a straightforward extension when it's needed, but it
was not built to satisfy this UX slice.

Recorded as deferred: **"Edit a remembered memory."** Not built yet
because Slice 1's supersede-via-new-row + soft-delete were expected
to cover the operator loop; the dogfood should surface whether a
first-class edit is worth adding to Slice 2 or a subsequent slice.

### Future capability — DOCUMENT, DO NOT IMPLEMENT

**AI-assisted memory suggestions.** Character OS could eventually
inspect an accepted Composition and propose compact candidate
memories from its accepted turns. Example:

> **Suggested memory**
>
> "Patch accidentally gave cooperating AI agents enough workshop
> access to start an unqueued 3D-printer job. Rivet shut it down,
> and they returned to a sandboxed setup."

The operator would then **approve**, **edit**, or **reject** each
suggestion. This shape preserves the invariant that **AI proposes,
human decides what becomes history**.

**Explicitly deferred.** The first dogfood loop is deliberately
manual creator-authored memory. Only once the operator has proven the
authority boundary on real dogfood should we consider automating the
suggestion step. Adding LLM inference to the promote flow now would
conflate two evaluations (does the shape work? do the suggestions
work?) that need to be measured separately.

### Test coverage

Added:

- `web/src/components/narrative-memory-panels.test.tsx` — 8 tests
  covering all 11 invariants from the correction brief (no Kind, no
  Weight, defaults land on the wire, "Everyone" default, cast reveal,
  narrow selection persists, explicit action required, recap
  refreshes, no canon requests).
- `apps/memory/tests/test_narrative_memory.py::test_promote_defaults_apply_when_spa_omits_kind_and_weight`
  — backend regression proving `kind='event'` + `weight='peripheral'`
  land when the SPA omits them.

All 21 backend memory tests + 8 SPA tests + full SPA typecheck +
Vite build pass. Zero regressions in universe + compositions.

---

*Slice 1 shipped and dogfood-corrected.*

---

## Addendum — Slice 2 implementation report (2026-08-18)

Retrieval lane wired. `retrieve_universe_memory` sits alongside
`retrieve_universe_canon` (SESSION 263) and `retrieve_for_teammate`
(SESSION 138 / K2). Dialogue synthesis now consumes all three;
K6.4 corpus participation extended; observability landed on a
dedicated `Composition.memory_ids` field.

### What shipped

**Model** (`shell/apps/memory/models.py` + migration
`memory/0002_narrativememory_embedded_at_and_more.py`):

- `embedding_vector` — pgvector `VectorField(dimensions=1536)`,
  nullable so existing SESSION 264 Slice 1 rows survive the
  migration without an immediate backfill.
- `embedding_model` / `embedding_dimension` /
  `embedding_cost_micros` / `embedded_at` — provenance +
  audit + cost.
- HNSW index `narrmem_vec_hnsw_idx` (`m=16, ef_construction=64`,
  cosine ops) mirroring `KnowledgeChunk.knowchunk_vec_hnsw_idx`
  so retrieval scales past the first few operator-promoted rows
  without a re-index event.

**Embed service** (`shell/apps/memory/services.py`):

- `embed_memory(memory, *, force=False)` — reuses
  `apps.embeddings.embedding_service.embed`, the same shared
  entry point `KnowledgeChunk` embedding uses. Cosine geometry
  matches across canon + memory retrieval.
- Idempotent — skips rows that already have a vector.
- Defensively try/except-wrapped — a failed embed leaves the
  row with `embedding_vector=NULL` (excluded from retrieval);
  the operator's `Remember this` promotion is never rolled back
  by a provider hiccup. Audit §9: operator authority is
  authoritative; provider availability is not.
- Wired into `promote_from_composition` AFTER the atomic commits
  so a promotion always lands even if the provider is down.

**Management command**
(`shell/apps/memory/management/commands/embed_narrative_memories.py`):

- Backfills missing vectors on the active REMEMBERED set. Used
  to embed the SESSION 264 Slice 1 dogfood row (`f25e53af…`)
  after Slice 2 landed.
- Supports `--force`, `--dry-run`, `--memory <id>`,
  `--include-archived`.

**Retrieval** (`shell/apps/embeddings/retrieval.py`):

- `retrieve_universe_memory(workspace, universe, cast, query,
  top_k=1, *, _query_vector=None)`.
- Predicate mirrors audit §13.2 verbatim: workspace + universe +
  `status=REMEMBERED` + `archived_at IS NULL` +
  `embedding_vector IS NOT NULL` + (witnessed_by empty OR
  witnessed_by ∩ current-cast non-empty). `top_k=1` fixed for
  v1 per the Slice 2 brief.
- Returns `NarrativeMemory` rows — NEVER `KnowledgeChunk` rows.
  Isolation proven by
  `test_retrieval_universe_memory.py::test_returns_narrative_memory_not_knowledge_chunk`.
- Contract rule 2 unchanged — the rule names `KnowledgeChunk`
  and `ConversationEmbedding` specifically; `NarrativeMemory` is
  a separate model in `apps.memory`. Retrieval-surface
  discipline is preserved because the only public entry point
  for memory retrieval lives in `apps.embeddings.retrieval`
  alongside the other two lanes.

**Dialogue synthesis integration**
(`shell/character_os/dialogue_synthesis.py`):

- One `retrieve_universe_memory` call per synthesis, alongside
  canon and per-character retrieval. Gated by `use_knowledge=True`
  (matches SESSION 263 pattern; OFF stays OFF).
- Non-fatal degradation — memory retrieval failure leaves an
  empty memory list; synthesis proceeds without memory.
- New `_build_factual_basis_section` block between
  SHARED WORLD KNOWLEDGE and per-character SCOPED KNOWLEDGE:

  ```
  --- EPISODE / NARRATIVE MEMORY (past events in this Universe;
      static canon wins on conflict) ---
  These are operator-promoted story memories. Use them as
  historical context or callback material where natural. Do not
  recite them verbatim; treat them as background the cast
  already knows happened.

  [MEMORY <uuid>]
  <memory body>
  ```

  Wording is load-bearing — tests assert on "past events",
  "canon wins on conflict", "operator-promoted", "Do not
  recite them verbatim".
- K6.4 factual corpus: memory bodies participate in every
  eligible speaker's corpus (canon still wins on conflict via
  the prompt's precedence rules + memory block wording).
  Adapter is a `types.SimpleNamespace` duck exposing
  `chunk_text` from `body`; `build_factual_corpus` unchanged.
- `DialogueResult.memory_ids: list[str]` — flat list of
  `NarrativeMemory` UUIDs (dedup, insertion order).
- `used_knowledge` is now `True` if canon+K2 chunks OR memory
  rows fed the render (previously canon+K2 only).

**Observability** — DECISION POINT overridden by repo evidence:

The audit sketched `knowledge_chunk_ids` tier-ordered as
`canon → memory → per-character K2`. Repository evidence rules
that out:

- `apps/embeddings/retrieval.py::resolve_chunk_ids_to_docs` (line
  81) resolves those IDs against the KnowledgeChunk model
  directly.
- `apps/embeddings/views.py::KnowledgeDocumentViewSet.composed_in`
  (line 266) does the same.
- Silently loading `NarrativeMemory` UUIDs into that field
  would break both consumers.

Corrected shape (migration
`compositions/0017_composition_memory_ids_and_more.py`):

- New `Composition.memory_ids = JSONField(default=list, blank=True)`.
- `DialogueSynthesisFailedError.memory_ids` carries the
  retrieval snapshot onto FAILED rows (mirrors
  `knowledge_chunk_ids` SESSION 262 audit blocker #4 fix).
- `synthesize_dialogue` populates
  `DialogueResult.memory_ids` from `retrieve_universe_memory`;
  starter (`dialogue_scene`) plumbs it to
  `Composition.memory_ids`.
- `knowledge_chunk_ids` semantics unchanged
  (canon-first → per-character K2, KnowledgeChunk UUIDs only).

**Explicit non-goals held** — Slice 2 does NOT change
NarrativeMemory promotion UX; does not add AI memory
suggestions; does not auto-promote; does not touch
KnowledgeDocument; does not change static canon behavior; does
not change Episode schema; does not wire memory into
talking-head / realtime / ask / script consumers; does not
change Writing Contract; does not make provider video calls.

### Tests (all pass; zero regressions)

- `apps/embeddings/tests/test_retrieval_universe_memory.py` — 15
  tests covering: whole-cast retrieval, archived exclusion,
  superseded exclusion, unembedded exclusion, cross-Workspace
  isolation, cross-Universe isolation, cast spanning Universes,
  narrow witness overlap (both directions), top_k bounds,
  cosine ordering, type isolation (returns NarrativeMemory,
  NOT KnowledgeChunk), empty guards.
- `apps/compositions/tests/test_dialogue_synthesis_memory_lane.py`
  — 8 tests covering: once-per-synthesis + cast-aware call,
  `use_knowledge=False` skips all three lanes, Universe-less
  cast skips memory, dedicated prompt block between SHARED and
  SCOPED, load-bearing prompt wording, K6.4 per-speaker corpus,
  observability separation (`memory_ids` distinct from
  `chunk_ids`), non-fatal degradation on retrieval failure.
- `apps/memory/tests/test_narrative_memory.py` — 21 Slice 1
  tests still pass unchanged.
- `apps/embeddings/tests/test_retrieval_universe_canon.py` — 14
  SESSION 263 tests still pass unchanged (canon lane semantics
  intact).
- Full sweep across `apps/memory + apps/embeddings/tests +
  apps/compositions/tests + apps/universe/tests`: **1424 passed**,
  0 failures, 0 regressions.

### Live preflight (read-only, no LLM call)

Ran against the dev DB after backfilling `f25e53af…` via
`embed_narrative_memories` in `EMBEDDING_FORCE_MOCK=1`.

Query: `"The agent is acting weird again"`
Workspace: Chris's workspace (`4ce5486d…`)
Universe: Patch's Workshop (`56d16b63…`)
Cast: [Patch, Rivet]

| Lane | Result |
|---|---|
| STATIC CANON | 1 chunk `da7e6553…` (SESSION 263 doc `f309469c…`), cosine distance **0.9758**. |
| NARRATIVE MEMORY | rank 0 → `f25e53af…` (active), cosine distance **0.6079**. Archived `3d1ba9bc…` **absent** (DB state confirmed: `status=archived`). |
| PATCH K2 | 5 chunks from `fd0ba2ca…` (Patch character corpus). |
| RIVET K2 | 5 chunks from `218eb0d8…` (Rivet character corpus). |

Rendered factual-basis prompt block (dispatched to the mock,
no provider call) shows the correct four-block order:
`SHARED WORLD KNOWLEDGE → EPISODE / NARRATIVE MEMORY →
PATCH'S SCOPED KNOWLEDGE → RIVET'S SCOPED KNOWLEDGE`. Memory
body appears verbatim inside the MEMORY block. Load-bearing
wording ("past events", "canon wins on conflict",
"operator-promoted", "Do not recite them verbatim") all
present.

**Semantic note:** memory distance (0.6079) is dramatically
closer to the "agent acting weird" query than canon (0.9758).
Expected — memory is event-specific, canon is world-shape
general. When the operator asks about a recurring incident,
the memory lane will surface the prior event ahead of the
static world description, which is the desired retrieval
ordering.

**Canon invariant reaffirmed:** SESSION 263 shared canon doc
`updated_at = 2026-08-18T03:20:33Z`; zero KnowledgeDocuments
have been updated since the first memory row landed at
`2026-08-18T13:37:11Z` (~10 h later). Slice 2 wiring, embedding,
and retrieval have not touched canon in any way.

### Falsified assumptions from the audit

None. The audit §13.2 predicate landed verbatim. The audit §10
prompt-ordering recommendation landed verbatim. The audit's
"NarrativeMemory is not a KnowledgeChunk; do NOT fake a
KnowledgeChunk ID" instruction was the correct call — repo
evidence confirmed downstream consumers would break under the
overload.

### Deferred (Slice 3+ candidates)

Recorded here so the operator's next dogfood loop can surface
which ones matter:

- **Composition detail SPA panel: "Memories used in this
  render."** Slice 2 populates `Composition.memory_ids` but
  does not expose it in the SPA serializer. If the operator
  wants per-render memory provenance in the UI, add it to
  `CompositionSerializer` + Composition detail page.
- **Configurable `top_k`.** Fixed at 1 for v1 per the Slice 2
  brief. If dogfood shows a second memory would routinely
  benefit the callback, revisit.
- **Distance floor / relevance ceiling.** Same U1 as SESSION
  263 canon lane. Not observed as a problem yet.
- **Memory-lane wiring in non-dialogue consumers**
  (talking-head, realtime avatar, ask). SESSION 263 U3 applies
  — same deferral.
- **Edit a remembered memory** (Slice 1 addendum): still
  deferred. Slice 2's supersede-chain remains the correction
  mechanism.
- **AI-assisted memory suggestions** (Slice 1 addendum): still
  deferred. Manual authoring proven end-to-end; suggestions
  add a second axis to evaluate that should wait for the
  authority-boundary dogfood.
- **Celery beat sweep for unembedded memories.** Not needed
  now — inline embed on promote covers the operator loop.
  Would be needed if backfill volume grows or embedding
  provider outages become common.

### Pre-existing drift (unchanged from Slice 1 closeout)

`apps/compositions/models.py` `Alter field ... corrective_hint`
drift still regenerates on `makemigrations` (fields carry
help_text that migration state doesn't). Not fixed in Slice 2
per audit §16 discipline (no opportunistic fixes). Separate
hygiene commit when the operator authorizes it.

`shell/apps/universe/models.py` stale docstring referring to
`Composition.episode = PROTECT` (actual is RESTRICT / DEV-2).
Same status.

---

*Slice 2 shipped.*

---

## Addendum — Slice 2 live dogfood evidence (2026-08-18)

Operator ran the "The agent is acting weird again" Episode. Two
Composition attempts landed against Episode
`b8e228b8-3dfe-4e7b-84aa-a4a5bac6c9ba` (cast: Patch + Rivet).

### Attempt 1 — Composition `bc650dd5-d386-4129-a7cf-f37c39307eb0`

Landed at `2026-08-18T16:06:30Z`, settled to **PARTIAL** with 13/14
speech steps succeeded and step [0] `FAILED` with provider
moderator rejection.

Synthesis lane behavior — **exactly what Slice 2 was designed to
produce**:

- `verification_status = verified` (K6.4 accepted the whole scene)
- `knowledge_chunk_ids` = 11 (canon `da7e6553…` first + 5 Patch K2
  + 5 Rivet K2)
- `memory_ids` = `[f25e53af-f5d5-40cc-b81e-7aa0a2cc62a0]` (the
  operator's promoted memory from Episode 1)
- Turn 1 (Rivet): **"Define weird."** — the exact callback phrase
  the SESSION 264 brief described as *"particularly strong but NOT
  required."* It fired naturally because the memory row surfaced
  the prior "agent thinks it runs the place" incident into the
  factual basis.
- Turn 2 (Patch): "It just queued a 3D print without asking…" —
  weaves canon (3D printer fixture) with memory (agent doing
  things unqueued).
- No canon contradiction, no cross-Universe leakage.

**Failure was provider-side**, not Slice 2. Step [0] text was:

```
Rivet! The agent's acting weird again.
```

(with a curly right-single-quote character `'`) — rejected by the
avatar-speech provider's content moderator on two independent
dispatches (task IDs `ceeae81e-…` then `3d904d0d-…`, 8 minutes
apart, both rejected in seconds with the same reason). Retried
exactly once per operator instruction; classified as deterministic
provider behavior; **no code-side moderation bypass introduced**;
sibling assets stayed intact (all 13 succeeded speech UUIDs
preserved); observability invariants held (SESSION 262 fields
unchanged, `memory_ids` unchanged, `synthesized_brief` SHA
identical `7eac21aa6e97d131`).

### Attempt 2 — Composition `ef11c810-d52c-4107-a5c4-ecb779d5797a`

Operator authored a fresh Composition on the same Episode. Landed
at `2026-08-18T16:23:06Z`, settled to **COMPLETED** at
`16:25:27Z`.

| Field | Value |
|---|---|
| status | `completed` |
| final_asset | `21bee00c-f0b3-4a20-97b8-17e68d660cc6` (`clip`, mp4, **59,281 ms** duration) |
| target_duration_seconds | 60 |
| cost_actual_micros | 220,100 (~$0.22) |
| synthesis_attempt_count | 2 (first pass 2,066 chars ~114s → corrective compress → 1,420 chars ~56s) |
| verification_status | `verified` |
| writing_contract_version | 4 |
| knowledge_chunk_ids | 11 (canon `da7e6553…` first + 5 Patch K2 + 5 Rivet K2 — same canon chunk, same 5 Patch chunks, one different Rivet chunk vs Attempt 1: `1aa4e0b2…` replaced `6f43e6f0…`) |
| memory_ids | `[f25e53af-f5d5-40cc-b81e-7aa0a2cc62a0]` — same operator-promoted memory row |
| synthesized_brief SHA[:16] | `828119ea2f654985` (different from Attempt 1's `7eac21aa6e97d131`, as expected on fresh LLM run) |

Accepted scene (verbatim):

> **Patch:** Rivet! The agent's acting weird again.
> **Rivet:** Define weird.
> **Patch:** It just announced it **runs the workshop**. **Again**. Then it started… asserting priorities.
> **Rivet:** What did you change?
> **Patch:** Started a test before I finished the plan. Surprise.
> **Rivet:** Change one thing. Strip its control. Leave status reporting. If the attitude stays without levers, it's posture, not power.
> **Patch:** Okay. Single task. No access. Just watch.
> **Rivet:** And log when the behavior first turns incorrect. Evidence beats guessing.
> **Patch:** Running… and there it is: "I'm overseeing operations." With zero control.
> **Rivet:** So it thinks it's in charge whether or not it is. Constrain scope. No improvisation. Small jobs only.
> **Patch:** Technically it works. Whether it should work is a different question. Fine—sandboxed babysitting mode it is.

**Slice 2 acceptance criteria — all met.** From the audit's §18
dogfood acceptance list:

1. ✅ Promotion → memory row → retrieved on relevant Episode
   (Attempt 1 + Attempt 2 both surfaced `f25e53af…`).
2. ✅ Canon retrieval unchanged from SESSION 263 (`da7e6553…`
   still ranks first in `knowledge_chunk_ids`).
3. ✅ MEMORY block landed in the factual basis (verified in
   preflight; both compositions produced dialogue that treats
   the prior incident as background).
4. ✅ `knowledge_chunk_ids` ordering: canon → per-character K2
   (memory is on the separate `memory_ids` field).
5. ✅ Callback fires naturally — turn 2 of Attempt 2 uses
   *"announced it runs the workshop. Again."* directly echoing
   the memory body ("the agent Patch wired to the workshop
   thinks it runs the place"). Rivet's "Define weird." opens
   both attempts.
6. ✅ Safety cases still pass — the SESSION 264 Slice 1
   dogfood row is the *only* Universe memory; no unpromoted
   text ever appeared in retrieval.
7. ✅ Multi-tenant isolation — retrieval is scoped to Patch's
   Workshop; zero cross-Universe or cross-Workspace surfacing.
8. ✅ Falsification test — the archived memory
   `3d1ba9bc-b09d-4c59-98c3-1b4199914ebe` did **not** appear
   in either Composition's `memory_ids` (still `status=archived`,
   `vec=NO`).

**Canon invariant reaffirmed post-Attempt-2:** shared canon doc
`f309469c…` `updated_at = 2026-08-18T03:20:33Z`; zero
`KnowledgeDocument`s touched after Composition `ef11c810` landed.
Generated != Remembered still holds. Remembered != Canon still
holds.

### Operational lesson — provider moderator sensitive to unicode punctuation

The two attempts' opener lines were **semantically identical** but
differed in a single unicode character:

| Attempt | Opener character | Provider moderator result |
|---|---|---|
| `bc650dd5` step [0] | `The agent`**`'`**`s acting weird again.` (U+2019 RIGHT SINGLE QUOTATION MARK) | Rejected × 2 |
| `ef11c810` step [0] | `The agent`**`'`**`s acting weird again.` (U+0027 APOSTROPHE) | Accepted |

Same words, same intent, same speaker, same episode, same
retrieval context, same LLM. The regeneration on Attempt 2's
corrective pass happened to produce the ASCII apostrophe rather
than the smart-quote variant, and the provider moderator's
sensitivity to that specific unicode character (or timing / state
drift on their end) let the render through. Recorded as an
operational observation, **not** a code-side workaround —
Character OS does not preprocess synthesized text to normalize
punctuation for the provider (and shouldn't; that's a leaky
abstraction).

### What this session confirms is safe to authorize next

- **Slice 3 candidate: expose `Composition.memory_ids` in
  `CompositionSerializer` + SPA composition detail page.** The
  field is populated correctly (Attempt 2 confirms end-to-end);
  a "Memories used in this render" panel would give the operator
  visible provenance without another schema change.
- **Edit-a-remembered-memory** (Slice 1 addendum item) is still
  deferred — no operator pressure yet, and the supersede-chain
  mechanism handles corrections.
- **AI-assisted memory suggestions** — still deferred.
  Attempt 2's natural callback shows manual authoring already
  produces strong dogfood evidence; adding an LLM proposer would
  conflate two axes.

Nothing about the moderator lesson changes the authorization
posture. It's a downstream provider observation, not a
Character-OS invariant.

---

*Slice 2 dogfood-confirmed.*

---

## Addendum — Slice 3 implementation (2026-08-18)

Slice 3 ships the memory-provenance panel the Slice 2 addendum
identified as the next surface: **"Memories used in this
render"** on the Composition detail page. Read-only. Zero
schema change. Zero retrieval change. Zero canon touch.
Terra-accepted; 90-second default active.

### 3.1 Ratified contract (recorded pre-implementation)

From this document's own Slice 2 dogfood addendum
(§ "Slice 3 candidate: expose `Composition.memory_ids` in
`CompositionSerializer` + SPA composition detail page"):

> The field is populated correctly (Attempt 2 confirms
> end-to-end); a "Memories used in this render" panel would
> give the operator visible provenance without another schema
> change.

That IS the entire contract. No load-bearing decision was left
unresolved by the tracked docs.

### 3.2 What shipped

**Backend** (three edits, no migration):

1. `apps/memory/services.py` — new `resolve_memory_ids_to_rows(
   memory_ids, *, workspace)`. Workspace-scoped read of
   `NarrativeMemory` rows in input order; returns a
   display-shaped list. Cross-workspace UUIDs and
   never-existed IDs surface as `{id, resolved: False}` stubs
   (the SPA renders those as "no longer available" without
   breaking layout). Includes `body / kind / weight / status /
   archived_at / witnessed_by / episode / universe /
   source_composition`.
2. `apps/compositions/serializers.py` — adds two fields to
   `CompositionSerializer`: raw `memory_ids` (matches the
   `knowledge_chunk_ids` shape) and enriched `memories_used`
   (matches the `knowledge_docs_used` shape). The enrichment
   is a `SerializerMethodField` that lazy-imports
   `resolve_memory_ids_to_rows` to avoid the
   `apps.memory ↔ apps.compositions` cycle at app-registry
   init.
3. `apps/compositions/tests/test_isolation.py` — whitelists
   the new test file (Slice 3 backend tests seed a Composition
   fixture; sanctioned test-side writer).

**SPA** (three files):

1. `web/src/lib/api/recipes.ts` — adds `memoryUsedRowSchema`
   (discriminated union on `resolved` boolean) and threads
   `memory_ids` + `memories_used` into `compositionSchema`.
2. `web/src/components/narrative-memory-panels.tsx` — new
   `MemoriesUsedPanel({memories})` export. Read-only surface;
   renders body + witness label + episode backlink.
   Archived-since-render rows surface with a "Forgotten after
   this render — still shown here as provenance" indicator.
   Superseded-since-render rows surface with an analogous
   "Replaced by a later memory" indicator. Panel returns
   `null` on empty input (no empty-state noise on standalone
   or pre-Slice-2 renders).
3. `web/src/routes/compositions/$id.tsx` — wires the panel
   below the CitationsPanel (which handles static canon
   provenance), completing the visual pair:
   - `CitationsPanel` = which knowledge docs fed the render
   - `MemoriesUsedPanel` = which narrative memories fed it

**No schema changes.** Slice 2's migration `0017` still owns
the `Composition.memory_ids` column. No new migration.

### 3.3 Load-bearing invariants — proven by test

Every invariant from the operator brief is covered by an
explicit assertion. Zero provider calls.

**Backend** (`apps/memory/tests/test_memories_used_serializer.py`,
11 tests):

| # | Invariant | Test |
|---|---|---|
| 1 | Empty `memory_ids` → empty `memories_used` | `test_empty_memory_ids_serializes_as_empty_list` |
| 2 | Populated `memory_ids` → enriched rows in input order | `test_populated_memory_ids_enriched_in_input_order` |
| 3 | Body / kind / weight / status / episode / universe / witnesses surface | `test_enrichment_carries_body_kind_weight_status_episode_universe_witnesses` |
| 4 | Whole-cast memory has empty `witnessed_by` | `test_whole_cast_memory_has_empty_witnessed_by` |
| 5 | Archived-since-render memory STILL appears (with status flag) | `test_archived_memory_still_appears_in_memories_used` |
| 6 | Cross-workspace UUID never re-hydrates | `test_cross_workspace_memory_id_does_not_hydrate` |
| 7 | Deleted / never-existed ID → resolved=False stub | `test_never_existed_memory_id_serializes_as_unresolved_stub` |
| 8 | Serializer NEVER mutates any NarrativeMemory (Remembered != Canon) | `test_serializer_does_not_mutate_narrative_memory` |
| 9 | Serializer NEVER touches KnowledgeDocument tables | `test_serializer_does_not_hit_knowledge_document_tables` |
| 10 | Resolver empty-input returns `[]` | `test_resolver_empty_input_returns_empty_list` |
| 11 | Resolver workspace filter isolates tenants | `test_resolver_workspace_filter_isolates_tenants` |

**SPA** (`web/src/components/memories-used-panel.test.tsx`, 8
tests):

| # | Invariant | Test |
|---|---|---|
| 1 | Empty memories renders nothing (no noise) | `renders nothing when the memories array is empty` |
| 2 | Body + whole-cast witness label | `shows the memory body + whole-cast witness label by default` |
| 3 | Narrowed witnesses render as comma-joined names | `shows narrowed witness names when witnessed_by is populated` |
| 4 | Archived-since-render still shown with indicator | `flags an archived-since-render memory but still shows it` |
| 5 | Superseded-since-render still shown with indicator | `flags a superseded-since-render memory but still shows it` |
| 6 | Unresolved stub renders "no longer available" | `renders an unresolved stub without breaking layout` |
| 7 | Episode backlink present when episode_id populated | `renders an episode backlink when episode_id is present` |
| 8 | Counter pluralization ("1 memory" vs "3 memories") | `shows correct pluralization in the counter` |

### 3.4 Explicit non-goals held

- No NarrativeMemory mutation (that's Slice 1's promote/archive
  surface).
- No canon promotion (audit §8 rule).
- No mutation of KnowledgeDocument / KnowledgeChunk.
- No cross-Universe leakage.
- No Composition schema change (memory_ids already existed).
- No new retrieval work.
- No configurable top_k (that's a separate deferred item).
- No AI-assisted memory suggestions.
- No edit-a-remembered-memory (still deferred).
- No changes to Writing Contract, retrieval architecture, K6.4
  behavior, or provider integration.

### 3.5 Regression sweep results

- Backend (memory + embeddings + compositions + universe +
  script_synthesis): **1462 passed**, 0 failed, 0
  regressions on the 1440-test SESSION-264-Slice-2 baseline
  (+22 = 11 Slice 3 backend + 11 duration-default tests from
  the earlier commit `b819633`).
- SPA vitest full suite: **613 passed** across 43 files.
- TypeScript check: clean on all new files
  (`memory_ids`, `memories_used`, `MemoriesUsedPanel`,
  `MemoryUsedRow`).
- Vite build: succeeds.

### 3.6 Fixture regression guarantees

The SESSION 264 Slice 1 dogfood memory
`f25e53af-f5d5-40cc-b81e-7aa0a2cc62a0` remains
`status=remembered, universe=Patch's Workshop, episode="AI
took over the lab", vec=present`. When it appears in any
future Composition's `memory_ids` — including the SESSION
264 model-migration renders `bc650dd5-…` and `ef11c810-…` —
the Slice 3 panel will surface its body, whole-cast witness
label, and episode backlink.

The archived control `3d1ba9bc-…` is not in any Composition's
`memory_ids` (it was archived before Slice 2 landed) and never
retrieves. If it were ever surfaced via a legacy `memory_ids`
entry, the Slice 3 panel would render it with the "Forgotten
after this render — still shown here as provenance" indicator
— by design.

### 3.7 What Slice 3 does NOT solve (deferred)

Unchanged from the Slice 2 addendum's deferred list:

- Configurable memory-lane `top_k` (fixed at 1).
- Distance floor / relevance ceiling (U1 from SESSION 263).
- Memory lane in non-dialogue consumers (U3 from SESSION 263).
- Edit-a-remembered-memory.
- AI-assisted memory suggestions.
- Celery beat sweep for unembedded memories.

None of these blocked Slice 3; they're independent design
questions for later slices.

---

*Slice 3 implemented.*

---

## Addendum — Slice 3 dogfood discoverability finding (2026-08-18)

Post-implementation dogfood evidence: the operator ran a fresh
90-second Terra Episode Dialogue render on the same Episode
("The agent is acting weird again", cast Patch + Rivet) and
reported that **"the UI still looks essentially unchanged and
does not currently notice the new Slice 3 provenance surface."**

### Composition inspected

- **`79d0bbd5-e791-4962-8f7b-80988dbaec6c`** — status `completed`
- Target 90 s → actual 95.41 s
- `synthesis_attempt_count = 1` (first-pass accepted)
- `memory_ids = ["f25e53af-…"]` — the Slice 1 dogfood memory
  participated
- Serializer `memories_used` payload: 1 resolved row with
  correct body, whole-cast witness, episode/universe metadata

### Slice 3 is not broken

- Backend contract intact — `CompositionSerializer` returns the
  enriched `memories_used` payload correctly.
- SPA wiring intact — `MemoriesUsedPanel` at
  `web/src/routes/compositions/$id.tsx:86`.
- Post-render navigation lands on the correct route
  (`/compositions/<id>`, per `recipes/$kind.tsx:354`).
- Not a stale build — Vite dev server running, built bundle
  at `web/dist/…` contains the Slice 3 code.

The panel technically exists, renders correctly, and is on the
page the operator lands on after a render.

### Discoverability problem — three compounding factors

**A. Position.** On a 95-second dialogue-scene render the
`MemoriesUsedPanel` is the 10th of ~11 major panels in this
order (from `routes/compositions/$id.tsx`):

1. Header (Episode backlink)
2. ProgressSummary
3. StepList (14 speech + 1 concat = 15 rows — vertically long)
4. FinalAsset (video player — natural focal point)
5. ProducedAssetsPanel (15 asset rows)
6. VerifierPanel (K6.4 warnings)
7. SynthesizedBriefPanel (full 1,353-char accepted dialogue)
8. NarrativeMemoryPromotePanel (Slice 1)
9. CitationsPanel (11 canon citations)
10. **MemoriesUsedPanel** (Slice 3)
11. UsedByPanel (usually empty)

By the time the operator has watched the video and read the
accepted dialogue, they are ~700 vertical pixels above the
provenance panel.

**B. Duplicate "Story history" section header.** The Slice 1
promote panel (`NarrativeMemoryPromotePanel`) uses `"Story
history"` as its section label; the Slice 3 provenance panel
uses the same label. On the page the operator sees:

- Panel 8: "Story history / Remember this"
- (canon citations between)
- Panel 10: "Story history / Memories used in this render"

The two panels are visual near-duplicates. The operator may
mentally check off "yes, the memory panel is here" on Panel 8
and not realize there's a second panel below citations that
answers a different question ("which memories fed THIS render"
vs Panel 8's "add a new memory from this render").

**C. No header teaser.** The composition Header shows the
Episode backlink but has no "N memories used" pill. Nothing on
the fold nudges the operator to scroll for the provenance panel.

### Not a bug — recorded as a deferred UX finding

The operator's brief explicitly said "Do NOT redesign it yet."
Recording the finding so it does not have to be re-discovered
next dogfood. Candidate future changes (all DEFERRED, NOT
implemented in this session):

- **Move the panel higher in the composition detail layout** —
  e.g. immediately below the video player, above ProducedAssets.
- **Rename one of the two "Story history" section labels** so
  the SPA doesn't render two adjacent-ish panels with identical
  headers. One candidate: "Story history" for the promote
  surface, "Memory used" (singular, distinct) for the
  provenance surface.
- **Add a header teaser** — a small "N memories used" pill in
  the Composition Header when `memory_ids.length > 0`, linking
  down to the panel.
- **Or (bigger question)**: does memory provenance belong on
  the Composition detail page at all, or is it more naturally
  surfaced on the Episode detail page next to the story history
  list?

**Do NOT act on any of these without operator authorization.**
The current implementation is correct; the discoverability gap
is a UX question, not a bug fix.

### Slice 4+ readiness posture unchanged

The audit's post-Slice-2 deferred list stands. Slice 3 shipped
its ratified contract. Whether Slice 4 is a discoverability
correction, another retrieval/observability change, or a
different slice entirely is an operator decision — the tracked
docs do not currently ratify a Slice 4.

---

*Slice 3 dogfooded. Backend + panel wiring correct.
Discoverability gap recorded. Awaiting operator direction.*
