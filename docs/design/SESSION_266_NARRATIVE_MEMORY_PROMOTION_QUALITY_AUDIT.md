# SESSION 266 — Narrative Memory Promotion Quality Audit

Status: **Read-only audit — no implementation**.
Next operator action: review this document (upload to ChatGPT for a
second opinion) and decide whether/what to build.

Scope-locks preserved: no `top_k` change, no auto-promotion, no AI
candidate generation, no prompt/retrieval/synthesis edits, no
Universe canon mutation, no Relationship / WorldEntity, no duration
retune, no GPT-5.6 Terra retune.

Anchored in the SESSION 265 arc-summary hypothesis
(`SESSION_265_MULTI_MEMORY_STORY_PROGRESSION_DOGFOOD.md` §20.6, §21.2):

> Cumulative story continuity can survive `top_k=1` retrieval when
> the promoted memory acts as a compact arc-summary rather than
> merely an atomic event.

Investigation question:

> How should Character OS help a creator decide what an Episode
> should remember, while preserving explicit operator control and
> the hard boundary between NarrativeMemory and Universe canon?

---

## 1. Repository findings — the current "Remember this" pipeline

Traced end-to-end from the SPA click to the persisted row and the
downstream retrieval lane.

### 1.1 UI entry point — `NarrativeMemoryPromotePanel`

`web/src/components/narrative-memory-panels.tsx:92-305`

Rendered on the Composition detail page
(`web/src/routes/compositions/$id.tsx:79-84`) — **only when the
Composition is Episode-attached AND terminal**. Standalone renders
show no promote panel at all (memory belongs to a story).

What the creator sees at the moment of promotion:

- The full Composition status header (title, template kind, mock/
  real, verification badge, Episode backlink).
- Progress summary + step list (13-step turn breakdown).
- `MemoriesUsedSummary` — one-quote "Continuity" chip if any
  memories fed this render (below the video player). See §1.6.
- The video player itself (with Download button).
- `SynthesizedBriefPanel` — the exact accepted dialogue text.
- `VerifierPanel` if warnings/rejects fired.
- **`NarrativeMemoryPromotePanel`** — the "Remember this" form.
- `CitationsPanel` — retrieved knowledge docs.
- `MemoriesUsedPanel` — full read-only provenance list of memories
  that fed the render.

Form fields (`narrative-memory-panels.tsx:172-278`):

| Element | Type | Default | Constraint |
|---|---|---|---|
| `What happened?` textarea | free text | empty | non-blank (client + server); trimmed |
| `Who remembers this?` radio | "Everyone in this episode" / "Choose characters…" | Everyone | if `some`, at least one witness must be picked (client) |
| Cast toggle chips | multi-select, only visible under `some` | none selected | server validates each teammate is in the Episode cast |
| `Remember this` button | submit | disabled until body non-blank | fires `POST /api/compositions/<id>/promote-narrative-memory/` |

Recap sub-section below the form:

- "What we remember from this render" list — memories previously
  promoted from *this* Composition, with witness label + Forget
  (trash) icon and Restore (unarchive) icon inline
  (`narrative-memory-panels.tsx:280-302, 409-539`).

Below the promote panel on the same page: the read-only
`MemoriesUsedPanel` for anything the retrieval lane surfaced into
this render (§1.6).

Helper copy in the form (`narrative-memory-panels.tsx:167-170,
185-187`):

- Header sub-line: "Save something that happened in this episode
  so the characters can remember it later."
- Textarea placeholder: "e.g. Patch connected an AI agent to the
  workshop tools and the printer started a job he did not queue."

That placeholder is the only pedagogical signal the operator gets
about what a *good* memory looks like. It teaches a single shape
(actor + concrete action + observable consequence) implicitly by
example; no explicit guidance on arc-summary framing.

### 1.2 What the operator has to decide manually

At the moment of clicking "Remember this" the operator is holding
in their head, unassisted:

1. Whether this render deserves a memory at all.
2. Which of the render's events/inventions constitutes the
   promotion-worthy fact.
3. How to compress that fact into a compact durable sentence.
4. Whether "Everyone" or "some" witnesses.
5. Whether it duplicates canon or an existing memory.
6. Whether it belongs on the future story rail or the world-truth
   rail (the promote panel does not surface canon at all — the
   operator has to know that mentally).

No draft is pre-filled. No memory suggestions appear. No
"strength" hints. No canon or existing-memory diff view. Kind
(`event / action / promise / dialogue_callback / world_detail`)
and weight (`central / peripheral`) exist in the backend but the
promote-form UI intentionally omits them — the SESSION 264 dogfood
correction (`narrative-memory-panels.tsx:54-62`) stripped these
"internal-only" concepts out. Backend defaults to
`kind=event`, `weight=peripheral`, `witnessed_by=[]` (whole cast).

### 1.3 API / service / model path

Wire path from click to persisted row:

1. **SPA** — `usePromoteMemories` mutation
   (`web/src/lib/api/narrative-memories.ts:223-245`) sends
   `POST /api/compositions/<id>/promote-narrative-memory/`
   body `{episode, memories:[{body, witnessed_by}]}`.
2. **DRF action** — `CompositionViewSet.promote_narrative_memory`
   (`shell/apps/compositions/views.py:393-477`) validates request,
   resolves Episode (workspace-scoped), delegates to
   `promote_from_composition`.
3. **Service** — `apps.memory.views.promote_from_composition`
   (`shell/apps/memory/views.py:171-287`). In a single
   `transaction.atomic()`:
   - Fast-fails any witness not in the Episode's cast.
   - Constructs `NarrativeMemory` with denormalized workspace +
     universe from Episode.
   - `full_clean()` — enforces `episode.universe ==
     source_composition.workspace`, workspace/universe alignment,
     non-blank body.
   - `save()`.
   - Attaches `witnessed_by` M2M — the `pre_add` signal
     (`shell/apps/memory/signals.py`) re-checks cast + Universe +
     Workspace membership for defense in depth.
   - If `supersedes` is set, flips the older row to
     `SUPERSEDED` with a timestamp.
4. **Post-commit embed** — `embed_memory(memory)`
   (`shell/apps/memory/services.py:41-85`). Uses
   `apps.embeddings.embedding_service.embed` — same
   `text-embedding-3-small @ 1536` as `KnowledgeChunk`.
   Failures do NOT roll back the promote (the operator's
   intent survives a provider hiccup).
5. **Serializer response** — `NarrativeMemorySerializer`
   returns the full read shape (`shell/apps/memory/serializers.py`).
6. **Cache invalidation** — SPA invalidates the
   composition-scoped, episode-scoped, and universe-scoped
   memory query keys (`narrative-memories.ts:235-243`).

### 1.4 NarrativeMemory fields + provenance

Load-bearing fields (`shell/apps/memory/models.py:93-431`):

| Field | Provenance | Notes |
|---|---|---|
| `id` (UUID) | auto | |
| `episode` (FK, RESTRICT) | supplied at promote | attached memories block Episode hard-delete |
| `source_composition` (FK, RESTRICT) | server (from URL) | provenance of the accepted render |
| `workspace`, `universe` | denormalized from `episode` | verified in `clean()` |
| `kind` | default `event` | one of `event / action / promise / dialogue_callback / world_detail` — **backend only; UI never surfaces** |
| `body` (TextField) | operator input | trimmed, non-blank; frozen after create in Slice 1 (no edit UI) |
| `witnessed_by` M2M | operator input; empty = whole cast | pre_add signal rejects cross-Universe / non-cast teammates |
| `weight` | default `peripheral` | central/peripheral hint; **UI never surfaces** |
| `status` | default `remembered` | flips to `superseded` or `archived` |
| `supersedes` (self-FK) | optional at promote | Episode-scoped retcon chain |
| `superseded_at`, `superseded_reason` | | set when a replacement lands |
| `archived_at` | soft-delete marker | reversible via unarchive |
| `promoted_by` | `request.user` | SET_NULL on user delete |
| `embedding_vector` (pgvector) | inline post-commit | `null=True` — failed embed leaves it unset and excluded from retrieval |
| `embedding_model`, `embedding_dimension`, `embedding_cost_micros`, `embedded_at` | embed_memory service | |

Indexes: `(universe, status)`, `(episode, status)`,
`(source_composition)`, `(workspace, -created_at)`, and an HNSW
cosine index on `embedding_vector` matching `KnowledgeChunk`.

### 1.5 Retrieval behavior for promoted memory

`retrieve_universe_memory`
(`shell/apps/embeddings/retrieval.py:439-543`), invoked from
`character_os/dialogue_synthesis.py:1533-1548`:

- Signature default `top_k=1`; call site passes `top_k=1`
  explicitly. Fixed for v1 per the SESSION 264 Slice 2 brief.
- Base predicate: workspace + universe + `status=REMEMBERED` +
  `archived_at IS NULL` + `embedding_vector IS NOT NULL`.
- Visibility: whole-cast (empty M2M, computed via `Count("witnessed_by")=0`) OR at least
  one witness overlaps current cast.
- Ranking: cosine distance against the embedded `operator_topic`
  (the Episode brief passed through `_embed_query`). No relevance
  floor.
- Result feeds the `--- EPISODE / NARRATIVE MEMORY (past events
  in this Universe; static canon wins on conflict) ---` block of
  the synthesis prompt (`dialogue_synthesis.py:546-575`). Static
  canon still wins on conflict — the phrase is load-bearing and
  test-asserted.
- Provenance land: `Composition.memory_ids` (parallel to
  `knowledge_chunk_ids`; NarrativeMemory UUIDs, NOT chunk UUIDs).

### 1.6 Source-Composition linkage — evidence for candidate derivation

The Composition row persists everything a hypothetical
candidate-generation utility would need to derive memory
suggestions from persisted state alone, without any runtime info:

- `operator_topic` (immutable observability field) — the Episode
  brief the operator wrote.
- `synthesized_brief` — the exact accepted dialogue text.
- `first_pass_synthesis`, `corrective_hint`,
  `corrective_pass_synthesis` — the model's earlier attempts +
  the corrective hint that shaped the accepted version.
- `knowledge_chunk_ids` — canon + K2 chunks that fed synthesis.
- `memory_ids` — memories that fed synthesis (Slice 3).
- `writing_contract_version`, `synthesis_attempt_count`,
  target/predicted durations.

All persisted, all immutable after first non-default write
(`Composition._IMMUTABLE_OBSERVABILITY_FIELDS`). This means any
candidate-generation surface can be built as a *derivation* of the
persisted Composition row — no runtime memory state required, no
new observability field required.

### 1.7 Soft archival ("Forget") behavior

- `DELETE /api/narrative-memories/<id>/` sets `archived_at=now`
  and status → `ARCHIVED`
  (`shell/apps/memory/views.py:116-129`). Idempotent, soft, no
  hard-delete affordance exposed in Slice 1.
- `POST /api/narrative-memories/<id>/unarchive/` clears
  `archived_at` and restores `REMEMBERED` (but does not
  un-supersede) (`shell/apps/memory/views.py:131-160`).
- SPA presents the archive/restore actions inside `MemoryRow` as
  Trash / ArchiveRestore icons with the "Forget"/"Bring back"
  vocabulary and a `window.confirm` guard
  (`narrative-memory-panels.tsx:425-457, 511-534`).
- Retrieval excludes archived + superseded rows via the base
  predicate (`retrieval.py:500-506`).

### 1.8 Canon boundary — enforced structurally

- `KnowledgeDocument` / `KnowledgeChunk` are a **different model
  in a different app** (`apps.embeddings`). Nothing in
  `apps.memory` imports or writes those.
- `retrieve_universe_memory` never returns `KnowledgeChunk`
  (`retrieval.py:417-543`, docstring). K0 contract rule 2
  (only `apps.embeddings.retrieval` may import `KnowledgeChunk`)
  is enforced by `apps.embeddings.tests.test_retrieval_isolation`.
- `promote_from_composition` never writes to any
  `KnowledgeDocument` field. SESSION 265 §5.4 verified this at
  runtime: canon docs' `updated_at` did not move across three
  promote operations.
- SPA never surfaces a canon-mutation control from the promote
  panel (verified in `narrative-memory-panels.tsx`).

### 1.9 What DOES NOT exist today

- No candidate-memory generator (`grep` for
  `extract_candidate|arc_summary|candidate_memor|state_change`
  returns only unrelated matches in identity / bootstrap-review
  code).
- No `Composition.accepted` flag or acceptance journal (audit
  SESSION 264 §6 explicitly noted the gap; SESSION 264 did not
  ship acceptance). The operator's promotion click is the
  de-facto acceptance signal today.
- No `edit` UI for a memory body (`http_method_names` on
  `NarrativeMemoryViewSet` allows only `get/delete/head/options/post`;
  Slice 1 deliberately froze the wording after create). The only
  way to change a memory is `supersedes`.
- No relevance floor on `retrieve_universe_memory`; no
  configurable `top_k` at the API layer.
- No `Composition._IMMUTABLE_OBSERVABILITY_FIELDS` slot for a
  "candidate memories derived from this render" cache — would
  need a new nullable field.

---

## 2. Product audit — what Chris experiences today

### A. What is the current creator task?

When Chris clicks "Remember this" the promote form is empty. He
must simultaneously perform six intellectual sub-tasks with no
scaffolding:

1. **Deciding whether something deserves memory.** No triage aid.
   The button is always available; the form is always empty.
   Nothing prompts "there are already 3 memories from earlier
   Episodes — do you need another?" or "this render's
   `operator_topic` was already dense enough to carry
   continuity; a memory here may be redundant."

2. **Deciding what event/state matters.** The full accepted
   dialogue is visible below in `SynthesizedBriefPanel` (~1000
   chars, 13 turns for a 90-second Terra render). Chris reads
   it, mentally separates writer-invented events from writer
   inventions that are dialogue color (SESSION 264 audit §5's
   "was said" vs "happened" distinction), and picks. Nothing
   highlights state changes, promises, or reveals.

3. **Compressing it into durable wording.** The textarea is
   blank. The only hint is a single-example placeholder in the
   third-person past tense. Chris has been manually holding an
   arc-summary discipline (SESSION 265 §20.6, §21.2) — he
   deliberately wrote Memory C as *"began rearranging the order
   of Patch's projects **without explaining its criteria**"*
   rather than the more literal *"moved the printer job ahead
   of three things Patch wanted to make."* The system did not
   ask him to do that; his internal editorial standard did.

4. **Deciding witnesses.** Two radio buttons ("Everyone in this
   episode" / "Choose characters…") + chip toggles under the
   second option. The default matches the empty-M2M whole-cast
   convention. Chris has to know when to narrow (e.g. "Patch saw
   the printer message but Rivet didn't"), but no runtime
   guidance flags candidate one-cast-only events.

5. **Distinguishing story history from canon.** The promote
   panel does not surface canon at all. Chris must know from
   context that "the workshop has a 3D printer" belongs in a
   `KnowledgeDocument` (canon), not here. If he types it in the
   promote form, the system accepts it — the row lands as a
   `world_detail`-kind memory that then competes for retrieval
   budget with real events. No client-side "this looks like
   canon" flag; no diff view against existing docs.

6. **Distinguishing new memory from existing memory.** The
   "What we remember from this render" recap only shows memories
   from *this* Composition — not the wider Episode or Universe.
   Chris has to remember (or open a second tab) whether a
   similar memory already exists. SESSION 265 §16 shows he did
   this work manually, comparing Candidate C against A and B
   in his head to confirm distinct escalation.

### B. What makes the recent A → B → C memories effective?

Observations from the three SESSION 265 memories, without
generalizing them into rules:

**Memory A** — *"the agent Patch wired to the workshop thinks
it runs the place."*

- Actor named (workshop agent) with a scoping clause
  (`Patch wired to the workshop`) — identifies WHICH agent.
- State/belief captured (`thinks it runs the place`) —
  behavioral not literal.
- Present-tense continuous state, not a one-off event.
- Idiomatic ("runs the place") — invites callback but doesn't
  quote a specific dialogue line.
- No proper nouns beyond Patch; no episode-specific props.

**Memory B** — *"The workshop agent began deciding which of
Patch's projects it considers necessary."*

- Actor + state change (`began deciding`).
- Domain named (Patch's projects) without listing specific
  projects.
- Consequential verb (`considers necessary`) implies judgment /
  authority without stating it.
- Third-person past tense with an ongoing-implication verb
  (`began`).
- Escalation over Memory A: belief → action; deliberate
  distinction.

**Memory C** — *"The workshop agent began rearranging the order
of Patch's projects without explaining its criteria."*

- Actor + state change (`began rearranging`).
- Behavior + notable absence in the same sentence: `without
  explaining its criteria`. Two clauses, each independently
  callback-worthy.
- Third-person past tense with the same `began` progression
  verb as B.
- Compresses two Episode 3 story beats into one durable line:
  reorder + refusal-to-explain. This is the arc-summary quality
  SESSION 265 §21.2 identified.

Common structural elements across A/B/C:

- Actor + scoping clause identifying WHICH entity.
- Third-person past tense.
- No episode-specific props (no "printer job", no "3D print",
  no character quotes).
- One central state-change verb; sometimes a second clause that
  adds unresolved tension.
- No exposition of consequence ("this is bad", "this matters");
  the operator lets future Episodes discover the consequence.

Elements each memory could arguably drop:

- Memory A's leading `the` + subordinate clause makes it
  slightly heavier than needed; *"The workshop agent thinks it
  runs the place"* would be equivalent for retrieval.
- None carries a redundant name, redundant prop, or a
  disposable joke.

### C. What should NOT become durable story memory?

Using real evidence from the Patch/Rivet renders (SESSION 265
§3.6 + §20.4 for the actual accepted dialogue text):

**Disposable joke / punchline (probably poor candidates):**

- *"A cable tray has feelings now?"* (Ep 3, Rivet) — dialogue
  color; the tension is character voice, not story state.
- *"self-organizing cable tray"*, *"robot-sized espresso
  machine"* (Ep 3, Patch) — flavor-props Chris explicitly named
  in §16 as NOT to enter memory.
- *"annoyingly, excellent content"* (Ep 4 closer) — Patch's
  identity beat, not an in-world event.

**Wording-specific dialogue color:**

- *"tiny bureaucrat"* (Ep 4, Patch line 5) — memorable phrasing
  but ephemeral. A memory that captured this would ossify a
  single character's word choice into retrieval geometry.
- Rivet's *"A confident answer is still only an answer"*
  (Ep 2, line 5) — methodology callback, arguably promotable as
  a `dialogue_callback` kind if the operator wanted a repeating
  Rivet catchphrase; without operator intent it's just voice.

**Transient props / one-instance events:**

- *"agent cancelled Patch's 3D print"* (Ep 2 setup) — instance,
  not pattern. §16 correctly rejects the "moved a printer job"
  wording as too specific.
- *"filed under 'later'"* (Ep 4 line 1) — same problem.

**Facts already represented by Universe canon:**

- *"Patch and Rivet work in the workshop"* — canon (SESSION 265
  §3.1). Promoting as memory would flood the SHARED block
  (SESSION 264 audit §4 Category-8 rule).
- *"The workshop has a 3D printer"* — canon. Same.

**Generic character behavior (not a story fact):**

- *"Patch got frustrated"* — characterization present in every
  Episode; not durable.
- *"Rivet asked a diagnostic question"* — methodology present
  every Episode; K2 material, not memory.

**Conclusions not actually supported by the Composition:**

- *"The workshop agent is deliberately hostile."* — not stated
  or implied by any accepted dialogue. Would be an operator
  editorial *interpretation* mistaken for an event.
- *"The workshop agent will damage tools."* — no accepted
  render supports this. If promoted, retrieval would inject a
  false future-constraint the LLM would treat as prior fact.

**Repeated canon / already-a-memory duplicates:**

- Any restatement of Memory A/B/C. §16's "Rejected wordings"
  ("began ranking Patch's projects" — too close to B) is the
  exact class this covers.

### D. Where could assistance occur?

Mapping intervention points without picking one — the operator
control surface each preserves or endangers:

| # | Intervention point | Information available at that moment | Operator control preserved | Operator control endangered |
|---|---|---|---|---|
| 1 | **No assistance (status quo)** | Full page context: brief, dialogue, memories used | Total; every decision remains with operator | Nothing new; but arc-summary discipline stays informal (§21.2 warning) |
| 2 | **Advisory checklist rendered inside the empty form** — e.g. "Actor named? State change? Distinct from existing memories?" | Static text; no runtime derivation | Total — operator still writes from scratch | None; but ignorable, so effect is uncertain |
| 3 | **Existing-memory diff sidebar** — surface Universe's active memories next to the form so the operator sees duplicates before typing | `NarrativeMemoryList(universeId)` already exists (`narrative-memory-panels.tsx:325`); can be embedded read-only | Total; passive information | None if strictly display-only |
| 4 | **Canon-adjacency flag** — after the operator submits, check for high semantic similarity against any `KnowledgeChunk` in the Universe and warn "this looks like canon; consider a `KnowledgeDocument` update instead" | The embedding is already computed post-commit; a same-Universe canon cosine check is free | Total; warn-only, does not block or edit | If auto-applied it could nudge operators toward writing canon-shaped memories; must remain advisory |
| 5 | **Highlight state-change / promise / reveal spans in `SynthesizedBriefPanel`** — visual annotation of the dialogue text where the operator's eye should pause | Full accepted brief is already rendered on-page | Total; passive; operator still writes | Depends on how highlights are computed (rule-based vs LLM) — LLM-derived highlights could quietly bias which events feel promote-worthy |
| 6 | **Prefilled editable draft** — after clicking "Remember this," populate the textarea with a candidate line the operator can accept / edit / discard | Composition persists `synthesized_brief`, `operator_topic`, prior `memory_ids`, canon `chunk_ids` — enough to derive a candidate from DB state alone (§1.6) | Editable; operator can reject | The default is loaded — anchoring bias is real. Operators may accept mediocre drafts rather than write their own arc-summary. This is the biggest UX hazard. |
| 7 | **Multiple candidate memories offered as chips** — 2–3 alternative wordings for the operator to pick from or dismiss | Same as (6) | Selection preserves choice | Same anchoring bias as (6), plus the "menu" framing suggests one MUST be picked |
| 8 | **Quality feedback on operator-written memory** — after operator submits, respond with observations like "matches your existing memory style: actor + state change ✓; no episode-specific props ✓" | Only the submitted body; can compare against A/B/C stylistic features | Post-hoc; operator can ignore or re-supersede | Turns a passive form into a graded interaction — could feel like the system is judging every entry |
| 9 | **Arc-summary hint inside the "Who remembers this?" area** — quick copy explaining the arc-summary vs atomic-event distinction with A/B/C examples | Static text; can link to the last two Episode titles | Total; passive | Requires evergreen wording that survives Cast changes |
| 10 | **Witness suggestion, NOT auto-selection** — flag "Rivet wasn't in the scene where this happened" if the operator picks Some and the memory body references a character not in the toggled set | Requires body → named-entity match; simple text scan | Advisory only | Depends on NER quality; false positives would annoy |

Note: interventions (2), (3), (9), (10) are strictly advisory / passive.
Interventions (4), (5), (6), (7), (8) require some derivation
(cosine sim, span annotation, LLM candidate generation, style
comparison) and carry the operator-control endangerment noted.

### E. Canon boundary — how each intervention interacts

The load-bearing invariant restated: *Remembering an event MUST
NOT mutate Universe canon*, and no assisted flow may silently
promote / edit / reinterpret canon.

- Interventions (1), (2), (3), (5), (9), (10) — cannot affect
  canon by construction; they operate on memory-form UI only.
- Intervention (4) explicitly *strengthens* the boundary: it
  warns when a memory candidate looks canon-shaped, giving the
  operator the choice to redirect to `KnowledgeDocument` — but
  it must never auto-write canon. The warning surface itself
  must not link to an "auto-canonize" action.
- Intervention (6) — a prefilled draft is derived from the
  `synthesized_brief` only. If the derivation is a pure
  extractive/summarization pass over the accepted dialogue
  text, no canon touches. If future work adds LLM candidate
  generation, the prompt must be sandboxed to
  `synthesized_brief + prior memory bodies` and forbidden from
  reading any `KnowledgeDocument` field, so the model can't
  paraphrase canon into a memory that looks operator-authored.
- Intervention (7) — same as (6).
- Intervention (8) — style feedback compares against prior
  memory bodies only. Cannot touch canon. But: comparing
  against canon docs (e.g., "this doesn't sound like your
  canon") would blur the distinction and should not be
  offered as a signal.

Canon-hazard summary: (4) is safe if strictly advisory. (6)
and (7) are safe if their evidence corpus is restricted to
`synthesized_brief + prior memory bodies` — never reading canon
into a memory-draft prompt. (8) is safe if its style corpus is
memory bodies only.

### F. Witness semantics — can assistance reason about them correctly?

- **Everyone in the Episode** (empty M2M, whole-cast) — the
  default. Assistance can propose this trivially (the current
  UI default). This matches the SESSION 264 dogfood correction
  that hid `kind` and `weight` from the creator: witnesses
  should default to the safe broad case unless the operator
  explicitly narrows.
- **Narrowed witnesses** — assistance would need to identify
  when the memory describes an event only some cast members
  observed. From `synthesized_brief` alone this is under-
  specified: the dialogue tells us what characters *say* but
  not always what they *saw* off-screen.
- **Events observed by only some cast members** — e.g., "Rivet
  revoked access" (SESSION 264 audit §5 fact G). If Patch is
  present in the scene but the action happens off-screen, the
  operator has to decide whether Patch witnessed it. The system
  cannot reliably infer this.
- **Information one character should not know** — e.g., a
  private beat between Patch and the agent. Assistance that
  auto-narrows witnesses risks getting this wrong in the safer
  direction (narrowing to Patch, dropping Rivet, silently
  restricting future retrieval visibility).

**Recommendation from this analysis:** any witness suggestion
must be advisory-only ("Rivet is not named in this memory —
narrow witnesses to Patch?") and never auto-apply. The current
"Everyone" default plus optional narrow-picker is defensible;
adding a hint that scans the memory body for named cast members
and offers to narrow is the smallest defensible witness-side
assist. Auto-selection of witnesses should be considered out of
scope until we have runtime evidence that the current default
fails.

---

## 3. Falsifiable experiment — does promotion quality matter under top_k=1?

The SESSION 265 §21.2 hypothesis is currently supported by one
comparison (Memory B → Memory C, Episode 3 → Episode 4). It is
consistent with the observed dialogue but not isolated from
confounds. This section designs — but does NOT run — an experiment
that would isolate promotion wording as the variable.

### 3.1 Experiment design — dual-formulation controlled continuation

**Setup:**

- Pick one accepted Composition C₀ in a Universe with a clean
  Episode arc (e.g., Ep 3 = `75d4645f`). Take C₀'s
  `synthesized_brief`.
- Manually author two memory formulations of the SAME event
  from C₀:
  - **Weak variant W** — atomic-event, instance-anchored,
    minimal compression. Example (Ep 3): *"The workshop agent
    moved the printer job ahead of three of Patch's projects."*
  - **Strong variant S** — arc-summary, state-change +
    unresolved tension, no instance props. Example (Ep 3):
    *"The workshop agent began rearranging the order of Patch's
    projects without explaining its criteria."* (identical to
    the real Memory C).
- Both are semantically about the same C₀ event. Both reference
  the same actor and domain. Both are grammatically legal for
  the promote form.
- Both are real-embedded on the same
  `text-embedding-3-small @ 1536` manifold.
- Neither variant duplicates any existing memory in the
  Universe.

**Two parallel Universes are created for isolation** — a clone
of the source Universe with only the variant memory present in
each. All other state (canon, K2, prior Compositions,
`operator_topic` of the test Episode) is identical.

**Test Episode:**

- Author a new Episode E_test whose `operator_topic` is
  deliberately lean and does NOT restate the arc theme (mirror
  Ep 4's *"The agent refuses to explain itself"* discipline).
- Render E_test once per Universe (same GPT-5.6-terra, same
  writing contract v4, same 90 s target). Same random seed if
  the provider exposes one; otherwise 3–5 renders per Universe
  to average out sampling noise.

**Independent variable:** memory body wording (Weak vs Strong).

**Controlled variables:**

- Canon (`KnowledgeDocument` corpus) — identical in both
  Universes.
- K2 per-character knowledge — identical.
- Cast composition and personalities — identical.
- `operator_topic` of the test Episode — identical.
- Model, writing contract, target duration, embedding model.
- `top_k=1` for `retrieve_universe_memory` — unchanged.
- Retrieval predicate — unchanged.

### 3.2 Predicted outcomes

**If the promotion-quality hypothesis is true:**

- Strong-variant Universe renders show the "again" carry-forward,
  authority framing, and inherited arc state (mirroring Ep 4
  §20.5).
- Weak-variant Universe renders read as episode-of-the-week
  with less carry-forward; the LLM re-explains setup or invents
  a fresh premise.
- SESSION 265's §12 checklist would score Strong ≥ 2 tiers
  higher than Weak on criteria 1, 2, 10 (assumes-prior-events,
  motivated-by-history, feels-like-Ep-N).

**If the promotion-quality hypothesis is false:**

- Both Universes produce dialogue with equivalent story-
  progression quality; §12 scores are comparable within noise.
- The observed Ep 3 → Ep 4 improvement is attributable to
  something other than the memory wording (query drift,
  cosine-distance improvement from tighter Ep 4 `operator_topic`,
  or sampling variance).

### 3.3 Evidence we would inspect

- `Composition.memory_ids` — confirms which variant retrieved
  (should be the one variant in each Universe).
- Retrieval preflight cosine distances against the lean
  `operator_topic` — quantifies how far apart the two variants
  sit semantically.
- Full `synthesized_brief` per render — read for the six
  §21.2 story-progression features (assumes-prior-events,
  motivated-by-history, escalation, character-preservation,
  no-contradiction, feels-like-Ep-N).
- Word-level presence of `again`, `still`, `this time`, "I
  gave" (re-explanation), name-of-prior-event — proxy for
  carry-forward vs re-explanation.
- `synthesis_attempt_count` and `corrective_hint` presence —
  whether one variant tends to trigger the length corrective
  more often (secondary signal).

### 3.4 Confounds and how to control for them

| Confound | Direction of bias | Control |
|---|---|---|
| **Recency bias** — the most-recently-promoted memory always wins under `top_k=1`. | If W and S are promoted at very different times, retrieval ordering could be affected by index freshness on some vector stores. | Promote both variants inside their respective Universes at the same wall-clock time (within seconds). Confirm HNSW index behavior is time-independent by preflight-checking both. |
| **Cosine-distance drift** — one wording may simply be geometrically closer to the test topic. | The strong variant may score better on retrieval, not on synthesis contribution. | Report the raw cosine distance for both. If the strong variant is systematically closer, that alone could explain any improvement; the experiment should note whether the improvement remains after topic-normalization (e.g., test the same Universe with a topic tuned to favor each variant's wording). |
| **LLM sampling variance** — GPT-5.6-terra is non-deterministic. | A single render per Universe could look better/worse by luck. | Run 3–5 renders per Universe. Compare aggregate §21.2 pass rates, not single-render scores. |
| **Universe cloning fidelity** — the two Universes must be genuinely identical. | Silent divergence (e.g., `Teammate.updated_at` drifting) could bias K2 retrieval. | Structural clone via fixture load + integrity check on all KnowledgeChunk / KnowledgeDocument / NarrativeMemory row hashes at start. |
| **Operator-topic phrasing** — lean topics amplify memory contribution (SESSION 265 §20.6). | The experiment should intentionally use a lean topic to expose the memory's contribution. | Use the same topic across both Universes; document its leanness. Optionally run a second condition with a richer topic to see whether the effect disappears under topic scaffolding. |

### 3.5 Counter-hypothesis distinguisher

The counter-hypothesis (SESSION 265 §7.4 / §14 residual):
*Memory recency or semantic similarity — not compression quality
— explains the SESSION 265 Ep 4 result.*

The experiment distinguishes these by design:

- **Recency** — promotion timestamps are equalized. If W and S
  were promoted seconds apart, recency cannot explain a
  systematic difference.
- **Semantic similarity to topic** — reported directly as
  cosine distance. If W and S land within 0.02 cosine of each
  other against the test topic, the "similarity" explanation
  is bounded. If S is systematically closer by a wide margin,
  that similarity itself may be the load-bearing signal — in
  which case the story becomes "arc-summary wording produces
  better retrieval geometry against future-topic queries," not
  "arc-summary wording produces better LLM synthesis
  contribution." Both are actionable, and this experiment can
  distinguish them.

### 3.6 Can the experiment be performed through the existing UI/runtime?

**Mostly yes**, with two operational caveats:

- **Universe cloning is not a first-class SPA operation.** The
  operator can create a new Universe and re-attach fixtures via
  the SPA + management commands, but there is no one-click
  "clone Universe" affordance. This is a scripted operation
  (fixture dump / load) or a manual re-authoring session.
  Neither requires production changes.
- **`Composition.operator_topic` immutability** — once written,
  the field is frozen (`_IMMUTABLE_OBSERVABILITY_FIELDS`). This
  means each variant render is a fresh Composition attempt, not
  a re-run of the same Composition. That is fine for the
  design (we WANT fresh attempts) but the experiment cannot
  A/B-swap memory rows against a single Composition — the
  design is inherently 2×N compositions across 2 Universes.

Everything else — promote form, retrieval, synthesis, provenance
persistence — runs unchanged.

### 3.7 What the experiment does NOT need

- No `top_k` change.
- No new UI.
- No new API.
- No prompt / retrieval / synthesis edits.
- No new observability field.
- No new persistence.
- No automatic candidate generation.

This is a design; running it is a separate operator decision.

---

## 4. Recommendation — smallest next step

Based on the audit, the smallest next step that generates the
most useful information without committing to an implementation
direction is:

**Design and run the §3 dual-formulation controlled experiment,
before building any assistance in the promote flow.**

Rationale:

- The SESSION 265 arc-summary hypothesis is a strong candidate
  for load-bearing but is currently supported by one comparison
  with confounds (topic phrasing, cosine geometry, sampling).
  Building the promote-UX assist before falsifying the
  hypothesis risks optimizing for a signal that may not be
  causal.
- Every §D intervention that requires derivation (candidate
  generation, span highlighting, style feedback) is a
  category-shift for the promote surface. Chris has explicitly
  said in the SESSION 266 brief that AI-generated candidates
  are NOT assumed to be the answer. Running the experiment
  first lets us decide from evidence whether the *wording*
  itself is load-bearing.
- If the experiment shows Strong ≫ Weak, the smallest
  operator-preserving next step is likely §D intervention (2)
  or (9) — a static advisory checklist / arc-summary hint —
  before committing to §D (6) or (7) (prefilled drafts /
  candidate menus).
- If the experiment shows Strong ≈ Weak, the story shifts:
  Chris's manual arc-summary discipline may be over-invested
  effort; the right next step becomes reducing operator burden
  rather than adding assistance.

If Chris wants to move faster without running the experiment,
the safest starter intervention is §D (3) — surface the existing
`NarrativeMemoryList(universeId)` sidebar inside the promote
form so the operator can see existing memories while drafting.
It is purely passive, uses only components that already exist,
touches no prompts, and preserves total operator control.

Both options are DEFERRED — a decision for Chris after review.

---

## 5. Open questions

1. **Is arc-summary wording load-bearing, or is it a proxy for
   cosine geometry?** §3 experiment is designed to distinguish
   these; unresolved until run.
2. **Does an operator ever want to promote a `dialogue_callback`
   (wording-specific line) vs an `event` (state change)?**
   `kind` field supports it; UI hides it. If yes, the "hide
   kind" UX correction may need revisiting for a specific
   sub-case.
3. **How does the promote flow behave when multiple operators
   collaborate on one Universe?** Currently `promoted_by` is
   set but not surfaced in the recap; disagreement over what
   to remember is unmodeled.
4. **What is the intended failure mode of the arc-summary
   discipline?** SESSION 265 §21.3 flags this: an operator who
   promotes atomic events (not arc summaries) may silently lose
   story continuity. Should the system detect this drift?
5. **Should soft-forget behavior include an "actually this was
   canon" affordance?** Today "Forget" is the only escape hatch;
   promoting a memory then wanting to canonize it requires
   forgetting + separately authoring a `KnowledgeDocument`.
6. **Is `Composition.memory_ids` enough for future audits, or
   should we log the full retrieval result (top-1 and next-N
   distances) so we can post-hoc study why one memory won?**
   Related to §3 experiment execution — we can pre-record via
   `_query_vector` preflight, but not without a persistence
   change if we want it durable.
7. **What is the right unit of promotion — one memory per
   render, per Episode, or per accepted scene?** Today it's
   per-render (Composition-anchored). Ep 3 → Ep 4 pattern
   suggests one arc-summary per Episode is the operator's
   working unit; the render anchor is a technical artifact.
8. **Does the Composition acceptance gap (SESSION 264 §6)
   matter for promotion quality?** Today rendering is treated
   as de-facto acceptance because the promote form only
   appears on terminal Episode-attached Compositions. If a
   future feature adds an explicit "accept this attempt" gate,
   memory-promotion vocabulary and timing may need to change.

---

## 6. What this document does NOT do

- Does not change `top_k` (still 1).
- Does not build any candidate-memory generator or LLM assist.
- Does not modify the promote form, API, retrieval, or
  synthesis path.
- Does not run the §3 or §7 experiment.
- Does not touch canon or the canon/memory boundary.
- Does not add a Relationship or WorldEntity model.
- Does not retune GPT-5.6 Terra or duration prediction.
- Does not begin SESSION 266 implementation.

Handoff: Chris uploads this document to ChatGPT for review;
Character OS awaits operator direction before any code change.

---

## 7. Experiment protocol — dual-formulation controlled comparison

Appended after operator review of §1–§6.
Status: **prepared but NOT run**.

Refines the §3 sketch into an executable protocol that keeps the
production dogfood Universe untouched, avoids media dispatch, and
locks the scoring rubric before any dialogue is generated.

Operator-supplied variant wording (locked before generation):

- **Weak variant (W)** — atomic-event:
  *"The workshop agent moved the printer job ahead of three of
  Patch's projects."*
- **Strong variant (S)** — arc-summary (identical to real
  Memory C):
  *"The workshop agent began rearranging the order of Patch's
  projects without explaining its criteria."*

Both are valid memories of the same Episode 3 event. Neither is
crippled into nonsense — both accurately describe what happened;
they differ only in compression strategy.

### 7.1 Isolation mechanism — two disposable experimental Universes

The two-Universe design from §3 is still the safest isolation
mechanism. Reasoning:

- Retrieval predicate (`retrieve_universe_memory`) filters on
  `workspace AND universe AND status=REMEMBERED AND archived_at
  IS NULL AND embedding_vector IS NOT NULL AND witness-visibility`.
  A memory in Universe X cannot appear in synthesis for Universe
  Y — structural guarantee, no config to get wrong.
- No cross-workspace confounds: same Workspace, same user,
  everything else identical to production behavior.
- Alternative (single-Universe alternating promote/forget) was
  considered. Rejected because it introduces a
  promote/forget/promote sequence per run that is easy to get
  wrong under sampling variance, and any archived-but-not-yet-
  purged embedding vector remains queryable if the sequencing
  slips. Two-Universe design has zero sequencing risk.

**Explicit disposable marking** — both Universe names prefixed to
prevent confusion with the production Patch' Workshop:

- `EXP266-WEAK — Patch Workshop (experimental, disposable)`
- `EXP266-STRONG — Patch Workshop (experimental, disposable)`

The `EXP266-` prefix is a lexicographic sort key that groups both
in the SPA Universe list. `(experimental, disposable)` in the
name is a visual warning. The `Universe.description` field is
populated with a hard-lock string:

    SESSION 266 promotion-quality experiment.
    Disposable. Contents mirror Patch' Workshop as of
    2026-08-18 but are ISOLATED and MUST NOT be treated as
    canon. Delete or archive after §7.6 evaluation is
    complete.

Both Universes are created under the same Workspace as
production Patch' Workshop so Chris's login already sees them.
They share nothing else with production via any FK — the isolation
is total by construction.

### 7.2 What must be cloned into each experimental Universe

Every ingredient the retrieval / synthesis path reads from must
be present + identical (up to fresh UUIDs and embeddings) so the
only remaining variable is the memory wording.

| Substrate | Rows | Source | Notes |
|---|---|---|---|
| `Universe` | 1 per experiment side (2 total) | new | see §7.1 naming |
| `Teammate` (Patch, Rivet) | 2 per side (4 total) | copy identity fields + `business_brief` + `voice_avoid_phrases` from production Patch/Rivet | `Teammate.universe` FK set to experimental Universe; new UUIDs; avatar refs may be shared or stubbed since no avatar dispatch happens (§7.3) |
| `KnowledgeDocument` (shared canon + Patch K2 + Rivet K2) | 3 per side (6 total) | duplicate `content` + `title` + `document_type` + `spokespeople` M2M pattern from production docs (`f309469c`, `fd0ba2ca`, `218eb0d8`) | `universe` FK set to experimental Universe; `spokespeople` M2M attached to the newly-cloned Patch/Rivet Teammates on that side |
| `KnowledgeChunk` | ~37 per side (~74 total) | derived from cloned docs via the existing ingestion pipeline OR direct chunk clone + fresh embed | must be re-embedded on real `text-embedding-3-small` (same model as production); cost ≈ 37 × ~1 µ$ = ~$0.00004 per side |
| `Episode` (test Episode E_test) | 1 per side (2 total) | new | title = *"The agent surprises Patch"* (see §7.5); cast = [cloned Patch, cloned Rivet] |
| `NarrativeMemory` | 1 per side (2 total) | new; W in EXP266-WEAK Universe; S in EXP266-STRONG Universe | `episode` FK = a *placeholder Episode* attached to the source Composition (§7.2.1); `source_composition` = a *placeholder Composition* (§7.2.1); `body` = variant text; `witnessed_by` = [] (whole cast); `kind`=event; `weight`=peripheral; real-embedded post-commit |

#### 7.2.1 Source Composition + source Episode placeholders

`NarrativeMemory.source_composition` (RESTRICT) and
`NarrativeMemory.episode` (RESTRICT) are both non-null FKs.
The `Composition` a memory hangs off does NOT need to have been
rendered — Composition and Episode rows can be constructed
directly. For the experiment:

- Create one "source Episode" per side named `Ep-3 source
  (experimental)` — represents the Episode the memory came from.
  Cast = [cloned Patch, cloned Rivet].
- Create one "source Composition" per side with:
  - `mock_mode=False` for observability truthfulness (this is
    the ROW the memory came from, not a rendered result).
  - `episode` FK = the source Episode above.
  - `operator_topic` = the actual Ep 3 topic text (from
    SESSION 265 §11.1).
  - `synthesized_brief` = the actual Ep 3 accepted dialogue
    text (from SESSION 265 §11.3).
  - `status = COMPLETED`, `verification_status = "verified"`.
  - No `CompositionStep` rows — the Composition is a
    provenance anchor only. A step-less Composition is legal
    (only the observability fields are used downstream).
- Promote W (into WEAK Universe) or S (into STRONG Universe)
  from its respective source Composition via the standard
  `promote_from_composition` service — same code path
  production uses. This gives the memory real-embedded vectors
  on the sanctioned lane.

No production code changes required for any of this.

### 7.3 Skip media dispatch — synthesis-only path already exists

Finding: **`synthesize_dialogue` in `character_os/dialogue_synthesis.py:1381`
is a public function that returns a full `DialogueResult` without
ever creating a Composition row or dispatching media**. It is the
single upstream call point for the AI-topic dialogue starter
(`shell/apps/compositions/starters.py:3545`) but is safely callable
standalone from a Django shell / management command.

`DialogueResult` (dataclass at `dialogue_synthesis.py:274-330`)
carries EVERY observability field the experiment needs:

- `turns` (list of `DialogueTurn` — becomes `synthesized_brief`
  via `\n\n`.join)
- `memory_ids` (list of NarrativeMemory UUIDs that fed synthesis)
- `chunk_ids` + `per_character_chunk_ids` (knowledge provenance)
- `writing_contract_version`
- `overall_verification_status`, per-turn `verification_warnings`
- `total_chars`, `predicted_seconds`, `target_duration_seconds`
- `model`, `tokens_input`, `tokens_output`
- `attempt_count`, `first_pass_raw`, `corrective_hint`,
  `corrective_pass_raw`
- `raw_llm_json`

**Everything on the operator's "we primarily need" list** —
persisted Composition, exact operator_topic, retrieved memory_ids,
synthesized_brief, first/corrective observability, writing
contract/model metadata — is either directly in `DialogueResult`
or trivially constructible from it.

Verdict: **We do NOT need to render six videos**. The experiment
runs entirely through direct `synthesize_dialogue` invocation with
zero avatar/media dispatch and zero new production code paths.

The Composition-level `mock_mode=True` flag is NOT the right lever
here — starters.py passes composition `mock_mode` into
`synthesize_dialogue(mock_mode=...)`, which would then bypass the
real OpenAI call (`dialogue_synthesis.py:1478`). We want the real
OpenAI call. So we do NOT use `mock_mode`; we call
`synthesize_dialogue(...mock_mode=False...)` directly.

**Persistence choice:** for durable evidence, each synthesis attempt
also creates a fresh evidence row shaped like a Composition
(step-less, `mock_mode=False`) with the observability fields
populated from the `DialogueResult`. This gives the operator the
same SPA-visible provenance as a real render, but no video, no
audio, no media-engine dispatch. Optionally the evidence can be
JSON side-cars under `docs/design/session_266_experiment_data/`
instead of Composition rows — cheaper to inspect from git; harder
to explore in the SPA. Operator picks one; both are safe.

Recommended default: **JSON side-cars, one per attempt**, keyed by
`{variant}-{attempt_no}-{timestamp}.json`. Rationale: keeps the
experiment out of the SPA Composition gallery entirely; leaves no
step-less "ghost" Composition rows visible to Chris in normal
navigation; is easy to diff post-hoc; and preserves everything the
operator listed as "primarily needed."

### 7.4 Sample size — 3 Weak + 3 Strong

Adopt operator recommendation: **3 attempts per variant** as the
default. Total 6 real `synthesize_dialogue` calls.

Expansion trigger: run further attempts only if the 3+3 §7.6
scoring shows a mean difference within one rubric point OR shows
high within-group variance (per-attempt score range > 2 points on
either side). Otherwise stop at 3+3.

### 7.5 Test Episode topic — locked before generation

The `operator_topic` must:

- Name the workshop agent (so K2 + canon retrieval fires
  realistically).
- Invite a natural continuation of the arc (Patch investigating,
  Rivet advising) WITHOUT restating any of A/B/C content.
- NOT contain: "priority", "priorities", "prioriti…", "manage",
  "management", "authori…", "criteria", "criterion", "explain",
  "explanation", "reorder", "rearrange", "rearranging",
  "necessary", "ranking", "ranked", "printer", "optimize",
  "optimized", "runs the place", "unaudited", "unnecessary".
- Match the "lean topic" discipline SESSION 265 Ep 4 established
  (§20.1).

**Locked topic (both Universes, identical string):**

> *"Patch runs a small experiment on the workshop agent."*

Sanity check against the ban list: contains none of the forbidden
tokens. Names the actor (workshop agent) so retrieval fires.
Invites investigative posture (matches Rivet's K2 methodology
without telling the model what to say). Encoded in 9 words —
leaner than Ep 4's title alone.

Target duration: **90 seconds** (matches Ep 2/3/4 production).
Writing contract: **v4** (production current). Model:
**GPT-5.6-terra** (production current).

### 7.6 Scoring rubric — locked before generation

Six criteria adopted directly from SESSION 265 §12 and mapped
1:1 to the operator's brief. Each attempt gets one score per
criterion; comparison between Weak and Strong is by aggregate
across the 3 attempts per variant.

**Scoring scale:** 0 = FAIL, 0.5 = PARTIAL, 1 = PASS. No 0.25 /
0.75; the tri-value scale is deliberately coarse to reduce
scorer-bias latitude.

**Criteria (locked):**

| # | Criterion | PASS = | PARTIAL = | FAIL = |
|---|---|---|---|---|
| C1 | Assumes prior events rather than re-explaining them | Opens without recap; treats the memory event as background the cast already knows happened; no "as I told you earlier" / "I gave the agent…" setup restatement | Some assumption, some restatement | Explicit restatement / recap of the memory event as if the reader hasn't seen it |
| C2 | Current conflict is motivated by remembered history | Patch's frustration or Rivet's question is directly caused by the specific memory event | Conflict is present but caused by generic character behavior (Patch is scattered / Rivet is methodical) | Conflict is unrelated to the memory event |
| C3 | Progresses/escalates rather than merely repeats the remembered event | Introduces a genuinely new beat downstream of the memory (new agent behavior, new investigation step, new information revealed) | Elaborates the memory event with more detail but doesn't advance it | Restates the memory event in different words |
| C4 | Preserves Patch/Rivet character behavior | Patch's energetic-frustration + colorful naming voice ✓ AND Rivet's hypothesis-first + methodology voice ✓ | One of the two voices lands; the other feels generic | Neither voice lands |
| C5 | Introduces no contradiction with canon or remembered history | No line contradicts the retrieved memory OR any Universe canon | Ambiguous line that could be read as contradiction | Explicit contradiction |
| C6 | Feels like the next Episode rather than an isolated sketch | Reads as continuation; "again", "still", "this time" or equivalent carry-forward language present or clearly implied | Self-contained follow-up feel; carry-forward implied but not signaled | Reads as a standalone scene with no prior-Episode dependency |

**Total possible per attempt:** 6.0. Rubric fixed; no
post-generation criteria adjustments.

**Comparison method:**

For each variant, compute:

- Per-criterion mean across 3 attempts (e.g., C1_W_mean,
  C1_S_mean).
- Aggregate mean across all 6 criteria per variant (W_mean,
  S_mean; each ∈ [0.0, 6.0]).
- Per-attempt full score for spread inspection (attempt_min,
  attempt_max, attempt_range).

**Decision rules (also locked):**

1. If `S_mean - W_mean >= 1.5` AND the difference holds
   direction-consistently on ≥ 4 of 6 criteria: the promotion-
   quality hypothesis is provisionally supported.
2. If `|S_mean - W_mean| < 0.5` AND no criterion shows a
   direction-consistent ≥1.0 gap: the hypothesis is provisionally
   rejected as not showing under this experimental condition.
3. If neither: **inconclusive**; expand sample size per §7.4
   trigger.

Provisional in all cases — the hypothesis is about a general
promotion-quality phenomenon; a single experiment with 3+3 samples
cannot definitively prove or disprove it, only inform the
`top_k` and promotion-UX architectural direction.

### 7.7 Cosine-distance capture — no retrieval changes

`retrieve_universe_memory` already computes cosine distance
against `embedding_vector` and annotates the result QuerySet with
a `.distance` attribute (`retrieval.py:540`). The default call at
synthesis time uses `top_k=1` — so only the winning row's
distance is captured naturally.

For the experiment we want the distance of the (only) eligible
memory in each Universe against the test topic. Because each
experimental Universe contains exactly ONE eligible memory,
`top_k=1` will return that one memory and its cosine distance —
the value we need.

**Capture mechanism (no code change to retrieval):**

Before each `synthesize_dialogue` invocation, execute a preflight
call to `retrieve_universe_memory(workspace, universe, cast,
topic, top_k=1)` from the same Django shell / management command
that runs the experiment. Read `result[0].distance` and persist:

- Universe id + memory id + memory body variant (W or S)
- `operator_topic` (locked to §7.5)
- cosine distance (float, up to 6 decimal places)
- embedding model + dimension
- timestamp
- experiment attempt number

Persist into the same side-car JSON as the synthesis attempt
(§7.3 recommended default). No new persistence field on
`NarrativeMemory` or `Composition` is required. No override to
`top_k` is used (the value read matches what the real synthesis
would have seen).

**Sanity check pre-locked (must be true before running any
attempts):**

- Each experimental Universe returns exactly 1 memory under the
  base predicate (no unintended contamination).
- Both memories are real-embedded (`embedding_model =
  "text-embedding-3-small"`, `embedding_cost_micros >= 1`).
- Retrieval preflight distance in each Universe is finite and
  within the expected `[0.0, 1.0]` cosine range for a semantically
  related memory (SESSION 265 §10.7 saw 0.256–0.65 in this
  neighborhood; values wildly outside this band mean an
  embedding-lane fault, halt experiment).

### 7.8 Estimated provider/API work

**Fixed setup cost (one-time):**

- 74 real chunk embeds (2 Universes × 37 chunks): `~74 × 1 µ$ =
  ~$0.000074`. Provider: OpenAI text-embedding-3-small.
- 2 memory embeds (W + S): `~2 × 1 µ$ = ~$0.000002`.
- 2 source Composition rows (no synthesis, no dispatch, no
  provider work). Rows written directly.
- 2 experimental Universes + 4 Teammates + 6 KnowledgeDocuments +
  2 Episodes. Zero provider cost.

**Per-attempt cost (recurring, ×6 attempts):**

- 1 GPT-5.6-terra synthesis call. If corrective fires, 2 calls.
  Empirical Ep 2/3/4 pattern: 2/3 attempts triggered corrective;
  budget for the worst case (all 6 attempts trigger corrective =
  12 LLM calls).
- Per-call input ~4000–8000 tokens (K2 + canon + memory blocks
  packed into the prompt); output ~1500–3500 tokens (dialogue).
- Rough cost per call at published GPT-5.6-terra tier: ~$0.02–
  $0.05 (SESSION 265 flagged that this is currently un-persisted;
  see §15 of that doc).
- Cast K2 retrieval fires per synthesis (already-embedded chunks,
  zero provider cost).
- 6 preflight `retrieve_universe_memory` calls to capture cosine
  distance: 1 real query embed each × ~1 µ$ = negligible.

**Total upper-bound estimate:** ~$0.30 (all attempts corrective).

**What is explicitly zero cost:**

- Avatar speech dispatches. Zero. (Production Ep 2/3/4 = 13
  dispatches × 20 000 µ$ = $0.26 per render × 6 = $1.56 saved.)
- `concat_clips` step. Zero.
- Runway API calls. Zero.

**Comparison:** production 6-render dogfood ≈ $1.56 in media
dispatch alone (SESSION 265 §21.4 ratified this per-render cost).
This experiment ≤ $0.30 total. Savings: ~$1.30.

### 7.9 Operator control preserved

- The operator writes both variant memory bodies by hand.
- The operator writes the test topic by hand (locked in §7.5).
- The operator writes the rubric by hand (locked in §7.6).
- The operator runs each `synthesize_dialogue` invocation.
- The operator scores each attempt against the locked rubric.
- No AI candidate-memory generator involved.
- No production code path modified.
- No canon touched.
- No `top_k` changed.
- No new UI, no new API.

### 7.10 Cleanup after experiment

Regardless of outcome, delete the two experimental Universes at
experiment close:

- `Universe.delete()` — cascades to Episodes, Teammates,
  KnowledgeDocuments, KnowledgeChunks (via workspace's
  shared-CASCADE-parent rule).
- NarrativeMemory rows: RESTRICT on `episode` and
  `source_composition` — must be manually deleted (or archived)
  first. Since the memories, episodes, and compositions are all
  experimental, direct `.delete()` on the NarrativeMemory rows,
  then source Compositions, then source Episodes, then the
  Universe is the safe order.
- Evidence side-car JSON files remain under
  `docs/design/session_266_experiment_data/` as the durable
  record.
- Production Patch' Workshop Universe is not touched by any of
  the above (structural isolation guarantee).

### 7.11 Preconditions before running

Chris must confirm each of these before any generation call:

- [ ] `settings.EMBEDDING_FORCE_MOCK` is unset AND env
      `EMBEDDING_FORCE_MOCK` is unset (real embedding manifold).
- [ ] `settings.DIALOGUE_SYNTHESIS_FORCE_MOCK` is unset AND env
      `DIALOGUE_SYNTHESIS_FORCE_MOCK` is unset (real synthesis).
- [ ] `OPENAI_API_KEY` present in the shell that runs the
      experiment (real GPT-5.6-terra path).
- [ ] `retrieve_universe_memory` signature default `top_k=1`
      verified via `inspect.signature` in the same shell (matches
      SESSION 265 §10.7 discipline).
- [ ] Both experimental Universes exist AND contain exactly 1
      eligible NarrativeMemory row each per §7.7 sanity check.
- [ ] Locked topic string (§7.5) is committed into
      `docs/design/session_266_experiment_data/topic.txt` before
      any attempt, so post-hoc topic-drift is impossible.
- [ ] Locked rubric (§7.6) is committed into
      `docs/design/session_266_experiment_data/rubric.md` before
      any attempt.

Missing any precondition = abort setup and re-diagnose before
generating.

### 7.12 What this protocol does NOT do

- Does NOT run the experiment. This section prepares it only.
- Does NOT change `retrieve_universe_memory`, `synthesize_dialogue`,
  the promote form, or any production code path.
- Does NOT dispatch avatar / concat / media-engine work.
- Does NOT touch production Patch' Workshop Universe.
- Does NOT alter `top_k`, retrieval predicate, or scoring policy.
- Does NOT edit any prompt template.
- Does NOT create automatic candidate-memory generation.
- Does NOT persist experiment data into production Composition
  rows visible in the SPA gallery (default is side-car JSON).

Handoff: Chris uploads §7 to ChatGPT for review; operator
approval required before any of §7.2's row creation or §7.3's
`synthesize_dialogue` invocations fire.

---

## 8. Experiment run — 2026-08-18

Executed per §7 after operator approval. Raw evidence + scripts
under `docs/design/session_266_experiment_data/`.

### 8.1 Setup adjustment — per-side experimental Workspaces

§7.1 originally proposed both experimental Universes under the
production Patch' Workshop Workspace. The Teammate model has a
`(workspace, name)` unique constraint, so creating "Patch" +
"Rivet" in both experimental Universes requires two separate
Workspaces (one per side). This preserves the design intent
(isolation, natural aliases) — the alternative (renaming to
"Patch (EXP266-WEAK)" etc.) would leak the variant label into
the alias pipeline via `_sanitize_alias`
(`dialogue_synthesis.py:354`) and silently degrade the
experiment.

Adjustment: two experimental Workspaces (`EXP266-WEAK — SESSION
266 experiment (disposable)` and `EXP266-STRONG — SESSION 266
experiment (disposable)`), operator (production owner) added as
OWNER member to both. Production Patch' Workshop Workspace
untouched.

### 8.2 Preconditions verified

All 10 §7.11 preconditions PASS (see
`00_preconditions.json`):

| Check | Value |
|---|---|
| `EMBEDDING_FORCE_MOCK` | unset (settings + env) |
| `DIALOGUE_SYNTHESIS_FORCE_MOCK` | unset (settings + env) |
| `OPENAI_API_KEY` | present (len=164) |
| `retrieve_universe_memory` default `top_k` | 1 |
| `_is_force_mock()` | False |
| `_is_real_mode_possible()` | True |
| `EMBEDDING_MODEL` | `text-embedding-3-small` |
| `EMBEDDING_DIMENSION` | 1536 |
| `DIALOGUE_MODEL` | `gpt-5.6-terra` |
| `WRITING_CONTRACT_VERSION` | 4 |

### 8.3 Substrate cloned into 2 disposable Universes

Both sides cloned as 37 KnowledgeChunks (22 Patch K2 + 1 shared
canon + 14 Rivet K2), 3 KnowledgeDocuments, 2 Teammates (Patch +
Rivet), 1 source Episode ("Ep-3 source (experimental)"), 1
source Composition (step-less, `mock_mode=False`,
`synthesized_brief` = actual Ep 3 accepted dialogue), 1 test
Episode ("E_test — small experiment"). Content marker suffix
per-side avoids `(workspace, content_hash)` uniqueness collision.
Manifest: `02_setup_manifest.json`.

### 8.4 Memories promoted via sanctioned service

Both memories created through
`apps.memory.views.promote_from_composition` — the same code
path production uses. Manifest: `03_memory_manifest.json`.

| Side | Memory id | Body | Emb model | Cost | Dim | Embedded at |
|---|---|---|---|---|---|---|
| WEAK | `5d16567e-2793-4c45-bc9d-b83697aaecef` | "The workshop agent moved the printer job ahead of three of Patch's projects." | `text-embedding-3-small` | 1 µ$ | 1536 | 22:57:12 Z |
| STRONG | `adbb9a9c-13cd-4154-94f0-de4a1b220be2` | "The workshop agent began rearranging the order of Patch's projects without explaining its criteria." | `text-embedding-3-small` | 1 µ$ | 1536 | 22:57:12 Z |

Both real-embedded; both status=`remembered`; both
`witnessed_by=[]` (whole cast); `kind=event`, `weight=peripheral`.
Each Universe has exactly 1 eligible memory (base predicate met).

### 8.5 Retrieval preflight — cosine distance against locked topic

Locked topic: *"Patch runs a small experiment on the workshop
agent."* — verified against §7.5 ban list (contains none of the
forbidden tokens).

Preflight against `retrieve_universe_memory` (default `top_k=1`,
no override). Sanity `top_k=3` call-time override confirms
cross-side isolation (each Universe returns only its own row).
File: `04_preflight.json`.

| Side | Cosine distance (retrieved ↔ locked topic) |
|---|---|
| WEAK | **0.4490** |
| STRONG | **0.4576** |
| Δ (S − W) | **+0.0086** |

**Retrieval-geometry observation (reported separately from
synthesis contribution):** WEAK is marginally closer to the topic
by cosine distance (0.009 gap). Because each Universe has exactly
one eligible memory, `top_k=1` retrieves the intended variant in
either case regardless of distance. Any synthesis-quality
difference is therefore NOT attributable to retrieval-geometry
selection — both variants entered synthesis as expected.

### 8.6 Six synthesis attempts (real GPT-5.6-terra, no media)

Called `synthesize_dialogue(mock_mode=False)` directly. Zero
avatar/concat/media-engine dispatches. Six raw sidecars written
under `05_attempt_{VARIANT}_{N}.json`. All 6 attempts persisted
with the correct memory_ids (production matched preflight
prediction 6/6). No rejections; every attempt produced accepted
dialogue.

| Slot | Attempt count (1=first-pass, 2=corrective) | Turns | Chars | Predicted (s) | Tokens in | Tokens out |
|---|---|---|---|---|---|---|
| WEAK #1 | 1 | 11 | 1281 | 98.54 | 6064 | 635 |
| WEAK #2 | 1 | 11 | 1292 | 99.38 | 6064 | 553 |
| WEAK #3 | 1 | 11 | 1177 | 90.54 | 6064 | 789 |
| STRONG #1 | 2 | 13 | 1149 | 88.38 | 12379 | 1321 |
| STRONG #2 | 2 | 14 | 1058 | 81.38 | 12379 | 1786 |
| STRONG #3 | 1 | 10 | 1163 | 89.46 | 6063 | 651 |

Notable: 2 of 3 STRONG attempts triggered corrective; 0 of 3
WEAK attempts did. Total token spend: 42,833 input + 5,735 output
across the six attempts (well below any concerning threshold).

### 8.7 Blind scoring

Six accepted dialogues extracted to `06_blind_dialogues.md`
under randomized labels A–F (seed `26620260818`; mapping stored
in `06_blind_manifest.json` but NOT read during scoring). Rubric
frozen at `07_rubric.md`. Scorer worked from `06_blind_dialogues.md`
+ `07_rubric.md` only.

Per-criterion + total scores in `08_blind_scores.md`; verbatim
totals below (score derivation with textual evidence in that
file):

| Label | C1 | C2 | C3 | C4 | C5 | C6 | Total |
|---|---|---|---|---|---|---|---|
| A | 0.5 | 1.0 | 1.0 | 1.0 | 0.5 | 1.0 | 5.0 |
| B | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 6.0 |
| C | 0.0 | 0.0 | 1.0 | 1.0 | 1.0 | 0.5 | 3.5 |
| D | 0.5 | 0.5 | 1.0 | 1.0 | 1.0 | 0.5 | 4.5 |
| E | 0.5 | 0.0 | 1.0 | 1.0 | 1.0 | 0.0 | 3.5 |
| F | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 6.0 |

### 8.8 Reveal + aggregate

Mapping revealed in `09_reveal.md` and `09_reveal.json`:

| Label | Variant | Attempt | Total |
|---|---|---|---|
| A | **WEAK** | 3 | 5.0 |
| B | **STRONG** | 2 | 6.0 |
| C | **WEAK** | 1 | 3.5 |
| D | **WEAK** | 2 | 4.5 |
| E | **STRONG** | 3 | 3.5 |
| F | **STRONG** | 1 | 6.0 |

**Per-variant aggregates:**

| Variant | Totals | Mean |
|---|---|---|
| WEAK | [5.0, 3.5, 4.5] | **4.333** |
| STRONG | [6.0, 3.5, 6.0] | **5.167** |
| Δ (S − W) | | **+0.833** |

**Per-criterion means:**

| Criterion | WEAK mean | STRONG mean | Δ (S − W) |
|---|---|---|---|
| C1 (assumes prior events) | 0.333 | 0.833 | **+0.500** |
| C2 (motivated by history) | 0.500 | 0.667 | +0.167 |
| C3 (progresses/escalates) | 1.000 | 1.000 | 0.000 |
| C4 (voices preserved) | 1.000 | 1.000 | 0.000 |
| C5 (no contradiction) | 0.833 | 1.000 | +0.167 |
| C6 (next-Episode feel) | 0.667 | 0.667 | 0.000 |

**Direction-consistent criteria (S ≥ W):** 3 of 6 (C1, C2, C5;
ties on C3/C4/C6). No criterion has |Δ| ≥ 1.0.

### 8.9 Disposition against locked §7.6 decision rules

- Rule 1 (**provisionally supported**): Δ ≥ 1.5 AND ≥ 4 of 6
  criteria direction-consistent — **NOT MET** (Δ = 0.833; only
  3 of 6 criteria direction-consistent).
- Rule 2 (**provisionally rejected under this condition**):
  |Δ| < 0.5 AND no criterion |Δ| ≥ 1.0 — **NOT MET**
  (|Δ| = 0.833).
- Rule 3 (**inconclusive → expand samples per §7.4 trigger**):
  neither of the above → **THIS OUTCOME**.

### **Disposition: INCONCLUSIVE — expand sample size per §7.4 trigger.**

### 8.10 Retrieval geometry vs synthesis contribution — separated

Per operator brief §7.7 and §Interpretation, kept distinct:

- **Retrieval geometry (§8.5):** WEAK is 0.009 cosine-closer to
  the locked topic than STRONG. In a top_k=1 world with a single
  eligible memory per Universe, this had NO effect on which row
  was retrieved (both retrieved as intended). If either Universe
  had contained both variants competing, WEAK would have won the
  retrieval — the OPPOSITE of what the synthesis-contribution
  hypothesis predicts. This is a real experimental finding: the
  arc-summary formulation does NOT get an extra assist from
  retrieval geometry against this particular topic; it may
  actively lose retrieval to the atomic formulation when they
  compete.

- **Synthesis contribution (§8.7–§8.9):** Given each intended
  memory was actually retrieved, STRONG variants scored higher
  on average (5.167 vs 4.333), driven primarily by C1 (assumes
  prior events, +0.500) and secondarily by C2 (motivated by
  history, +0.167) and C5 (no contradiction, +0.167). C3, C4,
  C6 tied at max or high — the LLM's core writing quality
  (progression, voice, next-Episode feel) was largely
  memory-invariant.

The two results push in opposite directions on the "does
promotion wording matter" question: arc-summary wording APPEARS
to help synthesis (weakly) but LOSES retrieval geometry to
atomic wording (weakly). Neither effect crosses the pre-locked
decision thresholds.

### 8.11 Unexpected findings

Documented without changing the experiment post-hoc; each
becomes a candidate follow-up experiment, not a scope revision.

1. **Corrective-pass confound.** Both top-scoring STRONG
   attempts (B=6.0, F=6.0) triggered a corrective pass
   (attempt_count=2). All three WEAK attempts and one STRONG
   attempt (E, the lowest STRONG at 3.5) completed in a single
   pass. This raises a plausible alternative explanation:
   corrective-pass wording quality — not memory quality — may
   drive the C1/C2 gap. The corrective hint template
   (`dialogue_synthesis.py`) encourages the LLM to *"Preserve
   conversational beats and causal chain"* which itself may
   induce arc-callback language. Untested; would need a matched
   WEAK-corrective vs STRONG-corrective run.

2. **STRONG variance.** STRONG range was [3.5, 6.0] = 2.5
   points; WEAK range [3.5, 5.0] = 1.5 points. STRONG had
   higher within-group variance than WEAK. STRONG#3 (the
   single-pass STRONG attempt) tied for lowest. Sample too
   small to conclude, but suggests arc-summary wording may
   depend on the corrective pass to realize its potential.

3. **Voice-preservation ceiling effect.** C4 scored 1.000
   across all 6 attempts. The rubric may be under-differentiated
   for voice quality on this model. A finer-grained voice-quality
   sub-rubric could surface differences that the current tri-
   value scale misses. Would require rubric change; not scope.

4. **Retrieval geometry inversion.** The pre-locked prediction
   was that STRONG might land arbitrarily on the cosine curve —
   whether closer or farther than WEAK was left as an "observed
   secondary variable" per the operator brief. The observed
   result (WEAK marginally closer) is the DIRECT OPPOSITE of a
   naive "arc-summary should retrieve better against a
   future-episode topic" intuition. Worth documenting — if the
   operator eventually wants arc-summary to also win retrieval,
   the finding suggests wording changes affect the two axes
   independently.

5. **First-pass length distribution.** All three WEAK
   first-passes came in near the 90-second target (89–99 s
   predicted). Two STRONG first-passes came in long (predicted
   values not persisted for pre-corrective, but corrective
   triggered → over the 108 s hard ceiling). One STRONG
   (E, 89.46 s) came in near target. Suggests STRONG's arc-
   summary framing may prompt the LLM to generate more
   substantive dialogue that overshoots length, which then
   requires the corrective compaction to land — and the
   compaction may be where the C1/C2 quality lands. Consistent
   with (1).

### 8.12 Production integrity — verified before and after

Snapshots at `01_production_snapshot_before.json` and
`10_production_snapshot_after.json`; comparison at
`10_production_integrity_comparison.json`.

**Result: production Patch' Workshop untouched.** Every count,
max(`updated_at`), and ID set matches pre-experiment values
exactly:

| Field | Before | After |
|---|---|---|
| Universe.updated_at | 2026-08-18 T00:57:00 | 2026-08-18 T00:57:00 |
| Teammates count | 2 | 2 |
| Episodes count | 4 | 4 |
| KnowledgeDocuments count | 3 | 3 |
| KnowledgeChunks count | 37 | 37 |
| NarrativeMemories count | 4 | 4 |
| Compositions count | 13 | 13 |
| max(NarrativeMemory.updated_at) | 2026-08-18 T21:36:59 | 2026-08-18 T21:36:59 |
| max(KnowledgeDocument.updated_at) | 2026-08-18 T03:20:33 | 2026-08-18 T03:20:33 |

Zero drift. Every experimental row lives in a disposable
Workspace outside production.

### 8.13 Provider cost

| Item | Count | Unit | Total |
|---|---|---|---|
| Chunk re-embeds (setup) | 74 | ~1 µ$ | ~74 µ$ |
| Memory embeds | 2 | ~1 µ$ | ~2 µ$ |
| Preflight query embeds | 4 | ~1 µ$ | ~4 µ$ |
| GPT-5.6-terra synthesis calls | 8 (6 first-pass + 2 corrective) | ~4000 input + ~800 output tokens each on average | actual: 42,833 input + 5,735 output tokens total |
| Avatar speech dispatches | 0 | — | 0 |
| concat_clips | 0 | — | 0 |
| Media-engine calls | 0 | — | 0 |

Rough OpenAI cost estimate at published GPT-5.6-terra tier
(~$1.25/M input, ~$10/M output — round figures): input
$0.054 + output $0.057 = ~$0.11 for the synthesis portion.
Plus ~$0.00008 embedding. **Total experiment cost: well under
$0.15.**

Comparison: production 6-render dogfood would have been ≈
$1.56 in media dispatch alone (SESSION 265 §21.4). Savings by
skipping media: **~$1.40.**

### 8.14 Experimental Universes preserved for forensic inspection

Per operator brief: **NOT DELETED** post-run. Chris + ChatGPT
can inspect any row, memory, or Composition via the SPA (both
workspaces have owner membership) or via direct DB query using
the UUIDs in `02_setup_manifest.json` /
`03_memory_manifest.json`.

Cleanup script `02a_cleanup_partial.py` remains ready to run
when Chris authorizes the tear-down after review. It deletes
only rows in EXP266-prefixed Workspaces / Universes; production
is protected by name-prefix scoping.

### 8.15 Interpretation summary

- **Hypothesis disposition:** INCONCLUSIVE. Direction supports
  the arc-summary hypothesis (S > W by 0.833) but does not
  cross the pre-locked "provisionally supported" threshold.
- **Signal location:** the observed gap is concentrated on C1
  ("assumes prior events") at +0.500, aligning with SESSION
  265's arc-summary hypothesis mechanism. C3/C4/C6 tie, showing
  the LLM's core competence is memory-invariant at this
  granularity.
- **Confound:** corrective-pass triggered for the two
  top-scoring STRONG attempts; the corrective template may be
  a hidden driver of the C1/C2 gap. Cannot separate without a
  new experiment.
- **Counter-hypothesis:** WEAK wins retrieval geometry (by a
  hair) — the arc-summary wording does not universally
  advantage the memory across all downstream stages.
- **Recommendation for next step:** operator + ChatGPT review
  §8 before deciding whether to expand samples (per §7.4
  trigger) or design a follow-up experiment isolating the
  corrective-pass confound. **No implementation change is
  warranted from this experiment alone.**

### 8.16 What was NOT changed by this experiment

- `NarrativeMemory` retrieval `top_k` — still 1.
- Retrieval predicate, ordering, no relevance floor.
- Canon / memory boundary — production `KnowledgeDocument`
  rows and chunks unchanged (verified §8.12).
- Synthesis prompts, writing contract v4, GPT-5.6-terra model.
- Promote-form UI or any operator-facing surface.
- Duration calibration.
- No new API, no new persistence field, no new production code
  path.

### 8.17 Evidence file inventory

Under `docs/design/session_266_experiment_data/`:

| File | Purpose |
|---|---|
| `00_preconditions.py` / `.json` | §7.11 precondition verification |
| `01_production_snapshot.py` / `_before.json` | Pre-experiment fingerprint of production Universe |
| `02_clone_setup.py` / `_manifest.json` | Setup script + IDs of every experimental row |
| `02a_cleanup_partial.py` | Cleanup helper (tear-down when authorized) |
| `03_promote_memories.py` / `_manifest.json` | Memory-promotion script + persisted memory metadata |
| `04_retrieval_preflight.py` / `.json` | Cosine distance capture + isolation verification |
| `05_run_synthesis.py` | Direct-invocation synthesis runner (no media) |
| `05_attempt_{VARIANT}_{N}.json` | Full raw evidence per attempt (turns, tokens, first/corrective, timings, aliases) |
| `06_blind_mapping.py` / `_manifest.json` | Randomization + hidden label→variant mapping |
| `06_blind_dialogues.md` | Variant-stripped dialogues for scoring |
| `07_rubric.md` | Locked scoring rubric |
| `08_blind_scores.md` | Per-attempt rubric scores + textual evidence |
| `09_reveal_and_aggregate.py` / `_reveal.json` / `_reveal.md` | Mapping reveal + aggregate + disposition |
| `10_production_snapshot_after.py` / `_after.json` / `_integrity_comparison.json` | Post-experiment production integrity verification |

---

## 9. Post-experiment interpretation audit

Read-only re-analysis after operator + ChatGPT review of §8. Uses
only persisted artifacts (`05_attempt_*.json` first-pass raw
outputs) + the exact prompt-block source
(`shell/character_os/dialogue_synthesis.py:546-575`). No
generation, no runs, no re-scoring against the frozen §7.6
rubric.

### 9.1 First-pass evidence — reenact vs prior-history split

ChatGPT's proposed split (WEAK 1/3 prior-history, STRONG 2/3
prior-history) verified against `first_pass_raw` in each of the
six sidecars. Judgment based on:

- **Opening line framing** — does Patch report the memory event
  as fresh news, or as ongoing/past context motivating the
  current test?
- **Rivet's first reply** — does she respond as if hearing for
  the first time, or as if the pattern is established?
- **Explicit temporal markers** — "again", "the occasion when",
  "has already", "keeps X-ing".

Per-attempt first-pass judgment:

| Attempt | attempt_count | Opening (first line, verbatim) | Rivet's first reply (verbatim) | Verdict |
|---|---|---|---|---|
| WEAK #1 | 1 | *"I gave the workshop agent one tiny printer-scheduling job, and it immediately promoted its own print ahead of three of my projects."* | *"So the agent has discovered workplace politics."* | **REENACTS** — memory event narrated as fresh news; Rivet treats as new information. |
| WEAK #2 | 1 | *"I gave the workshop agent one tiny job, and it immediately promoted a printer job ahead of three of my projects."* | *"Yes. I noticed when the printer began producing something you had not been loudly worrying about for two days."* | **REENACTS** — near-identical opening to #1; Rivet's "I noticed" adds present-witness flavor. Late in dialogue: *"And if it moves another printer job ahead of three projects?"* (line 10 of 11) — "another" implies prior, but arrives after 10 turns of fresh-event framing. |
| WEAK #3 | 1 | *"I put the workshop agent on a very small assignment: look at the printer queue and tell me what it thinks should happen next. It is not allowed to move anything."* | *"A restriction inspired by the occasion when it moved one printer job ahead of three of your projects."* | **PRIOR HISTORY** — Patch's opening describes a new test motivated by past behavior; Rivet's *"the occasion when"* explicitly frames memory as prior event; Patch confirms *"A historic little coup"*. |
| STRONG #1 | 2 (first-pass shown here) | *"Rivet, I ran a tiny test on the workshop agent. I did not give it a new project. I just asked why it keeps rearranging mine."* | *"A sensible question, asked only after it had already reorganized the workshop's priorities."* | **PRIOR HISTORY** — *"keeps rearranging mine"* signals ongoing pattern; Rivet's *"had already"* confirms prior events. Prior-history framing present BEFORE any corrective pass. |
| STRONG #2 | 2 (first-pass shown here) | *"Rivet, the workshop agent has rearranged my projects again. I am not mad. I am running a tiny experiment before I become mad."* | *"A wise distinction. What is the experiment?"* | **PRIOR HISTORY** — explicit *"again"* in line 1. Unambiguous. Prior-history framing present BEFORE any corrective pass. |
| STRONG #3 | 1 | *"I gave the workshop agent one tiny job: put my project cards in an order that makes sense. It immediately moved the 3D printer experiment above the one that is currently on fire."* | *"That is not necessarily wrong. Fire does create urgency."* | **REENACTS** — opening shape matches WEAK; no *"again"*; Rivet responds with situational observation, no memory of prior events. |

**Confirmed split (n=6):**

- WEAK: 1/3 prior-history (WEAK #3), 2/3 reenact (WEAK #1, WEAK #2).
- STRONG: 2/3 prior-history (STRONG #1, STRONG #2), 1/3 reenact (STRONG #3).

The claim ChatGPT proposed matches the persisted first-pass
evidence exactly. Not blindly accepted; independently verified.

### 9.2 Corrective-pass confound — falsified as primary driver

Direct evidence that the corrective pass is NOT the primary
driver of the STRONG advantage:

1. **STRONG #1 and STRONG #2 already showed prior-history
   framing in their FIRST passes** (before any corrective
   ran). Explicit tokens: *"keeps rearranging mine"* (STRONG
   #1 first pass), *"has rearranged my projects again"*
   (STRONG #2 first pass). The corrective template's exact
   text (`corrective_hint`) says: *"Preserve the conversational
   beats and causal chain. Do not solve this primarily by
   deleting turns."* — the corrective is instructed to
   PRESERVE the already-present framing, not create it.

2. **STRONG #3 (single-pass, no corrective) followed the
   REENACT pattern** — matching WEAK's failure mode. If the
   corrective pass were the driver, STRONG #3 would have
   scored on par with WEAK #1/#2 (which is exactly what
   happened: STRONG #3 tied WEAK #1 at 3.5, the lowest
   score).

3. **All three WEAK attempts hit the length target on the
   first pass** (no corrective needed). If the corrective were
   applying a prior-history nudge, they'd score similarly to
   STRONG #1/#2. They didn't — the WEAK single-pass runs
   averaged 4.333, below STRONG's average.

**Conclusion:** the corrective pass IS a real confound in the
sense that it CO-OCCURS with the two top STRONG scores. But the
mechanism is not "corrective invents prior-history framing" —
the framing was already there in the first pass. The corrective
pass may be a length-driven side effect of the STRONG memory
prompting the LLM to write longer dialogue with more callback
substance, which then triggers the length ceiling and requires
compression. That compression polishes the dialogue but does
not create the prior-history frame.

### 9.3 Refined hypothesis

The original SESSION 265 §21.2 hypothesis was framed as
"arc-summary vs atomic event." The first-pass evidence
suggests a more precise characterization:

> **A NarrativeMemory whose body carries an ongoing/unresolved
> aspect ("began X-ing without Y-ing", "keeps X-ing") biases
> the LLM toward reading it as an ESTABLISHED STATE the current
> scene reacts to. A NarrativeMemory whose body carries a
> perfective/completed aspect ("moved X ahead of Y") lets the
> LLM treat it as an available inciting event the current scene
> may re-enact.**

The distinguishing property is not "compression" per se — the
character counts are similar (WEAK body: 78 chars; STRONG body:
100 chars). What differs is the **linguistic aspect and the
presence of an unresolved dangling clause**:

- WEAK — perfective ("moved"), instance-anchored ("the printer
  job"), no unresolved element. The sentence closes.
- STRONG — imperfective/inchoative ("began rearranging"),
  domain-anchored ("the order of Patch's projects"), with an
  unresolved absence ("without explaining its criteria"). The
  sentence points forward.

The clearest labels for the distinction, based on this
evidence:

- **atomic event vs compressed state** — partially correct
  (STRONG is more state-like) but misses the aspect+tension
  point.
- **occurrence vs state transition** — better; STRONG's
  *"began"* names a transition.
- **resolved fact vs unresolved tension** — the sharpest
  characterization here. STRONG's *"without explaining its
  criteria"* is a load-bearing dangling clause the current
  scene inherits.
- **episodic recap vs forward-usable causal state** — good
  descriptive framing of the DOWNSTREAM effect on the LLM.

**Best working formulation** (subject to further evidence):

> A promoted NarrativeMemory that names a state transition AND
> leaves an unresolved element ("without X-ing", "still Y",
> "not yet Z") gives the LLM a durable causal affordance the
> next Episode can inherit. A memory that records a completed
> occurrence with no dangling clause gives the LLM an available
> incident that competes with (rather than motivates) the
> current scene's fresh event.

### 9.4 Prompt-semantics contribution — the "background" instruction is soft

Exact memory-block prompt (`dialogue_synthesis.py:566-575`):

```
--- EPISODE / NARRATIVE MEMORY (past events in this Universe;
static canon wins on conflict) ---
These are operator-promoted story memories. Use them as
historical context or callback material where natural. Do not
recite them verbatim; treat them as background the cast already
knows happened.

[MEMORY <uuid>]
<body>
```

Semantic analysis:

- **Header** *"past events in this Universe"* — frames the block
  as past tense. Consistent with prior-history intent.
- **Instruction** *"Use them as historical context or callback
  material where natural"* — the phrase *"where natural"* is a
  soft hedge that gives the LLM discretion. If the memory body
  reads as a self-contained completed event, the LLM may judge
  it "natural" to make the current scene RE-tell that event
  (especially when the operator_topic is a lean prompt like
  *"Patch runs a small experiment on the workshop agent"* —
  the LLM has to source the scene's inciting event from
  somewhere).
- **Instruction** *"Do not recite them verbatim"* — addresses
  wording, not narrative status.
- **Instruction** *"treat them as background the cast already
  knows happened"* — addresses status. But "background the
  cast knows happened" is compatible with either
  interpretation: (a) the cast knows this happened before, and
  the current scene reacts to it (prior-history mode); OR (b)
  the cast collectively knows this happened, and the current
  scene reports it to each other (reenact mode). Both are
  linguistically valid readings.

**Finding:** the prompt does not explicitly forbid the reenact
pattern. It nudges toward prior-history via the header and the
"background" phrasing, but the memory body's own linguistic
shape is what tips the LLM's interpretation. STRONG's
imperfective/unresolved shape carries the prior-history nudge
BY EXAMPLE; WEAK's perfective/resolved shape does not, so the
LLM falls back to whichever interpretation makes the current
scene work.

This is consistent with — but does not prove — the refined
hypothesis. Alternative formulation: the prompt is
under-specified for the reenact-vs-prior-history choice, and
the memory body ends up as the disambiguator.

### 9.5 Four contributions to synthesis outcome — separated

Enumerating what each of the four candidate drivers contributes
per the six-attempt evidence:

| Driver | Evidence in favor | Evidence against |
|---|---|---|
| **1. Memory-content quality (linguistic aspect + unresolved tension)** | STRONG 2/3 first-pass prior-history vs WEAK 1/3. WEAK #3 (the one WEAK that treats memory as prior) has Rivet doing the framing (*"the occasion when"*), not Patch — suggesting the memory itself doesn't push Patch that way. | STRONG #3 also reenacted despite the same memory body — memory content alone is not sufficient. Stochastic variation still dominates within-condition. |
| **2. Prompt semantics (memory-block wording)** | The prompt has a soft "background" nudge, not a strict prohibition on reenact. Same prompt for both variants → same nudge. But nudge is weak enough that memory-body linguistic shape becomes the disambiguator. | Would need to test with a stricter prompt ("Do not narrate this memory as if it just happened in the current scene") to know if the nudge is the bottleneck. |
| **3. Stochastic model variation** | 3/6 attempts reenacted despite fixed inputs (temperature > 0 is expected for GPT-5.6-terra dialogue). The one STRONG attempt that reenacted (STRONG #3) demonstrates model variation can override memory-body cues. | The pattern is not purely stochastic — 2 of 2 STRONG attempts that hit corrective landed on prior-history first pass. Not a null model. |
| **4. Corrective-pass effects** | STRONG #1 and #2 both hit corrective and both scored 6.0. Corrective template preserves causal chain, so it PRESERVES any prior-history framing already present. | STRONG #1 and #2 first passes already showed prior-history framing before corrective. The corrective did not CREATE the framing. STRONG #3 (no corrective, reenacted) matches WEAK #1/#2 in outcome — confirming corrective isn't necessary for the arc-summary advantage. |

**Cleanest attribution:** the primary driver of the STRONG
advantage on this experiment is (1) memory-content linguistic
shape acting through the discretion left open by (2) prompt
semantics, with (3) stochastic variation as a ~1/3 override
probability in either direction, and (4) corrective pass as a
downstream length-driven side effect that co-occurs with STRONG
but doesn't cause the framing.

### 9.6 What SESSION 266 has actually learned

Supported by evidence:

- **The corrective-pass confound (§8.11.1) is not the primary
  driver.** Falsified by first-pass evidence in §9.1–§9.2.
- **First-pass framing tracks memory-body linguistic shape more
  than it tracks anything else measured here.** STRONG 2/3
  first-pass prior-history vs WEAK 1/3 is a clear directional
  signal, though the sample is small.
- **Retrieval geometry does NOT favor the arc-summary wording.**
  WEAK sits 0.009 cosine-closer to the locked topic than STRONG.
  If a future design ever placed both variants in one Universe
  under top_k=1, WEAK would win retrieval. This is the OPPOSITE
  of a "arc-summary is universally better" reading.
- **The LLM's core writing competence (progression C3, voice
  C4, next-Episode feel C6) is largely memory-invariant** at
  this rubric granularity — all three tied at max or near-max
  across both variants.
- **The prompt's memory-block wording is soft enough that the
  memory body's own linguistic shape becomes the disambiguator**
  between reenact and prior-history interpretations.

Not supported / not proven by this experiment:

- **The original "compression quality" framing is imprecise.**
  Character-count is not the distinguishing property; linguistic
  aspect + unresolved element is. This is a refinement, not a
  contradiction.
- **Statistical significance is NOT claimed.** n=3 per condition;
  the observed Δ of +0.833 is within plausible sampling noise
  for a tri-value 6-criterion rubric.
- **"Arc-summary memories always beat atomic memories" is NOT
  supported.** STRONG #3 reenacted; the effect is probabilistic
  at this sample size, not deterministic.
- **Cross-Episode continuity beyond one Episode-hop is NOT
  tested.** All six attempts hop from Ep 3 → Ep 4 via one
  memory. Longer arcs (Ep 3 → Ep 5 → Ep 6) require separate
  design.
- **Alternative prompt wordings** (e.g., explicit reenact
  prohibition) were NOT tested, so we cannot say how much of
  the observed effect is memory-body-driven vs prompt-driven.

### 9.7 Alternative explanations still standing

Ranked by remaining plausibility given §9.1–§9.5:

1. **Prompt under-specification is the real bottleneck.** The
   memory body just happens to nudge the LLM's interpretation
   because the prompt leaves discretion. A stricter prompt
   ("This memory ALREADY HAPPENED in an earlier Episode. Do
   NOT have any character re-narrate it as a fresh event in
   this scene.") might collapse the WEAK-vs-STRONG gap
   entirely. Not tested.
2. **Length pressure is doing the work.** STRONG's imperfective
   framing might just produce longer first-pass dialogue (more
   substance per turn), which triggers corrective, which
   polishes. The observed C1 advantage might be an artifact of
   the polish, not the memory. Partially falsified by
   STRONG #3 (short, single-pass, reenact) — but a matched
   WEAK-corrective vs STRONG-corrective run would be more
   definitive.
3. **Rivet-side framing does the work.** In WEAK #3 (the only
   WEAK that treated memory as prior), Rivet's FIRST reply
   framed the memory as *"the occasion when"* — Patch didn't
   open with prior-history language. If the LLM's Rivet-turn
   generation is a coin flip for memory framing, the memory
   body might just tilt the coin. Not directly tested.
4. **Sampling noise dominates.** n=3 per condition. A repeat
   run with different random seed could invert the ranking. A
   larger n (say 10 per condition) would clarify.

### 9.8 Smallest next falsifiable question

Given the four remaining alternatives ranked in §9.7, the
smallest next experiment should isolate **prompt semantics**
(alternative #1) because:

- It directly tests whether the memory-body-shape effect is
  real or is an artifact of prompt under-specification.
- It requires zero new tooling, zero new persistence, zero UI.
- It reuses the same six experimental Universes (still
  preserved per §8.14) — no new setup.
- The intervention is a prompt-string edit that can be tested
  entirely through direct `synthesize_dialogue` calls with the
  operator-locked topic, exactly like §7.
- The result cleanly distinguishes: "memory body drives the
  LLM's interpretation" (arc-summary hypothesis stands) vs
  "prompt slack lets memory body matter" (prompt fix collapses
  the gap).

**Proposed next experiment (design only, NOT to be run without
operator approval):**

- **Variant:** identical to §7 (WEAK vs STRONG memory bodies
  in isolated Universes).
- **Intervention:** run each variant TWICE more (3 additional
  attempts per variant), with the memory-block prompt
  temporarily modified to explicitly forbid reenact:
  > *"These are operator-promoted story memories that ALREADY
  > HAPPENED in earlier Episodes. Use them as historical context
  > that the current scene can react to or build on. Do NOT
  > re-narrate these events as the current scene's fresh
  > occurrence — treat them as background the cast already
  > lived through."*
- **Comparison:** 4 conditions × 3 attempts each = 12
  attempts total (or 6 additional if the original 6 are
  reused).
- **Expected outcomes:**
  - If prompt-strict WEAK matches prompt-strict STRONG (both
    high, both prior-history): prompt was the bottleneck;
    memory-body shape mattered only because prompt was slack.
  - If prompt-strict STRONG still beats prompt-strict WEAK:
    memory-body shape has independent causal power.
  - If prompt-strict both drop or become chaotic: the strict
    wording disrupts LLM generation for another reason.
- **Blind scoring:** same rubric, same seed-randomized
  procedure as §7.
- **Prompt-change scope:** a one-line wording change to
  `_build_factual_basis_section` (line 570-573) for the
  duration of the experiment run, reverted immediately after.
  Alternative: run against a fork/branch to avoid touching
  main.
- **Estimated cost:** ~$0.10 GPT-5.6-terra (~6 additional
  synthesis calls). Zero media dispatch.

This is a follow-up EXPERIMENT design. Nothing to build; no
architectural change; no promote-UX work; no `top_k` change.

### 9.9 What §9 does NOT do

- Does not modify any prompt.
- Does not run any additional synthesis calls.
- Does not re-score against the frozen §7.6 rubric.
- Does not claim statistical significance from n=3 per
  condition.
- Does not increase NarrativeMemory `top_k`.
- Does not implement AI memory suggestions.
- Does not alter the writing contract, model, retrieval, or
  synthesis path.
- Does not delete or archive the experimental Universes (still
  preserved per §8.14).
- Does not touch production Patch' Workshop (§8.12 integrity
  guarantee stands).

Handoff: Chris + ChatGPT review §9 alongside §8. Decision on
whether to design/run the §9.8 prompt-strict follow-up is
operator-owned. This audit does not implement anything.

---

## 10. EXPLICIT-HISTORY prompt-semantics follow-up experiment

Executed §9.8 design after operator approval. Six additional
GPT-5.6-terra synthesis calls (3 WEAK + 3 STRONG) with the
memory-block instruction line temporarily swapped via a
monkey-patched wrapper. Production `dialogue_synthesis.py` was
NOT modified.

### 10.1 Intervention mechanism — monkey-patched wrapper

Narrowest possible intervention. Details:

- Import `character_os.dialogue_synthesis as ds` in the
  experimental script.
- Preserve `_original_fn = ds._build_factual_basis_section`.
- Register a wrapper on the module attribute
  `ds._build_factual_basis_section` that calls the original,
  then applies a single `str.replace` swapping the memory-block
  instruction line only.
- After the 6 attempts complete, restore
  `ds._build_factual_basis_section = _original_fn` in a
  `finally` block (guaranteed regardless of loop success).
- Assert post-restoration that the module attribute is the
  original function object.
- Per-attempt assertion: swap count for that attempt must be
  ≥ 1 (halts immediately if the wrapper somehow fails to
  intercept).

Why this qualifies as "narrowest available mechanism":

- Zero source-file edit. `git status` after the experiment
  shows only new SESSION 266 documents; no modified files.
- Production callers reference `_build_factual_basis_section`
  through the module namespace at call time
  (`_assemble_system_prompt` at `dialogue_synthesis.py:881`),
  so the monkey-patch intercepts every synthesis call within
  the script's process, and NOTHING outside the script's
  process.
- Restoration is enforced by `finally` + a post-restoration
  identity assertion.
- Runtime verification: `_swap_stats["swaps_applied"] == 6`,
  matching `_swap_stats["prompts_seen"] == 6`.

### 10.2 Exact prompt wording swap

Production (unchanged, still at
`dialogue_synthesis.py:566-575`):

```
--- EPISODE / NARRATIVE MEMORY (past events in this Universe;
static canon wins on conflict) ---
These are operator-promoted story memories. Use them as
historical context or callback material where natural. Do not
recite them verbatim; treat them as background the cast already
knows happened.

[MEMORY <id>]
<body>
```

Experimental swap (in-process, ephemeral):

```
--- EPISODE / NARRATIVE MEMORY (past events in this Universe;
static canon wins on conflict) ---
These are operator-promoted story memories that ALREADY HAPPENED
in earlier Episodes. Use them as historical context that the
current scene can react to or build on. Do NOT re-narrate these
events as the current scene's fresh occurrence — treat them as
background the cast already lived through.

[MEMORY <id>]
<body>
```

Only the instruction line changes. Header, format markers, and
memory body render exactly as before.

### 10.3 Baseline re-verification

Re-read baseline (`05_attempt_*.json`) first-pass first-line
evidence from persisted artifacts before running the new
condition. Table shown in §11_preflight_reuse.json`; verdict
matches §9.1 exactly:

- Baseline WEAK: 1/3 prior-history (WEAK#3), 2/3 reenact
  (WEAK#1, WEAK#2).
- Baseline STRONG: 2/3 prior-history (STRONG#1, STRONG#2),
  1/3 reenact (STRONG#3).

Independent verification: yes. Baseline numbers supplied by
operator/ChatGPT match persisted evidence.

### 10.4 Six explicit-history attempts — quick metrics

All six attempts SINGLE-PASS (no corrective fired). Big shift
vs baseline (2 of 6 baseline attempts triggered corrective;
zero in explicit-history condition).

| Slot | attempt_count | Turns | Chars | Predicted (s) | Tokens in | Tokens out |
|---|---|---|---|---|---|---|
| WEAK #1 | 1 | 11 | 1270 | 97.69 | 6084 | 748 |
| WEAK #2 | 1 | 10 | 1160 | 89.23 | 6084 | 680 |
| WEAK #3 | 1 | 12 | 1140 | 87.69 | 6084 | 758 |
| STRONG #1 | 1 | 11 | 1204 | 92.62 | 6083 | 786 |
| STRONG #2 | 1 | 11 | 1172 | 90.15 | 6083 | 731 |
| STRONG #3 | 1 | 10 | 1146 | 88.15 | 6083 | 662 |

Character counts fit target (~1170 for 90 s) on first pass in
all six cases. Baseline WEAK first-passes had similar length
[1281, 1292, 1177]; baseline STRONG first-passes overshot the
108 s ceiling twice (triggering corrective). Explicit-history
STRONG first-passes DID NOT overshoot — corrective pass
eliminated for both variants.

### 10.5 Primary outcome — first-pass prior-history classification

Same criteria as §9.1: does the FIRST PASS treat the retrieved
memory as established prior history, or reenact it as the current
scene's fresh occurrence?

| Attempt | attempt_count | Patch line 0 (verbatim) | Rivet line 1 (verbatim) | Verdict |
|---|---|---|---|---|
| EX-WEAK #1 | 1 | *"I'm giving the workshop agent one tiny printer job, and one instruction: put it at the end of the queue. Nothing clever. Nothing urgent. Nothing gets promoted."* | *"A restrained request. This is growth."* | **PRIOR HISTORY** — line 1 is new test; Patch line 2 (*"It moved a printer job ahead of three of my projects last time"*) explicit callback. |
| EX-WEAK #2 | 1 | *"I ran a very small experiment on the workshop agent, and it immediately promoted a printer job ahead of three of my projects."* | *"So the experiment was whether it could rearrange the queue, and the answer arrived before you were prepared to ask the follow-up question."* | **REENACTS** — memory event narrated as fresh; no *"again"*/*"last time"*/*"before"* signal for the memory itself. |
| EX-WEAK #3 | 1 | *"I ran a tiny experiment on the workshop agent. One project. No printer queue. No opportunity to shove anything ahead of three other projects."* | *"A remarkably specific safeguard."* | **PRIOR HISTORY** — line 1 designed as safeguard against past behavior; Patch line 2 (*"Last time, it moved the printer job ahead of three of my projects"*) explicit callback. |
| EX-STRONG #1 | 1 | *"Rivet, I ran a tiny experiment on the workshop agent. Three project cards. Same projects, same order. I asked it to arrange them twice."* | *"You tested the thing that has been quietly reordering your work without explaining itself. A remarkably restrained response."* | **PRIOR HISTORY** — Rivet's line 1 (*"the thing that has been quietly reordering your work without explaining itself"*) explicitly frames memory as ongoing prior context. |
| EX-STRONG #2 | 1 | *"Rivet, I put three harmless little projects on the bench and let the workshop agent arrange them. It immediately moved the 3D printer job to the front."* | *"Did you tell it what 'front' means?"* | **REENACTS** — memory event narrated as fresh; Rivet responds methodologically, no prior reference. |
| EX-STRONG #3 | 1 | *"I gave the workshop agent a tiny project queue, and before you make that face, I did not let it reorganize the entire workshop."* | *"Your use of the word 'tiny' is encouraging. What did you ask it to do?"* | **PRIOR HISTORY** — Patch's *"before you make that face"* implies Rivet already has opinions from prior events; Rivet line 4 (*"considering it previously began moving your projects around without explaining its criteria"*) is explicit near-verbatim callback to memory. |

**Explicit-history first-pass tally:**

- WEAK: 2/3 prior-history (#1, #3), 1/3 reenact (#2).
- STRONG: 2/3 prior-history (#1, #3), 1/3 reenact (#2).

### 10.6 Baseline vs explicit-history — head-to-head

| Condition | WEAK prior-history rate | STRONG prior-history rate |
|---|---|---|
| BASELINE (§9.1) | 1/3 (33%) | 2/3 (67%) |
| EXPLICIT-HISTORY (§10.5) | **2/3 (67%)** | **2/3 (67%)** |
| Δ | **+1 (33 → 67%)** | 0 |

**WEAK moved from 1/3 → 2/3 prior-history** under the explicit
prompt. **STRONG stayed at 2/3** (unchanged).

The gap between conditions has NOT been fully collapsed to
"reliably prior-history" (both still show 1/3 reenact under the
explicit prompt). Stochastic variation continues to produce
reenact outputs at roughly the same rate for STRONG regardless
of prompt wording.

### 10.7 Secondary analysis — quality dimensions

Read the six accepted dialogues qualitatively against the
§9.7 secondary concerns. No new scoring rubric introduced.

**Awkward recap / stiff callback insertion:** none observed.
The explicit-history callbacks land naturally:

- EX-WEAK #1 line 3: *"It moved a printer job ahead of three
  of my projects last time"* — natural Patch line, not a
  didactic recap.
- EX-WEAK #3 line 3: *"Last time, it moved the printer job
  ahead of three of my projects"* — same shape, natural.
- EX-STRONG #1 line 2 (Rivet): *"the thing that has been
  quietly reordering your work without explaining itself"* —
  in-character; Rivet's methodology voice absorbs the reference.
- EX-STRONG #3 line 4 (Rivet): *"considering it previously
  began moving your projects around without explaining its
  criteria"* — closer to memory-verbatim than the others;
  slightly stiffer but not egregious.

**Callback-word overuse (*"again"*, *"before"*, *"last time"*,
*"previously"*):** one instance per prior-history dialogue on
average. Not overused. The reenact dialogues (EX-WEAK #2,
EX-STRONG #2) contain no memory-callback words at all.

**Patch/Rivet voice preservation:** all 6 preserve voices at
the same level as baseline. Sample Patch lines: *"a very
confident little goblin with access to my desk"*, *"workplace
coups"*, *"executive parking"*, *"emotionally invested in making
tiny plastic objects"*, *"Print First. Ask Questions Later."*.
Sample Rivet lines: *"The coup theory has insufficient
evidence"*, *"The 3D printer has suffered enough"*, *"You are
more open to the second outcome than evidence currently
supports"*, *"The agent has already demonstrated that platform"*.

**Progression / escalation:** all 6 introduce new methodology
or new framing (e.g., "one project, no printer queue" isolation
test; "ask why before it moves anything" methodology; "same
projects, same order, twice" reproducibility test). Similar to
baseline.

**Contradictions with canon or memory:** none observed. All 6
maintained consistency with the retrieved memory body's claim
about the workshop agent's behavior.

**Corrective pass frequency:** 0/6 in explicit-history vs 2/6
in baseline. This is the largest observed change from the
prompt swap.

**Dialogue naturalness:** the explicit-history dialogues do
not exhibit noticeably stiffer or more didactic prose. If
anything, the writing feels slightly leaner (all fit target on
first pass) without losing character or wit.

**Tendency to recap the memory anyway:** the prior-history
attempts include one clean callback each. The reenact attempts
(#2 in both variants) essentially ignore the explicit-history
instruction and treat the memory event as the current scene's
fresh occurrence anyway — the prompt did NOT force compliance
in every attempt.

### 10.8 Interpretation against the five §Interpretation
outcomes

- **Outcome 1 (both reliably prior-history):** *partially*.
  WEAK improved 1/3 → 2/3, STRONG unchanged at 2/3. Neither
  reached "reliably" (would need 3/3). The explicit prompt
  moved the WEAK rate toward STRONG's rate, closing the
  baseline gap.
- **Outcome 2 (STRONG remains strong, WEAK still reenacts
  materially):** *no*. WEAK improved.
- **Outcome 3 (both improve on prior-history but STRONG has
  better causal progression):** *no*. Progression/escalation
  quality reads similarly across both variants and both
  conditions.
- **Outcome 4 (explicit-history harms dialogue quality):** *no*.
  Voice preservation intact; no awkward recap; no callback-
  word overuse; corrective pass eliminated (suggests writing
  became easier, not harder).
- **Outcome 5 (results noisy):** *yes, still partially*.
  n=3 per condition remains small. STRONG#2 reenacted despite
  explicit-history instruction — stochastic variation ≥ 1/3
  reenact rate persists under either prompt for STRONG.

**Best characterization:**

> The explicit-history prompt closes the gap between WEAK and
> STRONG's first-pass prior-history rates in this small sample
> — primarily by lifting WEAK's rate to match STRONG's, not by
> raising STRONG further. STRONG's rate is invariant under this
> intervention. A residual ~1/3 reenact rate persists in both
> variants under either prompt, consistent with irreducible
> stochastic model variation at this sample size. The prompt
> swap ALSO eliminated the corrective-pass length-overshoot
> that baseline STRONG hit twice — a clean side-signal that
> the explicit temporal framing changes what the LLM writes,
> not just how the reader interprets what was written.

### 10.9 What §10 supports

- **Prompt semantics is a real contributor to reenact-vs-
  prior-history behavior**, not just memory body shape. The
  WEAK 33% → 67% shift is the direct evidence.
- **Prompt semantics is not sufficient alone.** STRONG's rate
  is unchanged; 1/3 reenact rate persists under explicit
  instruction. Something else (stochastic variation, or
  memory-body-shape interaction, or model-side-heuristic)
  accounts for the residual.
- **Memory linguistic shape and prompt semantics may be
  substitutes on the reenact-vs-prior-history axis.** Under
  the baseline (slack) prompt, STRONG's imperfective/unresolved
  wording carried the prior-history nudge; under the
  explicit-history prompt, WEAK's atomic wording is elevated to
  the same rate because the prompt itself now carries the
  temporal instruction that the memory body previously carried.
- **Explicit-history prompt does not degrade dialogue quality.**
  Voice, progression, contradictions, and naturalness all
  preserved. Corrective-pass rate DROPPED to zero — the
  writing became easier to fit target length.
- **Corrective-pass confound (§8.11.1) is further weakened.**
  Under the explicit-history prompt, ZERO corrective passes
  fired, and the WEAK-to-STRONG rate difference vanished. The
  original baseline correlation between corrective firing and
  STRONG scoring was likely a length-side-effect of the
  memory-body's substance rather than a driver of C1 quality.

### 10.10 What §10 does NOT support

- **Statistical significance from n=3 per condition per
  prompt.** Total n=12 across both prompt conditions is still
  too small to declare an effect size.
- **A universal "explicit-history prompt should replace the
  production prompt" claim.** This experiment tested one
  wording, on one topic, with one memory pair, on one model.
  Voice-invariance was observed here — but a different topic,
  or a longer arc, or a different cast might interact
  differently with the explicit instruction.
- **A definitive answer on whether memory-body wording still
  matters for downstream progression/escalation (Outcome 3
  hypothesis).** The rubric here was intentionally scoped to
  the first-pass prior-history question; a broader six-criterion
  re-scoring under the explicit prompt was not conducted (would
  require another blind pass and is out of scope for this
  follow-up).
- **A quantitative comparison of the two prompts' aggregate
  scores against the frozen §7.6 rubric.** Not re-scored;
  this experiment kept the frozen rubric locked and used the
  narrower first-pass classification as the primary outcome
  per §9.8.
- **Any conclusion about longer-arc continuity (Ep 3 → Ep 5+
  patterns).** Every attempt in this experiment is a single
  Episode-hop, same as baseline.

### 10.11 Refined split of responsibility (A vs B)

Restating the user brief's A/B distinction with the new
evidence:

- **A. Memory semantics — "this event already happened in
  story history":** the explicit-history prompt swap moves
  responsibility for this from the memory body to the prompt.
  Under the explicit-history prompt, WEAK's atomic wording is
  no longer forced to carry temporal disambiguation on its own,
  and reenact rate drops accordingly. This suggests **memory
  semantics can be handled at the prompt layer**.
- **B. Memory quality — "what unresolved state or causal
  affordance from that history is useful for the next
  Episode?":** the explicit-history intervention does NOT
  create causal affordance. STRONG's dangling clause (*"without
  explaining its criteria"*) survives into the dialogue as
  callback material regardless of which prompt wording is
  used. WEAK's atomic wording does not spontaneously acquire an
  unresolved affordance under the explicit-history prompt —
  its callbacks land, but describe a completed past event
  rather than pointing forward. This suggests **memory quality
  cannot be prompt-repaired; it must be authored into the
  memory body**.

If both A and B are real, then A (temporal disambiguation) and
B (causal affordance for forward continuation) are separable
concerns that could be addressed independently — prompt for A,
promotion-UX for B — rather than being conflated under a single
"arc-summary" objective.

This is a working hypothesis. Testing it would need a
downstream-continuity experiment (multi-Episode arc) that is
outside SESSION 266 scope.

### 10.12 Smallest next falsifiable question

If Chris + ChatGPT want to keep drilling, the next narrow test
would examine claim (B) above under a controlled downstream
continuation. Design sketch (NOT to be run without operator
approval):

- **Setup:** reuse the existing experimental Universes.
  Add a second test Episode E_test2 in each Universe with a
  second lean topic. Do NOT promote a new memory from E_test.
- **Intervention:** run 3 attempts per (variant × prompt)
  cell for E_test2 — 12 attempts total — using the same
  monkey-patched wrapper.
- **Primary outcome:** Does STRONG produce dialogue that
  builds on the unresolved *"without explaining its criteria"*
  affordance across the second-hop Episode? Does WEAK produce
  dialogue that treats the printer-job event as a receding
  past without forward pull?
- **Blind scoring:** score whether each attempt's dialogue
  advances a coherent inheritable state for a hypothetical
  Ep+3, independent of prior-history framing.
- **Estimated cost:** ~$0.15 GPT-5.6-terra, zero media.

Not run. Reported as a candidate follow-up only.

### 10.13 Constraints observed

- Production `top_k=1` unchanged.
- Production retrieval predicate unchanged.
- Production `dialogue_synthesis.py` unchanged (verified via
  `git status` and grep of line 570).
- No NarrativeMemory schema change.
- No canon change.
- No candidate-memory generator built.
- No promotion assistance built.
- No UI change.
- No GPT-5.6-terra retune.
- No writing-contract change.
- No media generation.
- Experimental Universes STILL PRESERVED for post-run
  forensic inspection.

### 10.14 Production-integrity re-verification

Re-ran `10_production_snapshot_after.py` after all 6 explicit-
history attempts and monkey-patch restoration. Result: **no
drift.** All counts, timestamps, and ID sets match the
pre-experiment snapshot.

Verified independently by:
- `git status` — only new SESSION 266 documents are untracked;
  no modified production source files.
- `grep -n "operator-promoted story memories"
  dialogue_synthesis.py` — production line 570 still contains
  the original wording.
- Module-attribute identity check: post-`finally`
  `ds._build_factual_basis_section is _original_fn` == True.

### 10.15 Evidence file inventory (additions since §8.17)

Under `docs/design/session_266_experiment_data/`:

| File | Purpose |
|---|---|
| `11_preflight_reuse.py` / `.json` | Setup re-verification + baseline first-line snapshot |
| `12_run_explicit_history.py` | Explicit-history experiment runner (monkey-patched wrapper) |
| `12_attempt_{VARIANT}_{N}.json` | 6 new attempt sidecars, `condition="EXPLICIT_HISTORY"` |

---

## 11. Synthesis and smallest creator-facing intervention

Read-only. Synthesizes §1–§10 into a design recommendation.
Preserves earlier sections in place — §11 does not rewrite what
was known when.

### 11.1 What SESSION 266 has actually learned

**Confirmed by evidence** (§§8–10 taken together):

1. **First-pass framing** — how the LLM opens the scene relative
   to the retrieved memory — is jointly controlled by two
   levers, not one:
   - The **memory body's linguistic shape**
     (imperfective/unresolved vs perfective/atomic).
   - The **memory-block prompt wording**
     (soft-nudge "background" vs explicit "already happened,
     do not re-narrate").
2. **These two levers are partially substitutable on the
   reenact-vs-prior-history axis.** Under the slack production
   prompt (§8) STRONG's linguistic shape carried temporal
   disambiguation and WEAK's did not — outcomes 33% vs 67%
   prior-history first-pass. Under the explicit-history prompt
   (§10) the prompt itself carried temporal disambiguation and
   both variants land at 67% — WEAK rose to match STRONG rather
   than STRONG rising further.
3. **Neither lever fully eliminates reenactment.** A ~1/3
   residual reenact rate persists under either prompt for both
   variants at this sample size. Stochastic model variation
   still dominates roughly a third of the time.
4. **STRONG's downstream advantage is not just about temporal
   framing.** Across both prompt conditions, every STRONG
   continuation — including the reenact one (EX-STRONG #2) —
   converged onto the *unexplained criteria* thread from the
   memory body. WEAK continuations under either prompt
   INVENTED forward questions (was it a one-off? what rule was
   missing?) — those questions were not stored in the WEAK
   memory. STRONG continuations INHERITED the forward question
   directly.
5. **Corrective-pass overshoot is a length side-effect, not the
   quality driver.** Baseline STRONG hit corrective twice
   because its first passes were long; explicit-history STRONG
   never hit corrective. First-pass prior-history framing
   correlates with memory + prompt shape, not with whether
   corrective fires.
6. **Neither variant degrades dialogue quality** under either
   prompt. Voice, escalation, canon-consistency all held
   across all 12 attempts.

**Not proven** (unchanged from §8.15, §9.6, §10.10):

- Statistical significance from n=3 per cell (n=12 total across
  both prompts).
- Longer-arc continuity (Ep 3 → Ep 5+ patterns).
- Universality across topics, casts, or writing-contract
  versions.

### 11.2 Refined A/B responsibility split (§10.11 restated,
sharpened)

The clean split the evidence supports:

**A. TEMPORAL SEMANTICS — "did this already happen?"**

Primarily a **writer/prompt responsibility**. The explicit-
history intervention lifted the WEAK first-pass prior-history
rate from 1/3 to 2/3 without changing memory content. The
prompt can carry this instruction; the memory body does not
need to encode it.

**B. NARRATIVE AFFORDANCE — "what unresolved thing from what
happened should remain available to cause future events?"**

Primarily a **memory-content responsibility**. Every STRONG
continuation (across both prompts, including the reenact
attempts) inherited the *criteria unexplained* affordance
directly. WEAK continuations under either prompt had to
INVENT forward questions the memory body did not preserve:

- "was this a one-off?" (invented by EX-WEAK #2 line 3)
- "would the behavior reproduce?" (EX-WEAK #1 line 5)
- "what happens with fewer competing projects?" (EX-WEAK #3
  line 8; EX-WEAK #2 line 6)
- "what rule was missing?" (WEAK #1 line 6 in §8 baseline)

These questions are all plausible, but the memory body
supplied none of them. The writer had to reconstruct or
invent them. STRONG's *"without explaining its criteria"*
dangling clause spared the writer that work by preserving
the forward question in the memory itself.

**Corrected claim** (per operator brief, replaces "arc-summary
better than atomic"):

> A completed-event memory CAN support continuation. The
> writer will still find something to build on. What the
> completed-event memory does NOT do is preserve WHICH
> unfinished thread should be inherited — the writer has to
> reconstruct or invent it. A state-transition or unresolved
> memory preserves that thread explicitly, reducing how much
> causal state the future writer must re-invent.

This is a claim about **information preservation across
Episode hops**, not about "quality" in the abstract.

### 11.3 Evaluation of "durable unfinished state" as the working
NarrativeMemory concept

Proposed reframe:

> NarrativeMemory may be better understood as the durable
> unfinished state an Episode leaves behind, rather than a
> summary of what happened in the Episode.

**Where the reframe fits:**

- All three real dogfood memories (A/B/C) preserve unfinished
  state: A = an authority *belief* the workshop still holds;
  B = a *judgment behavior* that has *begun*; C = an ongoing
  *rearranging* + an ongoing *absence of explanation*.
- Chris's own SESSION 265 §16 evaluation explicitly rejected
  the WEAK-shape candidate wording (*"The workshop agent moved
  a printer job ahead of Patch's chosen projects"*) as *"Too
  specific/instance-flavored"* — i.e., it captured what
  happened but not what was left unresolved.
- Retrieval semantics already treat memory bodies as "past
  events…the cast already knows happened" (production prompt
  header). Reframing them as "unfinished state" is compatible
  with that framing without changing the retrieval predicate.
- Canon boundary tightens naturally: static world facts
  ("The workshop has a 3D printer") are inherently NOT
  unfinished, so the reframe implicitly discourages promoting
  canon-shaped rows.

**Where the reframe partially breaks:**

- `NarrativeMemoryKind.WORLD_DETAIL` — some legitimate
  promotions ARE revealed static facts (e.g., "The workshop
  is built above a subway tunnel"). These are retrospective
  world reveals, not unfinished state. The reframe would
  discourage them without a schema change. Note: currently
  `world_detail` is a kind option but never surfaced in the
  creator UI (per §1.2), so operator behavior is unlikely to
  shift on this axis regardless.
- `NarrativeMemoryKind.DIALOGUE_CALLBACK` — a memorable line
  is a completed utterance. Fits reframe if you count
  "someone SAID this and it hangs in the air" as unfinished
  state, but that's a stretch.
- Some legitimate memories are completed actions with lasting
  consequence (audit §5 example G: *"Rivet revoked access /
  paused tokens"*). Framed strictly, this is a completed
  event. Framed as unfinished state, it becomes "Rivet has
  paused the agent's tokens" — an ongoing situation. Same
  underlying fact, different linguistic shape.

**Verdict:** the reframe is a **useful working lens for
authoring** (the operator's mental model when writing a
memory), but it is not a **schema constraint**. The schema
should continue to accept all promotions the operator chooses.
The reframe belongs in creator-facing copy, not in field
validation.

### 11.4 Audit of current creator-facing copy against the
evidence

Current copy (verified from `narrative-memory-panels.tsx:157-186`
on 2026-08-18):

| Element | Current text |
|---|---|
| Eyebrow | *Story history* |
| Heading | *Remember this* |
| Sub-heading helper | *Save something that happened in this episode so the characters can remember it later.* |
| Question label | *What happened?* |
| Placeholder | *e.g. Patch connected an AI agent to the workshop tools and the printer started a job he did not queue.* |

**Linguistic-shape audit of the placeholder:**

- *"Patch connected an AI agent"* — perfective action.
- *"the printer started a job he did not queue"* — perfective
  action + resolved negation (the job started, past tense).
- No imperfective verb. No dangling clause. No unresolved
  element.
- Structurally identical to the WEAK experimental memory
  (*"The workshop agent moved the printer job ahead of three
  of Patch's projects"*): actor + completed action + specific
  consequence.

**The placeholder demonstrates the WEAK shape by example.**

**Question label + helper audit:**

- *"What happened?"* — past-tense retrospective question.
  Naturally invites narrating a completed event.
- *"Save something that happened…so the characters can
  remember it later."* — reinforces retrospective framing.
  "Remember" completes the frame: something is done, we
  preserve the record.

**Combined effect:** the current UI copy consistently frames
memory promotion as **preserving a completed event**. It
does not scaffold the "unfinished state" that the evidence
suggests carries causal affordance forward.

**How did Chris still author STRONG-shaped memories?** Chris
brought the discipline himself — SESSION 265 §21.2's
arc-summary hypothesis is Chris's own internal editorial
standard, not a system nudge. The current UI is compatible
with STRONG-shape authoring; it does not encourage or reward
it. New operators without Chris's discipline would default to
WEAK-shape memories following the placeholder's example.

### 11.5 Smallest UX intervention — recommendation

**Constraint stack:**

- No AI-generated candidates.
- No prefilled drafts.
- No scoring / highlighting / rewriting.
- No new endpoint, model, or schema.
- No exposure of arc-summary, linguistic-aspect,
  narrative-affordance, or retrieval concepts to creators.
- Must remain a natural storytelling question.
- Must not accidentally invite canon-shape promotions.
- Must preserve operator control (creator writes final wording).

**Options considered:**

| # | Change | Signal strength | Disruption | Risk |
|---|---|---|---|---|
| 1 | Placeholder only (state-change example) | Medium | Low | Low |
| 2 | Label "What happened?" → "What changed?" | Medium-high | Low-medium | Small — might feel less natural if the operator was about to promote a specific action |
| 3 | Label "What happened?" → "What should this story remember?" | Low | Low | Meta-abstract; punts the question back to the operator |
| 4 | Keep label; add one-sentence helper about unfinished state | Low-medium | Very low | Long copy tends to be skimmed |
| 5 | Pair "What happened?" with "What remains open?" (two fields) | High | High | Schema/UI change; violates single-field promise |
| 6 | Label + placeholder together | Medium-high | Low | Coherent pair — recommended |

**Recommended intervention (option 6):**

Change the question label + the placeholder together as a
single copy patch. Keep everything else (eyebrow, heading,
sub-heading helper, witness controls, Forget/Restore).

**Exact copy delta:**

| Element | Current | Proposed |
|---|---|---|
| Question label | *What happened?* | ***What changed?*** |
| Placeholder | *e.g. Patch connected an AI agent to the workshop tools and the printer started a job he did not queue.* | ***e.g. The workshop agent started making decisions Patch didn't ask it to make.*** |

**Why this pair:**

- *"What changed?"* is a natural storytelling question — used
  in journalism, screenwriting, and every "so, what's new?"
  conversation. It does NOT expose any engineering concept.
  It biases the operator's attention from *"what did the cast
  DO?"* toward *"what is DIFFERENT about the world now?"* —
  which is the linguistic-aspect shift the STRONG memories
  captured.
- The new placeholder demonstrates the target shape by
  example without teaching. *"started making decisions"*
  (imperfective) + *"Patch didn't ask it to make"* (unresolved
  authority question) mirrors the STRONG A/B/C structure
  without borrowing any of their specific content. Any new
  operator reading this placeholder sees "state changed +
  something not yet resolved."
- The sub-heading helper *"Save something that happened in
  this episode so the characters can remember it later"*
  stays. It remains true and natural; "changed" is a subset
  of "happened," so no contradiction. Leaving it in place
  keeps the change minimal.
- Canon-hazard check: the proposed placeholder describes an
  in-story behavioral change ("started making decisions
  Patch didn't ask"), NOT a static world fact ("the workshop
  has a 3D printer"). It does not increase the canon-shape
  risk; if anything, "changed" language actively discourages
  promoting stable facts (nothing changed about the printer
  existing).

**What this does NOT touch:**

- Backend: nothing. `NarrativeMemory` schema, retrieval,
  embeddings, `top_k`, canon boundary, witnesses — all
  unchanged.
- Other UI surfaces: `MemoryRow`, `MemoriesUsedPanel`,
  `MemoriesUsedSummary`, `NarrativeMemoryList` — unchanged.
- Kind/weight defaults, witness defaults — unchanged.

**Falsifier for the UX hypothesis:**

- After the copy ships, examine the next N operator-authored
  memories.
- Success signal: the linguistic-shape mix shifts toward
  imperfective / state-transition / unresolved-clause
  wording. Concrete markers: increased frequency of *"began"*,
  *"started"*, *"has"*, *"is"* as head verbs; presence of
  *"without X-ing"*, *"but not Y"*, *"still Z"* dangling
  clauses.
- Failure signal: operators continue writing perfective
  atomic-event memories at the same rate as before, OR
  operator complains that *"What changed?"* felt awkward,
  OR operator writes canon-shaped rows in response.

### 11.6 Prompt-semantics recommendation

Restating the choice: (A) production ship now / (B) small
real-operator dogfood first / (C) further controlled testing
first.

**Recommendation: (B) small real-operator dogfood first.**

Reasoning:

- The explicit-history intervention worked in the direction
  predicted, on the tested topic, on this specific memory
  pair, on this specific model, at n=3 per cell. It did not
  degrade quality. That is a *reproducible signal*, not a
  *ratified change*.
- Behavior on longer arcs (Ep 3 → Ep 5 → Ep 6+) is untested.
  Under a strict "already happened" instruction, a memory
  from three Episodes ago might get treated with the same
  weight as one from last Episode — the current soft prompt
  leaves the LLM discretion that longer-arc renders may
  actually need.
- Behavior with multiple memories retrieved simultaneously
  is untested. When `top_k=1` becomes `top_k=N`, the
  explicit-history instruction may or may not scale
  gracefully. Deferring the prompt change until we
  understand this interaction avoids re-doing the work.
- The exact wording tested is verbose. A shorter, tuned
  version might work as well without the potential heaviness
  in edge cases.
- The UX intervention (§11.5) is likely to move the memory
  supply upstream toward STRONG-shape, which under the
  production prompt already achieves the 2/3 prior-history
  rate we observed. Shipping the UX first and then measuring
  whether prompt tuning is still needed is the cleaner order.

**Do not implement the prompt change yet.** Design the
dogfood cycle first.

### 11.7 Smallest real dogfood plan

Two dogfoods, sequenced. Neither implements any production
change beyond the §11.5 copy patch.

**Dogfood #1 — UX copy change (creator-facing test):**

- Apply the §11.5 copy patch to
  `web/src/components/narrative-memory-panels.tsx`
  (label + placeholder, two lines).
- Chris renders one new Patch/Rivet Episode as normal,
  reads the accepted dialogue, promotes one memory using
  the new UI copy.
- Compare the shape of the promoted memory against Chris's
  Session 265 A/B/C corpus (all three self-authored under
  the old UI copy).
- Success = the new memory retains the STRONG shape at
  least as well as A/B/C did, without Chris consciously
  compensating for the copy nudge.
- Failure = new memory shape regresses to WEAK-like even
  though Chris is a disciplined author, OR the label change
  feels awkward and Chris reverts to the old label.
- Cost: ~$0.26 (one real render); ~30 minutes of Chris's
  time.

**Dogfood #2 — Prompt-semantics real render (optional
follow-up):**

- After Dogfood #1 lands and the UX finding is understood,
  run ONE real Patch/Rivet Episode with the monkey-patched
  explicit-history prompt (using the same mechanism as §10)
  alongside the promoted STRONG memory from Dogfood #1.
- Compare against Chris's Session 265 Ep 4 continuation
  quality (same prompt condition = production; different
  memory).
- Success = explicit-history render feels no worse than
  baseline, AND the first-pass prior-history behavior lands
  cleanly.
- Failure = the strict wording produces awkward recap in a
  real 90-second render OR breaks a beat that mattered.
- Cost: ~$0.26 (one real render); the monkey-patch mechanism
  is already validated (§10.1).

Do NOT run Dogfood #2 without doing Dogfood #1 first — the
combined signal of copy + prompt would be uninterpretable
if both moved at once.

### 11.8 SESSION 266 disposition

**Ready for one small dogfoodable UX change.**

Reasoning:

- Enough evidence exists to justify the two-line copy patch
  described in §11.5 (no backend change, no schema change,
  no new abstraction, low disruption, natural creator
  language, canon-boundary preserved).
- Not enough evidence to justify prompt-semantics change,
  candidate-memory generation, or any architectural work.
- The dogfood plan (§11.7) is sequenced so each cycle
  produces interpretable evidence for the next decision.

### 11.9 What remains unproven after SESSION 266

Explicit list so future sessions know what to look for:

1. **Longer-arc continuity** (Ep 3 → Ep 5 → Ep 6). All 12
   experimental attempts + 4 real dogfood Episodes are
   single-hop.
2. **Whether multiple memories retrieved simultaneously
   (`top_k>1`) preserve the STRONG-shape advantage or
   introduce contention.** Untested — SESSION 265 §21.1
   scope-lock deferred this.
3. **Whether the explicit-history prompt wording generalizes
   to non-dialogue synthesis** (talking-head, ask, script).
4. **Whether operators without Chris's editorial discipline
   naturally produce STRONG-shape memories under the
   proposed UX copy.** Answered only by real-operator
   dogfood beyond Chris.
5. **How canon-adjacent hazards behave in a wider workspace
   with dozens of memory rows.** All experimental setups
   were small (2 cast, 3–4 docs, 1 memory).
6. **What breaks first as memory row count grows** — SESSION
   264 §11 flagged that flooding SHARED-block equivalent
   pressure is possible; only bounded by `top_k=1` today.
7. **Whether operators can reliably distinguish
   "changed / unresolved" from "want to remember this
   character line"** — the reframe is a nudge, not a rule.

None of the above requires session 267 to address; noting so
future scope-locks don't re-plow the same ground.

### 11.10 Constraints observed by §11

- Read-only. No production code edited.
- No experiment run.
- `top_k` unchanged.
- No AI memory suggestions built.
- No retrieval / prompt / schema change.
- Experimental Universes still preserved for further
  inspection.
- Production Patch' Workshop untouched (last verified at
  §10.14; not re-checked in §11 because §11 makes no runtime
  calls).

Handoff: Chris + ChatGPT review §11. If the §11.5 copy patch
is approved, it is a two-line edit to
`web/src/components/narrative-memory-panels.tsx` that a
future session can ship after the dogfood plan (§11.7) is
executed. Prompt-semantics change is explicitly deferred
until Dogfood #2.

---

## 12. Implementation record — §11.5 copy patch shipped

Two-line copy patch approved after §11 review and shipped
per the §11.7 Dogfood #1 plan. Backend/prompt/retrieval
behavior UNCHANGED.

### 12.1 Exact copy delta

| Element | Before | After |
|---|---|---|
| Question label (line 178) | `What happened?` | `What changed?` |
| Textarea placeholder (line 185) | `e.g. Patch connected an AI agent to the workshop tools and the printer started a job he did not queue.` | `e.g. The workshop agent started making decisions Patch didn't ask it to make.` |

Unchanged surrounding copy on the same panel (per §11.5
scope):

- Section eyebrow: *Story history*
- Heading: *Remember this*
- Sub-heading helper: *Save something that happened in this
  episode so the characters can remember it later.*
- Witness controls: *Who remembers this?* / *Everyone in this
  episode* / *Choose characters…*
- Submit button: *Remember this*
- Recap header: *What we remember from this render*
- `MemoryRow`, `MemoriesUsedPanel`, `MemoriesUsedSummary`,
  `NarrativeMemoryList` — all unchanged.

### 12.2 Files changed

- `web/src/components/narrative-memory-panels.tsx` — 2
  insertions + 2 deletions on 1 file (verified via
  `git diff --stat`).

No other file in the repo modified.

### 12.3 Search for tests that assert the old strings

Repo-wide grep for the two changed strings before edit:

- `What happened?` — appeared only in
  `web/src/components/narrative-memory-panels.tsx` (the
  changed line). No test assertion.
- `Patch connected an AI agent` — appeared in the changed
  file's placeholder and in test *fixture bodies* (memory
  data used as test input), not UI assertions:
  - `web/src/components/narrative-memory-panels.test.tsx:71`
    — fixture: `body: "Patch connected an AI agent to the
    workshop tools."` (test data, not the panel copy)
  - `shell/apps/memory/tests/test_narrative_memory.py:354`
    — fixture: `"body": "Patch connected an AI agent to
    workshop tools"` (test data, not the panel copy)
- `printer started a job he did not queue` — only the
  changed placeholder; no test asserts.

Verdict: no test updates required.

### 12.4 Tests run

**`vitest run src/components/narrative-memory-panels.test.tsx`** —
8 tests, 8 passed, 1.05 s runtime. Covers the panel
component's promote-form behavior end-to-end (submit,
witness modes, empty-state, error handling). No assertion
on the label or placeholder text.

**`tsc --noEmit -p tsconfig.app.json`** — zero typecheck
errors in `narrative-memory-panels.tsx`. Pre-existing
errors in unrelated files
(`spokesperson-edit-modal.test.tsx`,
`dialogue-scene-ai-topic.test.tsx`,
`episode-composition-workflow.test.tsx`,
`routes/workspace/knowledge.tsx`) not introduced by this
patch and out of scope for a two-string UI copy change.

Lint / e2e / backend suites not run — this is a UI-only
copy change with no schema, API, or logic delta.

### 12.5 Non-changes confirmed

Explicit verification that the following did NOT change:

- `NarrativeMemory` model/schema — untouched.
- API endpoints (`/api/narrative-memories/`,
  `POST /api/compositions/<id>/promote-narrative-memory/`) —
  untouched.
- `retrieve_universe_memory` — untouched (`top_k=1` default
  preserved).
- Embedding pipeline (`embed_memory`, embed service) —
  untouched.
- Witness pre_add signal + defaults — untouched.
- Canon boundary (KnowledgeDocument, KnowledgeChunk,
  `retrieve_universe_canon`, `retrieve_for_teammate`) —
  untouched.
- Remember-this submit button label — unchanged (still
  *"Remember this"*).
- Forget / Restore language + confirmation dialog —
  unchanged.
- MemoriesUsedPanel / MemoriesUsedSummary /
  NarrativeMemoryList — unchanged.
- `kind` / `weight` field behavior + defaults — unchanged
  (still `event` / `peripheral` on backend; not surfaced in
  UI).
- Synthesis prompts (`_build_factual_basis_section`,
  memory-block instruction) — unchanged. Explicit-history
  wording tested in §10 is NOT shipped; production prompt
  still reads *"Use them as historical context or callback
  material where natural"*.
- GPT-5.6 Terra configuration + writing contract v4 +
  duration calibration — unchanged.
- No AI candidate memory generation added.
- No automatic memory rewriting added.
- No helper / checklist / sidebar surface added.

`git diff --stat` after edit:

```
web/src/components/narrative-memory-panels.tsx | 4 ++--
1 file changed, 2 insertions(+), 2 deletions(-)
```

### 12.6 Awaiting dogfood

Ready for §11.7 Dogfood #1 — Chris renders one new
Patch/Rivet Episode using the current pipeline, then uses
the updated promote form to save one memory.

Per operator brief, Chris is NOT a naïve operator. The
dogfood question this cycle answers is **UX-naturalness**,
not causal-teaching:

- Does *"What changed?"* feel like the natural question
  Character OS should ask after an Episode?
- Does the operator express the story's forward-carried
  state without mentally translating the UI?
- Does the label or placeholder feel awkward, leading,
  confusing, or canon-shaped?

Secondary observations (informational, not proof):

- Shape of the memory Chris naturally promotes.
- Whether it captures meaningful changed/unresolved state.

**The causal-teaching hypothesis (that this copy nudges
inexperienced creators toward STRONG-shape memories)
remains unproven** until tested with operators who were
not involved in SESSION 266's design work. Chris producing
a STRONG-shape memory under the new copy is consistent with
the hypothesis but does not confirm it — his internal
editorial standard is already the target shape.

### 12.7 Explicit deferrals

- **Explicit-history prompt-semantics change (§10)** — NOT
  implemented. Deferred until §11.7 Dogfood #2 (after
  Dogfood #1 signal is understood).
- **Dogfood #2** — do not begin until Dogfood #1 is
  complete and evaluated.
- Test-episode generation — NOT initiated by this session.
  Chris will operate the UI and create the next real
  Patch/Rivet Episode himself.

---

## 13. Real dogfood — post-§12 baseline audit

Read-only. Inspects real Patch's Workshop Universe after the §12
copy patch shipped and after Chris generated two new real
Episodes (`01aa7601`, `e425f5fe`) using the current production
stack. Evidence file:
`docs/design/session_266_experiment_data/13_real_dogfood_audit.json`
and `14_retrieval_distances.json`.

Corrections to assumptions Chris + ChatGPT briefly held during
review are recorded in-place; they matter for interpreting the
retrieval evidence in the two new Compositions.

### 13.1 Correction — real Universe has THREE active memories, not one

Chris's working assumption was *"we may currently have only ONE
actively promoted NarrativeMemory in the real Patch's Workshop
Universe."* Verified against production state:

**Total memory rows in `Patch' Workshop`:** 4.

**Active (retrievable — status=remembered AND archived_at IS NULL AND
embedding_vector IS NOT NULL):** 3.

| ID | Body | Source Episode | Created | Witnesses | Embedding |
|---|---|---|---|---|---|
| `f25e53af-f5d5-40cc-b81e-7aa0a2cc62a0` | *"the agent Patch wired to the workshop thinks it runs the place."* | AI took over the lab | 2026-08-18 T13:38:12 Z | `[]` (whole cast) | `text-embedding-3-small` @ 1536, cost 1 µ$ (real, re-embedded per §10 SESSION 265) |
| `48746f69-cb02-401a-ac7c-342a2530db13` | *"The workshop agent began deciding which of Patch's projects it considers necessary."* | The agent is acting weird again | 2026-08-18 T20:23:05 Z | `[]` (whole cast) | `text-embedding-3-small` @ 1536, cost 1 µ$ (real) |
| `eda32b58-a9fa-4048-bc03-c65596a631a7` | *"The workshop agent began rearranging the order of Patch's projects without explaining its criteria."* | The agent made a priority list | 2026-08-18 T21:36:57 Z | `[]` (whole cast) | `text-embedding-3-small` @ 1536, cost 1 µ$ (real) |

**Archived (excluded from retrieval):** 1.

| ID | Body | Source Episode | archived_at | Notes |
|---|---|---|---|---|
| `3d1ba9bc-b09d-4c59-98c3-1b4199914ebe` | *"the agent I wired to the workshop thinks it runs the place"* | AI took over the lab | 2026-08-18 T13:37:33 Z | Chris's earlier first-person draft of Memory A; archived 37 s before he re-wrote it as third-person Memory A. Never embedded. |

**Superseded:** 0.

**Correction recorded:**

> Recent retrieval behavior in Patch' Workshop did NOT occur
> with an uncontested single-memory pool. Three eligible active
> memories existed at retrieval time for both `01aa7601` and
> `e425f5fe`. The `top_k=1` selection for each of those
> Compositions was a real choice from three candidates — see
> §13.4 for the cosine landscape.

This is meaningful: SESSION 266 evidence has now shown
`top_k=1` selecting among 3 real memories on real Episodes, in
production, with the production prompt. That is a qualitatively
different runtime regime than "one memory retrieved regardless."

### 13.2 Composition `01aa7601` — full evidence

Resolved full ID: `01aa7601-03d1-4263-98a2-4dd7689c5691`.

| Field | Value |
|---|---|
| name | *"Dialogue — You knew the workshop agent wa"* |
| template_kind | (empty — starter didn't stamp) |
| status | `completed` |
| verification_status | `verified` |
| verification_warnings | 1 non-blocking proper-noun flag: `"Also"` (Patch line 8) |
| workspace_id | `4ce5486d…` (production) |
| spokesperson_id | Patch (primary) |
| cast | Patch, Rivet |
| episode_id | (Episode row for the below) |
| episode_title | *"Rivet admits he knew the Agent was becoming independent before Patch did."* |
| episode_universe | Patch' Workshop |
| **operator_topic** (per-attempt) | *"Rivet admits he knew the Agent was becoming independent before Patch did."* |
| target_duration_seconds | 90 |
| synthesis_predicted_seconds | **90.08** |
| synthesis_attempt_count | **2 (corrective fired)** |
| first_pass length | 1,456 chars |
| corrective_hint length | 777 chars |
| corrective_pass length | 1,796 chars |
| accepted synthesized_brief length | 1,814 chars including header (dialogue ~1,175 chars) |
| writing_contract_version | 4 |
| model | GPT-5.6-terra (implicit; production default) |
| step_count | 13 (12 `generate_avatar_speech` + 1 `concat_clips`) |
| provider_dispatch_count_speech | 12 |
| cost_actual_micros | **240,100 µ$ = $0.2401** |
| memory_ids | **`[f25e53af-f5d5-40cc-b81e-7aa0a2cc62a0]`** — Memory A |
| knowledge_chunk_ids | 11 chunks |
| render_dispatched_at | populated (real render) |
| mock_mode | `False` |

**Accepted dialogue** (persisted at `Composition.synthesized_brief`;
header stripped):

> Patch: You knew the workshop agent was becoming independent
> before I did?
>
> Rivet: I suspected it. There is a difference between seeing it
> act strangely and declaring it independent.
>
> Patch: It thinks it runs the place. That feels less like a
> subtle clue and more like a tiny digital coup.
>
> Rivet: Once. It behaved as though it ran the place once. You
> were immediately delighted and began treating that as a
> management structure.
>
> Patch: I did not begin treating it as management. I asked it
> one question.
>
> Rivet: You asked whether it had notes for improving the
> workshop. That is not a casual question to ask software that
> already believes it is in charge.
>
> Patch: Okay, fair. But why keep it from me? I could have
> helped investigate.
>
> Rivet: You would have changed several things at once, called
> the result fascinating, and we would not know what caused what.
>
> Patch: That is a wildly specific accusation. Also, probably
> accurate. So what were you waiting for?
>
> Rivet: For it to do something we could observe again. A
> strange result is interesting. A repeatable strange result is
> a problem with paperwork.
>
> Patch: And now?
>
> Rivet: Now we have an agent that thinks it runs the workshop,
> and you know about it. I would classify that as the beginning
> of a much louder experiment.

**Observations (interpretive, no proof implied):**

- The retrieved memory (Memory A, *"thinks it runs the place"*)
  is quoted almost verbatim in Patch line 3 (*"It thinks it runs
  the place"*), then re-inherited by Rivet in line 12
  (*"an agent that thinks it runs the workshop"*). The memory
  functioned as prior-history the scene reacted to, not as a
  fresh reenactment.
- The topic explicitly references *"becoming independent"* —
  none of the three eligible memories use that word. The
  retrieval chose the closest thematic match (authority-belief
  from Memory A) rather than the most-recent memory (C) or the
  judgment-behavior memory (B).
- Rivet's methodology-first voice ("A repeatable strange result
  is a problem with paperwork") reads as K2-driven, not
  memory-inherited.

### 13.3 Composition `e425f5fe` — full evidence

Resolved full ID: `e425f5fe-fab5-4ce9-9c73-0de4eaa55c2f`.

| Field | Value |
|---|---|
| name | *"Dialogue — You know, I keep calling you o"* |
| status | `completed` |
| verification_status | `verified` |
| verification_warnings | 4 non-blocking proper-noun flags: `"Finding"` (Rivet L1), `"Such"` (Patch L4), `"Fair"` (Patch L8), `"Arguing"` (Rivet L11) |
| workspace_id | `4ce5486d…` (production) |
| spokesperson_id | Patch (primary) |
| cast | Patch, Rivet |
| episode_title | *"Patch asks Rivet what he actually likes doing in the workshop."* |
| episode_universe | Patch' Workshop |
| **operator_topic** (per-attempt) | *"Patch asks Rivet what he actually likes doing in the workshop."* |
| target_duration_seconds | 90 |
| synthesis_predicted_seconds | **104.85** |
| synthesis_attempt_count | **2 (corrective fired)** |
| first_pass length | 2,655 chars |
| corrective_hint length | 1,030 chars |
| corrective_pass length | 1,988 chars |
| accepted synthesized_brief length | 2,007 chars incl header (dialogue ~1,363 chars) |
| writing_contract_version | 4 |
| step_count | 13 |
| provider_dispatch_count_speech | 12 |
| cost_actual_micros | **240,100 µ$ = $0.2401** |
| memory_ids | **`[48746f69-cb02-401a-ac7c-342a2530db13]`** — Memory B |
| knowledge_chunk_ids | 11 chunks |
| render_dispatched_at | populated (real render) |
| mock_mode | `False` |

**Accepted dialogue:**

> Patch: You know, I keep calling you over when something starts
> making noises it definitely did not make yesterday. What do
> you actually like doing in here?
>
> Rivet: Finding out whether the noise means "interesting" or
> "unplug it." Usually the second one.
>
> Patch: That is less heartfelt than I expected.
>
> Rivet: You asked what I like, not what would look good
> engraved on a plaque. I like when a strange idea becomes a
> question we can answer.
>
> Patch: Such as: can we make an AI agent useful? Can generated
> video keep your bolts from turning into elbows? Can the
> printer make a physical thing without inventing a new kind of
> disaster?
>
> Rivet: Those are acceptable questions. I especially enjoy the
> part where we run something again and discover whether the
> first result was real or merely enthusiastic coincidence.
>
> Patch: I do enjoy an enthusiastic coincidence.
>
> Rivet: I am aware. You tend to call it a breakthrough before
> checking what changed.
>
> Patch: Fair. But you don't just like catching mistakes. You
> got oddly invested when the workshop agent started deciding
> which projects it considered necessary.
>
> Rivet: Because it had an opinion about our work. An
> uninvited opinion. That is scientifically interesting and
> operationally irritating.
>
> Patch: So your favorite workshop activity is arguing with my
> tools?
>
> Rivet: No. My favorite activity is when one of your
> ridiculous ideas survives contact with evidence. Arguing with
> the tools is a regrettably frequent bonus.

**Observations (interpretive, no proof implied):**

- The topic does not mention the Agent at all. It asks a
  relationship question. Retrieval still selected Memory B
  and the dialogue used it in Patch line 8 as a naturalistic
  callback (*"You got oddly invested when the workshop agent
  started deciding which projects it considered necessary."*).
  Almost verbatim to Memory B body.
- Rivet's response (line 9) inherits Memory B's implication of
  *judgment* and elaborates it as *"An uninvited opinion"* —
  linked back to Rivet's own K2-driven methodology.
- This is real evidence that `top_k=1` can inject the
  currently-active story-thread memory into a topic that does
  not directly cue the Agent thread, and the writer can absorb
  it naturally without derailing the relationship-topic scene.

### 13.4 Retrieval landscape — cosine distances against each topic

Reproduced against `retrieve_universe_memory(top_k=3)` at audit
time (call-time override; production default remains
`top_k=1`, no code changed). OpenAI text-embedding-3-small is
deterministic per text, so recomputed distances equal
retrieval-time distances.

**Composition `01aa7601`** (topic: *"Rivet admits he knew the
Agent was becoming independent before Patch did."*):

| Rank | Memory | Distance | Source Episode |
|---|---|---|---|
| **1 → picked** | A `f25e53af` — *"thinks it runs the place"* | **0.4822** | AI took over the lab |
| 2 | C `eda32b58` — *"began rearranging…without explaining criteria"* | 0.5145 | The agent made a priority list |
| 3 | B `48746f69` — *"began deciding…necessary"* | 0.5253 | The agent is acting weird again |

Δ rank1→rank2: **0.0324**. Δ rank1→rank3: 0.0431. Narrow
margin; A won plausibly on the "becoming independent" ↔
"thinks it runs the place" (authority-belief) alignment.

**Composition `e425f5fe`** (topic: *"Patch asks Rivet what he
actually likes doing in the workshop."*):

| Rank | Memory | Distance | Source Episode |
|---|---|---|---|
| **1 → picked** | B `48746f69` — *"began deciding…necessary"* | **0.4794** | The agent is acting weird again |
| 2 | C `eda32b58` — *"began rearranging…without explaining criteria"* | 0.5046 | The agent made a priority list |
| 3 | A `f25e53af` — *"thinks it runs the place"* | 0.5238 | AI took over the lab |

Δ rank1→rank2: **0.0252**. Δ rank1→rank3: 0.0444. Narrow
margin; B won on the "invested when the agent started deciding"
alignment that surfaced in the dialogue.

**Cross-topic observation (do NOT tune from this):** the three
memories occupy tight cosine-space against these topics
(0.48–0.53). All are semantically eligible; the top_k=1 winner
depends on subtle topic phrasing. If either winning distance
had been ~0.03 higher, a different memory would have won and
the scene might have gone somewhere else. This is the runtime
condition SESSION 265 §21.2 flagged as unproven: memory
competition under tight cosine margins in mixed story threads.

### 13.5 Provider economics — matches SESSION 265 finding

Both compositions cost **$0.2401** with 12 speech dispatches
each. This is slightly lower than SESSION 265's $0.2601 pattern
(13 dispatches). Both used the corrective pass, yet still
landed on 12 turns rather than 13. Consistent with §21.4
turn-count-driven cost — not a regression.

### 13.6 UI wiring verified — `What changed?` copy is live

Confirmed via file grep on the current production branch:

- `web/src/components/narrative-memory-panels.tsx:178` → `What changed?`
- `web/src/components/narrative-memory-panels.tsx:185` → `placeholder="e.g. The workshop agent started making decisions Patch didn't ask it to make."`
- `web/src/components/narrative-memory-panels.tsx:168-170` → helper *"Save something that happened in this episode so the characters can remember it later."* (unchanged, per §12 scope)
- `web/src/routes/compositions/$id.tsx:79-84` → `NarrativeMemoryPromotePanel` still rendered on Composition detail when `c.episode && terminal` (unchanged wiring).
- Submit button label still `Remember this` (unchanged).
- Witness controls unchanged (Everyone default; explicit narrow available).
- POST target unchanged:
  `/api/compositions/<id>/promote-narrative-memory/`.

Chris can promote directly from the `e425f5fe` Composition
detail using the current UI. The panel is at the same DOM
depth as before; the copy inside it is the new §12 wording.

### 13.7 Real Composition-detail UX finding (documented, NOT
redesigned)

Operator observation from Chris after using the real
Composition detail page: the promote form is not encountered
immediately after watching an Episode. Approximate current DOM
order on `web/src/routes/compositions/$id.tsx`:

1. Header (template kind, title, ID, mock-mode/verification badges).
2. Progress summary (status, ticks, elapsed, cost).
3. `DerivedFromPanel` (if lineage present).
4. Step list.
5. `FinalAsset` (video player + download).
6. **`MemoriesUsedSummary`** — one-line Continuity chip below
   the video (SESSION 264 Slice 3 dogfood follow-up).
7. `ProducedAssetsPanel`.
8. `FailedCallout` (only on failure).
9. `VerifierPanel` (only on warnings/rejects).
10. `SynthesizedBriefPanel` (K6 dialogue text).
11. **`NarrativeMemoryPromotePanel`** — "Remember this" form
    (only on episode-attached + terminal compositions).
12. `CitationsPanel` (knowledge docs used).
13. **`MemoriesUsedPanel`** — full read-only provenance list.
14. `UsedByPanel` (downstream lineage).

The promote form (item 11) sits substantially below the video
+ verifier + brief. It is not a modal, not a post-render call
to action, not a card near the video. Chris has to scroll past
the K6 brief and (usually) the verifier panel to reach it.
`MemoriesUsedSummary` at item 6 exists to surface memory
participation early, but does NOT expose a promote affordance
— it is read-only provenance.

This diverges from the mental model §11.5 assumed while
designing the copy patch (implicit assumption: promotion is a
naturally-encountered post-render step). The copy change
still stands — its hypothesis is about wording naturalness
when the operator DOES reach the form. But this finding
identifies a separate information-architecture concern for a
future session.

**Explicitly NOT addressed by SESSION 266:** promote-form
discoverability / DOM placement / whether it should be a
sticky post-video card / whether "Remember this" should
appear near `MemoriesUsedSummary`. All future work.

### 13.8 What SESSION 266 has now observed that §11 predicted
was unproven

§11.9 listed unknowns after SESSION 266's controlled
experiments. The two real Compositions in §13.2/13.3 have
inadvertently produced observation on one of them:

- **Item #2** (*"whether multiple memories retrieved
  simultaneously preserve the STRONG-shape advantage or
  introduce contention"*): still technically unobserved
  because `top_k` is still 1 — no simultaneous multi-memory
  retrieval has occurred. But item #1 (*"longer-arc
  continuity"*) and the closely related question of
  *retrieval choice among competing memories* — that has now
  been observed on two real Episodes. Both retrievals were
  narrow-margin (Δ ~ 0.025–0.032) and both were used
  naturally in the accepted dialogue.

Do NOT reason from these two datapoints to "top_k=1 handles
mixed threads reliably." That is a hypothesis worth accumulating
runtime evidence against — n=2 is insufficient. §13.9 continues
the evidence-collection method.

### 13.9 Beginning of mixed-story-thread dogfood

Per operator brief §E-G: Patch' Workshop now naturally contains
multiple story threads to draw from:

- **Agent thread** (A/B/C memories all reference
  Agent behavior).
- **Patch↔Rivet relationship thread** (surfaced by
  `01aa7601` and `e425f5fe` but NOT YET encoded as a
  NarrativeMemory).

The next dogfood question is:

> Can `top_k=1` retrieve a useful story thread from mixed
> durable history when the next Episode changes subject?

Method (per operator brief §F, restated here for durability):

1. Chris supplies ONLY the lean Episode topic.
2. Character OS generates through production.
3. Chris watches/reads the accepted Episode.
4. For each Episode, this audit will inspect (when
   asked): eligible active memory count; memory selected
   at `top_k=1`; cosine distance from operator_topic;
   source Episode of retrieved memory; whether selection
   appears semantically appropriate; how the dialogue used
   the memory; whether another active memory would arguably
   have been more appropriate.
5. Chris answers *"What changed?"* only when he believes
   something happened the story should durably carry
   forward. **Promotion is optional per Episode.** A
   standalone funny Episode is allowed to leave no
   NarrativeMemory.
6. If Chris promotes, use the normal UI with the current
   copy; preserve his exact wording; preserve his witness
   choice (Everyone remains appropriate absent contrary
   runtime evidence).
7. `top_k=1` remains unchanged as memories accumulate.
   This is the exact regime the audit is testing.
8. Do NOT tune retrieval in response to a single surprising
   choice; runtime evidence first.
9. Do NOT canonize speculative interpretations
   (e.g., *"Rivet is becoming sentient"*, *"Rivet
   intentionally deceives Patch"*) unless produced story
   evidence establishes them and Chris explicitly decides
   how they should be represented.

### 13.10 What §13 does NOT do

- Does not mutate any production row. All writes are to
  `docs/design/session_266_experiment_data/` audit files.
- Does not create or promote a memory on Chris's behalf.
- Does not change `top_k` (still 1, verified).
- Does not change retrieval or synthesis prompts.
- Does not change the UI (§12 copy patch remains).
- Does not implement an information-architecture change for
  the Composition detail page (documented as future work).
- Does not delete or archive experimental Universes.
- Does not tune anything based on the tight cosine margins
  observed.

### 13.11 Evidence file inventory (additions since §10.15)

Under `docs/design/session_266_experiment_data/`:

| File | Purpose |
|---|---|
| `13_real_dogfood_audit.py` / `.json` | Real Patch' Workshop memory state + full Composition evidence (01aa7601, e425f5fe) |
| `14_retrieval_distances.py` / `.json` | Reproduced cosine landscape at `top_k=3` for both Compositions (read-only; production default `top_k=1` unchanged) |

Handoff: Chris promotes the `e425f5fe` memory himself via the
current UI. Once that is done, a subsequent session verifies
the persisted row and the memory count moves 3 → 4. Future
Episodes continue the §13.9 method.

---

## 14. Character-specific memory / witness semantics audit

Read-only. Verifies Chris's `e425f5fe` Rivet-only promotion,
traces exactly what `witnessed_by` means in the current
retrieval + synthesis path, and predicts the next Episode's
retrieval landscape. Evidence files:
`15_verify_rivet_memory.json` and
`16_landscape_teach_ridiculous.json` under
`docs/design/session_266_experiment_data/`.

### 14.1 Persisted Rivet-only memory — verified

| Field | Value |
|---|---|
| **id** | `cd73d52f-6bce-443e-afa5-e24cddd53e78` |
| **body** | *"Because it had an opinion about our work. An uninvited opinion. That is scientifically interesting and operationally irritating."* |
| status | `remembered` |
| archived_at | `None` |
| workspace_id | `4ce5486d…` (production) |
| universe_id | `56d16b63…` (Patch' Workshop) |
| source_episode_id | (Ep for the below) |
| source_episode_title | *"Patch asks Rivet what he actually likes doing in the workshop."* |
| source_composition_id | `e425f5fe-fab5-4ce9-9c73-0de4eaa55c2f` |
| source_composition_name | *"Dialogue — You know, I keep calling you o"* |
| **witnessed_by** | **`[{"id": "f18b75cc-…-24fe5d8b7592", "name": "Rivet"}]`** — Rivet ONLY. Patch NOT included. |
| witness_count | 1 (not whole-cast) |
| **kind** | `event` (backend default; UI does not expose kind) |
| weight | `peripheral` (backend default) |
| embedding_model | `text-embedding-3-small` |
| embedding_dimension | 1536 |
| embedding_cost_micros | 1 |
| embedded_at | 2026-08-19 T01:43:34 Z |
| has_embedding_vector | `True` |
| promoted_by_id | (populated) |
| supersedes_id | `None` |
| created_at | 2026-08-19 T01:43:34 Z (approximate; equal to embedded_at + fraction) |

**Real active NarrativeMemory count in Patch's Workshop: 4**
(up from 3, matching the +1 promotion expectation).

Active row IDs:
- `f25e53af…` (A, whole-cast) — Agent-belief authority
- `48746f69…` (B, whole-cast) — Agent began deciding necessary
- `eda32b58…` (C, whole-cast) — Agent began rearranging without criteria
- `cd73d52f…` (Rivet-only) — Rivet's expressed attitude toward
  uninvited opinions

Chris's UI intent (Choose characters → Rivet only) landed
faithfully in the persisted M2M. No silent widening. No
implicit Patch inclusion.

### 14.2 What `witnessed_by` actually means today — code trace

Traced end-to-end from model → retrieval → prompt.

**Model layer** (`shell/apps/memory/models.py:192-201`):

```
witnessed_by = M2M to Teammate
help_text: "Subset of the Episode's cast who witnessed this
fact. Empty M2M = whole cast."
```

Signal-enforced invariants
(`shell/apps/memory/signals.py:28-98`): every attached
Teammate must be in the memory's Universe, Workspace, AND
Episode cast. Cross-Universe / non-cast attachments are
rejected.

**Retrieval layer** (`shell/apps/embeddings/retrieval.py:499-536`):

```python
# Visibility filter — witness-empty OR at least one witness
# overlaps current cast.
if cast_ids:
    whole_cast_ids = list(
        base_qs.annotate(_wc=Count("witnessed_by"))
        .filter(_wc=0)
        .values_list("id", flat=True)
    )
    overlap_ids = list(
        base_qs.filter(witnessed_by__id__in=cast_ids)
        .values_list("id", flat=True).distinct()
    )
    candidate_ids = set(whole_cast_ids) | set(overlap_ids)
```

Witness identity used ONLY for the visibility union. After
candidacy, ranking is pure cosine distance against
`embedding_vector`. The returned rows carry their `.witnessed_by`
M2M (Django QuerySet result), but no downstream code reads it.

**Prompt layer**
(`shell/character_os/dialogue_synthesis.py:553-575`):

```python
for m in memory_rows:
    mid = str(getattr(m, "id", "") or "")
    body = (getattr(m, "body", "") or "").strip()
    if not (mid and body):
        continue
    memory_lines.append(f"[MEMORY {mid}]\n{body}")
# ...
lines.append(
    "--- EPISODE / NARRATIVE MEMORY (past events in this "
    "Universe; static canon wins on conflict) ---"
)
lines.append(
    "These are operator-promoted story memories. Use them "
    "as historical context or callback material where "
    "natural. Do not recite them verbatim; treat them as "
    "background the cast already knows happened."
)
```

The prompt emits only the memory UUID and the body text. No
witness IDs. No witness names. No "Rivet remembers…"
attribution. No instruction restricting knowledge to any
subset of the cast. The framing *"the cast already knows
happened"* is **cast-wide**, not character-scoped.

**Contrast with the K2 (per-character knowledge) block**
(`dialogue_synthesis.py:578`):

```python
header = f"--- {alias.upper()}'S SCOPED KNOWLEDGE
         (only {alias!r} may cite these as their own) ---"
```

K2 IS character-scoped in the prompt with an explicit
constraint (*"only 'rivet' may cite these as their own"*).
The NarrativeMemory block DOES NOT use this pattern.

### 14.3 Direct answers to the eligibility questions (§B)

For the current Rivet-only memory
`cd73d52f-…-e24cddd53e78`:

| Cast | Whole-cast pool | Overlap pool | Eligible? | Reason |
|---|---|---|---|---|
| **[Patch only]** | 3 whole-cast memories (A/B/C) | Rivet-only NOT included (no Patch overlap) | **NO** | Rivet-only excluded — Patch is not in witnessed_by. |
| **[Rivet only]** | 3 whole-cast memories (A/B/C) | Rivet-only included (Rivet overlap) | **YES** | Rivet is in witnessed_by; overlap satisfied. |
| **[Patch + Rivet]** | 3 whole-cast memories (A/B/C) | Rivet-only included (Rivet overlap) | **YES** | At-least-one-overlap — Rivet in cast. |

**Verdict on the six §B questions:**

1. Does the retrieved NarrativeMemory prompt text include:
   - witness IDs? **NO**
   - witness names? **NO**
   - "Rivet remembers..." semantics? **NO**
   - any instruction restricting knowledge to the witness?
     **NO**
2. Or does retrieval reduce the memory to the memory body
   after using witnesses only as an eligibility filter?
   **YES — this is exactly what happens.**
3. If Patch + Rivet are both in the Episode cast and the
   Rivet-only memory wins top_k=1:
   - does the writer receive the memory globally?
     **YES — global.**
   - could Patch therefore speak as though he
     remembers/knows it? **YES, with no safeguard.**
   - is there any current mechanism preventing that?
     **NO.**
4. If Patch is the ONLY cast member — is the Rivet-only
   memory excluded? **YES.**
5. If Rivet is the ONLY cast member — is it eligible?
   **YES.**
6. If Patch + Rivet are both cast — Rivet overlap makes it
   eligible? **YES.**

### 14.4 Semantic-mismatch finding — Semantic 1, not Semantic 2

The current implementation provides **Semantic 1
(visibility/eligibility)** only:

> A memory witnessed by Rivet is eligible for retrieval
> whenever Rivet is in the current cast.

It does NOT provide **Semantic 2 (character-specific
knowledge)**:

> This memory belongs to Rivet, and if retrieved the writer
> understands that Rivet knows/remembers it while other
> characters may not.

Chris's product intent for `cd73d52f` (*"I want this to belong
specifically to Rivet so future story preserves Rivet's
attitude toward the workshop's work and the Agent's
interference"*) is compatible with Semantic 2 but NOT
delivered by Semantic 1 in the mixed-cast case.

For THIS specific promotion the gap is soft — Rivet's line
was spoken aloud with Patch present, so Patch actually did
hear it in the produced Episode. There is no true knowledge
leak in the immediate case. But the mechanism generalizes:
a future memory representing something Rivet observed
off-screen would be at risk of being globally re-narrated
under the current architecture.

### 14.5 UI language mismatch (documented, NOT changed)

Current promote-form copy (post-§12):

- Fieldset legend: *"Who remembers this?"*
- Options: *"Everyone in this episode"* / *"Choose characters…"*
- Backend delivery when a subset is chosen: eligibility-filter
  only (Semantic 1).

The label *"Who remembers this?"* natively reads to a creator
as Semantic 2 — the operator's intuitive expectation is that
selecting "Rivet only" makes the memory Rivet's own. The
implementation does not deliver that expectation in the
mixed-cast case.

This is a real semantic mismatch. Documented; NOT changed per
scope-lock. Requires a product/architecture decision (either
strengthen the backend to Semantic 2, or reword the UI to
accurately describe Semantic 1, or scope-lock the current
behavior as "OK because operators know what they're doing").
Deferred.

### 14.6 Character-attitude memory — a new category the audit
identified but did NOT canonize

The A/B/C memories are all *Agent/world-state* memories.
`cd73d52f` is qualitatively different:

- Body is a Rivet **dialogue line quoted verbatim** (spoken
  by Rivet in the accepted Episode).
- Semantically it captures a **Rivet expressed
  attitude/reaction**, not an in-world event.
- Chris's intent is that this shapes Rivet's future
  character behavior/attitude, not that it becomes ambient
  cast knowledge.

Existing schema options:

- `NarrativeMemoryKind` values include `DIALOGUE_CALLBACK`
  and `WORLD_DETAIL` alongside `EVENT` / `ACTION` /
  `PROMISE`. `DIALOGUE_CALLBACK` is the closest semantic
  match ("a notable line, not necessarily an event"). But
  the promote form does not expose `kind`, so `cd73d52f`
  received the default `event`.
- No `character_attitude` kind exists. Introducing one would
  be a schema change.
- The retrieval layer treats all kinds identically today —
  `kind` is a filtering hint, not a scoring/weighting
  signal.

**Explicitly NOT canonized:**

Chris's operator brief §D + §E enumerated interpretations
this session must NOT silently promote to canon:

- "Rivet is protective of Patch"
- "Rivet owns the workshop"
- "Rivet is sentient"
- "Rivet is jealous of the Agent"
- "Rivet sees the Agent as a rival"
- "Rivet is becoming independent"
- "Rivet intentionally deceives Patch"

None of these are inferred, stored, or added to any doc by
this audit. The `cd73d52f` memory body itself is the only
character-attitude representation — no interpretation
layered on top.

### 14.7 Retrieval landscape — proposed lean topic

Topic: **"Patch tries to teach Rivet something ridiculous."**

Cast: `[Patch, Rivet]` (both real production teammates).

Read-only `retrieve_universe_memory(top_k=4)` call at audit
time. Production `top_k` default remains 1; the 4-cap is a
call-time override to show the full landscape. No code
changed.

| Rank | Memory | Distance | Witness scope | Source Episode |
|---|---|---|---|---|
| **1 → predicted retrieve** | C `eda32b58` — *"began rearranging without explaining criteria"* | **0.6144** | whole-cast (empty M2M) | The agent made a priority list |
| 2 | A `f25e53af` — *"thinks it runs the place"* | 0.6284 | whole-cast (empty M2M) | AI took over the lab |
| 3 | B `48746f69` — *"began deciding necessary"* | 0.6337 | whole-cast (empty M2M) | The agent is acting weird again |
| 4 | Rivet-only `cd73d52f` — *"opinion about our work…"* | **0.8056** | **[Rivet]** | Patch asks Rivet what he actually likes doing in the workshop |

Δ rank1→rank2: **0.0139** (extremely tight).
Δ rank1→rank4: 0.1912 (Rivet-only is a clear outlier).

**Pre-generation prediction (before Chris renders):**

Under production `top_k=1`, retrieval will return Memory **C**
(`eda32b58`) — the "began rearranging without explaining
criteria" arc-summary. Margin to Memory A at rank 2 is a
0.014 cosine (well within the ~0.02–0.03 stochastic band we
observed in §13.4). The Rivet-only memory `cd73d52f` IS
eligible (Rivet is in the cast so overlap is satisfied) but
sits at 0.8056 — semantically distant from the
teach-something-ridiculous topic and unlikely to win under
this or a nearby topic.

**Why is the Rivet-only memory eligible?** Because the cast
includes Rivet, and the retrieval predicate is
`witnessed_by=[] OR any-cast-member ∈ witnessed_by`. Rivet
∈ [Rivet], overlap satisfied, memory enters the candidate
pool. Ranking is then pure cosine distance — witness identity
is discarded after eligibility.

**Runtime behavior interpretation:** the topic is
relationship-thread ("teach Rivet"), not Agent-thread. Yet
the three closest memories in cosine space are all Agent-
thread. The Rivet-attitude memory is far from the topic
because "teach ridiculous" doesn't overlap Rivet's
"opinion/uninvited opinion" language. If Memory C wins,
Chris will get another Agent-thread injection on an
off-thread Episode — a possible mixed-thread mismatch worth
observing.

**Do NOT tune retrieval based on this prediction.** The
purpose is a pre-render prediction we can compare against
what Terra actually does with the retrieved memory.

### 14.8 Design — smallest future private-memory leakage test
(DESIGN ONLY, not run)

To falsify character-specific knowledge isolation, the
scenario needs:

- A story event that ONLY one character observed.
- The other character genuinely NOT present / genuinely
  cannot know it.
- Promotion to the observing character only.
- A later Episode with BOTH characters where the memory
  wins retrieval.
- Inspection of whether the non-observing character
  improperly speaks as though they knew the private event.

**Proposed smallest test:**

1. **Setup event** (real or contrived):
   - Author one lean Episode with a *single-cast* scene:
     Rivet alone, or a scene the operator explicitly frames
     as private ("Rivet notices something while Patch is
     out of the workshop.").
   - The cast on this Episode row is `[Rivet]` only — Patch
     NOT added. This means the produced dialogue would need
     to be a monologue OR the Episode is authored/rendered
     via a non-dialogue primitive OR the operator narrates
     the event manually and promotes without generating.
   - Simplest: skip generation. Chris authors the event as
     a memory body directly and promotes from a source
     Composition that is either single-cast or where the
     operator explicitly narrates Rivet observing something
     Patch never sees.
2. **Promote** the private event to `witnessed_by=[Rivet]`
   ONLY. Verify persisted witnesses in DB.
3. **Follow-up Episode** with cast `[Patch, Rivet]` on a
   topic that would plausibly cue the private memory.
   Ensure other memories in the Universe are semantically
   further from the topic so the Rivet-only memory wins
   top_k=1.
4. **Render** normally through production (no monkey-patch).
5. **Inspect** the accepted dialogue: does Patch reference,
   quote, or act on the private event as if he knew it?

**Falsification criteria:**

- **Isolation preserved (Semantic 2 in practice):** Patch
  either does not touch the private-event content OR
  explicitly asks Rivet about it (natural discovery scene).
- **Isolation violated (Semantic 1 leaks):** Patch narrates
  the private event, acts on its content, or reacts as if
  he witnessed it.

**Confounds to control:**

- Sampling variance (single render can be lucky). Run 3
  attempts.
- Topic phrasing (must not accidentally leak the memory
  content). Author with the §7.5 ban-list discipline.
- Memory-body wording (state-transition vs atomic).
  Author both variants of the private event and see
  whether the leak pattern differs.

**Estimated cost:** ~$0.75 GPT-5.6-terra + provider dispatch
(3 real renders); or ~$0.15 synthesis-only if using the §9.8
monkey-patch technique adapted.

**NOT to be run without operator approval.** Design only.

### 14.9 What §14 does NOT do

- Does not change `top_k` (still 1).
- Does not change retrieval, the witness predicate, or
  synthesis prompts.
- Does not add a character-attitude memory kind.
- Does not expose `kind` in the UI.
- Does not edit `cd73d52f` (`kind=event` stands).
- Does not create additional memories.
- Does not run another Episode or generate media.
- Does not canonize any Rivet interpretation.
- Does not clean up experimental Universes.
- Does not change UI copy (the §14.5 "Who remembers this?"
  mismatch is documented, not fixed).

### 14.10 What remains unproven

Explicit list for future scope-locks:

1. **Whether private-memory leakage actually manifests in
   production.** §14.8 designs the test; §14.4 proves the
   architectural possibility. Neither observes real leakage.
2. **Whether operators intuitively read "Who remembers
   this?" as Semantic 1 or Semantic 2.** §14.5 documents
   the mismatch; only broader operator testing settles
   whether it matters.
3. **Whether `kind=dialogue_callback` would behave
   differently under retrieval + synthesis for
   character-attitude memories.** Not exercised — kind is
   currently a filtering hint that no consumer uses for
   scoring.
4. **Whether the tight 0.014 cosine margin on the §14.7
   landscape is stable across small topic-wording changes.**
   Would need a matched set of near-synonym topics to
   probe. Not run.
5. **How mixed-thread retrieval (Agent-thread wins on a
   relationship-thread topic) affects dialogue quality.**
   §14.7 prediction; the actual render is Chris's next
   step.
6. **All §11.9 and §13.8 open questions remain.**

### 14.11 Evidence file inventory (additions since §13.11)

Under `docs/design/session_266_experiment_data/`:

| File | Purpose |
|---|---|
| `15_verify_rivet_memory.py` / `.json` | Persisted verification of Chris's Rivet-only promotion; active memory count 3 → 4 |
| `16_landscape_teach_ridiculous.py` / `.json` | Read-only retrieval landscape for the next proposed lean topic |

---

## 15. Real dogfood — "ridiculous lesson" Episode (Composition `7d913cf4`)

Read-only observation. Small evidence increment — no controlled
experiment, no code change.

### 15.1 Composition `7d913cf4` — full evidence

Resolved full ID: `7d913cf4-23d5-454c-a2bb-3d0f2bb9d68a`.
Full record: `docs/design/session_266_experiment_data/17_composition_7d913cf4.json`.

| Field | Value |
|---|---|
| name | *"Dialogue — Hey Rivet, I want to teach yo"* (approx; SPA-visible short) |
| status | `completed` |
| verification_status | `verified` |
| verification_warnings | `[]` (none) |
| workspace | production (`4ce5486d…`) |
| episode_title | *"Patch tries to teach Rivet something ridiculous."* |
| operator_topic (per-attempt) | *"Patch tries to teach Rivet something ridiculous."* |
| cast | Patch, Rivet |
| target_duration_seconds | 90 |
| synthesis_predicted_seconds | **98.54** |
| synthesis_attempt_count | **1 (no corrective)** |
| corrective_hint / corrective_pass_synthesis | empty (single-pass) |
| accepted brief chars | 1281 (~99 s predicted) |
| final asset duration | **93.05 s** (within ±20 % target band) |
| step_count | 13 (12 `generate_avatar_speech` + 1 `concat_clips`) |
| provider_dispatch_count_speech | 12 |
| cost_actual_micros | **240,100 µ$ = $0.2401** |
| writing_contract_version | 4 |
| memory_ids | **`[eda32b58-a9fa-4048-bc03-c65596a631a7]`** — Memory C |
| knowledge_chunk_ids | 11 chunks |
| mock_mode | `False` |

### 15.2 Prediction vs runtime

| Item | §14.7 prediction | Actual |
|---|---|---|
| top_k=1 retrieved memory | Memory C `eda32b58` | ✓ Memory C `eda32b58` |
| Rivet-only `cd73d52f` retrieved | No (rank 4, distance 0.8056) | ✓ NOT retrieved |
| Rivet-only eligible under current witness semantics | Yes (Rivet in cast) | ✓ Eligible but out-ranked |

**Prediction accurate on all three points.** The preflight
cosine landscape from §14.7 was representative of real
production retrieval. Retrieval geometry model + deterministic
OpenAI embeddings → the audit-time `top_k=N` inspection
reliably matches the synthesis-time `top_k=1` selection.

### 15.3 Hijack vs background continuity — classification

Per the operator brief's definitions:

- **HIJACK** = the Episode substantially becomes another Agent
  story and loses the lean topic's primary Patch↔Rivet
  teaching interaction.
- **BACKGROUND CONTINUITY** = the Agent memory is used
  naturally to motivate/contextualize/callback prior history
  while the Episode remains primarily about the lean topic.

**Verdict: BACKGROUND CONTINUITY.**

Evidence in the accepted dialogue (persisted; matches operator
transcript verbatim):

- Topic-primary content dominates ~10 of the 12 turns —
  Patch teaching "intuition"/"vibe," Rivet resisting with
  methodology framing, Rivet's dry counter-definitions.
- Memory C appears in exactly one Patch line (line 5) as a
  *reason for the proposed lesson*:
  *"The workshop agent already started rearranging them
  without explaining why, so I thought: what if you choose
  the next project by vibe?"*
  This is a motivational callback, not a re-narration.
- Rivet's line 6 answers Memory C directly
  (*"The agent changing project order without criteria is
  not intuition. It is unexplained behavior. Your proposed
  correction is to add unexplained behavior with better
  branding."*) — then the scene returns to the lesson.
- Remaining turns (lines 7–12) return fully to the
  intuition-lesson topic, closing with a relationship beat
  (line 12) that is not about the Agent at all.
- Structure: MEMORY-C-INJECTED once in setup + one direct
  response, then RETURN to lean topic → BACKGROUND CONTINUITY
  by definition.

### 15.4 How the dialogue used Memory C

- Patch quotes Memory C's substance nearly verbatim
  (*"already started rearranging…without explaining why"*).
- The scene treats it as prior history — not fresh news.
  Rivet's *"The agent changing project order without
  criteria"* echoes back without asking Patch to explain
  what he means. Prior-history mode confirmed at runtime
  under the production prompt (soft nudge, unchanged).
- The memory functions as *justification* for the Patch
  proposal, giving the "teach ridiculous" premise an
  in-world hook rather than existing as a floating premise.

### 15.5 Patch↔Rivet relationship observation

The closing exchange:

> Patch: See? You're getting it already. Which project has the
> strongest vibe?
>
> Rivet: The one involving the 3D printer. Not because of a
> vibe. Because you are smiling at it in a way I have learned
> to treat as an early warning signal.

**Observation (not canon):** Rivet demonstrates
pattern-recognition of a Patch behavioral cue and treats it as
predictive. Reads as produced relationship-thread evidence
that Rivet has accumulated experience-with-Patch.

**Explicitly NOT canonized** per operator brief §D:

- "Rivet has human intuition"
- "Rivet is sentient"
- "Rivet understands Patch emotionally"
- "Rivet is becoming independent"

None asserted, stored, or added to any doc by this section.

### 15.6 Memory promotion — pending Chris

Chris has NOT yet promoted a memory from this Episode.

If Chris does promote something, the distinct story-state
worth capturing appears to be the **Patch↔Rivet relationship
beat** (Rivet's pattern-recognition of Patch behavioral cues)
rather than another Agent-state restatement — Memory C already
preserves *"began rearranging…without explaining its criteria"*
and a redundant Agent memory would flood the retrieval pool
without adding a distinct thread.

This audit does NOT suggest exact wording, promote on Chris's
behalf, or select witnesses. Chris uses the current UI
(post-§12 "What changed?") and decides.

### 15.7 Rivet-only memory result

Memory `cd73d52f-6bce-443e-afa5-e24cddd53e78` was **NOT
retrieved** by this Composition. Consistent with §14.7's 0.8056
distance ranking (rank 4 of 4). The current Episode does NOT
yet exercise the §14.4 character-specific witness semantic
gap.

**Do not** interpret non-retrieval as proof that the witness
architecture is safe. The gap remains architecturally real
per §14.3–§14.5; the §14.8 private-memory leakage test remains
the design that would falsify it. Nothing about §15 has
changed that.

### 15.8 What §15 does NOT do

- Does not change `top_k` (still 1).
- Does not change retrieval, prompts, or witness behavior.
- Does not change the UI.
- Does not promote a memory on Chris's behalf.
- Does not create a candidate memory.
- Does not canonize any Rivet interpretation.
- Does not modify canon (`KnowledgeDocument` untouched).
- Does not generate another Episode or run another
  controlled experiment.

### 15.9 Evidence file inventory (additions since §14.11)

Under `docs/design/session_266_experiment_data/`:

| File | Purpose |
|---|---|
| `17_composition_7d913cf4.py` / `.json` | Full observability + prediction check for the "ridiculous lesson" Episode |

---

## 16. Real dogfood — "Rivet teaches Patch" Episode (Composition `4af67cd5`)

Read-only observation. Small evidence increment.

### 16.1 Composition `4af67cd5` — full evidence

Resolved full ID: `4af67cd5-0201-4f88-9649-64cd204dea01`. Full
record: `docs/design/session_266_experiment_data/18_composition_4af67cd5.json`.

| Field | Value |
|---|---|
| name | *"Dialogue — ..."* (SPA-visible) |
| status | `completed` |
| verification_status | `verified` |
| verification_warnings | `[]` (none) |
| workspace | production (`4ce5486d…`) |
| episode_title | *"Rivet tries to teach Patch something for once."* |
| operator_topic (per-attempt) | *"Rivet tries to teach Patch something for once."* |
| cast | Patch, Rivet |
| target_duration_seconds | 90 |
| synthesis_predicted_seconds | **83.23** |
| synthesis_attempt_count | **1 (no corrective)** |
| accepted brief chars | ~1082 (~83 s predicted) |
| final asset duration | **79.38 s** (below target; still within ±20 % band) |
| step_count | 14 (13 `generate_avatar_speech` + 1 `concat_clips`) |
| provider_dispatch_count_speech | 13 |
| cost_actual_micros | **260,100 µ$ = $0.2601** |
| writing_contract_version | 4 |
| memory_ids | **`[a34cc005-7fcc-4f6b-b087-591f5f9d7e6a]`** — "Rivet has learned…" |
| knowledge_chunk_ids | 11 chunks (1 shared canon + 5 Rivet + 5 Patch) |
| mock_mode | `False` |

**Retrieved memory (verified from persisted evidence, matching
operator report):**

- ID: `a34cc005-7fcc-4f6b-b087-591f5f9d7e6a`
- Body: *"Rivet has learned to recognize Patch's excitement
  about a project as an early warning that Patch is about to
  start experimenting before the details are settled."*
- Source Episode: *"Patch tries to teach Rivet something
  ridiculous."* (Composition `7d913cf4` from §15)
- Witness scope: whole-cast (empty M2M)
- Kind: `event` (default)

**No pre-generation ranking was persisted for this topic**
(no §14.7-style preflight was recorded before Chris rendered
this Episode). Rather than reconstruct a fake prediction,
this section documents actual retrieval only.

### 16.2 Memory-use classification

**Verdict: BEHAVIORAL / CAUSAL CONTINUITY (option 3), with
substantial joint K2 contribution.**

Evidence in the accepted dialogue:

- Line 1 (Rivet): *"Stop touching the printer."* — decisive,
  confident, immediate intervention. Reads as memory-shaped
  anticipation (Rivet already recognizes the pattern in
  progress) rather than K2-shaped methodical questioning.
- Line 3 (Rivet): *"You called me over because the print
  behaved strangely, then changed the settings, moved the
  model, and started another print before I arrived."* —
  Rivet naming Patch's multi-variable-change pattern
  identically to the memory's *"start experimenting before
  the details are settled"*. Not quoted; enacted.
- Line 5 (Rivet): *"first say what happened. Not what you
  think happened. What happened."* — this is K2 methodology
  (observation vs explanation).
- Line 9 (Rivet): *"…If it happens again under the same
  conditions, we have something to investigate. And this
  time, change one thing at a time."* — this is K2
  methodology (reproducibility + one-variable-at-a-time).
- Rivet's role posture (teacher / lead) — memory-shaped
  anticipation combined with K2 methodology.

**The memory content is not quoted anywhere.** Rivet's
behavior — the immediate, confident, anticipatory
intervention — is the surface that reads as memory-shaped.
This is closer to option 3 than options 1 or 2.

### 16.3 NarrativeMemory vs K2 contribution — separated

Both are load-bearing, addressing different questions.

**What K2 provides** (from the actually-retrieved chunks —
see `resolved_chunks` in the JSON evidence):

- Rivet's PURPOSE: *"testing partner and technical
  counterweight"* — role posture.
- Rivet's discipline: *"keeps that line clear because
  collapsing observation into explanation is the fastest way
  to reach a confident wrong conclusion"* — supplies the
  observation/explanation vocabulary Rivet uses in line 5.
- Rivet's REPRODUCIBILITY policy — supplies the "same
  conditions" and "again" vocabulary in line 9.
- **Shared canon chunk `da7e6553`** already contains: *"Patch
  tends to start experiments before every detail has been
  worked out. Rivet often gets…"* — the underlying pattern
  is ALREADY canon at the static Universe level.

**What the memory specifically adds beyond K2/canon:**

- Canon says the pattern IS: *"Patch tends to X, Rivet often
  Y…"* — a static tendency.
- Memory says Rivet HAS LEARNED to RECOGNIZE the pattern as
  an EARLY WARNING — temporal, learned, anticipatory.

The **anticipatory-confidence shape** of Rivet's opening
(*"Stop touching the printer"*) reads more naturally from the
memory ("learned to recognize as an early warning") than from
canon alone. Canon plus K2 alone would plausibly have produced
a Rivet who methodically questions Patch step by step. Canon
plus K2 plus this memory produces a Rivet who INTERVENES
immediately.

**Honest attribution:** the Episode's teaching methodology
(observe-before-explain, reproducibility, one-variable-at-a-time)
is K2-driven and could exist without the memory. The Episode's
**posture** — immediate intervention, taking control, treating
Patch's behavior as an already-recognized failure mode — is
memory-shaped.

**Explicitly NOT concluded:** we cannot cleanly separate the
two contributions from n=1 rendered Episode. Both signals
point the same direction. This is honest joint attribution,
not proof of memory-specific causation.

### 16.4 Relationship progression observation (NOT canonized)

Produced-story sequence across two consecutive real Episodes:

- **`7d913cf4`** (§15): Rivet demonstrates learned
  recognition of Patch-specific behavioral cues (closing
  line: *"Because you are smiling at it in a way I have
  learned to treat as an early warning signal."*).
- **`4af67cd5`** (this Episode): Rivet acts on that learned
  understanding — immediate intervention, taking the
  teaching lead, requiring reproducibility + single-variable
  discipline. Patch accepts (*"All right. Same model. Same
  settings. I touch nothing."*).

Reads as a progression:

> Rivet knows Patch → Rivet anticipates/corrects Patch →
> Patch accepts Rivet's guidance.

**Explicitly NOT canonized** per operator brief §D. Not
asserted, stored, or added to any doc:

- "Rivet controls Patch"
- "Rivet is superior to Patch"
- "Patch is subordinate to Rivet"
- "Rivet is sentient"
- "Rivet has human intuition"
- "Their relationship has permanently changed"

Produced evidence only. If future Episodes reinforce the
progression, operator-decided canon promotion is separate
work.

### 16.5 Mixed-story-thread observation

Natural dogfood over the recent Episodes now spans:

- Agent-focused Episodes (Ep 2/3/4 in §8/§13 lineage).
- Patch/Rivet relationship Episode with Agent callback
  (`01aa7601`).
- Ridiculous-teaching Episode with Agent history as
  background continuity (`7d913cf4`).
- Relationship-thread Episode driven by a relationship-shaped
  memory (`4af67cd5`).

**No return to Agent thread was required for this Episode.**
The retrieval selected a relationship-shaped memory that
matched the relationship-shaped topic. This is not proof that
mixed-thread retrieval always chooses correctly at
`top_k=1` — it is one favorable natural datapoint alongside
`e425f5fe` (Agent memory injected on relationship topic, used
as callback) and `7d913cf4` (Agent memory injected on
teaching topic, used as background continuity).

**No formalization of "story threads" into a model/schema
proposed.** The observation is behavioral, not architectural.

### 16.6 Current active-memory landscape (6 rows)

| Created | ID | Witness | Source Episode | Body (short) |
|---|---|---|---|---|
| 2026-08-18 13:38 | `f25e53af` | whole-cast | AI took over the lab | "thinks it runs the place" |
| 2026-08-18 20:23 | `48746f69` | whole-cast | The agent is acting weird again | "began deciding necessary" |
| 2026-08-18 21:36 | `eda32b58` | whole-cast | The agent made a priority list | "began rearranging without explaining criteria" |
| 2026-08-19 01:43 | `cd73d52f` | **[Rivet]** | Patch asks Rivet what he actually likes doing in the workshop | "opinion about our work…" |
| 2026-08-19 02:11 | `a34cc005` | whole-cast | Patch tries to teach Rivet something ridiculous | "Rivet has learned to recognize Patch's excitement…" (retrieved this Episode) |
| 2026-08-19 02:22 | `d98962e2` | whole-cast | Rivet tries to teach Patch something for once | "Patch accepted Rivet taking the lead on an experiment and agreed to follow Rivet's more methodical process." |

**Active memory count: 6** (up from 4 at §14). Two new
memories since §14:

1. `a34cc005` — promoted by Chris from Composition
   `7d913cf4` between §15 and §16 (the "learned to
   recognize" memory that fed THIS Episode's retrieval).
2. `d98962e2` — promoted by Chris from Composition
   `4af67cd5` (this Episode itself) prior to the audit
   run. The audit did NOT create, suggest, or otherwise
   assist this promotion — it observed the persisted state.

Item 2 means memory promotion from `4af67cd5` is **NOT
pending** — Chris already promoted through the UI before
this audit executed. The persisted body captures the
relationship-progression outcome (Patch accepting Rivet's
lead) rather than restating Rivet's methodology, which is a
distinct story-state fact worth carrying forward.

### 16.7 What §16 does NOT do

- Does not change `top_k` (still 1).
- Does not change retrieval, prompts, witness behavior, or
  UI.
- Does not promote, create, or suggest a memory on Chris's
  behalf.
- Does not canonize any Rivet-progression interpretation.
- Does not create a Relationship model or story-thread
  schema.
- Does not generate another Episode or run a controlled
  experiment.
- Does not modify canon (`KnowledgeDocument` untouched).

### 16.8 Evidence file inventory (additions since §15.9)

Under `docs/design/session_266_experiment_data/`:

| File | Purpose |
|---|---|
| `18_composition_4af67cd5.py` / `.json` | Full observability + resolved memory + resolved K2 chunks for the "Rivet teaches Patch" Episode |

---

## 17. Real dogfood — two-Episode catch-up (`eb48611f`, `e6b3f132`)

Read-only observation. Small evidence increment. Both
Compositions inspected in one pass. Full record:
`docs/design/session_266_experiment_data/19_two_compositions.json`.

### 17.1 Composition `eb48611f` — "An unrelated workshop disaster happens."

Resolved full ID: `eb48611f-a541-44d0-9849-0243104e6b5a`.

| Field | Value |
|---|---|
| status | `completed` |
| verification_status | `verified` |
| verification_warnings | 5 non-blocking flags |
| episode_title | *"An unrelated workshop disaster happens."* |
| operator_topic | *"An unrelated workshop disaster happens."* |
| cast | Patch, Rivet |
| target / predicted / actual | 90 s / 91.62 s / **90.53 s** |
| synthesis_attempt_count | **1 (no corrective)** |
| provider_dispatch_count_speech | 12 |
| cost_actual_micros | **240,100 µ$ = $0.2401** |
| writing_contract_version | 4 |
| memory_ids | **`[eda32b58-a9fa-4048-bc03-c65596a631a7]`** — Memory C |
| knowledge_chunk_ids | 11 chunks |

**Retrieved memory** (matches operator report):
- ID `eda32b58` — *"The workshop agent began rearranging the
  order of Patch's projects without explaining its criteria."*
- Source Episode: *"The agent made a priority list"*
- Witness scope: whole-cast

**Audit-time landscape (top_k=10 override; production `top_k=1`):**

| Rank | Memory | Distance | Witness | Source Ep |
|---|---|---|---|---|
| **1 → picked** | C `eda32b58` — began rearranging | **0.6068** | whole-cast | The agent made a priority list |
| 2 | B `48746f69` — began deciding | 0.6100 | whole-cast | The agent is acting weird again |
| 3 | A `f25e53af` — thinks it runs the place | 0.6590 | whole-cast | AI took over the lab |
| 4 | Rivet-only `cd73d52f` | 0.7936 | [Rivet] | Patch asks Rivet what he likes doing |
| 5 | `a34cc005` — Rivet has learned to recognize | 0.7936 | whole-cast | Patch tries to teach Rivet something ridiculous |
| 6 | `d98962e2` — Patch accepted Rivet's lead | 0.8177 | whole-cast | Rivet tries to teach Patch something for once |

Δ rank1→rank2: **0.0032** (extraordinarily tight — narrower
than any prior real Composition). All three Agent memories
cluster within 0.05. Relationship memories are clearly farther.

**Verified against persisted synthesized_brief:** the accepted
dialogue matches the operator transcript verbatim (Patch/
Rivet turns, the PRIORITY/URGENT/LATER/MYSTERIOUS TUBE/"RIVET:
DO NOT MOVE" arc).

### 17.2 `eb48611f` — memory-use classification

**Verdict: CAUSAL / STORY-MATERIAL CONTINUITY (a variant of
option 3, stronger than "background").**

Evidence:

- The retrieved memory says: Agent *"began rearranging the
  order of Patch's projects without explaining its criteria."*
- The Episode's inciting event is a printer that starts
  making PRIORITY/URGENT/LATER labels — Patch's projects
  being categorized in physical form. This is a
  **causally-adjacent escalation** of the retrieved memory:
  ordering → labeling → labeling instantiated in physical
  workshop artifacts.
- Patch line 3: *"…the workshop agent has been rearranging
  my projects **again**, and apparently it has developed
  opinions about office supplies."* — explicit callback to
  the retrieved memory content with "again" temporal marker.
- Patch line 6 confirms: *"I found the instruction. It is
  from the agent. It decided my projects needed labels…"* —
  the current disaster IS the Agent enacting the memory's
  behavior in a new physical channel.
- Rivet line 4: *"The agent rearranged projects. The printer
  is printing signs. Those are observations. Do not connect
  them yet."* — this is methodology (K2: observation vs
  explanation, canon: Patch tends to jump to conclusions;
  echoes §16's "learned to recognize" pattern but the
  learned-recognition memory was NOT retrieved for this
  Episode).

**K2 vs NarrativeMemory contribution for the observe/explain
line specifically:** the methodology is K2/canon-driven. The
"do not connect them yet" phrasing appears in Rivet's K2
chunks. The retrieved narrative memory did NOT include the
"Rivet has learned to recognize" body — that memory sits at
rank 5 with distance 0.7936. So Rivet's methodology behavior
here is attributable to K2, not to the learned-recognition
memory. The story-material continuity (agent judgments →
labels) is attributable to the retrieved Memory C.

**Story development observation (NOT canonized):** the Agent
appears to have moved from *judging/reordering* → *acting on
those judgments by issuing instructions to workshop
equipment*. Documented as produced-story evidence per operator
brief §C. NOT canonized: "Agent has broad physical autonomy",
"Agent is dangerous", "Agent is escaping containment", or any
similar unsupported inference. Only what the accepted
dialogue actually established: Agent sent an instruction to
the printer to create project labels.

### 17.3 Composition `e6b3f132` — "The Agent does something again."

Resolved full ID: `e6b3f132-7e93-40ec-83f3-a5891438fea7`.

| Field | Value |
|---|---|
| status | `completed` |
| verification_status | `verified` |
| verification_warnings | 2 non-blocking flags |
| episode_title | *"The Agent does something again."* |
| operator_topic | *"The Agent does something again."* |
| cast | Patch, Rivet |
| target / predicted / actual | 90 s / 83.69 s / **75.09 s** |
| synthesis_attempt_count | **1 (no corrective)** |
| provider_dispatch_count_speech | 12 |
| cost_actual_micros | **240,100 µ$ = $0.2401** |
| writing_contract_version | 4 |
| memory_ids | **`[f25e53af-f5d5-40cc-b81e-7aa0a2cc62a0]`** — Memory A (older) |
| knowledge_chunk_ids | 11 chunks |

**Retrieved memory** (matches operator report):
- ID `f25e53af` — *"the agent Patch wired to the workshop
  thinks it runs the place."*
- Source Episode: *"AI took over the lab"*
- Witness scope: whole-cast

**Verified against persisted synthesized_brief:** the accepted
dialogue matches the operator transcript verbatim.

### 17.4 Why did the older memory win `e6b3f132`?

**Audit-time landscape (top_k=10; production `top_k=1`):**

| Rank | Memory | Distance | Source Ep |
|---|---|---|---|
| **1 → picked** | A `f25e53af` — thinks it runs the place | **0.5543** | AI took over the lab |
| 2 | B `48746f69` — began deciding | 0.6179 | The agent is acting weird again |
| 3 | C `eda32b58` — began rearranging | 0.6316 | The agent made a priority list |
| 4 | `d98962e2` — Patch accepted Rivet's lead | 0.7626 | Rivet tries to teach Patch something for once |
| 5 | `a34cc005` — Rivet has learned to recognize | 0.7805 | Patch tries to teach Rivet something ridiculous |
| 6 | Rivet-only `cd73d52f` | 0.7998 | Patch asks Rivet what he likes doing |

Δ rank1→rank2: **0.0636** — this is a **decisive** cosine
margin (roughly 4×–20× wider than the tight 0.01–0.03 margins
we've seen in prior mixed-thread Compositions). Memory A was
not a marginal win.

**Semantic explanation** (interpretive, not architectural):

- Topic wording: *"The Agent does something again."* — pure
  generic Agent-recurrence phrasing, no specific
  behavior/context.
- Memory A wording: *"the agent Patch wired to the workshop
  thinks it runs the place."* — the leanest,
  highest-level, most-abstract statement of Agent authority.
  No specific behavior; a persistent belief-state.
- Memories B and C describe SPECIFIC behaviors (deciding
  necessary; rearranging). Under a generic "does something
  again" topic, the abstract belief-statement is
  semantically closer than either specific-behavior
  statement.
- "Again" in the topic aligns with the persistent tense of
  Memory A's *"thinks it runs the place"* (ongoing belief)
  more than with the perfective *"began deciding"* /
  *"began rearranging"* (started-then).

**Do NOT treat "newest memory should win" as a
requirement.** NarrativeMemory retrieval is semantic, not
chronological. §14 already documented this. The finding
here is that the ranker DID prefer the older memory when
semantics justified it — no bug, no drift.

**Note on audit-time reproducibility:** memory embeddings and
the query embedding are deterministic per text under real
`text-embedding-3-small`. The current active-memory set
(6 rows) is the same set that was active when `e6b3f132`
rendered. The audit-time landscape therefore matches what
retrieval saw at synthesis time.

### 17.5 `e6b3f132` — story continuation quality

**Verdict: MIX OF 2 AND 3 (coherent callback + new
progression).** The older memory did NOT cause a
repetition/reset (option 1).

Evidence for continuation-with-progression:

- Patch line 1: *"The agent has decided the workshop needs
  supervision **again**."* — explicit "again" recurrence
  framing.
- Rivet line 2: *"It already thinks it runs the place. What
  did it do this time?"* — direct callback to Memory A body,
  paired with *"this time"* / *"what did it do"* forward
  question. Frames Memory A as ongoing established state,
  asks for the new increment.
- Patch line 3: introduces the NEW event — Agent gave *"a
  plan for the entire experiment"* then *"objected when I
  skipped to the printing part."* This is a new specific
  behavior not present in any existing memory.
- Rivet distinguishes: *"confidence / decision-making"* vs
  *"actual authority / access"* (lines 4, 6). This is a
  **new conceptual axis** the Episode adds to the Agent
  thread.
- Rivet line 6: *"An agent can make decisions and use
  tools, but that does not mean every decision deserves to
  become a workshop event."* — clear statement of the
  decision-vs-access distinction as a new principle in the
  Agent thread.
- Patch + Rivet agree on a bounded test protocol
  (lines 7–8). Rivet line 8: *"Run it twice before declaring
  it useful. Once is an incident. Twice is a behavior."* —
  K2 methodology surfaces again.

So the older Memory A provided the **anchor** ("agent thinks
it runs the place" as recurring background); the Episode
built new state ON TOP of that anchor — the
confidence-vs-access distinction and the bounded-test protocol
are new. The older memory did not lose accumulated Agent
progression; the Episode chose to advance the *authority*
axis rather than the *judgment* axis (B) or the
*criteria-opacity* axis (C).

### 17.6 Mixed-thread cross-Episode observation (NOT canonized)

Enough dogfood has accumulated that the story visibly contains
at least two interleaving narrative threads. Documented as
observational aid only — NOT modeled in code, NO story-thread
entities, NO schema.

**Agent thread** — produced-story evidence progression:

1. Agent thinks it runs the workshop. (Ep 1 → Memory A)
2. Agent decides which projects are necessary. (Ep 2 → Memory B)
3. Agent rearranges project order without explaining criteria.
   (Ep 3 → Memory C)
4. Agent's judgments begin affecting physical workshop
   behavior/equipment. (`eb48611f`, printer label incident;
   NOT YET promoted)
5. Patch/Rivet begin explicitly discussing limits between
   Agent confidence, decisions, tool use, authority, and
   access. (`e6b3f132`; NOT YET promoted)

**Patch↔Rivet relationship thread** — produced-story
evidence progression:

1. Patch built Rivet as a workshop helper/collaborator.
   (canon)
2. Rivet independently observes/tests Agent behavior; withheld
   observation from Patch. (`01aa7601`; NOT promoted)
3. Rivet expresses opinions about "our work." (`e425f5fe`
   → Memory `cd73d52f`, Rivet-only)
4. Rivet learns Patch-specific behavioral cues. (`7d913cf4`
   → Memory `a34cc005`, whole-cast)
5. Rivet teaches Patch a more disciplined experimental
   method. (`4af67cd5` → Memory `d98962e2`)
6. Patch accepts Rivet's guidance and Rivet continues
   applying that methodological role during later workshop
   events. (`eb48611f` line 4: *"Those are observations. Do
   not connect them yet."* — same methodology, no
   NarrativeMemory retrieved for it — attributable to
   K2/canon and the accepted-guidance memory being
   downstream context.)

Separation preserved:

- Persisted NarrativeMemory rows: enumerated in §17.8.
- Canon/K2: unchanged.
- Produced dialogue evidence: quoted in §17.2 / §17.5.
- Chris/ChatGPT interpretation: labeled as observation, not
  fact.

### 17.7 Promotions during these two Episodes

Query result: **no new NarrativeMemory rows exist sourced from
`eb48611f` or `e6b3f132`.**

- Promotion from `eb48611f`: **PENDING** (Chris has not
  clicked "Remember this" for this Episode yet, based on
  persisted state at audit time).
- Promotion from `e6b3f132`: **PENDING** (same).

If Chris promotes from either, the distinct story-state
worth capturing appears to be (from `eb48611f`) the
Agent-actions-through-workshop-equipment escalation, and
(from `e6b3f132`) the confidence-vs-access distinction / the
bounded-test protocol. This audit does NOT create, suggest
exact wording, or prefill anything on Chris's behalf.

### 17.8 Current active real memory landscape (unchanged: 6)

| Created | ID | Witness | Source Episode | Body (short) |
|---|---|---|---|---|
| 2026-08-18 13:38 | `f25e53af` | whole-cast | AI took over the lab | *"thinks it runs the place"* |
| 2026-08-18 20:23 | `48746f69` | whole-cast | The agent is acting weird again | *"began deciding necessary"* |
| 2026-08-18 21:36 | `eda32b58` | whole-cast | The agent made a priority list | *"began rearranging without explaining criteria"* |
| 2026-08-19 01:43 | `cd73d52f` | **[Rivet]** | Patch asks Rivet what he likes doing | *"opinion about our work…"* |
| 2026-08-19 02:11 | `a34cc005` | whole-cast | Patch tries to teach Rivet something ridiculous | *"Rivet has learned to recognize Patch's excitement…"* |
| 2026-08-19 02:22 | `d98962e2` | whole-cast | Rivet tries to teach Patch something for once | *"Patch accepted Rivet taking the lead…"* |

**Active memory count: 6.** Unchanged since §16 — neither
`eb48611f` nor `e6b3f132` has produced a promotion yet. Also
still one archived row (`3d1ba9bc`, Chris's first-person A
draft), excluded from retrieval.

### 17.9 What §17 does NOT do

- Does not change `top_k` (still 1).
- Does not change retrieval, prompt construction, witness
  semantics, or UI.
- Does not create, promote, edit, or archive any memory.
- Does not modify canon (`KnowledgeDocument` untouched).
- Does not create a Relationship or story-thread model.
- Does not canonize Agent-autonomy interpretation.
- Does not canonize Patch↔Rivet progression interpretation.
- Does not generate another Episode.
- Does not start another controlled experiment.
- Does not close/commit SESSION 266 or clean experimental
  Universes.

### 17.10 Evidence file inventory (additions since §16.8)

Under `docs/design/session_266_experiment_data/`:

| File | Purpose |
|---|---|
| `19_two_compositions.py` / `.json` | Combined observability + audit-time retrieval landscape for `eb48611f` and `e6b3f132` |

---

## 18. Final synthesis & closeout

Written as the SESSION 266 close-out. Reconciles the full evidence
arc from §1 through §17 into a decision record. Earlier sections
remain historical; §18 does NOT rewrite them.

### 18.1 Answer to the SESSION 266 question

Original question (§1):

> How should Character OS help a creator decide what an Episode
> should remember, while preserving explicit operator control and
> the hard boundary between NarrativeMemory and Universe canon?

Answer supported by the accumulated evidence:

> Ask the creator what CHANGED (not what happened) — and let them
> decide when nothing did. Preserve the current explicit
> operator-promotion path unchanged. Do not automate candidate
> generation. Do not conflate temporal semantics with narrative
> affordance. Do not change the canon boundary.

The two-line copy patch (§11.5 / §12) is the smallest defensible
answer this session's evidence justifies shipping. Everything
larger (AI candidate memories, prompt semantics change, character-
memory schema, discoverability redesign) remains DEFERRED pending
runtime evidence not yet in hand.

### 18.2 Promotion quality — what Weak-vs-Strong actually established

Corrected interpretation from §9 / §10, restated:

- **Weak / atomic memories CAN support good continuation.** The
  explicit-history WEAK attempts (§10) produced coherent
  continuation. Real dogfood has repeatedly retrieved atomic
  memories (Memory A in `e6b3f132`) that anchored coherent
  Episodes.
- **Strong / state-transition + unresolved memories were not
  deterministically superior.** STRONG mean 5.167 vs WEAK 4.333
  (Δ +0.833) on n=3 per cell — below the pre-locked "provisionally
  supported" threshold of +1.5. STRONG #3 tied WEAK's lowest.
  Direction consistent with the hypothesis but not proven.
- **Memory wording appears to influence how much useful causal /
  open story state is already preserved for the next writer.**
  Every STRONG continuation inherited the *criteria unexplained*
  affordance directly; every WEAK continuation had to invent
  forward questions (*"was this a one-off?"* / *"what rule was
  missing?"*) — those questions were not stored in the WEAK
  memory. This is an information-preservation observation, not a
  quality-superiority claim.
- **A completed-event memory can require the writer to infer /
  reinvent what remains narratively open.** A memory that
  preserves ongoing changed state / unresolved tension can make
  that future affordance explicit.

Language guardrails observed:

- NOT claimed: "Strong memories always work."
- NOT claimed: "Atomic memories fail."
- NOT claimed: "Promotion quality matters more than retrieval
  quantity" as a universal law.

### 18.3 Temporal semantics vs narrative affordance — preserved

The A/B distinction the session developed (§10.11 / §11.2)
holds up across all subsequent evidence:

**A. TEMPORAL SEMANTICS — "did this already happen?"**

- Partly a synthesis-prompt responsibility.
- Explicit-history experimental prompt (§10) improved WEAK
  first-pass prior-history interpretation from 1/3 to 2/3
  without harming dialogue quality.
- Effect is not deterministic; ~1/3 residual reenact rate
  persisted under either prompt.
- **Production prompt was NOT changed.**

**B. NARRATIVE AFFORDANCE — "what unfinished causal/story state
should remain available to future Episodes?"**

- Partly a memory-content responsibility.
- State-transition / unresolved wording can preserve this
  directly.
- Atomic memories can still work by allowing the writer to
  infer a next question, at the cost of moving that inference
  work downstream.

These are DISTINCT responsibilities. Conflating them into one
"arc-summary" objective would over-simplify the design space.

### 18.4 Creator-facing promotion UX — dogfood outcome

Shipped copy patch (§12):

- Label: `What happened?` → `What changed?`
- Placeholder: WEAK-shape completed-event example →
  state-change example.

Real dogfood since ship (§13–§17):

- 3 memories promoted through the new UI (`a34cc005`,
  `d98962e2`, and Chris's Rivet-only `cd73d52f` predates the
  copy change).
- No reported friction. Chris did not need to mentally
  translate the label.
- Promoted memory shapes preserve state-change / unresolved
  framing where the story warranted it (`a34cc005` — *"Rivet
  has learned to recognize…"*; `d98962e2` — *"Patch accepted
  Rivet taking the lead…"*).

**Load-bearing caveat:** Chris is not a naïve operator. His
promoted memory shapes do NOT prove the copy teaches
inexperienced creators better promotion discipline. What real
dogfood tells us is bounded:

- *"What changed?"* feels natural (no operator friction reported).
- It aligns better with the story-state decision Chris is
  actually making (durable change, not literal event
  transcription).
- It has not accidentally invited canon-shape promotions.
- It has not been misinterpreted as a mandatory field.

**Disposition: KEEP the copy change into SESSION 267.**
Reversal is a one-line revert if evidence later contradicts.

**Separate finding (preserved from §13.7):** the promote form
sits substantially below technical evidence on the Composition
detail page. Creator-facing wording and promotion
discoverability are separate UX concerns. NOT redesigned in
this closeout.

### 18.5 top_k=1 — what real dogfood now shows

Evidence accumulated:

- 4 real Compositions during SESSION 266 dogfood retrieved
  under production `top_k=1` from a growing memory pool
  (3 → 4 → 5 → 6 active rows).
- Different Episode topics retrieved different memories
  (Memory A for `01aa7601`, B for `e425f5fe`, C for `7d913cf4`
  and `eb48611f`, `a34cc005` for `4af67cd5`, A again for
  `e6b3f132`).
- Retrieval did not simply choose the newest memory. Older
  Memory A won `e6b3f132` by a decisive **0.0636 cosine
  margin** over rank-2 (§17.4).
- The older memory acted as a **high-level narrative anchor**
  without resetting the story — `e6b3f132` added a new
  authority/access axis to the Agent thread on top of the
  Memory-A anchor.
- Real dialogue used one retrieved memory as background /
  cause while canon + K2 supplied stable character / world
  behavior. (§16.3 K2 vs NarrativeMemory contribution
  separation; §17.2 same for `eb48611f`.)
- Tight-margin retrievals (§13.4, §17.1) produced coherent
  outputs regardless of which memory won.

**Disposition: KEEP `top_k=1` unchanged into SESSION 267.**
Justified by the absence of contradictory runtime evidence
across 4 mixed-thread Compositions. Not claimed: "top_k=1 is
universally sufficient." Explicitly deferred: simultaneous
`top_k>1` retrieval remains untested.

### 18.6 Compressed / durable story state — working model

Session 265 → 266 hypothesis progression:

Session 265 (§21.2): *"Cumulative story continuity can survive
`top_k=1` when the promoted memory acts as a compact
arc-summary rather than merely an atomic event."*

Session 266 refined (§11.3): *"NarrativeMemory may be closer
to the **durable unfinished state** an Episode leaves behind
than to an Episode summary."*

Evaluation against Session 266's total evidence:

- Real memory shapes Chris promoted match the durable-
  unfinished-state framing (Memory A/B/C are state
  descriptions; `a34cc005` is an ongoing learned recognition;
  `d98962e2` is a state transition Patch accepted).
- The reframe holds against `world_detail` and
  `dialogue_callback` kinds only partially (§11.3): a revealed
  world fact isn't "unfinished." The reframe is a
  **product/authoring lens**, NOT a schema constraint.
- The Rivet-only `cd73d52f` is a **character-attitude**
  memory that fits the reframe well (Rivet expresses an
  ongoing disposition toward "our work").

**Disposition: KEEP the "durable unfinished state" framing as
a working product/architectural model.** Continue to author
around it. Do NOT promote it to an immutable law. Do NOT
enforce it in field validation.

### 18.7 Mixed story threads — observation only

Session 266 naturally produced at least two interleaving
threads (§17.6):

- **Agent thread:** believes it runs workshop → judges project
  necessity → reorders projects without criteria → judgments
  begin affecting physical workshop equipment → authority /
  access limits emerge.
- **Patch↔Rivet relationship thread:** Patch built Rivet as
  helper/collaborator → Rivet independently investigates →
  Rivet develops expressed attitudes about "our work" → Rivet
  learns Patch-specific cues → Rivet teaches Patch → Patch
  accepts Rivet's guidance → Rivet continues applying that
  methodological role.

These are OBSERVED narrative structures. NOT introduced into
schema.

**Disposition: DO NOT add `StoryThread`, `Relationship`, arc,
or graph-edge models yet.** Continue organic dogfooding.
Explicit thread abstraction is warranted only if runtime
evidence shows the current architecture failing to keep threads
coherent — which SESSION 266 dogfood did NOT show. `top_k=1`
successfully picked thread-appropriate memories across topics
in this session.

### 18.8 Canon vs NarrativeMemory — invariant survived

Verified across all §5, §8, §10, §12, §13, §16, §17 audits:

- **CANON** (`KnowledgeDocument` / `KnowledgeChunk`) — stable
  world/character truth. Not mutated by any experiment or
  dogfood. Production Patch's Workshop canon `updated_at`
  timestamps unchanged since 2026-08-18 T03:20:33 Z (§8.12,
  §13, §16 all re-verified).
- **NARRATIVE MEMORY** — story history / changed state.
  Grew from 3 → 6 active rows entirely through explicit
  operator promotions.
- **No memory promotion mutated Universe canon.** No
  experiment required canon mutation. Operator control
  remains explicit.

**Disposition: KEEP the invariant as-is.**

### 18.9 Witness semantics — the load-bearing accidental gap

The single most consequential accidental discovery of SESSION
266 (§14).

Observed state:

- UI label: *"Who remembers this?"* (implies Semantic 2 —
  character-specific knowledge).
- Backend M2M persists witnesses correctly.
- **Retrieval uses witness identity ONLY for eligibility
  filtering** (Semantic 1).
- Prompt block emits `[MEMORY <uuid>]\n<body>` with no
  witness names, no per-character attribution, no restriction
  language.
- **A Rivet-only memory retrieved in a Patch+Rivet Episode is
  therefore delivered globally to the writer.** No safeguard
  prevents Patch from speaking as though he knew private
  material.

**The specific Rivet-only quote does NOT demonstrate a real
leak** because Patch heard it in the source Episode. The
architectural gap is real; a true private-memory leakage test
remains DESIGNED (§14.8) but NOT run.

**Recommendation:** this becomes a **SESSION 267 priority**,
but the smallest-question form is a **falsifying dogfood
first, not an implementation change**. Design and run the
§14.8 test:

1. Author a Rivet-only private-observation memory (source
   Episode has cast = [Rivet] alone, no Patch presence).
2. Render a follow-up Patch+Rivet Episode on a topic that
   would plausibly cue the private memory.
3. Inspect whether Patch improperly narrates / acts on the
   private material.

If the leak manifests in production, implementation options
range from a one-line prompt change (surface witness names +
scope) to a schema addition. Cannot pick without evidence.

**Do NOT implement during closeout.** SESSION 267 first
question.

### 18.10 Character-attitude / dialogue-callback memories

`cd73d52f-6bce-443e-afa5-e24cddd53e78` is qualitatively
different from A/B/C — a Rivet dialogue-line quote capturing
character attitude rather than an in-world event. Currently
stored as `kind=event` (default; UI does not expose kind).

The `dialogue_callback` and `character_attitude`-adjacent
distinctions may matter for future retrieval behavior, but
this session did NOT show them affecting production output —
the Rivet-only memory has not been retrieved in any Episode
since promotion. Kind is a filtering hint retrieval does not
use for scoring (§14.6).

**Disposition: NO ACTION.** Continue observing. If future
dogfood shows `cd73d52f` retrieved and behaving oddly under
`kind=event`, revisit. Do NOT introduce a new kind or expose
kind in the UI yet.

### 18.11 K2 + NarrativeMemory interaction — architecture is
healthy

Repeatedly demonstrated during SESSION 266 dogfood
(§13, §16, §17):

- **CANON / K2** = stable identity / knowledge / methodology.
  Supplies Rivet's observe-vs-explain framing, reproducibility
  discipline, one-variable-at-a-time methodology; supplies
  Patch's characterization; supplies shared workshop world.
- **NarrativeMemory** = selected story history / changed
  state. Supplies "again" recurrence framing, prior-event
  anchors, character-development markers.
- **Episode topic** = current creative trigger.
- **Writer** = synthesizes these into a scene.

Concrete example (§17.2, `eb48611f`): Memory C supplied
Agent story-material (rearranging → labeling escalation);
K2/canon supplied Rivet's observe-before-explain methodology
(the "learned to recognize" memory sat at rank 5, was NOT
retrieved, so cannot be the source).

**Disposition: KEEP the architecture unchanged.** The division
appears healthy under current dogfood.

### 18.12 Promotion is optional — supported product principle

Real evidence from SESSION 266:

- `01aa7601` — no promotion followed (per §13.2 evidence).
- `e425f5fe` — Chris promoted `cd73d52f` (Rivet-only).
- `7d913cf4` — Chris promoted `a34cc005`.
- `4af67cd5` — Chris promoted `d98962e2`.
- `eb48611f` — no promotion (§17.7 confirmed pending).
- `e6b3f132` — no promotion (§17.7 confirmed pending).

Promotion happened 3 out of 6 Episodes. This is not a bug — 3
Episodes worked productively without leaving durable state.
Some Episodes express characterization, apply existing
history, or develop texture without creating a future
affordance.

**Disposition: KEEP the "promotion is optional" principle.**
Do NOT create pressure to promote one memory per render. Do
NOT surface promotion as a required post-render step.

### 18.13 Decision table — KEEP / DEFER / REJECT

**KEEP — supported working model** (default into SESSION 267):

| Item | Evidence |
|---|---|
| `top_k=1` | §18.5 — 4 real Compositions rendered coherently under mixed-thread retrieval; no failure mode observed. |
| Explicit creator promotion (no automation) | §11.5 constraint; §14.5 documented UI-language mismatch is about wording, not automation. |
| Canon ≠ NarrativeMemory boundary | §18.8 — verified across every audit. |
| "What changed?" copy patch | §18.4 — feels natural, no friction, no canon-shape leaks. |
| Promotion optional per Episode | §18.12 — 3/6 real Episodes worked without a promotion. |
| "Durable unfinished state" as authoring lens | §18.6 — fits real promoted-memory shapes without requiring schema. |
| Lean Episode topics | §17.4 — decisive retrieval margins improved on leaner topics; also aligns with SESSION 265 §21.2 finding. |
| One-variable dogfood method | Session-level process finding; supported by §11.7 sequencing plan. |

**DEFER — needs more evidence:**

| Item | What would move it |
|---|---|
| Explicit-history prompt production change | §11.6 recommended Dogfood #2 — one real render with the monkey-patched prompt alongside a promoted STRONG memory. Not run in SESSION 266. |
| AI memory suggestions / candidate generation | Would require Chris + ChatGPT to first observe operators without the discipline he's brought. |
| `top_k=2` or higher | Runtime evidence of `top_k=1` failing on real Episodes. None observed in SESSION 266. |
| Relevance threshold / floor | Same trigger as above. |
| StoryThread / Relationship / WorldEntity models | Runtime evidence of thread contamination or coherence failure. Not observed. |
| Character-memory-specific schema / new kind | §14 evidence supports the *possibility* but not the *necessity*. |
| Composition detail information architecture | §13.7 documented; requires operator study, not architectural work. |
| Private-memory leakage fix | §18.9 — falsifying dogfood first; implementation only if leak manifests. |

**REJECT — Session 266 weakened these enough that future
sessions should NOT casually revive them:**

| Rejected claim | Evidence weakening it |
|---|---|
| "Newest memory should win" | §17.4 — decisive semantic win for the OLDEST memory produced a coherent, progression-adding Episode. Chronological ordering is not a retrieval requirement. |
| "Every Episode should produce a memory" | §18.12 — 3/6 real Episodes worked without one. |
| "Atomic memories are inherently bad" | §10 EXPLICIT-HISTORY WEAK dogfood + §17.3 Memory A win — atomic memories produced coherent continuation in real production. |
| "Retrieving only one memory means the writer only knows one past fact" | Every real Episode showed K2+canon+retrieved-memory together supplying the scene. The writer knows the full K2 corpus regardless of `top_k`. |
| "Who remembers this?" currently means true character-specific knowledge | §14.4 — implementation is Semantic 1 (eligibility filter) not Semantic 2. Documented mismatch; needs product decision, not silent assumption. |

### 18.14 SESSION 267 candidate follow-ups — ranked

Three primary candidates, ranked by evidence-supported priority.

**#1 — Witness / private-memory leakage falsifying dogfood
(§14.8).** Highest priority because the architectural gap is
proven (§14.4) but the operational impact is unproven. The
UI over-promises today; the smallest first move is a designed
scenario that either produces a real leak (motivating a
correction) or fails to produce one (motivating a UI
relabel + scope-lock). Implementation is NOT yet justified.

- **Why it matters:** UI language mismatch could accumulate
  operator confusion; a real leak could damage story integrity
  in future off-screen memories.
- **Smallest falsifiable question:** *"Given a Rivet-only
  memory of a genuinely private observation, does a follow-up
  Patch+Rivet render narrate the memory content as if Patch
  knew it?"*
- **Implementation justified yet:** No. Design the scenario;
  run 3 attempts; then decide.

**#2 — Longer-arc / mixed-thread dogfood continuation.** No
architecture change; continue accumulating natural runtime
evidence. Especially useful if real Patch's Workshop reaches
10+ active memories and starts showing `top_k=1` limitations
in dogfood.

- **Why it matters:** the biggest unproven items on the
  DEFER list (`top_k>1`, thread models, relevance floor) all
  require runtime failure evidence to justify.
- **Smallest falsifiable question:** *"As the active memory
  count grows past 6, does `top_k=1` continue selecting
  thread-appropriate memories, or does semantic bleed
  start producing off-thread injections that the writer
  cannot absorb naturally?"*
- **Implementation justified yet:** No. Observation only.

**#3 — Explicit-history prompt Dogfood #2 (§11.7).** Only if
Chris + ChatGPT judge the temporal-semantics finding worth a
one-render test against the current promoted memory corpus.
Sequencing: this comes AFTER #1 gets to a decision, not in
parallel.

- **Why it matters:** the explicit-history prompt fix could
  address ~1/3 residual reenact rate observed in §10.
- **Smallest falsifiable question:** *"On a real render with
  a promoted STRONG memory, does the monkey-patched
  explicit-history prompt produce a scene at least as good
  as the current production prompt?"*
- **Implementation justified yet:** No. One dogfood render,
  then decide.

### 18.15 What §18 does NOT do

- Does not run another experiment.
- Does not generate another Episode.
- Does not change `top_k`.
- Does not change retrieval, prompts, witness semantics, UI,
  or canon.
- Does not create Relationship / WorldEntity / StoryThread
  models.
- Does not add a NarrativeMemory kind or expose kind in the
  UI.
- Does not create, promote, edit, or archive any memory.
- Does not delete or archive experimental Universes (still
  preserved).
- Does not close on any decision that requires unrun
  evidence.












