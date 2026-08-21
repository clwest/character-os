# SESSION 275 — Character Knowledge Lifecycle Audit

**Slice 1 — READ-ONLY forensic audit. No fixes.**

Framing chosen by Chris + ChatGPT: **generic mechanical trace** (not scenario-driven).

## Primary question

What actually happens to character-specific knowledge when the character (Teammate) is deleted?

## Load-bearing sub-question

Can deletion preserve the `KnowledgeDocument` / chunks / embeddings while removing the last spokesperson relation, thereby changing formerly private knowledge into shared / broadcast knowledge?

## Known evidence entering SESSION 275

- SESSION 274 CLOSED at commit `ccdb724`. Slice 2 §21 records the distinction: **data preservation** (KD/chunk/embedding survives) is separate from **retrieval eligibility** (surviving KD may become broadcast-visible).
- 9 legacy Class A KDs (`universe=None, spokespeople=∅`) live in `chriss-workspace` — TANK, Tulsi, 6× Hearth & Hollow, Riggs. Chris reports the SPA gives him no way to delete them. These are the anchor evidence — preserved as-is.
- Ruby's Class C KD `8f825c98-…` (Fox & Flour Bakery, spokespeople=∅) exists as SESSION 274 anchor. Preserved as-is.
- Ruby's Class D KD `74e7f18f-…` (Ruby-specific) preserved as-is.

## Chris's historical recollection — UNVERIFIED

> "KnowledgeDocuments may have been intentionally preserved when deleting characters because deleting the associated chunk / embedding substrate was undesirable or unsafe."

Verdict below (§10): **PARTIALLY SUPPORTED**. Preservation is real and tested; the *reason* was "preserve historical customer outputs" (SESSION 251 commit `0c64c5c` message), **not** explicitly "embedding cost / safety." No code comment, ADR, or design doc found that cites embedding cost as the motivation. Chris's recollection may conflate two overlapping motives.

## Slice 1 checklist

- [x] repo/runtime baseline
- [x] live 9-KD evidence baseline
- [x] SPA Teammate delete path
- [x] API Teammate delete path
- [x] Teammate model delete behavior
- [x] M2M delete behavior
- [x] universe=None B→A source verdict
- [x] universe=U D→C source verdict
- [x] KnowledgeChunk lifecycle
- [x] embedding storage/lifecycle
- [x] Composition provenance implications
- [x] historical rationale search
- [x] deletion test inventory
- [x] nine suspected orphan KDs classified
- [x] KnowledgeDocument delete API path
- [x] KnowledgeDocument delete SPA path
- [x] lifecycle state diagram
- [x] issue classification
- [x] destructive-experiment necessity decision

---

## §1. Repo / runtime baseline

- Branch: `main`
- HEAD: `0cea9b7`… actually `0cea5b9b4d94da6c1952ff43b71d8fb60c539fea` (SESSION 274 CLOSEOUT sha-record commit; SESSION 274 CLOSEOUT proper is `ccdb724`, one commit prior).
- `main == origin/main` ✅
- Working tree clean ✅
- SESSION 274 CLOSEOUT `ccdb724` present in history ✅
- Django `:8010/admin/` → **302** ✅
- Media-engine `:8001/health` → `{status:ok, openai_mock:false, runway_mock:false, image_gen_mock:false, any_mock:false, llm_provider:openai, llm_model:gpt-4o-mini}` ✅
- Vite `:5174/` → **200** ✅
- Celery `character_os inspect ping` → **1 node online** ✅
- Zero mock / experiment env vars in running Django/media-engine/celery processes ✅

## §2. Live 9-KD evidence baseline

Workspace: `chriss-workspace` (`4ce5486d-35a4-4bee-8745-38004adb33bc`).
Total KDs in workspace: 18 (universe=None: 13; universe set: 5; **Class A = 9**).
Total teammates: 8 (Mason, Penny, Ruby, Mike, Repo Red, Patch, Rivet, Riggs — all `status=ready`; Ruby in `Fox & Flour Bakery`, Patch & Rivet in `Patch' Workshop`, rest legacy).

All 9 candidate KDs: `is_active=True`, `status=processed`, `ingested_via=paste`, `created_by=chris@donkeybetz.com`, `universe=None`, `spokespeople=∅`.

| # | UUID | Title | Created | Chunks |
|---|------|-------|---------|--------|
| 1 | `aa90d895-cac9-41d4-b505-f2b23ffd5241` | About Hearth & Hollow Books | 2026-07-24 | 1 |
| 2 | `e37ea174-98e8-4588-a690-81f6e1bbfe4b` | How We Recommend Books | 2026-07-24 | 1 |
| 3 | `b58efd31-d05c-4008-beac-3a75755e5c6b` | Children's Reading | 2026-07-24 | 1 |
| 4 | `7f41d8e3-9be0-4591-9648-8c901861628d` | Bookstore Events | 2026-07-24 | 1 |
| 5 | `c408656d-191d-49be-a92d-8721aa294b58` | Supporting Local Authors | 2026-07-24 | 1 |
| 6 | `0088f31f-56fc-4e66-837a-f5391d6bbd94` | Helping Customers Find Their Next Read | 2026-07-24 | 1 |
| 7 | `7ecde40b-6d72-45eb-b676-6feb260e2ff8` | Tulsi — Core Identity and Public Purpose | 2026-08-05 | 3 |
| 8 | `8c6f0c14-b2c9-4161-b6b7-a17d3f9b4545` | TANK — AUTOMOTIVE FINANCING CONTENT KNOWLEDGE | 2026-08-16 | 22 |
| 9 | `90ad200c-5019-4036-82e9-a1ccc5cbce72` | Riggs | 2026-08-17 | 1 |

Content-sniff of the character-named docs:

- **TANK** (`8c6f0c14`): first chunk begins *"TANK — AUTOMOTIVE FINANCING CONTENT KNOWLEDGE / PURPOSE / Tank is an automotive financing spokesperson designed primarily for short-form social media content…"* — a character-specific brief written **for** a Tank teammate.
- **Tulsi** (`7ecde40b`): first chunk begins *"# Tulsi — Core Identity and Public Purpose / ## About Character OS…"* — character self-description for a Tulsi teammate.
- **Riggs** (`90ad200c`): entire content is *"Just knows a lot about everything"* — character-specific stub.
- **6× Hearth & Hollow**: bookstore-specific knowledge (about a bookstore called *Hearth & Hollow Books*) — every doc appears written **for** a Hearth & Hollow character.

No Tulsi, Tank, or Hearth & Hollow teammate currently exists in the workspace. A Riggs teammate does exist (`5731a73d-88b2-448a-88b2-d9da3b280e89`, universe=None, ready) — but the Riggs KD is unattached (spokespeople=∅).

## §3. SPA Teammate delete path

- Route: `/spokespeople/:id` — `web/src/routes/spokespeople/$id.tsx`
- Affordance: `Delete` button (Trash2 icon, ghost variant, destructive hover), top-right masthead — `$id.tsx:348-360`.
- Tooltip: `Delete ${spokesperson.name} (existing videos and assets stay in your library)` — `$id.tsx:353`.
- Confirmation modal: `web/src/components/spokesperson-delete-modal.tsx:92`.
  - Title: `Delete {spokespersonName}?`
  - Body (verbatim, lines 95-98): *"{spokespersonName} will be removed from your team and can no longer be used to create new content. Existing generated videos and assets will remain in your library."*
  - Buttons: `Cancel` / `Delete {spokespersonName}` (destructive) — lines 111-133.
- Handler: `handleDelete()` — `spokesperson-delete-modal.tsx:51-61`.
- HTTP: `DELETE /api/spokespeople/{id}/` with empty body, CSRF token, session cookies — `web/src/lib/api/spokespeople.ts:609-611`.
- Post-delete: `navigate("/dashboard", { replace: true })` — `$id.tsx:115-118`. React-Query invalidates `["spokesperson", id]`, `["spokespeople"]`, `["workspace-overview"]` — `spokespeople.ts:617-627`. Silent removal (no toast).
- UI knowledge options offered: **NONE**. Grep of the delete modal contains zero mentions of *knowledge*, *document*, *chunk*, *embedding*, *universe*, *reassign*, *archive*.

**What an ordinary operator is told will happen:** the teammate leaves the team, videos and assets survive. Nothing else is disclosed.

## §4. API / backend Teammate delete path

- URL: `shell/apps/spokespeople/urls.py:15-18` — DRF `DefaultRouter` registering `TeammateViewSet` at `/api/spokespeople/`, giving DELETE at `/api/spokespeople/<uuid>/`.
- View: `shell/apps/spokespeople/views.py:242` — `class TeammateViewSet(viewsets.ModelViewSet)` with `permission_classes = [IsWorkspaceMember]` (line 252). **No `destroy` / `perform_destroy` override.** Vanilla DRF → `Model.delete()`.
- Signals on `Teammate`: `shell/apps/spokespeople/signals.py` only registers `pre_save` + `post_save` for personality-sync to Runway. **Zero `pre_delete` / `post_delete` receivers on Teammate anywhere in `shell/`.**
- M2M signals: `shell/apps/embeddings/signals.py:31,93` registers `m2m_changed` on `KnowledgeDocument.spokespeople.through`, but **both handlers early-return unless `action == "pre_add"`** (lines 42-43, 117-118). They do NOT intervene on `pre_remove`/`post_remove`/`pre_clear`/`post_clear`, which is what Teammate delete triggers.
- Celery cleanup on delete: **none**. `shell/apps/spokespeople/tasks.py` fires only on personality changes.
- Soft delete: `Teammate` has **no** `is_active` / `deleted_at`. `Status.ARCHIVED` exists as a choice on the `status` CharField but is not exercised by the destroy path. DELETE is a **hard delete**.

## §5. All Teammate-facing relations

| Model | Field | on_delete | File:line |
|-------|-------|-----------|-----------|
| `Video.spokesperson` | FK | **CASCADE** | `shell/apps/videos/models.py:51-55` |
| `ConversationThread.spokesperson` | FK | SET_NULL | `shell/apps/conversations/models.py:40-46` |
| `Script.spokesperson` | FK | SET_NULL | `shell/apps/scripts/models.py:91-106` |
| `Composition.spokesperson` | FK | SET_NULL | `shell/apps/compositions/models.py:385` |
| `Asset.spokesperson` | FK | SET_NULL | `shell/apps/compositions/models.py:324` |
| `RealtimeSession.spokesperson` | FK | SET_NULL | `shell/apps/realtime/models.py` |
| `PersonalizedCampaign.spokesperson` | FK | SET_NULL | `shell/apps/campaigns/models.py` |
| `CharacterIdentity.teammate` | FK | SET_NULL | `shell/apps/identity/models.py` |
| `KnowledgeDocument.spokespeople` (M2M via `KnowledgeDocumentSpokesperson.teammate`) | through-FK | **CASCADE** | `shell/apps/embeddings/models.py:95-99` |

All FKs to Teammate are either CASCADE (Video only) or SET_NULL (all historical output rows). This SET_NULL policy is documented in commit `0c64c5c` (SESSION 251, 2026-08-14): *"SET_NULL migrations on 5 FKs so historical customer content survives the delete."*

## §6. KnowledgeDocument.spokespeople M2M — exact behavior

- Explicit through-model: `KnowledgeDocumentSpokesperson` — `shell/apps/embeddings/models.py:70-108`.
  - `knowledgedocument` FK — `on_delete=CASCADE`, `db_column="knowledgedocument_id"` (lines 90-94).
  - `teammate` FK — `on_delete=CASCADE`, `db_column="spokesperson_id"` (lines 95-99).
  - Docstring explains the class exists to pin `db_column` after the SESSION 240 rename (Spokesperson → Teammate); persistence identifiers stay `spokesperson_*`.
- Deletion collector behavior when a Teammate is deleted:

| Row | Fate |
|-----|------|
| `Teammate` | **DELETED** (hard) |
| `KnowledgeDocumentSpokesperson` (through) | **DELETED via CASCADE** on `teammate` FK |
| `KnowledgeDocument` | **SURVIVES** — no FK from KD → Teammate; only the through-row is cascaded |
| `KnowledgeChunk` rows | **SURVIVE** — Teammate delete does not touch chunks |
| `embedding_vector` on each chunk | **SURVIVES** — stored on the chunk row (`pgvector.django.VectorField`, 1536-dim) |
| `KnowledgeDocument.is_active` | remains `True` — no code path flips it on Teammate delete |
| `KnowledgeDocument.status` | remains `"processed"` |

Post-delete state of a KD that had exactly one attached teammate = `spokespeople.count() == 0`, `is_active=True`, `status="processed"`. **Nothing marks it orphaned or inactive.**

## §7. Retrieval predicate + scope-transition verdicts

Retrieval function: `retrieve_for_teammate(spokesperson, query, top_k=5)` — `shell/apps/embeddings/retrieval.py:159-226`.

Filter pipeline (verbatim):

```python
qs = KnowledgeChunk.objects.filter(
    document__workspace=spokesperson.workspace,
    document__is_active=True,
    document__status="processed",
)  # retrieval.py:194-198

if spokesperson.universe_id is None:
    qs = qs.filter(document__universe__isnull=True)
else:
    qs = qs.filter(document__universe_id=spokesperson.universe_id)
    # retrieval.py:211-214

qs = (
    qs.filter(
        Q(document__spokespeople__isnull=True)
        | Q(document__spokespeople=spokesperson)
    )
    ...
)  # retrieval.py:216-224
```

Empty M2M passes `Q(spokespeople__isnull=True)` → **broadcasts to every eligible teammate** (matching universe scope).

### CASE 1 — universe=None (B→A):

- BEFORE: `KD.universe=None, KD.spokespeople={A}` — visible only to teammate A per `Q(spokespeople=A)`.
- Delete A → `KD.universe=None, KD.spokespeople=∅, KD.is_active=True, KD.status='processed'`.
- For any legacy teammate T (`T.universe_id is None`), `retrieve_for_teammate(T)` filters `document__universe__isnull=True` (TRUE) AND `Q(document__spokespeople__isnull=True)` (TRUE).

**Verdict: CONFIRMED FROM SOURCE.** The surviving KD becomes Class A broadcast-eligible to every legacy teammate in the workspace. Citations: `shell/apps/embeddings/models.py:95-99` (M2M CASCADE), `shell/apps/embeddings/retrieval.py:211-220` (predicate).

### CASE 2 — universe=U (D→C):

- BEFORE: `KD.universe=U, KD.spokespeople={A}` — visible only to A.
- Delete A. **Django's ORM does NOT touch `KD.universe`** (no FK on Teammate → Universe cascade path affects KD). The KD retains `universe=U`.
- Result: `KD.universe=U, KD.spokespeople=∅, KD.is_active=True, KD.status='processed'`.
- For any teammate T with `T.universe_id == U`, `retrieve_for_teammate(T)` filters `document__universe_id=U` (TRUE) AND `Q(document__spokespeople__isnull=True)` (TRUE).

**Verdict: CONFIRMED FROM SOURCE.** The surviving KD becomes Class C Universe-shared broadcast-eligible to every teammate in Universe U. This is exactly the "private → Universe canon" promotion the load-bearing sub-question warned about. Citations: same as CASE 1, plus `retrieve_for_teammate` Universe branch at `retrieval.py:213-214`.

## §8. KnowledgeChunk + embedding lifecycle

- FK: `KnowledgeChunk.document` → `KnowledgeDocument`, `on_delete=CASCADE` — `shell/apps/embeddings/models.py:319-323`.
- Vector storage: `embedding_vector = VectorField(dimensions=1536)` — on-row, pgvector column, HNSW-indexed (`m=16, ef_construction=64, opclasses=["vector_cosine_ops"]`). No external vector store — cite `models.py:336, 366-374`.
- Cost per chunk: `embedding_cost_micros` — models.py:346-352.
- Teammate deletion does NOT touch `KnowledgeChunk` (only the through-row).
- KD hard-delete would CASCADE chunks and destroy the on-row vectors — but the SPA/API surface Chris uses is **soft-delete only** (see §12).
- Re-embedding a KD would require re-running `apps.embeddings.tasks` (paying OpenAI `text-embedding-3-small` cost again) — technically straightforward, financially cheap but non-zero.
- No code path explicitly requires chunk preservation.

## §9. Composition provenance implications

- Field: `Composition.knowledge_chunk_ids = models.JSONField(default=list, blank=True)` — `shell/apps/compositions/models.py:427`.
- Type: **JSONField list of raw UUID strings.** Not a Django FK. No `on_delete`. No referential integrity.
- Read paths:
  - `shell/apps/embeddings/retrieval.py:63-118` — `resolve_chunk_ids_to_docs()` fetches surviving chunks, silently skips missing ones (`if chunk is None: continue`, lines 102-104).
  - `shell/apps/embeddings/views.py:248-272` — reverse lookup uses set-membership on string UUIDs (never touches KnowledgeChunk table for the comparison).
- Effect of chunk deletion: **graceful degradation.** Composition rows stay intact; historical provenance shows partial (only still-live chunks). No 500s, no ProtectedError.
- **No code path explicitly protects KDs / chunks from deletion for Composition-history reasons.** The soft-delete of KDs (via API) preserves chunks and thus preserves provenance, but this is not enforced anywhere — it's a side-effect of the destroy method's `is_active=False` choice (§12).

## §10. Historical embedding-preservation rationale — verdict

**PARTIALLY SUPPORTED.**

Supporting evidence:

- Commit `0c64c5c` (2026-08-14, "feat(spokespeople): customer teammate delete + preserve historical outputs") is the commit that landed the customer-facing Teammate delete flow. Message body verbatim (partial): *"Ships a customer-facing delete flow for Teammates that survives their prior work. […] SET_NULL migrations on 5 FKs so historical customer content survives the delete: Composition.spokesperson (PROTECT → SET_NULL), RealtimeSession.spokesperson (PROTECT → SET_NULL), Script.spokesperson (CASCADE → SET_NULL), PersonalizedCampaign.spokesperson (CASCADE → SET_NULL), ConversationThread.spokesperson (CASCADE → SET_NULL). Asset.spokesperson and CharacterIdentity.teammate were already […]"*
- `docs/handoffs/SESSION_251_TEAMMATE_DELETE_AND_DOGFOOD_PLUMBING.md:56-66` records the same rationale.
- `shell/apps/spokespeople/tests/test_delete.py:118` — `test_delete_detaches_knowledge_but_keeps_document` asserts M2M detach + KD survival is intentional.
- `shell/apps/embeddings/views.py:110-118` — `destroy()` docstring: *"Soft delete — flip `is_active=False` instead of dropping the row. The chunk rows stay so the retrieval path's `is_active=True` filter is the gatekeeper. Hard-delete is an admin-only operation."*

Contradicting / missing evidence:

- No comment on `KnowledgeDocumentSpokesperson` (`models.py:70-108`) mentions embedding cost, safety, or the reason for CASCADE on the through-model.
- No ADR (`KNOWLEDGE_LAYER.md`, `UNIVERSE_SCHEMA_V1.md`, `CANONICAL_IDENTITY_CONTRACT_V1.md`, `CUSTOMER_JOURNEY_V1.md`) discusses embedding-cost as a preservation motivator.
- `KNOWLEDGE_LAYER.md` does not discuss deletion policy at all.
- The M2M-through-model uses CASCADE by Django convention; there's no evidence it was chosen after weighing alternatives (SET_NULL / PROTECT / archive-flag).

**Interpretation.** Chris's recollection is *partially* correct: KDs ARE intentionally preserved on character deletion, and preservation IS tested. But the recorded motivation is **"preserve historical customer outputs"** (Composition/Script/Campaign continuity), not **"embedding cost / substrate safety."** The two motivations overlap — preserving chunks preserves both the vectors AND the Composition-provenance chain — but no source cites embedding cost specifically. Recollection likely conflates the two.

## §11. Deletion test coverage inventory

20 deletion / M2M-lifecycle tests exist across `shell/apps/spokespeople/tests/test_delete.py`, `shell/apps/embeddings/tests/test_m2m_through_column_contract.py`, `shell/apps/embeddings/tests/test_retrieval_universe.py`, `shell/apps/embeddings/tests/test_retrieval_universe_canon.py`, `shell/apps/embeddings/tests/test_api.py`. Selected high-signal rows:

| File:line | Test | Asserts | Invariant | Gap |
|---|---|---|---|---|
| `spokespeople/tests/test_delete.py:73` | `test_owner_can_delete_their_teammate` | DELETE→204, Teammate gone | delete succeeds | — |
| `spokespeople/tests/test_delete.py:118` | `test_delete_detaches_knowledge_but_keeps_document` | M2M detaches, KD survives | data preservation | **does NOT assert retrieval eligibility change** |
| `spokespeople/tests/test_delete.py:142` | `test_delete_preserves_compositions_and_assets_with_nulled_attribution` | Composition/Asset survive, `spokesperson_id=NULL` | SET_NULL cascade | — |
| `embeddings/tests/test_retrieval_universe.py:89` | `test_row1_legacy_teammate_legacy_doc_empty_m2m_visible` | empty-M2M legacy doc visible to legacy teammate | broadcast semantics | **static; no delete involved** |
| `embeddings/tests/test_retrieval_universe.py:141` | `test_row6_universe_teammate_same_universe_doc_empty_m2m_visible` | empty-M2M Universe doc visible to same-Universe teammate | broadcast semantics | **static; no delete involved** |
| `embeddings/tests/test_retrieval_universe_canon.py:121` | `test_m2m_null_broadcast_is_canon_for_full_cast` | empty-M2M doc included in canon | broadcast semantics | static |
| `embeddings/tests/test_api.py:635` | `test_delete_soft_deletes` | KD DELETE → `is_active=False` | soft-delete contract | — |

Total suite ≈ 2,845 tests.

**Gap plainly stated:** no test exists of the form "create KD with `spokespeople=[A]`, delete A, retrieve for teammate B, assert B does NOT see it." The two invariants — "M2M detaches on delete" and "empty M2M broadcasts to all" — are each individually protected, but their **composition** (delete → audience-widen) is untested.

## §12. Nine Class A KD classification

Definition (from Slice 1 spec §12): *orphan = KD that survives after its intended character association no longer exists and currently has no explicit spokesperson assignment.*

| # | UUID | Title | Verdict | Rationale |
|---|------|-------|---------|-----------|
| 1 | `aa90d895` | About Hearth & Hollow Books | **PROBABLE ORPHAN** | Bookstore-specific content; no "Hearth & Hollow" teammate exists |
| 2 | `e37ea174` | How We Recommend Books | **PROBABLE ORPHAN** | Same |
| 3 | `b58efd31` | Children's Reading | **PROBABLE ORPHAN** | Same |
| 4 | `7f41d8e3` | Bookstore Events | **PROBABLE ORPHAN** | Same |
| 5 | `c408656d` | Supporting Local Authors | **PROBABLE ORPHAN** | Same |
| 6 | `0088f31f` | Helping Customers Find Their Next Read | **PROBABLE ORPHAN** | Same |
| 7 | `7ecde40b` | Tulsi — Core Identity and Public Purpose | **PROBABLE ORPHAN** | Content is character-specific self-description; no Tulsi teammate exists |
| 8 | `8c6f0c14` | TANK — AUTOMOTIVE FINANCING CONTENT KNOWLEDGE | **PROBABLE ORPHAN** | Content is character-specific brief; no TANK teammate exists |
| 9 | `90ad200c` | Riggs | **POSSIBLE ORPHAN** | Riggs teammate exists (`5731a73d`) but KD is unattached; could be pre-attach-never or post-detach — cannot distinguish from evidence alone |

None classified CONFIRMED ORPHAN because we lack a definitive audit trail proving each KD was ever attached to a since-deleted teammate — the M2M through-row deletion is silent (no journal, no `deleted_at`). No test flag or historical log records prior attachment state.

Names of teammates suggested by titles/content but absent from the current teammates list: **Hearth & Hollow** (never existed as a teammate name, possibly a workspace-level bookstore identity), **Tulsi**, **TANK**.

## §13. Why can't Chris delete these from the SPA?

- Backend API: `DELETE /api/knowledge/<id>/` **exists** — `shell/apps/embeddings/urls.py:7` + `shell/apps/embeddings/views.py:110-118`. It performs **soft-delete** (`is_active=False`; chunks preserved). Hard delete is admin-only.
- Permission: `IsWorkspaceMember` — owner role gates DELETE. Chris IS the owner of `chriss-workspace`.
- SPA: delete button **exists** — `web/src/routes/workspace/knowledge.tsx:737-747` (Trash2 button inside `KnowledgeRow`; confirmation copy line 701: *"Delete "\${doc.title}"? Chunks stay searchable in admin only."*).

**When was this added?** SPA KD delete landed in commit `dd5bf37` (2026-08-17, SESSION 261 Phase 4 — Universe UI). Before 2026-08-17, no SPA affordance existed. 8 of the 9 KDs (all except Riggs, created 2026-08-17 15:53) predated the SPA delete button. Riggs KD was created the same day.

**Explanation of Chris's report.** The SPA has a delete affordance today, but:

1. It lives on `/workspace/knowledge` — a distinct route from the Teammate detail page where Chris does most of his work. There is no cross-link (Teammate detail → the KDs it was attached to).
2. The button is a bare Trash2 icon inside the list row, not a labeled destructive action — discoverability is low.
3. Between 2026-07-24 and 2026-08-17 (the window in which 8/9 of these KDs were created) no SPA delete existed at all. During that window, deletion would have required admin or direct API call. That is likely the origin of Chris's "I can't delete these" recollection.

This is a **discoverability / operator UX issue**, not a hard block. The capability exists; Chris hasn't found it, or hasn't revisited the workspace since it landed.

## §14. Lifecycle state diagram (evidence-based)

```
                             delete Teammate A
     ┌──────────────────────────────────────────────────────────┐
     │                                                          │
     ▼                                                          │
[Teammate A]  ── FK CASCADE ──►  Video rows          (DELETED) │
                                                                │
[Teammate A]  ── FK SET_NULL ─►  ConversationThread  (survives w/ spokesperson=NULL)
                                 Script               (survives w/ spokesperson=NULL)
                                 Composition          (survives w/ spokesperson=NULL)
                                 Asset                (survives w/ spokesperson=NULL)
                                 RealtimeSession      (survives w/ spokesperson=NULL)
                                 PersonalizedCampaign (survives w/ spokesperson=NULL)
                                 CharacterIdentity    (survives w/ teammate=NULL)

[Teammate A]  ── M2M-through CASCADE ──►  KnowledgeDocumentSpokesperson row  (DELETED)
                                                          │
                                                          ▼
                       KnowledgeDocument  (SURVIVES; is_active=True; status='processed')
                                        │
                                        ├─ spokespeople.count() == 0
                                        ├─ retrieval predicate: Q(spokespeople__isnull=True) → TRUE
                                        │
                                        ▼
                              ╔══════════════════════════════════╗
                              ║  AUDIENCE PROMOTION EVENT        ║
                              ║                                  ║
                              ║  universe=None → Class A         ║
                              ║    → broadcasts to all legacy    ║
                              ║      teammates in workspace      ║
                              ║                                  ║
                              ║  universe=U   → Class C          ║
                              ║    → broadcasts to all teammates ║
                              ║      inside Universe U           ║
                              ╚══════════════════════════════════╝
                                        │
                                        ▼
                         KnowledgeChunk rows  (SURVIVE — no FK from Teammate to chunk)
                                        │
                                        ▼
                         embedding_vector (on-row pgvector)  (SURVIVES)
                                        │
                                        ▼
                Composition.knowledge_chunk_ids provenance  (INTACT — soft UUID reference)
```

## §15. Issue classification

**PROVISIONAL E — MULTIPLE ISSUES.** Read-only evidence supports each component below without a destructive experiment (see §16).

- **B — LIFECYCLE SEMANTICS BUG (confirmed by source).** Preservation is intentional; deletion silently widens the audience of the surviving KD because empty M2M is overloaded to mean "broadcast to all in scope." Both B→A and D→C promotion paths are structurally proven from source. The M2M through-model's CASCADE (rather than a surviving journal row, a `deleted_at` marker on the KD, or an audience-preserving `is_broadcast` explicit flag) is the mechanical trigger.
- **D — UI / OPERATOR BUG (confirmed by source).** The SPA delete modal (`spokesperson-delete-modal.tsx:95-98`) discloses only that "videos and assets remain." It does not mention knowledge, chunks, embeddings, or the audience-promotion side effect. An operator cannot reason about the resulting scope from the UI copy alone. Separately, the KD delete affordance exists (`workspace/knowledge.tsx:737`) but is not surfaced from the Teammate flow, so Chris's inability to find it is a real discoverability defect.
- **C — NOT a deletion-cleanup bug.** Preservation was deliberate (commit `0c64c5c` message) — the intent to preserve historical outputs is recorded and tested. This rules out "cleanup failed / never implemented."
- **A — NOT no-bug.** The audience-promotion side effect is real and would surprise an operator who deletes a character expecting the character's private knowledge to become inaccessible.

## §16. Destructive-experiment necessity — verdict: **NO**

Source + history + live orphan evidence conclusively establish both scope transitions:

- The M2M through-model (`KnowledgeDocumentSpokesperson`) uses CASCADE on `teammate` FK — proven at `shell/apps/embeddings/models.py:95-99`.
- Django's deletion collector will remove the through-row and only the through-row (no journal, no signal intercepts remove events, no `on_delete=PROTECT` on any KD-side field).
- The retrieval predicate is exact — `retrieval.py:216-220`. Empty M2M passes `Q(spokespeople__isnull=True)`; no additional guard.
- The Universe filter is applied **before** the M2M filter (`retrieval.py:211-214`), so Universe scoping stays intact after Teammate delete — a Universe KD that loses its last spokesperson becomes Class C, not Class A.
- The 9 live orphan-candidate KDs match this exact predicted post-delete state (universe=None, spokespeople=∅, is_active=True, status=processed) — real-world corroboration.

An experiment would confirm what source already proves. It is unnecessary. **Do not run one for ceremony.**

If Chris disagrees or wants observational confirmation, a minimal disposable experiment would be:

```
1. Create disposable Workspace W_exp (or reuse a scratch workspace).
2. Create disposable Universe U_exp inside W_exp.
3. Create teammate T_legacy (universe=None) and T_universe (universe=U_exp) inside W_exp.
4. Create two tiny KDs (paste, 1 chunk each — no provider call: use pre-computed
   zero vector via retrieval._query_vector test path):
   - KD_legacy: universe=None, spokespeople={T_legacy}
   - KD_universe: universe=U_exp, spokespeople={T_universe}
5. Record baseline: KnowledgeDocumentSpokesperson row counts + retrieval outputs
   (retrieve_for_teammate for each teammate).
6. Delete T_legacy AND T_universe via API.
7. Record post-state: same rows, same retrieval calls.
8. Assert: through-rows dropped; KD rows survive; spokespeople.count()==0;
   surviving KDs appear in retrieval output for any other teammate matching
   the corresponding universe scope (create a witness teammate in each scope).
9. Cleanup: delete both KDs (soft-delete via API), delete Universe (RESTRICT
   is safe because empty), delete workspace. Idempotent.
```

Costs: $0 (no OpenAI call — use test-path `_query_vector`). Preserve UUIDs in the doc before cleanup. Chris approval gate before executing.

## §17. Product questions — exposed, not decided

These are decision questions for Chris after the audit. NOT solved here.

- Should character deletion ever change KD audience?
- Should preserved knowledge become INACTIVE (`is_active=False`) on last-spokesperson delete, keeping the vectors but excluding from retrieval?
- Should orphaned knowledge remain retrievable in any capacity (admin only? broadcast? workspace-wide fallback?)?
- Should deleting a character prompt: preserve / reassign / archive / delete?
- Should "no spokesperson selected" remain overloaded to mean "shared" — or be split into two explicit states (`audience=none-yet` vs `audience=broadcast`)?
- Should explicit scope/audience (a `KnowledgeAudience` model or an enum on KD) replace the empty-M2M semantics? This is Slice 1 §8.5 P4 from SESSION 274.
- Should historical `Composition.knowledge_chunk_ids` provenance be decoupled from active retrieval (e.g. a snapshot of chunk text at render time) so KD deletion doesn't degrade Composition history?

Related lever (independent of the above): the SPA Teammate delete modal (`spokesperson-delete-modal.tsx:95-98`) discloses zero knowledge-related side effects. Copy could disclose the fact that any KD previously attached only to this character will become broadcast-visible. That is a copy-only mitigation; it does not remove the promotion.

## §18. Unresolved questions carried forward

- Was any of the 9 KDs ever attached to a since-deleted teammate? No audit trail exists; the through-row cascade is silent. To distinguish "created without an attachment" from "attachment removed via delete," we'd need a journal or an M2M `deleted_at` marker — neither exists.
- Is Chris's specific "embedding cost" recollection independently attested anywhere outside the sources searched? Deep git archaeology across the retired hackathon prototype was out of scope.
- Is there operational impact today? The 9 orphan-candidate KDs are already broadcast-eligible to all 6 legacy Chris workspace teammates (Mason, Penny, Mike, Repo Red, Riggs, and Ruby is in a Universe so excluded). Whether current retrievals actually return them depends on cosine distance vs the query — a runtime observation, not a source claim.

## §19. Docs / evidence written

- `docs/design/SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md` (this file).
- No sidecar directory needed — all evidence embedded above.

## §20. Recommendation on committing this doc

Documentation-only commit is appropriate. Suggested message:

```
docs(session-275): §1-§20 Slice 1 — character-delete → KD lifecycle audit (read-only)
```

Recommend Chris authorize the commit before Slice 2. This is a pure additive doc, no code changes, no schema changes.

---

# SESSION 275 — Slice 2 — Knowledge Lifecycle Contract / Smallest Safe Design

**Slice 2 is a DESIGN / DECISION slice. Read-only + doc-only. No code, no migrations, no fixtures.**

## §21. Slice 1 commit

- Slice 1 committed as `66c45fd` on 2026-08-20.
- Pushed to `origin/main`. `main == origin/main == 66c45fd`. Working tree clean at Slice 2 open.
- File changed: `docs/design/SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md` (+421 lines).

## §22. Slice 2 question

Given the audience-promotion mechanism proven in Slice 1, **what lifecycle contract should Character OS enforce when a character is deleted, and what is the smallest safe implementation that preserves historical data WITHOUT increasing knowledge audience?**

## §23. Lifecycle invariant — verdict: **SUPPORTED**

Proposed invariant (verbatim):

> A removal or deletion action must never broaden the audience of surviving knowledge.
>
> For any KnowledgeDocument K with audience A_before:
> `delete(character X)` must satisfy `A_after(K) ⊆ A_before(K)`
> unless the operator explicitly chooses a broader audience.

**Verdict: SUPPORTED — evidence-backed.**

Nothing in current product / history / test contract contradicts this. Supporting evidence:

- SESSION 251 commit `0c64c5c` message declares preservation intent as **"historical customer content survives the delete"** — consistent with data preservation. It says nothing about audience widening being desirable; audience-widening is a mechanical side-effect of the CASCADE on the through-model.
- `docs/design/KNOWLEDGE_LAYER.md` §"Data model" (`shell/apps/embeddings/models.py:14-17`): *"`spokespeople` M2M is the visibility filter — empty M2M means 'visible to all spokespeople in the workspace.'"* This is an *authoring* semantic (operator explicitly chose to broadcast by leaving M2M empty), not a *deletion* semantic. Applying the same semantics to a M2M that was previously non-empty inverts the authoring intent.
- `docs/design/UNIVERSE_SCHEMA_V1.md` §"Deletion policy" already establishes RESTRICT on `Universe` to *"structurally prevent the knowledge-bleed hazard where hard-delete of a populated Universe would silently demote… and expose it to unrelated legacy characters"* — the same class of hazard the invariant guards. Precedent supports the invariant.
- No test in the suite asserts audience-widening is desired on delete (§11).

**One caveat.** If Chris ever wants a workflow like "delete this character AND promote their knowledge to Universe canon in one gesture," the invariant would say "no — that must be two explicit operations (unassign→broaden, THEN delete)." That is a philosophical stance, not an evidence-blocker. **Marking this as a REQUIRES PRODUCT DECISION for one narrow case** would only apply if Chris wants deletion to double as promotion. Nothing in the current product suggests he does. Recommendation: adopt the invariant as-is.

## §24. Preservation vs. active retrieval — explicit separation

Slice 1 conflated some of these; Slice 2 makes them axiomatic.

| Concept | Storage | Question it answers | Current control |
|---|---|---|---|
| **DATA EXISTS** | `KnowledgeDocument` row + `KnowledgeChunk` rows + `embedding_vector` pgvector column + `source_metadata` + `raw_content` + `processed_content` | Does the knowledge still exist on disk? | Whether row is deleted (hard) — no soft equivalent |
| **ACTIVE FOR RETRIEVAL** | `KnowledgeDocument.is_active=True` AND `status="processed"` | Would `retrieve_for_teammate` consider this KD as a source? | `is_active` (flipped by `views.py:destroy`); `status` (set by ingestion pipeline) |
| **ASSIGNED AUDIENCE** | `KnowledgeDocument.universe` + `KnowledgeDocument.spokespeople` M2M | Who is this KD scoped for? | Universe on ingestion form; M2M via K5 attach/detach endpoints |
| **OPERATOR VISIBILITY** | Filtered by SPA (`views.py:70` `.filter(is_active=True)`) | Can the operator see this KD in the Knowledge list? | Whichever `is_active` is |
| **HISTORICAL PROVENANCE** | `Composition.knowledge_chunk_ids` (JSON UUID list) resolvable via `resolve_chunk_ids_to_docs` (`retrieval.py:63-118`) | Can we display "this Composition drew from doc X"? | Resolver does NOT filter `is_active` — provenance is safe regardless of active status |

**The load-bearing insight:** DATA EXISTS + HISTORICAL PROVENANCE are independent of ACTIVE FOR RETRIEVAL. Flipping `is_active=False` preserves the first two and only affects the third (plus operator visibility, which is downstream of the same flag). This is exactly what a "safe orphan archive" needs.

## §25. Candidate lifecycle options

Each evaluated against the invariant (§23) and the smallest-safe criterion.

### Option A — INACTIVATE ORPHANED KDs

On `Teammate` deletion, iterate every KD where this Teammate is currently a spokesperson. For each such KD:
- If this Teammate is the **only** spokesperson (i.e., after cascade, spokespeople count would go 1→0), set `is_active=False`.
- Otherwise leave alone (audience narrows safely to the surviving spokespeople).

Then let Django's default cascade drop the through-rows.

- **Historical intent preserved?** Yes — data survives (§24 row 1 unchanged); provenance resolves (§24 row 5 unchanged).
- **KD later reassignable?** Not with today's UI — see §30. Requires small SPA follow-up.
- **API/UI already understands inactive KDs?** Partially. Retrieval + list already filter it out (§29). SPA renders nothing for inactive today. Admin can see + filter.
- **Does soft-delete use the same state?** Yes — that's the overload concern. Both operator delete and orphan-archive would set `is_active=False`. Without a `deactivated_reason` column, an operator inspecting an inactive KD later cannot tell which happened.
- **Overload acceptable for smallest safe fix?** Borderline. Adding one nullable enum column (`deactivated_reason`) resolves the overload cleanly; without it, we ship a semantics mud-puddle. **Recommendation: pair Option A with a tiny `deactivated_reason` column** so intent is recoverable from day 1.

**Verdict:** smallest true delta. See §35.

### Option B — EXPLICIT ORPHAN STATE

Add a `lifecycle_state = CharField(choices=[ACTIVE, ORPHANED, ARCHIVED, DELETED])` on `KnowledgeDocument`. Retrieval filters `lifecycle_state=ACTIVE`.

- **Schema/migration cost:** medium. New column + backfill (all existing rows default `ACTIVE` if `is_active=True`, `DELETED` if `is_active=False`).
- **Clarity:** high — the enum is self-documenting. Distinguishes the three concerns.
- **Future extensibility:** high — easy to add `PENDING_REVIEW`, `ARCHIVED_BY_ADMIN`, etc.
- **Overbuilt for current problem?** Slightly. Solves the audience bug + solves the semantic-overload concern in one migration.
- **Comparison to Option A + `deactivated_reason`:** functionally near-identical (both give you a distinguishable orphan state). Option A reuses `is_active`; Option B replaces it. Option B costs one migration to introduce, plus a deprecation window to remove `is_active`. Net: Option B is cleaner long-term but strictly larger than Option A now.

**Verdict:** viable, but strictly more surface area than Option A + `deactivated_reason`. If Chris wants a proper state machine, escalate to Option C.

### Option C — EXPLICIT AUDIENCE MODEL

Replace empty-M2M overloading with an explicit `audience` enum on `KnowledgeDocument`:
- `audience = CHARACTER_SPECIFIC` (M2M authoritative)
- `audience = UNIVERSE_SHARED` (Universe-broadcast; M2M ignored)
- `audience = WORKSPACE_SHARED` (legacy Class A; universe=None + broadcast)
- `audience = ORPHANED` (post-delete, not retrievable)
- `audience = NONE` (never assigned; not retrievable)

This is the SESSION 274 §8.5 P4 direction and would unblock P2-lite. **Too large for SESSION 275** — requires backfilling all existing rows into an explicit state, retrievel-predicate rewrite, K5 endpoint rewrite, SPA scope UI rewrite. Weeks of work.

**Verdict:** long-term correct. Do NOT block Slice 2 on it.

### Option D — DELETE KD WITH CHARACTER (cascade)

Change `KnowledgeDocumentSpokesperson.knowledgedocument` to cascade on Teammate delete via a signal, OR delete the KD outright when its last spokesperson is deleted.

- **What is lost:**
  - `KnowledgeChunk` rows (CASCADE) → embedding vectors gone (payment sunk, must re-embed if content returns).
  - `Composition.knowledge_chunk_ids` provenance points at dead UUIDs → `resolve_chunk_ids_to_docs` silently drops those chunks (`retrieval.py:102-104`) → historical Composition detail shows "drew from 3 chunks (2 no longer exist)" or worse.
  - `raw_content` + `processed_content` gone → re-ingestion requires the operator to have the source.
- **Contradicts SESSION 251 commit `0c64c5c` intent** ("preserve historical outputs").

**Verdict:** Rejected. Solves the promotion bug but demolishes the recorded preservation intent. Do NOT recommend.

### Option E — REQUIRE OPERATOR DECISION

Modify the Teammate delete modal to present, per affected KD: `archive / reassign / delete / share explicitly`.

- **Correctness:** high — operator picks per KD.
- **UX burden:** high. If a character has 22 KDs (Chris's TANK-era case had that many chunks; other characters may have many docs), the modal becomes a table.
- **Backend complexity:** medium. Each KD needs a per-doc mutation before the Teammate delete; whole flow must be transactional. Race conditions if operator dawdles and another operator ingests a new doc during the decision.
- **Atomicity:** solvable but non-trivial. Would want to pre-serialize the operator's choices into one delete-with-plan request.
- **When it belongs:** as a Phase-2 SPA layer on TOP of Option A. Immediate backend fix (Option A) makes the default safe; Option E is a discoverable "advanced" flow for operators who want to convert-instead-of-archive.

**Verdict:** correct long-term UX complement, not the immediate backend safety fix.

## §26. Multi-spokesperson trace (each option × each scenario)

Legend:
- `{A}` = KD.spokespeople contains only Teammate A
- `{A,B}` = KD.spokespeople contains both A and B
- `∅` = born-empty (Class A or Class C canon)
- Universe scope shown as suffix: `-none` or `-U`

Scenarios (each applies at both `-none` and `-U`):

| # | Start | Action | Option A expected | Option D expected | Option E expected |
|---|---|---|---|---|---|
| 1 | `{A}-none` | delete A | KD `is_active=False` (orphan-archived) | KD row deleted, chunks CASCADEd | operator picks per KD |
| 2 | `{A}-U` | delete A | KD `is_active=False` (universe intact but hidden) | KD row deleted | operator picks |
| 3 | `{A,B}-none` | delete A | M2M cascades to `{B}`, KD stays active | KD row deleted (bad) | operator picks |
| 4 | `{A,B}-U` | delete A | M2M cascades to `{B}`, KD stays active in U | KD row deleted (bad) | operator picks |
| 5 | `{A,B}-none` | delete A then B | after A: `{B}` active. After B: `∅`, KD inactivated | after A: KD gone; B delete is no-op for this KD | 2 prompts |
| 6 | `∅-none` (born-empty Class A canon) | delete unrelated legacy teammate T | no effect — T is not in M2M | no effect | no effect |
| 7 | `∅-U` (born-empty Class C canon — Ruby's Fox & Flour hours) | delete Ruby | no effect — Ruby is not in M2M | no effect | no effect |

**Option A satisfies every row.** Scenarios 6 and 7 are the load-bearing ones (§27) — Option A correctly leaves born-empty shared KDs alone because the condition is "was `teammate` in the M2M AND removing them empties it" — a born-empty KD fails the first clause.

## §27. Intentionally shared KD behavior — the load-bearing distinction

Class C born-empty KDs (e.g. Ruby's Fox & Flour "House Policies & Hours") **must not** be archived when a Universe member is deleted. Option A achieves this **by construction**: the signal iterates KDs where the deleted Teammate is currently a spokesperson (via `KnowledgeDocument.spokespeople.filter(pk=teammate.pk)` equivalent). A born-empty KD has ∅ spokespeople; the deleted Teammate was never in that M2M; the iteration skips it.

Explicit rule:

```
IF teammate ∈ KD.spokespeople (was)
   AND KD.spokespeople.count() == 1 (i.e. teammate was the sole spokesperson)
   AND KD.is_active == True (don't re-archive)
THEN set KD.is_active = False (and KD.deactivated_reason = 'orphaned_by_teammate_delete')
```

Do NOT propose "archive every empty KD after delete" — that would break Class C canon. The condition must be *"membership + last member,"* not *"empty result state."*

## §28. Enforcement-boundary analysis

| Boundary | Coverage | Atomicity | Testability | Risk of bypass | Verdict |
|---|---|---|---|---|---|
| `TeammateViewSet.perform_destroy` | DRF only | tx around one request | high | admin, mgmt cmds, tests bypass | Rejected |
| dedicated `TeammateDeletionService` module | callers must opt-in | good | high | anyone calling `Teammate.delete()` directly bypasses | Rejected (relies on discipline) |
| `Teammate.delete()` model override | single-instance only | tx per row | high | `queryset.delete()` (admin bulk delete via `delete_selected`) bypasses model.delete(); iterates rows via collector only | Rejected — bypass real |
| **`@receiver(pre_delete, sender=Teammate)`** | catches **every** ORM path (single `.delete()`, `queryset.delete()`, admin bulk, mgmt cmds, tests). Only raw SQL bypasses. Fires per-row for both single and bulk. | tx per delete (parent tx) | high | raw SQL only | **Winner** |
| `@receiver(m2m_changed, sender=KnowledgeDocument.spokespeople.through)` on `pre_remove` | catches M2M edits including cascade-remove | tx-tied | high | wrong semantics — fires for `.detach()` too (broader than delete) | Rejected — semantic mismatch |
| DB-level check constraint | at commit | strong | opaque to Python | catches nothing at app layer (can't set `is_active` via constraint) | Rejected |

**Recommendation: `pre_delete` signal on `Teammate` at `shell/apps/spokespeople/signals.py`.** `shell/apps/spokespeople/apps.py:15-18` already imports `signals` in `ready()` — no wiring change needed.

Bulk-delete note: Django's collector iterates and fires `pre_delete` per row for `queryset.delete()`. Under the same transaction. Small per-row overhead is acceptable — Teammate deletes are rare (not a hot path).

## §29. `is_active` semantic audit — verdict

Currently **DELETED** (soft-delete), single-purpose, clean:

| Set False | `shell/apps/embeddings/views.py:116` (`destroy()`) — operator-triggered soft-delete |
| Set True | `shell/apps/embeddings/ingestion.py:117` — implicit revival via `(workspace, content_hash)` dedup on re-ingest |
| Filtered in retrieval | `shell/apps/embeddings/retrieval.py:155,196,364` |
| Filtered in list | `shell/apps/embeddings/views.py:70` (viewset queryset) |
| Filtered in workspace stats | `shell/apps/accounts/views.py:146` |
| Admin display | `shell/apps/embeddings/admin.py:29` list_display; `:32` list_filter |
| SPA rendering | None. `web/src/lib/api/knowledge.ts:69` types it but no UI shows or acts on it |
| Explicit reactivate endpoint | None |
| Distinguishable from other set-False causes | No — no `reason` field, no `deactivated_at` |

**Overloading `is_active` for orphan-archive without a companion column: CONVENIENT-BUT-OVERLOADED.**
- Both paths (operator delete + orphan archive) would set `is_active=False`.
- Later audit cannot distinguish intent.
- Re-ingestion dedup (`ingestion.py:113-131`) blindly restores any inactive row — orphan-archived KDs would be re-activated by a coincidental content-hash collision, which is not always desired.

**Mitigation (small):** add `deactivated_reason = CharField(max_length=32, blank=True, default="")` (choices: `""` / `"operator_delete"` / `"orphaned_by_teammate_delete"`) as part of the same migration. Nullable-blank preserves backward compat; existing rows keep `""`.

This is the smallest schema addition that removes the semantic overload from day 1.

## §30. Reassignment / reactivation audit

Today:

- **Attach single spokesperson (K5):** `POST /api/knowledge/<id>/attach/` (`shell/apps/embeddings/views.py:122-148`). **Blocks on `is_active=True`** — get_object filters `is_active=True` (line 70). An inactive KD returns 404. Impact: after Option A archives a KD, operator cannot attach a replacement teammate without first flipping `is_active=True`.
- **Detach single spokesperson (K5):** symmetric — same 404 gate.
- **Bulk reassign:** no endpoint, no SPA.
- **Manual reactivate:** no endpoint. Only path is re-ingestion of identical content (dedup-triggered).
- **Universe reassign:** PATCH `universe` field is accepted by `KnowledgeDocumentSerializer` (`shell/apps/embeddings/serializers.py:111,404-424`) but no SPA UI exposes it. Direct API call required.
- **View inactive KDs:** admin-only. SPA has no "archived" tab.

**Implication for Option A:** the immediate safety fix is technically ship-able WITHOUT recovery UI (the KD is safe from audience widening the moment it becomes inactive; further recovery is optional). But Chris would rely on admin + re-ingest to recover. **Recommendation: ship Option A backend independently; ship recovery UI as Slice 3/4 depending on Chris's urgency.** See §35.

Minimum recovery affordances the SPA would need in a follow-up slice:

1. "Show archived" toggle on `/workspace/knowledge` list (filter param `include_inactive=true` → viewset relaxes `is_active` filter).
2. Badge on archived rows (e.g., "Archived — assigned character deleted" when `deactivated_reason='orphaned_by_teammate_delete'`).
3. Restore button that flips `is_active=True` (small new `POST /api/knowledge/<id>/restore/` endpoint or PATCH exposure of `is_active`).
4. Attach action needs to accept `is_active=False` KDs (relax the 404 gate for restore-then-attach flows) OR chain restore → attach as one operator gesture.

## §31. Historical provenance impact

`resolve_chunk_ids_to_docs()` (`shell/apps/embeddings/retrieval.py:63-118`) intentionally **does NOT filter `document__is_active`.** Docstring lines 71-74 confirm: *"resolving the K6-populated `Composition.knowledge_chunk_ids` JSON list."* Missing chunks are skipped silently (`if chunk is None: continue`, lines 102-104), but soft-deleted chunks (still on disk under an inactive KD) are found and returned normally.

**Consequence for Option A:** setting `is_active=False` on an orphaned KD does NOT break Composition provenance display. Historical "this render drew from …" continues to resolve. Regression contract §32 test 8 will lock this in.

## §32. Desired regression contract — 10 tests (design, not implementation)

Target file: `shell/apps/spokespeople/tests/test_delete.py` (extend) or a new `test_delete_orphan_archive.py`.

| # | Test name | Setup | Action | Assertion | Gap covered |
|---|---|---|---|---|---|
| 1 | `test_last_spokesperson_delete_legacy_inactivates_kd` | KD `universe=None, spokespeople={A}`, legacy teammate T | delete A | `KD.is_active=False`, `deactivated_reason='orphaned_by_teammate_delete'`; `retrieve_for_teammate(T)` returns 0 chunks | B→A promotion blocked |
| 2 | `test_last_spokesperson_delete_universe_inactivates_kd` | KD `universe=U, spokespeople={A}`, second teammate B in U | delete A | `KD.is_active=False`; `retrieve_for_teammate(B)` returns 0 chunks | D→C promotion blocked |
| 3 | `test_multi_spokesperson_delete_one_leaves_kd_active` | KD `spokespeople={A,B}` | delete A | `KD.is_active=True`; `KD.spokespeople.count()==1`; retrieval for B still returns it | audience narrowing (safe) preserved |
| 4 | `test_multi_spokesperson_delete_sequential_final_inactivates` | KD `spokespeople={A,B}` | delete A → delete B | after A: active with `{B}`; after B: `is_active=False` | Sequential-to-empty guarded |
| 5 | `test_born_empty_class_c_survives_universe_member_delete` | KD `universe=U, spokespeople=∅` (canon); teammate R in U | delete R | KD unchanged; `is_active=True`; retrieval for other U-members still returns it | Class C canon protected |
| 6 | `test_born_empty_class_a_survives_legacy_teammate_delete` | KD `universe=None, spokespeople=∅`; unrelated legacy teammate T | delete T | KD unchanged; `is_active=True` | Class A canon protected |
| 7 | `test_chunks_and_embeddings_survive_orphan_archive` | KD with 3 chunks + vectors, `spokespeople={A}` | delete A | KD chunks count still 3; embedding vectors still present; only `is_active` flipped | Data preservation preserved |
| 8 | `test_composition_provenance_resolves_after_orphan_archive` | Composition C with `knowledge_chunk_ids=[chunk_ids of KD]`, `spokespeople={A}` on KD | delete A | `resolve_chunk_ids_to_docs(C.knowledge_chunk_ids)` still returns all chunks + doc titles | Provenance preserved |
| 9 | `test_teammate_delete_atomic_if_kd_update_fails` | KD `spokespeople={A}`, force `KnowledgeDocument.objects.filter().update()` to raise via mock | delete A | Teammate NOT deleted; KD.is_active still True; transaction rolled back | Atomicity |
| 10 | `test_deactivated_reason_distinguishes_operator_delete_from_orphan_archive` | Two KDs: KD1 operator-deleted via `DELETE /api/knowledge/<KD1>/`; KD2 orphan-archived via last-spokesperson-delete | inspect both | KD1: `is_active=False, deactivated_reason='operator_delete'`; KD2: `is_active=False, deactivated_reason='orphaned_by_teammate_delete'` | Semantic clarity of overload mitigation |

Also add coverage for the bulk-delete boundary: `test_bulk_queryset_delete_triggers_orphan_signal` — asserts that `Teammate.objects.filter(...).delete()` (used by admin's `delete_selected`) fires the signal per row and archives the KDs (§28 concern).

## §33. Existing nine-KD remediation — kept separate

The nine live Class A orphan-candidate KDs in `chriss-workspace` (Slice 1 §2, §12) are NOT auto-remediated by Option A. Option A is a **forward-only** contract — it triggers on a delete event that has not yet happened. It does nothing on existing rows.

**Explicitly reject** an automatic backfill of the form *"set `is_active=False` for every KD where `universe=None, spokespeople=∅`"* — that would break intentional Class A/C canon (§27 confirms canon can be born-empty; we cannot mechanically distinguish canon from orphan for pre-existing rows without a history journal).

Options for later remediation, listed for record — do NOT choose in Slice 2:

- **Leave as-is.** Zero risk of collateral archive; accepts that 8-9 rows may broadcast to legacy teammates in Chris's workspace.
- **Manual per-KD operator review.** Ship a small SPA screen listing the 9 candidates + a per-row "archive / promote to canon / reassign to teammate" chooser.
- **Content-shape heuristic + operator confirmation.** Content-sniff (like Slice 1 §2 did — "Tulsi", "TANK", "Riggs", "About Hearth & Hollow" all title-shaped for characters) produces a shortlist; operator confirms archive.
- **Preserve + attach to Chris's active teammates.** Reassign the Hearth & Hollow set to a still-present teammate if the bookstore ever becomes an active identity again; archive the character-named ones.

Defer to Slice 3+.

## §34. Operator / UI contract

The Teammate delete modal currently says only *"videos and assets remain."* After Option A ships, the modal MUST be able to state (operator semantics, not final copy):

- The character will be deleted.
- Videos already generated will remain in the library.
- Compositions, scripts, campaigns, and threads that this character produced will remain (attributed as `character deleted`).
- **Knowledge that was assigned only to this character will be archived** (no longer available for retrieval; recoverable by admin or by re-ingest of the same content).
- **Knowledge shared with other characters will remain assigned to those characters.**
- **Knowledge intentionally shared with the Universe or workspace (never assigned to a specific character) will remain shared.**
- **Knowledge will NOT silently become available to other characters.**

The backend safety fix (§28) can ship **independently** of this copy — the invariant is enforced regardless of what the modal says. But shipping backend without UI-copy update leaves operators surprised when they later notice an archived KD. Recommend shipping copy update in the same commit as the backend fix, and defer the richer per-KD chooser (§25 Option E) + recovery UI (§30) to Slice 3.

## §35. Recommended immediate contract

**Adopt Option A + `deactivated_reason` column.**

Why it wins:
- Satisfies the invariant (§23) in every scenario (§26).
- Preserves data + preserves historical provenance (§24, §31).
- Enforcement boundary is airtight for every ORM deletion path (§28).
- Correctly distinguishes intentional Class C/A canon from orphaned-empty (§27).
- Minimal schema delta: one nullable CharField.
- Reuses existing `is_active` filter path — retrieval / list / stats already respect it (§29).
- Provenance-safe by prior design of `resolve_chunk_ids_to_docs` (§31).
- Signal + column pair enables clean future recovery UI without further schema changes.

## §36. Long-term lifecycle direction

Adopt **Option C (explicit audience model)** in a future session paired with SESSION 274 §8.5 P4 / KnowledgeAudience work. Option A is *not* orthogonal to Option C — the `deactivated_reason='orphaned_by_teammate_delete'` marker becomes `audience=ORPHANED` under Option C's enum. Migration path is straightforward: mirror is_active → audience during the Option C migration, then deprecate the CharField `deactivated_reason` in favor of the enum.

Option E (per-KD chooser on delete modal) is the natural UX complement once Option C ships — with explicit audience states, the operator's choices become "reassign to teammate X / promote to workspace-shared / promote to universe-shared / archive / delete." Slice ε or ζ material.

## §37. Proposed implementation plan (Option A + `deactivated_reason`)

**Files to touch:**

| File | Change | Lines est. |
|---|---|---|
| `shell/apps/embeddings/migrations/0NNN_add_deactivated_reason.py` | new migration: add `deactivated_reason` CharField(max_length=32, blank=True, default="") to `KnowledgeDocument` | ~25 |
| `shell/apps/embeddings/models.py` | add `deactivated_reason` field with `TextChoices` (empty / `OPERATOR_DELETE` / `ORPHANED_BY_TEAMMATE_DELETE`) | ~15 |
| `shell/apps/embeddings/views.py:110-118` | `destroy()` sets `deactivated_reason='operator_delete'` alongside `is_active=False` | +1 line, +1 update_field |
| `shell/apps/embeddings/ingestion.py:113-131` | when re-ingest revives a soft-deleted KD, clear `deactivated_reason` back to "" | +1 line |
| `shell/apps/embeddings/serializers.py` | expose `deactivated_reason` as read-only in `KnowledgeDocumentSerializer` | +1 field, +1 in `read_only_fields` |
| `shell/apps/spokespeople/signals.py` | add `@receiver(pre_delete, sender=Teammate)` handler that finds KDs where deleted teammate is sole spokesperson and bulk-updates them to `is_active=False, deactivated_reason='orphaned_by_teammate_delete'` | ~45 |
| `shell/apps/spokespeople/tests/test_delete.py` (or new `test_delete_orphan_archive.py`) | 10 regression tests per §32 + 1 bulk-delete test | ~350 (tests are verbose) |
| `web/src/components/spokesperson-delete-modal.tsx:95-98` | update copy per §34 (operator semantics; final wording is Chris's call) | ~10 |

**Query shape for signal handler (Django ORM):**

```python
from django.db.models import Count
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone

@receiver(pre_delete, sender=Teammate)
def archive_kds_orphaned_by_teammate_delete(sender, instance, **kwargs):
    # Import inside the handler to avoid the models.py circular chain.
    from apps.embeddings.models import KnowledgeDocument, DeactivationReason

    # Find every KD where this teammate is currently the SOLE spokesperson.
    # Use the through-table for a distinct count (avoiding the JOIN
    # amplification that a naive Count('spokespeople') would produce
    # when combined with a filter on that same M2M).
    orphan_kd_ids = (
        KnowledgeDocument.objects
        .filter(spokespeople=instance, is_active=True)
        .annotate(sp_count=Count(
            "knowledgedocumentspokesperson",
            distinct=True,
        ))
        .filter(sp_count=1)
        .values_list("pk", flat=True)
    )
    if orphan_kd_ids:
        KnowledgeDocument.objects.filter(pk__in=list(orphan_kd_ids)).update(
            is_active=False,
            deactivated_reason=DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE,
            updated_at=timezone.now(),
        )
```

**Transaction strategy:** `pre_delete` fires inside the same transaction as `Teammate.delete()`. Django's atomic transaction wrapping (default in DRF request handlers via `ATOMIC_REQUESTS` or per-endpoint `transaction.atomic`) means: if the KD update raises, the teammate delete rolls back. Test 9 in §32 asserts this.

**Backward compatibility:** `deactivated_reason` is nullable with `default=""` — no data migration required; existing rows keep the default. Serializer field is read-only; no SPA client changes required to consume it.

**Migration requirements:** YES — one `AlterField` / `AddField` migration on `KnowledgeDocument`. Zero downtime; column addition is fast on Postgres.

**Existing 9 orphan-candidate KDs:** UNTOUCHED by this plan (§33). Their `deactivated_reason` will remain `""` post-migration.

**Rollback considerations:**
- Signal is idempotent — running Teammate delete twice on the same teammate would find zero orphaned KDs on second pass.
- Migration is reversible with a matching `RemoveField` operation (no data loss because the column is additive and never load-bearing for reads outside the audit trail).
- Ship behind a feature flag if Chris wants to observe first? Not required — the signal only fires on the exact delete-with-last-spokesperson case, which is a rare event. Direct ship is acceptable.

**Backward-compat with re-ingestion revival (`ingestion.py:113-131`):** the current code flips `is_active=True` on dedup hit. That code is unaware of `deactivated_reason`. Small addition: clear the reason on revival. Otherwise a revived orphaned KD would falsely claim `deactivated_reason='orphaned_by_teammate_delete'`.

**Non-goals in this implementation:**
- Recovery UI (Slice 3+).
- "Show archived" toggle in Knowledge list (Slice 3+).
- Modal per-KD chooser à la Option E (Slice 3+ / Option C companion).
- Backfill / triage of the 9 existing orphan-candidate KDs (deferred; §33).
- Any migration of Composition provenance shape (unnecessary — provenance is provably safe under Option A).

## §38. Slice 2 decision gate

Slice 2 is a design/decision slice. Nothing has been implemented. All source, DB, KDs, teammates, retrieval, SPA copy, and models remain untouched. The 9 orphan-candidate KDs remain preserved.

**Chris must explicitly approve before implementation begins.** Approval targets:

1. Adopt the no-audience-broadening invariant as stated in §23.
2. Adopt Option A + `deactivated_reason` column as the immediate safety contract (§35).
3. Defer Option C (explicit audience) + Option E (per-KD chooser) + recovery UI to later slices (§36, §30).
4. Do NOT auto-remediate the 9 existing orphan-candidate KDs (§33).
5. Update the Teammate delete modal copy in the same commit as the backend fix (§34).

Optional companion decision:

6. Ship a lightweight "Show archived" list toggle + Restore button in the SAME slice as the backend fix, so operators aren't waiting on Slice 3 for recovery capability. Recommendation: **Yes**, but Chris's call.

### Slice 2 checklist

- [x] Slice 1 committed / pushed (`66c45fd`)
- [x] no-audience-broadening invariant assessed — SUPPORTED (§23)
- [x] preservation vs active retrieval separated (§24)
- [x] Option A assessed (§25)
- [x] Option B assessed (§25)
- [x] Option C assessed (§25)
- [x] Option D assessed (§25)
- [x] Option E assessed (§25)
- [x] multi-spokesperson lifecycle assessed (§26)
- [x] intentionally shared KD lifecycle assessed (§27)
- [x] enforcement boundaries compared (§28)
- [x] `is_active` semantics audited (§29)
- [x] reassignment/reactivation audited (§30)
- [x] Composition provenance impact assessed (§31)
- [x] desired regression contract designed (§32)
- [x] existing orphan remediation separated (§33)
- [x] operator/UI contract defined (§34)
- [x] immediate safety recommendation made (§35)
- [x] long-term model recommendation made (§36)
- [x] implementation plan produced (§37)
- [x] **Chris approval obtained** — Slice 2 approved with modification (no generic "Show archived + Restore" in this slice)

---

# SESSION 275 — Slice 3 — Implementation

**Slice 3 implements the Option A + `deactivated_reason` contract approved in Slice 2 with Chris's modification that no generic Restore/Show-archived UI ships in this slice.**

## §39. Slice 3 approval snapshot

Chris + ChatGPT approved 2026-08-20:

1. Adopt the no-audience-broadening invariant (§23).
2. Adopt Option A + `deactivated_reason` immediate safety contract (§35).
3. Adopt `pre_delete`-based enforcement (§28), subject to test validation.
4. Do NOT auto-remediate the 9 existing orphan-candidate KDs (§33).
5. Update the Teammate delete modal copy in the same slice (§34).
6. Defer Option C / Option E / recovery UI to later slices (§36, §30).

**Modification vs Slice 2 §38 item 6:** DO NOT ship a generic "Show archived + Restore" affordance in Slice 3. A bare `is_active=False → True` restore on a `spokespeople=∅` KD recreates the exact audience-widening hazard. Future recovery must require an explicit safe-audience decision (attach a character, promote to Universe-shared, promote to workspace-shared). Slice 3 records this as a load-bearing requirement for the future recovery slice (§46).

## §40. Files changed

| File | Change | Purpose |
|---|---|---|
| `shell/apps/embeddings/models.py` | Added `DeactivationReason` TextChoices + `deactivated_reason` CharField(max_length=40, blank, default="") on `KnowledgeDocument` | Distinguishable orphan-archive vs operator-delete state |
| `shell/apps/embeddings/migrations/0006_session275_deactivated_reason.py` | New migration adding the field | Applied cleanly to local Postgres (0006 → OK) |
| `shell/apps/spokespeople/signals.py` | Added `_stash_kd_membership_for_orphan_check` (pre_delete) + `_archive_orphaned_kds_on_teammate_delete` (post_delete) | Enforce audience invariant on every ORM delete path (single + bulk) |
| `shell/apps/embeddings/views.py` | `KnowledgeDocumentViewSet.destroy` also stamps `deactivated_reason=OPERATOR_DELETE`; added import | Distinguishable operator-delete reason |
| `shell/apps/embeddings/ingestion.py` | Added `OrphanRevivalRejected` exception + safe-revival gate in `_persist`; revival now clears `deactivated_reason` | Prevent re-ingestion from silently reactivating an orphan-archived KD into empty-M2M broadcast |
| `shell/apps/embeddings/serializers.py` | Added `deactivated_reason` to fields + `read_only_fields`; added `OrphanRevivalRejected` catch in all three ingest branches | Read-only API exposure; clean 400 on rejected revival |
| `web/src/components/spokesperson-delete-modal.tsx` | Added second paragraph disclosing knowledge lifecycle contract; updated docstring | Operator can reason about audience scope before confirm |
| `web/src/components/spokesperson-delete-modal.test.tsx` | Added `discloses the SESSION 275 knowledge-lifecycle contract` test | Locks the copy contract |
| `shell/apps/spokespeople/tests/test_delete_orphan_archive.py` | New 12-test regression file | 10 cases from §32 + bulk-delete case + operator-revival case |
| `shell/apps/embeddings/tests/test_retrieval_privacy.py` | Added the new test file to K0 privacy `ALLOWED_FILES` | Sanctioned test-side writer for `KnowledgeChunk.objects.create` (real pgvector seeds) |
| `shell/apps/compositions/tests/test_isolation.py` | Added the new test file to composition-writer `ALLOWED_FILES` | Sanctioned test-side writer for `Composition.objects.create` (provenance test) |

Nothing else was touched. `shell/apps/spokespeople/apps.py:15-18` already imports `signals` in `ready()` — no wiring change was needed.

## §41. Migration

`shell/apps/embeddings/migrations/0006_session275_deactivated_reason.py` — depends on `0005_universe_fk`. Applied cleanly to the local Postgres via `python manage.py migrate embeddings`:

```
Operations to perform:
  Apply all migrations: embeddings
Running migrations:
  Applying embeddings.0006_session275_deactivated_reason... OK
```

Migration is additive (one nullable CharField with `default=""`), so no data migration and zero downtime. `makemigrations --dry-run --check embeddings` reports "No changes detected" against the model — migration matches the field definition exactly.

## §42. Signal behavior — final implementation

Two receivers, coordinated via a private instance attribute:

- **`@receiver(pre_delete, sender=Teammate) _stash_kd_membership_for_orphan_check`** — snapshots the list of KD ids where this teammate is currently a spokesperson (via `KnowledgeDocumentSpokesperson.filter(teammate=instance).values_list('knowledgedocument_id')`) and stores it on `instance._session275_orphan_candidate_kd_ids`.
- **`@receiver(post_delete, sender=Teammate) _archive_orphaned_kds_on_teammate_delete`** — reads the snapshot; queries `KnowledgeDocument.filter(pk__in=snapshot, is_active=True).annotate(sp_count=Count('spokespeople')).filter(sp_count=0)`; bulk-updates the survivors to `is_active=False, deactivated_reason=ORPHANED_BY_TEAMMATE_DELETE`.

**Why not a single pre_delete?** The Slice 2 §37 sketch proposed a pre_delete that filters on `sp_count=1`. Test 9 (bulk-delete of two teammates sharing a KD) proved that pattern was wrong: when Django's Collector fires all pre_delete signals BEFORE any cascade SQL runs, each teammate's pre_delete still sees the OTHER doomed teammates as spokespeople — a KD with `{A,B}` where both are being deleted looks "still has 2 members" to both pre_delete handlers, and neither archives it. Splitting into pre_delete-snapshot + post_delete-check-post-cascade correctly handles both single- and bulk-delete. This is a deviation from the Slice 2 §37 pseudocode (see §48) — the invariant and the file targets are unchanged, but the mechanism moved to a two-signal pattern that only became necessary once the test suite proved it.

Bulk-delete correctness in post_delete: for two teammates sharing a KD, both post_delete handlers see the KD as empty. The first sets `is_active=False`; the second's `is_active=True` filter matches nothing and does nothing. No duplicate stamps, no logic collision.

## §43. Single-spokesperson result

Test 1 (`test_last_spokesperson_delete_legacy_inactivates_kd`) + Test 2 (`test_last_spokesperson_delete_universe_inactivates_kd`) — PASS.

Confirmed: `spokespeople={A}` (universe=None or universe=U) → delete A → KD becomes `is_active=False`, `deactivated_reason='orphaned_by_teammate_delete'`, `spokespeople.count()==0`. `retrieve_for_teammate` returns 0 chunks for any other legacy teammate (Case 1) or any other same-Universe teammate (Case 2).

## §44. Multi-spokesperson result

Test 3 (`test_multi_spokesperson_delete_one_leaves_kd_active`) + Test 4 (`test_multi_spokesperson_delete_sequential_final_archives`) + Test 9 (`test_bulk_queryset_delete_triggers_orphan_archive_per_row`) — ALL PASS.

Confirmed:
- `{A,B}` → delete A → KD stays active with `{B}`. B still retrieves it. Audience narrowed safely.
- `{A,B}` → delete A then delete B (sequential) → after A: active; after B: archived.
- `{A,B}` → bulk `Teammate.objects.filter(pk__in=[A,B]).delete()` → KD_shared archived by whichever post_delete fires first; second post_delete no-ops because of the `is_active=True` filter.

## §45. Intentionally shared KD result

Test 5 (`test_born_empty_class_c_canon_survives_universe_member_delete`) + Test 6 (`test_born_empty_class_a_canon_survives_unrelated_delete`) — PASS.

Confirmed by construction: the pre_delete snapshot lists only KDs where THIS teammate is currently a spokesperson. Class C canon (born-empty) never had the deleted teammate in its M2M, so it never enters the snapshot; post_delete never touches it. Class A born-empty is symmetric. The load-bearing distinction from §27 holds in code, not just in design.

## §46. Operator-delete behavior

Test 10 (`test_deactivated_reason_distinguishes_operator_delete_from_orphan`) — PASS.

Operator soft-delete via `DELETE /api/knowledge/<id>/` now sets `deactivated_reason='operator_delete'` alongside `is_active=False` (`views.py:110-124`). System orphan-archive sets `deactivated_reason='orphaned_by_teammate_delete'`. Both flip `is_active=False`; the reason field discriminates.

## §47. Orphan-archive behavior + safe-revival gate

Test 11 (`test_ingestion_revival_rejects_orphan_without_spokespeople`) + Test 12 (`test_ingestion_revival_of_operator_deleted_kd_still_works`) — PASS.

`ingestion._persist` now branches on `existing.deactivated_reason` when the dedup hit is soft-deleted:

- Reason == `ORPHANED_BY_TEAMMATE_DELETE`:
  - If caller supplied NO spokespeople (or empty list) → raise `OrphanRevivalRejected`. KD stays inactive with reason preserved. Serializer catches the exception in each ingest branch and returns HTTP 400 with the error attached to `spokesperson_ids`.
  - If caller supplied non-empty spokespeople → revive normally: `is_active=True`, `deactivated_reason=""`, `spokespeople.set(new_list)`. Audience is bounded by the explicit new set — safe.
- Reason == `OPERATOR_DELETE` (or blank legacy):
  - Revive as today. `deactivated_reason` cleared to `""`. Prior M2M preserved if caller supplied nothing (unchanged behavior); replaced if caller supplied a new list.

**Future recovery invariant (§16, kept as load-bearing rule for later slices):** any recovery flow that flips `is_active=False → True` for an `ORPHANED_BY_TEAMMATE_DELETE` KD MUST require an explicit safe-audience decision (attach character(s), promote to Universe-shared, or promote to workspace-shared). A bare flip is disallowed. Slice 3 enforces this at the ingestion revival boundary; a future recovery UI must enforce the same at the admin/API boundary before shipping.

## §48. Composition provenance result

Test 8 (`test_composition_provenance_resolves_after_orphan_archive`) — PASS.

`resolve_chunk_ids_to_docs(chunk_ids, workspace=ws)` continues to return the archived KD's chunks + title (output shape: `{id, title, chunk_count}`) after orphan-archive flips `is_active=False`. Confirms §31 design — the resolver intentionally omits the `is_active` filter, so historical Composition provenance survives orphan-archive unchanged.

## §49. Bulk QuerySet.delete result

Test 9 (`test_bulk_queryset_delete_triggers_orphan_archive_per_row`) — PASS.

`Teammate.objects.filter(pk__in=[A,B]).delete()` correctly archives:
- KD_solo_a (A was sole spokesperson) → orphaned
- KD_solo_b (B was sole spokesperson) → orphaned
- KD_shared (A and B were both spokespersons) → orphaned by the first post_delete handler; second no-ops via `is_active=True` filter

Confirms the pre_delete/post_delete split (§42) handles admin's `delete_selected` and any programmatic queryset delete.

## §50. Atomicity result — PROVEN BY TEST

**§50 originally stated that atomicity was reasoned-only. Chris + ChatGPT reviewed Slice 3 and correctly flagged that this was an unmet acceptance condition. The atomicity gap is now closed by an explicit failure-injection regression test — added after that review; this section is rewritten to reflect the new evidence.**

Test: `test_teammate_delete_atomic_if_orphan_archive_update_fails` in `shell/apps/spokespeople/tests/test_delete_orphan_archive.py` (case 13 of the test matrix).

**Failure injection method.** Patches `django.db.models.query.QuerySet.update` at the class level via `pytest`'s `monkeypatch` fixture, but only raises for updates whose `self.model is KnowledgeDocument`. Every other `.update()` in the delete plan runs unchanged. The archive step in `_archive_orphaned_kds_on_teammate_delete` calls exactly one such update (`KnowledgeDocument.objects.filter(pk__in=orphan_ids).update(...)`), so the injection hits exactly the archive write. Django's Collector uses `sql.UpdateQuery.update_batch` directly for SET_NULL cascades (Composition / Script / Asset etc.) — those are NOT routed through `QuerySet.update` — so the injection does NOT interfere with the SET_NULL fan-out.

**Exception type.** A test-local `InjectedArchiveFailure(RuntimeError)` marker so we can uniquely assert we caught OUR raise (not a coincidental DB error).

**Boundary.** The teammate delete is wrapped in `with transaction.atomic()` inside the test so the `django_db` outer transaction can observe the rollback of the savepoint without contaminating fixture state. Inside the savepoint, `Collector.delete()` wraps its operations in `mark_for_rollback_on_error(self.using)` (`django/db/models/deletion.py:452`) — the raise propagates, the connection is marked for rollback, and the atomic exit rolls back the savepoint.

**Pre-delete state (recorded).** `Teammate.objects.filter(pk=a.pk).exists()` = True; `KnowledgeDocument.objects.filter(pk=kd.pk).exists()` = True; `kd.is_active` = True; `kd.deactivated_reason` = ""; `kd.chunks.count()` = 1; `KnowledgeDocumentSpokesperson.objects.filter(teammate=a, knowledgedocument=kd).exists()` = True.

**Injection observed.** `call_hits["count"] >= 1` — the archive `.update()` was attempted (proves we tested the real path, not an unrelated failure).

**Post-rollback state (asserted).** Every one of the pre-delete assertions holds exactly. Teammate row present. KD present. `is_active=True` unchanged. `deactivated_reason=""` unchanged. Through-row present. Chunk count unchanged.

**Transaction-boundary evidence.** `Model.delete()` and `QuerySet.delete()` both funnel through `Collector.delete()` (`django/db/models/deletion.py:436`), which wraps operations in `mark_for_rollback_on_error(self.using)` (line 452). Confirmed via `grep` on the pinned `django/db/models/deletion.py` in the local venv (Django 5.2.16). This means the atomicity contract proven by the single-instance test above is identical for `QuerySet.delete()` — no duplicate bulk-atomicity test is required. Test 9 already exercises the bulk-delete happy path; the atomicity contract is inherited from the same Collector.

**Invariant proven.** Either the teammate delete + M2M through-row cascade + KD orphan-archive all commit, or NONE of them commit. No partial-state observable.

## §51. Ingestion / reactivation finding

The revival gate (§47) means the safe-revival contract is enforced end-to-end at the ingestion boundary today. No other reactivation path exists in the operator-facing SPA (§30 Slice 2). Admin can still hard-set `is_active=True` via Django admin — that path is admin-only and out of scope for operator-safety guarantees; the future recovery slice will address it (§46 load-bearing rule).

## §52. Narrow test results

`pytest apps/spokespeople/tests/test_delete_orphan_archive.py` → **13 passed in 5.39s** (post-atomicity-test run). All test cases from §32 covered, plus:
- `test_bulk_queryset_delete_triggers_orphan_archive_per_row` (bulk-delete boundary)
- `test_ingestion_revival_of_operator_deleted_kd_still_works` (revival gate specificity)
- `test_teammate_delete_atomic_if_orphan_archive_update_fails` (atomicity — added after Chris + ChatGPT review of Slice 3 §50)

## §53. Broader regression results

Post-atomicity-test rerun: `pytest apps/spokespeople/tests/ apps/embeddings/tests/ apps/compositions/tests/ apps/universe/tests/` with `EMBEDDING_FORCE_MOCK=1` → **1636 passed in 126.31s. 0 regressions.** (Previously 1635; the +1 is the atomicity test.)

Full-suite run (`pytest`) with the same env → 2776 passed + 80 failures + 1 skipped **at Slice 3 pre-atomicity checkpoint**. Every failure was verified against pre-Slice-3 `main` (git-stashed) and reproduces identically. **Zero failures caused by Slice 3.** The 80 pre-existing failures are in `apps/bootstrap_review/tests/*` (missing `candidate.json` fixture files) and `character_os/clients/tests/test_media_engine_timeouts.py` (unrelated timeout assertion) — outside SESSION 275's scope. The atomicity addition only added one new test; the full-suite failure set is unchanged.

## §54. SPA verification

`npx vitest run src/components/spokesperson-delete-modal.test.tsx` → **8 passed** (7 pre-existing + 1 new for SESSION 275 knowledge-lifecycle copy).

Full SPA suite (`npx vitest run`) → **641 passed across 47 files, 0 failures.**

## §55. Existing nine-KD preservation confirmation

Queried `chriss-workspace` post-migration + post-code-change:

```
Total Class A KDs in chriss-workspace: 9
  aa90d895 About Hearth & Hollow Books                       is_active=True reason=''
  e37ea174 How We Recommend Books                            is_active=True reason=''
  b58efd31 Children's Reading                                is_active=True reason=''
  7f41d8e3 Bookstore Events                                  is_active=True reason=''
  c408656d Supporting Local Authors                          is_active=True reason=''
  0088f31f Helping Customers Find Their Next Read            is_active=True reason=''
  7ecde40b Tulsi — Core Identity and Public Purpose          is_active=True reason=''
  8c6f0c14 TANK — AUTOMOTIVE FINANCING CONTENT KNOWLEDGE     is_active=True reason=''
  90ad200c Riggs                                             is_active=True reason=''
```

All 9 KDs unchanged: `is_active=True`, `deactivated_reason=''` (blank because they predate the migration and no code path in Slice 3 touches existing rows). Ruby's Class C KD `8f825c98-…` (Fox & Flour) and Ruby's Class D KD `74e7f18f-…` similarly untouched.

## §56. Slice 3 checklist

- [x] Slice 2 committed (`0d…` — Slice 2 was in the same working tree as Slice 3 changes; both will land in Slice 3's commit per Chris's approval that Slice 2 didn't need its own commit before implementation)
- [x] `DeactivationReason` TextChoices added to `KnowledgeDocument` model
- [x] `deactivated_reason` field added; migration `0006_session275_deactivated_reason` created + applied
- [x] pre_delete + post_delete signals on `Teammate` implemented (`_stash_kd_membership_for_orphan_check` + `_archive_orphaned_kds_on_teammate_delete`)
- [x] `KnowledgeDocumentViewSet.destroy` stamps `deactivated_reason=OPERATOR_DELETE`
- [x] Ingestion revival gates on `deactivated_reason == ORPHANED_BY_TEAMMATE_DELETE` + no explicit spokespeople; raises `OrphanRevivalRejected`
- [x] `OrphanRevivalRejected` caught in all three ingest branches of `KnowledgeDocumentSerializer.create` → HTTP 400
- [x] `deactivated_reason` added to serializer fields + read_only_fields
- [x] `SpokespersonDeleteModal` copy updated with §34 semantics; docstring updated
- [x] `spokesperson-delete-modal.test.tsx` extended with `discloses the SESSION 275 knowledge-lifecycle contract` test
- [x] `test_delete_orphan_archive.py` — 12 tests covering §32 matrix + bulk + revival cases; all pass
- [x] K0 privacy `ALLOWED_FILES` updated to sanction the test file's `KnowledgeChunk.objects.create` seeds
- [x] Composition-isolation `ALLOWED_FILES` updated to sanction the test file's `Composition.objects.create` provenance seed
- [x] Migration applied cleanly; `makemigrations --dry-run --check` reports "No changes detected"
- [x] Narrow test run: 13/13 pass (12 original + 1 atomicity added after review)
- [x] Broader test run (spokespeople + embeddings + compositions + universe): 1636/1636 pass with `EMBEDDING_FORCE_MOCK=1`
- [x] Full test run: 2776 pass; 80 failures verified as pre-existing on baseline `main`
- [x] SPA test run: 641/641 pass
- [x] Nine orphan-candidate KDs preserved unchanged (verified via direct DB query)
- [x] Ruby's Class C `8f825c98-…` and Class D `74e7f18f-…` untouched
- [x] Composition provenance still resolves after orphan-archive (test 8)
- [x] **Atomic rollback verified by failure-injection regression test (test 13, added after Chris + ChatGPT flagged §50 gap)**
- [x] Documentation extended (§39-§56 + §50 rewritten with runtime evidence)
- [x] **Chris approval to commit Slice 3** — granted 2026-08-20, all acceptance conditions closed

## §57. Deviations from approved Slice 2 design

Two:

1. **Signal split** (§42): Slice 2 §37 sketched a single pre_delete handler that filtered `sp_count=1`. Slice 3 test 9 proved that pattern fails for bulk-delete of teammates who share a KD. Implementation moved to **pre_delete-snapshot + post_delete-check-post-cascade** — the enforcement boundary, target files, invariant, and semantics are unchanged; only the mechanism split into two signals. The single-signal §37 sketch was pseudocode; the two-signal implementation is the version proven by tests.

2. **Ingestion revival gate**: Slice 2 §29 flagged the ingestion revival hazard but §37 did not spell out the exception name or the caller-facing error shape. Slice 3 chose `OrphanRevivalRejected` (Python exception in `ingestion.py`) surfaced as a 400 with the error attached to `spokesperson_ids` via three per-branch except clauses in `serializers.py.create`. This is a specification refinement, not a design change.

No other deviations. The audience invariant, `deactivated_reason` field shape, target files, migration approach, and UI copy scope all match Slice 2 §37 exactly.

## §58. Slice 3 decision gate

**Nothing committed yet.** All Slice 3 changes are in the working tree, uncommitted, pending Chris's approval.

To commit: `git add …` (see §59 diff summary) and use a message like:

```
feat(session-275): §39-§58 Slice 3 — orphan-archive contract + safe revival gate
```

Recommended: single commit covering all Slice 3 files (migration + signals + views + ingestion + serializers + UI copy + tests + doc). Slice 2 doc additions (§21-§38) already commingled with Slice 3 additions in the working tree — one commit lands both since Slice 2 was doc-only and approval + implementation happen back-to-back.

## §59. Slice 3 git diff summary

```
10 files modified + 2 new files (post-atomicity-test):
  M docs/design/SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md  (+~540 for §21-§59)
  M shell/apps/compositions/tests/test_isolation.py                 (+7)
  M shell/apps/embeddings/ingestion.py                              (+61)
  M shell/apps/embeddings/models.py                                 (+38)
  M shell/apps/embeddings/serializers.py                            (+21)
  M shell/apps/embeddings/tests/test_retrieval_privacy.py           (+7)
  M shell/apps/embeddings/views.py                                  (+14, -3)
  M shell/apps/spokespeople/signals.py                              (+112, -5)
  M web/src/components/spokesperson-delete-modal.tsx                (+22, -2)
  M web/src/components/spokesperson-delete-modal.test.tsx           (+20)
  A shell/apps/embeddings/migrations/0006_session275_deactivated_reason.py  (~35)
  A shell/apps/spokespeople/tests/test_delete_orphan_archive.py     (~600 — bumped from ~475 by the atomicity test)
```

Zero unintended surface change. No changes to retrieval predicate, no changes to Universe interactions, no changes to Composition provenance resolver, no changes to intentional Class C/A canon semantics, no touch of the 9 orphan-candidate KDs, no touch of Ruby/Patch/Rivet/Mason.

## §60. Acceptance-condition reconciliation (post-review)

Literal comparison of the approved Slice 3 prompt's acceptance conditions against actual evidence:

| Requirement (Slice 3 prompt) | Status | Evidence |
|---|---|---|
| CASE 1 (`{A}` → delete A → archived + not retrievable) | Verified | Test 1 |
| CASE 2 (`{A,B}` → delete A → active with `{B}`; then delete B → archived) | Verified | Tests 3 + 4 |
| CASE 3 (born-empty ∅ → delete unrelated → no change) | Verified | Tests 5 + 6 |
| Distinguish "became empty" from "was already empty" | Verified — by construction (§27, §45) | Signal design + tests 5-6 |
| `deactivated_reason` semantics (active/default, operator_delete, orphaned_by_teammate_delete) | Verified | Model + test 10 |
| Operator DELETE also stamps `operator_delete` | Verified | View + test 10 |
| Legitimate re-ingestion reasoning + no accidental orphan reactivation | Verified | Ingestion gate + tests 11 + 12 |
| pre_delete enforcement (if source still supports) — source still supports; split to pre_delete + post_delete for correctness | Verified | Signals + §42/§57 |
| Atomic behavior (orphan-archive + Teammate delete) | **Verified by test 13** — was reasoned-only at first submission; closed by explicit failure-injection test after review | Test 13 + §50 |
| Verify `instance.delete()` and `QuerySet.delete()` behavior | Verified — same Collector transaction boundary confirmed via Django source (`deletion.py:452`); test 9 covers bulk delete happy path; test 13 covers single-delete atomicity (inherited by bulk) | §42 + §50 evidence |
| Regression matrix from §32 | Verified — all 10 designed cases exist + 2 additional (bulk, revival) + atomicity = 13 tests | Test file |
| Test invariants "prove behavior, not implementation details" | Verified — every test asserts observable state (M2M count, is_active, retrieval output, provenance resolution) not internal wiring | Test file |
| Do not weaken broadcast semantics | Verified | 293 embeddings-app tests including all existing retrieval-truth-table tests still green |
| Delete modal copy per §34 semantics | Verified | Modal + copy-contract test |
| No recovery UI | Verified — none added | Slice 3 diff |
| Nine orphan KDs untouched | Verified | §55 direct DB query |
| Migrations clean | Verified | `showmigrations` + `--dry-run --check` |
| No provider credit spend | Verified — no provider calls in any code path added | Diff review |

All acceptance conditions are now mechanically verified. **No other unmet acceptance condition remains after the atomicity gap closure.**

