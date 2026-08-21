# SESSION 275 — Handoff

Fresh-session starting point. SESSION 274 is CLOSED.

**Full SESSION 274 record** — Slice 1 four-scope characterization + Slice 2 Class C dogfood + CLOSEOUT lives across three commits and two docs:

- Slice 1 characterization: `docs/design/SESSION_274_SHARED_GLOBAL_KNOWLEDGE_CHARACTERIZATION.md` (§1–§11)
- Slice 2 dogfood + CLOSEOUT: `docs/design/SESSION_274_UNIVERSE_SHARED_KNOWLEDGE_DOGFOOD.md` (§1–§24)
- Slice 1 commit `e7ff4a4` · Slice 2 commit `e96e33d` · SESSION 274 CLOSEOUT commit `<CLOSEOUT_SHA_PLACEHOLDER>`

Read at minimum §19–§24 of the Slice 2 doc before starting SESSION 275. This handoff is orientation, not a substitute.

---

## §A. WHAT SESSION 274 ESTABLISHED (short)

- Character OS has four mechanical knowledge scopes: **A** `universe=None, spokespeople=∅`; **B** `universe=None, spokespeople={A}`; **C** `universe=U, spokespeople=∅`; **D** `universe=U, spokespeople={A}` (plus an emergent D-fullcast sub-shape where the M2M contains every teammate in U).
- Class A is broadcast-eligible ONLY to legacy teammates (`universe=None`) — SESSION 259 row 5 makes it structurally invisible to teammates inside any Universe.
- Class C (Universe-shared) + Class D (character-specific) coexistence is a **VIABLE** product model. Cross-Universe isolation is CONFIRMED. Retrieval uses one flat cosine-ranked `top_k=5` pool with no per-scope quotas / no dedup / no priority — verdict YELLOW.
- **P2-lite** (preserve schema; expose Class C/D correctly in SPA; retrieve each with independent small budgets; merge / dedupe before K6; persist provenance later) is the **leading candidate direction** — NOT authorized for implementation.
- Ruby's newly created live Class C KD `8f825c98-…` (Fox & Flour Bakery, spokespeople=∅, 5 chunks) is the anchor specimen. Ruby's Class D KD, persona, NarrativeMemory unchanged. No provider render was performed.
- The current Class A pool in `chriss-workspace` (9 KDs — TANK, Tulsi, 6× Hearth & Hollow, Riggs) is Chris's operator-reported orphan set — knowledge left by deleted characters, with no SPA delete affordance. **This is the SESSION 275 opening question.** Not investigated in SESSION 274.

## §B. WHERE WE ARE

- **SESSION 274 is CLOSED** at commit `<CLOSEOUT_SHA_PLACEHOLDER>`.
- `main == origin/main`. Working tree clean at closeout.
- No retrieval code, no SPA copy, no Knowledge UI, no K6 prompt, no schema was changed.
- Ruby's Fox & Flour Class C KD (`8f825c98-…`) was created and is preserved as-is. Do **NOT** delete it.
- The 9 Class A orphan-candidate KDs are preserved as-is. **Do NOT delete them.** They are the primary evidence for SESSION 275.
- Chris's historical recollection about intentional KD preservation on character deletion (see §22 of the Slice 2 doc) is recorded as **hypothesis, unverified.**

**Local-real runtime expected state** (verified at SESSION 274 closeout):

- Django `:8010/admin/` → 302
- Media-engine `:8001/health` → `{status:ok, openai_mock:false, runway_mock:false, image_gen_mock:false, any_mock:false, llm_provider:openai, llm_model:gpt-4o-mini}`
- Vite `:5174/` → 200
- Celery `inspect ping` → 1 node online
- Zero experiment / mock env vars across Django, media-engine, celery PIDs

## §C. SESSION 275 PRIMARY OPENING QUESTION

> **What happens to character-specific knowledge when a character is deleted, and can preservation of its `KnowledgeDocument` / chunks / embeddings accidentally change that knowledge from private to shared?**

SESSION 275 must begin **READ-ONLY** — mechanical / product / lifecycle characterization first.

Do NOT begin by:

- deleting anything
- changing cascade behavior
- deleting the 9 Class A orphan-candidate KDs (they are evidence)
- deleting the Slice 2 Class C KD `8f825c98-…`
- modifying the empty-M2M broadcast semantics
- assuming Chris's embedding-preservation recollection is correct
- assuming Chris's embedding-preservation recollection is incorrect
- assuming cascade deletion is desirable
- assuming empty-M2M broadcast semantics is the root cause until mechanically proven
- implementing P2-lite
- fixing the Knowledge UI scope semantics

## §D. THE IMPORTANT DISTINCTION SESSION 275 MUST PRESERVE

From Slice 2 §21 — do NOT conflate:

- **DATA PRESERVATION** — the KD row, its chunks, and its embeddings survive character deletion. This may be intentional design (Chris recalls it was, for embedding-cost reasons — see §E). Not necessarily a defect.
- **RETRIEVAL ELIGIBILITY** — the surviving KD becomes visible to more teammates than the operator originally intended, because empty-`spokespeople` currently means "broadcast to all in scope."

These are separate concerns. The eventual defect may NOT be "knowledge should have been cascade-deleted." It may instead be **"preserved knowledge unintentionally became shared knowledge."** SESSION 275 must let the evidence pick which framing is correct.

## §E. CHRIS'S HISTORICAL HYPOTHESIS (verbatim from Slice 2 §22)

> Chris recalls that KnowledgeDocuments may have been intentionally preserved when deleting characters because deleting the associated chunk / embedding substrate was undesirable or unsafe. The exact historical implementation rationale has not yet been mechanically verified.

SESSION 275 must investigate whether repository history / ADRs / session docs / model comments / delete-path source support that recollection. Return one of:

- **CONFIRMED** — evidence directly supports the recollection
- **PARTIALLY SUPPORTED** — some elements match; others differ or are unproven
- **NOT FOUND** — no evidence either way; recollection can neither be confirmed nor falsified
- **CONTRADICTED** — evidence directly contradicts the recollection

Do not invent historical intent. Cite `file:line` and commit SHAs for any evidence.

## §F. PRIMARY INVESTIGATION SCOPE

Reconstruct the complete lifecycle **mechanically, read-only**:

```
Character / Teammate
        ↓
KnowledgeDocument.spokespeople M2M
        ↓
KnowledgeChunk
        ↓
embedding / pgvector data
        ↓
retrieval eligibility
        ↓
Composition provenance / history
```

### F.A. Character deletion path

- How is a `Teammate` deleted? SPA path (buttons, confirmations, side effects). API path (endpoint, permission, serializer, view, service). Django model deletion behavior (`on_delete` semantics). M2M through-table behavior (`KnowledgeDocumentSpokesperson`). Signals (pre_delete / post_delete). Cleanup jobs / archival behavior if any.

### F.B. Knowledge relationship on last-character delete

- Trace what happens to the `KnowledgeDocument` row, its `spokespeople` relation (specifically: does the M2M row on `KnowledgeDocumentSpokesperson` cascade with the teammate?), the `KnowledgeChunk` rows, the embedding vectors, ingestion metadata, source files if applicable, `Composition.knowledge_chunk_ids` provenance references, any historical references, when the LAST assigned character is deleted.

### F.C. Empty-M2M transition — the load-bearing question

Explicitly determine whether:

```
BEFORE:  KD spokespeople = { Character A }
                              ↓ (Character A deletion)
AFTER:   KD spokespeople = ∅
```

...and whether that surviving KD immediately becomes mechanically eligible as Class A or Class C **shared / broadcast** knowledge under `retrieve_for_teammate`'s existing `Q(spokespeople__isnull=True) | Q(spokespeople=teammate)` predicate.

**This is the load-bearing question.** Prove or falsify from source + a controlled read-only probe if possible; a destructive experiment (see §H) may be required and needs Chris's approval before it runs.

### F.D. Universe interaction

Test / source-trace BOTH possibilities:

1. `universe=None + last spokesperson deleted → does it become Class A?`
2. `universe=U + last spokesperson deleted → does it become Class C?`

If either holds, this means deletion may promote private knowledge into a broader audience at **two scope levels** — the whole workspace for legacy KDs, or the whole Universe for Universe-scoped KDs. Prove or falsify each independently.

## §G. PROBLEM-CLASSIFICATION FRAMEWORK

Once evidence is in, distinguish among (do not choose until evidence supports it):

- **A. NO BUG.** Preserved KDs remain non-retrievable or safely scoped. The current behavior matches original design intent AND does not accidentally promote knowledge audience.
- **B. LIFECYCLE SEMANTICS BUG.** Preservation is intentional; deletion broadens retrieval eligibility as an accidental side effect of overloaded empty-M2M semantics.
- **C. DELETION CLEANUP BUG.** Knowledge was intended to be removed / archived on character deletion but cleanup failed / was never implemented.
- **D. UI / OPERATOR BUG.** Backend behavior is intentional but the deletion UI fails to communicate what happens to knowledge (leaving operators unable to reason about the resulting scope).
- **E. MULTIPLE ISSUES** — some combination of B/C/D.

## §H. SAFE EXPERIMENT DESIGN (only if source cannot conclusively prove behavior)

If source / history cannot conclusively prove the lifecycle behavior, SESSION 275 MAY propose a controlled experiment using **new disposable substrate**:

- Do NOT use Ruby.
- Do NOT use Patch.
- Do NOT use Rivet.
- Do NOT use Mason.
- Do NOT use any production-important KD.
- Do NOT delete anything in `chriss-workspace` unless the experiment scaffolding lives entirely in a scratch workspace and Chris authorizes the destructive step.

Before executing any destructive lifecycle experiment:

- Create the experiment plan in a durable session doc.
- Define expected DB rows before / after.
- Define cleanup strategy (idempotent tear-down; leave no orphan side effects behind).
- Preserve UUIDs so the experiment is fully reconstructable.
- Verify no provider call is required.
- **Ask Chris for approval and WAIT.**

Do not execute destructive testing automatically.

## §I. SECONDARY QUESTION — ONCE LIFECYCLE IS CHARACTERIZED

Once the deletion lifecycle is understood, determine what an ideal lifecycle SHOULD mean. States worth evaluating:

- `ACTIVE CHARACTER-SPECIFIC`
- `ACTIVE UNIVERSE-SHARED`
- `ARCHIVED / INACTIVE`
- `UNASSIGNED BUT NON-RETRIEVABLE`
- `REASSIGNED`
- `DELETED`

Do NOT assume empty-M2M should change meaning globally. Consider whether **"no characters assigned"** and **"shared with all eligible characters"** should actually be two explicit states instead of one overloaded representation. This may ultimately connect to P2-lite or a future `KnowledgeAudience` model (P4 from Slice 1 §8.5).

Do not implement during the initial audit.

## §J. SESSION 275 STARTING CHECKLIST

- [ ] Verify repo / runtime baseline (main == origin/main, clean tree, services healthy, zero mock/experiment env drift)
- [ ] Trace character-delete SPA path (which button, which confirm, which endpoint call)
- [ ] Trace character-delete API path (view, serializer, service layer)
- [ ] Trace `Teammate` deletion model behavior (`.delete()`, `on_delete=` FKs pointing at Teammate, signals)
- [ ] Trace `KnowledgeDocument.spokespeople` M2M behavior on teammate delete (through-table `KnowledgeDocumentSpokesperson.on_delete`; cascade vs restrict vs set_null)
- [ ] Trace `KnowledgeChunk` / embedding lifecycle on KD change
- [ ] Trace historical `Composition.knowledge_chunk_ids` provenance implications
- [ ] Determine `universe=None + last-character deletion` semantics (does surviving KD become Class A?)
- [ ] Determine `universe=U + last-character deletion` semantics (does surviving KD become Class C?)
- [ ] Verify whether private → shared audience promotion can occur on deletion
- [ ] Investigate historical embedding-preservation rationale (§E): CONFIRMED / PARTIALLY SUPPORTED / NOT FOUND / CONTRADICTED
- [ ] Inspect deletion-related tests (`test_*delete*`, `test_teammate*`, `test_knowledge*`) for asserted invariants
- [ ] Inventory current suspected orphan KDs in `chriss-workspace` (the 9 Class A: TANK, Tulsi, 6× Hearth & Hollow, Riggs)
- [ ] Determine whether they are mechanically orphaned (e.g., inspect `created_by`, `updated_at`, any surviving audit trail)
- [ ] Investigate why the SPA cannot delete them (is delete intentionally absent? does an API delete path exist? is deletion forbidden by design for embeddings/provenance? is this merely missing SPA functionality?)
- [ ] Classify the lifecycle issue per §G (A / B / C / D / E)
- [ ] Decide whether a controlled destructive experiment (per §H) is required, and if so propose it for Chris's approval
- [ ] Only then consider product / lifecycle changes

Checkbox discipline: `[x]` only for evidence-backed completed work. Ambiguous prose does not substitute for a checkbox.

## §K. SECONDARY CANDIDATES (carried but NOT primary)

SESSION 275 should preserve but NOT begin with these:

| Item | Status | Notes |
| --- | --- | --- |
| **P2-lite implementation** | Leading candidate; NOT authorized | Slice 2 §14. Blocks on lifecycle characterization + Chris's explicit product-model decision. |
| **Knowledge scope UI cleanup** | Known problem; NOT fixed | Slice 1 §5 + Slice 2 §9. Reasonable Slice 3 target after lifecycle is understood — the deletion UI and the scope UI probably want a coherent redesign. |
| **One-page Episode creator** | SPA-only feasible (SESSION 273 §32) | Requires Chris authorization. |
| **Composition observability SPA** | 9 fields captured per render, not surfaced | Slice 1 §8.5 carried; not urgent. |
| **Mason companion dogfood** | Deferred (SESSION 273 §11.9 Slice ε) | Would strengthen wizard-default multi-domain verdict from n=2 to n≥3. |
| **PublishBundle dogfood** | Optional (SESSION 273 §11.9 Slice δ) | Assemble a small PublishBundle from Ruby Video #1 + #2. |
| **Compression-hint analog** | Carried from SESSION 272 §22.5.1 | `_compression_hint` still opens with `REWRITE THE SAME NARRATIVE BELOW`. |
| **Q-270-16 K6.4 verifier false positives** | Carried | Sentence-initial capitalized adverbs misclassified as proper nouns. |
| **YouTube ingest silent failure** | Memory `project_youtube_ingest_silent_failure` | Reports "processed" but trafilatura captures nothing. |
| **REPO RED Shape β** | Carried from SESSION 272 §22.5.5 | Canned-quote / voice-lock authoring pathology. |

**Primary SESSION 275 focus is knowledge lifecycle.** Do not precommit to any secondary item.

## §L. HARD RULES FOR SESSION 275

- Begin SESSION 275 with **read-only mechanical characterization** of the character-delete → KD lifecycle. Do NOT modify retrieval, UI copy, KD assignments, or the M2M table in the first slice.
- Do NOT delete the 9 Class A orphan-candidate KDs in `chriss-workspace`. They are evidence.
- Do NOT delete or modify the Slice 2 Class C KD `8f825c98-…`.
- Do NOT delete or modify Ruby's Class D KD `74e7f18f-…`.
- Do NOT modify Ruby, Patch, Rivet, Mason, or their personas / NarrativeMemory.
- Do NOT begin the render decision — SESSION 275 is a lifecycle audit, not a synthesis experiment.
- Do NOT begin P2-lite implementation.
- Do NOT begin the Knowledge UI scope cleanup.
- Do NOT assume Chris's embedding-preservation recollection is correct or incorrect.
- Do NOT begin a destructive lifecycle experiment without Chris's explicit approval (per §H).

## §M. SESSION 274 CLOSEOUT COMMIT + PROVENANCE

- SESSION 274 CLOSEOUT commit: **`<CLOSEOUT_SHA_PLACEHOLDER>`** (SHA recorded here in a follow-up commit per SESSION 273 precedent).
- Slice 1 characterization commit: `e7ff4a4`
- Slice 2 dogfood commit: `e96e33d`
- Full SESSION 274 commit trail: `git log --oneline docs/design/SESSION_274_*.md`

## §N. RECOMMENDED SESSION 275 START

1. `git status && git log --oneline -10` — verify main is at the SESSION 274 CLOSEOUT SHA (`<CLOSEOUT_SHA_PLACEHOLDER>`) and working tree is clean.
2. `bash scripts/start-local-real.sh` if services aren't already up.
3. Read `docs/design/SESSION_274_UNIVERSE_SHARED_KNOWLEDGE_DOGFOOD.md` §19–§24 (render decision, final verdicts, distinction between data preservation vs retrieval eligibility, Chris's historical recollection, closeout progression, non-change audit). Skim Slice 1 §2 (four-scope truth table) and Slice 2 §12 (retrieval matrix) for retrieval-mechanics context.
4. Confirm the 9 Class A orphan-candidate KDs are still present and unchanged in `chriss-workspace`.
5. Ask Chris: *before we characterize the character-delete → KD lifecycle, is there a specific operator scenario you want the audit framed around, or should we begin with a generic mechanical trace?* Do not steer.
6. First slice = read-only: trace the character-delete path from SPA to database, inspect `KnowledgeDocumentSpokesperson.on_delete`, any signals on `Teammate` deletion, and any tests that exercise this path.

---

**End of SESSION 275 handoff. SESSION 274 CLOSED. YELLOW verdict on flat cosine top_k accepted. P2-lite is the leading candidate direction, not authorized. No provider render was needed. Ruby's Fox & Flour Class C KD `8f825c98-…` is preserved as-is. The 9 Class A orphan-candidate KDs are preserved as-is and are the primary SESSION 275 evidence. Chris's historical embedding-preservation recollection is carried as unverified hypothesis. Chris decides SESSION 275 opening framing.**
