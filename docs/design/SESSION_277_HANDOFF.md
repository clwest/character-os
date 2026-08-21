# SESSION 277 — Handoff (from SESSION 276)

## Status at the top

- SESSION 276 is CLOSED. Direction Delta rolled out and sealed. See `docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md` §382 for the closeout.
- The Delta audience-invariant model is PERMANENT. `audience_scope` is now NOT NULL and constrained by three DB-level CheckConstraints.
- Current `KnowledgeDocument` substrate is intentionally empty (0 rows) after Slice 20's disposable-dogfood reset. Slice 21 preserved that state and added the DB constraints on top.
- Fresh operator dogfood on the clean substrate is the natural next activity.

## What NOT to do in SESSION 277

- **Do NOT reopen historical NULL remediation.** All 10 historical NULL rows were included in the disposable-dogfood scope (SESSION 276 §340). The Riggs correction (§279) and the audit history are preserved for evidence, not for future work.
- **Do NOT reintroduce empty-M2M-as-broadcast inference** in any retrieval, LIST, or serializer path. The pre-Delta shape-derived audience is gone. Positive intent is required at every write boundary.
- **Do NOT reintroduce a NULL audience compatibility branch** in `retrieval.py` or `views.py`. Migration 0009 made `audience_scope IS NULL` unrepresentable at the DB layer; any code path that assumes NULL would be dead code.
- **Do NOT add a PostgreSQL trigger for the CHARACTER→M2M-non-empty invariant.** That invariant intentionally remains at the application layer per SESSION 276 §361. Six write-boundary guards (Slices 8/10/13/14/15/20) cover every mutation path.
- **Do NOT hard-delete Workspaces, Users, Teammates, Universes, or unrelated Composition / Script / Video / RealtimeSession rows** while cleaning up. Chris's §340 preservation scope stands.
- **Do NOT append future work into the large `SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md` document.** That doc is evidence + history. New work goes in a fresh document.

## Facts about the current substrate

- `KnowledgeDocument` count: 0. `KnowledgeChunk` count: 0. Through-rows: 0.
- `audience_scope` column: NOT NULL.
- Active DB CheckConstraints (installed by migration 0009):
  - `session276_universe_requires_universe_fk` — UNIVERSE row must have a non-null `universe_id`.
  - `session276_workspace_forbids_universe_fk` — WORKSPACE row must have a null `universe_id`.
  - `session276_none_requires_inactive` — NONE row must have `is_active=False`.
- Migration head: `0009_session276_final_delta_constraints`.
- 128 `knowledge_chunk_ids` JSON arrays in Composition / Script / RealtimeSession rows reference deleted chunks. `resolve_chunk_ids_to_docs` returns `[]` silently for stale IDs. **Accepted dogfood residue** — no cleanup planned.
- SPA workspace-knowledge routes, ingestion primitives, retrieval + LIST predicates all work on the empty substrate and will work identically on freshly-ingested content.

## Permanent write contract (do not violate)

Every fresh `KnowledgeDocument` create through any supported path must supply a positive audience signal:

- `spokesperson_ids` non-empty → CHARACTER
- `universe` non-null → UNIVERSE
- `audience_scope="workspace"` (SPA) / `workspace_shared_intent=True` (internal Python) → WORKSPACE

Attempting to create without a positive signal raises:

- **DRF `POST /api/knowledge/`** → `400` with `{"code": "audience_scope_required_on_create", "detail": "..."}`
- **`apps.embeddings.ingestion.ingest_text/pdf/url`** or `_persist` directly → `django.core.exceptions.ValidationError`

The SPA's `UniverseScopePicker` gesture already emits a positive marker on every CREATE call site (SESSION 276 Slice 12).

## Recommended starting question for SESSION 277

> On a completely clean `KnowledgeDocument` substrate, does fresh operator dogfood through the current SPA create correctly-scoped `CHARACTER`, `UNIVERSE`, and `WORKSPACE` knowledge and retrieve / list each only to its intended audience without any migration compatibility behavior?

Execute that dogfood in SESSION 277, not here.

## Optional / non-blocking follow-ups

- `retrieve_universe_canon` positive-audience reformulation — aesthetic; can be indefinitely deferred without cost.
- Recovery UI / archived-KD SPA surface — separate future product decision.
- SPA-side smoke of the LIST + retrieval predicates on freshly-created scoped content — nice-to-have; a fresh dogfood run covers it implicitly.

## Where to look

- **Delta model + invariants:** `docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md` §46-§71 (design), §51 (invariants), §377 (permanent enforcement matrix).
- **Migration 0009:** `shell/apps/embeddings/migrations/0009_session276_final_delta_constraints.py`.
- **Retrieval predicate:** `shell/apps/embeddings/retrieval.py` `retrieve_for_teammate` (positive-audience Delta).
- **LIST predicate:** `shell/apps/embeddings/views.py` `KnowledgeDocumentViewSet.get_queryset` `?spokesperson=` branch.
- **Serializer guard:** `shell/apps/embeddings/serializers.py` `KnowledgeDocumentSerializer.validate` (positive audience required on CREATE).
- **Ingestion guard:** `shell/apps/embeddings/ingestion.py` `_persist` else branch (fails closed).
- **Orphan / revival:** `shell/apps/spokespeople/signals.py` (pre_delete stash + post_delete atomic NONE-stamp).

## Discipline summary

- Positive audience intent, always.
- No NULL compatibility, anywhere.
- CHARACTER→M2M-non-empty stays at the application layer.
- DB scalar invariants stay at the DB layer.
- Empty substrate is the intended starting state for fresh dogfood.
- SESSION 276 is closed; treat its audit doc as history + evidence.
