# SESSION 274 — Shared / Global Knowledge Characterization (Slice 1)

**Status:** READ-ONLY characterization. No code, copy, KD, spokesperson-assignment, or Universe-assignment changes performed. **No product decision made.**

**Slice 1 stop condition:** deliver mechanical truth table + live-data classification + UI-semantics audit + product-decision brief → **wait for Chris.**

**Author window:** SESSION 274 open → this doc.

**Origin question (SESSION 274 handoff §D):**
> What should shared / global knowledge mean as a product capability in Character OS, and what does the current implementation actually do across workspace, Universe, and character boundaries?

This document answers the second half of that question ("what does the current implementation actually do") and captures the operator-facing surface ("what does the UI currently imply"). It does **not** answer the first half ("what should it mean") — that is Chris's product decision, and this doc's role is to expose the decision space.

---

## §1. REPOSITORY / RUNTIME VERIFICATION

Verified at SESSION 274 open:

| Check | Evidence |
| --- | --- |
| `main == origin/main` | `git rev-parse HEAD` = `git rev-parse origin/main` = `0fda9ce135679aa2c94ce7bc4f2550c8c12fd7c3` |
| Working tree clean | `git status --short` empty at open |
| SESSION 273 CLOSEOUT SHA present | `git log --oneline` shows `7b95798 docs(session-273): §34-§38 CLOSEOUT + SESSION 274 handoff` in ancestry (HEAD is the SHA-record follow-up commit `0fda9ce`) |
| Django `:8010/admin/` | HTTP 302 |
| Media-engine `:8001/health` | `{"status":"ok","openai_mock":false,"runway_mock":false,"image_gen_mock":false,"any_mock":false,"llm_provider":"openai","llm_model":"gpt-4o-mini"}` |
| Vite `:5174/` | HTTP 200 |
| Celery `inspect ping` | `celery@Chriss-MacBook-Pro.local: OK / pong / 1 node online.` |
| Worker env drift | PIDs 26101 (Django), 12677 (media-engine uvicorn), 26630 (celery) grepped for `MOCK / EXPERIMENT / USE_MOCK` — zero matches |
| DB port | `DB_PORT=5434` from running Django env; used for all read-only shell probes below |

**No drift observed.** No corrective action taken.

---

## §2. FOUR-SCOPE MECHANICAL TRUTH TABLE

Character OS defines four mechanical knowledge scopes as combinations of two `KnowledgeDocument` fields:

- `KnowledgeDocument.universe` — nullable FK to `Universe`
- `KnowledgeDocument.spokespeople` — M2M to `Teammate` (through `KnowledgeDocumentSpokesperson`)

The four canonical classes:

| Class | `universe` | `spokespeople` | Colloquial name |
| --- | --- | --- | --- |
| **A** | `None` | empty | Workspace-shared (legacy) |
| **B** | `None` | `{A, …}` | Workspace character-specific (legacy) |
| **C** | `U` | empty | Universe-shared |
| **D** | `U` | `{A, …}` | Universe character-specific |

There is also an emergent sub-shape (**D-fullcast**) where `universe=U` and `spokespeople = every teammate in U`. Mechanically it is Class D, but the `retrieve_universe_canon` lane (§3) treats it as canon via a full-cast branch. Only one live example exists (`PATCH'S WORKSHOP — SHARED CANON`, §4).

### §2.1. Eligibility matrix — `retrieve_for_teammate`

The primary retrieval function is `retrieve_for_teammate(spokesperson, query, top_k=5)` at `shell/apps/embeddings/retrieval.py:159–226`. Its eligibility predicates (lines 194–220):

1. **Workspace filter (unconditional, lines 194–197):** `document__workspace = spokesperson.workspace` AND `document__is_active=True` AND `document__status="processed"`.
2. **Universe branch (lines 211–214):**
   - If `spokesperson.universe_id is None`: `document__universe__isnull=True`
   - Else: `document__universe_id = spokesperson.universe_id`
3. **Spokespeople M2M filter (lines 217–219):** `Q(document__spokespeople__isnull=True) | Q(document__spokespeople=spokesperson)`
4. Ranking: `.annotate(distance=CosineDistance(embedding_vector, vector)).order_by("distance")` (lines 222–223).
5. `top_k`: applied as `list(qs[:top_k])` (line 226).

Resulting truth table (E = ELIGIBLE, ✗ = NOT ELIGIBLE):

| KD state | teammate.universe = **None** (legacy) | teammate.universe = **U** (same U) | teammate.universe = **V** (different U) |
| --- | --- | --- | --- |
| **A** — universe=None, spokespeople=empty | **E** | ✗ | ✗ |
| **B** — universe=None, spokespeople={teammate} | **E** | ✗ | ✗ |
| **B′** — universe=None, spokespeople={other legacy} | ✗ | ✗ | ✗ |
| **C** — universe=U, spokespeople=empty | ✗ | **E** | ✗ |
| **D** — universe=U, spokespeople={teammate} | ✗ | **E** | ✗ |
| **D′** — universe=U, spokespeople={other in U} | ✗ | ✗ | ✗ |

Every cell corresponds to a load-bearing test in `shell/apps/embeddings/tests/test_retrieval_universe.py` and `test_retrieval_privacy.py`. Rows 5 (universe teammate + legacy doc → ✗) and 9 (cross-Universe → ✗) are annotated `_LOAD_BEARING` in the test names; they close the SESSION 259 audit §6 leak class per `docs/design/UNIVERSE_SCHEMA_V1.md`.

### §2.2. Eligibility matrix — `retrieve_universe_canon` (separate lane)

`retrieve_universe_canon(workspace, universe, cast, query, top_k=2)` at `shell/apps/embeddings/retrieval.py:282–413` is a **separate retrieval lane** called by `dialogue_synthesis` for multi-character scenes. It requires `universe is not None` and `cast is not empty`, and considers a doc eligible if EITHER:

- **Empty-M2M branch (lines 370–372):** `universe=U` AND `spokespeople=empty` → Class C.
- **Full-cast branch (lines 390–402):** `universe=U` AND `spokespeople` contains every teammate in `cast` (count > 1) → the D-fullcast sub-shape.

**Neither branch is used by `retrieve_for_teammate`.** Character OS therefore has **two retrieval lanes** with different notions of "canon": solo synthesis (`retrieve_for_teammate` — Class C treated as normal broadcast-eligible, D-fullcast treated as normal per-character attach) vs multi-character dialogue (`retrieve_universe_canon` — both variants surface as canon in a `top_k=2` lane with a separate quota).

### §2.3. Related retrievers (out of Slice 1 scope but noted)

- `retrieve_for_thread` — delegates to `retrieve_for_teammate` for doc chunks; adds thread-scoped conversation memory (separate table).
- `retrieve_universe_memory` — operates on `NarrativeMemory` rows, not `KnowledgeChunk`. Not implicated in shared/global knowledge semantics.
- `resolve_chunk_ids_to_docs` — read-only serializer helper; does NOT re-check scope (assumes ID list is trusted, groups by document, returns `{id, title, chunk_count}`).

---

## §3. RETRIEVAL PIPELINE TRACE

### §3.1. End-to-end path (solo synthesis, most common case)

```
KnowledgeDocument (workspace + universe + spokespeople + is_active + status)
     │
     ├── async ingest → chunker → OpenAI embed → KnowledgeChunk rows (embedding_vector: pgvector)
     ↓
[retrieval eligibility] shell/apps/embeddings/retrieval.py:194–220
     ├── workspace filter (unconditional)
     ├── universe branch (spokesperson.universe_id None vs set)
     ├── spokespeople M2M filter (Q isnull=True OR = spokesperson)
     ├── pgvector cosine ranking (CosineDistance annotation)
     └── list(qs[:top_k])       ← flat list of KnowledgeChunk ORM objects
     ↓
[K6 synthesis] shell/character_os/script_synthesis.py:438–655
     ├── chunks passed as `retrieved_chunks: list[KnowledgeChunk]`
     ├── _assemble_system_prompt → _build_factual_basis_section
     └── LLM sees a flat "FACTUAL BASIS" block — no scope labels
     ↓
[Composition persistence] shell/apps/compositions/models.py:427
     └── Composition.knowledge_chunk_ids = [chunk_uuid_str, ...]    ← flat, no scope metadata
     ↓
[SPA render] web/src/routes/workspace/knowledge.$id.tsx
     └── "Used by compositions" panel calls resolve_chunk_ids_to_docs
         └── returns {id, title, chunk_count} per document — loses per-chunk ordering AND scope
```

### §3.2. Where scope is enforced / retained / discarded

| Stage | Scope information |
| --- | --- |
| KD ingest | Persisted on the KD row (`universe`, `spokespeople` M2M). Immutable via SPA post-creation. |
| Chunking / embedding | Chunk rows carry `document_id` (FK). No scope fields on `KnowledgeChunk` itself. |
| Retrieval eligibility | **Enforced** via ORM Q filters (retrieval.py:194–220). |
| Retrieval return | **Discarded** — return type is `list[KnowledgeChunk]`. Chunks re-derivable via `chunk.document.universe`, but no scope tag is attached to the returned object. |
| K6 prompt assembly | **Invisible.** Chunks are rendered as flat "FACTUAL BASIS" text; LLM cannot distinguish a shared chunk from a private one. |
| Composition persistence | **Invisible.** `Composition.knowledge_chunk_ids` is a flat JSON list of UUIDs. No `[shared, shared, private, private, shared]` labeling. |
| SPA "Used by compositions" | **Coarse.** `resolve_chunk_ids_to_docs` re-groups by document ID and returns `{id, title, chunk_count}` — the operator sees "5 chunks from doc D" but not scope. |

### §3.3. Multi-character dialogue path (only add-on)

`shell/character_os/dialogue_synthesis.py:1489–1815`:

- Calls `retrieve_for_teammate(tm, topic, top_k=5)` **once per cast member** (per-character branch).
- Calls `retrieve_universe_canon(workspace, universe, cast, topic, top_k=2)` **once** (canon branch).
- Merges the two result sets, dedupes chunks, prepends canon IDs first so downstream provenance panels can infer "the first N IDs are canon" **by ordering convention only** (comment at lines 1774–1777).
- Persists a **flat** deduplicated list to `Composition.knowledge_chunk_ids` (line 1815).

**Consequence:** the shared/canon distinction survives inside `dialogue_synthesis` orchestration but is **discarded at persistence time**. Even the "canon-first ordering" convention is undocumented at the schema layer and is not enforced by any code outside that call site.

### §3.4. Retrieval pipeline finding — critical answers

- **Ranking is pure cosine distance.** No scope-priority weighting, no per-document diversity quota, no per-scope quota inside `retrieve_for_teammate`.
- **`top_k` is applied after ranking.** A single document CAN occupy all top_k slots if its chunks are the closest matches.
- **K6 cannot differentiate shared vs character-specific chunks.** They arrive as a flat list, are rendered as an undifferentiated "FACTUAL BASIS" block, and K6 has no scope-tagging affordance to reason about them separately.
- **`Composition.knowledge_chunk_ids` is a flat list of UUIDs.** Scope is not persisted; can only be re-derived by re-querying each chunk's document.
- **Composition has no `universe` FK.** It reaches Universe transitively via `spokesperson.universe` (per `UNIVERSE_SCHEMA_V1.md:221–226`). This is intentional.

---

## §4. LIVE-DATA CLASSIFICATION (READ-ONLY)

DB probes were executed against the live Postgres (port 5434) using Django ORM in `manage.py shell`. All operations were read-only. **No rows were created, modified, or deleted.**

### §4.1. Workspace inventory (non-e2e workspaces only)

| Workspace | Teammates | Universes | KDs |
| --- | --- | --- | --- |
| `chriss-workspace` (4ce5486d) | 8 | 2 | 17 |
| `admins-workspace` (f4f2aa20) | 2 | 0 | 46 |
| `bootstrap-fixtures` (d3bec53f) | 0 | 0 | 0 |
| `exp266-weak-…` (097bd82e) | 2 | 1 | 3 |
| `exp266-strong-…` (fa26e601) | 2 | 1 | 3 |
| `session272-rivet-debug-ctl` (d73fb96a) | 1 | 1 | 1 |
| `session272-rivet-debug-exp` (1f4fad65) | 1 | 1 | 1 |

Only `chriss-workspace` and `admins-workspace` are meaningful active surfaces; the four `exp266-…` / `session272-…` workspaces are disposable experiment artifacts. All e2e workspaces (~60) were excluded from this inventory.

### §4.2. `chriss-workspace` — teammates

| Teammate | UUID | Universe |
| --- | --- | --- |
| Mason | `28b9a7ea-…` | **None (legacy)** |
| Penny | `ce8ab526-…` | **None (legacy)** |
| Ruby | `5875a7b4-…` | `1a0af807-…` (Fox & Flour Bakery) |
| Mike | `ed4cb364-…` | **None (legacy)** |
| Repo Red | `f3eb657c-…` | **None (legacy)** |
| Patch | `7fad8172-…` | `56d16b63-…` (Patch's Workshop) |
| Rivet | `f18b75cc-…` | `56d16b63-…` (Patch's Workshop) |
| Riggs | `5731a73d-…` | **None (legacy)** |

Universe membership: Fox & Flour Bakery = {Ruby}. Patch's Workshop = {Patch, Rivet}.

### §4.3. `chriss-workspace` — KDs by class

| KD Title | Class | `universe` | `spokespeople` | Chunks |
| --- | --- | --- | --- | --- |
| About Hearth & Hollow Books | **A** | None | ∅ | 1 |
| How We Recommend Books | **A** | None | ∅ | 1 |
| Children's Reading | **A** | None | ∅ | 1 |
| Bookstore Events | **A** | None | ∅ | 1 |
| Supporting Local Authors | **A** | None | ∅ | 1 |
| Helping Customers Find Their Next Read | **A** | None | ∅ | 1 |
| Tulsi — Core Identity and Public Purpose | **A** | None | ∅ | 3 |
| TANK — AUTOMOTIVE FINANCING CONTENT KNOWLEDGE | **A** | None | ∅ | 22 |
| Riggs | **A** | None | ∅ | 1 |
| Penny Riverstone Knowledge Base | **B** | None | {Penny} | 7 |
| Surgo_Automotive_Mike_Knowledge_Base | **B** | None | {Mike} | 16 |
| Surgo Financing | **B** | None | {Mike} | 5 |
| REPO RED — AUTOMOTIVE FINANCING & SOCIAL CONTENT KNOWLEDGE | **B** | None | {Repo Red} | 22 |
| PATCH — AI BUILDING, EXPERIMENTATION & CONTENT KNOWLEDGE | **D** | Patch's Workshop | {Patch} | 22 |
| RIVET — EXPERIMENTATION, TESTING & WORKSHOP KNOWLEDGE | **D** | Patch's Workshop | {Rivet} | 14 |
| PATCH'S WORKSHOP — SHARED CANON | **D-fullcast** | Patch's Workshop | {Patch, Rivet} | 1 |
| Fox & Flour Bakery — Working Knowledge | **D** | Fox & Flour Bakery | {Ruby} | 10 |

**Class distribution in `chriss-workspace`:** A=9, B=4, C=**0**, D=3+1(fullcast).

### §4.4. `admins-workspace` — summary

- Teammates: Rigby, Riggs (both legacy, both `universe=None`).
- Universes: 0.
- KDs: 46. Class distribution: A=1, B=45, C=0, D=0.
- Interpretation: nearly every doc is character-scoped to Rigby or Riggs. Not relevant to the shared-knowledge characterization other than confirming Class C is unused here too.

### §4.5. Session-experiment workspaces — summary

- `exp266-weak` / `exp266-strong`: A=0, B=0, C=0, D=3 each. Universe-scoped Patch/Rivet clones.
- `session272-rivet-debug-ctl` / `-exp`: A=0, B=0, **C=1**, D=0 each. **The only live Class C specimens exist here.** These are disposable session-272 artifacts.

### §4.6. Retrieval eligibility per `chriss-workspace` teammate

Given the truth table in §2.1, each teammate can retrieve:

| Teammate | KDs eligible | Notable exclusions |
| --- | --- | --- |
| Ruby (universe=Fox & Flour) | 1 KD — Fox & Flour Bakery — Working Knowledge (Class D, spokespeople={Ruby}) | All 9 Class A KDs are BLOCKED (row 5). All Patch's Workshop KDs BLOCKED (row 9). |
| Patch (universe=Patch's Workshop) | 2 KDs — PATCH KB + PATCH'S WORKSHOP SHARED CANON | RIVET KB blocked (row 8 — universe match but M2M excludes Patch). All 9 Class A KDs BLOCKED. |
| Rivet (universe=Patch's Workshop) | 2 KDs — RIVET KB + PATCH'S WORKSHOP SHARED CANON | PATCH KB blocked (row 8). All 9 Class A KDs BLOCKED. |
| Mason (legacy, universe=None) | **9 Class A KDs** (all 6 Hearth & Hollow + Tulsi + TANK + Riggs). No character-specific. | All Class C/D universe-scoped KDs BLOCKED (row 4). |
| Penny (legacy) | 9 Class A + Penny KB (Class B) = **10 KDs** | Universe-scoped BLOCKED. Mike/Repo Red B-class KDs BLOCKED. |
| Mike (legacy) | 9 Class A + Mike KB + Surgo Financing = **11 KDs** | Universe-scoped BLOCKED. Penny/Repo Red B-class BLOCKED. |
| Repo Red (legacy) | 9 Class A + Repo Red KB = **10 KDs** | Universe-scoped BLOCKED. Penny/Mike B-class BLOCKED. |
| Riggs (legacy) | 9 Class A only | No character-specific KDs targeted at Riggs. |

### §4.7. Live-data observations that matter to product

1. **Class C (Universe-shared, empty M2M) is unused in production.** Chris's workspace has zero Class C KDs. The two Class C specimens in `session272-rivet-debug-*` are disposable experiment artifacts. Operators — or possibly the SPA — are avoiding Class C.
2. **`PATCH'S WORKSHOP — SHARED CANON` uses D-fullcast instead of Class C.** Operator intent is clearly "shared canon for the Patch's Workshop cast," but the encoding is `spokespeople = {Patch, Rivet}` (explicit full cast), not `spokespeople = ∅`. Both encodings would work for `retrieve_for_teammate`; both are picked up by `retrieve_universe_canon` (via different branches). The chosen encoding suggests either (a) the SPA doesn't easily expose "leave empty" as an intentional broadcast affordance in a Universe context, or (b) the operator prefers explicit lists.
3. **All 9 legacy teammates in `chriss-workspace` still see the full Class A pool.** Mason is the last un-attached SESSION-273 substrate; the four Class A automotive/bookstore docs (TANK, Tulsi, all Hearth & Hollow) leak into any legacy teammate's cosine ranking regardless of relevance. This is exactly the shape SESSION 273 §13.3 diagnosed for Ruby pre-attach.
4. **Attaching Ruby to Fox & Flour Bakery removed her Class A access.** Row 5 of the truth table (`teammate.universe != None + document.universe = None → ✗`) is the mechanical reason for the SESSION 273 §17.6 observation that "attaching Ruby to Fox & Flour made her stop seeing the workspace KDs." She flipped from row 1 eligibility to row 5 non-eligibility for those docs.

---

## §5. UI SEMANTICS AUDIT

Sources: `web/src/routes/workspace/knowledge.tsx`, `web/src/routes/workspace/knowledge.$id.tsx`, `web/src/components/knowledge-panel.tsx`, `web/src/components/spokesperson-universe-panel.tsx`, `web/src/lib/api/knowledge.ts`, `shell/apps/embeddings/serializers.py`, `shell/apps/embeddings/views.py`.

### §5.1. Create form (Paste / Upload / URL / Search tabs)

- **Universe field** — dropdown labeled `"World / Universe"` (`knowledge.tsx:72`).
  - Options: `"— Pick a scope —"` (disabled placeholder), `"None (legacy — visible to workspace-wide legacy teammates only)"`, one option per Universe in the workspace.
  - Help text: `"Pick a world to scope this doc to that world's characters, or pick "None (legacy)" to make it visible to legacy (pre-Universe) characters."` (`knowledge.tsx:95–97`).
  - **Selection is required** to enable submit.
- **Spokesperson assignment field — DOES NOT EXIST on the create form.** The M2M is always empty at creation time.
- **Empty-state copy (list page, no KDs yet):** `"Paste content or upload a PDF above. Every spokesperson in the workspace will be able to draw from it."` (`knowledge.tsx:216–217`).
  - Uses the word **"workspace"** unconditionally, regardless of whether the doc will be Class A (workspace-shared) or Class C (Universe-shared). This is **factually incorrect for Class C**.

### §5.2. Edit / attach flow (Spokesperson detail page)

The only way to modify M2M attachment is via each Spokesperson detail page's Knowledge panel (`knowledge-panel.tsx`):

- For a KD with **empty M2M** (Class A or Class C): row label `"Visible to every spokesperson in the workspace · {chunk_count} chunk(s)"` (`knowledge-panel.tsx:177`). Button text: `"Make {spokespersonName}-only"` (line 196). Tooltip: `"Restrict to {spokespersonName} only"` (line 194).
- For a KD with **non-empty M2M** where this spokesperson is attached: label `"Attached to {N} spokesperson(s) · {chunk_count} chunk(s)"` (line 179). Button: `"Detach"` (line 208).
- For a KD with non-empty M2M where this spokesperson is **not** attached: the row does not appear (filtered by backend).

**Same label problem as §5.1:** empty-M2M docs are labeled "workspace" even when they are Class C (Universe-shared).

### §5.3. Knowledge list page (`/workspace/knowledge`)

Columns: title, document type, chunk count, ingestion source, status pill, delete button.

**`universe` is NOT displayed. `spokespeople` is NOT displayed.** No scope-class badge (no A/B/C/D label). No "eligible characters" count. No sort or filter by Universe or by scope.

### §5.4. Knowledge detail page (`/workspace/knowledge/{id}`)

Metadata grid shows: Type, Ingested via, Chunks, Source URL (if any), Hostname, Author, Date, Extracted char count, Fetched char count, PDF page count, Created.

**`universe` is NOT in the metadata grid.** **`spokespeople` (the attached characters) is NOT in the metadata grid.** No "Eligible characters" section. No scope class badge.

### §5.5. Universe reassignment on Spokesperson detail

`spokesperson-universe-panel.tsx` includes a move-preview modal when a Universe change would orphan docs:

- Modal heading: `"Reassigning would orphan {count} doc attachment(s)"` (line 198–200).
- Modal body: `"The following documents are attached to this teammate but belong to a different world. If you proceed, this teammate will no longer see those docs in retrieval. You can reassign the docs first if you want to keep them accessible."` (lines 202–206).
- **This is the only place in the SPA where Universe scope of a KD is surfaced to the operator** — and only as a warning during a specific side-effect flow.

### §5.6. API contract — KnowledgeDocument fields returned to SPA

`KnowledgeDocumentSerializer` (list) returns: `id, workspace, workspace_name, universe, spokespeople, title, document_type, content_hash, source_url, source_metadata, ingested_via, status, error_message, is_active, chunk_count, created_at, updated_at`.

`KnowledgeDocumentDetailSerializer` adds: `chunks` (array), `processed_content` (full text).

**The API DOES return `universe` and `spokespeople`.** The SPA simply does not render them anywhere in list, detail, or teammate-panel views. The operator's inability to see scope is a **SPA rendering gap**, not an API gap.

### §5.7. UI semantics finding — critical items

| Class | Can operator intentionally create? | Can operator recognize after creation? | Can operator understand retrieval consequence? |
| --- | --- | --- | --- |
| **A** — workspace-shared | **YES** (pick "None (legacy)" in the required dropdown) | **NO** — no post-creation surface shows `universe=None` | PARTLY — empty-state copy is accurate for Class A |
| **B** — workspace character-specific | **YES** but two-step: create as A, then attach on each Spokesperson page | **PARTLY** — visible on Spokesperson detail as "Attached to N spokesperson(s)" | PARTLY — no consolidated view |
| **C** — Universe-shared | **YES** (pick a Universe) — but no post-save affordance to confirm | **NO** — no surface shows `universe=U` on the doc | **NO** — empty-state copy says "workspace" which is factually wrong for Class C |
| **D** — Universe character-specific | **YES** two-step: pick Universe on create, attach on each Spokesperson page | **NO** — no `universe` field surfaced; only per-spokesperson M2M badge | **NO** — same as Class C plus no consolidated attached-cast view |

**The greatest observed operator-facing risk:** a Class C KD is visually indistinguishable from a Class A KD after creation. The label "Visible to every spokesperson in the workspace" is displayed for both, but is **factually true only for Class A**. For Class C, a spokesperson outside the chosen Universe cannot retrieve it — and the operator has no post-creation surface that would surface this constraint.

### §5.8. Terminology risk

- The SPA never uses the phrase "unassigned."
- Empty-M2M docs are labeled with either "Visible to every spokesperson in the workspace" (accurate for Class A only) or nothing (list page).
- Universe scope is described as "world" or "World / Universe" only at creation time.
- "Legacy" is used to describe both `universe=None` teammates AND `universe=None` KDs — but the term is undefined in the SPA copy.
- "Broadcast" is not used anywhere.
- The empty-M2M mechanic ("empty spokespeople = broadcast-eligible to all in scope") is **never explained** in operator-facing copy. It is only communicable via button state transitions.

---

## §6. PRODUCT-SEMANTICS MATRIX

Combining §2, §3, §4, §5.

| Class | Mechanical meaning today | Live example(s) in `chriss-workspace` | Retrievable by | Ranking behavior | Operator-visible after save | Likely operator interpretation | Ambiguity / risk | Potential legitimate product use (brainstorm) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **A** | universe=None + M2M=∅; broadcast-eligible to every legacy (universe=None) teammate in the workspace. | 9 KDs — Hearth & Hollow set (×6), Tulsi Core Identity, TANK, Riggs | Every legacy teammate in the workspace. NOT any Universe-scoped teammate. | Pure cosine, no priority. Can starve character-specific chunks. | Nothing distinguishes it from Class C. | "Everyone can use this" — but silently NOT anyone in a Universe. | § 3.4 K6 blindness + § 5.7 invisibility + § 4.7 leak into unrelated queries. | Workspace-wide company facts / policies, historic pre-Universe residue. |
| **B** | universe=None + M2M={A,…}; scoped to those legacy teammates only. | 4 KDs — Penny KB, Mike KB (×2), Repo Red KB | Only the listed legacy teammates. | Pure cosine within eligible set. | Visible on Spokesperson detail as "Attached to N speaker(s)." | "Belongs to Penny / Mike / Repo Red." Usually correct. | No consolidated cross-character view — attaching a doc to multiple characters is a per-character workflow. | Character-private expertise / persona docs (pre-Universe era). |
| **C** | universe=U + M2M=∅; broadcast-eligible to every teammate in U. | **NONE** in production. Two disposable specimens in `session272-rivet-debug-*`. | Every teammate in U. | Pure cosine within eligible set. | Nothing distinguishes it from Class A. | If SPA copy is followed literally: "workspace" — factually WRONG for Class C. | Class C is technically supported but effectively unused. Whether that's intent or emergent-from-UI is unknown. | Universe/world canon shared by all cast members. |
| **D** | universe=U + M2M={A,…}; scoped to those Universe teammates. | 3 KDs — PATCH KB → {Patch}, RIVET KB → {Rivet}, Fox & Flour → {Ruby}. | Only the listed teammates within U. | Pure cosine within eligible set. | Visible on Spokesperson detail. Universe not visible anywhere. | "Character-scoped inside the Universe." | Operator has no consolidated view of who else in U is attached; can be confused with Class B. | Character expertise inside a Universe, per-character memories. |
| **D-fullcast** | universe=U + M2M=every teammate in U; behaves like Class D for `retrieve_for_teammate` but hits the full-cast canon branch of `retrieve_universe_canon`. | 1 KD — PATCH'S WORKSHOP — SHARED CANON → {Patch, Rivet}. | Every teammate in U (via the M2M being a superset). | Pure cosine within eligible set (solo lane); canon `top_k=2` lane in dialogue. | Visible on Spokesperson detail as "Attached to 2 speaker(s)." | Operator likely intended "Class C" — cast shared canon — but implemented via explicit full cast. | Two encodings for "cast-shared" produce identical solo-lane behavior; only dialogue lane distinguishes. Emergent, undocumented. | Cast canon; also the only way current operators appear to express "shared in a Universe." |

### §6.1. Retrieval-time interaction risks

- **top_k starvation:** In a legacy retriever's Class A pool, if the top 5 cosine matches all come from one 22-chunk doc (e.g., TANK for a broad automotive query), the character's own Class B chunks are silently starved. There is no per-document diversity, per-scope quota, or minimum-per-tier guarantee.
- **Class A vs Class B contest:** For a legacy teammate, workspace-shared and character-specific chunks compete in one candidate pool with only cosine ranking. There is no "always keep at least one character-specific chunk" rule.
- **Class A vs Class C mismatch:** Both are labeled the same in the SPA (empty-M2M → "workspace") but have completely different retrieval eligibility. The SPA copy for Class C is mechanically wrong.
- **Class D vs D-fullcast:** For `retrieve_for_teammate`, both look identical to any single teammate. Divergence only manifests inside `retrieve_universe_canon`. Operators picking one encoding vs the other are making a decision they may not know they are making.

### §6.2. What is deliberate vs emergent

| Behavior | Deliberate | Emergent |
| --- | --- | --- |
| Workspace boundary is absolute | ✔ (SESSION 259) | |
| Universe boundary is absolute | ✔ (SESSION 261) | |
| Legacy teammates cannot see Universe-scoped docs (row 4) | ✔ | |
| Universe teammates cannot see legacy Class A docs (row 5) | ✔ (SESSION 259 §6 leak fix) | |
| Empty M2M = broadcast-eligible in scope | ✔ (design intent, load-bearing test coverage) | |
| Pure cosine ranking with no per-scope priority | | ✔ (no evidence anyone chose this; no test asserts absence of priority) |
| No per-document diversity | | ✔ |
| No per-tier quota inside single retrieval call | | ✔ |
| Class C SPA-copy factual error | | ✔ (SPA copy predates SESSION 261 Universe rollout; not updated) |
| Universe field hidden in list/detail after creation | | ✔ (SPA has the data but doesn't render it) |
| `Composition.knowledge_chunk_ids` loses scope | | ✔ (JSON list is trivial; no schema effort to preserve scope) |
| Canon-first ordering convention in dialogue_synthesis | ✔ (SESSION 263 §B comment) but undocumented at schema | |
| D-fullcast is the only production encoding of "cast shared canon" | | ✔ (probably operator preference given SPA affordances) |
| Class C effectively unused in production | | ✔ |

---

## §7. ARCHITECTURAL QUESTIONS — ANSWERS

**A. Is "global knowledge" actually one thing today, or are there really TWO shared scopes: workspace-shared and Universe-shared?**

Two. Class A (`universe=None`, empty M2M) is workspace-scoped and only visible to legacy teammates. Class C (`universe=U`, empty M2M) is Universe-scoped and only visible to teammates in U. They are mechanically distinct and mutually exclusive (a KD cannot be both). The SPA collapses them into a single "workspace" label, which is why they appear as one thing operationally.

**B. Is "character-specific" a separate retrieval tier, or merely an eligibility constraint inside the same ranked pool?**

**Merely an eligibility constraint.** `retrieve_for_teammate` filters by `Q(document__spokespeople__isnull=True) | Q(document__spokespeople=spokesperson)` and then ranks the union by cosine distance. Shared and character-specific chunks compete in the same ranked pool. There is no separate tier, no priority weighting, no reserved slot count.

**C. Does current retrieval have a concept of "shared defaults + character specialization," or does it merely have "all eligible chunks compete equally"?**

**Only the latter.** All eligible chunks compete equally on cosine distance. "Shared defaults" and "character specialization" exist only at the eligibility filter level, not at the ranking level.

**D. Could a highly similar shared chunk starve a relevant private chunk because of top_k?**

**Yes.** `top_k` is applied via `list(qs[:top_k])` after cosine sort. If the closest 5 chunks are all from a workspace-shared 22-chunk doc, the character-specific chunks never enter the returned set even if they exist and are meaningfully relevant at rank 6.

**E. Could five shared chunks from one document occupy the entire factual basis?**

**Yes.** No per-document diversity mechanism exists. Confirmed by absence: no `distinct` beyond de-dup, no `Count`/`F()` document-diversity annotation, no post-processing pass to enforce document variety.

**F. Is there any document-level diversity mechanism, per-scope quota, or per-character quota?**

**No** at the retrieval-function level. `dialogue_synthesis` orchestrates separate calls with separate quotas — `retrieve_universe_canon(top_k=2)` and `retrieve_for_teammate(top_k=5)` per cast member — but each individual retrieval call has no internal diversity/quota logic.

**G. If we eventually wanted "shared facts everybody knows, plus Ruby's expertise," does the existing architecture already express that safely, or only approximately?**

**Approximately.** The eligibility layer expresses it exactly: Class C (or D-fullcast) shared canon + Class D character-specific for Ruby will both be eligible for Ruby's retrieval. But the **ranking layer does not preserve the intent** — cosine distance alone will surface whichever chunks are closer to the query embedding, regardless of scope. In practice, if the shared canon is close in embedding space to a query, it can push Ruby's expertise out of `top_k`. So the semantic intent is expressible; the retrieval-time guarantee is not.

**H. Are cross-Universe boundaries structurally strong?**

**Yes.** Row 9 of the truth table (`teammate.universe=V, doc.universe=U, U≠V → ✗`) is enforced by the direct equality filter at retrieval.py:214 (`document__universe_id=spokesperson.universe_id`). No branch of `retrieve_for_teammate` allows cross-Universe leakage. `retrieve_universe_canon` also fails-closed if any cast member is in a different Universe (retrieval.py:349–351). Structurally impossible to cross a Universe boundary through retrieval.

**I. What happens to workspace-shared documents once a character is attached to a Universe?**

**They become structurally invisible to that character.** The Universe branch at retrieval.py:211–214 makes `document.universe = None` unreachable for any teammate with `universe_id != None`. This is row 5 of the truth table (`_LOAD_BEARING`). "Workspace-global" is therefore **NOT actually global to characters inside Universes** — it is global only to the *shrinking pool of legacy teammates*. As operators migrate characters into Universes, workspace-shared docs progressively lose reach. SESSION 273 §17.6 observed this directly with Ruby: attaching her to Fox & Flour Bakery made her stop seeing the 9 Class A KDs she previously retrieved. The behavior is by design (SESSION 259 §6 leak fix) but the product implication — that Class A slowly becomes orphan as adoption of Universes grows — is not surfaced anywhere in the SPA or documentation.

---

## §8. PRODUCT-DECISION BRIEF (OPTIONS ONLY, NO RECOMMENDATION)

### §8.1. Summary of what exists today

- **Mechanically:** four scopes (A/B/C/D) + one emergent sub-shape (D-fullcast). Eligibility is enforced correctly and tested. Cross-workspace and cross-Universe leaks are structurally impossible.
- **Operationally:** Class C is unused; Class A is the workspace-shared workhorse for legacy teammates but is invisible to Universe teammates; D-fullcast is the operator's chosen encoding for "cast canon."
- **UI:** Universe scope is a required creation-time input but has no post-creation representation. Empty-M2M semantics ("broadcast-eligible in scope") is never explained; the label "workspace" is used regardless of true scope, which is factually wrong for Class C.
- **Retrieval:** pure cosine ranking with no per-scope, per-document, or per-tier priority. shared chunks can starve character-specific chunks.
- **Persistence:** `Composition.knowledge_chunk_ids` is a flat list; scope is not persisted.
- **K6:** cannot distinguish shared from character-specific chunks; sees a flat factual basis.

### §8.2. Where mechanical model and operator model disagree

1. **Class A "workspace-global" is not global to Universe teammates.** Operator likely reads the label as "everyone" but the mechanical scope is "everyone still on legacy." As adoption of Universes grows, Class A KDs progressively serve fewer and fewer teammates.
2. **Class C SPA copy is factually wrong.** Empty-state and Spokesperson-panel copy say "workspace" for empty-M2M docs; for Class C this is a misstatement — the actual scope is "everyone in the chosen Universe."
3. **D-fullcast collapses into Class D for solo retrieval.** Operators appear to be using D-fullcast to express "cast canon" instead of Class C. Either encoding works, but the intent-encoding-behavior triangle is confusing.

### §8.3. Semantic ambiguities and retrieval risks

- Empty-M2M semantics is never explained (§5.8).
- Class C exists mechanically but is unused in production; unclear if that is intentional or emergent from UI.
- Class A's slow decay is invisible; no operator warning as Universe adoption grows.
- Pure-cosine ranking can silently invert operator intent when shared+specific chunks compete.
- Canon-first ordering in `dialogue_synthesis` is undocumented at the schema layer.
- `Composition.knowledge_chunk_ids` is scope-blind; provenance panels cannot answer "which chunks were shared vs private."

### §8.4. Which questions require an intentional experiment vs source inspection

**Answered from source alone (this doc):**
- All 4-scope eligibility semantics.
- All cross-scope competition behavior at the ranking level.
- All persistence gaps.
- All UI copy gaps.
- All truth-table cells (also covered by existing load-bearing tests).

**Would require a controlled live experiment (NOT done in Slice 1):**
- **E1.** Confirm empirically that a Class A doc (e.g., TANK) can starve a Class B doc for a legacy teammate whose query is ambiguously relevant to both. Source proves it *can*; only a probe proves it *does* for a specific query embedding topology.
- **E2.** Measure how often, in production compositions, shared chunks and character-specific chunks co-occurred in a single `knowledge_chunk_ids` list, and how often shared chunks would have crowded out character-specific chunks if per-scope quotas were introduced.
- **E3.** Test whether a Class C KD (Universe-shared, empty M2M) behaves as expected end-to-end in the SPA — including creation via the current form, visibility on Universe-scoped teammates' Spokesperson-detail pages, and correct exclusion for teammates in other Universes.
- **E4.** Compare K6 output quality for a query where the "correct" answer is in a character-specific chunk but a shared chunk is embedding-closer — does K6 grounding stay accurate or drift?
- **E5.** Assess whether operators would prefer Class C or D-fullcast for "cast canon" given equal UI affordance.

### §8.5. Product-model OPTIONS (NOT RECOMMENDATIONS)

Chris chooses. Every option below preserves the SESSION 259 / SESSION 261 workspace and Universe isolation invariants. None of these are pre-endorsed by this doc.

#### Option **P1** — Preserve current model; fix UI accuracy only

**What changes:** No mechanical retrieval change. SPA copy updated to accurately describe scope. Universe field surfaced in list/detail. Empty-M2M semantics explicitly named (e.g., "Shared with every character in this world" for Class C, "Shared with every legacy character in the workspace" for Class A, "Only these characters" for B/D).

**What this admits:** Class C stays as a supported-but-rarely-used scope. Class A stays as legacy-only. Cosine-only ranking stays. Shared vs private chunk starvation stays possible.

**Tradeoff:** Cheapest. Purely operator-facing improvement. Does not fix the ranking-starvation risk or the K6-blindness. Does not change persistence.

#### Option **P2** — Formalize a two-lane retrieval model

**What changes:** Retrieval returns two visibly distinct sets — "shared/canon" and "character-specific" — with independent `top_k` budgets in every call site (not just `dialogue_synthesis`). Solo synthesis gets its own `retrieve_shared_for_teammate` + `retrieve_specific_for_teammate` split, plus a combined convenience wrapper. Composition provenance persists both lanes separately (e.g., `Composition.canon_chunk_ids` + `Composition.persona_chunk_ids`).

**What this admits:** Operator intent ("here are shared facts + here is Ruby's expertise") is preserved through synthesis and persistence. K6 can be given per-lane labels. Starvation is bounded per-lane. Class C becomes first-class.

**Tradeoff:** Bigger change. Requires new API surface, new persistence fields (with backfill or forward-compat), new SPA rendering, new K6 prompt structure. Every current caller of `retrieve_for_teammate` needs to decide whether to migrate.

#### Option **P3** — Workspace → Universe → Character inheritance model

**What changes:** Class A becomes visible to Universe teammates too (workspace fact → inherited). Universe scope adds facts on top; character scope adds facts on top of that. Three concentric rings: workspace canon → Universe canon → character expertise.

**What this admits:** Class A KDs stay useful as Universe adoption grows. Explicit "company-wide facts" tier. Operators can put "brand voice" or "company policy" at workspace level and rely on it reaching every character.

**Tradeoff:** Breaks the SESSION 259 §6 leak fix — legacy Class A docs would once again reach Universe teammates. Any pre-existing Class A doc (all 9 in `chriss-workspace`, including TANK/Tulsi/Hearth&Hollow) would suddenly become visible to Ruby, Patch, Rivet. Requires either (a) migrating existing Class A docs to explicit Class C for each Universe, or (b) accepting the leak. Would require rebuilding the workspace/Universe/character priority scheme from scratch — likely with per-scope priority weights or reserved slots (else same starvation risk as P1).

#### Option **P4** — Explicit "audiences" as first-class construct

**What changes:** Replace the `universe + spokespeople` scoping fields with a single `audiences` M2M pointing to a new `KnowledgeAudience` table. Audiences can be: `workspace-legacy`, `universe:{U}`, `character:{A}`, `custom:{list-of-teammates}`. An operator picks one or more audiences when creating a KD. Retrieval eligibility becomes "teammate is in at least one audience of the KD." No implicit "empty means broadcast" mechanic — every KD explicitly declares its audiences.

**What this admits:** Empty-M2M ambiguity disappears. Class A/B/C/D collapse into audience combinations, but the operator picks them explicitly. New audience shapes (e.g., "all Universes," "Fox & Flour cast + Patch's Workshop cast") become expressible without model changes.

**Tradeoff:** Largest change. Requires a schema migration (KD table, new audience table), full SPA rework, backfill of existing 63 KDs (17 in `chriss-workspace` + 46 in `admins-workspace`), retrieval predicate rewrite, likely a rethink of `retrieve_universe_canon`. Probably not appropriate as a first move; may be the endpoint of a longer arc.

### §8.6. What Slice 1 does NOT decide

- Whether Class C should stay, be renamed, be removed, or be encouraged.
- Whether Class A should be preserved, deprecated, or migrated to Class C per Universe.
- Whether shared vs character-specific chunks should have per-scope priority in ranking.
- Whether K6 should see scope labels.
- Whether `Composition.knowledge_chunk_ids` should preserve scope.
- Whether the SPA should expose the `universe` field in list/detail.
- Which of P1/P2/P3/P4 (or a fifth model derived from further characterization) is right.
- Whether a Slice 2 experiment (E1–E5) is warranted before making the product call.

**All of the above are Chris's decisions to make after reading this doc.**

---

## §9. SLICE 1 CHECKBOX STATUS

Evidence-backed completion only.

- [x] Verify main == origin/main (§1)
- [x] Verify working tree clean at open (§1)
- [x] Verify SESSION 273 CLOSEOUT SHA in history (§1)
- [x] Verify runtime health + zero mock/experiment env drift (§1)
- [x] Trace `retrieve_for_teammate` mechanically from source (§2.1, §3)
- [x] Trace `retrieve_universe_canon` mechanically from source (§2.2)
- [x] Build 4-scope eligibility truth table (§2.1)
- [x] Confirm truth table matches load-bearing tests in `test_retrieval_universe.py` (§2.1)
- [x] Document workspace filter as unconditional (§2.1, §3.4)
- [x] Document Universe filter as absolute (row 5 + row 9) (§2.1, §3.4)
- [x] Document spokespeople M2M as eligibility only, not ranking (§7 B, §7 C)
- [x] Document `top_k` as post-ranking slice with no diversity mechanism (§3.4, §7 D–F)
- [x] Document K6 as scope-blind at prompt-assembly time (§3.1, §3.4)
- [x] Document `Composition.knowledge_chunk_ids` as scope-blind at persistence (§3.1, §3.4)
- [x] Confirm `Composition` has no direct `universe` FK (§3.4)
- [x] Inventory all live KDs in `chriss-workspace` and classify A/B/C/D (§4.3)
- [x] Enumerate teammates in `chriss-workspace` with Universe assignment (§4.2)
- [x] Sample `admins-workspace` + session-experiment workspaces for class distribution (§4.4, §4.5)
- [x] Confirm Class C is unused in production (§4.7 item 1)
- [x] Confirm D-fullcast is the observed encoding for "cast canon" (§4.7 item 2)
- [x] Confirm Ruby's Universe attach mechanically explains the SESSION 273 §17.6 leak-stop (§4.7 item 4)
- [x] Audit Knowledge SPA create/edit/list/detail surfaces (§5.1–§5.6)
- [x] Cite exact operator-visible copy with `file:line` references (§5.1–§5.5)
- [x] Confirm `universe` field is hidden from list + detail post-creation (§5.3, §5.4)
- [x] Confirm empty-M2M is labeled "workspace" regardless of true scope (§5.1, §5.2, §5.7)
- [x] Answer §7 architectural questions A–I from source (§7)
- [x] Build product-semantics matrix (§6)
- [x] Enumerate deliberate-vs-emergent behaviors (§6.2)
- [x] Present 2–4 product-model OPTIONS with tradeoffs, no recommendation (§8.5)
- [x] Enumerate open questions that require experiment vs source inspection (§8.4)
- [x] Preserve SESSION 274 HANDOFF as starting artifact (no modification)
- [x] Confirm no code, copy, KD, spokesperson-assignment, or Universe-assignment changes made

Unresolved / experiment-required (deferred to Chris's decision):

- [ ] E1 — Empirically demonstrate Class A starvation of Class B for a legacy teammate on a live query
- [ ] E2 — Measure historical co-occurrence of shared+specific chunks in `Composition.knowledge_chunk_ids`
- [ ] E3 — End-to-end Class C dogfood via the SPA (create, verify visibility, verify exclusion)
- [ ] E4 — K6 grounding drift test: shared chunk embedding-closer than the "correct" character-specific chunk
- [ ] E5 — Operator preference test between Class C and D-fullcast for cast canon
- [ ] **P0** — Chris's product-model decision (P1 / P2 / P3 / P4 / other)

---

## §10. FILES WRITTEN / GIT DIFF SUMMARY

**Created (1 file):**

- `docs/design/SESSION_274_SHARED_GLOBAL_KNOWLEDGE_CHARACTERIZATION.md` (this file)

**Not modified:**

- `docs/design/SESSION_274_HANDOFF.md` — preserved as-is; is the starting artifact for the session.
- Any source under `shell/`, `web/`, `services/`, `scripts/` — no code, copy, or config changed.
- Any KD, spokesperson assignment, Universe assignment, or Composition — no DB write executed.

**Expected `git status --short`:** one untracked file:

```
?? docs/design/SESSION_274_SHARED_GLOBAL_KNOWLEDGE_CHARACTERIZATION.md
```

---

## §11. COMMIT RECOMMENDATION

This is documentation-only. It captures a load-bearing mechanical and operational characterization that SESSION 274's product decision (and any downstream slice) will lean on repeatedly. **Recommendation: commit as a standalone documentation slice** on `main`, with a conventional-commits-style subject:

```
docs(session-274): §1-§11 Slice 1 — shared/global knowledge characterization (read-only)
```

Chris authorizes the commit. If not authorized, the file stays untracked pending review.

---

**End of SESSION 274 Slice 1 characterization. Chris decides next step.**
