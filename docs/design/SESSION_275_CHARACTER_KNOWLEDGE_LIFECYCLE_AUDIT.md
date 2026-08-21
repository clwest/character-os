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
