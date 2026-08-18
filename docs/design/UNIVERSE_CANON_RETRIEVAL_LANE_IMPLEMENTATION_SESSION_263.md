# UNIVERSE CANON RETRIEVAL LANE — IMPLEMENTATION SESSION 263

**Status:** implementation report. Ships slice B + C.1 from
`docs/design/UNIVERSE_CANON_RETRIEVAL_LANE_AUDIT_SESSION_263.md`
verbatim to the operator's brief. No provider call, no real render.

**Companion audits:**

* `docs/design/PATCH_RIVET_RUNTIME_CONTENT_ARCHITECTURE_AUDIT_SESSION_263.md`
  — the runtime evidence + hypothesis.
* `docs/design/UNIVERSE_CANON_RETRIEVAL_LANE_AUDIT_SESSION_263.md`
  — the architecture comparison + preferred slice.

---

## 1. What shipped

Two files touched in production code; two new test files; one
allowlist entry.

### 1.1 `apps/embeddings/retrieval.py`

* New public function `retrieve_universe_canon(workspace, universe,
  cast, query, top_k=2, *, _query_vector=None)`.
* Shared-tier predicate matches the audit definition exactly:
  Universe-scoped AND `is_active` AND `status='processed'` AND
  (M2M-null OR M2M covers every cast member with count > 1).
* Cast-Universe defensive gate — returns empty when the cast spans
  Universes or any member is universe-less. Belt-and-suspenders vs.
  `synthesize_dialogue`'s own guard.
* Cosine ordering + `LIMIT top_k` mirrors `retrieve_for_teammate`
  exactly.
* Two-step doc resolution (chained "has all of" filter → fresh
  `Count` on candidate IDs) to sidestep the annotation-on-chained-
  M2M-joins subtlety that silently drops rows.
* `retrieve_for_teammate` semantics unchanged. `retrieve_for_thread`
  untouched. No other consumer affected.

### 1.2 `character_os/dialogue_synthesis.py`

* `synthesize_dialogue` now runs one canon-lane retrieval per
  synthesis (not per character) when `use_knowledge=True` AND a
  Universe is present on the cast.
* Canon lane is gated by `use_knowledge` — `use_knowledge=False`
  disables BOTH character retrieval and the canon lane, per brief.
* Canon lane failure is non-fatal: logs a warning and proceeds
  without shared canon (same posture as per-character failure).
* Mock branch (`force_mock`) skips the canon lane — no provider
  hops.
* `_assemble_system_prompt` grows a `shared_chunks` parameter,
  plumbed to `_build_factual_basis_section`.
* `_build_factual_basis_section` gains a `shared_chunks`
  parameter. SHARED emission is now deterministic from the B pass;
  the post-hoc detector is replaced by C.1 scope-aware promotion
  (see §1.3).
* K6.4 corpus wiring: each speaker's factual corpus receives
  `shared_chunks + per_character_chunks[alias]`. Character
  isolation preserved (Patch's corpus never contains Rivet's
  per-character K2, and vice versa).
* `DialogueResult.chunk_ids` aggregation places canon chunk IDs
  FIRST (dedup-safe), followed by per-character IDs.
* Failed-composition rescue path (`DialogueSynthesisError.chunk_ids`)
  also captures canon IDs so the FAILED-composition observability
  preserves the same provenance the accepted path would have
  persisted.
* Prompt block heading renamed from "SHARED WORKSPACE KNOWLEDGE" to
  "SHARED WORLD KNOWLEDGE" to match the audit's canon vocabulary.
  Prompt block semantics are otherwise unchanged.

### 1.3 New helper `_is_scope_shared_document` (C.1 fix)

* Returns True iff `doc.spokespeople.count() == 0` (Universe-wide
  broadcast) OR `> 1` (explicit shared canon).
* Used by `_build_factual_basis_section` to promote scope-shared
  chunks that leak into per-character retrieval on high cosine
  relevance. Fixes the pre-SESSION-263 latent bug where such
  chunks were emitted under a character SCOPED block and the §1
  SCOPE RULE told the OTHER character it could not cite them —
  denying access to a fact the retrieval scope filter grants.

### 1.4 `apps/embeddings/tests/test_retrieval_universe_canon.py` (new)

14 focused tests covering:

* Empty-input guards — no Universe, empty cast, `top_k=0`.
* Positive cases — M2M-null broadcast, M2M-many covering full cast.
* Negative cases — M2M count = 1 (character-only), M2M covering
  some-but-not-all cast members.
* Isolation — cross-Universe blocked, legacy doc blocked from
  Universe cast, cast spanning Universes blocked, cross-workspace
  blocked.
* Ranking + bounded budget — `top_k=2` caps output, cosine
  ordering ascending.
* Empty-canon regression — Universe with only character-scoped
  docs returns empty (does not accidentally include per-character
  docs).

### 1.5 `apps/compositions/tests/test_dialogue_synthesis_canon_lane.py` (new)

8 focused tests covering:

* Canon retrieval fires once per synthesis with full cast +
  verbatim topic + `top_k=2`.
* `use_knowledge=False` disables both retrieval calls.
* Universe-less cast skips canon call.
* Canon chunk lands in SHARED WORLD KNOWLEDGE block in the assembled
  prompt.
* `Composition.knowledge_chunk_ids` (via `DialogueResult.chunk_ids`)
  contains canon chunk IDs first, plus per-character IDs deduped.
* Every speaker's K6.4 factual corpus contains the canon text (so
  canon-cited facts pass verification for either speaker) — with
  character isolation preserved between per-character K2.
* C.1 promotion — a scope-shared chunk leaked into per-character
  retrieval is emitted under SHARED, not under the character's
  SCOPED block.
* C.1 negative — a chunk from a doc with M2M count = 1 stays in
  that character's SCOPED block.

### 1.6 `apps/embeddings/tests/test_retrieval_privacy.py`

One-line addition to `ALLOWED_FILES` for the new
`test_retrieval_universe_canon.py`, following the pattern
established by `test_retrieval_universe.py`. K0 contract rule 2 —
only sanctioned code paths query `KnowledgeChunk` directly.

---

## 2. Test results

```
apps/embeddings/tests/test_retrieval_universe_canon.py     14 passed
apps/compositions/tests/test_dialogue_synthesis_canon_lane.py  8 passed
apps/compositions/tests/test_dialogue_synthesis.py         (pre-existing, all green)
apps/embeddings/tests/test_retrieval_universe.py           (pre-existing, all green)
apps/embeddings/tests/test_retrieval_privacy.py            (pre-existing, all green)
apps/compositions/tests/test_dialogue_ai_topic_wiring.py   (pre-existing, all green)
apps/compositions/tests/test_session262_composition_observability.py  (pre-existing, all green)
apps/universe/tests/*                                       (pre-existing, all green)
apps/embeddings/**                                          (all green)
```

Full sweep across the touched neighbourhood:

```
361 passed in 33.57s
```

Zero regressions in adjacent suites; new coverage additive.

---

## 3. Preflight verification — exact operator topic

Read-only probe against the persisted Patch's Workshop DB rows,
calling the new retrieval functions with the same arguments
`synthesize_dialogue` would use for the Episode
`AI took over the lab` at 60 s. No LLM call. No render. No writes.

```
topic  : 'AI took over the lab'
cast   : [Patch, Rivet]  universe: Patch' Workshop

=== SHARED Universe canon (canon-pass + C.1 promotions) (1 chunk) ===
  [canon-pass] chunk=da7e6553...  doc="PATCH'S WORKSHOP — SHARED CANON"  idx=0  dist=0.7598

=== PATCH scoped knowledge (5 chunks) ===
  chunk=da2fc3ed...  doc='PATCH — AI BUILDING, EXPERIMENTATION & CONTENT KNOWLEDGE'  idx=11  dist=0.6241
  chunk=3c5165ea...  doc='PATCH — AI BUILDING, EXPERIMENTATION & CONTENT KNOWLEDGE'  idx=4   dist=0.6492
  chunk=ed18e966...  doc='PATCH — AI BUILDING, EXPERIMENTATION & CONTENT KNOWLEDGE'  idx=1   dist=0.6594
  chunk=1b98ba6a...  doc='PATCH — AI BUILDING, EXPERIMENTATION & CONTENT KNOWLEDGE'  idx=6   dist=0.6738
  chunk=505acbba...  doc='PATCH — AI BUILDING, EXPERIMENTATION & CONTENT KNOWLEDGE'  idx=3   dist=0.6739

=== RIVET scoped knowledge (5 chunks) ===
  chunk=80811ca8...  doc='RIVET — EXPERIMENTATION, TESTING & WORKSHOP KNOWLEDGE'  idx=4   dist=0.6554
  chunk=6f43e6f0...  doc='RIVET — EXPERIMENTATION, TESTING & WORKSHOP KNOWLEDGE'  idx=7   dist=0.6769
  chunk=fac8c122...  doc='RIVET — EXPERIMENTATION, TESTING & WORKSHOP KNOWLEDGE'  idx=5   dist=0.6874
  chunk=1aa4e0b2...  doc='RIVET — EXPERIMENTATION, TESTING & WORKSHOP KNOWLEDGE'  idx=11  dist=0.7024
  chunk=fb84ba3d...  doc='RIVET — EXPERIMENTATION, TESTING & WORKSHOP KNOWLEDGE'  idx=0   dist=0.7081

=== Composition.knowledge_chunk_ids preview (11 unique) ===
['da7e6553-a5ea-463f-994f-354289ab9b5b',   # canon
 'da2fc3ed-50d8-4cbd-b45e-a226d5b08329', '3c5165ea-c97f-4412-b8e7-b46d91777ae9',
 'ed18e966-1084-4626-914f-1bcc30f13dea', '1b98ba6a-7996-43a4-a99c-a3e15947cd95',
 '505acbba-fbc4-41b2-8494-4c937a3e3e28',   # ← Patch top-5 end
 '80811ca8-002e-4822-9f5c-a37da5a6a411', '6f43e6f0-13a4-49bf-bd1b-ac666a39d68c',
 'fac8c122-9f09-463b-b268-614ccc46cc2e', '1aa4e0b2-b151-4537-ab9f-fa86cb343e44',
 'fb84ba3d-b486-4f8d-a2bc-d47445af475a']   # ← Rivet top-5 end
```

Observations:

1. **The canon chunk (`da7e6553…`) now enters SHARED** on the exact
   `"AI took over the lab"` topic. Under the pre-SESSION-263
   `top_k=5` competition, this chunk landed at rank 9 (Rivet) / 17
   (Patch) and never entered synthesis.
2. **Per-character retrieval is unchanged** — same 5+5 chunks as
   the archived 60 s / 90 s dogfood. Character depth preserved
   (no `top_k` reduction).
3. **Aggregate `knowledge_chunk_ids` has canon-first ordering** —
   provenance panels can identify canon by position.
4. **C.1 did not fire on this Universe** — no scope-shared chunk
   leaked into per-character retrieval, so the C.1 promotion path
   ran but had nothing to promote. This is correct behaviour for
   a Universe where the shared canon didn't clear per-character
   top-5 on its own.
5. **Distance figures preserved:** canon at 0.7598 (rank 9 vs.
   Rivet top-5 which caps at 0.7081; rank 17 vs. Patch top-5
   which caps at 0.6739). The canon lane admitted the chunk on
   scope, not on relevance-tier competition — exactly the audit's
   design intent.

---

## 4. What did NOT change (guard-rail confirmation)

* `retrieve_for_teammate` signature and semantics.
* Character `top_k=5` in dialogue synthesis.
* Non-dialogue retrieval consumers (`script_synthesis`,
  `teammate_ask`, `realtime_document`, `recall_knowledge`,
  `retrieve_for_thread`).
* `KnowledgeDocument` schema.
* `Universe` schema.
* `Episode` schema or wiring.
* Writing Contract v4.
* `_call_dialogue_api` / OpenAI call shape.
* Any distance/relevance threshold — canon lane admits its top-2
  by cosine, no floor.
* Any Composition state machine transition.
* Any migration (zero migrations added).

---

## 5. Files changed

```
shell/apps/embeddings/retrieval.py                                 (+118 -1)
shell/character_os/dialogue_synthesis.py                           (+108 -32)
shell/apps/embeddings/tests/test_retrieval_universe_canon.py       (new)
shell/apps/compositions/tests/test_dialogue_synthesis_canon_lane.py (new)
shell/apps/embeddings/tests/test_retrieval_privacy.py              (+7)
docs/design/UNIVERSE_CANON_RETRIEVAL_LANE_IMPLEMENTATION_SESSION_263.md (new — this file)
```

No provider calls made during implementation or verification.

---

## 6. Deferred (per audit; explicitly out of scope for this slice)

* Distance floor / relevance ceiling for canon lane (audit U1).
* Configurable `shared_top_k` (audit U2 — fixed at 2 for now).
* Canon lane in non-dialogue consumers (audit U3).
* Separate `canon_chunk_ids` observability field (audit U4 —
  commingled with `knowledge_chunk_ids`, canon-first ordering
  gives ordering-based provenance).
* Query-independent canon (audit U5 — cosine still ranks canon
  against query).
* Canon-authoring SPA affordance (audit U6).
* Universe schema field for explicit canon listing (audit U7).
* Any Writing Contract v4 change (SESSION 263 content-architecture
  audit deferred as separate slice).

---

## 7. Ready state for the dogfood

* Canon document already exists at DB row
  `f309469c-8167-434e-ad10-54c4ec1dc86f`, chunk
  `da7e6553-a5ea-463f-994f-354289ab9b5b`, universe
  `56d16b63-…` (Patch's Workshop), M2M scope = {Patch, Rivet}.
* The preflight in §3 confirms this chunk will enter the SHARED
  §1 block on re-render of the exact same Episode
  (`f90ce54f-07f9-4511-aaba-9078dc232446`) at 60 s.
* No further preparation required. The operator can fire the
  render from the SPA; the AI side will tail the persisted
  observability post-render.
