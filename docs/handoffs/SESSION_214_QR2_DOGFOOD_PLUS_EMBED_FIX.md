---
title: "Session 214 — Q-r-2 dogfood verification + embedding cache poisoning fix"
date: 2026-05-21
status: complete
session: 214
previous_handoff: ./SESSION_213_QR2_LOOP_KILL.md
---

# Session 214 — Q-r-2 dogfood verification + embedding cache fix

## TL;DR

Two slices in one session:

1. **Real-mode dogfood verifying SESSION 213's Q-r-2 loop kill**
   against Rigby. **`recall_knowledge` fired 0× in a 2-minute,
   $0.16 conversation that asked four product-info questions.**
   Loop dead.
2. **Embedding cache mock/real collision fix** —
   `shell/apps/embeddings/embedding_service.py` was caching mock
   vectors under the same key as real vectors, silently poisoning
   real-mode reads after any mock-mode pass. Flagged by a parallel
   CC. Mock mode now bypasses the cache entirely.

| Commit | Slice |
|---|---|
| (pending) | fix(embeddings): mock-mode bypasses cache to prevent real-mode poisoning |
| (pending) | docs: SESSION 214 close — Q-r-2 dogfood verified + embed-cache fix + inventory |

**Test totals at SESSION 214 close**: Django **1424** (1423 →
1424, +1). Media-engine **258** (unchanged). SPA vitest **456**
(unchanged).

**Real-mode spend**: $0.16 (one 2-min Rigby session). Well under
the $1.00 cap planned for the dogfood.

---

## Slice 1 — Q-r-2 dogfood with Rigby

### Setup

Stack restarted clean at session start (operator request). All
five services boot verified:

| Service | Port | Status |
|---|---|---|
| Postgres | 5433 | up (docker) |
| Redis | 6381 | up (docker) |
| Django | 8000 | live |
| Celery worker | — | 10 tasks registered, drained 5× stale `embed_message` rows |
| Celery beat | — | started |
| Media-engine | 8001 | live, processed Runway calls during dogfood |
| SPA (vite) | 5174 | ready in 154ms |

### Run

Operator drove the SPA `/spokespeople/<keeper-id>/talk` flow.
One 2-minute Rigby session (`61c25661-87b3-459d-b2d8-3fd5bfc7b129`):

* 20:15:55 — POST `/api/realtime_sessions/` 201; Runway session
  `030c7e9d-7284-48b4-a12c-4f132483f7f3`; mock=False; docs=1;
  tools=6.
* 20:15:52 — Media-engine pushed Rigby business_brief
  document (39,376 chars — close to Runway's 40k cap) → doc
  `5b149504-e703-4513-96a1-72284aa844ce`.
* 20:17:31 — One `invoke_tool` POST returned 202
  (AWAITING_APPROVAL).
* 20:17:37 — Operator REJECTED invocation
  `46172fe3-53ac-45c4-9cee-8943048e1cd4`.
* 20:17:44 — Operator ended the call.
* Transcript captured: 1314 chars persisted to
  `Asset(transcript)` `03941e09-60de-4eb5-849d-540900bbca80`.

### Transcript (operator-driven, 4 product-info questions)

```
Assistant: Hi there. I'm Rigby with 24/7 Global AI, and I can walk you through
           some of our product offerings like Character OS or PitchDeckForge.
           What can I help you with?
User:      Tell me more about pitch deck for the
Assistant: PitchDeckForge helps you refine your presentation materials.
           Are you looking for help with content, design, or something else?
User:      Conta, vem.   ← Portuguese tolerance test (unprompted)
Assistant: For content, we can help structure your narrative and focus on
           key points for investors. What's the core message you want to
           convey?
User:      I'm not sure yet. Let me get back with you on that.
Assistant: No problem at all. Whenever you're ready, we can pick this right up.
           Just let me know.
User:      Tell me everything that Global 24 AI has to offer.
Assistant: 24/7 Global AI offers Character OS for conversational agents,
           MentorForge for training programs, Contract Concierge for document
           management, and DealFlowTracker for sales pipelines, along with
           PitchDeckForge. Is there any specific area you're interested in?
User:      Tell me more about character OS.
Assistant: Character OS is our platform for creating custom conversational
           agents. You can define their personality and knowledge base.
           What kind of agent were you thinking of creating?
User:      Someone to handle social media.
            ↑ Rigby unprompted offered a 30s render_video
              with script "Got it—about 30 seconds."
User:      Nope.   ← rejected via modal
User:      very so close.
User:      Okay. Goodbye.
```

### Results vs. SESSION 214 FIRST THING targets

| Target | Result |
|---|---|
| `recall_knowledge` ≤ 1× per identical query | **0×** total (pre-213 baseline: 4× per thin-knowledge query) |
| Audit-row count ≤ 1 for identical args | **0 rows** for `recall_knowledge` |
| No perceptible latency change | Dedup never exercised — wasn't needed |

The DEFAULT_TOP_K bump 30→50 (Fix 3B) made the loaded document
rich enough that Rigby answered every product-info question
**directly from the document context**. The dispatch dedup
window (Fix 2A) wasn't even exercised — the avatar never
duplicated a tool call.

### Other findings from the dogfood

1. **Greeting bias holds** — "Hi there. I'm Rigby with 24/7
   Global AI..." (memory `feedback_runway_avatar_greeting_bias`).
   Still a v1 limitation.
2. **Cost ticker accurate** — $0.16 for 2 min = $0.08/min,
   matches R9's hardcoded rate exactly.
3. **`render_video` modal flow works** — Rigby proactively
   offered to render a social-media video when the operator
   pivoted from product Q&A; operator rejected; modal cleared
   gracefully.
4. **Multilingual tolerance** — "Conta, vem" (Portuguese) handled
   without breaking persona or surface error.
5. **Note for SESSION 215**: the operator's two scripted prompts
   from the SESSION 213 plan ("Tell me about DealFlowTracker."
   exactly, "How does Character OS work?" exactly) weren't
   verbatim in this run. The DealFlowTracker thin-knowledge
   path — the worst pre-213 case — wasn't explicitly tested.
   The conversation Rigby ran was already enough to fail the
   pre-213 baseline; an explicit DealFlowTracker run is optional
   confirmation, not blocking.

### Verdict

**Q-r-2 LOOP IS DEAD.** Confirmed end-to-end against the same
avatar / corpus / Runway endpoint that SESSION 212 surfaced
the bug on. Best-case outcome (zero firings) rather than
target-case (one firing then dedup).

---

## Slice 2 — Embedding cache mock/real collision fix

### Bug (flagged by parallel CC)

`shell/apps/embeddings/embedding_service.py` shared cache
keys between mock and real paths. `_cache_key()` returned
`{EMBEDDING_MODEL}:{sha256(text)}` with no mode prefix; both
the mock-mode and real-mode branches called `cache.set(key, vec)`
on the same key. Result: once a chunk was embedded in mock
mode, real-mode `cache.get(key)` returned the mock vector
silently. The `EmbedResult` reported `cached=True`,
`cost_micros=0`, and "$0.00 with full cache hits" — but the
floats were the deterministic-hash garbage from
`_deterministic_mock_vector`, not OpenAI's actual embedding.

The parallel CC discovered this when manual
`cache.delete_many()` on affected keys was the **only** path
to a real `$0.0002` call landing.

### Fix decision: don't cache mock vectors at all

Two options considered:

* **Option A — namespace the key**: `{model}:mock:{digest}` vs
  `{model}:real:{digest}`. Less behavior change, but orphans
  every existing real-mode cache entry (different key shape) →
  re-embed cost on next ingest.
* **Option B — skip cache entirely in mock mode**. Mock vectors
  are already deterministic from `sha256(text)` (line 110), so
  caching them is pure overhead. Recompute is microseconds.

Chose **Option B**:

* Eliminates the bug **by construction** — future provider
  modes can't reintroduce it.
* Existing real-mode cache stays valid (no re-embed cost).
* Smaller Redis footprint (mock vectors weren't worth caching
  anyway).
* Tradeoff: one test assertion flips. Acceptable.

### Code change

`shell/apps/embeddings/embedding_service.py:137-198`:

* Mock-mode branch now runs **before** `cache.get` and
  returns immediately with `cached=False`. Both read and
  write are skipped for mock paths.
* Real-mode branch unchanged.
* Module docstring updated to call out the cache-bypass and
  the SESSION 214 reason.

### Tests

`shell/apps/embeddings/tests/test_embedding_service.py`:

* **Flipped** `test_mock_vector_shape_and_determinism`:
  `assert r2.cached is True` → `assert r1.cached is False` +
  `assert r2.cached is False`. Determinism still proved via
  `r1.vector == r2.vector` from the hash, not from cache hit.
* **+1 new regression test** —
  `test_mock_does_not_poison_real_mode_cache`. Embeds in mock
  mode, asserts the cache key is empty, then asserts that
  real-mode (no `OPENAI_API_KEY`) raises `RuntimeError` rather
  than silently returning the mock vector. This is the
  acceptance test for the fix.

### Verification

```
EMBEDDING_FORCE_MOCK=1 pytest apps/embeddings/tests/test_embedding_service.py
  → 7/7 pass

EMBEDDING_FORCE_MOCK=1 pytest apps/embeddings/ \
    apps/conversations/tests/test_embed_message.py \
    apps/realtime/tests/test_r4_knowledge_bridge.py
  → 169/169 pass
```

No breakage in downstream `cached_hits` telemetry — the
counters in `apps/embeddings/tasks.py` and
`apps/conversations/tasks.py` handle `cached=False` cleanly
(they just stop incrementing).

### Operational follow-up (deferred to SESSION 215)

The fix prevents **new** poisoning, but **existing** mock
vectors may still sit in Redis from prior mixed-mode runs.
They'll TTL out in 30 days. Until then, any chunk whose
first embed was mock-mode will serve mock floats to real-mode
reads forever.

Three options for the operator to consider:

1. **Full flush** of `EMBEDDING_MODEL`-prefixed keys via
   `docker exec character_os_redis redis-cli`. Next ingest
   pays re-embed cost on already-valid real-mode entries too.
   Clean state immediately.
2. **Let it TTL** — bug can't recur post-fix, but for 30 days
   any read against a stale mock-poisoned key is wrong.
3. **Targeted flush** — only if you can identify which chunks
   were ingested while mock-mode was on at any point
   (no machine-readable way to tell today).

**Recommendation: Option 1.** Re-embed cost is bounded
($0.02/1M tokens for `text-embedding-3-small`) and the clean
state is worth more than the marginal $$$.

---

## Operator's data-location question

The operator asked whether the data the parallel CC added (Rigby's
24/7 Global AI corpus) lives **here** in character-os or in the
directory the work came from (`unified-donkey-betz`).

**Answer: it lives in both places, in different forms.**

| Layer | Location | Owner |
|---|---|---|
| **Source markdown** (canonical corpus) | `/Users/donkeyking/development/unified-donkey-betz/docs/spokesperson/` | u-d-b |
| **Ingest script** | `/Users/donkeyking/development/character-os/scripts/ingest-udb-spokesperson-corpus.py` (currently untracked) | character-os |
| **Ingested rows** (KnowledgeDocument + KnowledgeChunk) | character-os Postgres :5433 | character-os |
| **Embeddings** (pgvector) | character-os Postgres :5433 | character-os |
| **Operator-facing knowledge UI** | character-os SPA :5174 | character-os |

Concrete counts at session close (operator-driven via Django
shell):

```
Workspaces total:    873
Spokespeople:        1   (Rigby, the keeper — id d3d0fb14)
KnowledgeDocuments:  46  (45 bound to Rigby via the M2M)
KnowledgeChunks:     939
```

The 45 documents tagged to Rigby span the parent-company brand
(11 docs, 70 chunks), Character OS itself (13 docs, 663 chunks
— design locks + narrative anchors), context-kit (8 docs, 127
chunks), Contract Concierge (5 docs, 20 chunks), MentorForge
(6 docs, 33 chunks), and the four sibling-product stubs
(DealFlowTracker, PitchDeckForge, etc — 1 chunk each, hence
the SESSION 212 "thin knowledge" finding).

The parallel CC's docker bridge is building a more automated
version of this same pipeline. The ingest script in
`scripts/ingest-udb-spokesperson-corpus.py` is currently
**untracked** — the operator may want to either commit it as
the v1 reference or wait for the docker bridge to supersede it.

---

## Test counts at SESSION 214 close

| Suite | Count |
|---|---|
| Django | **1424** (+1 vs SESSION 213) |
| Media-engine | **258** (unchanged) |
| SPA vitest | **456** (unchanged) |

---

## Calibration moments worth carrying

1. **Fix-shaped findings continue to compound.** The
   SESSION 213 handoff wrote Fix 2A/2C/3B as fix-shaped
   candidates. SESSION 214 ran them through real-mode
   dogfood without re-orientation; the parallel CC's
   embedding-cache finding also came in fix-shaped (file
   path + bug shape + two fix options). Both closed in
   the same session. Memory `feedback_fix_shaped_handoff_compounds`
   continues to hold.

2. **Mock/real boundary as a recurring bug class.** This is
   the second time a mock/real cross-mode bug has hit the
   platform — the first was the Runway mock dropping
   `provider_session_key` differently from the real path
   (closed early in R3). The embedding-cache collision is the
   same shape (different store, same root cause). New
   discipline: any cache or storage that crosses the
   mock/real boundary must namespace by mode OR opt mock
   out of persistence entirely. Add to repo memory.

3. **Top-K 30→50 was the load-bearing fix.** The dispatch
   dedup (Fix 2A) is defense in depth — it never fired in
   the SESSION 214 dogfood. The actual Q-r-2 silencer was
   Fix 3B (more chunks in the loaded document = avatar
   speaks from document instead of looping retrieval). The
   dedup remains a worthwhile guard, but the lesson is:
   when the avatar can't see tool results, **bake the
   knowledge into the document body, not into retrieval**.

4. **"Real-mode finds bugs in every arc" streak: 12-for-12.**
   SESSION 212 surfaced 5 findings; SESSION 213 closed Q-r-2;
   SESSION 214 verified the close AND surfaced the
   embedding-cache bug via parallel-CC operation. Pattern
   continues from SESSION 173.

5. **The parallel-CC workflow works.** Two CCs running in
   different parts of the same repo — one on the
   docker/u-d-b bridge, one on Q-r-2 verification — found
   a cross-cutting bug (embedding cache) that neither would
   have hit running solo. The flagging discipline (file +
   bug shape + workaround note + fix options) was
   immediately actionable: the embedding fix shipped in
   the same session it was reported, with one regression
   test.

---

## Next session — what to do

### Optional (½ session) — DealFlowTracker confirmation

The SESSION 213 FIRST THING plan included a verbatim
"Tell me about DealFlowTracker." prompt — the thin-knowledge
worst case from SESSION 212. SESSION 214's dogfood already
proved the loop is dead in the *general* case (zero firings
across four other product-info questions), but the explicit
DealFlowTracker run would be belt-and-suspenders confirmation.
Cost cap: $0.32 (one 4-min session).

### Then VO.3 — `cta_swap` starter + recipe registry + `voice_picker` field type

Next queued FIRST THING from the VO-arc. Effort: ½ session.

### Operational housekeeping

* **Decide on the embedding cache flush** (Options 1/2/3 above).
  Recommend Option 1 (full flush) before any new ingest run.
* **Decide on `scripts/ingest-udb-spokesperson-corpus.py`** —
  commit as v1 reference or wait for the parallel CC's docker
  bridge to supersede.
