---
title: "Session 137 — Knowledge Layer scope lock (no code)"
date: 2026-05-14
status: complete
session: 137
previous_handoff: ./SESSION_136_CAST_WENT_LIVE.md
---

# Session 137 — Knowledge Layer scope lock

## TL;DR

- **What shipped:** `docs/design/KNOWLEDGE_LAYER.md` (783 lines) —
  the scope-lock doc for the knowledge-layer arc. Follows the
  `CREATE_SPOKESPERSON_WIZARD.md` pattern: contract rules, data
  model, retrieval surface, ingestion pipeline, operator surfaces,
  render + conversation flow integration, migration plan, slice
  breakdown (K1 → K10), out-of-scope list, open questions, and a
  privacy-guarantee test contract. **No code yet.** Two project/
  feedback memories saved to capture session-level calibration that
  must survive into future sessions (cast-is-example-data,
  hackathon knowledge-leak precedent).
- **What's blocking next:** Nothing. SESSION 138 is **K1 — Postgres
  + pgvector migration** (infra-only, zero user-visible value, but
  forcing function for everything downstream).
- **What's in a weird state:** Same as SESSION 136 — e2e in
  real-mode still needs the `mv .env .env.real` workaround.
  `RUNWAY_FORCE_MOCK=1` env override is still queued as a tiny
  unblocker; consider knocking it out before K1 starts so the
  Postgres-migration verification has a clean test surface.

---

## What changed

This was a design session. Three artifacts landed:

### `docs/design/KNOWLEDGE_LAYER.md` (new, 783 lines)

The scope-lock doc. Highlights of what's locked vs. left open:

**Seven contract rules** (load-bearing for every slice):

1. Explicit `KnowledgeDocument.workspace` FK, never derivable
   through M2M.
2. Retrieval flows through exactly two named functions in
   `apps/embeddings/retrieval.py`.
3. Workspace scoping is unconditional — no bypass parameter
   exists.
4. Documents and conversation turns live in **separate tables**,
   not discriminated rows.
5. Content-hash dedup at ingest. `(workspace, content_hash)`
   unique constraint. Re-embedding loops cost zero.
6. Render degrades gracefully on empty knowledge.
7. No cross-workspace knowledge sharing in v1.

**Five locked design decisions:**

1. Spokesperson visibility — M2M `Spokesperson ↔ KnowledgeDocument`,
   empty = visible to all spokespeople in workspace.
2. RAG location — shell does the retrieval + script synthesis, sends
   the finished `brief` to media-engine. Contract with media-engine
   unchanged (it still receives `body.brief` as a pre-built string).
3. URL ingestion — paste OR serper-discovery → single fetch+extract
   pipeline → ingest. `trafilatura` for extraction.
4. Onboarding seed — yes, but only for `Workspace.is_operator=True`.
   Customer workspaces bring their own. Source-of-truth =
   `docs/seeds/character_os/*.md`.
5. Postgres + pgvector migration is **K1** — the first slice in the
   arc.

**Two privacy guarantees** designed in (motivated by the prior
hackathon leak — see AI notes below):

- **Workspace anchor:** required FK + cross-workspace check on
  save + `m2m_changed` signal. Unique constraint
  `(workspace, content_hash)`. Single named retrieval function
  `retrieve_for_spokesperson(spokesperson, query, top_k)`.
- **Conversation isolation:** separate `ConversationMessage` +
  `ConversationEmbedding` tables, distinct from
  `KnowledgeDocument` + `KnowledgeChunk`. Separate retrieval
  function `retrieve_for_thread(thread, query, top_k_docs,
  top_k_history)`. Cross-thread bleed is structurally impossible.

**Three privacy tests** the implementation must pass before K2
closes (named in the doc under §"How to verify the privacy
guarantee"):

1. `test_cross_workspace_chunk_isolation`
2. `test_cross_thread_conversation_isolation`
3. `test_only_retrieval_module_queries_chunk_tables`
   (repo-level grep test — enforces rule #2)

**Slice breakdown:** K1 (Postgres) → K2 (KnowledgeDocument +
KnowledgeChunk + retrieval skeleton) → K3 (ingestion: paste +
PDF) → K4 (workspace knowledge route) → K5 (spokesperson
Knowledge tab) → K6 (render flow integration) → K7 (URL +
serper) → K8 (conversation models) → K9 (conversation REST +
SPA) → K10 (onboarding seed). 8-12 sessions total.

### `memory/feedback_cast_is_example_data.md` (new)

Project-scoped feedback memory. Captures the early framing
correction: Riggs/Sasha/Donny/Maya are seeded example data, not
product shape. Spokesperson capabilities (render + converse) are
universal. The trap is generalizing from a cast member's specific
`business_brief` framing into a product-level feature — what I did
when I called it "Maya's tutor mode."

### `memory/project_hackathon_knowledge_leak.md` (new)

Project memory. Captures the prior incident: in the
runway-hackathon predecessor, an avatar referenced **context-kit**
instead of staying on the hackathon platform. This is the
load-bearing motivation for the K0 privacy guarantees — same
failure mode, must not recur in character-os.

### `memory/MEMORY.md` (new)

Project memory index file, pointing at the two memories above.

---

## How we got here (conversation arc)

The session is worth reading because the *path* to the locked
decisions matters more than the decisions themselves. Three
non-obvious moves:

### 1. The u-d-b reconnaissance

~30 min reading u-d-b's `content/` + `core/conversation_memory.py`
+ `core/rag_integration.py` + `self_awareness/embeddings.py`.
Found two parallel RAG systems coexisting (the old `core/rag.py`
file-based one + the production `content/`-app one). The
production one has the shape we want; the older `unified_embeddings`
raw-SQL one we're *not* porting.

Key prior-art findings: `Document` + `DocumentEmbedding` +
`KnowledgeBase` schema (pgvector 1536 + HNSW index m=16
ef_construction=64), `TextSplitter` with chunk_size=1000
chunk_overlap=200, `process_document_for_rag_sync` for Celery,
`text-embedding-3-small` as the default model, content_hash
dedup pattern in `self_awareness/embeddings.py` (which I
initially missed and the operator caught).

### 2. Three framing corrections during the conversation

These are why the final doc shape isn't the shape we started with:

- **Framing 1 — Cast is example data, not product shape.** I
  framed axis 5 of the start-here doc as "Maya's tutor-mode
  tie-in." Operator: every spokesperson has the same shape; Maya's
  tutor framing is just one operator's choice of `business_brief`.
  Saved as feedback memory.
- **Framing 2 — Axis 2 wasn't really three options.** Start-here
  framed scope as "per-spokesperson vs per-workspace vs hybrid."
  After u-d-b read: only workspace-level KB + per-spokesperson
  visibility filter doesn't fork the system. The three "options"
  were one option in disguise.
- **Framing 3 — Cost concern was 20× overstated.** Initial
  pushback proposed a per-workspace upload cap. Operator caught
  the math: 500-page PDF is ~$0.025 not $0.50; 100 PDFs is
  ~$2.50 not $50. Real cost protection is `content_hash` dedup,
  which u-d-b already has. Dropped the cost-cap concern;
  surfaced "must port the dedup step from u-d-b" as a contract
  rule instead.

### 3. The hackathon-leak precedent

Mid-conversation the operator mentioned: in the runway-hackathon
predecessor an avatar leaked context (referenced context-kit when
it should have stayed on the hackathon platform). This is
*exactly* the failure mode the high-severity scoping concerns
described — a real prior instance, not a hypothetical. It
hard-anchored the design toward "structural correctness, not
remembered filters." Saved as project memory because future
sessions implementing K2/K6 need to remember this is a real
incident, not a paranoid hypothetical.

---

## Queued investigations (priority-ordered)

Re-ordered now that the scope-lock is done. K-prefix items are
the knowledge-layer slices (locked sequence in
`docs/design/KNOWLEDGE_LAYER.md` §"Slice breakdown").

1. **K1 — Postgres + pgvector migration.** First implementation
   slice. Infra-only.
2. **`RUNWAY_FORCE_MOCK=1` env override** — still tiny, still
   worth landing before K1 verification so the e2e suite is
   clean during migration verification.
3. **K2 — `KnowledgeDocument` + `KnowledgeChunk` + retrieval
   skeleton.**
4. **K3 — Ingestion pipeline (paste + upload + PDF).**
5. **K4 — Workspace knowledge route (SPA + REST).**
6. **K5 — Spokesperson "Knowledge" tab.**
7. **K6 — Render flow integration.**
8. **K7 — URL ingestion + serper discovery.**
9. **K8 — Conversation models.**
10. **K9 — Conversation REST + SPA.**
11. **K10 — Onboarding seed.**
12. **Voice preset audit** — happens naturally once first
    real-mode knowledge-informed renders land (post-K6).
13. **First marketing video** — happens naturally once K6 lands.
14. **W11.1 — Edit-spokesperson modal.**
15. **W12 — Legacy form retirement.**
16. **Cast sync command.**
17. **Tier 2 prompt helpers** — likely subsumed by K6's
    `script_synthesis.synthesize()` step.
18. **Stuck-row janitor.**
19. **Additional video kinds** — cinematic / dialogue / long_ad.
20. **Act-Two performance capture.**
21. **`lesson` video kind.**
22. **Real Google OAuth + dj-stripe.**
23. **Allauth legacy-settings cleanup.**
24. **smoke_voice / smoke_avatar transaction discipline.**
25. **Drift verifier** (`verify_doc_claims --only-drift`).
26. **Brand Identity v2 + dark mode.**

---

## AI notes

- **Pattern that worked: u-d-b recon before the conversation.**
  The operator's pre-session instruction was "spend ~30 min
  reading u-d-b first." That instruction was load-bearing — three
  of the seven contract rules came directly out of patterns I'd
  have invented worse versions of without seeing the prior art
  (content_hash dedup, separate-table vs discriminator, HNSW
  index params). Future arcs that open with a "design before
  code" conversation should default to: read the predecessor
  repo first, then converge.
- **Calibration event: the cost-math correction.** I proposed a
  per-workspace upload cap as a "medium-severity" concern; the
  operator empirically knew it was wrong ("I've embedded 3-hour
  YouTube videos for cents"). I re-did the math and was off by
  ~20×. **Lesson: when proposing a guard against a hypothetical
  problem, do the actual arithmetic first.** "$50 in surprise
  embedding costs" sounded plausible; the real number was
  $2.50. Operator's empirical instinct beat my overcautious
  math.
- **Calibration event: the hackathon leak precedent.** When
  surfacing concerns A and B (workspace anchor + conversation
  scoping), I framed them as "high-severity but theoretical."
  The operator surfaced a real prior incident in seconds. This
  is the second time in two sessions (also SESSION 136's
  "step back, what do they talk about?" moment) the operator
  has caught me reasoning about hypotheticals when concrete
  prior incidents existed. **Default forward: ask for prior
  art before grading severity on hypotheticals.**
- **Pattern that worked: pushing back when framing looked
  wrong.** Three times in this session I told the operator
  "the framing as stated isn't quite right" — once for cast-as-
  example-data, once for axis-2-isn't-really-three-options,
  once acknowledging my own cost math was wrong. The
  conversation converged faster because of these moments, not
  in spite of them. Continue this pattern in K2+ slice
  planning — push back when the framing of a sub-question
  looks off, don't just answer the question as asked.
- **The doc itself is ~200 lines longer than the wizard
  scope-lock.** That's because the knowledge layer has two
  things the wizard didn't: (1) a privacy contract that needs
  to be spelled out structurally (not just procedurally), and
  (2) a migration plan as K1. Both earn their lines. Future
  arcs that touch privacy + infra forcing functions should
  expect ~700-800 line scope-locks; pure feature arcs are
  closer to 500.
