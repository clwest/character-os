# SESSION 276 — Handoff

Fresh-session starting point. SESSION 275 is CLOSED.

**Full SESSION 275 record** lives in a single durable document plus three commits:

- Audit + design + implementation + closeout: `docs/design/SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md` (§1–§61)
- Slice 1 (read-only audit) commit: `66c45fd`
- Slice 3 implementation commit: `89d21d3`
- Slice 3 SHA-record follow-up: `45e82f5`
- SESSION 275 CLOSEOUT commit: recorded below in §M

Read at minimum §61 (CLOSEOUT) of the audit doc before starting SESSION 276. This handoff is orientation, not a substitute.

---

## §A. WHAT SESSION 275 ESTABLISHED (short)

- Deleting a `Teammate` used to silently promote character-specific knowledge into workspace-shared (Class A) or Universe-shared (Class C) broadcast state. Empty M2M means "visible to all in scope" under the retrieval predicate.
- SESSION 275 adopted a non-negotiable invariant: *"A removal or deletion action must never broaden the audience of surviving knowledge unless the operator explicitly chooses that broader audience."*
- Enforcement (landed at `89d21d3`) — `pre_delete` snapshot + `post_delete` archive on `Teammate`. When a KD's spokespeople M2M goes from non-empty to empty as a direct result of a delete, the KD is archived: `is_active=False`, `deactivated_reason='orphaned_by_teammate_delete'`. Intentionally born-empty KDs (Class A / Class C canon) are untouched by construction.
- New `KnowledgeDocument.deactivated_reason` column distinguishes operator soft-delete (`operator_delete`) from system orphan-archive (`orphaned_by_teammate_delete`).
- Ingestion revival gate: dedup will not silently reactivate an orphan-archived KD into empty-M2M broadcast state — the caller must supply explicit new spokespeople, otherwise `OrphanRevivalRejected` → HTTP 400.
- The Teammate delete modal now discloses the knowledge lifecycle contract.
- 13 regression tests + full four-app regression pass. Atomicity proven by explicit failure-injection test (`transaction.atomic` + `QuerySet.update` patched to raise on `KnowledgeDocument`).
- The 9 pre-existing Class A orphan-candidate KDs in `chriss-workspace` (6× Hearth & Hollow, Tulsi, TANK, Riggs) are preserved unchanged as evidence. They were NOT auto-remediated by Slice 3 and their remediation remains a Chris-approved product decision.
- No recovery / operator UX shipped — Chris explicitly deferred a generic "Show archived + Restore" affordance because a bare `is_active=False → True` flip on an empty-M2M row would recreate the exact broadcast hazard the invariant prevents.

## §B. WHERE WE ARE

- SESSION 275 is CLOSED at the CLOSEOUT commit recorded in §M.
- `main == origin/main`. Working tree clean at closeout.
- Migration `0006_session275_deactivated_reason` applied.
- Retrieval predicate, Universe interactions, intentional Class A/Class C broadcast semantics — all unchanged.
- Ruby Class C `8f825c98-…` (Fox & Flour bakery hours), Ruby Class D `74e7f18f-…`, Patch, Rivet, Mason, and every other production teammate — all unchanged.

**Local-real runtime expected state** (verified at CLOSEOUT):

- Django `:8010/admin/` → 302
- Media-engine `:8001/health` → `{status:ok, openai_mock:false, runway_mock:false, image_gen_mock:false, any_mock:false, llm_provider:openai, llm_model:gpt-4o-mini}`
- Vite `:5174/` → 200
- Celery `character_os inspect ping` → 1 node online
- Zero mock / experiment env vars across running processes

## §C. SESSION 276 — OPENING PRODUCT QUESTIONS

SESSION 276 must begin with **AUDIT / ORIENT / PRODUCT DECISION** work. Do not open with implementation.

Two related but potentially separable questions inherit from SESSION 275:

### A. Legacy knowledge remediation

**What should happen to the 9 historical Class A orphan-candidate KDs in `chriss-workspace`?**

Anchor evidence (Slice 1 §2 / §12):

| # | UUID | Title | Chunks | Content shape |
|---|---|---|---|---|
| 1 | `aa90d895-…` | About Hearth & Hollow Books | 1 | Bookstore-specific |
| 2 | `e37ea174-…` | How We Recommend Books | 1 | Bookstore-specific |
| 3 | `b58efd31-…` | Children's Reading | 1 | Bookstore-specific |
| 4 | `7f41d8e3-…` | Bookstore Events | 1 | Bookstore-specific |
| 5 | `c408656d-…` | Supporting Local Authors | 1 | Bookstore-specific |
| 6 | `0088f31f-…` | Helping Customers Find Their Next Read | 1 | Bookstore-specific |
| 7 | `7ecde40b-…` | Tulsi — Core Identity and Public Purpose | 3 | Character self-description (Tulsi teammate no longer exists) |
| 8 | `8c6f0c14-…` | TANK — AUTOMOTIVE FINANCING CONTENT KNOWLEDGE | 22 | Character-specific brief (TANK teammate no longer exists) |
| 9 | `90ad200c-…` | Riggs | 1 | Character stub (Riggs teammate DOES currently exist; KD is unattached) |

All have `is_active=True, deactivated_reason='', universe=None, spokespeople=∅, created_by=chris@donkeybetz.com, ingested_via=paste`. All 8 of the first 8 KDs predate the SPA delete affordance (`dd5bf37`, 2026-08-17). Riggs KD was created same-day as the SPA delete landed.

Do NOT modify these KDs. Do NOT propose an auto-migration keyed on `spokespeople=∅` — that would destroy intentional Class C canon (Ruby's Fox & Flour bakery hours, etc.).

### B. Recovery UX

**What should an operator eventually be able to do with knowledge archived because its last assigned character was deleted?**

Possible recovery actions already identified (do NOT pre-commit to any):

- Attach / reassign to character(s).
- Explicitly promote / share to a Universe.
- Explicitly promote / share to the workspace.
- Leave archived (do nothing).

**Load-bearing constraint carried forward from SESSION 275 §47:** any future recovery flow that flips `is_active=False → True` on an `ORPHANED_BY_TEAMMATE_DELETE` KD MUST require an explicit safe-audience decision. A bare Restore is disallowed. This constraint is enforced today at the ingestion boundary; a future admin/API/SPA restore path must enforce it at the boundary before shipping. Slice 3 codified this as invariant, not preference.

## §D. HARD RULES FOR SESSION 276

- Begin SESSION 276 with **read-only audit + orient + product-decision work**. Do NOT modify KD rows, retrieval, signals, or UI in the first slice.
- Do NOT modify the 9 Class A orphan-candidate KDs.
- Do NOT modify Ruby's Class C `8f825c98-…` or Class D `74e7f18f-…`.
- Do NOT modify Ruby, Patch, Rivet, Mason, or any teammate.
- Do NOT begin building "Show archived" list, Restore button, or per-KD chooser UI without an explicit product decision + Chris approval.
- Do NOT weaken or change the SESSION 275 no-audience-broadening invariant.
- Do NOT auto-remediate the 9 KDs on the basis of any single heuristic — content shape hints (character-name titles) are informative but not authoritative without evidence.
- Do NOT begin Option C (explicit `KnowledgeAudience` model) or Option E (per-KD chooser on delete) without explicit Chris approval — both remain future possibilities, not committed direction.
- Do NOT bypass the SESSION 275 ingestion revival gate (`OrphanRevivalRejected`).
- Do NOT change the retrieval predicate (`shell/apps/embeddings/retrieval.py:216-220`) — it remains the invariant surface for scope decisions.

## §E. RECOMMENDED SESSION 276 START

SESSION 276 should NOT be pre-committed to implementation.

1. `git status && git log --oneline -10` — verify main is at the SESSION 275 CLOSEOUT SHA (§M below) and working tree is clean.
2. `bash scripts/start-local-real.sh` if services aren't already up.
3. Read `docs/design/SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md` §61 (CLOSEOUT) end-to-end, then skim §12 (the 9 KD inventory), §27 (the load-bearing distinction canon-vs-orphaned), §30 (reactivation audit), §46 (future recovery invariant), §47 (ingestion revival gate details).
4. Ask Chris: *before we open Question A (legacy remediation) or Question B (recovery UX), do you want them scoped as one bundled slice, two separate slices, or does one block on the other?* Do not steer.
5. First slice = read-only: for legacy remediation, inspect the actual 9 KDs in detail (source_metadata, created_by, content sample, timestamp clustering, any surrounding audit log evidence). For recovery UX, inspect the actual `KnowledgeDocument` admin + SPA surfaces + API endpoints already available for reassign / restore / audience-change, and enumerate what an operator can and cannot do today. Cite `file:line` and DB evidence.
6. Formulate falsifiable questions before touching code or data. Examples of the shape (do not lock in as final):
   - Can each of the 9 KDs be classified as "orphaned by past character delete" vs "intentionally shared canon" using surviving evidence (source_metadata, git log, ingestion logs)? If not, what evidence would be sufficient?
   - Is any of the 9 currently reachable by a live teammate under the current retrieval predicate? (Runtime observation, not source claim — cosine distance vs specific queries.)
   - Should recovery UX and legacy remediation live in the same slice (they share the "safe audience decision" primitive) or separate slices (legacy is a one-shot triage; recovery is an ongoing product surface)?
   - If we ship recovery UX first, does that unblock legacy remediation? Or vice versa?

## §F. SECONDARY CANDIDATES (carried but NOT primary)

SESSION 276 should preserve but NOT begin with these:

| Item | Status | Notes |
| --- | --- | --- |
| **Option C — explicit `KnowledgeAudience` model** | Deferred | SESSION 275 §36. Long-term-correct replacement for empty-M2M overload. Pairs with SESSION 274 §8.5 P4 / P2-lite. Weeks of work. |
| **Option E — per-KD chooser on delete modal** | Deferred | SESSION 275 §25. UX complement to Option C. |
| **P2-lite** | SESSION 274 leading candidate | Independent scope + M2M merge for retrieval. Not authorized. |
| **Composition observability SPA** | SESSION 274 §K carryover | 9 fields captured per render, not surfaced. |
| **PublishBundle dogfood** | SESSION 274 §K carryover (Slice δ) | Optional. |
| **Mason companion dogfood** | SESSION 273 §11.9 Slice ε | Strengthens wizard-default multi-domain verdict from n=2 to n≥3. |
| **YouTube ingest silent failure** | Memory `project_youtube_ingest_silent_failure` | Reports "processed" but trafilatura captures nothing. |
| **REPO RED Shape β** | SESSION 272 §22.5.5 carryover | Canned-quote / voice-lock authoring pathology. |
| **Compression-hint analog** | SESSION 272 §22.5.1 carryover | `_compression_hint` still opens with `REWRITE THE SAME NARRATIVE BELOW`. |
| **Q-270-16 K6.4 verifier false positives** | SESSION 274 §K carryover | Sentence-initial capitalized adverbs misclassified as proper nouns. |
| **Bootstrap-review + media-engine-timeouts pre-existing failures** | Not SESSION 275's scope | Documented in audit doc §61. Fresh session should read that section before running the full suite. |

**Primary SESSION 276 focus is the two product questions in §C.** Do not precommit to any secondary item.

## §G. LIVE-STATE INVARIANTS THAT MUST REMAIN TRUE

Fresh session should verify these before any change:

- The 9 Class A orphan-candidate KDs in `chriss-workspace` are still `is_active=True, deactivated_reason='', universe=None, spokespeople=∅`.
- Ruby's Class C `8f825c98-…` and Class D `74e7f18f-…` remain unchanged.
- Migration `0006_session275_deactivated_reason` is applied.
- `apps/embeddings/retrieval.py` is byte-identical to `89d21d3`.
- The Teammate delete signal pair (`_stash_kd_membership_for_orphan_check` + `_archive_orphaned_kds_on_teammate_delete`) is registered on Teammate `pre_delete` + `post_delete`.
- The ingestion revival gate (`ingestion.OrphanRevivalRejected`) rejects orphan-archived KD revival without explicit spokespeople.
- The delete modal copy contract test passes.
- No new mock / experiment env vars are set on the running processes.

## §H. HARD NON-GOALS

Same as SESSION 275 §L, forward-copied:

- Do NOT change retrieval, UI copy for shipped surfaces, KD assignments, or the M2M table in the first slice.
- Do NOT delete or modify the 9 Class A orphan-candidate KDs.
- Do NOT delete or modify the Slice 2 Class C KD `8f825c98-…`.
- Do NOT delete or modify Ruby's Class D KD `74e7f18f-…`.
- Do NOT modify Ruby, Patch, Rivet, Mason, or their personas / NarrativeMemory.
- Do NOT begin a destructive experiment without Chris's explicit approval.
- Do NOT change the enforced audience-invariant behavior.

## §I. USEFUL PROCESS FINDINGS PRESERVED

Recorded here so a fresh session inherits the durable engineering lessons rather than rediscovering them:

- The originally proposed single-`pre_delete` design (Slice 2 §37 pseudocode) was falsified by the bulk-delete-shared-KD test (test 9). Splitting into `pre_delete` snapshot + `post_delete` archive was the version proven by tests, not a stylistic choice. Preserved in §57 of the audit doc.
- Reasoning-only acceptance of atomicity was rejected by Chris + ChatGPT during Slice 3 review. The explicit failure-injection test (test 13) was added post-review and closed the gap. Preserved in §50 and §60.
- SPA delete affordance discoverability (§13, §30) matters — the SPA delete button existed on `/workspace/knowledge` since `dd5bf37` but Chris didn't find it because it isn't cross-linked from the Teammate detail page. Recovery UX design should not repeat that mistake.
- Empty-M2M overloading is real. "No spokesperson selected" currently means "broadcast to all in scope." Any future model (Option C) that replaces this overloading should preserve the SESSION 275 invariant during migration — not just at steady state.

## §J. SESSION 276 STARTING CHECKLIST

- [ ] Verify repo / runtime baseline (main == origin/main, clean tree, services healthy, zero mock / experiment env drift)
- [ ] Confirm the 9 Class A orphan-candidate KDs still meet §G invariants
- [ ] Confirm Ruby Class C + Class D unchanged
- [ ] Confirm `0006_session275_deactivated_reason` applied
- [ ] Confirm the Teammate delete signal pair is registered (grep `pre_delete\|post_delete` in `shell/apps/spokespeople/signals.py`)
- [ ] Confirm the ingestion revival gate still raises on orphan-archived-without-spokespeople (targeted test rerun)
- [ ] Ask Chris the scoping question (§E step 4)
- [ ] Formulate falsifiable product questions before proposing implementation
- [ ] Do NOT begin implementation

Checkbox discipline: `[x]` only for evidence-backed completed work. Ambiguous prose does not substitute for a checkbox.

## §K. SECONDARY CANDIDATES

See §F — same set as SESSION 275 carried forward; SESSION 275 did not touch any of them.

## §L. RECOMMENDED SESSION 276 START (concise)

1. Verify baseline (§J).
2. Read §61 of the audit doc.
3. Ask Chris the scoping question in §E step 4 — do NOT steer.
4. Read-only investigation of the 9 KDs and the current recovery-UX surface — cite file:line + DB evidence.
5. Formulate falsifiable product questions.
6. STOP and align with Chris on Slice 1 scope before any implementation.

## §M. SESSION 275 CLOSEOUT COMMIT + PROVENANCE

- SESSION 275 CLOSEOUT commit: **`05e6f8f`** (2026-08-21).
- Slice 1 audit commit: `66c45fd`
- Slice 3 implementation commit: `89d21d3`
- Slice 3 SHA-record follow-up: `45e82f5`
- Full SESSION 275 commit trail: `git log --oneline docs/design/SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md`

---

**End of SESSION 276 handoff. SESSION 275 CLOSED. Audience-broadening invariant enforced. The 9 legacy Class A orphan-candidate KDs preserved as evidence. Ruby's Class C `8f825c98-…` and Class D `74e7f18f-…` preserved as-is. Recovery UX explicitly deferred with the load-bearing constraint that no bare `is_active=False → True` revival is permitted. Chris decides SESSION 276 opening scope — legacy remediation vs recovery UX, bundled or separate.**
