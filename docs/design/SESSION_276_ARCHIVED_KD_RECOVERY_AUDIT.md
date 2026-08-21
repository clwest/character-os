# SESSION 276 — Archived-KD recovery + legacy KD ambiguity — Slice 1 + Slice 2

**Status.** READ-ONLY orient / audit for both slices. No code, migration, DB row, or SPA behavior modified. No provider spend. Working tree changes limited to this document.

**Owner.** Chris (chris@donkeybetz.com).
**Baseline commit.** `d4754737d1d66bbae9fa261308ae36d93ff1769d` (`main == origin/main`).
**Preceding session.** SESSION 275 CLOSED at `05e6f8f`; SHA-record follow-up `45e82f5..d475473`.
**Preceding handoff.** `docs/design/SESSION_276_HANDOFF.md`.
**Preceding audit.** `docs/design/SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md` §12, §27, §29–§31, §46, §47, §61.

---

## §1. Falsifiable question

> Does Character OS currently preserve enough information — in `KnowledgeDocument` state, surviving historical evidence, and existing operator/API surfaces — for an operator to make a **safe explicit audience decision** for both:
>
> 1. a **future** KD archived as `orphaned_by_teammate_delete`, where provenance is known; and
> 2. one of the **nine historical** empty-M2M Class A KDs in `chriss-workspace`, where provenance may be ambiguous?

Two evidence tracks investigated inside the same read-only slice.

## §2. Prediction / hypothesis before evidence

- **Track A (legacy):** at least a subset of the 9 KDs will be classifiable from surviving DB state + design-doc references + Composition/Asset SET_NULL fingerprints. A subset will be genuinely indeterminate.
- **Track B (future orphan):** the SESSION 275 signal + revival gate seal the orphan-archive path but leave a "no operator-visible surface + admin-only revival" gap. The API path is likely sealed too by the `is_active=True` queryset filter, but this requires verification.

## §3. Baseline verification (§J of SESSION 276 handoff)

Executed 2026-08-21. All checkboxes evidence-backed.

| Check | Evidence |
|---|---|
| `main == origin/main` clean | `git rev-parse HEAD` = `d4754737...` == `git rev-parse origin/main`; `git status` clean |
| Django `:8010/admin/` → 302 | `curl -s -o /dev/null -w '%{http_code}'` = `302` |
| Media-engine `:8001/health` OK, mocks all false | `{"status":"ok","openai_mock":false,"runway_mock":false,"image_gen_mock":false,"any_mock":false,"llm_provider":"openai","llm_model":"gpt-4o-mini"}` |
| Vite `:5174/` → 200 | `curl -s -o /dev/null -w '%{http_code}'` = `200` |
| Celery 1 node online | `celery -A character_os inspect ping` → `celery@Chriss-MacBook-Pro.local: OK` |
| 9 KDs still `is_active=True, deactivated_reason='', universe=None, spokespeople=∅` | ORM count query = `9`; per-row `deactivated_reason=''` for all 9 |
| Ruby Class C `8f825c98-…` unchanged | `is_active=True, deactivated_reason='', universe=1a0af807-…, m2m=0` |
| Ruby Class D `74e7f18f-…` unchanged | `is_active=True, deactivated_reason='', universe=1a0af807-…, m2m=1` |
| Migration `0006_session275_deactivated_reason` applied | `MigrationRecorder` last embeddings row = `0006_session275_deactivated_reason` |
| `Teammate` `pre_delete` + `post_delete` signal pair registered | `shell/apps/spokespeople/signals.py:115,157` (`@receiver(pre_delete, sender=Teammate)` + `@receiver(post_delete, sender=Teammate)`) |
| Ingestion revival gate active | `from apps.embeddings.ingestion import OrphanRevivalRejected` succeeds; raise site `shell/apps/embeddings/ingestion.py:150` |
| No mock / experiment env drift | `env \| grep -E "MOCK\|FORCE\|EXPERIMENT"` = empty; no `RUNWAY_FORCE_MOCK / OPENAI_MOCK / EMBEDDING_FORCE_MOCK` set in running procs |

Every §G / §J invariant in the SESSION 276 handoff still holds.

---

## §4. Track A — inspection of the 9 legacy KDs

### §4.1 Fresh DB dump (read-only)

Confirms SESSION 275 §2 + §12 baseline verbatim. Common shape:

- All 9: `workspace_id = 4ce5486d-35a4-4bee-8745-38004adb33bc` (`chriss-workspace`).
- All 9: `universe_id = NULL`, `spokespeople.count() = 0`, `is_active = True`, `deactivated_reason = ''`, `status = 'processed'`, `ingested_via = 'paste'`, `document_type ∈ {'text','markdown'}`, `created_by = chris@donkeybetz.com (id=883)`.
- All 9: `source_url = ''`, `source_metadata = {}` (empty JSON). No ingestion-side provenance beyond the content itself.

Full per-KD detail:

| # | UUID | Title | Created | Updated | Δ | Chunks | raw len | first-chunk sniff |
|---|---|---|---|---|---|---|---|---|
| 1 | `aa90d895-cac9-41d4-b505-f2b23ffd5241` | About Hearth & Hollow Books | 2026-07-24T00:15:50 | 2026-07-24T00:27:23 | 693s | 1 | 582 | *"Hearth & Hollow Books is an independent neighborhood bookstore…"* |
| 2 | `e37ea174-98e8-4588-a690-81f6e1bbfe4b` | How We Recommend Books | 2026-07-24T00:16:14 | 2026-07-24T00:27:23 | 669s | 1 | 506 | *"Every recommendation begins with the reader, not the bestseller list…"* |
| 3 | `b58efd31-d05c-4008-beac-3a75755e5c6b` | Children's Reading | 2026-07-24T00:16:43 | 2026-07-24T00:27:24 | 641s | 1 | 383 | *"Helping children discover a love of reading…"* |
| 4 | `7f41d8e3-9be0-4591-9648-8c901861628d` | Bookstore Events | 2026-07-24T00:17:03 | 2026-07-24T00:27:25 | 622s | 1 | 322 | *"Hearth & Hollow Books hosts regular community events…"* |
| 5 | `c408656d-191d-49be-a92d-8721aa294b58` | Supporting Local Authors | 2026-07-24T00:17:27 | 2026-07-24T00:27:25 | 598s | 1 | 351 | *"We proudly feature books written by local and regional authors…"* |
| 6 | `0088f31f-56fc-4e66-837a-f5391d6bbd94` | Helping Customers Find Their Next Read | 2026-07-24T00:17:53 | 2026-07-24T00:27:26 | 572s | 1 | 413 | *"The best recommendation isn't always the newest or most popular book…"* |
| 7 | `7ecde40b-6d72-45eb-b676-6feb260e2ff8` | Tulsi — Core Identity and Public Purpose | 2026-08-05T21:59:55 | 2026-08-05T22:00:00 | 4.5s | 3 | 2178 | *"# Tulsi — Core Identity and Public Purpose / ## About Character OS…"* |
| 8 | `8c6f0c14-b2c9-4161-b6b7-a17d3f9b4545` | TANK — AUTOMOTIVE FINANCING CONTENT KNOWLEDGE | 2026-08-16T17:04:59 | 2026-08-16T17:05:07 | 8.1s | 22 | 15898 | *"TANK — AUTOMOTIVE FINANCING CONTENT KNOWLEDGE / PURPOSE / Tank is an automotive financing spokesperson…"* |
| 9 | `90ad200c-5019-4036-82e9-a1ccc5cbce72` | Riggs | 2026-08-17T15:53:36 | 2026-08-17T15:53:38 | 2.1s | 1 | 33 | *"Just knows a lot about everything"* |

The `updated_at − created_at` gap on #1–#6 is a coherent 5-10 minute burst (all 6 created between 00:15:50 and 00:17:53, all updated within a ~3-second span at 00:27:23–00:27:26) — consistent with sequential paste-ingest followed by a single embedding pass ~10 min later.

#7 (Tulsi) sits at 4.5s. #8 (TANK) at 8.1s. #9 (Riggs) at 2.1s. Each is a "type-then-embed" tight loop.

### §4.2 Cross-model forensic evidence (SET_NULL fingerprints + surviving artifacts)

Per SESSION 275 §14 diagram, Teammate deletion is SET_NULL for `Composition.spokesperson`, `Asset.spokesperson`, `ConversationThread.spokesperson`, `Script.spokesperson`, `Asset.spokesperson`, `RealtimeSession.spokesperson`, `PersonalizedCampaign.spokesperson`, and `CharacterIdentity.teammate`. A workspace-scoped row that carries a character's name but has `spokesperson_id = None` (or `teammate_id = None`) is therefore a strong signal that a Teammate for that character once existed and was later deleted.

**CharacterIdentity in `chriss-workspace`, chronological:**

| created_at | name | teammate link | archived_at |
|---|---|---|---|
| 2026-08-16T15:59:23 | Mike | Mike (linked) | None |
| **2026-08-16T17:03:18** | **Tank** | **None** | **None** |
| 2026-08-16T17:19:05 | Repo Red | Repo Red (linked) | None |
| 2026-08-16T18:05:53 | Patch | Patch (linked) | None |
| 2026-08-16T18:57:43 | Rivet | Rivet (linked) | None |
| 2026-08-17T15:53:11 | Riggs | Riggs (linked) | None |

**Tank is the sole CharacterIdentity row in the workspace whose `teammate` FK is NULL.** Given the SET_NULL contract and that every other row is linked to a live Teammate, this is a **unique SET_NULL fingerprint**: a Tank `Teammate` row existed on 2026-08-16 (before or at `CharacterIdentity` creation at 17:03:18), and was later deleted. This is not inference; it is direct evidence of the fingerprint SESSION 275's signal was designed to prevent.

**Compositions with `spokesperson_id = None` in `chriss-workspace`:**

| created_at | name | matches Track A KD? |
|---|---|---|
| 2026-08-05T22:35:10 | `Complicated AI` | no |
| 2026-08-14T15:13:53 | `Talking-head — Gandry King of the Geese` | no |
| 2026-08-14T15:56:30 | `Testing talking heads vs Reels` | no |
| 2026-08-14T16:53:14 | `Talking-head — Tulsi` | **yes** (KD #7) |
| 2026-08-16T17:08:30 | `Tank's first video` | **yes** (KD #8) |

**Assets with `spokesperson_id = None` in `chriss-workspace`:**

| created_at | title | matches Track A KD? |
|---|---|---|
| 2026-08-14T16:53:35 | `Talking-head — Tulsi` | **yes** (KD #7) |
| 2026-08-16T17:10:50 | `Tank's first video — step 1/2 (generate_avatar_speech)` | **yes** (KD #8) |
| 2026-08-16T17:11:06 | `Tank's first video — step 2/2 (add_intro_outro)` | **yes** (KD #8) |

**Hearth & Hollow (#1–#6):** zero Composition, Asset, or CharacterIdentity row references *Hearth*, *Hollow*, or *bookstore*. No forensic SET_NULL fingerprint exists for a Hearth & Hollow Teammate.

**Riggs (#9):** Riggs teammate CURRENTLY EXISTS (`5731a73d`, `status=ready`, `created_at=2026-08-17T15:52:32`); its CharacterIdentity row (`2026-08-17T15:53:11`) has an intact `teammate` link. The Riggs KD was created at `2026-08-17T15:53:36` — 64 seconds AFTER the Riggs teammate row and 25 seconds AFTER its CharacterIdentity row. The KD content is a stub ("Just knows a lot about everything") and was ingested unattached (`spokespeople=∅`). This is **not** an orphan pattern — it is a live teammate + a stub knowledge doc that was ingested without an M2M attach.

### §4.3 Design-doc / knowledge-base references

Independent corroboration outside DB state:

- `docs/design/UNIVERSE_BOUNDARY_V1.md`: *"Automotive, Hearth & Hollow bookstore, plus Tulsi cohabit"* … *"Patch/Rivet dialogue synthesis can retrieve TANK, Tulsi, or Hearth & Hollow chunks"* … *"TANK (Motorcade), Tulsi (whichever), and Hearth & Hollow (Bookstore)"* — treats Tulsi and TANK as historical spokespeople; Hearth & Hollow described as a *bookstore* (business identity, not a character name).
- `docs/design/UNIVERSE_SCHEMA_V1.md`: *"Mike, Repo Red, Tulsi, and every historical…"* — Tulsi named as legacy Teammate.
- `docs/design/RELATIONSHIP_BOUNDARY_V1.md`: *"Legacy behavior (Mike-the-plumber, Repo Red, Tulsi)"* + *"Historical business spokespeople (Mike, Repo Red, Tulsi)"* — Tulsi consistently listed as historical Teammate.
- `docs/design/WORLD_ENTITY_BOUNDARY_V1.md`: *"Legacy pre-Universe rows exist? YES (Mike, Repo Red, Tulsi)"* — same.
- `docs/design/SESSION_274_UNIVERSE_SHARED_KNOWLEDGE_DOGFOOD.md:596`: **operator testimony** — *"Chris reports that the current Class A workspace-shared KDs in `chriss-workspace` (TANK, Hearth & Hollow set, Tulsi, Riggs) are knowledge left behind by DELETED characters, and that the current UI does not allow him to delete those orphaned KDs."* This is Chris's own recollection recorded before SESSION 275. Not an audit trail — operator memory is subject to correction — but a direct primary source stating the intent.
- `docs/design/CAPABILITY_INVENTORY_SESSION_261.md:458-462`: *"Tulsi (3 chunks), TANK (22), Riverstone (7), Hearth & Hollow (six 1-chunk docs), Surgo Automotive Mike KB (16), Surgo Financing (5) — all cohabit `chriss-workspace` with empty M2M; Patch/Rivet dialogue synthesis can (and does) retrieve from any of them if the topic embedding is close."* — audit as of SESSION 261 recorded the same 6-doc Hearth & Hollow set plus Tulsi + TANK as workspace-scoped-with-empty-M2M rows.

Neither Riverstone, Surgo Automotive Mike KB, nor Surgo Financing appear in the current 9-KD set — those are separate KDs (either since-deleted or attached to teammates). The 9 KDs SESSION 275 identified are exactly the residual subset that survived.

### §4.4 Per-KD classification (evidence-tiered)

Using this evidence hierarchy: PROVEN > STRONG > WEAK > INDETERMINATE.

| # | UUID | Fresh classification | Load-bearing evidence | Evidence *against* / weakening |
|---|---|---|---|---|
| 1 | `aa90d895` About Hearth & Hollow Books | **WEAK-INFERENCE — orphan OR intentional business canon** | Content is bookstore-first-party voice; SESSION 261 & SESSION 274 doc references; operator testimony (SESSION 274 §596); the 6-doc Hearth & Hollow burst has a shared authoring pattern | No CharacterIdentity, Composition, or Asset row bears the Hearth/Hollow name → no SET_NULL fingerprint. Hearth & Hollow could plausibly have been (a) a Teammate that produced no Composition before deletion, or (b) a workspace-level *business identity* that was never a Teammate at all |
| 2 | `e37ea174` How We Recommend Books | **WEAK-INFERENCE — same** | Same burst; created 24s after #1 | Same |
| 3 | `b58efd31` Children's Reading | **WEAK-INFERENCE — same** | Same burst; +29s after #2 | Same |
| 4 | `7f41d8e3` Bookstore Events | **WEAK-INFERENCE — same** | Same burst; +20s after #3 | Same |
| 5 | `c408656d` Supporting Local Authors | **WEAK-INFERENCE — same** | Same burst; +25s after #4 | Same |
| 6 | `0088f31f` Helping Customers Find Their Next Read | **WEAK-INFERENCE — same** | Same burst; +26s after #5 | Same |
| 7 | `7ecde40b` Tulsi | **STRONG-INFERENCE — formerly-character-specific orphan** | Composition + Asset both titled *"Talking-head — Tulsi"* with `spokesperson_id=None` (SET_NULL fingerprint); Tulsi named as historical Teammate in 4 design docs; content is Tulsi-first-person self-description; operator testimony | No CharacterIdentity row survived (unlike TANK) — makes the fingerprint slightly weaker than TANK. Could theoretically be a Composition/Asset whose spokesperson was manually cleared rather than deleted, but no product path currently allows manual clearing |
| 8 | `8c6f0c14` TANK | **PROVEN — formerly-character-specific orphan** | CharacterIdentity[Tank] with `teammate_id=None` is unique in the workspace (SET_NULL fingerprint); Composition `Tank's first video` + 2 Assets with `spokesperson_id=None`; TANK named in 3 design docs; content is character brief; operator testimony | None. The CharacterIdentity SET_NULL fingerprint alone is definitive |
| 9 | `90ad200c` Riggs | **PROVEN — NOT an orphan; unattached / never-attached KD** | Riggs Teammate `5731a73d` currently exists, `status=ready`; Riggs CharacterIdentity has intact `teammate` link; KD created 64s AFTER Teammate creation; content is a 33-char stub ("Just knows a lot about everything"); no Composition/Asset produced | None. This is a misconfigured / never-attached ingest, not an orphan |

**Distribution:** 1 PROVEN orphan (TANK), 1 STRONG-INFERENCE orphan (Tulsi), 1 PROVEN not-orphan (Riggs), 6 WEAK-INFERENCE (Hearth & Hollow burst).

### §4.5 Answer to Track A question

> Can any of the nine be safely classified from surviving evidence as intentionally workspace-shared, formerly character-specific/orphaned, simply unattached/misconfigured, or genuinely indeterminate?

- **PROVEN orphan (TANK #8):** yes — CharacterIdentity SET_NULL fingerprint is dispositive. Safe to remediate as "orphaned by past Teammate delete."
- **STRONG-INFERENCE orphan (Tulsi #7):** yes — combined Composition + Asset SET_NULL fingerprint + design-doc + operator testimony is sufficient to remediate as orphan **for Chris's own workspace under his signoff**. Would not survive a hypothetical adversarial audit against a stranger's workspace, but this is Chris's own data.
- **PROVEN not-orphan (Riggs #9):** yes — the Riggs Teammate exists. This is a misconfigured/unattached KD; the correct remediation is either attach it to Riggs or delete it. It is **not** an orphan case.
- **WEAK-INFERENCE (Hearth & Hollow #1–#6):** no. Two hypotheses fit the evidence equally well: (a) Hearth & Hollow was a Teammate that produced no Composition before deletion → orphan, OR (b) Hearth & Hollow was always intended as workspace-level *business canon* about the bookstore → intentional shared knowledge. Cannot distinguish from surviving evidence. Combined with operator testimony (SESSION 274 §596) they *lean* orphan, but that leaning is Chris's recall, not a fingerprint. **Indeterminate under a strict evidence bar; ORPHAN-BY-OPERATOR-TESTIMONY under Chris's signoff.**

> What evidence would be required before an operator could safely remediate an indeterminate row?

For the Hearth & Hollow set — either of these would resolve the indeterminacy:
1. A surviving Composition, Asset, CharacterIdentity, ConversationThread, or Message that references a "Hearth & Hollow" spokesperson with `spokesperson_id=None` (SET_NULL fingerprint). None exist in the current DB.
2. An audit log or event journal recording an M2M attach or a Teammate creation named "Hearth & Hollow". No such journal exists in the codebase.
3. **Operator recall + explicit signoff.** Documented in SESSION 274 §596 and now again here — Chris asserts these 6 KDs are orphan artifacts. Under Chris's signoff and applied to his own workspace, this is sufficient basis for remediation; but the general "operator makes an audience decision" workflow cannot itself infer it.

---

## §5. Track B — inspection of the current inactive-KD recovery surface

Every surface capable of revealing an inactive KD or flipping its `is_active` back to True.

### §5.1 SPA visibility of inactive KDs

- **Route `/workspace/knowledge`:** filters via `getKnowledgeDocuments(workspace_id, spokesperson_id?)` at `web/src/lib/api/knowledge.ts:112` → `GET /api/knowledge/?workspace=<uuid>`. Backend queryset (`shell/apps/embeddings/views.py:62-108`) hard-codes `is_active=True`. **Inactive KDs are invisible in the SPA list.**
- **Route `/workspace/knowledge/<id>`:** `getKnowledgeDocument(id)` at `web/src/lib/api/knowledge.ts:157` → `GET /api/knowledge/<id>/`. `get_object` uses the same queryset → **404 on any inactive KD** — no detail view.
- **No archived / "Show archived" toggle exists.** `grep -r 'include_inactive\|archived\|showArchived' web/src` returns zero SPA hits related to KD lifecycle. The only `is_active` reference in the SPA is the Zod type at `web/src/lib/api/knowledge.ts:69`.
- **Spokesperson detail Knowledge tab:** same viewset with `?spokesperson=<uuid>`; same `is_active=True` filter.
- **No badge or copy anywhere** discloses `deactivated_reason` to the operator. The serializer surfaces it read-only (`shell/apps/embeddings/serializers.py:123-127`), but no SPA route consumes the field.

### §5.2 Django admin (`/admin/embeddings/knowledgedocument/`)

- Registered at `shell/apps/embeddings/admin.py:22-40`.
- `list_display = ('title','workspace','document_type','ingested_via','status','is_active','created_at')` — shows `is_active` column.
- `list_filter = ('status','document_type','ingested_via','is_active')` — admin can filter on `is_active=False` and see inactive rows.
- `readonly_fields = ('id','content_hash','created_at','updated_at')` — **`is_active` and `deactivated_reason` are NOT readonly.** An admin can freely toggle `is_active=True` and clear `deactivated_reason` via the change form.
- **This is the ONE remaining path capable of reviving an `orphaned_by_teammate_delete` KD without an explicit audience decision.** Ingestion is gated; the DRF API is gated by the queryset filter; admin is not gated.

### §5.3 REST API surfaces (from `router.urls` enumeration)

Routes registered by `DefaultRouter` on `KnowledgeDocumentViewSet` at `shell/apps/embeddings/urls.py:16`:

| Route | Behavior on inactive KD |
|---|---|
| `GET /api/knowledge/` | queryset filters `is_active=True` → inactive KD absent from list |
| `POST /api/knowledge/` | ingestion path; `_persist` dedup revival is safe-gated (`OrphanRevivalRejected` at `shell/apps/embeddings/ingestion.py:150`) |
| `GET /api/knowledge/<id>/` | `get_object` filtered → **404** on inactive |
| `PATCH /api/knowledge/<id>/` | `get_object` filtered → **404** on inactive. NB: the serializer classifies `is_active` as R/W (`fields=[…,"is_active",…]`; not in `read_only_fields`), so a PATCH `{is_active: true}` *would* revive — but the queryset gate means the row cannot be reached to PATCH it |
| `DELETE /api/knowledge/<id>/` | `get_object` filtered → **404** on already-inactive; no double-archive path |
| `POST /api/knowledge/<id>/attach/` | `get_object` filtered → **404** (SESSION 275 §30) |
| `POST /api/knowledge/<id>/detach/` | `get_object` filtered → **404** |
| `POST /api/knowledge/<id>/compositions/` | `get_object` filtered → **404** |
| `POST /api/knowledge/search/` | Serper-only; no KD-lifecycle interaction |
| `POST /api/knowledge/preview/` | uses `retrieve_for_teammate` which filters `document__is_active=True` (`shell/apps/embeddings/retrieval.py:155,196,364`) → inactive KDs not surfaced |

**Verdict:** the DRF API surface **is** sealed against non-ingestion revival — by the `is_active=True` queryset filter, not by a serializer field lock. This is a *coincidental* seal, not an explicit invariant. If a future refactor removed the queryset filter (e.g. to add "Show archived" support) without also read-only-locking `is_active` or introducing a `POST /restore` endpoint with the safe-audience gate, the audience-broadening invariant would silently re-open.

### §5.4 Reassign / audience-change primitives on active KDs

Present today, active-only:

- `PATCH /api/knowledge/<id>/` with `{spokesperson_ids: [...]}` → serializer `update()` at `shell/apps/embeddings/serializers.py:499-500` calls `instance.spokespeople.set(...)`. Active KD only.
- `POST /api/knowledge/<id>/attach/` `{spokesperson_id: <uuid>}` — active KD only.
- `POST /api/knowledge/<id>/detach/` `{spokesperson_id: <uuid>}` — active KD only.
- `PATCH /api/knowledge/<id>/` with `{universe: <uuid|null>}` → serializer `update()` at `shell/apps/embeddings/serializers.py:425-445` with universe-reassign M2M-orphan preflight. Active KD only.
- Cross-workspace spokesperson attach rejected by `apps.embeddings.signals` `m2m_changed` guard (`shell/apps/embeddings/views.py:186-188`).
- Cross-Universe spokesperson attach rejected by serializer `validate()` at `shell/apps/embeddings/serializers.py:212-245`.

### §5.5 Every path capable of setting `is_active=True`

Complete enumeration (`grep is_active` under `apps/embeddings/`):

| Path | File:Line | Gated? |
|---|---|---|
| Ingestion dedup revival | `apps/embeddings/ingestion.py:164` | **YES** — `OrphanRevivalRejected` at `:150` if reason is `ORPHANED_BY_TEAMMATE_DELETE` and no spokespeople supplied |
| DRF `PATCH` on `is_active` field | Would be reachable via serializer field, but `get_queryset` filter at `views.py:70` returns queryset with `is_active=True` → `get_object` 404s | **YES (coincidental)** — via queryset filter, not serializer read-only |
| DRF `attach` / `detach` | `views.py:143-159` | **YES (coincidental)** — via same queryset filter |
| Django admin change form | `admin.py:22-40` | **NO** — `is_active` not in `readonly_fields`; admin can toggle without any signal-side check |
| Direct ORM / management command / `manage.py shell` | Unrestricted | **NO** — always available to any code with DB access. Not the operator surface |

**Only ingestion enforces the SESSION 275 §46 load-bearing "explicit safe audience" requirement.** Every other operator-adjacent revival path is either coincidentally sealed (DRF queryset filter) or unsealed (Django admin).

### §5.6 Answer to Track B question

> Determine exactly what an ordinary operator can and cannot do today with a KD archived as `deactivated_reason='orphaned_by_teammate_delete'`.

**Can:**
- Nothing in the SPA. Zero visibility, zero action.
- Nothing via the DRF API. Every route 404s on inactive KDs.
- If the operator has Django admin access (Chris does): view, filter to `is_active=False`, edit `is_active` and `deactivated_reason` freely — including the exact bare `is_active=False → True` flip SESSION 275 §46 declares disallowed.
- Re-ingest the same content via SPA → paste → knowledge modal. If they include a spokesperson selection, revival succeeds and `deactivated_reason` clears. If they don't, `OrphanRevivalRejected` → HTTP 400 with a copy that instructs them to select a character.

**Cannot:**
- See that any archived KDs exist.
- Discover *which* KDs were archived by which teammate delete.
- Reassign to a new character in one gesture (must re-ingest identical content).
- Reassign to a Universe without also picking spokespeople.
- Learn `deactivated_reason` for a specific KD without shell/admin access.
- Restore *without* re-ingesting the exact original content.

> Is existing state + existing APIs sufficient for a small safe recovery workflow?

- **State:** yes. `deactivated_reason` distinguishes the two archive causes. `spokespeople` M2M can hold the explicit audience choice. `universe` FK can hold the Universe promotion choice. No new column needed for a v1 recovery workflow.
- **APIs:** *almost*. Every existing endpoint gates on `is_active=True`. A recovery workflow needs *either* (a) an `include_inactive=true` query param on `GET /api/knowledge/` + explicit revival endpoint, or (b) a dedicated `POST /api/knowledge/<id>/restore/` that accepts a required audience payload and enforces the same safe-audience contract the ingestion gate enforces. Both approaches can be built on existing primitives with no new column and no retrieval change.

---

## §6. Product-model comparison

### Q1. Do legacy remediation and future orphan recovery require the same operator decision model, or do they merely share an audience-selection primitive?

**They share the audience-selection primitive but require different upstream flows.** The audience decision itself — *"attach to character(s) X / promote to Universe U / promote to workspace / keep archived"* — is identical for both. What differs is:

- **Future orphan:** `deactivated_reason='orphaned_by_teammate_delete'` is proof the KD *was* character-specific and the character *was* deleted. The system knows *why* it needs a new audience. The operator's task is only the audience choice.
- **Legacy KD:** the system knows *only* that the KD is empty-M2M. It cannot tell orphan from Class A canon from misconfigured-unattached. The operator's task is a **classification** first ("is this orphan? intentional canon? misconfigured?"), then an audience choice.

The primitive is shared; the *decision context* is different. A single recovery UI can serve both only if it surfaces the classification distinction clearly enough that an operator does not treat legacy indeterminate rows as if they were system-attested orphans.

### Q2. What information is known for a future system-created orphan that is absent for ambiguous legacy data?

Four things the system will know for a future orphan that the 9 legacy rows lack:

1. **`deactivated_reason = 'orphaned_by_teammate_delete'`** — proof of causal event.
2. **Which teammate was deleted** — the `pre_delete` snapshot logs the teammate name/id at signal time (currently in-memory only, not persisted; but retrievable from an audit journal if added).
3. **The historical M2M** — implicit in the snapshot: this teammate was in the M2M immediately before delete.
4. **Timestamp of archive** — `updated_at` when `is_active` flipped.

None of this exists for the 9 legacy rows. The archives predate the SESSION 275 mechanism.

### Q3. Is `archived / inactive` currently functioning as lifecycle state, audience state, both, or neither cleanly?

**Both, and not cleanly.**

- Lifecycle state: `is_active=False` means "not retrievable, not visible in the operator list, chunks preserved for admin audit."
- Audience state: `is_active=False` on an ex-orphan KD ALSO functionally means "no audience assigned; do not re-broadcast without an explicit new audience." The SESSION 275 revival gate encodes this — but the encoding lives in `ingestion._persist`, not in the model. From the outside, `is_active=False` looks like a pure lifecycle bit; SESSION 275 loaded it with additional audience semantics via a companion field (`deactivated_reason`) rather than by giving audience its own column.

`deactivated_reason` is the small step toward separating the two, but only partially — it discriminates *why* the row is inactive, not *what audience decision is pending*.

### Q4. Can an inactive KD retain a meaningful intended audience under the current model?

**No.** The two paths that set `is_active=False` both leave the M2M in whatever state deletion produced:

- `operator_delete`: M2M preserved from before delete (untouched). But the KD is now inactive so retrieval ignores it.
- `orphaned_by_teammate_delete`: the last spokesperson was removed by CASCADE, so M2M is empty. No positive record of intended audience remains.

Neither case carries a first-class "intended audience" field. An inactive KD's "audience" is either whatever the M2M happened to be (potentially empty; potentially stale) or nothing at all. There is no `intended_universe` / `intended_spokespeople` / `pending_audience_decision` state today.

### Q5. Is existing state + existing APIs sufficient for a small safe recovery workflow?

**Yes for state; almost yes for APIs.** See §5.6. No schema change is strictly required for a v1 recovery. `deactivated_reason` is the only new column SESSION 275 added, and it already carries the archive-cause distinction. A recovery workflow needs (a) list visibility for inactive KDs (either query param or dedicated endpoint), (b) a restore endpoint that requires a non-empty audience payload for `ORPHANED_BY_TEAMMATE_DELETE` (same contract as `OrphanRevivalRejected`), and (c) an admin-form guard that mirrors the same contract when admins toggle `is_active` directly.

### Q6. What concrete evidence, if any, suggests an explicit `KnowledgeAudience` state/model is necessary rather than merely cleaner architecture?

Three pieces of evidence point at *cleaner*, not *necessary*:

1. The current model **works** as-is with the SESSION 275 signal + revival gate. No production bug results from empty-M2M-as-broadcast under the current invariants.
2. The 6 Hearth & Hollow rows would remain indeterminate under a `KnowledgeAudience` model too, because a model-level "audience" field does not synthesize evidence that no longer exists.
3. The revival gate proves the audience-decision-at-boundary approach is enforceable without a schema change.

One piece of evidence would push toward *necessary*:

- If we discover a **third** archive cause (e.g. Universe delete, workspace hand-off, character merge/rename) that has different revival semantics than the two we have today, the pairwise `deactivated_reason` discrimination will start to sprawl. If more than 2-3 reasons accumulate, a first-class `KnowledgeAudience` model becomes clearly right instead of merely cleaner.

Not observed today. Option C (§36 in SESSION 275 audit) remains the right long-term direction; the evidence today does not force it.

### Q7. Could the nine historical rows be handled safely without forcing them through the future-orphan workflow?

**Yes.** They pre-date the SESSION 275 mechanism and no `deactivated_reason='orphaned_by_teammate_delete'` will ever be stamped on them by the signal (the signal only fires on live Teammate deletes; the historical Teammates are gone). They are `is_active=True, deactivated_reason=''` and stay that way unless explicitly touched.

Three separable safe-remediation paths exist even without any new UI:

1. **Delete them** via the existing SPA delete button (`web/src/routes/workspace/knowledge.tsx:737-747`, live since `dd5bf37` 2026-08-17). This stamps `deactivated_reason='operator_delete'`. Safe. Chris can do this today.
2. **Attach them to specific characters** via existing `attach` endpoint or `PATCH spokesperson_ids`. Narrows audience explicitly. Safe. Chris can do this today.
3. **Promote them to a Universe** via existing `PATCH universe=<uuid>` on the serializer. Bounds audience to Universe members. Safe. Chris can do this today.

The 9 legacy rows do **not** need to be forced through a future-orphan workflow. They need an operator classification decision that only Chris can make (per §4.4 §4.5). The primitives to act on that decision already exist.

### Q8. What must an operator be shown before making a safe audience decision?

Minimum information set (per KD):

1. **Title + first-chunk sniff.** So the operator can recognize the content.
2. **Timestamp.** So the operator can reason about *when* it was ingested and correlate with what they were doing then.
3. **`deactivated_reason` (if archived).** So the operator knows *whether* the system attests this was an orphan or an operator delete or (legacy) neither.
4. **The teammate that was deleted (if reason is orphan).** So the operator knows *whose* knowledge this was. Requires either (a) capturing the teammate name in the archive signal, or (b) an audit journal — neither exists today.
5. **The current M2M state.** So the operator sees whether any surviving relations remain.
6. **The Universe (if any).** So the operator sees the current scope.
7. **Compositions that already consumed this KD's chunks.** So the operator sees the provenance impact of any decision. This is already computable via `GET /api/knowledge/<id>/compositions/`.
8. **The audience-decision affordances.** *"Attach to character(s) X / promote to Universe U / keep archived / delete permanently."*

Points 1–3, 5–7 exist in the model today. Point 4 does not — the SESSION 275 `pre_delete` snapshot is in-memory only. Point 8 is a UI concern.

---

## §7. Prediction vs. evidence

| Prediction (§2) | Evidence |
|---|---|
| Track A: subset classifiable, subset indeterminate | Confirmed. 1 PROVEN orphan (TANK), 1 STRONG orphan (Tulsi), 1 PROVEN not-orphan (Riggs), 6 WEAK / indeterminate (Hearth & Hollow) |
| Track B: SESSION 275 signal + revival gate seal orphan-archive; SPA gap remains | Confirmed. Ingestion revival is safe-gated. SPA has zero visibility |
| Track B: DRF API sealed by `is_active=True` queryset filter | Confirmed — but the seal is *coincidental* (queryset filter, not serializer read-only or endpoint invariant). Django admin remains an unguarded revival path |

## §8. Unresolved questions

1. **Hearth & Hollow (KDs #1–#6): true classification.** Cannot be resolved from surviving evidence alone. Depends on Chris's product decision: treat as orphan (delete) or as intentional business canon (attach to a workspace-level "Hearth & Hollow" concept, if such a concept ever gets first-class representation).
2. **Should the SESSION 275 `pre_delete` snapshot persist a durable record?** Currently in-memory only. If yes, that's a small addition (a `KnowledgeDocumentArchiveLog` model with `kd_id`, `teammate_id`, `teammate_name`, `archived_at`) that would enable operator-visible "archived because *teammate X* was deleted" copy in any future recovery UI. Not implemented; not authorized.
3. **Should Django admin enforce the safe-audience contract?** Admin bypasses the ingestion gate. A `KnowledgeDocumentAdmin.save_model` override could refuse `is_active=False → True` transitions on `ORPHANED_BY_TEAMMATE_DELETE` rows without an accompanying non-empty M2M or a Universe change. Not implemented; not authorized.
4. **Bundle vs split slice.** Does Chris want legacy remediation (Question A) and recovery UX (Question B) as (a) one bundled slice, (b) two separate slices where one blocks the other, or (c) two independent slices? This is the scoping question in SESSION 276 handoff §E step 4. **Not answered by evidence — a Chris product decision.**
5. **Riggs KD.** It's not an orphan and it's not an intentional canon — it's a stub. Should the recovery workflow have a "misconfigured / never-attached" concept, or is that class of row always handled by *attach* / *delete* alone?

## §9. Recommendation

**Do not implement anything in SESSION 276 Slice 1.** This slice's job was audit + evidence gathering; that job is complete. The audit provides enough evidence to inform Chris's scoping decision but does not itself commit direction.

Two directional options are *supported by the evidence* but should NOT be taken as recommendations until Chris chooses:

- **Direction 1 — remediate legacy first (n=1 slice).** Small: Chris manually classifies each of the 9 KDs (§4.4 gives him the evidence to do this in ~5 minutes) and uses the existing SPA delete / attach / universe-PATCH primitives to remediate. No code change. Removes the debt entirely; leaves recovery UX for later. Blocks nothing.
- **Direction 2 — recovery UX first (n=2 slices).** Slightly larger: Slice A ships archive-list-visibility (`include_inactive=true` query param) + a `POST /api/knowledge/<id>/restore/` endpoint with the safe-audience payload contract + admin-form guard. Slice B ships the SPA "Show archived / Restore" UI. Legacy remediation then falls out for free (Chris uses the same recovery UI on the 9 rows).

Direction 1 clears technical debt today with no code change. Direction 2 builds the reusable recovery surface but leaves legacy debt in place until the surface ships. They are not exclusive — Direction 1 could ship immediately and Direction 2 later. Chris's choice.

## §10. Explicit decision gate

**STOP.** SESSION 276 Slice 1 is complete. This document does not authorize any code, migration, DB, admin, or SPA change.

Before SESSION 276 Slice 2 begins, Chris must decide:

1. Bundle vs split (SESSION 276 handoff §E step 4).
2. Direction 1 vs Direction 2 vs both (§9).
3. Whether to persist the SESSION 275 archive snapshot to enable "archived by *X*" copy (§8 point 2).
4. Whether to close the Django admin bypass (§8 point 3).

Chris's answers determine Slice 2 scope. Slice 2 must open with a design/plan section, not implementation — same pattern as SESSION 275 §21-§38.

## §11. Smallest falsifiable next questions

Not for this session. Formulated so that Slice 2 can pick a starting shape without re-audit:

- **Q-276-1.** *If Chris classifies each of the 9 KDs using §4.4 as evidence and uses only existing primitives (delete, attach, universe-PATCH), does the debt clear cleanly with zero code change?* Falsifiable by trying it on 1 KD (e.g. TANK — the PROVEN orphan is the safest first move).
- **Q-276-2.** *Would a Django-admin `save_model` guard refusing `is_active=False → True` on `ORPHANED_BY_TEAMMATE_DELETE` rows without a non-empty M2M or Universe reassignment break any legitimate admin workflow?* Falsifiable by test: does any current test or admin action rely on a bare admin revival of an orphan-archived KD? (SESSION 275 §51 says "Admin can still hard-set `is_active=True`" — so at minimum any existing test that does this would need updating.)
- **Q-276-3.** *Does the SESSION 275 in-memory `pre_delete` snapshot contain enough for a persistent audit journal, or would we need to add fields?* Falsifiable by reading `shell/apps/spokespeople/signals.py:115-190` and enumerating what's captured.
- **Q-276-4.** *Would surfacing `deactivated_reason` in the SPA (badge on archived-list rows) require any backend change, or can it be pure frontend + existing serializer field?* Falsifiable by inspecting the current serializer response — `deactivated_reason` is already present (`serializers.py:127`) but a query param + relaxed queryset are needed to see inactive rows.

Each is a ½-slice worth of falsifiable work.

## §12. SESSION 276 Slice 1 checklist

- [x] Verify §J baseline invariants — §3
- [x] Confirm 9 KDs still meet §G invariants — §3
- [x] Confirm Ruby Class C + Class D unchanged — §3
- [x] Confirm `0006_session275_deactivated_reason` applied — §3
- [x] Confirm `Teammate` `pre_delete` + `post_delete` signal pair registered — §3
- [x] Confirm ingestion revival gate still importable — §3 (raise site unchanged; not exercised via test in this slice)
- [x] Read SESSION 275 §12, §27, §30, §46, §47, §61 — task #2
- [x] Track A — enumerate every observable field on the 9 KDs — §4.1
- [x] Track A — cross-model forensic evidence (SET_NULL fingerprints, surviving Composition/Asset/CharacterIdentity) — §4.2
- [x] Track A — design-doc + operator-testimony corroboration — §4.3
- [x] Track A — per-KD evidence-tiered classification — §4.4
- [x] Track A — answer the classification and evidence-required questions — §4.5
- [x] Track B — SPA visibility inventory — §5.1
- [x] Track B — Django admin inventory — §5.2
- [x] Track B — every DRF route × inactive-KD behavior — §5.3
- [x] Track B — reassign / audience-change primitive inventory — §5.4
- [x] Track B — every `is_active=True` mutation path — §5.5
- [x] Track B — answer what operator can / cannot do + primitive-sufficiency — §5.6
- [x] Product-model comparison — §6 Q1-Q8
- [x] Prediction vs. evidence — §7
- [x] Unresolved questions — §8
- [x] Recommendation — §9
- [x] Explicit decision gate — §10
- [x] Smallest falsifiable next questions — §11
- [x] Zero KD rows mutated; zero migrations run; zero provider spend; working tree clean at end of slice
- [ ] Chris review + Slice 2 scoping decision (§10)

---

**End of SESSION 276 Slice 1 read-only audit. STOP before implementation. Awaiting Chris's scoping decision (§10).**

---

# SESSION 276 — Slice 2 read-only audit: provenance requirement + revival invariant boundary

**Status.** READ-ONLY orient / audit / product-semantics investigation. Continued from Slice 1. No code, migration, DB row, admin, SPA, or provider behavior modified during this slice.

**Slice 2 baseline commit.** `d4754737d1d66bbae9fa261308ae36d93ff1769d` (unchanged from Slice 1 close). 9 KDs still `is_active=True, deactivated_reason=''`; Ruby Class C / Class D unchanged; migration `0006` applied; signal pair and revival gate registered — verified in Slice 1 §3 and revalidated after Slice 2 file appends.

**Load-bearing constraint carried forward from SESSION 275 §46 + Slice 1 §5.6:** any recovery flow that flips `is_active=False → True` on an `ORPHANED_BY_TEAMMATE_DELETE` KD must require an explicit safe-audience decision. A bare flip is disallowed.

**Additional invariant carried forward from SESSION 275 §23:** *"A removal or deletion action must never broaden the audience of surviving knowledge unless the operator explicitly chooses that broader audience."* Slice 2 restates the recovery corollary: *"Reactivation must never implicitly broaden audience."*

Legacy remediation and future orphan recovery remain **separate upstream flows** that may share an audience-selection primitive but are not the same decision model (Slice 1 §6 Q1). Slice 2 does not remediate the 9 legacy KDs and does not convert operator recollection (SESSION 274 §596) into fabricated system provenance.

---

## §13. Slice 2 questions

### §13.A — Provenance requirement

> What is the minimum historical audience/provenance Character OS must *durably* preserve when knowledge becomes orphaned so that a future ordinary operator can understand what happened and make a safe explicit recovery decision?

Investigated *without* pre-committing to a storage mechanism. Storage-shape follows requirement.

### §13.B — Revival invariant boundary

> What is the narrowest authoritative enforcement boundary that can guarantee an orphaned KD can never become actively retrievable with an implicitly broadened audience, regardless of whether the mutation originates from ingestion, DRF, Django admin, future SPA recovery, or another normal application path?

Investigated *without* implementing the answer. Slice 2 also verifies that any candidate enforcement location does not accidentally prohibit legitimate Class A / Class C intentional empty-M2M shared canon.

## §14. Predictions / hypotheses before evidence

- **§13.A prediction.** The load-bearing minimum provenance is the *identity* (name; possibly id) of the deleted teammate whose removal orphaned the KD. Everything else — universe, workspace, prior full M2M history, actor user id — is either already available on surviving rows or is nice-to-have context. Deleted-teammate-name is the largest single provenance jump.
- **§13.B prediction.** Both the DRF queryset seal (Slice 1 §5.3) and the ingestion revival gate (`shell/apps/embeddings/ingestion.py:150`) enforce *different* boundary invariants that happen to combine to seal a narrow case. Django admin and any future `KnowledgeDocument.objects.filter(...).update(is_active=True)` bypass both. Expected outcome: the narrowest sufficient enforcement is a *composite* — a model-level transitional check (catches admin form + full_clean + serializer.save + model.save) plus a DB CHECK constraint (catches `.update()` and raw SQL). Neither alone is sufficient; each alone has a documented bypass. This mirrors the SESSION 275 §57 finding that a single `pre_delete` design was falsified by bulk-delete test 9.
- **Adversarial prediction.** Any candidate enforcement that reads "reject `is_active=True` when spokespeople M2M is empty" will accidentally prohibit Class A / Class C canon (which is legitimately `is_active=True, spokespeople=∅`). The correct rule shape must be a *transitional* invariant keyed on `deactivated_reason`, not a *steady-state* invariant on M2M alone.

## §15. Exact current deletion lifecycle (SESSION 275 mechanism)

Traced from source. All line references are to `main == 45e82f5` == `d4754737` (Slice 2 baseline; no relevant file changed since Slice 3 landed).

### §15.1 The two Teammate lifecycle signal handlers

**Handler A — `_stash_kd_membership_for_orphan_check`** (`shell/apps/spokespeople/signals.py:115-154`):

- Receiver: `@receiver(pre_delete, sender=Teammate)`.
- Fires: once per doomed Teammate row, before Django's `Collector` emits DELETE SQL for that row. Fires for both `instance.delete()` and `QuerySet.delete()` (SESSION 275 §42, §49; test 9 confirms).
- Reads: `KnowledgeDocumentSpokesperson.objects.filter(teammate=instance).values_list("knowledgedocument_id", flat=True)`.
- Writes: `setattr(instance, "_session275_orphan_candidate_kd_ids", kd_ids)` — **in-memory only**. The Teammate row is about to be deleted from the DB; the Python instance still lives during signal dispatch.
- Persists to DB: **nothing**.

**Handler B — `_archive_orphaned_kds_on_teammate_delete`** (`shell/apps/spokespeople/signals.py:157-206`):

- Receiver: `@receiver(post_delete, sender=Teammate)`.
- Fires: once per doomed Teammate row, after Django's Collector has emitted DELETE SQL for that row *and* cascaded through-row deletions.
- Reads: `getattr(instance, "_session275_orphan_candidate_kd_ids", None)` from the stash, then `KnowledgeDocument.objects.filter(pk__in=kd_ids, is_active=True).annotate(sp_count=Count("spokespeople")).filter(sp_count=0).values_list("pk", flat=True)`.
- Writes: `KnowledgeDocument.objects.filter(pk__in=orphan_ids).update(is_active=False, deactivated_reason=DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE, updated_at=timezone.now())`.
- Also writes: **one `logger.info` line** — `"session-275: teammate=%s archived %d orphan KD(s): %s"` (`signals.py:201-206`) — which reaches whatever log backend Django is configured with. **This log is the only surviving record of the deleted teammate's PK relative to the archived KD.** It is not a persistent database row; it disappears when logs are rotated.

### §15.2 Information timeline for a single Teammate delete

Ordered stages. Each stage lists what is knowable at that moment and what has already disappeared.

| Stage | Available (in-memory) | Available (DB) | Permanently lost after commit |
|---|---|---|---|
| **T-1: just before `.delete()` call** | Teammate row loaded → `id, name, universe_id, workspace_id, personality, business_brief, status, created_at`. KD-side M2M rows loadable via query. | All Teammate columns; all KDSpokesperson through-rows; all KD columns; all Composition/Asset/etc. FKs to this Teammate. | — |
| **T0: `pre_delete` fires** | Everything from T-1 still present. Signal captures `kd_ids` list and stashes it on the instance attribute `_session275_orphan_candidate_kd_ids`. No other snapshot is taken. | Same as T-1. | — |
| **T+1: Django Collector emits DELETE for Teammate row + CASCADE for through-rows + SET_NULL for Composition/Asset/Script/Thread/RealtimeSession/CharacterIdentity/PersonalizedCampaign FKs** | Teammate Python instance still holds the pre-delete field values (Django does not zero them out). Stash attribute persists on the Python object. | Teammate row: **gone**. KDSpokesperson rows referencing this teammate: **gone** (CASCADE). Composition.spokesperson: **NULL** (SET_NULL). Asset.spokesperson: **NULL**. etc. KD.is_active still True. | Nothing lost *yet* — the Python instance still holds T-1 data. |
| **T+2: `post_delete` fires** | Handler reads stash from Python instance. Handler computes orphan_ids by querying live DB (KDs whose `pk in kd_ids AND is_active=True AND sp_count=0`). Handler bulk-updates KDs. Handler emits `logger.info` line naming `instance.pk`. | Same as T+1, plus: KD rows for orphaned ids now `is_active=False, deactivated_reason='orphaned_by_teammate_delete', updated_at=now`. | — |
| **T+3: transaction commits (Collector's `mark_for_rollback_on_error` boundary exited without raise)** | Python instance may be discarded. Stash attribute survives only as long as any live Python reference. | Post-commit state locked in. | Everything about the deleted Teammate: `id, name, universe_id, workspace_id, personality, business_brief`. The prior M2M relationship (Teammate ↔ KD). The pre_delete snapshot list. **Any operator context about who was deleted, from where, or into what audience the surviving KD was originally scoped.** |

### §15.3 What durably survives about a given orphan-archived KD

Post-commit, forever, the operator can retrieve from the DB:

- `KnowledgeDocument.id, title, workspace_id, universe_id (unchanged), raw_content, processed_content, content_hash, source_url, source_metadata, ingested_via, created_by_id (if user still exists), created_at, updated_at` (= archive timestamp), `is_active=False`, `deactivated_reason='orphaned_by_teammate_delete'`.
- `KnowledgeChunk` rows (chunks + embeddings intact — SESSION 275 §31, §48).
- Any `Composition` that consumed this KD's chunks continues to resolve them via `resolve_chunk_ids_to_docs` (`shell/apps/embeddings/retrieval.py:63-118`; SESSION 275 §31).

Post-commit, forever, the operator **cannot** retrieve from the DB:

- The deleted Teammate's name (Tulsi? TANK? Riggs? Ruby?).
- The deleted Teammate's UUID.
- The deleted Teammate's universe scope at deletion time.
- Whether the archived KD had *other* spokespeople who were also deleted earlier (Case 3 below).
- Whether the archived KD was ever character-shared vs character-specific vs Universe-scoped historically.
- Which operator initiated the delete (delete-signal path does not surface `request.user`).
- The pre-delete M2M snapshot.

## §16. Case-by-case information-loss analysis

Four cases named in the task. Traced against the §15 lifecycle. No characters mutated; conceptual specimens only.

### §16.Case-1 — KD initially `{Ruby}`, Ruby deleted

- **T-1:** KD active, spokespeople=`{Ruby}`, universe=U (say Ruby's universe).
- **T0 pre_delete on Ruby:** stash `kd_ids=[KD.id]` on Ruby instance.
- **T+1 CASCADE:** KDSpokesperson(Ruby, KD) deleted. KD.spokespeople now `∅`. Ruby row gone.
- **T+2 post_delete:** KD is `pk∈kd_ids ∧ active ∧ sp_count=0` → orphan. Bulk-update KD: `is_active=False`, `deactivated_reason=ORPHANED_BY_TEAMMATE_DELETE`, `updated_at=now`. Log line names `instance.pk` (Ruby's now-deleted UUID).
- **T+3 commit:** KD archived. Ruby row unrecoverable.
- **What survives:** KD (inactive), reason attests archive-by-teammate-delete. Log line names Ruby's PK (rotates).
- **What is permanently lost:** Ruby's name/id (from DB), the M2M relationship, the fact that this was Ruby's private knowledge.
- **Safe operator inference AFTERWARDS:** "This KD was orphaned by *some* teammate delete." "Its content sniff and title may hint at the deleted teammate." "It is safe to leave archived or reassign to a chosen character." **Not safe to infer** *which specific teammate was deleted* — that requires provenance that no longer exists.
- **KD becomes inactive:** yes.

### §16.Case-2 — KD initially `{Ruby, Mason}`, Ruby deleted

- **T-1:** KD active, spokespeople=`{Ruby, Mason}`.
- **T0 pre_delete on Ruby:** stash `kd_ids=[KD.id]`.
- **T+1 CASCADE:** KDSpokesperson(Ruby, KD) deleted. KDSpokesperson(Mason, KD) *survives* — different through-row, unrelated FK. KD.spokespeople now `{Mason}`.
- **T+2 post_delete:** KD is `pk∈kd_ids ∧ active`, but `sp_count=1 (Mason)`. Does **not** match `sp_count=0`. No archive. Handler logs nothing about this KD.
- **T+3 commit:** KD active, spokespeople=`{Mason}`. Ruby row gone.
- **What survives:** KD (active with Mason), Mason relationship, all chunks, retrieval works for Mason.
- **What is permanently lost:** the fact that Ruby ever was a spokesperson on this KD. The Ruby↔KD through-row is CASCADE-deleted; no history remains.
- **Safe operator inference AFTERWARDS:** "This KD is Mason-specific." (Mason is the only surviving relation; the *current* audience is correct.) **Not safe to infer** that this used to be Ruby-shared — that history is unrecoverable. But this is a *narrowing* case, not a broadening case; SESSION 275's invariant is not violated.
- **KD becomes inactive:** no.

### §16.Case-3 — KD initially `{Ruby, Mason}`; Ruby deleted; Mason deleted later

- **After Ruby delete (Case 2 outcome):** KD active, spokespeople=`{Mason}`. Ruby row gone. Prior Ruby↔KD through-row gone.
- **T-1 (Mason delete arrives, days/weeks later):** KD active, spokespeople=`{Mason}`. Nothing in the DB records that Ruby ever was in the M2M.
- **T0 pre_delete on Mason:** stash `kd_ids=[KD.id]` on Mason instance.
- **T+1 CASCADE:** KDSpokesperson(Mason, KD) deleted. KD.spokespeople now `∅`.
- **T+2 post_delete:** KD `pk∈kd_ids ∧ active ∧ sp_count=0` → orphan. Bulk-update. Log line names Mason's PK.
- **T+3 commit:** KD archived, reason=ORPHANED_BY_TEAMMATE_DELETE.
- **What survives:** KD (inactive), reason.
- **What is permanently lost:** BOTH Ruby's identity AND Mason's identity. And, critically, the *history* that this KD was ever shared between Ruby and Mason. From the surviving evidence, this looks identical to Case 1 (a KD that was always solo).
- **Safe operator inference AFTERWARDS:** "Orphaned KD." **Not safe to infer** *which* teammate was the final one, and completely unrecoverable that it was previously shared.
- **KD becomes inactive:** yes.

### §16.Case-4 — Intentionally shared empty-M2M KD; unrelated character X deleted

- **T-1:** KD active, spokespeople=`∅` (born-empty; Class A workspace canon or Class C Universe canon).
- **T0 pre_delete on X:** stash `kd_ids = [KDs where X was in M2M]`. This KD is **not** in the snapshot (X was never in its M2M — SESSION 275 §27 load-bearing).
- **T+1 CASCADE:** X's other relations processed. This KD untouched.
- **T+2 post_delete:** handler iterates `kd_ids` — this KD is absent from the list. No archive.
- **T+3 commit:** KD still active, empty-M2M, unchanged. Canon preserved by construction (SESSION 275 §27).
- **What survives:** everything, unchanged.
- **What is permanently lost:** nothing on this KD's side. (X's own row is gone.)
- **Safe operator inference AFTERWARDS:** "This KD is intentional canon." **Safe inference** because `deactivated_reason` stays `''` (canon and orphan are now distinguishable by reason field on the surviving KD).
- **KD becomes inactive:** no.

### §16.5 Case-summary information matrix

| Case | Archive? | Deleted-teammate-name recoverable post-commit? | Prior-audience-history recoverable? | Distinguishable from other cases post-facto? |
|---|---|---|---|---|
| 1 (solo delete) | yes | **no** (only in log line; rotates) | n/a (was solo) | reason=orphan; content-sniff may hint; no ID trail |
| 2 (narrowing delete) | no | **no** (Ruby's identity gone from DB) | **no** (Ruby↔KD through-row CASCADE-deleted) | active KD looks native to Mason; audit-invisible |
| 3 (delayed complete-orphan) | yes | **no** (Mason's identity gone; Ruby's identity gone since earlier) | **no** | reason=orphan; **indistinguishable from Case 1** at inspection time |
| 4 (canon; unrelated delete) | no | n/a | n/a | reason='' distinguishes canon from Case 2 also-active |

**Load-bearing takeaway:** post-commit, the surviving KD row cannot tell the operator (a) which teammate's delete orphaned it, or (b) whether the archived KD was originally shared or solo. Cases 1 and 3 are visually identical at recovery time. Case 2's Ruby-history is completely erased.

## §17. Repository-wide provenance / audit inventory

Complete file-cited inventory of every mechanism in the repo that could plausibly hold lifecycle provenance for KD orphaning. Extended search over the entire `shell/apps/` tree, not just `apps/embeddings/`.

### §17.1 Absences (nothing exists to reuse)

- **No generic `AuditLog` / `ActivityLog` / `EventLog` / `AuditRecord` / `ChangeLog` / `HistoryEntry` / `LifecycleEvent` / `DeletionRecord` / `Tombstone` model.** Verified via glob + grep across `shell/apps/**/models.py`. Zero hits under any of those names.
- **No `django-simple-history` or `django-reversion` integration.** Neither package is imported anywhere; neither appears in `pyproject.toml`.
- **No workspace-scoped persistent event stream API.** No SPA route exists that consumes a durable event feed.
- **No soft-delete on `Teammate`.** `shell/apps/spokespeople/models.py:27-33` defines a `Status.ARCHIVED = "archived"` choice but SESSION 275 §117 confirmed it is never exercised by the delete path — Teammate deletion is hard-delete via CASCADE only.
- **No delete-side actor capture.** Neither the SESSION 275 signal nor Django's Collector surfaces `request.user`. Actor identity is not recoverable at signal time without a thread-local or explicit param.

### §17.2 Adjacent structures that exist but are shape-mismatched

- **`PromotionAudit`** (`shell/apps/bootstrap_review/models.py:90-206`). Purpose-specific: SESSION 249 decision-materialization index for reference-promotion audit. Not a generic audit trail. Reusing it for orphan provenance would abuse the model's purpose and require multiple invariant changes.
- **`bootstrap_review/journal.py`** — in-memory journal for SESSION 249 Step 9 decision state. Not persistent.
- **`archived_at` soft-delete pattern** — established on `Universe` (`apps/universe/models.py:115`), `Episode` (`:329-334`), `NarrativeMemory` (`apps/memory/models.py:252-259`), `CharacterIdentity` (`apps/identity/models.py:147`). Universe/Episode/NM/CI are archived by *themselves*; the pattern does not model *event-about-an-external-row*.
- **`KnowledgeDocument.source_metadata`** (`apps/embeddings/models.py:212-219`) is a `JSONField(default=dict)` free-form field. Currently only holds ingestion-time metadata (Serper query, PDF page count, trafilatura stats). *Could* mechanically hold a `deleted_teammate` snapshot post-orphan-archive. **But** this would (i) overload a field whose docstring says "ingestion provenance," (ii) mix write-only-at-create semantics with write-at-lifecycle-event semantics, and (iii) be JSON-only (no FKs, no queryability by teammate id).
- **SET_NULL fingerprints** — `Composition.spokesperson`, `Asset.spokesperson`, `ConversationThread.spokesperson`, `Script.spokesperson`, `RealtimeSession.spokesperson`, `PersonalizedCampaign.spokesperson`, `CharacterIdentity.teammate` all SET_NULL on Teammate delete (SESSION 275 §14 diagram). This preserves *that a teammate once existed* (the row survives with `spokesperson_id=None`) but loses the teammate's identity. Slice 1 §4.2 used the `CharacterIdentity[Tank].teammate_id=None` fingerprint as *forensic* evidence of a past delete — but that's a fingerprint, not durable provenance about the specific KD orphaning event.
- **`created_by` / `promoted_by` actor fields** — pervasive on KD, Asset, Composition, Script, Universe, Episode, NarrativeMemory, Campaign, RealtimeSession, CharacterIdentityVersion. All SET_NULL on User delete. Records *actor at creation*, not *actor at deletion*.
- **`sweep_expired_assets` management command + Celery task** — cleanup pattern; performs SET_NULL updates on expired provider assets. Does not write an audit trail.

### §17.3 Verdict on reuse

None of the existing infrastructure is shape-appropriate to hold the provenance a future orphan recovery needs. Specifically:

- No model preserves the **name/identity of a deleted actor**.
- No model preserves **event context** at the moment of a mutation.
- No model is **workspace-scoped and event-shaped**.

**A new persistent record IS required *if* the product requires deleted-teammate identity for safe recovery decisions.** Whether the product actually needs that is answered next in §18. This slice does not decide storage shape — it only records that the reuse question was investigated and closed.

## §18. Minimum-sufficient-provenance analysis

Field-by-field evaluation of the candidate provenance set named in the task, evaluated independently. "Required" means *without this, a safe recovery decision cannot be reliably made*; "useful context" means *nice-to-have for the operator but not decision-blocking*; "unnecessary" means *the recovery decision is unchanged regardless*.

| Field | REQUIRED / USEFUL / UNNECESSARY? | Already durable? | Introduces stale-semantic risk? | Rationale |
|---|---|---|---|---|
| Deleted teammate **id** | USEFUL (not REQUIRED) | no | low — opaque UUID, no live join | Only useful if the teammate might be re-created with the same id (it can't; UUIDs are fresh) or if some other system stores the id. Operator does not read UUIDs |
| Deleted teammate **name** | **REQUIRED** | no | medium — name is display-stable, but a rename between original attach and delete would show the last-known name, not the historical attach-time name | Without a name, the operator cannot decide "attach this to a similar character" or "recognize this as knowledge belonging to a since-deleted character." Content-sniff may hint but is not authoritative (Case 3 makes this fail) |
| Deletion **timestamp** | USEFUL | yes — `KnowledgeDocument.updated_at` is set by the archive `.update()` (`signals.py:199`) | low — timestamp is single-fact | Already recoverable from the KD row. No new storage needed |
| **KD id** | REQUIRED (trivially — the KD is the target) | yes | none | Recovery is per-KD; identifier is inherently present |
| **Audience immediately before deletion (prior full M2M)** | USEFUL (not REQUIRED) — only useful if we want a "restore to previous audience" affordance. Absent that affordance, unused | no — the prior M2M is CASCADE-deleted before the operator can inspect it | high — the "previous audience" for a Case 3 KD may itself have included a since-deleted teammate whose name is *also* gone. A restored M2M list containing only dangling names/ids would be misleading | Only meaningful for a "restore-to-prior-audience" feature that Chris has not authorized. Without that feature, this data is decorative |
| **Surviving audience immediately after deletion (surviving M2M)** | UNNECESSARY | trivially yes — it's the KD's current `spokespeople.all()` | none | Directly queryable on the surviving KD row. No storage needed |
| **Universe at deletion** | USEFUL | trivially yes — `KnowledgeDocument.universe_id` is unchanged by the archive | none | Directly queryable |
| **Workspace** | REQUIRED (already durable) | yes — `KnowledgeDocument.workspace_id` unchanged | none | Directly queryable |
| **Reason / event type** | REQUIRED | yes — `KnowledgeDocument.deactivated_reason` is set to `orphaned_by_teammate_delete` by the signal | none | SESSION 275 already added this field. This is the *why* |
| **Operator/system actor if knowable** | USEFUL | no — signal path does not carry `request.user` | medium — actor may be "system:teammate_delete_signal" if the delete originated from admin or DRF, but no thread-local capture exists. Attributing wrongly is worse than not attributing | Useful for multi-user workspaces or forensic audit. Not decision-blocking for a single-operator workspace like Chris's |
| **Whether this deletion actually caused the KD to become orphaned** | REQUIRED (already durable) | yes — implied by `deactivated_reason='orphaned_by_teammate_delete'` set by that specific delete | none | The reason field is monotone; if present, the archive happened |
| **Prior audience history before the final deletion (Case 3 detection)** | USEFUL (not REQUIRED) — decisions do not depend on this | no — only observable if every audience-narrowing event was journaled from the beginning | high — history would be incomplete unless journaled from now onward; retrofitting is impossible | Would enable "this KD was previously shared with N teammates" copy. Not decision-blocking |

### §18.1 Answer to §13.A — the minimum sufficient provenance

**Required (for a safe explicit-audience recovery decision):**

1. **Deleted teammate name.** Operator must be able to recognize whose knowledge this was.
2. **KD id + workspace id + reason + timestamp.** Already durable — no new storage needed.

**Useful context (not decision-blocking, but low-cost to record with the same event):**

3. Deleted teammate id (opaque; useful for cross-system reconciliation).
4. Deleted teammate `universe_id` at delete time (helps operator scope the replacement audience).
5. Actor user id (if thread-local capture exists; not required to invent one).

**Unnecessary / trap fields:**

6. Full prior M2M snapshot — only justified by a "restore to previous audience" feature; Chris has not authorized that feature; recording it now is speculative.
7. Prior audience *history* for narrowing events (Case 2 chain) — retrofitting is impossible; forward-only journaling would produce incomplete data for years; product decisions do not depend on it.

### §18.2 Sub-question — final deleted character vs. audience-immediately-before-orphaning

For orphan-archived KDs (Cases 1 and 3), the audience immediately before orphaning is by definition the deleted character (and only the deleted character — otherwise the KD would not be orphaned; sp_count would have been > 0 after CASCADE, per §16.Case-2). So the two questions collapse to the same fact.

For narrowing deletes (Case 2), the KD is **not** archived, so no recovery decision is triggered — the KD stays active with the surviving audience. No provenance is required.

**Conclusion:** *safe recovery only requires remembering the final deleted character at the moment of archive.* Recording historical audience for every audience-narrowing deletion (Case 2) is not required; it would produce mostly-uninteresting journal entries and carries retrofit-completeness risk.

### §18.3 Sub-question — every deletion or only when the KD is archived?

**Only when the KD is archived.** The invariant SESSION 275 §23 protects is *broadening on removal*. Narrowing (Case 2) does not violate the invariant. Recovery UI has no decision to make about a KD that is still active with a bounded audience. Journal entries for narrowing events are decorative, not load-bearing.

## §19. Revival mutation-boundary inventory

Every application path today capable of affecting `is_active`, `deactivated_reason`, `spokespeople` M2M, or `universe` on a `KnowledgeDocument`. Enumerated exhaustively via grep (§Slice 1 §5.5 covered `is_active`; extended here to M2M / universe).

### §19.1 `is_active` mutation surface

| # | Path | File:line | Sets `is_active=True`? | Sets `is_active=False`? | Gated? |
|---|---|---|---|---|---|
| 1 | Ingestion revival on dedup hit | `shell/apps/embeddings/ingestion.py:164` | yes | no | **YES** — `OrphanRevivalRejected` at `:150` if reason is `ORPHANED_BY_TEAMMATE_DELETE` and no spokespeople provided |
| 2 | Ingestion fresh insert | `shell/apps/embeddings/ingestion.py:191-207` | yes (as `default=True` on create) | no | n/a — new row, no history |
| 3 | DRF `DELETE /api/knowledge/<id>/` | `shell/apps/embeddings/views.py:124` | no | yes (stamps reason `OPERATOR_DELETE`) | n/a — soft-delete of active row |
| 4 | DRF `PATCH /api/knowledge/<id>/` with `{"is_active": true}` on an active KD | `shell/apps/embeddings/serializers.py` — `is_active` is R/W (§Slice 1 §5.3) | via serializer field | via serializer field | **coincidentally sealed** — `get_queryset` filters `is_active=True` (`views.py:70`) so inactive KD is unreachable via detail routes. Active-KD PATCH on `is_active=true` is a no-op. If a future change relaxes the queryset filter, this gate silently vanishes |
| 5 | DRF `attach` / `detach` actions | `apps/embeddings/views.py:143-159` | no | no | **coincidentally sealed** by same queryset gate |
| 6 | Teammate `post_delete` signal | `apps/spokespeople/signals.py:196-200` | no | yes (stamps reason `ORPHANED_BY_TEAMMATE_DELETE`) | invariant enforcer (writes safely; other paths must not bypass) |
| 7 | Django admin change form | `apps/embeddings/admin.py:22-40` | **yes — unguarded** | **yes — unguarded** | **NO** — `is_active` and `deactivated_reason` are both editable and not in `readonly_fields`. Slice 1 §5.2 flagged this |
| 8 | Direct ORM `KnowledgeDocument.objects.filter(...).update(is_active=True)` | any code path | yes (bypasses `.save()`, `clean()`, `pre_save`/`post_save` signals) | yes | **NO** — bypass by design |
| 9 | Raw SQL | any migration or `connection.cursor()` call | yes | yes | **NO** |
| 10 | Management command / `manage.py shell` | any command | yes | yes | **NO** — always-available; not the operator surface |

### §19.2 `deactivated_reason` mutation surface

- Set to `OPERATOR_DELETE` by (3). Set to `ORPHANED_BY_TEAMMATE_DELETE` by (6). Cleared to `""` by (1) and (2). Editable via (7)–(10).
- **No `save()`/`pre_save`/`m2m_changed` receiver observes the *transition* from `ORPHANED_BY_TEAMMATE_DELETE` → `""` outside of the ingestion gate.**

### §19.3 `spokespeople` M2M mutation surface

Enumerated via `grep 'spokespeople\.(set|add|remove|clear)'`:

| Path | File:line | Guarded? |
|---|---|---|
| Serializer `update()` — `instance.spokespeople.set(...)` | `apps/embeddings/serializers.py:500` | pre_add m2m_changed signal enforces workspace + Universe invariants (`apps/embeddings/signals.py:31,93`); no `post_clear` / `post_remove` observer for the "M2M just went empty" transition |
| Serializer `create()` — `existing.spokespeople.set(...)` (revival) | `apps/embeddings/ingestion.py:182` | same |
| Ingestion fresh create — `doc.spokespeople.set(...)` | `apps/embeddings/ingestion.py:213` | same |
| View `attach` — `doc.spokespeople.add(sp)` | `apps/embeddings/views.py:183` | same |
| View `detach` — `doc.spokespeople.remove(sp)` | `apps/embeddings/views.py:185` | **no post-remove guard** — a detach that empties the M2M passes silently. SESSION 275 relies on the signal-based archive to catch the *Teammate-delete* path; a detach on an active KD that empties the M2M today just flips the KD from character-specific to "broadcast to all in scope" **and is not gated** |
| CASCADE via Teammate delete | Django internal | protected by SESSION 275 signal (§15) |
| Django admin — spokespeople NOT exposed on change form | `apps/embeddings/admin.py:35-39` — comment: *"`filter_horizontal` is incompatible with an explicit M2M `through=`. … attach/detach still happens via the K5 API"* | admin cannot edit M2M; admin can still toggle `is_active` |
| ORM `.through.objects.create/delete(...)` | any code | ungated (bypasses `m2m_changed` `pre_add` — actually `m2m_changed` fires only when the related manager is used, not when the through model is manipulated directly) |
| Management command / raw SQL | any | ungated |

**Latent hole flagged for future audit.** `apps/embeddings/views.py:185` `detach` is documented (in the docstring at `views.py:152-158`) as intentionally allowing the M2M to collapse to empty ("*detaching the last spokesperson … collapses visibility back to *all* spokespeople in the workspace"*). This is a **known audience-broadening operator gesture** already permitted today. Under SESSION 275 §23's invariant, that gesture should require an *explicit* operator confirmation that the operator intends broadcast. It does not today; SESSION 275 did not close it because the gesture is operator-initiated (not a removal-side effect). Nonetheless, this is a live audience-broadening path in production that Slice 2 identifies as adjacent to the current investigation.

### §19.4 `universe` FK mutation surface

- Serializer `update()` — `instance.universe = new_universe` (`apps/embeddings/serializers.py:425-445`) with a preflight M2M-orphan guard.
- Django admin change form — editable, not in `readonly_fields`.
- ORM / raw SQL — ungated.

### §19.5 The composition failure

The SESSION 275 §57 lesson: "an implementation can look correct locally while failing under bulk deletion." The Slice 2 equivalent:

**Any candidate enforcement that reasons only about `is_active` transitions in isolation will fail under composition.** Concretely:

- An enforcement that says *"reject `is_active=True` when spokespeople M2M is empty"* fails against **Class A / C canon** (born-empty KDs that are legitimately `is_active=True, spokespeople=∅`). See §16.Case-4.
- An enforcement that says *"reject `is_active=True` when `deactivated_reason='orphaned_by_teammate_delete'`"* fails when an admin *first* clears `deactivated_reason` to `""` and *then* flips `is_active=True`. Two operations, each individually not violating the rule, together recreate the leak.
- An enforcement that says *"reject clearing `deactivated_reason` from `ORPHANED_BY_TEAMMATE_DELETE` unless spokespeople is non-empty"* fails against `QuerySet.update(deactivated_reason="")` because `pre_save` and `clean()` don't fire for `.update()`. A DB CHECK constraint that fired on the transition would need trigger-level logic (Postgres check constraints cannot observe old vs. new; they see only the new row).

The correct rule shape is a **composite pair of invariants** where each seals a different bypass:

- **Invariant I (steady-state):** `NOT (is_active=True AND deactivated_reason='orphaned_by_teammate_delete')` — a row cannot be simultaneously active and marked as still-orphan. Enforceable as a Postgres `CHECK` constraint on the KD row (single row, no relations). Catches `.update()`, raw SQL, admin form ("save the row with is_active=True but forgot to clear reason"), and every other write path.
- **Invariant II (transitional):** clearing `deactivated_reason` from `ORPHANED_BY_TEAMMATE_DELETE` requires that the row also becomes character-scoped by a non-empty M2M `.set(...)` **as part of the same operator gesture**. Enforceable in Python at the model / serializer / admin layer, because it requires observing the *before* and *after* states — Postgres CHECK constraints cannot do this alone (would need a trigger).

The two together cover: admin form save (I catches "flip is_active without clearing reason"; II catches "clear reason without attaching spokespeople"), `.update()` writes (I fires at DB level), ingestion revival (already gated by `OrphanRevivalRejected`), future SPA restore endpoint (II fires at serializer layer).

Slice 2 does **not** implement any of this. It records the composite shape as the minimum sufficient sealing pattern; storage/enforcement mechanism selection is Chris's decision.

## §20. Candidate invariant-boundary comparison

Six candidate enforcement locations for the composite invariant. Comparison against actual Django semantics.

| # | Boundary | Fires on `PATCH` via serializer? | Fires on `.save()` (model)? | Fires on `.update()` (queryset)? | Fires on admin form save? | Fires on `.spokespeople.set/add/remove/clear`? | Breaks Class A/C canon? | Verdict |
|---|---|---|---|---|---|---|---|---|
| A | Serializer `validate()` / `update()` in `KnowledgeDocumentSerializer` | yes | no (`.save()` bypass) | no | no | via serializer only | no (only affects operator-facing DRF path) | insufficient — bypasses admin, `.update()`, and any non-serializer code path |
| B | ViewSet `perform_update()` / dedicated `POST /restore/` action | yes | no | no | no | no | no | narrower than A; only catches DRF. Insufficient |
| C | Ingestion boundary — `_persist` | yes (via `OrphanRevivalRejected`) | no | no | no | no | no | already implemented; sufficient for ingestion path only. Does not extend to admin / serializer / etc. |
| D | Django admin `save_model` override | no | no | no | yes | yes (via `save_related`) | no | admin-only. Coordinates with A/B/C — does not replace them. Task explicitly says do NOT assume this is the correct fix in isolation |
| E | Model `KnowledgeDocument.save()` / `clean()` extension + `pre_save` receiver | via `.save()` | yes | **no** (`.update()` bypasses `save()` + all its signals) | yes (admin form calls `save()` → `pre_save`, and `full_clean()` invokes `clean()`) | separately via `m2m_changed` `post_remove` / `post_clear` receiver | no (checks are keyed on `deactivated_reason`, not M2M-empty alone; canon has reason=`''`) | strongest single Python layer — but still has `.update()` bypass. Must compose with F or C or another DB-level layer |
| F | Postgres `CHECK` constraint on `(is_active, deactivated_reason)` row shape | yes (rejected at commit) | yes | **yes** | yes | n/a (constraint applies only to KD columns, not M2M) | **no** — canon has `deactivated_reason=''`, so `NOT (is_active=True AND deactivated_reason='orphaned_by_teammate_delete')` is satisfied | strongest single layer for the *steady-state* invariant. Cannot observe transitions or M2M state; must compose with E (or similar) to enforce the transitional invariant |
| G | Signal on `KnowledgeDocument.pre_save` observing `_state.adding` and old-value diff | yes (via `.save()`) | yes | **no** | yes | no (M2M edits do not fire `pre_save`) | no | equivalent power to E for the transitional check. Same `.update()` bypass |
| H | Model `.delete()` override on `KnowledgeDocument` | n/a | n/a | n/a | n/a | n/a | n/a | wrong direction — this is about *reactivation*, not deletion. Not applicable |

### §20.1 Recommended sealing pattern (READ-ONLY finding; NOT implemented)

The evidence supports a **two-layer composite** as the narrowest sufficient enforcement:

- **Layer 1 — DB `CHECK` constraint** on `KnowledgeDocument` enforcing `NOT (is_active=true AND deactivated_reason='orphaned_by_teammate_delete')`. Universal (catches every write path including `.update()` and raw SQL). Does not break canon (canon has `deactivated_reason=''`).
- **Layer 2 — Python `clean()` extension or `pre_save` receiver** on `KnowledgeDocument` enforcing: if the transition is `deactivated_reason: ORPHANED_BY_TEAMMATE_DELETE → ""`, then either (a) the same save must attach non-empty spokespeople, OR (b) the save must be part of an explicit operator recovery gesture that provides an audience-selection payload. Catches admin form save and any code path that goes through `.save()`.
- **Layer 0 — the existing ingestion gate** (`OrphanRevivalRejected`) remains in place; it is a specialized instance of Layer 2 at the ingestion boundary and continues to serve its purpose.

Layers 1 and 2 are complementary: Layer 1 seals `.update()` / raw SQL / admin "forgot to clear reason"; Layer 2 seals admin "clear reason but no attach." Neither alone is sufficient. Both together cover every mutation path enumerated in §19.

Candidates A (serializer only), B (dedicated restore endpoint only), and D (admin `save_model` only) are individually **insufficient** and were rejected as the primary enforcement location. Any of them can and should be used as **operator-facing surfaces** that call into the Layer 2 primitive, but they are not themselves the invariant boundary.

### §20.2 Class A / C canon is preserved

For every candidate above, canon is preserved because the check keys on `deactivated_reason='orphaned_by_teammate_delete'` (a positive marker), not on `spokespeople.count()==0` (which canon shares with orphans). This distinction is load-bearing and Slice 2 explicitly preserves it.

## §21. Adversarial scenarios evaluated

### §21.1 Slice 2 primary adversarial scenario

Task-provided scenario:

1. Character-specific KD becomes orphaned and inactive (SESSION 275 signal fires; `deactivated_reason='orphaned_by_teammate_delete'`; M2M is empty).
2. M2M stays empty.
3. A future code path changes only `is_active=True`.
4. Retrieval still interprets empty M2M as broadcast/shared (predicate at `apps/embeddings/retrieval.py:216-220` unchanged).

**Result:** the orphaned KD becomes retrievable to every eligible teammate in scope — the exact SESSION 275 leak.

**Sealing:** Layer 1 CHECK constraint (§20.1) rejects the write at commit. No matter which path invoked step 3, the DB fails the write.

### §21.2 Adversarial variant — clear reason first, then flip

1. Same setup.
2. Admin edit: `deactivated_reason` cleared to `""`, `is_active` left False. Saves successfully (Layer 1 is satisfied — the row is not simultaneously active + orphan-marked).
3. Second admin edit or `.update()`: `is_active=True`. Layer 1 is satisfied (reason is now `""`).
4. Retrieval predicate broadcasts.

**Result:** leak recreated in two steps.

**Sealing:** Layer 2 catches step 2 (or step 3 depending on which transition triggered): clearing `deactivated_reason` from `ORPHANED_BY_TEAMMATE_DELETE` requires attaching non-empty spokespeople. `.save()`-based writes (admin, serializer) fire `pre_save` and hit Layer 2. `.update()` writes bypass Layer 2 but Layer 1 catches them differently — specifically, a `.update()` that sets only `deactivated_reason=""` while leaving `is_active=False` would satisfy Layer 1 but *not* satisfy the intended composite invariant. This is a residual hole for `.update()` calls that clear reason without touching `is_active` — flagged as unresolved in §23.

### §21.3 Adversarial variant — bypass by promoting to Universe-scoped

1. Same setup.
2. An operator wants to legitimately promote the orphan-archived KD to Universe-scoped canon (Class C).
3. Admin edit: `deactivated_reason=""`, `universe=U`, `is_active=True`. M2M stays empty.
4. Retrieval predicate: for a teammate in Universe U, the empty-M2M fallback matches; the KD is broadcast Universe-wide.

**Is this a leak?** By SESSION 275 §23, this is a *legitimate operator gesture* if the operator explicitly chose Universe-shared. It becomes a leak only if the operator did not intend that.

**Sealing:** Layer 2 must distinguish "clear reason because I attached spokespeople" from "clear reason because I explicitly chose Universe-shared" from "clear reason accidentally." The cleanest distinction is an explicit operator payload (a `POST /api/knowledge/<id>/restore/` endpoint requiring `{"audience": {"spokesperson_ids": [...]} | {"universe": "..."} | {"workspace_shared": true}}`). Admin — which has no such payload — should either be forbidden from clearing reason on `ORPHANED_BY_TEAMMATE_DELETE` rows, OR require an admin-side extra step (e.g. `save_model` override that refuses unless the operator ticks a "confirm intentional broaden" checkbox).

The current codebase has **no explicit "workspace-shared" marker** — every Class A canon KD relies on `deactivated_reason='' AND spokespeople=∅ AND universe=None` as the *implicit* signal. This is Option C (`KnowledgeAudience` model) territory — Slice 2 does not open it — but the load-bearing observation is: **the invariant cannot mechanically distinguish "intentional workspace-shared canon" from "silently broadened orphan" today** without an explicit operator gesture. The revival gate must therefore require an explicit gesture whether the target audience is character-specific, Universe-shared, or workspace-shared.

### §21.4 Adversarial variant — SPA "Show archived" without gate

1. Future SPA slice adds `?include_inactive=true` to `GET /api/knowledge/`.
2. Backend viewset relaxes `is_active=True` filter when the param is present.
3. Suddenly `get_object` returns inactive KDs; `PATCH is_active=True` succeeds.
4. Serializer `is_active` is R/W (§Slice 1 §5.3) — the PATCH commits.
5. Leak recreated.

**Sealing:** Layer 1 CHECK constraint catches this at commit. Additionally, whenever the SPA visibility change lands, the serializer's `is_active` field should be explicitly moved to `read_only_fields` and revival must go through a dedicated restore endpoint that enforces Layer 2. Slice 2 records this as a **required paired change** for any archived-visibility feature — it must not ship alone.

## §22. Refinement of Slice 1 §6 Q4 statement on inactive-KD audience

**Slice 1 §6 Q4 wording** (verbatim):

> Neither case carries a first-class "intended audience" field. An inactive KD's "audience" is either whatever the M2M happened to be (potentially empty; potentially stale) or nothing at all.

**Refinement — the Slice 1 wording is imprecise and Slice 2 corrects it.** The correct source-derived reading:

- **Operator-deleted KD** (`deactivated_reason='operator_delete'`): the DELETE view (`shell/apps/embeddings/views.py:110-129`) sets `is_active=False` and `deactivated_reason='operator_delete'` via `.save(update_fields=[...])`. It does **not** touch the `spokespeople` M2M. Therefore the M2M **retains whatever explicit set the operator had chosen before delete** — Ruby-specific, Ruby+Mason-shared, empty for canon, etc. The M2M is a valid record of the last operator-intended audience.
- **Orphan-archived KD** (`deactivated_reason='orphaned_by_teammate_delete'`): the archive path fires after Django's CASCADE has already removed all through-rows for the deleted teammate. In §16.Case-1, the M2M is `∅` **because** the last spokesperson was CASCADE-removed. In §16.Case-3, the M2M is `∅` for the same reason. The M2M **cannot** represent the pre-delete audience — that state was CASCADE-destroyed before the archive-write executed.

**Corrected statement:** an *operator-deleted* inactive KD retains its pre-delete M2M as a meaningful audience anchor (revival can preserve it — `ingestion.py:181-182` restores it when the caller supplies no new spokespeople). An *orphan-archived* inactive KD has an empty M2M by construction and cannot recover its pre-delete audience from surviving state; safe revival must therefore *require* an explicit new audience choice (the SESSION 275 §47 revival gate encodes exactly this rule).

**Why the refinement matters for Slice 2:**

- The two archive causes carry **different audience recoverability semantics**, not just different reason strings.
- A future recovery UX that presents an archived KD to the operator can (a) *preserve and offer* the surviving M2M as "restore to prior audience" for `operator_delete` KDs, and (b) *demand* a fresh audience choice for `orphaned_by_teammate_delete` KDs.
- This refinement does not change any code, invariant, or recovery contract — it corrects a Slice 1 §6 Q4 statement that read too broadly and would have obscured the operator_delete vs orphan distinction in Slice 2's provenance analysis.

Slice 1 §6 Q4 remains as originally written (per SESSION 275 doc-preservation discipline — "do not silently overwrite the previous conclusion"). §22 stands as the recorded refinement.

## §23. Prediction vs evidence

| Prediction (§14) | Evidence |
|---|---|
| Deleted-teammate-name is the biggest single provenance jump; everything else is available or nice-to-have | Confirmed — §18 table. Name is REQUIRED; id is USEFUL not REQUIRED; timestamp/reason/kd_id/workspace/universe are already durable |
| DRF queryset seal + ingestion gate together cover a narrow case; admin + `.update()` bypass both | Confirmed — §19.1 rows 7-9 |
| Narrowest sufficient enforcement is a *composite* — model/pre_save + DB CHECK — not a single boundary | Confirmed — §20 comparison; §21.1-§21.4 adversarial variants each require different layers |
| Any candidate keyed on "reject `is_active=True` when M2M is empty" breaks Class A/C canon | Confirmed — §20.2. Keying on `deactivated_reason` positive marker avoids this |
| SESSION 275's `pre_delete` writes nothing durable about the deleted teammate identity | Confirmed — `signals.py:201-206` emits `logger.info` only; §17.1 shows no reusable audit model |

All Slice 2 predictions supported by evidence.

## §24. Unresolved questions

1. **Storage shape for deleted-teammate identity.** §18.1 says "name" is REQUIRED. Whether that's a new `KnowledgeDocumentArchiveLog` model, a JSON snapshot appended to `KnowledgeDocument.source_metadata`, a `deleted_teammate_name` denormalized column on `KnowledgeDocument`, or some other shape — is a product/architecture decision. **Slice 2 does not choose.**
2. **Whether to also record deleted-teammate id / universe_id / actor.** §18 marks them USEFUL not REQUIRED. Cost of recording is low (marginal columns / JSON keys) if a persistent record is created at all. Under-record risks operator context; over-record risks stale semantics if identifiers are later reused.
3. **Actor capture at signal time.** Django signals have no `request.user` by default. A thread-local or an explicit param on `Teammate.delete()` would be needed. Not authorized to build.
4. **Residual hole in §21.2 for `.update(deactivated_reason="")` without touching `is_active`.** Layer 1 (CHECK constraint on the pair) does not catch this. Second write would then flip `is_active`. Full sealing requires either (a) a `CHECK` on `deactivated_reason` transitions (needs trigger — Postgres check constraints see only the new row) or (b) making `deactivated_reason` truly append-only at DB level with a separate history table. Both are heavier than Slice 2 is investigating.
5. **The known-permitted operator gesture at `detach` (§19.3, `views.py:185`) that intentionally collapses M2M to empty.** SESSION 275 accepted this as operator-explicit and did not gate it. Under Slice 2's stricter reading of §23's invariant, that gesture *does* broaden audience without an explicit "I intend broadcast" confirmation. Should the recovery-invariant work also close this gate? Not authorized to touch; flagged.
6. **Whether to record narrowing events (Case 2).** §18.3 concludes no. If a future feature explicitly needs "this KD was previously shared with N teammates" copy, revisit. Nothing depends on it today.
7. **Whether existing `source_metadata` should be reused for lifecycle events.** §17.2 says overload risk is real. Preserving `source_metadata` for ingestion-time facts and using a separate mechanism for lifecycle events is architecturally cleaner but requires the new mechanism §24.1 defers.
8. **Bundle vs split (carried forward from Slice 1 §8 point 4).** Still not answered by evidence; still a Chris product decision.

## §25. Recommendation

**Do not implement anything in Slice 2.** The audit's job was to establish the information requirement (§18) and the invariant boundary shape (§20). Both are established.

Two directional readings the evidence supports (**not** recommendations until Chris chooses):

- **Direction Alpha — small: preserve name only.** Add a single denormalized `KnowledgeDocument.orphaned_by_teammate_name = CharField(blank=True, default="")` populated by the SESSION 275 `post_delete` handler alongside the reason stamp. No new model. Recovery UX shows "Archived — knowledge belonged to *{name}*." Name is the single REQUIRED field per §18. Everything else stays as it is. Enforcement invariant is deferred; §21.1's leak still requires Layer 1 + Layer 2 to fully seal — Direction Alpha addresses provenance, not enforcement.
- **Direction Beta — richer: new lifecycle-event model.** Add `KnowledgeDocumentArchiveLog(kd_id, deleted_teammate_id, deleted_teammate_name, deleted_teammate_universe_id, workspace_id, deleted_at, actor_user_id_nullable, prior_spokesperson_ids_json)`. First lifecycle-event model in the codebase (§17.1). Recovery UX can show full context. Extensible if other lifecycle events (Universe delete, workspace hand-off, character merge) emerge later. More surface area; more schema to migrate; not required by §18's minimum.

**Invariant sealing (§21.1) is a separate decision from provenance.** Direction Alpha or Beta both leave the SESSION 275 §46 revival invariant exactly as strong as it is today (ingestion-only). Fully closing the enumerated bypasses (§19, §21.1-§21.4) requires the composite Layer 1 + Layer 2 pattern in §20.1 — whether Chris opts for that now, later, or defers until the next actual breach evidence is his call.

**Current schema is sufficient for a small safe recovery workflow** (Slice 1 §5.6 restated): `deactivated_reason` + `spokespeople` + `universe` cover the audience-decision primitive. No schema change is *strictly required* for the recovery workflow itself. What is missing today is (a) surfaces (SPA visibility, restore endpoint), (b) provenance (deleted-teammate-name for operator context), and (c) full enforcement (composite invariant). Each is separable.

## §26. Explicit decision gate

**STOP.** Slice 2 does not authorize any code, migration, DB row, admin change, or SPA change.

Before Slice 3 begins, Chris must decide:

1. **Provenance:** Direction Alpha (name-only denormalized column) vs Direction Beta (lifecycle-event model) vs neither yet.
2. **Enforcement:** commit to the Layer 1 + Layer 2 composite (§20.1)? Ship one layer first? Defer until a breach is actually observed?
3. **Recovery UX ordering:** does provenance + enforcement precede any archived-visibility UI? (Given §21.4, they should. Enforcement layers must be in place before "Show archived" ships.)
4. **§24 residuals:** actor capture, `.update()` bypass residual, `detach → empty` gesture, `source_metadata` reuse, bundle vs split — each is a discrete decision.

Chris's answers determine Slice 3 scope. Slice 3 must open with a design/plan section, not implementation — same pattern as SESSION 275 §21-§38 and Slice 1 §10.

## §27. Smallest falsifiable next questions

Formulated so Slice 3 can open on a concrete question rather than re-audit.

- **Q-276-5.** *If we add the DB CHECK constraint `NOT (is_active=true AND deactivated_reason='orphaned_by_teammate_delete')` (Layer 1), does any existing test fail?* Falsifiable by running the full test suite after adding the constraint in a scratch branch. Direct answer: probably no tests fail — SESSION 275's own tests set both together correctly and no legitimate code path ever violates the pair — but empirical verification is the smallest experiment that proves the constraint is compatible with today's codebase.
- **Q-276-6.** *If we add `KnowledgeDocument.orphaned_by_teammate_name` and stamp it in `_archive_orphaned_kds_on_teammate_delete`, does the existing failure-injection atomicity test (`test_teammate_delete_atomic_if_orphan_archive_update_fails`, SESSION 275 test 13) still hold?* Falsifiable — the test patches `QuerySet.update`; adding a column to the same `.update()` call must remain rolled back on failure. Small verification. Direction Alpha requires this.
- **Q-276-7.** *Does closing the Django admin bypass by adding `is_active` and `deactivated_reason` to `readonly_fields` on `KnowledgeDocumentAdmin` break any legitimate admin workflow?* Falsifiable by inspecting whether SESSION 275 or any test relies on admin flipping these fields. Slice 1 §5.5 notes admin is *not* the operator-safety surface — admin currently is the bypass, not a documented workflow. Making these fields readonly in admin is the smallest single-line lock.
- **Q-276-8.** *If we build a `POST /api/knowledge/<id>/restore/` endpoint with an audience-payload contract and a `?include_inactive=true` list param, is the code additive (no changes to existing routes) or does it require modifying the queryset filter?* Falsifiable by attempting the design. Answers whether SPA visibility can ship independently from other changes.
- **Q-276-9.** *For each of the 9 legacy KDs, can Chris deterministically classify (from §Slice 1 §4.4 evidence) whether to (a) delete via existing SPA affordance, (b) attach to a specific character, or (c) promote to Universe/workspace-shared canon — and how long does that classification take?* Falsifiable by Chris doing it once for TANK (the PROVEN orphan; safest first move). Result determines whether legacy remediation is a small operator task or a product-scope commitment.

Each is a ½-slice worth of falsifiable work. None require touching production data first.

## §28. Slice 2 checklist

- [x] Re-verify baseline against Slice 1 §3 — main == origin/main, 9 KDs unchanged, migration + signals + revival gate intact — §Slice 2 preamble
- [x] Slice 2 Question A stated — §13.A
- [x] Slice 2 Question B stated — §13.B
- [x] Predictions before evidence — §14
- [x] Exact SESSION 275 signal lifecycle traced with file:line — §15.1
- [x] Information-loss timeline (T-1 through T+3) — §15.2
- [x] What survives / what is permanently lost — §15.3
- [x] Case 1 (solo delete) — §16.Case-1
- [x] Case 2 (narrowing delete) — §16.Case-2
- [x] Case 3 (delayed complete-orphan) — §16.Case-3
- [x] Case 4 (canon; unrelated delete) — §16.Case-4
- [x] Case-summary matrix — §16.5
- [x] Repo-wide provenance/audit inventory — §17.1 (absences), §17.2 (adjacent-but-mismatched), §17.3 (verdict)
- [x] Minimum-sufficient-provenance analysis, field by field — §18
- [x] Answer to §13.A explicit — §18.1
- [x] Sub-question — final vs pre-orphan audience — §18.2
- [x] Sub-question — every deletion vs archive-only — §18.3
- [x] Mutation-boundary inventory (is_active, deactivated_reason, M2M, universe) — §19
- [x] Composition-failure analysis of naive rules — §19.5
- [x] Candidate invariant-boundary comparison — §20
- [x] Recommended sealing pattern (READ-ONLY finding) — §20.1
- [x] Class A/C canon preservation verified — §20.2
- [x] Primary adversarial scenario evaluated — §21.1
- [x] Adversarial variant — clear reason first — §21.2
- [x] Adversarial variant — legitimate Universe promotion path — §21.3
- [x] Adversarial variant — future SPA archived-visibility — §21.4
- [x] Refinement of Slice 1 §6 Q4 statement (operator_delete vs orphaned retain audience differently) — §22
- [x] Prediction vs evidence — §23
- [x] Unresolved questions carried forward — §24
- [x] Recommendation (no implementation; two directional options) — §25
- [x] Explicit decision gate — §26
- [x] Smallest falsifiable next questions — §27
- [x] Zero KD rows mutated; zero migrations run; zero signals altered; zero admin/SPA/serializer changes; zero provider spend; working tree change limited to this document
- [ ] Chris review + Slice 3 scoping decision (§26)

---

**End of SESSION 276 Slice 2 read-only audit. STOP before implementation. Awaiting Chris + ChatGPT review on §25 recommendation, §26 decision gate, and §27 next questions.**

---

# SESSION 276 — Slice 3 read-only audit: full audience-transition system

**Status.** READ-ONLY audit / design evidence only. Continued from Slice 2. No code, migration, DB row, admin, SPA, model, constraint, or provider behavior modified during this slice.

**Slice 3 baseline.** `main == origin/main == d4754737`. Doc pre-Slice-3 append length: 927 lines. 9 KDs unchanged (`is_active=True, deactivated_reason='', universe=None, spokespeople=∅`). Ruby Class C `8f825c98-…` unchanged (`is_active=True, reason='', universe=1a0af807-…, m2m=0`). Ruby Class D `74e7f18f-…` unchanged (`is_active=True, reason='', universe=1a0af807-…, m2m=1`). Django `:8010` 302; Vite `:5174` 200.

**Load-bearing invariant carried forward** — SESSION 275 §23 + Slice 2 §21 corollary:

> A removal, deletion, detach, recovery, or other lifecycle action must never broaden the audience of surviving knowledge unless the operator explicitly chooses that broader audience.

**Load-bearing Slice 2 refinement carried forward** — §22:

- operator-deleted inactive KD retains its prior M2M audience anchor;
- orphan-archived KD loses its final character relation and requires a fresh explicit audience choice before revival.

Legacy 9 KDs remain preserved as forensic specimens; no remediation in this slice.

## §29. Slice 3 falsifiable question

> What are ALL legitimate `KnowledgeDocument` audience / lifecycle transitions supported by the current system, and for each transition does the resulting audience reflect explicit operator intent or an implicit side-effect of another operation?

The premise for Slice 3: SESSION 275 (Teammate delete) and Slice 2's investigation of the orphan-revival case both revealed the same root pattern — empty M2M is overloaded across "intentional canon" and "audience-broadening side-effect." Before recommending a fix for any *further* individual manifestation, Slice 3 maps the entire audience-transition system and tests whether Slice 2's Layer 1 + Layer 2 proposal (§20.1) generalizes.

## §30. Predictions before evidence

1. **detach-final vs `PATCH spokesperson_ids=[]`.** Predicted semantically equivalent — both drop M2M to ∅ on an active KD. Both produce the same retrieval outcome. Difference will be gesture surface (endpoint vs endpoint), not effect.
2. **Universe removal (`PATCH universe=null`).** Predicted to create an implicit broadening path when applied to a Universe canon KD (`SD` state) — the KD becomes legacy-workspace-shared without operator gesture beyond "reassign scope."
3. **Slice 2 Layer 1 + Layer 2 sufficiency.** Predicted insufficient as a *general* audience-safety boundary. Both layers key on `deactivated_reason`, which is only set on archive. Active-KD broadenings (detach-final, PATCH-empty, universe-detach on canon) don't involve `deactivated_reason` at all.
4. **Explicit "workspace-shared" operator gesture.** Predicted absent. Workspace-shared is inferred from `(is_active=True, universe=None, spokespeople=∅, deactivated_reason='')` — no positive marker.
5. **Evidence for first-class KnowledgeAudience.** Predicted the transition audit will surface enough distinct manifestations of the same root that the "cleaner" framing from SESSION 275 §36 / Slice 2 §25 is upgradeable to "the general fix." But this remains a Chris product decision — Slice 3 records evidence, not architecture commitments.

Predictions compared to evidence in §40.

## §31. Current-state definitions (derived from actual behavior)

Every `KnowledgeDocument` is fully described for retrieval purposes by the tuple `(is_active, universe, spokespeople, deactivated_reason)`. Combining these with the retrieval predicate at `shell/apps/embeddings/retrieval.py:194-221` yields six behaviorally distinct states:

| Label | `is_active` | `universe` | `spokespeople` | `deactivated_reason` | Retrieval audience |
|---|---|---|---|---|---|
| **SA** — active character-specific legacy | True | NULL | ≥1 legacy teammate(s) | `''` | Those legacy teammates only |
| **SB** — active character-specific Universe | True | U | ≥1 Universe-U teammate(s) | `''` | Those Universe-U teammates only |
| **SC** — active workspace-shared canon (Class A) | True | NULL | ∅ | `''` | **Every legacy (universe=NULL) teammate in workspace** |
| **SD** — active Universe-shared canon (Class C) | True | U | ∅ | `''` | **Every teammate in Universe U** |
| **SE** — inactive operator-deleted | False | any | prior M2M preserved (whatever it was) | `'operator_delete'` | None (retrieval filters `is_active=True`) |
| **SF** — inactive orphan-archived | False | prior universe preserved | ∅ (by construction; CASCADE stripped it) | `'orphaned_by_teammate_delete'` | None |

**Load-bearing observations:**

- SC, SD, and SF all have `spokespeople=∅`. SC/SD are legitimate operator-chosen canon; SF is a side-effect of a teammate delete. Distinguishable only by `deactivated_reason` (SF is `'orphaned_by_teammate_delete'`; SC/SD are `''`) and by `is_active` (SC/SD are active; SF is inactive).
- SE preserves prior M2M (Slice 2 §22 refinement) — so its retrieval audience *would* be its prior audience if it were reactivated. SF has no such anchor.
- The "audience" for any active KD is fully mechanically determined by (universe, M2M). Empty M2M ALWAYS means "broadcast in current scope." The system does not carry a separate "intended audience" marker — it derives audience from state shape. This is the load-bearing overload.

## §32. Complete mutation inventory

Every code path today capable of transitioning a KD between the §31 states. Grouped by gesture; each row cites the file:line.

| # | Gesture | Endpoint / entry point | File:line | Payload | Product surface |
|---|---|---|---|---|---|
| M1 | Create paste — empty M2M, chose scope (universe or legacy) | `POST /api/knowledge/` | `shell/apps/embeddings/views.py:48` + `serializers.py:279-376` | `{workspace, universe, title, text_content}` (no `spokesperson_ids`) | **SPA** — `workspace/knowledge.tsx:292-297` paste form |
| M2 | Create paste — non-empty M2M | same | same | `{workspace, universe, title, text_content, spokesperson_ids:[...]}` | **SPA** — `spokesperson-ask-panel.tsx:620` citation-add flow |
| M3 | Create PDF / URL — same variants | same | `serializers.py:303-341` | `pdf_data_uri` / `source_url_input` variants | SPA + DRF |
| M4 | Attach one spokesperson | `POST /api/knowledge/<id>/attach/` | `views.py:133-144, 161-191` | `{spokesperson_id}` | **SPA** — `knowledge-panel.tsx:191-197` "Make {name}-only" |
| M5 | Detach one spokesperson | `POST /api/knowledge/<id>/detach/` | `views.py:146-159, 161-191` | `{spokesperson_id}` | **SPA** — `knowledge-panel.tsx:199-210` "Detach" |
| M6 | PATCH `title` | `PATCH /api/knowledge/<id>/` | `serializers.py:416-418` | `{title}` | DRF only (no SPA gesture besides M8) |
| M7 | PATCH `text_content` (in-place re-ingest) | same | `serializers.py:447-493` | `{text_content}` | **SPA** — `spokesperson-ask-panel.tsx:509-512` Beat 3 |
| M8 | PATCH `spokesperson_ids` | same | `serializers.py:499-500` | `{spokesperson_ids:[...]}` | **DRF only** — no SPA gesture today |
| M9 | PATCH `universe` (reassign / detach) | same | `serializers.py:425-445` | `{universe: <uuid \| null>}` | **DRF only** — no SPA gesture today |
| M10 | DELETE (soft) | `DELETE /api/knowledge/<id>/` | `views.py:110-129` | none | **SPA** — `workspace/knowledge.tsx:698-705` delete button |
| M11 | Ingestion revival on dedup hit | `POST /api/knowledge/` with duplicate content-hash | `ingestion.py:122-187` | same as M1/M2/M3 | via SPA create/citation-add |
| M12 | Teammate delete (single instance) | `Teammate.delete()` via `TeammateViewSet.destroy` or `Teammate.objects.get().delete()` | `spokespeople/signals.py:115-206` | none | **SPA** — spokesperson-delete-modal flow |
| M13 | Teammate delete (bulk) | `Teammate.objects.filter(...).delete()` or admin `delete_selected` | same signal path | none | admin / mgmt commands / tests |
| M14 | Django admin: change form save on KD | `/admin/embeddings/knowledgedocument/<id>/change/` | `apps/embeddings/admin.py:22-40` | edits `title, workspace, document_type, ingested_via, status, is_active, deactivated_reason, universe` | **admin only** — M2M NOT editable (see comment `admin.py:35-39`; `filter_horizontal` incompatible with explicit `through`) |
| M15 | Raw ORM / mgmt / shell | any `.update()`, `.save()`, `.set()`, `.through.objects.*`, raw SQL | anywhere | any | not operator; enforcement-boundary consideration only |

### §32.1 Surface counts

- **Operator-facing (SPA)**: M1, M2, M4, M5, M7, M10, M12.
- **DRF-only (no SPA gesture today)**: M6, M8, M9.
- **Admin-only**: M14.
- **Not operator, but must be considered for enforcement**: M11 (ingestion revival; already gated), M13 (bulk teammate delete; signal-covered), M15 (raw paths).

## §33. Transition matrix

For every mutation × starting-state × input variant, this table records: actual mutation, resulting state, retrieval-audience delta, whether any broadening was **explicitly** chosen by the operator gesture (strict — the gesture name and SPA copy must describe the broadening result), and whether the SESSION 275/276 invariant holds.

Legend for delta: `NARROW` (audience strictly smaller), `EQUAL` (unchanged set), `SHIFT` (different set of teammates, neither strictly smaller nor larger), `BROADEN` (audience strictly larger), `INACTIVE` (moves to SE/SF), `REVIVE` (moves out of SE/SF).

Explicit-intent column: `Y` (gesture semantically corresponds to the resulting audience shape) / `N` (gesture describes a smaller-scope action but produces broadening as a side-effect) / `n/a`.

| ID | From | Gesture | Input | Actual mutation | To | Δ | Explicit? | Invariant? | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| T1 | — | M1 create paste — legacy | `universe=None, sp=∅` | new KD `(True, None, ∅, '')` | **SC** | new | Y (chose legacy + no character = intent for legacy canon) | ✓ | `workspace/knowledge.tsx:292-297` |
| T2 | — | M1 create paste — Universe | `universe=U, sp=∅` | new KD `(True, U, ∅, '')` | **SD** | new | Y (chose Universe + no character = intent for Universe canon) | ✓ | same |
| T3 | — | M2 create citation-add | `universe=None or U, sp=[X]` | new KD `(True, universe, {X}, '')` | **SA/SB** | new | Y (chose character) | ✓ | `spokesperson-ask-panel.tsx:620` |
| T4 | **SC** | M4 attach(X) | `sp=X (legacy)` | `doc.spokespeople.add(X)` | **SA** | NARROW (all legacy → {X}) | Y ("Make X-only") | ✓ | `views.py:183`; `knowledge-panel.tsx:191-197` |
| T5 | **SD** | M4 attach(X) | `sp=X (universe-U)` | same | **SB** | NARROW | Y | ✓ | same |
| T6 | **SA** (count≥2) | M4 attach(Y) | | `.add(Y)` | **SA** (count+1) | NARROW-ish (still character-scoped, adds one more) | Y | ✓ | same |
| T7 | **SA** (count≥2) | M5 detach(X) | | `.remove(X)` | **SA** (count−1) | NARROW (or SHIFT if the removed teammate had matched a query the others don't) | Y ("Remove X from this doc's visibility") | ✓ | `views.py:185`; `knowledge-panel.tsx:199-210` |
| T8 | **SA** (count=1) | M5 detach(only-X) | | `.remove(X)` — M2M becomes ∅ | **SC** | **BROADEN** (was {X}; now every legacy teammate in workspace) | **N** — SPA copy "Detach" / "Remove X from this doc's visibility" describes removal, NOT broadcast intent. `views.py:152-158` docstring calls this "intentional" but the SPA UI copy at `knowledge-panel.tsx:206` reads *"Remove {name} from this doc's visibility"* — no warning, no confirm | **✗ FAILS** — operator gesture and resulting audience diverge | same |
| T9 | **SB** (count=1) | M5 detach(only-X) | | same | **SD** | **BROADEN** (was {X in U}; now every teammate in U) | **N** — same UI copy | **✗ FAILS** | same |
| T10 | **SC** | M8 PATCH `spokesperson_ids=[Y]` | | `.set([Y])` (Y must be workspace member) | **SA** | NARROW | Y (chose explicit set) | ✓ | `serializers.py:500` |
| T11 | **SA** (count≥1) | M8 PATCH `spokesperson_ids=[]` | | `.set([])` — M2M becomes ∅ | **SC** (or **SD** if universe=U) | **BROADEN** | **N** — no SPA gesture; DRF-only payload. `[]` on a REST payload is *literally* explicit-empty, but the API surface has no accompanying "confirm broadcast" contract or copy. From product intent, this is indistinguishable from a client sending `.set([])` in a script that meant "clear these attach rows" without understanding the broadcast side-effect | **✗ FAILS** (DRF-only today; no SPA path) | same |
| T12 | **SA** (count≥1) | M8 PATCH `spokesperson_ids=[Y,Z]` different | | `.set([Y,Z])` | **SA'** (different M2M) | SHIFT | Y | ✓ | same |
| T13 | **SC** | M9 PATCH `universe=U` | | `instance.universe = U`; preflight OK (M2M ∅) | **SD** | SHIFT (was every legacy; now every U member) | Y (chose new scope) | ✓ if operator intent was "assign to Universe U canon"; ✗ if operator thought "reassign" was a no-op semantically | `serializers.py:425-445` |
| T14 | **SD** | M9 PATCH `universe=None` | | `instance.universe = None`; preflight OK (M2M ∅) | **SC** | **BROADEN** (was every U member; now every legacy teammate in workspace, typically a larger pool) | **N** — no SPA gesture; DRF-only. Preflight only protects against M2M orphaning, not against audience broadening on empty-M2M canon | **✗ FAILS** (DRF-only) | `serializers.py:431-443` |
| T15 | **SD** | M9 PATCH `universe=B` (canon U→B) | | same; preflight OK | **SD'** (different U) | SHIFT | Y-ish (operator gestures reassignment; audience is a different set entirely) | ✓ if intentional; ✗ if not — hard to characterize without operator context | same |
| T16 | **SA** (count≥1, universe=U) | M9 PATCH `universe=None` | | preflight: M2M sp with universe=U ≠ None → **reject with 400** | (unchanged) | rejected | n/a | ✓ safe (preflight guard) | `serializers.py:435-443` |
| T17 | **SA** (count≥1, universe=None, sp legacy) | M9 PATCH `universe=U` | | preflight: legacy sp ≠ U → **reject with 400** | (unchanged) | rejected | n/a | ✓ safe | same |
| T18 | **SA** (count≥1, universe=U_A) | M9 PATCH `universe=U_B` | | preflight: sp universe=U_A ≠ U_B → **reject** | (unchanged) | rejected | n/a | ✓ safe | same |
| T19 | **SA/SB/SC/SD** | M10 DELETE | | `is_active=False, deactivated_reason='operator_delete'` — M2M UNTOUCHED (§Slice 2 §22 refinement) | **SE** | INACTIVE (audience becomes none; M2M preserved as anchor) | Y (chose delete) | ✓ | `views.py:110-129` |
| T20 | **SE** (any prior audience) | M11 ingestion revival — caller omits `spokesperson_ids` | | dedup hits SE; `is_active=True, deactivated_reason=''` — prior M2M preserved | back to prior state (SA/SB/SC/SD) | REVIVE — audience is prior audience | Y (re-ingest = "restore what was here") | ✓ | `ingestion.py:181-187` |
| T21 | **SE** | M11 ingestion revival — caller supplies `spokesperson_ids=[Y]` | | `is_active=True, reason=''`, M2M replaced with [Y] | new **SA/SB** | REVIVE (potentially SHIFT vs prior) | Y (explicit new attach) | ✓ | `ingestion.py:181-182` |
| T22 | **SF** (orphan) | M11 ingestion revival — caller omits `spokesperson_ids` | | dedup hits SF; **`OrphanRevivalRejected` at `ingestion.py:150-158`; HTTP 400** | (unchanged) | rejected | n/a | ✓ SESSION 275 §47 safe-revival gate | `ingestion.py:146-158` |
| T23 | **SF** | M11 ingestion revival — caller supplies `spokesperson_ids=[Y]` | | `is_active=True, reason=''`, M2M=[Y] | new **SA/SB** | REVIVE (explicit new audience) | Y | ✓ | `ingestion.py:181-182` |
| T24 | **SA** (count=1, {X}) | M12/M13 Teammate delete of X | | signal: `pre_delete` snapshot {KD.id}; CASCADE strips through-row; `post_delete` sees sp_count=0 → bulk-update `is_active=False, reason='orphaned_by_teammate_delete'` | **SF** | INACTIVE (SESSION 275 mechanism) | n/a (system action; operator gesture was "delete X") | ✓ | `signals.py:115-206`; SESSION 275 §42-§50 |
| T25 | **SA** (count≥2, includes X) | M12/M13 Teammate delete of X | | CASCADE strips Ruby↔KD; sp_count now ≥1 → post_delete does NOT archive | **SA** (count−1) | NARROW | n/a (system-driven; audience narrows safely) | ✓ (SESSION 275 §Slice 2 Case 2) | same |
| T26 | **SC/SD** (canon; X was never in M2M) | M12/M13 Teammate delete of X | | pre_delete snapshot does not include this KD; unchanged | **SC/SD** | EQUAL | n/a | ✓ (SESSION 275 §27 load-bearing) | same |
| T27 | **SA→SF** completed earlier; later Y deleted (Case 3) | M12/M13 | | Y was final surviving member (after earlier Ruby delete); post_delete archives (already covered by T24 pattern for Y) | **SF** | INACTIVE | n/a | ✓ | Slice 2 §16.Case-3 |
| T28 | **SF** | M14 admin: `is_active=True` (edit form) | | model.save with `is_active=True`, reason unchanged (still `'orphaned_by_teammate_delete'`) | active but reason still stamped — inconsistent state (`is_active=True, reason='orphaned_by_teammate_delete', M2M=∅`) | **REVIVE + BROADEN** (retrieval predicate sees active + empty M2M → broadcast in scope) | **N** — admin form has no "confirm broadcast" contract; admin can silently reactivate | **✗ FAILS** — admin bypass (Slice 1 §5.2, Slice 2 §19.1 row 7) | `apps/embeddings/admin.py:22-40` |
| T29 | **SF** | M14 admin: `is_active=True` **and** clear `deactivated_reason` | | both fields written; M2M unchanged (admin cannot edit M2M) | active `(True, universe, ∅, '')` — indistinguishable from SC/SD canon | **REVIVE + BROADEN** | **N** — admin has no audience-selection gesture | **✗ FAILS** — admin bypass | same |
| T30 | **SA/SB/SC/SD** | M14 admin: `universe` swap | | model.save with new universe FK | analogous to T13/T14/T15 but bypasses serializer preflight | may SHIFT/BROADEN | **N** — admin has no gesture describing audience change | **✗ FAILS** if the swap broadens; ✓ if not | same |
| T31 | **any** | M15 raw `KnowledgeDocument.objects.filter(...).update(is_active=True)` | | direct SQL UPDATE; bypasses `save()`, `pre_save`, `clean()`, admin | any transition possible | any | n/a (not operator gesture) | **✗ FAILS** for all invariant-relevant transitions | anywhere |
| T32 | **any** | M15 raw `.spokespeople.set([])` etc. | | via manager; fires `m2m_changed` (`pre_add`/`pre_remove`/`pre_clear`) but the existing receivers at `signals.py:31,93` only guard `pre_add` for workspace/universe consistency — nothing observes `pre_clear` or `pre_remove` to detect "went to empty" | any | any | n/a | **✗ FAILS** | `apps/embeddings/signals.py` |

### §33.1 SPA-facing rows summarized

Of the 32 transition rows above, only these have an operator-facing SPA gesture:

- Safe / correct: T1, T2, T3, T4, T5, T6, T7, T19, T24, T25, T26 (and T20-T23 via re-ingest from the SPA create paths).
- **Unsafe / operator gesture mismatches result**: **T8** (detach-final legacy → SC broadcast), **T9** (detach-final Universe → SD broadcast).

**T8 and T9 are the only operator-facing SPA gestures that violate the SESSION 275/276 invariant today.** Everything else that violates the invariant is DRF-only (T11, T14, T15), admin-only (T28, T29, T30), or bypass-class (T31, T32).

## §34. Retrieval consequence per resulting state

Cross-reference §31 × §33. Every resulting active state has one of four retrieval audiences:

- **SA** → `spokesperson.workspace = KD.workspace AND KD.universe IS NULL AND KD.spokespeople ∋ spokesperson` → the specific legacy teammates in the M2M.
- **SB** → `spokesperson.workspace = KD.workspace AND KD.universe = spokesperson.universe AND KD.spokespeople ∋ spokesperson` → the specific Universe-U teammates.
- **SC** → `spokesperson.workspace = KD.workspace AND KD.universe IS NULL AND KD.spokespeople IS NULL` (retrieval predicate emits `spokespeople__isnull=True`) → **every legacy (universe=NULL) teammate in the workspace**.
- **SD** → `spokesperson.workspace = KD.workspace AND KD.universe = spokesperson.universe AND KD.spokespeople IS NULL` → **every teammate in Universe U**.

Inactive states (SE, SF) never retrieve — the `document__is_active=True` filter at `retrieval.py:196` gates them out.

Predicate source: `apps/embeddings/retrieval.py:194-224`.

## §35. Explicit-vs-implicit operator-intent classification

Definition applied here: an operator gesture is **explicit** for a resulting audience shape iff (a) the SPA copy for that gesture describes the resulting audience, or (b) the API contract requires an audience-selection payload for the resulting audience. Both conditions must be true for SPA gestures; for DRF-only gestures the caller must supply the audience payload with knowledge of the resulting shape.

Applying to §33:

- **Explicit → correct match:** T1, T2, T3, T4, T5, T6, T7, T10, T12, T19, T20, T21, T23. Also T13 for the "assign to Universe U" narrative.
- **System action, no operator gesture ambiguity:** T24, T25, T26, T27 (signal-driven; SESSION 275 covers).
- **Implicit → mismatch, produces broadening:** T8, T9 (SPA), T11, T14 (DRF), T28, T29, T30 (admin), T31, T32 (bypass).

## §36. Adversarial composition analysis (§37 in preamble; renumbered here)

### §36.1 Compositions where two individually-valid semantics combine to broaden audience

- **T8 = SA + M5** — detach the sole spokesperson via SPA. Documented in `views.py:152-158` as "intentional semantics." Under the SESSION 275/276 invariant this is a broadening side-effect masked by "removal" copy.
- **T11 = SA + M8 `spokesperson_ids=[]`** — DRF PATCH. Semantically identical outcome to T8. No SPA gesture; DRF-only. An external client sending `.set([])` to "reset attachments" produces broadcast.
- **T14 = SD + M9 `universe=None`** — DRF PATCH. Preflight passes because the M2M is empty (Class C canon). Universe-scoped canon becomes legacy-workspace canon; audience broadens across the (typically larger) legacy pool. Operator gesture is "reassign scope"; no gesture describes "expand to workspace-wide."
- **T28–T30 = SF/SE + M14 admin** — admin can bare-flip `is_active=True` (and clear `deactivated_reason`) without any audience-selection payload. Independent of SESSION 275's signal because the signal fires only on Teammate delete, not on KD state changes.
- **Sequential composition** — an operator can (a) M8 PATCH `spokesperson_ids=[Y]` (narrow to Y), then (b) M8 PATCH `spokesperson_ids=[]` (broaden). Each step passes serializer validation individually. Composition produces broadening without an intervening "confirm broadcast" gesture. Same shape for T11/T14.
- **Universe removal on canon after user delete** — orthogonal composition, not investigated here: if `KnowledgeDocument.created_by` is SET_NULL on user delete and admin later PATCHes `universe=None`, no signal or invariant catches the audience broadening.

### §36.2 Compositions where clearing one scoping primitive causes another implicit scope to take over

- Clearing M2M (T8, T11) → *universe* becomes the sole scoping primitive → broadcast in universe scope.
- Clearing universe on canon (T14) → *workspace + M2M-empty broadcast fallback* becomes the sole scoping primitive → broadcast in legacy pool.

Both are examples of the same root: **audience is derived from the negation of scoping primitives, so removing one exposes broader scoping.** Any operation that clears one primitive on a canon-shape KD produces broader retrieval by construction.

### §36.3 API actions whose names describe removal but whose resulting state implies sharing

- `POST /api/knowledge/<id>/detach/` — name = "detach." Resulting state on count=1 KD = broadcast. Mismatch flagged in T8, T9.
- `PATCH spokesperson_ids=[]` — name = "set to empty list." Same semantic as detach-final. Same mismatch (T11).
- Admin change form → change `is_active` — name = "toggle active." Resulting state on SF = broadcast if reason coincidentally aligns. Mismatch (T28).

## §37. Answers to Slice 3 A-J

### A. Is `detach final spokesperson` the only remaining live operator path that can unintentionally broaden audience?

**No.** The operator-facing SPA path is T8/T9 (detach-final). But three other classes exist:

- **DRF-only** — T11 (`PATCH spokesperson_ids=[]` on active KD), T14 (`PATCH universe=null` on canon), T15 (`PATCH universe=B` on canon — SHIFT rather than strict BROADEN, but audience-set changes without an explicit intent gesture).
- **Admin** — T28, T29, T30 (bare reactivation / clear-reason / universe-swap on any KD).
- **Bypass** — T31, T32 (raw `.update()` / raw M2M manipulation).

Slice 3 does not investigate raw paths as operator gestures (per task instruction) but records them for enforcement-boundary analysis.

### B. Does `PATCH spokesperson_ids=[]` create the same semantic problem through a different route?

**Yes.** T8 and T11 produce identical resulting states via different endpoints. Semantic equivalence confirmed. No SPA gesture exists for T11 today; it is a DRF-only affordance, but any external caller (curl, scripts, third-party client, Python management command) can trigger it. The invariant should not depend on the SPA being the only client.

### C. Can changing or clearing `universe` broaden an audience without an explicit broadening decision?

**Yes** — T14 (universe→None on Class C canon) broadens to Class A workspace canon. The serializer preflight (`serializers.py:431-443`) only protects against **M2M orphaning** (cross-Universe attach rows becoming impossible), not against audience broadening on empty-M2M canon. T15 (Universe A → B on canon) is a lateral audience SHIFT — neither broaden nor narrow but not what the operator gesture "reassign" would imply if they thought about it. No preflight guards either transition on canon.

### D. Are there any transitions where `operator_delete` revival silently restores or changes audience incorrectly?

**No.** T20 (revive without new payload) preserves the prior M2M — audience is restored to what it was, not broadened. T21 (revive with explicit new spokesperson_ids) replaces — audience is explicitly chosen. Both branches are safe. The operator gesture (re-ingest same content) explicitly means "restore or replace this document"; the ingestion path implements exactly that.

**But note:** SE could reach an ambiguous state if the operator deleted a character-specific KD (SA→SE) and then later deleted the sole surviving spokesperson via M12 while the KD was inactive. Does the Teammate `pre_delete` signal find the SE KD in its snapshot? Reading `signals.py:149-154` — the query is `KnowledgeDocumentSpokesperson.objects.filter(teammate=instance).values_list("knowledgedocument_id", flat=True)`. Through-rows for an SE KD survive (only KD.is_active changes, not the M2M rows). So yes — the pre_delete signal WOULD snapshot the SE KD. `post_delete` at `signals.py:186-192` runs `.filter(pk__in=kd_ids, is_active=True).annotate(sp_count=Count("spokespeople")).filter(sp_count=0)`. SE has `is_active=False` — so `.filter(is_active=True)` excludes it, and no archive-write fires. The through-row is CASCADE-cleared silently. SE's M2M anchor is lost. On later revival (T20), the anchor no longer exists — SE becomes indistinguishable from SF but without the `orphaned_by_teammate_delete` marker, and T20's "preserve prior M2M" restores an empty set. **This is a latent hole:** an operator-deleted KD whose sole surviving spokesperson is later deleted **loses its M2M anchor silently and can be revived into a broadcast state without triggering the OrphanRevivalRejected gate** (because reason stays `'operator_delete'`, not `'orphaned_by_teammate_delete'`). Slice 3 records this as a new adversarial variant not covered by SESSION 275 or Slice 2.

### E. Are there any transitions where current ingestion revival semantics differ from direct API mutation semantics?

**Yes.** Three different postures for the same logical "revive an inactive KD" transition:

1. Ingestion (M11): safe-gated for `orphaned_by_teammate_delete` via `OrphanRevivalRejected`. Preserves prior M2M for `operator_delete`. Explicit new-audience acceptance path.
2. DRF PATCH (M6-M9): `get_queryset` filter at `views.py:70` makes inactive KDs unreachable → 404. Coincidental seal per Slice 1 §5.3 / Slice 2 §19.1. If the queryset filter is ever relaxed (Slice 2 §21.4 archived-visibility case), this seal disappears silently.
3. Admin (M14): unguarded. Can flip `is_active`, clear `deactivated_reason`, and change universe with no audience-selection payload.

Three different enforcement postures for the same logical revive-transition is exactly the composition-failure pattern Slice 2 §19.5 predicted.

### F. Does the current API possess an explicit representation of "I intentionally want this knowledge to be workspace-shared"?

**No.** Workspace-shared is a *shape*: `(is_active=True, universe=NULL, spokespeople=∅, deactivated_reason='')`. No positive marker. The SPA create-paste form (`workspace/knowledge.tsx:292-297`) is the closest thing to an explicit gesture: the operator picks "legacy" in the UniverseScopePicker AND does not add any character. That combined gesture creates SC. But after creation, the shape is identical to any other empty-M2M legacy KD, including one reached via detach-final (T8) or PATCH-empty (T11). The intent-at-creation is not preserved.

### G. Does the current API possess an explicit representation of "I intentionally want this knowledge to be Universe-shared"?

**No.** Same shape (`universe=U, spokespeople=∅`); no positive marker; SPA gesture is "pick Universe + no character at create." Same intent-erasure post-creation.

### H. Which transitions are currently safe because they narrow audience, even if historical provenance is lost?

- **T4/T5** (attach on canon → character-scoped) — narrows explicitly.
- **T6** (attach adding to existing character-scoped M2M) — narrows character set.
- **T7** (detach with count≥2) — narrows character set.
- **T10** (PATCH `spokesperson_ids=[non-empty]` on canon) — narrows explicitly.
- **T25** (Teammate delete when KD had ≥2 spokespersons) — narrows audience; loses the deleted teammate's identity but the remaining M2M is a valid audience.
- **T26** (Teammate delete of unrelated character on canon) — unchanged; SESSION 275 §27.

None of these produce audience broadening; provenance loss (e.g., no longer knowing Ruby used to be a spokesperson in T25) is a *separate* concern addressed by Slice 2 §18.

### I. Which transitions require an explicit confirmation/gesture that does not exist today?

- **T8** (detach-final on SA) — SPA has no confirmation dialog. Would need a "This will make it visible to every legacy teammate — continue?" style gate, OR a positive workspace-shared marker gesture the operator picks affirmatively.
- **T9** (detach-final on SB) — same, for Universe canon.
- **T11** (PATCH `spokesperson_ids=[]`) — DRF only; would need either an explicit `{"audience": {"scope": "workspace_shared"}}` payload, or a rule refusing empty set on active KDs unless a broader-scope-intent flag is provided.
- **T14** (PATCH `universe=None` on SD canon) — same shape; needs explicit "broaden to legacy pool" acceptance.
- **T15** (Universe A → B on SD canon) — needs explicit reassign-audience acceptance.
- **T28-T30** (admin bypass) — admin needs either read-only lock on `(is_active, deactivated_reason, universe)` for affected states, or a `save_model` gate that requires an audience-selection accompanying any transition into an active empty-M2M shape.
- **The D-latent variant** (operator-deleted KD whose sole spokesperson is later deleted) — needs the SESSION 275 signal to also inspect inactive KDs and either archive-with-orphan-reason or preserve-with-tombstone. Neither is implemented today.

### J. Nature of the problem?

Given the completeness of A-I, the evidence supports this classification:

**The problem is neither isolated endpoint bugs nor merely inconsistent transition semantics. It is the absence of a first-class audience representation.**

Root cause: **audience is derived by negation** — "no spokesperson attached AND no universe scope" ⇒ broadcast; "no spokesperson attached AND universe=U" ⇒ Universe broadcast. Any operation that clears one scoping primitive on a canon-shape KD exposes broader scoping *by construction*. Every fix that tries to catch these operations after the fact is a per-endpoint reimplementation of the same "was this an explicit audience gesture?" check — SESSION 275 built one for Teammate delete; Slice 2 proposed another for orphan revival; Slice 3 identifies four more classes (T8/T9 SPA, T11 DRF, T14/T15 DRF, T28-T30 admin, and the D-latent variant). Each new fix increases per-endpoint reasoning debt.

The evidence-forced framing:

- SESSION 275's signal was necessary and sufficient for the *removal-side* leak it addressed.
- Slice 2's Layer 1 + Layer 2 is necessary and sufficient for the *orphan-revival* leak.
- **Neither addresses the general audience-broadening class** because both key on `deactivated_reason`, which is only set on archive. Active-KD state transitions (T8, T9, T11, T14, T15) never touch `deactivated_reason`.
- A general fix requires either (i) per-endpoint gates for every remaining path (five distinct manifestations enumerated) plus perpetual vigilance against new manifestations, or (ii) a first-class `KnowledgeAudience` state (Option C in SESSION 275 §36 / Slice 2 §25) that makes canon a positive marker.

Option (ii) is not evidence-*forced* in the sense that Option (i) is impossible — it is possible. But the pattern-recurrence evidence from SESSION 275 → Slice 2 → Slice 3 (three consecutive sessions, each finding a new manifestation of the same root) is strong indication that continuing with per-endpoint gates will produce Slice 4, Slice 5, Slice N with the same shape. Slice 3 records this pattern as the strongest evidence-based argument for Option C available today; the promotion from "cleaner" to "necessary" remains **Chris's product decision** and is not asserted by Slice 3.

## §38. Provenance conclusion re-check

Slice 2 §18.1 conclusion:

> **Required:** deleted teammate name (+ already-durable KD/workspace/reason/timestamp).
> **Useful:** deleted teammate id, universe_id, actor.
> **Not required:** prior M2M snapshot, narrowing-event history.

Slice 3 transition matrix findings vs. this conclusion:

- **T24** (Teammate delete → SF): unchanged from Slice 2. Deleted teammate name remains the only REQUIRED provenance.
- **T25** (narrowing delete): Slice 3 confirms no provenance is required for narrowing — no recovery decision is triggered.
- **§37 D-latent** (SE + Teammate delete of sole surviving spokesperson): would produce an SE row whose M2M anchor is silently cleared. If it later revives (T20) with an operator expecting the prior audience, the audience is empty → broadcast. **New provenance implication:** either (a) the signal should treat SE KDs symmetrically with SA — snapshot + archive-transition even when the KD is inactive (with a new reason such as `'orphaned_by_teammate_delete_while_deleted'`), or (b) the D-latent variant needs a separate remedy. If (a), the "deleted teammate name" provenance requirement extends to SE-inactive KDs too. Same shape; no new REQUIRED field.
- **T14 (canon universe removal)** and **T8/T9 (detach-final)**: no provenance is needed because no archive occurs; the invariant question is enforcement, not provenance.

**Slice 2 conclusion holds unchanged.** Deleted teammate NAME is REQUIRED and remains the sole REQUIRED provenance field. The transition matrix does not falsify this. The D-latent variant expands the *scope* over which the same provenance rule should apply, not its content.

## §39. Slice 2 enforcement proposal re-check

Slice 2 §20.1 proposed a Layer 1 + Layer 2 composite:

- **Layer 1**: DB CHECK constraint `NOT (is_active=true AND deactivated_reason='orphaned_by_teammate_delete')`.
- **Layer 2**: Python `clean()` / `pre_save` extension enforcing clearing `deactivated_reason` from ORPHANED_BY_TEAMMATE_DELETE requires non-empty M2M.

Tested against the §33 transition matrix:

| Transition | Layer 1 catches? | Layer 2 catches? | Slice 2 proposal outcome |
|---|---|---|---|
| T22 (orphan revival without new sp — ingestion) | already gated by `OrphanRevivalRejected` | already gated | ✓ (already sealed pre-Layers) |
| T28 (admin: flip `is_active=True`, leave reason) | **yes** — CHECK constraint fails at commit | n/a | **sealed by Slice 2** |
| T29 (admin: flip `is_active=True` AND clear reason) | fails (both flip together) | Layer 2 catches — clearing reason requires new M2M | **sealed by Slice 2 (composite)** |
| T31 (raw `.update(is_active=True, deactivated_reason='orphaned...')` — implausible; scripts unlikely to explicitly stamp orphan reason but leave active) | **yes** — CHECK constraint | n/a | **sealed** |
| T31' (raw `.update(is_active=True)` on SF, leaving reason as-is) | **yes** — CHECK | n/a | **sealed** |
| T31'' (raw `.update(deactivated_reason='')` on SF, then later flip `is_active=True`) | catches only the final state, not the intermediate `.update()` | Layer 2 not fired by `.update()` (bypass) | **residual hole** — Slice 2 §24 point 4 already recorded this |
| **T8** (detach-final SPA on SA → SC) | **no** — SC has `deactivated_reason=''`; the CHECK is satisfied | **no** — no `deactivated_reason` transition involved | **NOT sealed** |
| **T9** (detach-final Universe → SD) | **no** | **no** | **NOT sealed** |
| **T11** (PATCH `spokesperson_ids=[]` on SA) | **no** | **no** | **NOT sealed** |
| **T14** (PATCH `universe=None` on SD) | **no** | **no** | **NOT sealed** |
| **T15** (Universe A → B on SD) | **no** | **no** | **NOT sealed** |
| **T30** (admin: universe swap on canon) | **no** | **no** | **NOT sealed** |
| **§37 D-latent** (SE + Teammate delete of sole sp → M2M silently cleared) | **no** (SE stays inactive; CHECK is about active) | **no** (no reason transition) | **NOT sealed** |

### §39.1 Verdict on Slice 2 proposal

**Slice 2 Layer 1 + Layer 2 is sufficient for the specific case it was scoped to (orphan revival) but does NOT constitute a general audience-safety boundary.** Six distinct classes of transition violating the SESSION 275/276 invariant remain uncovered: T8, T9 (SPA), T11 (DRF), T14, T15 (DRF), T30 (admin universe), and the §37 D-latent variant.

Layer 1 correctly seals the specific "flip `is_active=True` while `deactivated_reason` still says orphan" bypass. Layer 2 correctly seals "clear reason without new M2M." Both are correct *within their scope*. Neither generalizes because both key on `deactivated_reason` — a field that is not touched during active-KD transitions (T8/T9/T11/T14/T15/T30).

`deactivated_reason` is therefore the **correct authoritative state only for the archive-cause distinction**, not for the full audience invariant. The full invariant needs either (a) per-endpoint gates repeating the "explicit audience?" reasoning at every mutation surface, or (b) a first-class audience field the retrieval predicate can key on positively rather than by negation.

### §39.2 Does any Slice 2 proposal accidentally reject Class A / Class C canon?

**No.** Layer 1 keys on `(is_active=True AND deactivated_reason='orphaned_by_teammate_delete')`; canon has `deactivated_reason=''` and satisfies the constraint. Layer 2 keys on the transition of `deactivated_reason` FROM `'orphaned_by_teammate_delete'`; canon never had that value. Canon is preserved by construction under Slice 2's proposal. This finding is unchanged from Slice 2 §20.2 and re-verified.

## §40. Prediction vs evidence

| Prediction (§30) | Evidence |
|---|---|
| 1. detach-final and PATCH `spokesperson_ids=[]` semantically equivalent | **Confirmed** — T8 vs T11. Same resulting state, same audience delta. Only difference is endpoint (SPA-facing vs DRF-only) |
| 2. Universe removal creates implicit broadening on canon | **Confirmed** — T14 (SD → SC broadens); T15 (SD → SD' shifts). Preflight only guards against M2M orphaning |
| 3. Slice 2 Layer 1 + Layer 2 sufficient for the *general* invariant | **Falsified** — sealed only orphan-revival specific transitions (T22, T28, T29, T31'). Did NOT seal T8, T9, T11, T14, T15, T30, D-latent. Sufficient for its scoped case; not a general boundary. §39 records the falsification explicitly |
| 4. Explicit "workspace-shared" gesture exists today | **Confirmed absent** — SC/SD are shape-inferred, not marked. §37.F |
| 5. Transition audit provides evidence that first-class KnowledgeAudience is *necessary* rather than merely *cleaner* | **Partial** — the audit provides evidence that per-endpoint gating for T8, T9, T11, T14, T15, T30, D-latent would each be a distinct instance of the same pattern SESSION 275 and Slice 2 already implemented twice. Three consecutive sessions producing new manifestations of the same root is *strong pattern evidence*, not *mathematical necessity*. Option (i) per-endpoint gates is still possible in principle; Option (ii) KnowledgeAudience is not evidence-forced but is evidence-favored. Chris product decision |

Additionally discovered during the audit but not predicted:

- **§37.D D-latent variant** — operator-deleted KD whose sole surviving spokesperson is later deleted. The Teammate `pre_delete` signal snapshots the through-row; `post_delete`'s `is_active=True` filter (`signals.py:188`) excludes SE KDs; through-row is CASCADE-cleared silently; SE loses its M2M anchor without an archive marker. On later T20 revive, prior M2M is empty → broadcast. Not covered by SESSION 275, not by Slice 2, not by Slice 3's Layer 1/Layer 2 test above. **New evidence.**

## §41. Unresolved questions

Carried from Slice 2 §24 (still open):

- (§24.1) Storage shape for deleted-teammate identity — Direction Alpha vs Direction Beta.
- (§24.2) Whether to record deleted teammate id / universe / actor beyond REQUIRED name.
- (§24.3) Actor capture at signal time.
- (§24.4) Residual `.update(deactivated_reason="")` hole.
- (§24.5) Known-permitted `detach → empty` gesture (T8, T9) — now upgraded from "flagged latent hole" to "primary SPA-facing invariant violation."
- (§24.6) Whether to record narrowing events.
- (§24.7) `source_metadata` reuse for lifecycle events.
- (§24.8) Bundle vs split — still awaiting Chris.

New from Slice 3:

- (§41.9) **§37.D-latent — operator-deleted KD whose last surviving spokesperson is later deleted.** Should the Teammate `pre_delete`/`post_delete` signal pair also update SE KDs to a distinct state (e.g. `deactivated_reason='orphan_pending_from_operator_delete'`), or should this remain untreated because SE is already inactive and no immediate leak occurs? Note: leak DOES occur on later T20 revive.
- (§41.10) **Is per-endpoint gating (Option i) or first-class KnowledgeAudience (Option ii) the right general fix?** Slice 3 records the evidence pattern but does not commit. Chris product decision.
- (§41.11) **If Option ii, migration story.** A new `KnowledgeAudience` field/model would need a backfill for all existing KDs (the 9 legacy + Ruby's C/D + every other production KD). Backfill logic itself becomes an audience-decision surface subject to the same invariant. Not designed here.
- (§41.12) **If Option i, minimum first three gates.** SPA T8/T9 (add confirm dialog + optionally rewrite copy to "Make workspace-shared" instead of "Detach"), DRF T11 (reject empty payload without explicit intent field), admin T28-T30 (readonly lock on affected fields). Each is a ½-slice; ordering follows from operator-facing priority.
- (§41.13) **T15 characterization** — is Universe swap on canon (A → B) a broadening or a shift? Depends on |members(A)| vs |members(B)|. Product intent question: does the "reassign scope" gesture cover audience shift, or is it distinct from an audience gesture?

## §42. Recommendation

**Do not implement anything in Slice 3.** The audit's job was to build the complete transition matrix (§33), test Slice 2's proposal against it (§39), and identify whether the general invariant needs a different fix (§37.J, §40 prediction 5). Both are established.

Two directional readings the evidence supports (**not** recommendations until Chris chooses):

- **Direction Gamma — per-endpoint gates (Option i).** Add discrete confirmations / gates for T8/T9 (SPA copy + confirm dialog), T11 (DRF explicit-intent payload), T14/T15 (DRF explicit-scope-broaden payload), T28-T30 (admin readonly locks or `save_model` gate), D-latent (extend Teammate signal to SE KDs). Each is a small independent ½-slice. Same-shape reasoning re-implemented at each surface. Sustainable but growing debt as new mutation surfaces land.
- **Direction Delta — first-class audience (Option ii, Option C from SESSION 275 §36).** Introduce a positive `KnowledgeDocument.audience_scope` field (choices: `character | universe | workspace`) — or a companion model — that the retrieval predicate keys on positively. Empty M2M without an explicit audience marker no longer means broadcast; broadcast requires the marker. Retrieval predicate change becomes a single invariant boundary. Migration cost: backfill decisions for every existing KD. Larger scope; solves the pattern rather than the manifestation.

Direction Gamma is faster and more incremental. Direction Delta is a genuine schema/retrieval-invariant change that will affect the SESSION 274 P2-lite / composition-observability arcs. The evidence is not mathematically forcing; the *pattern of repeated slice discovery* is the strongest argument for Direction Delta.

**Slice 2 Layer 1 + Layer 2 proposal remains valid for the orphan-revival scope it was defined for.** If Chris chooses Direction Gamma, Slice 2 Layer 1 + Layer 2 becomes one of the gates (the orphan-revival one). If Chris chooses Direction Delta, Slice 2 Layer 1 + Layer 2 becomes superseded (audience field owns the invariant; reason field owns only the archive-cause distinction).

**Current schema remains sufficient for the small safe recovery workflow** (Slice 1 §5.6, Slice 2 §25 restated). Nothing in Slice 3 falsifies that. What is still missing: general audience invariant enforcement across all surfaces.

## §43. Explicit decision gate

**STOP.** Slice 3 does not authorize any code, migration, DB row, admin, or SPA change.

Before Slice 4 begins, Chris must decide:

1. **Direction Gamma vs Delta** (§42). Per-endpoint gates or first-class audience marker.
2. If **Gamma**: ordering across the 5-6 remaining manifestations (T8/T9 SPA first? T11 DRF? T14/T15 DRF? Admin bypass? D-latent?).
3. If **Delta**: is Slice 4 the design slice, or does Chris want a Slice 3.5 that specifies the audience-field shape + migration semantics first?
4. **§41 residuals** — each is a discrete decision (D-latent, `.update()` residual, T15 characterization, provenance storage from Slice 2, etc.).
5. **Bundle vs split** (still open from Slice 1 §8, Slice 2 §24.8, §41).

Chris's answers determine Slice 4 scope. Slice 4 must open with a design/plan section, not implementation — same pattern as SESSION 275 §21-§38, Slice 1 §10, Slice 2 §26.

## §44. Smallest falsifiable next questions

Continuing the Q-276-N numbering from Slice 2 §27.

- **Q-276-10.** *If the SPA detach button's copy at `knowledge-panel.tsx:206` is changed on the last-detach case to "This will make {title} visible to every legacy teammate in the workspace — continue?" (with a confirm-dialog gate), does the SPA test suite still pass?* Falsifiable — the smallest T8-only fix under Direction Gamma. Isolates SPA copy from any backend change.
- **Q-276-11.** *If the DRF endpoint `PATCH /api/knowledge/<id>/` rejects `spokesperson_ids=[]` unless the payload also includes an explicit `{"audience_intent": "workspace_shared" | "universe_shared"}` field, does any existing test / caller break?* Falsifiable — the smallest T11-only fix.
- **Q-276-12.** *If Direction Delta is chosen, what does a backfill decision look like for the 9 legacy KDs?* Falsifiable by attempting a backfill classification using Slice 1 §4.4 evidence: TANK/Tulsi/Riggs each get an explicit decision by Chris; the 6 Hearth & Hollow rows require operator classification. This is a *pre-Slice-4* product question — the migration story for Direction Delta necessarily surfaces the legacy-remediation question that Slice 1 identified.
- **Q-276-13.** *Does the D-latent variant (§37.D) actually manifest in practice?* Falsifiable by tracing whether Chris's workspace has any operator-deleted KD with a since-deleted sole surviving spokesperson. Read-only DB query; not implemented.
- **Q-276-14.** *Under Direction Delta, is the retrieval predicate change purely additive (`AND audience_scope IN {allowed}`) or does it require also removing the current empty-M2M-broadcast fallback?* Falsifiable by writing the new predicate on paper and testing against the §31 truth table. Design work; no code required.
- **Q-276-15.** *Under Direction Gamma, does closing all six manifestations produce a coherent operator model, or does it produce six independent gates that operators have to learn separately?* Falsifiable by writing the SPA copy + DRF error messages for all six and reading them end-to-end. Product/UX judgment.

Each is ½-slice or less. None require touching production data or code.

## §45. Slice 3 checklist

- [x] Re-verify baseline against Slice 2 close (§29 preamble)
- [x] Slice 3 falsifiable question stated (§29)
- [x] Predictions before evidence (§30)
- [x] State model derived from actual behavior — 6 states SA-SF (§31)
- [x] Complete mutation inventory (§32) — 15 mutation classes; operator-facing / DRF-only / admin / raw split
- [x] Complete transition matrix (§33) — 32 rows with actual mutation + result + delta + explicit-intent + invariant + evidence
- [x] Retrieval consequence per resulting state (§34)
- [x] Explicit-vs-implicit operator-intent classification (§35)
- [x] Adversarial composition analysis (§36)
- [x] Answer to A — detach-final is not the only path (§37.A)
- [x] Answer to B — PATCH `sp_ids=[]` semantic equivalent (§37.B)
- [x] Answer to C — Universe changes broaden on canon (§37.C)
- [x] Answer to D — operator_delete revival safe except D-latent variant (§37.D)
- [x] Answer to E — three different revival postures (§37.E)
- [x] Answer to F — no explicit workspace-shared marker (§37.F)
- [x] Answer to G — no explicit Universe-shared marker (§37.G)
- [x] Answer to H — narrowing transitions safe (§37.H)
- [x] Answer to I — transitions requiring explicit gesture (§37.I)
- [x] Answer to J — nature of the problem (§37.J)
- [x] Provenance conclusion re-check — Slice 2 conclusion holds; D-latent expands scope not content (§38)
- [x] Slice 2 enforcement proposal re-check — sealed 4-of-14 transitions; NOT sealed 6-of-14 uncovered classes (§39.1)
- [x] Class A/C canon preservation under Slice 2 proposal verified (§39.2)
- [x] Prediction vs evidence table (§40)
- [x] Unresolved questions carried forward + new (§41)
- [x] Recommendation — Direction Gamma vs Delta, no implementation (§42)
- [x] Explicit decision gate (§43)
- [x] Smallest falsifiable next questions Q-276-10..15 (§44)
- [x] Zero KD rows mutated; zero migrations; zero admin/SPA/serializer/signal/retrieval changes; zero legacy KD remediation; zero detach "fixes"; zero provider spend; working tree change limited to this document
- [ ] Chris + ChatGPT review + Slice 4 scoping decision (§43)

---

**End of SESSION 276 Slice 3 read-only audit. STOP before implementation. Awaiting Chris + ChatGPT review on §42 recommendation (Direction Gamma vs Delta), §43 decision gate, and §44 next questions.**

---

# SESSION 276 — Slice 4 read-only design / falsification audit: Direction Delta first-class audience

**Status.** READ-ONLY design + falsification + migration-semantics audit. Continued from Slice 3. Direction Delta authorized for INVESTIGATION only. No code, migration, DB row, admin, SPA, model, retrieval, signal, serializer, or provider behavior modified during this slice.

**Slice 4 baseline.** `main == origin/main == d4754737`. Doc pre-Slice-4 append length: 1358 lines. 9 chriss-workspace KDs unchanged; Ruby Class C/D unchanged; migration `0006` applied; signal pair + revival gate intact; services healthy. Slice 3 conclusions carried forward.

**Load-bearing invariants carried forward:**

- SESSION 275 §23 + Slice 2 §21 corollary + Slice 3 restated: *a removal, deletion, detach, recovery, migration, or other lifecycle action must never broaden the audience of surviving knowledge unless the operator explicitly chooses that broader audience.*
- **Task-added migration invariant:** *a migration must not turn ambiguous existing knowledge into a broader audience merely because its current physical row shape resembles intentional shared canon.* This forbids blanket-migrating `(empty M2M, universe NULL)` → `WORKSPACE` without surviving evidence.

## §46. Slice 4 falsifiable question

> Can Character OS introduce a first-class `KnowledgeDocument` audience representation that replaces empty-M2M broadcast semantics **without changing the effective audience of any currently well-classified `KnowledgeDocument`**, while safely quarantining or requiring explicit operator decisions for rows whose intended audience is ambiguous?

Answered evidence-first; if evidence falsifies Delta's feasibility, this slice says so explicitly.

## §47. Predictions before evidence

Taken from Slice 4 task predictions verbatim, so §63 can score each:

1. A three-state `CHARACTER | UNIVERSE | WORKSPACE` audience field will be insufficient — orphan / unresolved rows need a fail-closed representation.
2. A four-state model including `NONE` / `UNRESOLVED` will cleanly separate lifecycle from audience.
3. Most existing KDs with non-empty M2M will migrate deterministically to `CHARACTER`.
4. Known intentional Universe canon like Ruby Class C will migrate deterministically to `UNIVERSE`.
5. The nine historical empty-M2M / no-Universe rows will prevent a blanket `WORKSPACE` backfill.
6. Delta will make the D-latent case easier to model — an inactive `CHARACTER` row whose final character disappears can transition to `NONE` (or become malformed-fail-closed) instead of implicit broadcast.
7. Retrieval can become fail-closed: unknown audience → no retrieval.
8. Delta will allow `deactivated_reason` to remain lifecycle / provenance rather than carrying audience-security semantics.
9. The migration can likely be staged rather than requiring a flag-day rewrite.

Compared against evidence in §63.

## §48. Lifecycle vs audience vs scope decomposition

Slice 3 §31 showed the current tuple `(is_active, universe, spokespeople, deactivated_reason)` conflates three orthogonal concepts:

| Concept | What it answers | Current field(s) | Delta separation |
|---|---|---|---|
| **Lifecycle** | *Is this KD in a state where retrieval should even consider it?* | `is_active` | keeps `is_active` (pure boolean: active vs inactive) |
| **Archive-cause provenance** | *Why is this KD inactive?* | `deactivated_reason` | keeps `deactivated_reason` (pure enum: `OPERATOR_DELETE` / `ORPHANED_BY_TEAMMATE_DELETE`; nothing else derived from it) |
| **Scope context** | *Where does this KD live?* | `workspace` + `universe` | keeps both FKs unchanged (workspace stays load-bearing anchor; Universe stays substrate FK per SESSION 261) |
| **Audience** | *WHO can retrieve this KD?* | derived by negation from `(universe, spokespeople)` — the load-bearing overload Slice 3 documented | **new positive field** `audience_scope` |

Answers to the sub-questions in the task:

- **Should `is_active` remain purely lifecycle?** Yes. Under Delta it flips only on operator delete or system orphan-archive; never carries audience semantics.
- **Should `deactivated_reason` remain purely archive-cause provenance?** Yes. Slice 2 Layer 1 + Layer 2 loaded it with audience-security enforcement; Delta removes that load. `deactivated_reason` becomes lifecycle metadata only.
- **Should audience remain meaningful while inactive?** Yes for `SE` (operator-deleted) — the pre-delete audience is the anchor for revival (Slice 2 §22 refinement). For `SF` (orphan-archived) audience becomes `NONE` — no surviving safe audience.
- **Is orphaned knowledge best modeled as audience state, lifecycle state, or both?** Both. Lifecycle = inactive; audience = `NONE` (fail-closed).
- **Is "unassigned" semantically different from "workspace-shared"?** Yes. `NONE` = fail-closed; `WORKSPACE` = intentional broadcast to workspace teammates.
- **Do we need an explicit `NONE` state?** Yes — for `SF`, for D-latent malformed rows, and (as `NULL` during migration only) for the 10 currently-ambiguous rows awaiting operator triage.
- **Does multi-character need a separate audience type?** No. `CHARACTER` with M2M ≥ 2 handles it. Multi-character is a shape variant of `CHARACTER`, not a distinct audience.
- **Can Universe-shared and character-specific-in-Universe coexist?** Yes. `audience_scope=UNIVERSE` with universe=U ignores M2M for retrieval; `audience_scope=CHARACTER` with universe=U requires M2M ≥ 1 and each M2M member must have `universe_id=U`. Both row shapes coexist in the same Universe cleanly.

## §49. Candidate audience models

### §49.1 Candidate 1 — three-state enum

```
audience_scope = {CHARACTER, UNIVERSE, WORKSPACE}
```

Row shapes:

- `CHARACTER`: M2M must be non-empty; universe may be NULL (legacy) or a Universe FK.
- `UNIVERSE`: universe must be non-NULL; M2M is irrelevant (typically empty; if non-empty, meaning is ambiguous).
- `WORKSPACE`: universe must be NULL; M2M is irrelevant.

**Falsified.** Fails against three cases:

- **`SF` orphan-archived** (Slice 3 §31): the row survives with M2M=∅, no Universe promotion decision. Under Candidate 1 the row has no valid `audience_scope` — every choice is a lie. Assigning `WORKSPACE` broadcasts to workspace teammates, `UNIVERSE` requires a Universe the row may not have, `CHARACTER` violates the shape rule.
- **D-latent** (Slice 3 §37.D): `SE` with `audience_scope=CHARACTER` whose sole M2M member is later deleted becomes `CHARACTER` + M2M=∅. Malformed. Candidate 1 has no fail-closed shape to hold this.
- **Legacy ambiguous rows during migration** (§55): the 10 rows cannot be blanket-migrated to `WORKSPACE` per Chris's task-added migration invariant. Candidate 1 has no valid non-broadcasting state.

### §49.2 Candidate 2 — four-state enum with fail-closed `NONE`

```
audience_scope = {CHARACTER, UNIVERSE, WORKSPACE, NONE}
```

Row shapes:

- `CHARACTER`, `UNIVERSE`, `WORKSPACE` — same as Candidate 1.
- `NONE`: retrieval never matches. Restricted to `is_active=False` rows (invariant §51 #4).

Solves all three Candidate 1 falsifications:

- `SF` orphan-archived → `audience_scope=NONE` + `is_active=False`.
- D-latent → same shape; can transition to `NONE` by extending Teammate signal to also process `SE` rows (or rely on retrieval fail-closed on malformed shape).
- Legacy ambiguous rows during migration → represented by `audience_scope IS NULL` during Stages 1–4 (§57), with retrieval compatibility fallback; transition to `NONE + is_active=False` OR to `CHARACTER/UNIVERSE/WORKSPACE` when operator classifies.

**Favored.**

### §49.3 Candidate 3 — companion `KnowledgeAudience` model

Separate row-per-KD `KnowledgeAudience(kd_id, scope, universe_id, spokesperson_ids_json, decided_by_user_id, decided_at, ...)`.

Rejected as MORE EXPRESSIVE than the product requires. Slice 2 §17.3 established that no existing audit / lifecycle model shape fits; Slice 2 §18 established that provenance requires only deleted-teammate-name. A companion model introduces:

- Additional table + FK maintenance.
- Denormalized shape (row-per-KD but data derivable from KD state).
- Ambiguity about which side is source of truth for retrieval.
- Migration cost (create table + backfill row-per-KD).

Delta's minimum sufficient shape is a single `audience_scope` field on `KnowledgeDocument`. Candidate 3 is deferred — if a future need to attach audience *decision provenance* (who set the audience, when, why) emerges, a companion model can be added later without changing `audience_scope` semantics.

## §50. Favored minimum audience model

**Candidate 2 survives falsification** for the Delta scope. The minimum sufficient shape:

- Single new field: `KnowledgeDocument.audience_scope = CharField(choices=[CHARACTER, UNIVERSE, WORKSPACE, NONE], null=True, blank=False)`.
- `null=True` **only during the staged migration window** (Stages 1–4 in §57). Post-migration invariant: `audience_scope IS NOT NULL`.
- `NONE` valid only when `is_active=False`.
- Retrieval keys positively on `audience_scope`; NULL / malformed / NONE all fail closed.

## §51. Complete new-state truth table

Every state × audience_scope combination. Cells: `V` = valid legitimate state; `M` = malformed (must never occur); `Q` = transitional / migration-only valid; `N` = never matches retrieval; `→` = retrieval audience.

| # | is_active | deactivated_reason | audience_scope | universe | M2M | Valid? | Retrieval → | Operator action to enter |
|---|---|---|---|---|---|---|---|---|
| 1 | True | `''` | `CHARACTER` | NULL | ≥1 legacy | **V** | those legacy teammate(s) only | create-with-sp OR attach after create |
| 2 | True | `''` | `CHARACTER` | U | ≥1 Universe-U | **V** | those Universe-U teammate(s) only | create-with-sp-and-universe OR attach |
| 3 | True | `''` | `CHARACTER` | any | ∅ | **M** | **N** (fail-closed) | reached only by malformed transition (e.g., detach-final bug or D-latent); model.clean() rejects |
| 4 | True | `''` | `UNIVERSE` | U | any (typically ∅) | **V** | every teammate in Universe U | explicit "share to Universe" gesture at create-time or PATCH |
| 5 | True | `''` | `UNIVERSE` | NULL | any | **M** | **N** | model.clean() rejects |
| 6 | True | `''` | `WORKSPACE` | NULL | any (typically ∅) | **V** | every legacy teammate in workspace | explicit "share to workspace" gesture |
| 7 | True | `''` | `WORKSPACE` | non-NULL | any | **M** | **N** | model.clean() rejects |
| 8 | True | `''` | `NONE` | any | any | **M** | **N** | not permitted for active rows; model.clean() rejects |
| 9 | True | `''` | `NULL` | any | any | **Q** | migration-fallback empty-M2M-broadcast for Stages 1–4; **N** after Stage 6 | migration only; not creatable by any endpoint |
| 10 | False | `'operator_delete'` | `CHARACTER` | NULL | ≥1 legacy (preserved) | **V** | nobody (inactive) | operator DELETE on SA |
| 11 | False | `'operator_delete'` | `CHARACTER` | U | ≥1 Universe-U (preserved) | **V** | nobody | operator DELETE on SB |
| 12 | False | `'operator_delete'` | `UNIVERSE` | U | ∅ | **V** | nobody | operator DELETE on SD |
| 13 | False | `'operator_delete'` | `WORKSPACE` | NULL | ∅ | **V** | nobody | operator DELETE on SC |
| 14 | False | `'operator_delete'` | `NONE` | any | any | **V** but degenerate | nobody | operator DELETE on a KD that was already `NONE` |
| 15 | False | `'orphaned_by_teammate_delete'` | `NONE` | preserved | ∅ | **V** | nobody | signal-driven (SESSION 275 mechanism); audience_scope stamped `NONE` at archive |
| 16 | False | `'orphaned_by_teammate_delete'` | `CHARACTER` | any | ∅ | **M** | **N** | pre-Delta shape; would fail Stage 5 invariant. Delta requires the signal to also set `audience_scope=NONE` |
| 17 | False | `''` | any | any | any | **M** | **N** | inactive rows must carry a reason |

**Impossible combinations (invariants #1–#4 in §52):**

- CHARACTER + M2M=∅ + is_active=True (row #3)
- UNIVERSE + universe=NULL (row #5)
- WORKSPACE + universe non-NULL (row #7)
- NONE + is_active=True (row #8)
- inactive + reason='' (row #17, existing rule reinforced)

**Migration-only valid:** row #9 (audience_scope=NULL) during Stages 1–4; disappears after Stage 6.

## §52. Enforcement invariants (design, not code)

Small closed set:

1. `audience_scope = CHARACTER` ⇒ `spokespeople.count() >= 1`. (Cannot enforce in a Postgres CHECK constraint alone — requires model-layer `clean()` + `pre_save` receiver + `m2m_changed pre_remove`/`pre_clear` receiver.)
2. `audience_scope = UNIVERSE` ⇒ `universe_id IS NOT NULL`. (Postgres CHECK-enforceable.)
3. `audience_scope = WORKSPACE` ⇒ `universe_id IS NULL`. (Postgres CHECK-enforceable.)
4. `is_active = True` ⇒ `audience_scope IN {CHARACTER, UNIVERSE, WORKSPACE}` (i.e., NOT `NONE` and NOT `NULL` post-Stage 6). (Postgres CHECK-enforceable.)
5. `is_active = False` ⇒ `deactivated_reason != ''`. (Existing rule; no Delta change.)
6. Cross-workspace + cross-Universe M2M consistency. (Existing rule; no Delta change; `apps/embeddings/signals.py:31,93`.)

Compared to Slice 2 Layer 1 + Layer 2:

- Slice 2 Layer 1 (`NOT (is_active=true AND deactivated_reason='orphaned_by_teammate_delete')`) is **subsumed** by invariant #4 + Delta's requirement that orphan-archive stamps `audience_scope=NONE` (row #15). If both are stamped correctly, revival requires setting audience_scope to a live value — the same intent Slice 2's Layer 1 encoded, now enforced via positive marker instead of negative reason check.
- Slice 2 Layer 2 (transition gate on `deactivated_reason` clearing) becomes redundant. Revival is now gated by "must set a valid `audience_scope` before flipping `is_active=True`" — same effect, cleaner primitive.

Delta invariants are **fewer, positive, and orthogonal**. Each enforces a single row-shape rule. Composite failure risk (Slice 3 §36) reduces because the invariants don't compose transitively — every write must satisfy all four; no clever sequence of individually-valid steps can produce a malformed state.

## §53. Conceptual new retrieval predicate

Current predicate (`shell/apps/embeddings/retrieval.py:194-224`):

```
retrieve_for_teammate(T, query):
    workspace = T.workspace
    universe_filter = (KD.universe IS NULL if T.universe IS NULL else KD.universe = T.universe)
    m2m_filter = (KD.spokespeople IS NULL) OR (T ∈ KD.spokespeople)
    is_active_filter = (KD.is_active = True AND KD.status = 'processed')
```

Delta-conceptual predicate:

```
retrieve_for_teammate(T, query):
    workspace = T.workspace
    is_active_filter = (KD.is_active = True AND KD.status = 'processed')
    audience_match =
        (KD.audience_scope = 'CHARACTER' AND T ∈ KD.spokespeople AND
            (KD.universe IS NULL AND T.universe IS NULL) OR (KD.universe = T.universe))
        OR (KD.audience_scope = 'UNIVERSE' AND KD.universe = T.universe)
        OR (KD.audience_scope = 'WORKSPACE' AND KD.universe IS NULL AND T.universe IS NULL)
    # NONE / NULL / any malformed shape never matches
```

Compatibility fallback (Stages 1–4 only):

```
    OR (KD.audience_scope IS NULL AND
        [current empty-M2M-broadcast logic — universe-match AND (M2M IS NULL OR T ∈ M2M)])
```

Fallback removed at Stage 6.

**Fail-closed property.** Any row where `audience_scope` is `NULL` (post-migration) or `NONE`, or where the invariant is violated (e.g., CHARACTER with empty M2M), never matches the audience_match clause. A malformed row that somehow reaches the DB (bug, race, out-of-band write) becomes invisible to retrieval rather than broadcast.

## §54. Current-state → new-state audience equivalence

The load-bearing table for the invariant "no well-classified KD changes effective audience across migration." Every Slice 3 §31 state × the Delta predicate:

| Current state | Current predicate result | Delta target | Delta predicate result | Equivalent? |
|---|---|---|---|---|
| **SA** — active char-specific legacy `(True, NULL, ≥1 legacy, '')` | those legacy teammates | `audience_scope=CHARACTER` | same M2M match | ✓ **YES** |
| **SB** — active char-specific Universe `(True, U, ≥1 U, '')` | those Universe-U teammates | `audience_scope=CHARACTER` (with universe=U preserved) | same M2M match, gated by universe equality | ✓ **YES** |
| **SC** — active workspace-shared canon `(True, NULL, ∅, '')` | every legacy teammate in workspace | `audience_scope=WORKSPACE` | every legacy teammate in workspace | ✓ **YES** *if the row is a well-classified WORKSPACE canon* |
| **SC (ambiguous subset, 10 rows)** | every legacy teammate in workspace | `audience_scope=NULL` (migration fallback) | same via Stage-1–4 fallback; **fail-closed after Stage 6 UNTIL operator classifies** | ✓ during migration; requires operator action before Stage 6 |
| **SD** — active Universe-shared canon `(True, U, ∅, '')` | every teammate in Universe U | `audience_scope=UNIVERSE` | every teammate in Universe U | ✓ **YES** *for the 3 evidence-backed rows* |
| **SE** — operator-deleted `(False, any, prior M2M preserved, 'operator_delete')` | nobody (inactive) | `audience_scope` = whatever it was before delete (CHARACTER / UNIVERSE / WORKSPACE) | nobody (inactive) | ✓ **YES** |
| **SF** — orphan-archived `(False, any, ∅, 'orphaned_by_teammate_delete')` | nobody (inactive) | `audience_scope=NONE` | nobody (inactive) | ✓ **YES** |

**Equivalence guarantee.** Every well-classified KD retrieves to the same audience before and after Delta. The **only** rows that change behavior across migration are the ambiguous 10, and they change from "silently broadcast to workspace legacy teammates" to "operator triage required before broadcast continues" — a NARROWING that the invariant explicitly permits (SESSION 275 §23 forbids broadening, not narrowing) and that requires Chris's authorization at the *migration cutover* (Stage 6), not automatically.

## §55. Full-DB migration bucket inventory (read-only)

Executed 2026-08-21. All KnowledgeDocument rows across every workspace in the current DB. No mutations.

**Aggregate by shape (all 72 rows):**

| Shape `(is_active, universe_set, m2m_nonempty, deactivated_reason)` | Count | Delta bucket |
|---|---|---|
| `(True, False, False, '')` | 10 | **AMBIGUOUS — operator classification required** |
| `(True, False, True, '')` | 49 | deterministic `CHARACTER` (legacy) |
| `(True, True, False, '')` | 3 | deterministic `UNIVERSE` (evidence-backed intentional canon) |
| `(True, True, True, '')` | 10 | deterministic `CHARACTER` (Universe-scoped) |
| Inactive (any shape) | 0 | n/a — SESSION 275 mechanism has NOT fired in production yet; no SE, no SF |

**Per-workspace breakdown:**

- **admins-workspace** (46 KDs): 45 `CHARACTER` legacy + 1 ambiguous (`33c07feb "Wikipedia is trafilatura's home turf"`, created 2026-05-14 by admin@mail.com; pre-Universe era; content is workspace-level tech note about trafilatura library).
- **chriss-workspace** (18 KDs): 4 `CHARACTER` legacy (Surgo Automotive Mike KB, Surgo Financing, Penny Riverstone, REPO RED) + 4 `CHARACTER` Universe (Ruby Working Knowledge, PATCH knowledge, RIVET knowledge, `PATCH'S WORKSHOP — SHARED CANON` multi-character) + 1 `UNIVERSE` canon (Ruby `8f825c98` House Policies & Hours) + 9 ambiguous (the historical set from Slice 1).
- **exp266-strong / exp266-weak** (3 KDs each = 6): all `CHARACTER` Universe (Patch, Rivet, Patch+Rivet SHARED CANON).
- **session272-rivet-debug-ctl / -exp** (1 KD each = 2): both `UNIVERSE` canon (SESSION 272 knowledge-shape experiment substrates; intentional Universe-shared by construction).
- **68 other workspaces** (mostly e2e-wizard-generated + smoke-test + inspects/probes): 0 KDs each.

### §55.1 Deterministic classification

**62 of 72 rows (86%) migrate deterministically:**

- **`CHARACTER` = 59 rows** (49 legacy + 10 Universe-scoped). Every row with non-empty M2M migrates to `CHARACTER` by construction; the M2M itself is the audience decision that was already made at create / attach time.
- **`UNIVERSE` = 3 rows.** Each requires evidence of intentional Universe-shared authoring:
  - Ruby `8f825c98` — SESSION 275 §Slice 1 confirmed as intentional Fox & Flour Bakery canon; content is bakery house-policies-and-hours.
  - session272-rivet-debug-ctl `d8ab3d2c` — SESSION 272 experimental substrate; intentional Universe canon by construction (test workspace).
  - session272-rivet-debug-exp `64c91888` — same.

### §55.2 Ambiguous classification (10 rows; operator action required)

**Cannot be blanket-migrated per the task-added migration invariant.** Each requires an explicit operator decision.

- **chriss-workspace: 9 rows** — the historical set from Slice 1 §4:
  - TANK `8c6f0c14` — PROVEN historical orphan (CharacterIdentity[Tank].teammate_id=NULL fingerprint). Correct Delta target = `NONE + is_active=False`.
  - Tulsi `7ecde40b` — STRONG historical orphan (Composition + Asset with spokesperson_id=NULL). Correct Delta target = `NONE + is_active=False`.
  - Riggs `90ad200c` — PROVEN never-attached / misconfigured (Riggs teammate exists; KD created 64s after; content stub). Correct Delta target under operator decision: either `CHARACTER` (attach to Riggs), delete, or `NONE + is_active=False` if Chris decides it was noise.
  - 6× Hearth & Hollow (`aa90d895 · e37ea174 · b58efd31 · 7f41d8e3 · c408656d · 0088f31f`) — mechanically indeterminate; operator recollection (SESSION 274 §596) says orphan; content is bookstore-first-party voice. Correct Delta target under operator decision: either `WORKSPACE` (accept as intentional workspace canon) or `NONE + is_active=False` (accept operator recollection).
- **admins-workspace: 1 row** — `33c07feb "Wikipedia is trafilatura's home turf"` by admin@mail.com. Pre-Universe era; internal admin workspace. Likely intentional workspace-shared tech note but no forensic evidence. Correct Delta target: `WORKSPACE` under admin decision, OR `NONE + is_active=False` if admin decides it's obsolete.

**All 10 ambiguous rows are in operator-facing workspaces where the workspace owner has the context to decide.** No hidden third-party rows.

### §55.3 Inactive-row inventory

**Zero.** No `is_active=False` rows anywhere in the current DB. Corollary: the SESSION 275 signal has not yet fired in production. The mechanism is proven by tests but has never actually archived a row.

**Migration implication for SF (orphan-archived):** the migration currently has ZERO orphan-archived rows to backfill. Delta stage 2 only needs to backfill `CHARACTER` / `UNIVERSE` for existing active rows plus decisions on ambiguous rows. No SE / SF backfill logic needed today. **BUT** — the Delta migration must include a *guarantee* that any FUTURE orphan-archive stamps `audience_scope=NONE` alongside `deactivated_reason='orphaned_by_teammate_delete'` (row #15 in §51 truth table). This is a small extension to the SESSION 275 signal at `shell/apps/spokespeople/signals.py:196-200`.

## §56. Special treatment for the 9 legacy KDs (+ 1 admins)

Per task instruction, Slice 1 classifications are preserved unless new evidence falsifies them. Slice 4 evidence does not falsify any.

**If Delta were implemented, migration options for each:**

| # | KD | Slice 1 verdict | Delta options | Would leaving ambiguous violate invariant? |
|---|---|---|---|---|
| 1–6 | 6× Hearth & Hollow | WEAK-INFERENCE orphan; operator recollection supports orphan | (a) `WORKSPACE` (formalize current effective audience; NOT a broaden), (b) `NONE + is_active=False` (accept operator recollection; NARROW). Blanket `WORKSPACE` violates task-added migration invariant | Leaving active + `audience_scope=NULL` during Stages 1–4 preserves current behavior via fallback. Post-Stage-6 the row FAILS CLOSED — retrieves to nobody. That is a NARROW (safe re invariant) but a behavior change |
| 7 | Tulsi | STRONG-INFERENCE orphan | (a) `NONE + is_active=False` (matches evidence), (b) `WORKSPACE` (formalize leak — but no evidence supports intent). Recommended: `NONE + is_active=False` under Chris signoff | Same |
| 8 | TANK | PROVEN orphan | `NONE + is_active=False` (deterministic by evidence — CharacterIdentity SET_NULL fingerprint is dispositive). This is the ONE ambiguous row Slice 1 evidence classifies definitively | Same |
| 9 | Riggs | PROVEN not-orphan / misconfigured | (a) `CHARACTER` with M2M={Riggs} (attach), (b) `NONE + is_active=False`, (c) hard-delete. Operator decision | Same |
| 10 | admins `33c07feb` | trafilatura tech note; no orphan fingerprint | (a) `WORKSPACE` under admin decision, (b) `NONE + is_active=False`. Same shape as Hearth & Hollow ambiguity | Same |

**Load-bearing answers to §56 sub-questions:**

- **Would leaving ambiguous rows active during migration violate the invariant?** No — the invariant forbids *broadening*. Leaving a currently-broadcasting-to-legacy-workspace row exactly where it is is *neither* narrowing nor broadening. Post-Stage-6 the row goes fail-closed (narrows to nobody) — that IS a behavior change but is invariant-safe.
- **Should ambiguous rows be automatically quarantined?** Not automatically. Chris's task instruction: *"Do not assume quarantine is approved merely because it is safe."* Any auto-quarantine at Stage 6 is a NARROW that requires Chris's authorization at cutover time. Slice 4 records the option but does not commit.
- **Is migration allowed to narrow audience automatically for safety?** The invariant permits it; product intent may not. Slice 4 flags "auto-quarantine at Stage 6" as a decision requiring explicit sign-off per row (or per class).

**The 9 legacy rows do NOT block the Delta migration.** They only require an operator triage flow before Stage 6 cutover. The 62 deterministic rows can migrate at Stage 2 without touching the 10 ambiguous rows at all.

## §57. Migration / deployment sequencing

Design only. No code, no migration file, no schema change.

### §57.1 Candidate staged sequence

| Stage | Action | Reversible? | Old code + new code coexist? | Failure at this stage means what? |
|---|---|---|---|---|
| **1** | Add nullable `audience_scope` column via Django migration. No backfill. No retrieval change. All rows have `audience_scope=NULL`. | ✓ — column-drop reverses | ✓ — old code ignores new column; new code has fallback for NULL | old code continues to work; no retrieval change |
| **2** | Data migration: backfill deterministic rows. `CHARACTER` for M2M-nonempty (59 rows). `UNIVERSE` for the 3 evidence-backed intentional-canon rows (Ruby `8f825c98`, session272-rivet-debug-ctl/exp). 10 ambiguous rows stay NULL. | ✓ — clear `audience_scope=NULL` for all rows | ✓ — old code still ignores; new code uses populated values for 62 rows and falls back for 10 | 62 rows correctly classified; 10 rows stay in current-behavior fallback |
| **3** | Extend every mutation surface (ingestion, serializer, views, admin, `KnowledgeDocument.save()`) to set `audience_scope` on writes. Extend SESSION 275 signal to stamp `audience_scope=NONE` on orphan-archive. | Partially reversible — the mutation-surface changes can be reverted per-endpoint | ✓ — old code writes NULL (falls back); new code writes correctly | new writes correctly classified; old rows still safe |
| **4** | Build operator triage UI for the 10 ambiguous rows. Operator explicitly classifies each. Chris + admin decide. | Reversible — operator can re-classify | ✓ — triage UI writes `audience_scope` explicitly | ambiguous rows drop to zero as operator works through |
| **5** | New retrieval predicate goes live. Delta-conceptual predicate from §53. Compatibility fallback for `audience_scope IS NULL` still present. | Reversible — swap predicate back | ⚠️ — old code may still perform retrieval via legacy predicate. If any pending row exists, both codepaths see the same broadcast behavior via fallback | if any ambiguous row still NULL, it retrieves via fallback (current behavior); otherwise fail-closed |
| **6** | After ALL rows are non-NULL (`audience_scope IS NOT NULL` for every row), remove compatibility fallback. Add DB CHECK constraint enforcing invariants #2, #3, #4 (§52). Add Postgres NOT NULL constraint on `audience_scope`. | Constraint removal is a fast migration | ⚠️ — old code that writes NULL now violates NOT NULL → integrity error. Requires all deploys to be on new code | fail-closed for any lingering malformed shape; production-safe |
| **7** | Retire Slice 2 Layer 1 + Layer 2 proposal (§52 subsumption). `deactivated_reason` returns to pure lifecycle metadata. Ingestion `OrphanRevivalRejected` becomes generalized "must set audience_scope explicitly on revive." | Refactor | n/a — new-code-only | code cleanup complete |

Stages are **decoupled**. Each has an independent success criterion. Deployment can pause at any stage without leaks (Stages 1–4 preserve current behavior via fallback; Stage 5 preserves it while `audience_scope IS NULL`; Stage 6 requires zero NULL rows; Stage 7 is pure cleanup).

### §57.2 Rollback / failure-mode analysis

| Stage | Roll-forward failure | Roll-back cost |
|---|---|---|
| 1 | Column add fails or slow | drop column; zero data loss (nothing written yet) |
| 2 | Backfill script fails partway | 62-row backfill is small; retry idempotent; or drop `audience_scope=NULL` on rollback — no data loss |
| 3 | Endpoint change bug leaves audience_scope wrong | mutation-side revert; row is malformed but fails closed under §53 predicate — no leak |
| 4 | Operator misclassifies during triage | reclassify — no data loss; audience is a mutation, not a destroy |
| 5 | New predicate returns wrong audience | revert predicate to fallback-only; `audience_scope` values still valid (harmless) |
| 6 | Constraint add fails because a row is malformed | fix the row (surface via preflight query listing violators), retry |
| 7 | Cleanup revert | trivial; restores dead code |

**Deployment safety at each stage:**

- **Between deploys where Stage N and Stage N+1 have different code versions live simultaneously** (e.g., blue-green rollover): all steady-state fallbacks work. The most dangerous window is between Stage 5 (predicate change) and Stage 6 (fallback removal) — if an old-code worker writes `audience_scope=NULL` during that window, the row is retrievable via fallback but flagged as malformed by new code. This is the "grace" window. As long as Stage 3 (mutation surface updates) is fully rolled out before Stage 5, no old code writes NULL.
- **What can accidentally become broadcast?** Nothing. The fallback preserves current behavior; Stage 6 fail-closes malformed shapes. A row cannot silently become broadcast via any Stage transition.
- **What can accidentally become inaccessible?** The 10 ambiguous rows at Stage 6 IF the operator has not triaged them AND Stage 6 removes fallback. Stage 6 must gate on "all rows non-NULL" — that gate is checkable via `KnowledgeDocument.objects.filter(audience_scope__isnull=True).exists()` before the constraint migration runs.

### §57.3 Composition failure the migration must NOT produce

The migration itself is subject to the SESSION 275/276 invariant. Explicit failure modes to avoid:

- **Blanket-migrating `(empty M2M, universe NULL)` → `WORKSPACE`**. Forbidden — would formalize the 10 ambiguous rows as intentional canon without evidence. Migration must skip these at Stage 2.
- **Auto-quarantining ambiguous rows at Stage 6 without Chris signoff.** NARROWING is invariant-safe but is a behavior change requiring authorization.
- **Failing to extend the SESSION 275 signal to stamp `audience_scope=NONE`.** Without this, a future orphan-archive stamps `is_active=False, reason='orphaned_by_teammate_delete', audience_scope=NULL` — post-Stage-6 that row satisfies Stage 5 predicate fail-closed but violates Stage 6 NOT NULL constraint. Signal extension is a REQUIRED companion change.
- **Removing the ingestion `OrphanRevivalRejected` gate before Stage 6 completes.** During Stages 1–5, the existing gate stays in place. Stage 7 generalizes it into "must set audience_scope explicitly on revive."

## §58. Slice 3 transition matrix replayed under Delta

For every unsafe transition Slice 3 §33 identified, what does Delta do?

| Slice 3 ID | Transition | Delta behavior |
|---|---|---|
| **T8** | SPA detach-final on SA | Serializer detach action calls `.remove(sp)`. Post-remove, model.clean() (via `pre_save` receiver on the M2M or model layer) checks: `audience_scope=CHARACTER` requires M2M ≥ 1. FAILS. Response: HTTP 400 with body copy "This character was the last spokesperson. Choose UNIVERSE or WORKSPACE audience explicitly, delete the document, or attach another character." SPA can then present the operator with the three-way choice as a confirmation dialog. **BLOCKED cleanly** |
| **T9** | SPA detach-final on SB | Same invariant; same 400 | **BLOCKED** |
| **T11** | DRF `PATCH spokesperson_ids=[]` on SA | Serializer processes the payload; before commit, model.clean() rejects `CHARACTER + M2M=∅`. HTTP 400 | **BLOCKED** |
| **T14** | DRF `PATCH universe=None` on SD canon | Serializer processes; `audience_scope=UNIVERSE + universe=NULL` violates invariant #2. HTTP 400. Operator must either send `{universe: null, audience_scope: 'WORKSPACE'}` explicitly (intentional broaden) or `{universe: null, audience_scope: 'CHARACTER', spokesperson_ids: [...]}` (narrow) | **BLOCKED without explicit audience choice** |
| **T15** | DRF `PATCH universe=B` on SD canon (Universe swap) | `audience_scope=UNIVERSE + universe=B` satisfies invariants. The audience SHIFTS (different set of Universe-B teammates) but stays "UNIVERSE-shared" as a type. Product-decision question: should Universe SWAPS require explicit confirmation? Delta doesn't force this; the invariants pass. A separate UI gesture ("Reassign scope: are you sure?") can be added, but it's not an invariant violation | **PERMITTED** (Delta does not add friction here; product may choose to add UI gate) |
| **T28** | Admin: flip `is_active=True` on SF, leave `reason` = orphaned | Admin form save → model.save → `pre_save` receiver checks invariant #4 (`is_active=True` requires `audience_scope != NONE`). Admin cannot flip `is_active=True` without also setting `audience_scope`. If admin sets `audience_scope=CHARACTER`, invariant #1 requires M2M ≥ 1 — admin cannot edit M2M (`admin.py:35-39`) so admin cannot alone revive to CHARACTER. Admin CAN set `audience_scope=UNIVERSE` (if universe set) or `WORKSPACE` (if universe NULL), which is an explicit admin-side audience decision. **BLOCKED without explicit audience choice by admin** |
| **T29** | Admin: flip `is_active=True` AND clear `reason` | Same invariant; same block until admin also sets valid `audience_scope` | **BLOCKED** |
| **T30** | Admin: universe swap on canon | Analogous to T14. If admin changes universe on `UNIVERSE`-audience KD without also updating audience_scope, invariant #2 may fail (if universe cleared to NULL). Admin form's model.clean fires | **BLOCKED IF result would malform**, else permitted |
| **T31** | Raw `KnowledgeDocument.objects.filter(...).update(is_active=True)` bypasses model.save/clean/pre_save | Layer 1 DB CHECK invariant #4 (`is_active=True ⇒ audience_scope != NONE`) is enforceable as Postgres CHECK. Invariant #1 is NOT (needs M2M count). Row would fail CHECK on active + NONE — **BLOCKED**. Row could pass CHECK on active + CHARACTER + M2M=∅ (invariant #1 not DB-enforced) but the retrieval predicate fails closed on the malformed shape — **NO LEAK** even if invariant #1 is app-layer only | **BLOCKED or fail-closed** |
| **T32** | Raw M2M manipulation (through-model direct writes) | `m2m_changed` signals don't fire for through-model direct writes. Delta cannot prevent this at signal level. But the retrieval predicate fail-closes malformed shape — the row becomes invisible, not broadcast | **fail-closed** |
| **D-latent** | SE + later Teammate delete of sole surviving spokesperson | Extended signal (per §57.1 Stage 3) sees SE + M2M-becomes-empty and either (a) stamps `audience_scope=NONE` (fail-closed on any future revival) or (b) simply lets the CASCADE happen — resulting `CHARACTER + M2M=∅ + is_active=False` is malformed but inactive; retrieval fail-closes; revival requires re-setting `audience_scope` explicitly. Either sub-strategy solves the leak | **naturally solved** |

**All 6+ Slice 3 unsafe transitions are cleanly handled by Delta invariants.** No per-endpoint gates required — the same 4-invariant set covers every mutation path.

## §59. D-latent under Delta

Slice 3 §37.D discovery: operator-deleted KD (SE) whose sole surviving spokesperson is later deleted. The SESSION 275 signal's `is_active=True` filter (`shell/apps/spokespeople/signals.py:188`) excludes SE, so through-row CASCADEs silently. SE loses M2M anchor without archive marker.

Under Delta:

- SE has `audience_scope=CHARACTER` (from before delete) + M2M={the-teammate} + `is_active=False`.
- Teammate delete → CASCADE strips through-row → SE now has `audience_scope=CHARACTER + M2M=∅ + is_active=False`.
- This shape violates invariant #1 (CHARACTER requires M2M ≥ 1). It is MALFORMED.
- Retrieval predicate fails closed on the malformed shape (row #3 in §51 truth table).
- Any future revival attempt (ingestion dedup, admin flip, etc.) must set `audience_scope` to a valid live value + satisfy shape invariants — bare revival cannot succeed.

**Optional refinement:** extend the SESSION 275 signal to inspect SE KDs too. When a Teammate delete would empty an SE KD's M2M, transition `audience_scope=CHARACTER → NONE` alongside `is_active=False` (which it already is). This makes the row EXPLICITLY MALFORMED-KNOWN rather than IMPLICITLY MALFORMED. Cleaner but not strictly required — the invariants + retrieval fail-closed guarantee no leak either way.

Delta **naturally solves** D-latent. This is the strongest Slice 4 evidence that positive audience representation is architecturally superior to negative-shape-derived audience for this problem class.

## §60. Creation / authoring semantics under Delta

Operator-facing UI does not need to change fundamentally. Current SPA gestures map to Delta as follows:

| Current SPA gesture | Payload today | Delta payload |
|---|---|---|
| Paste form (`workspace/knowledge.tsx:292-297`) with UniverseScopePicker=legacy, no character | `{workspace, universe: null, title, text_content}` | add `audience_scope: 'WORKSPACE'` (default when no character AND legacy scope) |
| Paste form with UniverseScopePicker=Universe-U, no character | `{workspace, universe: U, title, text_content}` | add `audience_scope: 'UNIVERSE'` |
| Citation-based add via ask panel (`spokesperson-ask-panel.tsx:620`) | `{workspace, universe: sp.universe, title, text_content, spokesperson_ids: [sp]}` | add `audience_scope: 'CHARACTER'` |
| Attach (`knowledge-panel.tsx:191`) | `POST /attach/ {spokesperson_id}` on SC/SD row | server-side: if source was `WORKSPACE`/`UNIVERSE`, transition to `CHARACTER`. If already `CHARACTER`, add to M2M. Explicit "make character-scoped" gesture |
| Detach (`knowledge-panel.tsx:199`) | `POST /detach/ {spokesperson_id}` on SA/SB row | server-side: remove from M2M; if M2M becomes empty, respond 400 with three-way choice dialog (§58 T8) |

**Defaults preserve current simple authoring.** An operator using the paste form today does NOT need to learn about audience_scope — the server infers it from `(universe, spokesperson_ids)`:

- `spokesperson_ids` present → `CHARACTER` (with universe from the M2M members' universe).
- `spokesperson_ids` absent + `universe=U` → `UNIVERSE`.
- `spokesperson_ids` absent + `universe=null` → `WORKSPACE`.

**Persisted state is unambiguous** even though the UI gesture is simple. The server materializes the operator's implicit intent into an explicit `audience_scope` value.

**Should current "no character selected" continue to mean shared?** Yes at create time — that's the SPA's existing convention and it maps cleanly to `WORKSPACE`/`UNIVERSE`. The overload only causes problems POST-CREATION when detach-final produces the same shape without the same intent. Delta's server-side inference at create time preserves current authoring; the invariants on transitions catch the post-creation cases.

**Chris's product-philosophy rule preserved:** operator remains at the "pick scope + optionally attach characters" level. Audience_scope is a server-side materialization, not an operator concept.

## §61. Recovery semantics under Delta

Slice 2 §46 load-bearing rule: revival must never implicitly broaden audience.

Under Delta, revival becomes uniform across all paths:

- **Ingestion revival on SE (`operator_delete`):** as today, restore prior M2M if caller supplies nothing OR replace with caller-supplied set. `audience_scope` was preserved from pre-delete; no change needed.
- **Ingestion revival on SF (`orphaned_by_teammate_delete`, `audience_scope=NONE`):** invariant #4 (`is_active=True ⇒ audience_scope != NONE`) requires the revive path to also set `audience_scope`. `OrphanRevivalRejected` gate becomes "must set audience_scope to CHARACTER (with new M2M) or UNIVERSE or WORKSPACE." Same operator contract, cleaner invariant.
- **Admin restore:** same invariant. Admin cannot flip `is_active=True` without also setting valid `audience_scope`.
- **Future SPA restore endpoint** (Slice 2 §21.4 archived-visibility feature): must accept an audience-selection payload as part of the restore action. The endpoint contract is one field: `audience_scope`. Simpler than Slice 2's proposed multi-branch restore endpoint.

**Eliminates need to overload `deactivated_reason`.** Post-Delta, `deactivated_reason` is metadata: "why is this row inactive?" That's all. The audience decision is orthogonal, carried by `audience_scope`.

## §62. Provenance conclusion re-check

Slice 2 §18.1 conclusion:

> Required: deleted teammate name (+ already-durable KD/workspace/reason/timestamp). Useful: deleted teammate id, universe_id, actor. Not required: prior M2M snapshot, narrowing-event history.

**Delta does not change this conclusion.** Deleted-teammate-name remains the only REQUIRED provenance for orphan recovery. The audience_scope=NONE + is_active=False row explicitly says "this KD has no safe audience" — that's a stronger signal than the current implicit shape, but it doesn't tell the operator *which teammate's* knowledge this was.

**Delta may slightly reduce the URGENCY of provenance** because malformed rows fail closed — an operator who never triages an orphan-archived row cannot accidentally cause it to broadcast. The provenance need is now purely operator-context ("would you like to see who owned this knowledge before deciding?"), not safety-critical ("this row is a live audience-broadening risk if you touch it wrong").

But the requirement itself — if provenance is added at all, the required field is still the name — is unchanged.

**`audience_scope=NONE` itself is a form of lifecycle provenance:** it says "the system knows this row has no safe audience." That satisfies part of what §18 asked ("what happened to this KD"): archived, and known-audience-less. The remaining question is "who owned it before" — same as Slice 2.

## §63. Enforcement simplification analysis

Compared against Slice 3 §37.J and Slice 3 §42 (Gamma vs Delta):

| Property | Direction Gamma | Direction Delta |
|---|---|---|
| Conceptual invariants | 6+ per-endpoint gates (one per T8/T9/T11/T14/T15/T28-T30/D-latent) | **4 row-shape invariants** (§52) |
| Mutation surfaces needing audience reasoning | every mutation surface must know when to gate | every mutation surface must set `audience_scope`; no other reasoning |
| Retrieval predicate | absence-derived (empty M2M = broadcast) | **positive** (audience_scope match) |
| Malformed row behavior | may broadcast or fail closed depending on which endpoint bug | **fails closed** |
| Future new endpoint | must reason about audience-broadening independently | must set `audience_scope`; invariants automatic |
| Slice 2 Layer 1 + Layer 2 (`deactivated_reason`-keyed) | still needed | **subsumed** — Delta invariants #1–#4 cover its scope |
| `deactivated_reason` semantic load | audience-security + provenance | **provenance only** |
| Per-slice pattern-recurrence | high — each new manifestation is a new slice | **low** — new bugs would violate one of the 4 invariants and fail closed |

**Delta creates a small closed set of invariants enforceable at durable boundaries.** Retrieval becomes positive rather than absence-derived. Malformed rows fail closed by construction. A future new endpoint that forgets to set `audience_scope` produces rows invisible to retrieval — same fail-closed property.

**Slice 2's Layer 1 + Layer 2 is subsumed** by Delta invariant #4 + the `NONE`-on-orphan-archive signal extension. Layer 1 was "cannot have is_active=True with orphan-reason"; invariant #4 says "cannot have is_active=True with NONE" — same net effect via positive marker. Layer 2 was "cannot clear orphan-reason without new M2M"; invariant #1 says "CHARACTER requires M2M ≥ 1" — any revival that clears reason without providing a valid audience_scope fails one of the 4 invariants.

**`deactivated_reason` returns to pure lifecycle/provenance semantics.** No enforcement load. A cleaner separation than Slice 2 proposed.

## §64. Generalization test

Applying Delta's four-state model to the arbitrary future configurations named in the task:

| Business | Configuration | Delta representation |
|---|---|---|
| **Bakery** | Ruby only | `CHARACTER` + universe=`Fox & Flour` + M2M={Ruby} |
| Bakery | Ruby + another baker | `CHARACTER` + universe=`Fox & Flour` + M2M={Ruby, Other} |
| Bakery | all characters in Fox & Flour Universe | `UNIVERSE` + universe=`Fox & Flour` + M2M=∅ (Ruby's existing `8f825c98` shape) |
| Bakery | company-wide bakery policy across all workspaces | doesn't fit — Delta is workspace-scoped by design. Cross-workspace policy requires a different primitive (not in Delta scope) |
| **Coffee shop** | three bears with individual expertise | 3× `CHARACTER` rows, each M2M={one bear} |
| Coffee shop | shared coffee-shop handbook | `UNIVERSE` + universe=`Coffee Shop U` + M2M=∅ OR `WORKSPACE` + universe=NULL if legacy |
| **Dealership** | five dealership characters | 5× `CHARACTER` rows |
| Dealership | financing knowledge for one character | `CHARACTER` + M2M={that character} |
| Dealership | sales policy shared across dealership Universe | `UNIVERSE` + universe=`Dealership U` |
| Dealership | workspace-wide compliance material | `WORKSPACE` |
| **Workshop** | Patch-only | `CHARACTER` + universe=`Patch's Workshop` + M2M={Patch} (matches existing `fd0ba2ca`) |
| Workshop | Rivet-only | `CHARACTER` + M2M={Rivet} (matches `218eb0d8`) |
| Workshop | Patch + Rivet shared | `CHARACTER` + M2M={Patch, Rivet} (matches `f309469c`) |
| Workshop | Universe/workshop canon | `UNIVERSE` + universe=`Patch's Workshop` + M2M=∅ (not currently in the DB but supported by shape) |

Delta handles every named configuration without character-specific special cases. The four-state model is domain-agnostic. Cross-workspace configurations are OUT OF SCOPE for Delta (as they are for the current system).

## §65. Prediction vs evidence

| Prediction (§47) | Evidence |
|---|---|
| 1. Three-state model insufficient — orphan/unresolved needs fail-closed | **Confirmed** — §49.1 falsified Candidate 1 against SF, D-latent, and legacy ambiguous rows |
| 2. Four-state model with NONE cleanly separates lifecycle from audience | **Confirmed** — §49.2 + §51 truth table + §48 decomposition |
| 3. Most existing KDs with non-empty M2M migrate deterministically to CHARACTER | **Confirmed** — §55 shows 59/72 rows (82%) map cleanly to CHARACTER |
| 4. Known intentional Universe canon (Ruby Class C) migrates deterministically to UNIVERSE | **Confirmed** — 3 rows total: Ruby `8f825c98` + 2 SESSION 272 experiment substrates. All evidence-backed |
| 5. The nine historical empty-M2M/no-Universe rows prevent blanket WORKSPACE backfill | **Confirmed** — §55.2 + §56. Also discovered a 10th ambiguous row (`33c07feb` in admins-workspace) |
| 6. Delta makes D-latent easier to model | **Confirmed strongly** — §59. Naturally solved by invariant #1 + retrieval fail-closed |
| 7. Retrieval can become fail-closed: unknown audience → no retrieval | **Confirmed** — §53 predicate + §51 truth table rows 3, 5, 7, 8, 9 all show `N` retrieval outcome |
| 8. `deactivated_reason` can return to lifecycle/provenance | **Confirmed** — §52 shows Slice 2 Layer 1+2 subsumed by Delta invariants #1–#4 |
| 9. Migration can be staged | **Confirmed** — §57 shows 7 independent stages, each with rollback-safe posture |

Additionally discovered during Slice 4 (not predicted):

- **10 ambiguous rows total, not 9.** The 1 admins-workspace `33c07feb` was not previously catalogued in Slice 1 (which focused on chriss-workspace). Migration must handle both workspaces.
- **Zero inactive rows anywhere in the DB.** The SESSION 275 mechanism has never fired in production. Migration has no SE/SF backfill work to do; but the signal must be extended (Stage 3) to stamp `audience_scope=NONE` on future orphan-archives.
- **The 62/72 deterministic ratio is high** (86%). Migration is small in absolute row count. Operator triage burden is 10 rows, all in operator-facing workspaces.
- **T15 (Universe swap on canon) is NOT reduced by Delta.** Delta's invariants pass a Universe-A → Universe-B swap because both satisfy invariant #2. Product may want an additional UI gate for scope reassignment, but that's separate from the audience invariant.

Every prediction supported by evidence.

## §66. Did Slice 4 falsify Direction Delta, refine it, or support it?

**Slice 4 supports Direction Delta with two explicit refinements:**

1. **Add a fifth transitional state during migration.** `audience_scope=NULL` (or an explicit `PENDING` enum value) for the 10 ambiguous rows during Stages 1–4. Retrieval fallback to current empty-M2M-broadcast semantics for `audience_scope IS NULL`. Removed at Stage 6 once triage completes. This preserves current effective audience for ambiguous rows without violating the task-added migration invariant.
2. **Extend the SESSION 275 signal (Stage 3) to stamp `audience_scope=NONE` on orphan-archive.** Without this extension, future orphan-archived rows would land in a malformed `(is_active=False, reason='orphaned...', audience_scope=NULL)` state that violates Stage 6 NOT NULL constraint. Small ~5-line signal change; not implemented in Slice 4.

**Delta was NOT falsified.** Every falsification attempt (§49.1 Candidate 1 test, §51 truth table, §54 equivalence table, §55 migration bucket inventory, §57 rollback analysis, §58 transition matrix replay, §59 D-latent, §64 generalization test) passed or refined rather than rejected.

**Delta is READY for implementation design** — but Slice 4 does not implement. The next slice must open with a design/plan section covering exact migration file structure, signal-extension diff, retrieval-predicate diff, mutation-surface changes, and the operator triage UI shape (Stage 4). That is Slice 5's scope, not Slice 4's.

## §67. Unresolved questions

Carried forward from Slice 2 §24 and Slice 3 §41 (still open):

- Actor capture at signal time (Slice 2 §24.3).
- Storage shape for deleted-teammate identity — Direction Alpha (denormalized column) vs Direction Beta (companion `KnowledgeDocumentArchiveLog` model). Delta does not answer this — provenance is orthogonal (Slice 2 §18, Slice 4 §62).
- Bundle vs split (Slice 1 §8.4, Slice 2 §24.8, Slice 3 §41).
- T15 characterization — Universe swap on canon: is it worth a separate UI gate?

New from Slice 4:

- (§67.5) **Migration-only `NULL` vs explicit `PENDING` enum value.** NULL is DB-natural and requires no schema change beyond `null=True`. PENDING is a named state that would appear in `choices` and in Django admin filters. Which does Chris prefer? Both work.
- (§67.6) **Auto-quarantine at Stage 6 vs indefinite operator triage.** If Chris does not triage all 10 ambiguous rows before a Stage 6 deploy, the deploy blocks. Alternative: Stage 6 optionally auto-transitions untriaged rows to `NONE + is_active=False` (narrow-safe, invariant-safe, but a behavior change). Which cutover semantics does Chris prefer?
- (§67.7) **Should Delta ship with the ingestion path's `OrphanRevivalRejected` gate replaced immediately (Stage 7) or preserved as belt-and-braces?** Preserving both layers costs nothing; removing simplifies but reduces defense-in-depth. Chris preference.
- (§67.8) **Companion model for audience-decision provenance (who set audience_scope, when, why)?** Slice 4 rejected Candidate 3 as MORE EXPRESSIVE than required. If Chris later wants "audit trail of audience changes," a small companion table can be added without changing the `audience_scope` field itself. Deferred.
- (§67.9) **Does the SPA need a new "audience picker" widget at create time?** Slice 4 §60 answered NO — server-side inference from `(universe, spokesperson_ids)` preserves current authoring. If Chris wants to make audience explicit at create (rather than inferred), a UI change is required but is not blocking Delta.
- (§67.10) **Model.clean() vs pre_save receiver vs m2m_changed receiver for invariant #1.** All three fire at slightly different times. Slice 4 §52 notes invariant #1 requires observing M2M count, which cannot be a pure DB CHECK. Implementation choice for Slice 5.

## §68. Recommendation

**Direction Delta survives falsification and is favored for implementation.** Slice 4 does not implement.

The evidence-backed reasoning:

- Every previously-identified unsafe transition (SESSION 275 orphan, Slice 2 Layer 1+2, Slice 3 T8/T9/T11/T14/T28-T30, Slice 3 §37.D-latent) is covered by 4 row-shape invariants under Delta. Same-shape reasoning that Direction Gamma would repeat per-endpoint is unified into one small invariant set.
- Retrieval becomes positive rather than absence-derived. Malformed rows fail closed. Unknown / new bugs land in fail-closed territory.
- Migration is small (62 deterministic + 10 operator-triage rows) and stageable (7 rollback-safe stages). No flag-day rewrite.
- Effective audience for every well-classified KD is preserved across migration.
- The 10 ambiguous rows do NOT block Delta — they require operator triage before Stage 6 cutover, but Stages 1–5 preserve current behavior via compatibility fallback.
- `deactivated_reason` returns to pure lifecycle/provenance, removing Slice 2's cross-loading.
- Delta solves the *pattern* — same-root recurrence across three slices — rather than the individual manifestations.

**What Delta does NOT do:**

- Doesn't answer the provenance shape question (Slice 2 §24.1). Direction Alpha vs Beta is a separate Chris decision.
- Doesn't remediate the 10 ambiguous rows automatically. Chris must triage them (or authorize auto-quarantine) at Stage 6.
- Doesn't ship any operator-facing UI in Slice 4. Stage 4 needs a triage UI; Stage 3 needs no UI change if defaults preserve authoring.
- Doesn't touch the SPA authoring surface beyond the additive `audience_scope` field on payloads.

**Current schema remains sufficient for the small safe recovery workflow** (Slice 1 §5.6, Slice 2 §25, Slice 3 §42 restated). Delta ADDS a schema field; it does not require rebuilding recovery-adjacent infrastructure.

## §69. Explicit decision gate

**STOP.** Slice 4 does not authorize any code, migration, DB row, admin, or SPA change. Direction Delta is *investigated and supported* — not *implemented*.

Before Slice 5 begins, Chris must decide:

1. **Confirm Direction Delta as the general architecture.** Slice 4 supports it; Chris + ChatGPT approve or refine.
2. **Migration-only NULL vs explicit PENDING enum value** (§67.5).
3. **Auto-quarantine at Stage 6 vs indefinite operator triage** (§67.6).
4. **Slice 5 opening scope.** Is Slice 5 the design/plan slice for Stage 1 (migration file + `null=True` field addition + no backfill), or does Chris want Slice 5 to cover Stages 1+2 (add + backfill deterministic)? Slice 5 must open with a design section, not implementation — same pattern as SESSION 275 §21-§38 and every prior Slice N gate.
5. **Provenance direction (Slice 2 §24.1) — pair with Delta or defer.** Direction Alpha (denormalized name column) can be added at Stage 3 as part of the signal extension. Direction Beta (companion model) is a larger separate arc.
6. **§67 residuals** — each is a discrete decision.
7. **Bundle vs split** (still open from Slice 1 §8.4).

Chris's answers determine Slice 5 scope.

## §70. Smallest falsifiable next questions

Continuing Q-276-N numbering from Slice 3 §44.

- **Q-276-16.** *If we add a nullable `audience_scope = CharField(choices=[CHARACTER,UNIVERSE,WORKSPACE,NONE], null=True, blank=True)` migration and run the full test suite, does anything break?* Falsifiable — Stage 1 dry-run. Zero backfill; retrieval unchanged. Should be a no-op for existing tests.
- **Q-276-17.** *If the backfill script runs on the current DB (62 deterministic + 10 NULL), does the DB end up in the shape §55 predicts?* Falsifiable by running a scratch backfill in a transaction and rolling back before commit. Read-only verification of the classification logic.
- **Q-276-18.** *Would extending the SESSION 275 signal to stamp `audience_scope=NONE` on orphan-archive break SESSION 275 test 13 (atomicity)?* Falsifiable — small signal patch + rerun `test_delete_orphan_archive.py`. The `.update()` call adds one more field; atomicity should hold.
- **Q-276-19.** *Can the compatibility fallback at Stage 5 be expressed as a single `Q(...)` addition to the existing retrieval predicate without breaking the K2 privacy-grep contract?* Falsifiable by writing the predicate on paper against `retrieval.py:194-224` and checking that the K2 grep test still passes.
- **Q-276-20.** *For the 10 ambiguous rows, would a triage UI that presents each with its Slice 1 §4.4 evidence + a three-way choice `{CHARACTER-with-picker | WORKSPACE | NONE-archive}` be sufficient for operator classification?* Falsifiable by mocking the UI on paper and walking through TANK (should default-select NONE), Ruby's Class C `8f825c98` (already deterministic, not in the 10), and admins `33c07feb` (should default-select WORKSPACE).
- **Q-276-21.** *Does adding a Postgres CHECK constraint for invariant #2 (`audience_scope=UNIVERSE ⇒ universe IS NOT NULL`) via a Django migration produce any test failures on baseline `main` after Stage 4 completes?* Falsifiable by adding the constraint in a scratch branch and running the full test suite.

Each is ½-slice or less. None require touching production data. Most are pure design verification.

## §71. Slice 4 checklist

- [x] Re-verify baseline against Slice 3 close (§46 preamble)
- [x] Slice 4 falsifiable question stated (§46)
- [x] Predictions before evidence (§47)
- [x] Lifecycle vs audience vs scope decomposition (§48)
- [x] Candidate audience models compared — 1, 2, 3 (§49)
- [x] Favored minimum audience model (§50)
- [x] Complete new-state truth table (§51)
- [x] Enforcement invariants design (§52)
- [x] Conceptual new retrieval predicate (§53)
- [x] Current-state → new-state audience equivalence (§54)
- [x] Read-only full-DB migration bucket inventory (§55) — 62 deterministic + 10 ambiguous + 0 inactive
- [x] Deterministic vs ambiguous classification (§55.1, §55.2)
- [x] Special treatment analysis for the 10 legacy KDs (§56)
- [x] Migration staging (§57.1) — 7 stages, each rollback-safe
- [x] Rollback / failure-mode analysis (§57.2)
- [x] Composition failure modes migration must avoid (§57.3)
- [x] Slice 3 transition matrix replayed under Delta (§58) — all 6+ unsafe transitions naturally handled
- [x] D-latent analysis (§59) — naturally solved
- [x] Creation / authoring semantics (§60) — server-side inference preserves current authoring
- [x] Recovery semantics under Delta (§61) — uniform across paths; subsumes `OrphanRevivalRejected`
- [x] Provenance conclusion re-check (§62) — unchanged; deleted-teammate-name remains only REQUIRED
- [x] Enforcement simplification analysis (§63) — 4 invariants replace 6+ per-endpoint gates
- [x] Generalization test (§64) — bakery/coffee/dealership/workshop all map cleanly
- [x] Prediction vs evidence table (§65) — all 9 predictions supported
- [x] Explicit Delta survival verdict (§66) — supported with 2 refinements; not falsified
- [x] Unresolved questions (§67)
- [x] Recommendation (§68)
- [x] Explicit STOP / decision gate (§69)
- [x] Smallest falsifiable next questions Q-276-16..21 (§70)
- [x] Zero KD rows mutated; zero migrations; zero admin/SPA/serializer/signal/retrieval changes; zero legacy KD remediation; zero KnowledgeAudience/audience_scope/provenance implementation; zero provider spend; working tree change limited to this document
- [ ] Chris + ChatGPT review + Slice 5 scoping decision (§69)

---

**End of SESSION 276 Slice 4 read-only design / falsification audit. Direction Delta INVESTIGATED and SUPPORTED with two refinements (§66). Not implemented. STOP before implementation. Awaiting Chris + ChatGPT review on §68 recommendation, §69 decision gate, and §70 next questions.**

---

# SESSION 276 — Slice 5 / Delta Stage 1 — nullable `audience_scope` field

**Status.** IMPLEMENTATION SLICE — the smallest first Delta step. Adds the `KnowledgeDocument.audience_scope` field as a nullable `CharField(choices=[CHARACTER, UNIVERSE, WORKSPACE, NONE])` with NO backfill, NO retrieval change, NO mutation-surface change, NO invariant enforcement.

**Slice 5 baseline.** `main == origin/main == d4754737`. Migration head pre-slice: `0006_session275_deactivated_reason`. All Slice 4 predictions and evidence carried forward. 72 KDs total; 0 inactive; 62 deterministic + 10 ambiguous per §55.

**Task scope authorization** (per Slice 4 §69 gate resolved by Chris): implement Delta Stage 1 only. Explicitly excluded: Stage 2 backfill, signal extension, retrieval change, provenance work, invariant enforcement, triage UI. Slice 5 is intentionally tiny.

## §72. Slice 5 falsifiable question

> If we add nullable `KnowledgeDocument.audience_scope` with choices `{CHARACTER, UNIVERSE, WORKSPACE, NONE}`, while leaving every existing row NULL and leaving retrieval/mutation semantics unchanged, does Character OS behave exactly as before?

**Prediction:** yes. This is a schema-only additive change with no effective audience change, no retrieval change, and no effect on existing KnowledgeDocument lifecycle behavior. All existing tests should pass. All 72 existing rows should have `audience_scope IS NULL` post-migration. If evidence falsifies that prediction, STOP and diagnose.

## §73. Exact model diff (`shell/apps/embeddings/models.py`)

Two additive changes:

**1.** New `AudienceScope` `TextChoices` enum immediately after `DeactivationReason` (models.py line 81 in the new file):

```python
class AudienceScope(models.TextChoices):
    """SESSION 276 Slice 5 / Delta Stage 1 — first-class audience marker.

    Replaces the negative-shape-derived audience semantics
    (empty-M2M-broadcast) documented in
    ``docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md``
    §31, §46-§71. The full four-state model is Slice 4 §50 and
    §51.

    Stage 1 posture: the field is nullable, unpopulated on every
    existing row, and NOT consulted by retrieval or any mutation
    path. Retrieval keeps the empty-M2M-broadcast semantics at
    ``apps/embeddings/retrieval.py:216-220`` unchanged. Later
    stages populate rows deterministically, extend mutation
    surfaces to set the field, and only then switch retrieval to
    key on the field positively.

    NULL is a MIGRATION-ONLY state — post-Delta the field will be
    NOT NULL. NULL does NOT mean WORKSPACE; it means "audience
    not yet classified under Delta."
    """
    CHARACTER = ("character", "Character-specific")
    UNIVERSE = ("universe", "Universe-shared")
    WORKSPACE = ("workspace", "Workspace-shared")
    NONE = ("none", "None — fail-closed")
```

**2.** New `audience_scope` field on `KnowledgeDocument` immediately after `deactivated_reason`:

```python
audience_scope = models.CharField(
    max_length=20,
    choices=AudienceScope.choices,
    null=True,
    blank=True,
    default=None,
    help_text=(
        "Delta Stage 1 first-class audience marker. NULL is a "
        "MIGRATION-ONLY state during Delta rollout; NULL does NOT "
        "mean WORKSPACE. Retrieval currently does not consult this "
        "field. See SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md."
    ),
)
```

**Chosen defaults:**

- `null=True` — required. NULL is the migration-only state; no default value classifies an existing row.
- `blank=True` — mirrors DRF/admin form-widget behavior; existing choice fields (e.g., `deactivated_reason` with `blank=True`) follow the same convention.
- `default=None` — explicit. Django's default for CharField is `""`; setting `default=None` guarantees new instances created without the field specified get NULL, not empty string. This is load-bearing for Stage 1 inertness.
- `max_length=20` — the longest choice value (`workspace`) is 9 chars; 20 gives headroom for possible future values without a schema migration.
- **No `db_index`** — retrieval does not yet consult the field; no index needed. Later stages may add one when the retrieval predicate switches.
- **No `verbose_name`** — the choices are display-labelled; verbose_name would only affect admin form label rendering.

**Explicitly not added:** no CHECK constraint (Slice 4 §52 invariants deferred), no NOT NULL constraint, no companion index, no companion signal, no automatic value on save.

## §74. Exact migration diff (`shell/apps/embeddings/migrations/0007_session276_audience_scope.py`)

Generated by `manage.py makemigrations embeddings --name session276_audience_scope`, then annotated with a durable docstring block. The generated `Migration` class is:

```python
class Migration(migrations.Migration):
    dependencies = [
        ("embeddings", "0006_session275_deactivated_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="knowledgedocument",
            name="audience_scope",
            field=models.CharField(
                blank=True,
                choices=[
                    ("character", "Character-specific"),
                    ("universe", "Universe-shared"),
                    ("workspace", "Workspace-shared"),
                    ("none", "None — fail-closed"),
                ],
                default=None,
                help_text=(
                    "Delta Stage 1 first-class audience marker. NULL is a "
                    "MIGRATION-ONLY state during Delta rollout; NULL does "
                    "NOT mean WORKSPACE. Retrieval currently does not "
                    "consult this field. See "
                    "SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md."
                ),
                max_length=20,
                null=True,
            ),
        ),
    ]
```

**Generated SQL** (`manage.py sqlmigrate embeddings 0007_session276_audience_scope`):

```sql
BEGIN;
--
-- Add field audience_scope to knowledgedocument
--
ALTER TABLE "embeddings_knowledgedocument" ADD COLUMN "audience_scope" varchar(20) NULL;
COMMIT;
```

Pure additive `ADD COLUMN … NULL` — no data migration, no default touching existing rows, no index rebuild. Fully reversible via `migrate embeddings 0006` (which emits `DROP COLUMN`).

## §75. Serializer / API exposure decision

**Chosen posture: OMIT from public serializer.**

Inspection of `KnowledgeDocumentSerializer` (`shell/apps/embeddings/serializers.py:39-156`) confirms it uses an **explicit `Meta.fields = [...]` list** — not `"__all__"` and not automatic model-field discovery. `audience_scope` is not in that list, so DRF does not auto-serialize it. Structurally omitted; no serializer code change needed.

Consequences:

- `GET /api/knowledge/<id>/` responses do NOT include `audience_scope`. Old and new API clients see identical JSON.
- `PATCH /api/knowledge/<id>/` does NOT accept `audience_scope`. A caller sending `{"audience_scope": "workspace"}` in the payload has the key silently dropped by the serializer (unknown field ignored by DRF `ModelSerializer` in strict-typed mode isn't ignored — but this serializer does not read from `validated_data.get("audience_scope")` anywhere, so any accidentally-passing payload has zero effect on the row).
- No SPA change; no API contract change; no operator-visible surface change.

**Why NOT expose read-only.** Making the field read-only in the serializer would surface a Stage 1 diagnostic value (mostly NULL today) to API clients. That would be safe but adds a semantic the SPA doesn't yet know how to interpret and could be misread as an operator-facing feature. Omission is cleaner for Stage 1 posture; read-only exposure will be part of the Stage 3 mutation-surface update when the SPA starts caring about the value.

**KnowledgeDocumentDetailSerializer** (`serializers.py:532-568`) subclasses the base and extends `fields` with `"chunks"` + `"processed_content"` only. Also does not expose `audience_scope`.

## §76. Admin exposure decision

**Chosen posture: ADD to `readonly_fields`.**

Inspection of `KnowledgeDocumentAdmin` (`shell/apps/embeddings/admin.py:22-40`) shows it does NOT set `fields` or `fieldsets`, which means Django admin's default change form auto-detects editable model fields and would render `audience_scope` as an editable dropdown. To prevent accidental admin mutation before Delta invariants are enforced in later stages, `audience_scope` is added to `readonly_fields`.

```python
readonly_fields = (
    "id", "content_hash", "created_at", "updated_at",
    "audience_scope",
)
```

Consequences:

- Admin change form still SHOWS the field (for audit / diagnostic visibility) but as read-only text — cannot be edited.
- Admin change list is unchanged (`list_display`/`list_filter` untouched).
- No admin workflow is created for audience_scope. Stage 1 posture preserved.

**Load-bearing observation:** admin can still edit `is_active` and `deactivated_reason` directly (Slice 1 §5.2 / Slice 2 §19.1 flagged this as the admin bypass). Slice 5 does NOT close that bypass. Delta invariants at Stage 6 (or a compensating admin lock) will address it. Adding `audience_scope` to admin editable fields today would create a NEW bypass class; keeping it readonly maintains the existing surface.

## §77. Tests added

New test module: `shell/apps/embeddings/tests/test_audience_scope_stage1.py` (9 test cases). Covers:

| Test | What it proves | Status |
|---|---|---|
| A: `test_audience_scope_defaults_to_null_when_unspecified` | Creating a KD without specifying `audience_scope` leaves it NULL | PASS |
| B: `test_stage1_leaves_existing_lifecycle_fields_untouched` | A fresh KD has the pre-Delta lifecycle shape (active, reason='', universe=None, m2m=0, audience_scope=None) | PASS |
| C: `test_audience_scope_accepts_all_four_choices` (× 4 parametrized) | All four choice values (`CHARACTER`, `UNIVERSE`, `WORKSPACE`, `NONE`) accepted and round-trip through DB | PASS × 4 |
| D-1: `test_stage1_does_not_yet_enforce_character_requires_m2m` | `CHARACTER` + empty M2M SUCCEEDS (invariant #1 not yet active) | PASS |
| D-2: `test_stage1_does_not_yet_enforce_universe_requires_non_null_universe` | `UNIVERSE` + universe=NULL SUCCEEDS (invariant #2 not yet active) | PASS |
| D-3: `test_stage1_does_not_yet_enforce_none_requires_inactive` | `NONE` on active row SUCCEEDS (invariant #4 not yet active) | PASS |

The D-tests are **guard tests against accidental early invariant enforcement**. If a future slice enables an invariant prematurely, one of these tests will start failing — signaling that behavior has drifted outside Stage 1 scope.

**No existing test file was modified.** The Stage 1 tests are additive.

## §78. Verification results

### §78.1 Migration verification

```
$ python manage.py showmigrations embeddings
embeddings
 [X] 0001_install_pgvector
 [X] 0002_initial
 [X] 0003_alter_knowledgedocument_is_active
 [X] 0004_session251_pin_m2m_through_column
 [X] 0005_universe_fk
 [X] 0006_session275_deactivated_reason

$ python manage.py makemigrations --dry-run --check embeddings
No changes detected in app 'embeddings'   [pre-slice; head was 0006]

$ python manage.py makemigrations embeddings --name session276_audience_scope
Migrations for 'embeddings':
  apps/embeddings/migrations/0007_session276_audience_scope.py
    - Add field audience_scope to knowledgedocument

$ python manage.py sqlmigrate embeddings 0007_session276_audience_scope
BEGIN;
ALTER TABLE "embeddings_knowledgedocument" ADD COLUMN "audience_scope" varchar(20) NULL;
COMMIT;

$ python manage.py migrate embeddings
Operations to perform:
  Apply all migrations: embeddings
Running migrations:
  Applying embeddings.0007_session276_audience_scope... OK
```

### §78.2 Test results

```
$ pytest apps/embeddings/tests/test_audience_scope_stage1.py -v
9 passed in 4.18s

$ pytest apps/spokespeople/tests/test_delete_orphan_archive.py -v
13 passed in 5.40s   (SESSION 275 lifecycle regression — unchanged)

$ pytest apps/embeddings/ -q
221 passed in 18.61s

$ pytest apps/spokespeople/ apps/universe/ apps/compositions/ -q
1424 passed, 2 warnings in 111.88s
```

Every existing test passes. The 2 warnings are pre-existing DateTime naive-vs-aware warnings unrelated to Slice 5.

### §78.3 DB verification (read-only, post-migration)

Live DB shell output (all invariants asserted):

```
=== Schema check ===
audience_scope column: ('audience_scope', 'character varying', 'YES', 20)
    → column type varchar(20), nullable=YES, matches migration SQL

=== Full-DB inventory (post-migration) ===
total KDs: 72
audience_scope IS NULL: 72
audience_scope non-null: 0
    → 100% of existing rows have audience_scope=NULL

=== Bucket recount matches Slice 4 §55 ===
CHARACTER-legacy (universe=NULL, M2M≥1): 49  (Slice 4: 49)  ✓
CHARACTER-universe (universe=U, M2M≥1): 10  (Slice 4: 10)  ✓
Universe canon-shape (universe=U, M2M=∅): 3  (Slice 4: 3)  ✓
Legacy canon-shape ambiguous (universe=NULL, M2M=∅): 10  (Slice 4: 10)  ✓
Inactive: 0  (Slice 4: 0)  ✓

=== 9 chriss-workspace legacy KDs — pre-Delta invariants ===
  aa90d895 | is_active=True | reason='' | audience_scope=None | universe=None | m2m=0
  e37ea174 | is_active=True | reason='' | audience_scope=None | universe=None | m2m=0
  b58efd31 | is_active=True | reason='' | audience_scope=None | universe=None | m2m=0
  7f41d8e3 | is_active=True | reason='' | audience_scope=None | universe=None | m2m=0
  c408656d | is_active=True | reason='' | audience_scope=None | universe=None | m2m=0
  0088f31f | is_active=True | reason='' | audience_scope=None | universe=None | m2m=0
  7ecde40b | is_active=True | reason='' | audience_scope=None | universe=None | m2m=0
  8c6f0c14 | is_active=True | reason='' | audience_scope=None | universe=None | m2m=0
  90ad200c | is_active=True | reason='' | audience_scope=None | universe=None | m2m=0

=== Ruby specimens ===
  8f825c98: active=True reason='' audience_scope=None universe=True  m2m=0
  74e7f18f: active=True reason='' audience_scope=None universe=True  m2m=1
```

Every §J baseline / §G Slice 3 invariant holds. Only observable change: new column exists on the row, value is NULL for every row.

## §79. Prediction vs actual

| Prediction | Actual | Status |
|---|---|---|
| additive nullable column | pure `ALTER TABLE … ADD COLUMN varchar(20) NULL` | ✓ |
| zero backfill | zero rows populated post-migration; 72/72 NULL | ✓ |
| zero retrieval change | retrieval.py untouched; 221 embeddings tests pass unchanged | ✓ |
| zero lifecycle change | 13/13 SESSION 275 orphan tests pass unchanged; 9 legacy KDs unchanged; Ruby C/D unchanged | ✓ |
| all existing rows NULL | 72/72 rows `audience_scope IS NULL` | ✓ |
| existing test suites pass unchanged | 221 embeddings + 1424 spokespeople+universe+compositions + 9 Stage 1 = 1654 total; all pass | ✓ |
| no API contract change | serializer omits the field structurally; SPA unchanged | ✓ |
| no admin editing surface | admin `readonly_fields` locks the field | ✓ |
| no invariant enforcement | 3 D-tests confirm CHARACTER-empty-M2M / UNIVERSE-null-universe / NONE-active all still SAVE | ✓ |

**Every prediction supported. Zero falsifications.** Stage 1 is behaviorally inert.

### §79.1 Unexpected findings

None. The migration is exactly as small as Slice 4 §57.1 Stage 1 predicted. The pyright warnings in models.py and the new test file are Django dynamic-attribute false positives seen throughout the repo (unrelated to Slice 5).

## §80. Files changed (Slice 5)

```
 M shell/apps/embeddings/admin.py                                 (+7 lines — audience_scope in readonly_fields)
 M shell/apps/embeddings/models.py                                (+41 lines — AudienceScope enum + audience_scope field)
?? shell/apps/embeddings/migrations/0007_session276_audience_scope.py    (new — 58 lines w/ docstring)
?? shell/apps/embeddings/tests/test_audience_scope_stage1.py     (new — 172 lines, 9 tests)
?? docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md         (untracked; contains this Slice 5 section)
```

Total code change (excluding tests + doc): 3 files, ~106 lines added, 0 lines removed. Zero SPA changes. Zero other backend app changes.

## §81. Unresolved questions

Carried from Slice 4 §67 (still open — Slice 5 did not authorize solving any of them):

- (§67.5) Migration-only NULL vs explicit PENDING enum value — Slice 5 confirmed NULL works cleanly; PENDING remains an alternative Chris could still choose for Stage 2+.
- (§67.6) Auto-quarantine at Stage 6 vs indefinite operator triage — deferred.
- (§67.7) Preserve ingestion `OrphanRevivalRejected` as belt-and-braces or remove — deferred.
- (§67.8) Companion audience-decision-provenance model — deferred.
- (§67.9) Explicit audience picker in SPA vs server-side inference — deferred.
- (§67.10) `clean()` vs `pre_save` vs `m2m_changed` for invariant #1 — deferred (belongs to Stage 5+).
- Provenance direction (Alpha / Beta / defer) — deferred.
- Bundle vs split — still open.

**No new Slice-5-specific unresolved questions.**

## §82. Recommendation

**Stage 1 is complete and behaviorally inert. Direction Delta is now a live schema substrate but activates NO new behavior.**

Slice 5 does not authorize any further work. Every subsequent stage (Stage 2 deterministic backfill, Stage 3 mutation-surface + signal extension, Stage 4 operator triage UI, Stage 5 retrieval predicate switch, Stage 6 constraint enforcement, Stage 7 Slice 2 Layer 1+2 retirement) requires an independent Chris + ChatGPT scope decision.

**The commit for Slice 5** (if Chris authorizes) can bundle: model + migration + admin lock + tests + this doc section. Or Chris can split (model+migration first, doc second) — both are safe because the code changes are inert and reversible.

## §83. Explicit STOP gate

**STOP.** Slice 5 authorizes no further changes.

Do NOT begin:

- Stage 2 deterministic backfill (Q-276-17)
- Signal extension for `audience_scope=NONE` on orphan-archive
- Provenance work (Direction Alpha / Beta)
- Retrieval predicate change
- Mutation-surface changes to populate `audience_scope`
- Operator triage UI for the 10 ambiguous rows
- DB CHECK constraints
- NOT NULL constraint
- SPA-side changes
- Removing SESSION 275 protections

Even though Stage 1 passed cleanly.

## §84. Smallest recommended next question

**Q-276-16** from Slice 4 §70 is now answered by Slice 5 evidence: *adding the nullable field breaks nothing.* The next natural experiment is:

- **Q-276-17.** *If the deterministic backfill script runs on the current DB (62 deterministic rows → CHARACTER/UNIVERSE + 10 ambiguous rows stay NULL), does the DB end up in the shape §55 predicts?* Falsifiable by writing the backfill inside `transaction.atomic()` and rolling back before commit — pure verification, no persisted change. This is the smallest Stage 2 dry-run.

Deferred to a future slice pending Chris authorization.

## §85. Slice 5 checklist

- [x] Verify baseline before Stage 1 (§72 preamble + task 26)
- [x] Slice 5 falsifiable question stated (§72)
- [x] Add `AudienceScope` `TextChoices` enum in `models.py` (§73)
- [x] Add nullable `audience_scope` field on `KnowledgeDocument` (§73)
- [x] Zero default that would classify any row (`null=True, default=None`) (§73)
- [x] Zero invariant enforcement in the model layer (§73 + §77 D-tests)
- [x] Generate migration `0007_session276_audience_scope.py` via `makemigrations` (§74)
- [x] Verify pure `AddField` with `null=True` (§74 generated SQL: `ADD COLUMN varchar(20) NULL`)
- [x] Serializer non-exposure verified via explicit `Meta.fields` list (§75)
- [x] Admin `readonly_fields` extended to include `audience_scope` (§76)
- [x] No retrieval change (§78.2 — 221 embeddings tests pass unchanged)
- [x] No mutation-path change (ingestion / views / signals unchanged)
- [x] Stage 1 inertness test module created — 9 tests covering A/B/C/D (§77)
- [x] `manage.py migrate embeddings` applies cleanly (§78.1)
- [x] Stage 1 tests pass (§78.2: 9/9)
- [x] SESSION 275 lifecycle regression passes (§78.2: 13/13)
- [x] Embeddings app regression passes (§78.2: 221/221)
- [x] Spokespeople + universe + compositions regression passes (§78.2: 1424/1424)
- [x] Post-migration DB: total 72 KDs, all `audience_scope IS NULL` (§78.3)
- [x] Slice 4 §55 bucket counts still match exactly (§78.3)
- [x] 9 chriss-workspace legacy KDs unchanged except new NULL column (§78.3)
- [x] Ruby Class C/D unchanged except new NULL column (§78.3)
- [x] No inactive rows appeared (0/72) (§78.3)
- [x] No M2M / universe / is_active / deactivated_reason values changed (§78.3)
- [x] Prediction vs actual: every prediction supported, zero falsifications (§79)
- [x] Files changed inventory (§80)
- [x] Explicit STOP gate (§83)
- [x] Zero provider spend; no SPA files touched; no commit/push
- [ ] Chris review + Stage 2 scoping decision (§82)

---

**End of SESSION 276 Slice 5 / Delta Stage 1. Field added; migration applied; every regression passes; DB verified inert. STOP before Stage 2. Awaiting Chris authorization for (a) commit of Slice 5 changes and (b) any subsequent stage scope.**

**Slice 5 landed commit SHA:** `ee9efd7` (`feat(session-276): Slice 5 / Delta Stage 1 — inert audience_scope substrate`). Pushed to `origin/main`. Post-push `main == origin/main == ee9efd7`; working tree clean.

---

# SESSION 276 — Slice 6 / Delta Stage 2 backfill rehearsal (Q-276-17)

**Status.** READ-ONLY / ROLLBACK-ONLY data-migration rehearsal. Answers Slice 4 §70 Q-276-17. Does NOT persist any Stage 2 assignment. Does NOT create the Stage 2 migration. Substrate from Slice 5 is the landed `audience_scope` field.

**Slice 6 baseline.** `main == origin/main == ee9efd7` (Slice 5 landing SHA). Working tree clean at slice start. 72 KDs; all `audience_scope IS NULL`; Slice 5 verification carried forward.

**Load-bearing invariants carried forward:** SESSION 275 §23 audience-broadening prohibition; Slice 2 §22 SE-vs-SF audience refinement; Slice 4 §66 Delta model + §55 migration bucket inventory.

## §86. Slice 6 falsifiable question — Q-276-17

> If the deterministic Delta backfill logic runs against the current real `KnowledgeDocument` dataset inside an explicitly rolled-back transaction, does it produce exactly the migration shape predicted by Slice 4:
>
> - 59 rows → `CHARACTER`
> - 3 evidence-backed rows → `UNIVERSE`
> - 10 ambiguous rows → remain `NULL`
> - 0 rows → `WORKSPACE`
> - 0 rows → `NONE`
>
> with no changes to any other `KnowledgeDocument` fields, M2M rows, Universes, lifecycle state, chunks, or retrieval behavior?

**Prediction:** yes. The prediction is deterministic — Slice 4 §55 established the bucket counts and the exact 3 UNIVERSE canon IDs + 10 ambiguous IDs from a fresh full-DB read. Slice 6 mechanically verifies against live DB state.

## §87. Fresh Slice 6 DB baseline (read-only, pre-rehearsal)

Executed at Slice 6 start; identical to Slice 5 §78.3.

```
total KDs: 72
audience_scope distribution: {None: 72}

Shape buckets:
  (active=True, universe=False, m2m_nonempty=False, reason=''): 10   [10 ambiguous]
  (active=True, universe=False, m2m_nonempty=True,  reason=''): 49   [CHARACTER legacy]
  (active=True, universe=True,  m2m_nonempty=False, reason=''):  3   [3 UNIVERSE canon candidates]
  (active=True, universe=True,  m2m_nonempty=True,  reason=''): 10   [CHARACTER Universe-scoped]
  inactive: 0

CHARACTER target: 49 legacy + 10 Universe = 59

3 UNIVERSE canon candidates (universe=U + M2M=∅, active):
  8f825c98-f420-4867-8700-6d4db6832d9d  ws=chriss-workspace          title='Fox & Flour Bakery — House Policies & Hours'
  d8ab3d2c-cab3-41f3-91a1-bab8ba88f5b6  ws=session272-rivet-debug-ctl title='RIVET-DEBUG (CTL) — SESSION 272 experimental substrate'
  64c91888-5534-418b-bbe2-33743f815bcf  ws=session272-rivet-debug-exp title='RIVET-DEBUG (EXP) — SESSION 272 experimental substrate'

10 ambiguous rows (active + universe=NULL + M2M=∅):
  33c07feb-65ee-4ed3-8fc0-0f2fc33600c7  ws=admins-workspace   title="Wikipedia is trafilatura's home turf"
  aa90d895-cac9-41d4-b505-f2b23ffd5241  ws=chriss-workspace   title='About Hearth & Hollow Books'
  e37ea174-98e8-4588-a690-81f6e1bbfe4b  ws=chriss-workspace   title='How We Recommend Books'
  b58efd31-d05c-4008-beac-3a75755e5c6b  ws=chriss-workspace   title="Children's Reading"
  7f41d8e3-9be0-4591-9648-8c901861628d  ws=chriss-workspace   title='Bookstore Events'
  c408656d-191d-49be-a92d-8721aa294b58  ws=chriss-workspace   title='Supporting Local Authors'
  0088f31f-56fc-4e66-837a-f5391d6bbd94  ws=chriss-workspace   title='Helping Customers Find Their Next Read'
  7ecde40b-6d72-45eb-b676-6feb260e2ff8  ws=chriss-workspace   title='Tulsi — Core Identity and Public Purpose'
  8c6f0c14-b2c9-4161-b6b7-a17d3f9b4545  ws=chriss-workspace   title='TANK — AUTOMOTIVE FINANCING CONTENT KNOWLEDGE'
  90ad200c-5019-4036-82e9-a1ccc5cbce72  ws=chriss-workspace   title='Riggs'
```

Zero drift from Slice 5. Zero new rows. Zero inactive. Zero non-NULL `audience_scope`. The 3 UNIVERSE canon candidates match Slice 4 §55.1 exactly; the 10 ambiguous rows match Slice 4 §55.2 exactly.

## §88. Deterministic classification rules (as rehearsed)

Rules are Slice 4 §55.1 + §55.2 verbatim; no new rules invented.

- **Rule A — CHARACTER.** Every KD with M2M count ≥ 1 gets `audience_scope=CHARACTER`. Applies regardless of `universe` (legacy or Universe-scoped). Positive evidence: the M2M itself.
- **Rule B — UNIVERSE.** Only the 3 frozen evidence-backed IDs (§87) receive `audience_scope=UNIVERSE`. Not applied to any other `universe != NULL AND M2M empty` row. **Frozen ID set embedded as a constant — see §92 for rationale.**
- **Rule C — NULL preserved.** The 10 ambiguous rows stay `audience_scope IS NULL`. No implicit classification. Post-Delta operator triage will decide each explicitly.
- **Rule D — inactive rows.** Zero in the current DB. If any existed, the rehearsal would STOP before applying rules — Stage 2 semantics for inactive rows are deferred to a later slice.

## §89. Rehearsal mechanism

Executed via `manage.py shell` (single Python process, single DB connection). Structure:

```python
class ForcedRollback(Exception): ...

before = full_fingerprint()
try:
    with transaction.atomic():
        # Rule A
        KnowledgeDocument.objects.annotate(spc=Count("spokespeople")) \
            .filter(spc__gt=0).update(audience_scope=AudienceScope.CHARACTER)
        # Rule B
        KnowledgeDocument.objects.filter(pk__in=UNIVERSE_CANON_IDS) \
            .update(audience_scope=AudienceScope.UNIVERSE)
        during = full_fingerprint()
        # invariant assertions ...
        raise ForcedRollback  # mechanical rollback trigger
except ForcedRollback:
    pass
after = full_fingerprint()
assert before == after  # rollback proof
```

`transaction.atomic()` guarantees rollback on any raised exception. `ForcedRollback` is a purpose-defined marker exception so the rehearsal cannot be silenced by any real error being swallowed. `full_fingerprint()` reads persisted state via a fresh queryset — after the `except` block, Django's connection returns to the pre-atomic autocommit state and reads see committed data only.

**Why this is a mechanical proof, not intent-based:** the rollback is triggered by an exception INSIDE the atomic block; Django's `atomic` context manager unwinds via `__exit__(exc_type, ...)` and issues a ROLLBACK to the DB. The AFTER fingerprint is a fresh query against the committed data. If any assignment had leaked past ROLLBACK, `after.audience_scope_dist` would show non-None values.

## §90. Fingerprints (BEFORE / IN-TX / AFTER-ROLLBACK)

```
=== BEFORE fingerprint ===
  kd_count: 72
  chunk_count: 1149
  m2m_count: 62
  kd_rows_hash: -7801475400362189577
  m2m_rows_hash: -8154885081713289592
  audience_scope_dist: {None: 72}

=== IN-TRANSACTION fingerprint (post-writes, pre-rollback) ===
  kd_count: 72
  chunk_count: 1149
  m2m_count: 62
  kd_rows_hash: -5078510630773828736             ← CHANGED (audience_scope column mutated)
  m2m_rows_hash: -8154885081713289592            ← UNCHANGED (M2M rows untouched)
  audience_scope_dist: {'universe': 3, 'character': 59, None: 10}

=== FORCED ROLLBACK executed ===

=== AFTER-ROLLBACK fingerprint ===
  kd_count: 72
  chunk_count: 1149
  m2m_count: 62
  kd_rows_hash: -7801475400362189577             ← RESTORED (matches BEFORE)
  m2m_rows_hash: -8154885081713289592
  audience_scope_dist: {None: 72}

=== ROLLBACK PROOF ===
  BEFORE == AFTER for every fingerprint field
  Zero rehearsal assignments persisted; DB returned to Stage 1 baseline exactly
```

**Independent post-rehearsal recheck** (fresh `manage.py shell -c` invocation, new DB connection):

```
post-rehearsal: total=72, distribution={None: 72}, inactive=0
```

Zero persistence confirmed by two independent read paths.

## §91. In-transaction invariant assertions (all passed)

Under the mid-rehearsal DB state, before the forced rollback:

| Invariant | Assertion | Result |
|---|---|---|
| Distribution — CHARACTER | count == 59 | PASS |
| Distribution — UNIVERSE | count == 3 | PASS |
| Distribution — NULL | count == 10 | PASS |
| Distribution — WORKSPACE | count == 0 (absent from dict) | PASS |
| Distribution — NONE | count == 0 (absent from dict) | PASS |
| Rule A shape — CHARACTER + M2M ≥ 1 | 0 rows violate | PASS |
| Rule B shape — UNIVERSE + universe non-NULL | 0 rows violate | PASS |
| Rule B identity — UNIVERSE row IDs == frozen 3 | exact set match | PASS |
| Rule C — 10 ambiguous stay NULL | every ambiguous ID verified `audience_scope is None` | PASS |
| Rule D — no inactive rows | count == 0 | PASS |
| Zero-change vector — kd_count | == 72 (unchanged) | PASS |
| Zero-change vector — chunk_count | == 1149 (unchanged) | PASS |
| Zero-change vector — m2m_count | == 62 (unchanged) | PASS |
| Zero-change vector — m2m_rows_hash | == BEFORE (M2M rows untouched) | PASS |

Every assertion passed. The only field that changed inside the transaction was `audience_scope` (kd_rows_hash diverged as expected); every other field on every row was byte-identical.

## §92. Eventual migration implementation-shape analysis

Not a design commitment — deferred to a future authorized slice. Recorded here so Chris can review before Stage 2 is scoped.

### §92.1 Rule A — CHARACTER via M2M existence

Can be expressed generically without embedding IDs:

```python
KnowledgeDocument.objects.annotate(spc=Count("spokespeople")) \
    .filter(spc__gt=0).update(audience_scope=AudienceScope.CHARACTER)
```

This is safe as a **generic** predicate because the shape "has ≥1 explicit spokesperson attach row" is definitionally character-scoped — it was explicit at attach time. No historical drift risk: if a future migration re-runs, additional rows with new attach rows correctly receive CHARACTER; existing CHARACTER rows are idempotent.

**Verdict:** Rule A is safe as a generic `.filter(spc__gt=0).update(...)` inside the migration.

### §92.2 Rule B — UNIVERSE with frozen IDs

The generic predicate `universe != NULL AND M2M empty` **cannot** be used safely because it would sweep any future row with that shape — including a future orphan whose signal writes `audience_scope=NONE` and then somehow reverts, or a future data-migration bug that creates a row with the same shape. The whole point of Slice 4 is to STOP deriving audience from shape ambiguity.

**Recommended shape for the Stage 2 migration** — embed the 3 UUIDs as explicit historical constants:

```python
# SESSION 276 Slice 4 §55.1 evidence-backed intentional UNIVERSE canon.
# Frozen list — do NOT extend without a new audit slice.
UNIVERSE_CANON_ROWS_20260821 = [
    "8f825c98-f420-4867-8700-6d4db6832d9d",  # Ruby Fox&Flour House Policies & Hours
    "d8ab3d2c-cab3-41f3-91a1-bab8ba88f5b6",  # SESSION 272 rivet-debug-ctl substrate
    "64c91888-5534-418b-bbe2-33743f815bcf",  # SESSION 272 rivet-debug-exp substrate
]
KnowledgeDocument.objects.filter(pk__in=UNIVERSE_CANON_ROWS_20260821) \
    .update(audience_scope=AudienceScope.UNIVERSE)
```

Frozen IDs give the migration a **deterministic meaning relative to the 2026-08-21 dataset**. Future rows of the same shape (`universe != NULL AND M2M empty`) do NOT receive UNIVERSE from this migration — they will be classified by whatever mechanism owns audience assignment at their create time (Stage 3+).

### §92.3 Rule C — NULL preserved

No code needed; the field is already NULL for every row post-Stage-1. The migration simply skips these 10 rows. Operator triage (Stage 4) will assign explicit values.

### §92.4 Rule D — inactive rows

Zero exist today. Migration should guard with a preflight assertion:

```python
if KnowledgeDocument.objects.filter(is_active=False).count() > 0:
    raise RuntimeError(
        "Stage 2 preflight failed: inactive KDs present. Stage 2 does not "
        "define semantics for inactive rows — see Slice 4 §51 rows 10-15 + "
        "future signal extension. Halt and design before proceeding."
    )
```

If any orphan-archived row exists at the time of Stage 2 migration, it needs `audience_scope=NONE` (Slice 4 §51 row 15) — but that logic belongs to the SESSION 275 signal extension (Q-276-18), NOT to Stage 2. Preflight ensures the two migrations are ordered correctly.

### §92.5 Idempotency

The proposed migration is **idempotent** by construction:

- Rule A `.filter(spc__gt=0).update(audience_scope=CHARACTER)` — running twice sets the same value. No side effect.
- Rule B `.filter(pk__in=[3 constants]).update(audience_scope=UNIVERSE)` — running twice sets the same value.
- Rule C — no code; no-op.
- Rule D — preflight raises if state has drifted; no partial mutations.

Two runs produce identical DB state to one run.

### §92.6 Django mechanism

**`RunPython` with an explicit forward + reverse function pair** is the smallest appropriate Django mechanism. The migration is data-only (no schema change); `RunPython` is designed for exactly this. No `RunSQL` — the ORM `.update()` calls are Postgres-portable and readable.

### §92.7 Reverse migration

The reverse function should ONLY revert the two deterministic assignments performed by the forward function. It should NOT sweep every `audience_scope` back to NULL — that could reverse legitimate Stage 3+ mutations if Stage 2 is rolled back after later stages have deployed.

```python
def reverse(apps, schema_editor):
    KnowledgeDocument = apps.get_model("embeddings", "KnowledgeDocument")
    # Undo Rule A: revert every CHARACTER row to NULL (only if we still
    # believe every CHARACTER value was set by THIS migration; if Stage 3
    # has been deployed on top, that assumption is false — see caveat).
    # Undo Rule B: revert exactly the 3 frozen IDs to NULL.
    KnowledgeDocument.objects.filter(pk__in=UNIVERSE_CANON_ROWS_20260821) \
        .update(audience_scope=None)
    # Rule A reverse is unsafe past Stage 3 → document as "reverse only
    # meaningful if immediately after forward". If Chris wants a strict
    # reverse, we can add a companion tracking table (overkill for now).
```

**Documented caveat:** if Stage 3 (mutation-surface updates writing `audience_scope` on new/edited KDs) has deployed before Stage 2 is reversed, some CHARACTER values were set by Stage 3, not Stage 2. Reversing Rule A generically would clobber those. Practical guidance: the Stage 2 reverse is only meaningful for immediate rollback (before Stage 3 code lands). Longer-term rollback requires re-running the Stage 2 forward or a fresh audit.

**Verdict:** the migration file itself is small (~40 lines including docstring, constants, forward, reverse). Slice 6 does not create it.

## §93. Prediction vs actual

| Prediction (§86) | Actual | Status |
|---|---|---|
| `CHARACTER = 59` | `character: 59` in IN-TRANSACTION distribution | ✓ |
| `UNIVERSE = 3` | `universe: 3` | ✓ |
| `NULL = 10` | `None: 10` | ✓ |
| `WORKSPACE = 0` | absent from distribution dict | ✓ |
| `NONE = 0` | absent from distribution dict | ✓ |
| No changes to other fields | m2m_rows_hash + chunk_count + m2m_count unchanged mid-transaction; kd_rows_hash restored post-rollback | ✓ |
| Rollback returns DB to exact BEFORE state | BEFORE == AFTER for every fingerprint field | ✓ |
| Zero persistence | Independent recheck shows `distribution={None: 72}` | ✓ |

**Q-276-17 CONFIRMED.** Deterministic classification produces the exact predicted distribution under mechanically rolled-back transaction. Rule A + Rule B assignments together cover 62/72 rows; Rule C leaves 10/72 ambiguous rows correctly untouched.

## §94. Unresolved questions

Carried forward from Slice 4 §67 + Slice 5 §81 (all still open):

- Migration-only NULL vs explicit PENDING (Slice 4 §67.5). Slice 6 evidence continues to support NULL as sufficient.
- Auto-quarantine at Stage 6 vs indefinite operator triage (§67.6).
- Preserve `OrphanRevivalRejected` gate through Stage 7 or retire (§67.7).
- Companion audience-decision-provenance model (§67.8).
- Explicit audience picker in SPA (§67.9).
- `clean()` vs `pre_save` vs `m2m_changed` for invariant #1 (§67.10).
- Provenance direction Alpha vs Beta.
- Bundle vs split.

New from Slice 6 (§92):

- (§94.1) **Should Stage 2 migration embed a preflight assertion for inactive rows?** §92.4 recommends yes; Chris confirms shape.
- (§94.2) **Should Stage 2 reverse migration be a strict inverse (only undo forward) or a generic reset to NULL?** §92.7 recommends strict inverse with a documented "only safe immediately after forward" caveat.
- (§94.3) **Which stage owns the SESSION 275 signal extension that stamps `audience_scope=NONE` on future orphan-archive events?** Slice 4 §57.1 placed it in Stage 3 (mutation-surface pass). Ordering matters — Stage 2 depends on it NOT firing during backfill (which it won't, because Stage 2 doesn't delete Teammates). Post-Stage-2 the signal must exist before any real orphan-archive fires in production.
- (§94.4) **Rehearsal-only script — retain or discard?** The Slice 6 rehearsal was executed via a one-shot `manage.py shell << PYEOF` heredoc; no file was created. If Chris wants a permanent regression harness that runs the rehearsal-with-rollback as a pytest test, that would live in `apps/embeddings/tests/`. Not currently authorized.

## §95. Recommendation

**Q-276-17 is confirmed. Direction Delta Stage 2 backfill algorithm is validated deterministic for the current dataset.** Slice 6 does not authorize creating the Stage 2 migration.

Recommended shape for the eventual Stage 2 migration (§92):

- Django `RunPython` with explicit forward + reverse.
- Rule A generic (`.filter(spc__gt=0).update(...)`).
- Rule B with the 3 frozen UUIDs embedded as constants (`UNIVERSE_CANON_ROWS_20260821`).
- Preflight assertion that zero inactive rows exist (guards against Stage 3 signal-extension ordering issues).
- Reverse strictly inverts what forward did.
- Idempotent by construction.
- Docstring citing Slice 4 §55.1 evidence + Slice 6 §90 rehearsal fingerprints.

**Migration file estimated size:** ~40 lines including docstring, constants, forward, reverse.

Before Slice 7 (or equivalent), Chris + ChatGPT should decide:

1. Confirm the Stage 2 migration shape (§92) — accept or refine.
2. Confirm §94.1-§94.3 residuals.
3. Decide whether Stage 2 migration lands standalone or bundled with the Q-276-18 signal extension.
4. Confirm the frozen ID list (§92.2) is the correct set — one last sanity check on the 3 UUIDs before they become permanent history-code constants.

## §96. Explicit STOP gate

**STOP.** Slice 6 authorizes no further work.

Do NOT begin:

- Real Stage 2 data migration file (0008)
- Q-276-18 signal extension for `audience_scope=NONE` on orphan-archive
- Provenance work (Direction Alpha / Beta)
- Mutation-surface changes to populate `audience_scope`
- Retrieval predicate change
- Operator triage UI
- DB CHECK constraints
- NOT NULL constraint
- SPA-side changes
- Removal of SESSION 275 protections

Even though Q-276-17 passed cleanly.

## §97. Smallest recommended next question

**Q-276-22.** *If the Stage 2 migration (§92 shape) is landed on top of Slice 5 and run against the current DB, does the persisted post-migration state exactly match Slice 6 §90 IN-TRANSACTION fingerprint?* Falsifiable by writing the migration file and running `manage.py migrate embeddings` — but this is the actual Stage 2 execution, so requires explicit Chris authorization.

(Q-276-18 signal extension remains available as an alternative next slice, per §94.3.)

## §98. Slice 6 checklist

- [x] Land Slice 5 checkpoint first (Step 0) — commit `ee9efd7` pushed to `origin/main`
- [x] Slice 6 baseline verified — `main == origin/main == ee9efd7`, working tree clean at slice start
- [x] Fresh read-only DB inventory (§87) — 72 KDs, 10 ambiguous, 3 UNIVERSE canon, 0 inactive
- [x] Deterministic classification rules verified against Slice 4 §55 (§88)
- [x] Rehearsal mechanism designed with `transaction.atomic()` + `ForcedRollback` (§89)
- [x] BEFORE fingerprint captured (§90)
- [x] IN-TRANSACTION distribution captured (§90) — CHARACTER=59, UNIVERSE=3, NULL=10
- [x] All in-transaction invariants asserted (§91) — 14 assertions, all passed
- [x] Forced rollback executed (§90)
- [x] AFTER-ROLLBACK fingerprint captured (§90) — matches BEFORE exactly
- [x] Independent post-rehearsal recheck via fresh DB connection (§90) — confirms zero persistence
- [x] Prediction vs actual (§93) — Q-276-17 CONFIRMED
- [x] Eventual migration shape analysis (§92) — no migration created
- [x] Unresolved questions (§94)
- [x] Recommendation (§95)
- [x] Explicit STOP gate (§96)
- [x] Smallest next question Q-276-22 (§97)
- [x] Zero KD rows persistently modified; zero migrations created; zero mutation-surface changes; zero signal changes; zero retrieval changes; zero SPA changes; zero provider spend
- [x] Commit + push Slice 6 doc-only change — landed as `5f87c06`
- [x] Chris + ChatGPT review + Slice 7 scoping decision (§95) — Q-276-22 authorized

---

**End of SESSION 276 Slice 6 / Delta Stage 2 rehearsal. Q-276-17 CONFIRMED — deterministic classification produces the exact Slice 4 §55 distribution under a mechanically rolled-back transaction. Zero data persisted. Stage 2 migration NOT authorized to land. STOP for Chris + ChatGPT review of §95 recommendation, §96 gate, and §97 next question.**

**Slice 6 landed commit SHA:** `5f87c06` (`docs(session-276): Slice 6 — verify deterministic audience backfill rehearsal`). Pushed to `origin/main`. Post-push `main == origin/main == 5f87c06`; working tree clean.

**Slice 6 SHA-record follow-up:** `0780f82` (`docs(session-276): record Slice 6 landed SHA 5f87c06`) — doc-only checklist + inline SHA record.

---

# SESSION 276 — Slice 7 / Delta Stage 2 persisted deterministic backfill (Q-276-22)

**Status.** IMPLEMENTATION SLICE — persists the audience classification rehearsed and confirmed in Slice 6. Chris + ChatGPT authorized the smallest next question (Q-276-22) with the approved product decisions from §94–§97.

**Slice 7 baseline.** `main == origin/main == 0780f82` (Slice 6 SHA-record). Working tree clean at slice start. Migration head pre-slice: `0007_session276_audience_scope` (Slice 5 Stage 1 substrate). Slice 6 fingerprints carried forward:

- kd_count = 72
- chunk_count = 1149
- m2m_count = 62
- m2m_rows_hash = `-8154885081713289592`
- audience_scope_dist = `{None: 72}`

**Authorized decisions carried forward** (from Slice 6 §94–§97):

1. Direction Delta remains approved.
2. Migration-only unresolved representation stays `audience_scope=NULL`; no permanent PENDING enum value.
3. Stage 2 migration MUST include a preflight abort on any inactive KD.
4. Reverse migration must be a STRICT INVERSE — not a generic reset.
5. Stage 2 lands STANDALONE (Q-276-18 signal extension deferred).
6. SESSION 275 signal extension stamping `audience_scope=NONE` remains Stage 3 work.
7. The 10 ambiguous rows remain NULL; no classify / quarantine / archive.
8. No provenance implementation in this slice.
9. No retrieval change.
10. No serializer/API audience behavior change.
11. No SPA change.

**Frozen UNIVERSE-canon set** approved for Stage 2 migration:

- `8f825c98-f420-4867-8700-6d4db6832d9d` — Ruby / Fox & Flour Bakery House Policies & Hours
- `d8ab3d2c-cab3-41f3-91a1-bab8ba88f5b6` — SESSION 272 rivet-debug-ctl substrate
- `64c91888-5534-418b-bbe2-33743f815bcf` — SESSION 272 rivet-debug-exp substrate

## §99. Slice 7 falsifiable question — Q-276-22

> If the Stage 2 migration using the Slice 6 §92 shape is landed on top of the existing Delta Stage-1 substrate and run against the current DB, does the persisted post-migration state exactly match the Slice 6 §90 in-transaction rehearsal fingerprint?

**Prediction:** yes. Persisted distribution: CHARACTER=59, UNIVERSE=3, NULL=10, WORKSPACE=0, NONE=0. Only `audience_scope` changes on the 62 deterministic rows. Zero change to any other field, M2M row, chunk, or lifecycle state.

## §100. Final frozen-3 UUID sanity check (pre-migration)

Executed at Slice 7 start; every check passed:

```
=== Slice 7 fresh baseline ===
total KDs: 72
audience_scope distribution: {None: 72}
inactive rows: 0
chunk count: 1149
M2M through-rows: 62

Shape buckets (unchanged from Slice 6 §87):
  (active=True, universe_set=False, m2m_nonempty=False): 10
  (active=True, universe_set=False, m2m_nonempty=True):  49
  (active=True, universe_set=True,  m2m_nonempty=False):  3
  (active=True, universe_set=True,  m2m_nonempty=True):  10

=== FINAL frozen UNIVERSE-canon sanity check ===
  8f825c98.. OK | ws=chriss-workspace          | title='Fox & Flour Bakery — House Policies & Hours'
  d8ab3d2c.. OK | ws=session272-rivet-debug-ctl | title='RIVET-DEBUG (CTL) — SESSION 272 experimental substrate'
  64c91888.. OK | ws=session272-rivet-debug-exp | title='RIVET-DEBUG (EXP) — SESSION 272 experimental substrate'

  ALL THREE FROZEN CANON IDS PASS SANITY CHECK
```

Every frozen ID: exists, active, universe non-null, M2M empty, `audience_scope=NULL`, correct workspace, correct title prefix. Zero drift since Slice 4 §55.1 and Slice 6 §87 evidence. Safe to proceed with migration.

## §101. Migration implementation shape

New file: `shell/apps/embeddings/migrations/0008_session276_stage2_backfill.py` (~120 lines with docstrings).

### §101.1 Structure

- Django `RunPython` data migration with `apply_forward` + `apply_reverse` functions and a dedicated `Stage2PreflightError(RuntimeError)` exception subclass.
- Historical model access via `apps.get_model("embeddings", "KnowledgeDocument")` — never imports the runtime model class or the `AudienceScope` enum.
- Choice values as string literals (`"character"`, `"universe"`) — not the runtime enum — so future model-code refactors cannot alter this migration's meaning.
- Frozen constant list: `UNIVERSE_CANON_ROWS_20260821 = [3 UUIDs]` embedded as historical fact.

### §101.2 Forward operation (`apply_forward`)

1. **PREFLIGHT.** Raise `Stage2PreflightError` if `KnowledgeDocument.objects.filter(is_active=False).count() > 0`. Message cites the Slice 4 §55 / Slice 6 §87 zero-inactive assumption and the Q-276-18 signal-extension ordering dependency.
2. **Rule A — CHARACTER.** `KnowledgeDocument.objects.annotate(_sp_count=Count("spokespeople")).filter(_sp_count__gt=0).update(audience_scope="character")`. Generic predicate — surviving explicit M2M is positive evidence.
3. **Rule B — UNIVERSE.** `KnowledgeDocument.objects.filter(pk__in=UNIVERSE_CANON_ROWS_20260821).update(audience_scope="universe")`. Frozen-3 only. NOT a generic shape predicate.
4. **Rule C — NULL preserved.** No code — the 10 ambiguous rows are untouched by construction (Rule A shape-filter excludes empty M2M; Rule B PK-filter excludes non-frozen rows).

### §101.3 Reverse operation (`apply_reverse`)

Strict inverse of forward:

1. **Reverse Rule B.** `KnowledgeDocument.objects.filter(pk__in=UNIVERSE_CANON_ROWS_20260821, audience_scope="universe").update(audience_scope=None)`. `audience_scope="universe"` filter guards against clobbering a Stage-3+ reassignment.
2. **Reverse Rule A.** `KnowledgeDocument.objects.annotate(_sp_count=Count("spokespeople")).filter(_sp_count__gt=0, audience_scope="character").update(audience_scope=None)`. Same guard shape.

Documented caveat: reverse is strict-inverse only pre-Stage-3. Post-Stage-3 rollback may clobber Stage-3 assignments; that's a downstream ordering concern, not a Slice 7 responsibility.

### §101.4 Idempotency + generic properties

- Forward is idempotent by construction — Rule A sets same value; Rule B sets same value; running twice = running once.
- Reverse is idempotent (filter matches nothing on second call).
- No `RunSQL`, no raw connection cursor, no schema change.
- No dependency on runtime code beyond `django.db.models.Count`.

## §102. Migration regression tests

New test module: `shell/apps/embeddings/tests/test_stage2_backfill_migration.py` (~275 lines, 6 test cases).

Imports the migration module via `importlib.import_module("apps.embeddings.migrations.0008_session276_stage2_backfill")` because Python cannot `import` a module whose name starts with a digit. Invokes `apply_forward` / `apply_reverse` directly with the runtime `django.apps.apps` registry, which is contract-equivalent to the historical registry Django passes at migration time (both provide `get_model("embeddings", "KnowledgeDocument")` returning a queryset-capable class).

| Test | Coverage | Status |
|---|---|---|
| T1 `test_forward_classifies_character_universe_and_ambiguous` | Rule A + Rule B + Rule C together — synthesized rows in a test workspace get exactly the predicted classification | PASS |
| T2 `test_forward_does_not_falsely_classify_non_frozen_universe_row_as_universe` | An `(active, universe non-null, M2M empty)` row **not in the frozen set** stays NULL — the load-bearing shape-vs-identity guard | PASS |
| T3 `test_forward_aborts_when_any_inactive_row_exists` | Preflight raises `Stage2PreflightError` on any inactive KD; no partial CHARACTER writes leak | PASS |
| T4 `test_reverse_restores_stage1_state_for_forward_touched_rows` | Forward → reverse round-trips the audience_scope to NULL for rows the forward touched; ambiguous rows remain NULL | PASS |
| T5 `test_reverse_does_not_touch_unrelated_audience_values` | Reverse leaves WORKSPACE, NONE, off-frozen UNIVERSE, and CHARACTER-with-empty-M2M rows untouched — proves strict-inverse posture against future Stage-3+ mixed states | PASS |
| T6 `test_forward_is_idempotent` | Running forward twice = running forward once (state hash byte-identical) | PASS |

## §103. Pre- vs post-migration fingerprint

**Pre-migration** (§100 fresh baseline, matches Slice 6 §90 BEFORE):

```
kd_count: 72
chunk_count: 1149
m2m_count: 62
m2m_rows_hash: -8154885081713289592
audience_scope_dist: {None: 72}
inactive: 0
migration head: 0007_session276_audience_scope
```

**Post-migration** (fresh read after `manage.py migrate embeddings`):

```
kd_count: 72                                    ← unchanged
chunk_count: 1149                               ← unchanged
m2m_count: 62                                   ← unchanged
m2m_rows_hash: -8154885081713289592             ← byte-identical to Slice 6 §90 BEFORE
audience_scope_dist: {'universe': 3, 'character': 59, None: 10}   ← matches Slice 6 §90 IN-TRANSACTION
inactive: 0                                     ← unchanged
migration head: 0008_session276_stage2_backfill  ← advanced
```

**Every non-audience field is byte-identical.** The `m2m_rows_hash` match is the strongest single proof — every M2M through-row's `(knowledgedocument_id, teammate_id)` pair is unchanged.

## §104. Persisted classification proof

Full assertions run against live DB post-migration:

- Distribution: `CHARACTER=59 ✓  UNIVERSE=3 ✓  NULL=10 ✓  WORKSPACE=0 ✓  NONE=0 ✓`
- Every `CHARACTER` row has M2M ≥ 1: **0 violations**.
- The 3 frozen UUIDs are `UNIVERSE`:
  ```
  8f825c98.. UNIVERSE ✓
  d8ab3d2c.. UNIVERSE ✓
  64c91888.. UNIVERSE ✓
  ```
- The 10 ambiguous rows remain `NULL`:
  ```
  33c07feb.. NULL ✓  ("Wikipedia is trafilatura's home turf")
  aa90d895.. NULL ✓  ('About Hearth & Hollow Books')
  e37ea174.. NULL ✓  ('How We Recommend Books')
  b58efd31.. NULL ✓  ("Children's Reading")
  7f41d8e3.. NULL ✓  ('Bookstore Events')
  c408656d.. NULL ✓  ('Supporting Local Authors')
  0088f31f.. NULL ✓  ('Helping Customers Find Their Next Read')
  7ecde40b.. NULL ✓  ('Tulsi — Core Identity and Public Purpose')
  8c6f0c14.. NULL ✓  ('TANK — AUTOMOTIVE FINANCING CONTENT KNOWLEDGE')
  90ad200c.. NULL ✓  ('Riggs')
  ```

## §105. Regression results

```
$ pytest apps/embeddings/tests/test_stage2_backfill_migration.py -v
6 passed in 3.92s                          # Slice 7 new tests

$ pytest apps/embeddings/tests/test_stage2_backfill_migration.py \
         apps/embeddings/tests/test_audience_scope_stage1.py \
         apps/spokespeople/tests/test_delete_orphan_archive.py -v
28 passed in 6.88s                         # Slice 7 + Slice 5 + SESSION 275 lifecycle

$ pytest apps/embeddings/ apps/spokespeople/ apps/universe/ apps/compositions/ -q
1651 passed, 2 warnings in 128.09s         # broader regression

$ python manage.py makemigrations --check embeddings
No changes detected in app 'embeddings'    # no schema drift
```

The 2 warnings are pre-existing DateTime naive-vs-aware unrelated to Slice 7 (identical warnings recorded in Slice 5 §78.2).

## §106. Prediction vs actual

| Prediction | Actual | Status |
|---|---|---|
| Persisted CHARACTER count = 59 | 59 | ✓ |
| Persisted UNIVERSE count = 3 | 3 | ✓ |
| Persisted NULL count = 10 | 10 | ✓ |
| Persisted WORKSPACE count = 0 | 0 (absent from distribution dict) | ✓ |
| Persisted NONE count = 0 | 0 (absent) | ✓ |
| Only `audience_scope` changes | `m2m_rows_hash` byte-identical; `chunk_count`, `m2m_count`, `kd_count` unchanged | ✓ |
| 10 ambiguous rows remain NULL | all 10 verified NULL individually | ✓ |
| No retrieval behavior change | retrieval.py unchanged; 221 embeddings tests pass | ✓ |
| No lifecycle behavior change | 13/13 SESSION 275 orphan tests pass; 0 inactive rows | ✓ |
| Persisted state matches Slice 6 §90 IN-TRANSACTION exactly | distribution + m2m_rows_hash + all bucket counts identical | ✓ |

**Q-276-22 CONFIRMED. Zero deviations. Zero unexpected findings.** Stage 2 migration is behaviorally identical to the Slice 6 rehearsal.

## §107. Files changed (Slice 7)

```
?? shell/apps/embeddings/migrations/0008_session276_stage2_backfill.py       (new — 120 lines with docstring)
?? shell/apps/embeddings/tests/test_stage2_backfill_migration.py             (new — 275 lines, 6 tests)
?? docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md                     (untracked; this Slice 7 section)
```

Zero SPA changes. Zero mutation-surface changes. Zero retrieval changes. Zero signal changes. Zero serializer changes. Zero admin changes. Zero constraint additions.

## §108. Unresolved questions

Carried from Slice 4 §67, Slice 5 §81, Slice 6 §94 (all still open):

- Q-276-18 signal extension stamping `audience_scope=NONE` on orphan-archive (Slice 4 §66 refinement 2; Slice 6 §94.3). Delayed to Stage 3.
- Provenance direction Alpha vs Beta (Slice 2 §24.1).
- Auto-quarantine at Stage 6 vs indefinite operator triage (§67.6).
- SPA audience-picker vs server-side inference (§67.9).
- Model-layer invariant enforcement mechanism (`clean()` vs `pre_save` vs `m2m_changed`) — Stage 5+.
- Bundle vs split (still open from Slice 1 §8.4).

**No new Slice-7-specific unresolved questions.** Every design assumption from Slice 4 §57.1 Stage 2 shape held.

## §109. Recommendation

**Stage 2 is complete and persisted. Direction Delta now has 62/72 rows carrying deterministic audience labels; 10 rows carry NULL awaiting operator triage.**

Retrieval still uses the empty-M2M-broadcast fallback (unchanged) — no runtime behavior change from Slice 7. The `audience_scope` column is populated for the deterministic subset but not yet consulted by retrieval or any mutation path.

Slice 7 does not authorize any further work. Each subsequent stage requires an independent Chris + ChatGPT decision:

- **Q-276-18 / Stage 3 signal extension.** Extend `_archive_orphaned_kds_on_teammate_delete` at `shell/apps/spokespeople/signals.py:196-200` to also stamp `audience_scope="none"` alongside `deactivated_reason="orphaned_by_teammate_delete"`. Small change (~2 lines in the `.update()` call + 1 signal test).
- **Stage 3 mutation-surface pass.** Extend ingestion `_persist`, `KnowledgeDocumentSerializer.create/update`, and `views.KnowledgeDocumentViewSet.attach/detach` to set `audience_scope` on writes. Preserves server-side inference (per Slice 4 §60).
- **Operator triage UI for the 10 ambiguous rows** (Stage 4).
- **Retrieval predicate switch** (Stage 5).
- **CHECK constraints + NOT NULL cutover** (Stage 6).

## §110. Explicit STOP gate

**STOP.** Slice 7 authorizes no further work.

Do NOT begin:

- Q-276-18 signal extension
- Mutation-surface population of `audience_scope` on writes
- Provenance work (Direction Alpha / Beta)
- Retrieval predicate change
- Operator triage UI for the 10 ambiguous rows
- DB CHECK constraints
- NOT NULL cutover
- SPA audience-picker or audience-visibility UI
- Removal of SESSION 275 protections

## §111. Smallest recommended next question

**Q-276-18.** *If the SESSION 275 `_archive_orphaned_kds_on_teammate_delete` signal is extended to also stamp `audience_scope="none"` alongside `deactivated_reason="orphaned_by_teammate_delete"` in its bulk `.update(...)`, does the SESSION 275 test 13 atomicity guarantee still hold, and do all 13 SESSION 275 lifecycle tests still pass?*

Falsifiable by writing the ~2-line signal patch + 1 new assertion in the existing atomicity test, then rerunning `apps/spokespeople/tests/test_delete_orphan_archive.py`. Small, well-scoped, and the natural next Delta step per Slice 4 §57.1 Stage 3.

## §112. Slice 7 checklist

- [x] Step 0 — commit + push Slice 6 SHA-record (commit `0780f82`)
- [x] Slice 7 fresh baseline verified (§100) — 72 KDs, all NULL, 0 inactive, migration head `0007`
- [x] Final frozen-3 UUID sanity check (§100) — all 3 pass every property
- [x] Migration `0008_session276_stage2_backfill.py` created (§101) — `RunPython` with forward + reverse + preflight
- [x] Historical model access via `apps.get_model` (§101.1)
- [x] Choice values as string literals (not runtime enum) (§101.1)
- [x] Frozen 3-UUID constant embedded (§101.1)
- [x] Preflight aborts on any inactive row (§101.2)
- [x] Rule A generic via `Count("spokespeople") > 0` (§101.2)
- [x] Rule B restricted to frozen 3 UUIDs (§101.2)
- [x] Rule C — no code touches ambiguous rows (§101.2)
- [x] Reverse is strict inverse (§101.3)
- [x] Reverse guarded by current-value filter (§101.3)
- [x] Migration tests added — 6 cases covering forward classification, no-false-Universe, preflight, reverse restore, reverse-no-clobber, idempotence (§102)
- [x] All 6 migration tests pass (§102)
- [x] Migration applied to local DB (§103) — `Applying embeddings.0008_session276_stage2_backfill... OK`
- [x] Post-migration distribution matches Slice 6 §90 IN-TRANSACTION exactly (§103, §104)
- [x] All 3 frozen UUIDs are UNIVERSE (§104)
- [x] All 10 ambiguous IDs remain NULL (§104)
- [x] Every CHARACTER row has M2M ≥ 1 (§104)
- [x] `m2m_rows_hash` byte-identical to Slice 6 §90 BEFORE (§103) — M2M untouched
- [x] `chunk_count`, `kd_count`, `m2m_count` unchanged (§103)
- [x] 28-test focused regression (Stage 2 + Stage 1 + SESSION 275 lifecycle) passes (§105)
- [x] 1651-test broader regression passes (§105)
- [x] `makemigrations --check` — no schema drift (§105)
- [x] Prediction vs actual — Q-276-22 CONFIRMED (§106)
- [x] Files changed inventory (§107)
- [x] Explicit STOP gate (§110)
- [x] Smallest next question Q-276-18 (§111)
- [x] Zero SPA / mutation-surface / retrieval / signal / serializer / admin / constraint changes; zero provider spend
- [x] Commit + push Slice 7 — landed as `65be308`
- [x] Chris + ChatGPT review + Slice 8 scoping decision (§109) — Q-276-18 authorized

---

**End of SESSION 276 Slice 7 / Delta Stage 2. Deterministic backfill persisted. Q-276-22 CONFIRMED — 62/72 rows classified (CHARACTER=59, UNIVERSE=3), 10 rows preserved NULL, zero non-audience state changed. Migration head advanced to `0008_session276_stage2_backfill`. STOP for Chris + ChatGPT review of §109 recommendation, §110 gate, and §111 Q-276-18 next question.**

**Slice 7 landed commit SHA:** `65be308` (`feat(session-276): Slice 7 / Delta Stage 2 — persist deterministic audience backfill`). Pushed to `origin/main`. Post-push `main == origin/main == 65be308`; working tree clean.

**Slice 7 SHA-record follow-up:** `8e268d5` (`docs(session-276): record Slice 7 landed SHA 65be308`) — doc-only checklist + inline SHA record.

---

# SESSION 276 — Slice 8 / Delta Stage 3A — orphan-archive stamps `audience_scope=none` (Q-276-18)

**Status.** IMPLEMENTATION SLICE — extends the SESSION 275 Teammate-delete orphan-archive `.update()` to atomically stamp `audience_scope='none'` alongside `is_active=False` and `deactivated_reason='orphaned_by_teammate_delete'`. Chris + ChatGPT authorized the smallest next question (Q-276-18) with the constraint that Slice 8 is limited to the lifecycle boundary only — no broader Stage 3B mutation-surface pass, no provenance, no retrieval change.

**Slice 8 baseline.** `main == origin/main == 8e268d5` (Slice 7 SHA-record). Working tree clean at slice start. Real-DB state carried forward from Slice 7:

- 72 KDs; `CHARACTER=59`, `UNIVERSE=3`, `NULL=10`, `WORKSPACE=0`, `NONE=0`
- 0 inactive rows
- 1149 chunks, 62 M2M through-rows
- Migration head: `0008_session276_stage2_backfill`

**Authorized product semantics** (from task):

For a true final-character orphan, the desired durable state is:

- `is_active=False`
- `deactivated_reason='orphaned_by_teammate_delete'`
- `audience_scope='none'`
- spokespeople M2M empty
- Universe preserved as historical/scope context
- chunks preserved
- embeddings preserved
- Composition provenance preserved

MUST NOT occur when:

- deleting one member of a multi-character KD leaves another member
- deleting an unrelated teammate near intentionally shared canon
- a KD was intentionally born empty/shared

## §113. Slice 8 falsifiable question — Q-276-18

> If the existing SESSION 275 Teammate-delete orphan archive operation is extended so that a true final-character orphan is stamped `audience_scope='none'` in the SAME archive write that sets `is_active=False` and `deactivated_reason='orphaned_by_teammate_delete'`, does the complete SESSION 275 lifecycle contract — especially bulk-delete behavior and failure-injection atomicity — remain correct?

**Prediction:** yes. The change is a one-field addition to the existing bulk `.update(...)`. All 5 existing SESSION 275 lifecycle guarantees plus the failure-injection atomicity contract must hold, with the new invariant added: true orphans get `NONE`; non-orphans preserve pre-delete `audience_scope`.

## §114. Exact signal diff (`shell/apps/spokespeople/signals.py`)

Two surgical changes to `_archive_orphaned_kds_on_teammate_delete`:

**1.** Lazy import extended to include `AudienceScope`:

```python
# Before:
from apps.embeddings.models import DeactivationReason, KnowledgeDocument

# After:
from apps.embeddings.models import (
    AudienceScope, DeactivationReason, KnowledgeDocument,
)
```

**2.** Bulk `.update()` extended with one field:

```python
# Before:
KnowledgeDocument.objects.filter(pk__in=orphan_ids).update(
    is_active=False,
    deactivated_reason=DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE,
    updated_at=timezone.now(),
)

# After:
KnowledgeDocument.objects.filter(pk__in=orphan_ids).update(
    is_active=False,
    deactivated_reason=DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE,
    audience_scope=AudienceScope.NONE,
    updated_at=timezone.now(),
)
```

Docstring block also extended with a SESSION 276 Slice 8 paragraph explaining why the NONE stamp belongs in the same `.update()` (atomicity inheritance from SESSION 275 test 13).

Zero other code changes anywhere. No refactor. No new signal. No pre_delete/post_delete restructuring. The `sp_count=0` filter (existing) still gates which KDs receive the stamp — narrowing deletes are excluded by construction.

## §115. Test changes (`shell/apps/spokespeople/tests/test_delete_orphan_archive.py`)

Extended the existing SESSION 275 lifecycle regression suite in place — same 13 test IDs, additional `audience_scope` assertions. Two new imports (`AudienceScope`) and one docstring update. No parallel test file created.

Per-test extensions:

| Test | New audience_scope assertions |
|---|---|
| Case 1 (singleton legacy orphan) | `kd.audience_scope is None` pre-delete (fixture default); `kd.audience_scope == AudienceScope.NONE` post-archive |
| Case 2 (singleton Universe orphan) | Same |
| Case 3 (multi-spokesperson narrowing) | Capture `pre_delete_audience_scope`; assert unchanged post-delete; assert `!= AudienceScope.NONE` |
| Case 4 (sequential final orphan) | Intermediate: unchanged. Final: `AudienceScope.NONE` |
| Case 5 (Class C canon + Universe-member delete) | `pre_delete_audience_scope` captured; unchanged post-delete; NOT NONE |
| Case 6 (Class A canon + unrelated delete) | Same as Case 5 |
| Case 7 (chunks + embeddings survive) | Post-archive: `AudienceScope.NONE` |
| Case 8 (Composition provenance) | Post-archive: `AudienceScope.NONE`; provenance still resolves |
| Case 9 (bulk QuerySet delete) | All 3 orphaned KDs (kd_a, kd_b, kd_shared) stamped `AudienceScope.NONE` |
| Case 10 (operator-delete vs orphan) | Operator-delete API path preserves `audience_scope` (Stage 3B scope, NOT changed here); orphan path stamps NONE |
| Case 11 (revival gate) | Post-archive NONE; rejected-revival preserves NONE. Post-successful-revival intentionally NOT asserted (Stage 3B revival extension will address the malformed CHARACTER-shape+NONE state that emerges — flagged as known transitional) |
| Case 12 (operator-delete revival) | No new assertions (operator-delete never touches audience_scope) |
| **Case 13 (atomicity failure-injection — LOAD-BEARING)** | Capture `original_audience_scope`; assert `kd.audience_scope == original_audience_scope` post-rollback — proves the NONE stamp rolls back atomically with the other lifecycle fields |

Total additions: ~30 lines across the 13 tests. Zero behavior weakening — every existing assertion still fires.

## §116. Extended lifecycle test results

```
$ pytest apps/spokespeople/tests/test_delete_orphan_archive.py -v
13 passed in 5.55s

  Case 1  test_last_spokesperson_delete_legacy_inactivates_kd            PASSED
  Case 2  test_last_spokesperson_delete_universe_inactivates_kd          PASSED
  Case 3  test_multi_spokesperson_delete_one_leaves_kd_active            PASSED
  Case 4  test_multi_spokesperson_delete_sequential_final_archives       PASSED
  Case 5  test_born_empty_class_c_canon_survives_universe_member_delete  PASSED
  Case 6  test_born_empty_class_a_canon_survives_unrelated_delete        PASSED
  Case 7  test_chunks_and_embeddings_survive_orphan_archive              PASSED
  Case 8  test_composition_provenance_resolves_after_orphan_archive      PASSED
  Case 9  test_bulk_queryset_delete_triggers_orphan_archive_per_row      PASSED
  Case 10 test_deactivated_reason_distinguishes_operator_delete_from_    PASSED
  Case 11 test_ingestion_revival_rejects_orphan_without_spokespeople     PASSED
  Case 12 test_ingestion_revival_of_operator_deleted_kd_still_works      PASSED
  Case 13 test_teammate_delete_atomic_if_orphan_archive_update_fails     PASSED
```

## §117. Per-scenario evidence

**A — Singleton orphan gets NONE** (Case 1 + Case 2): confirmed. Both legacy and Universe scopes stamp `AudienceScope.NONE` in the same archive write.

**B — Narrowing delete does NOT stamp NONE** (Case 3): confirmed. Pre-delete `audience_scope` captured (None in transitional fixture); post-A-delete audience_scope unchanged. `sp_count=0` signal filter excludes this KD from the archive candidate set.

**C — Intentional shared canon untouched** (Cases 5 + 6): confirmed. Empty-M2M canon KDs, when an unrelated teammate is deleted, retain their audience_scope. The `pre_delete` snapshot excludes them (deleted teammate was never in their M2M).

**D — Bulk / QuerySet delete** (Case 9): confirmed. `Teammate.objects.filter(pk__in=[a.pk, b.pk]).delete()` correctly archives `kd_a`, `kd_b`, and the last-teammate-standing `kd_shared` — all three stamped `NONE`.

**E — Atomic failure injection** (Case 13): confirmed. Injected `InjectedArchiveFailure` in the archive `.update()` triggers rollback of the entire delete plan. Post-rollback assertions verified:

- Teammate row still exists ✓
- KnowledgeDocument still exists ✓
- `is_active == original_is_active` (True) ✓
- `deactivated_reason == original_reason` ('') ✓
- **`audience_scope == original_audience_scope` (None) ✓** ← NEW Slice 8 assertion
- M2M through-row still exists ✓
- chunks unchanged ✓

The NONE stamp rolls back atomically with the other lifecycle fields because all three ship in the same `.update()` call.

**F — Preserved SESSION 275 semantics** (all 13 tests): confirmed. No pre-existing assertion was weakened; every SESSION 275 guarantee still fires.

## §118. Real-DB post-Slice-8 verification

Signal code changed; real DB rows did not change (no Teammate was deleted during Slice 8).

```
$ manage.py shell -c "..."
total=72
distribution={'universe': 3, 'character': 59, None: 10}
inactive=0
chunks=1149
m2m=62
```

Byte-identical to Slice 7 §103 post-migration state. Zero drift. Slice 8 changes future lifecycle behavior only.

## §119. Broader regression results

```
$ pytest apps/spokespeople/tests/test_delete_orphan_archive.py \
         apps/embeddings/tests/test_audience_scope_stage1.py \
         apps/embeddings/tests/test_stage2_backfill_migration.py -q
28 passed in 6.79s                          # extended lifecycle + Stage 1 + Stage 2 migration

$ python manage.py makemigrations --check embeddings
No changes detected in app 'embeddings'    # no schema drift

$ pytest apps/embeddings/ apps/spokespeople/ apps/universe/ apps/compositions/ -q
1651 passed, 2 warnings in 126.36s          # broader — same count as Slice 7
```

Every regression suite unchanged in count from Slice 7. The 2 warnings are pre-existing DateTime naive-vs-aware unrelated to Slice 8.

## §120. Prediction vs actual

| Prediction | Actual | Status |
|---|---|---|
| One tiny signal-write extension (~1 field to `.update()` + 1 import addition) | Exactly that; docstring block also extended for durability | ✓ |
| True orphan gets NONE (single delete) | Cases 1, 2 pass | ✓ |
| True orphan gets NONE (bulk delete) | Case 9: all 3 stamped NONE | ✓ |
| Non-orphans (narrowing) preserve audience_scope; NOT NONE | Cases 3, 4 (intermediate) pass | ✓ |
| Intentional canon untouched; NOT NONE | Cases 5, 6 pass | ✓ |
| Failure injection proves atomicity including audience_scope rollback | Case 13 pass with new `original_audience_scope` assertion | ✓ |
| Current real DB unchanged | 72 KDs; same distribution; 0 inactive | ✓ |
| All 13 SESSION 275 lifecycle tests still pass | 13/13 pass | ✓ |
| Broader regression unchanged | 1651/1651 pass | ✓ |
| No schema drift | `makemigrations --check` clean | ✓ |

**Q-276-18 CONFIRMED.** Zero falsifications. Zero unexpected findings.

## §121. Known transitional state (not a bug)

After Slice 8, an operator-triggered ingestion revival of an orphan-archived KD produces a row with:

- `is_active=True` (revived)
- `deactivated_reason=""` (cleared by revival)
- `audience_scope='none'` (still — ingestion revival NOT extended in this slice)
- `spokespeople=[c]` (new explicit set)

This is a Slice 4 §51 row-3 malformed shape (`CHARACTER-like M2M + audience_scope=NONE + active`). It **fails closed under retrieval** (the future Delta predicate keys positively on audience_scope; NONE never matches) — so no leak. It is a KNOWN Stage-3B follow-up: extending `ingestion._persist` at `shell/apps/embeddings/ingestion.py:181-187` to also clear `audience_scope` (or set it to `CHARACTER`) on revival will resolve it. Slice 8 intentionally does NOT lock in an assertion about this transitional state (Case 11 comment records the deferred concern).

Retrieval today still uses the legacy empty-M2M-broadcast predicate; the malformed shape doesn't leak until Stage 5 switches retrieval. By that time Stage 3B should have shipped.

## §122. Files changed (Slice 8)

```
 M shell/apps/spokespeople/signals.py                                        (+18 lines — docstring + import + one .update() field)
 M shell/apps/spokespeople/tests/test_delete_orphan_archive.py               (+~40 lines — extended assertions, one import)
?? docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md                     (this Slice 8 section)
```

Zero SPA / retrieval / mutation-surface / serializer / admin / ingestion / migration / constraint changes.

## §123. Unresolved questions

Carried from Slice 4 §67, Slice 5 §81, Slice 6 §94, Slice 7 §108 (all still open):

- Stage 3B mutation-surface pass (§121 explicitly flags the ingestion revival extension as the smallest follow-up).
- Provenance direction Alpha vs Beta.
- Retrieval predicate switch (Stage 5).
- Operator triage UI for the 10 ambiguous rows (Stage 4).
- DB CHECK constraints + NOT NULL cutover (Stage 6).
- SPA audience UI (deferred; server-side inference for authoring remains preserved).
- Bundle vs split (still open from Slice 1 §8.4).

**No new Slice-8-specific unresolved questions.** The known transitional state at §121 is a documented Stage-3B follow-up, not an unresolved question.

## §124. Recommendation

**Q-276-18 is confirmed. Delta lifecycle boundary is now audience-invariant-aware.** A future orphan-archive on a live Teammate delete will atomically stamp `is_active=False + deactivated_reason='orphaned_by_teammate_delete' + audience_scope='none'` in one bulk write; all three roll back atomically on failure.

Slice 8 does not authorize any further work. Each subsequent stage requires an independent Chris + ChatGPT decision:

- **Stage 3B mutation-surface pass** — extend ingestion `_persist`, `KnowledgeDocumentSerializer.create/update`, and `views.KnowledgeDocumentViewSet.attach/detach` to set / update `audience_scope` on writes. Preserves server-side inference (Slice 4 §60). This is the natural next step and resolves the known transitional state in §121.
- **Operator triage UI** (Stage 4).
- **Retrieval predicate switch** (Stage 5).
- **CHECK constraints + NOT NULL cutover** (Stage 6).

## §125. Explicit STOP gate

**STOP.** Slice 8 authorizes no further work.

Do NOT begin:

- Stage 3B mutation-surface pass (ingestion, serializer, attach/detach)
- Provenance work (Direction Alpha / Beta)
- Retrieval predicate change
- Operator triage UI
- DB CHECK constraints
- NOT NULL cutover
- SPA audience-picker or audience-visibility UI
- Removal of SESSION 275 protections

## §126. Smallest recommended next question

**Q-276-23.** *If `ingestion._persist` at `shell/apps/embeddings/ingestion.py:164-186` is extended so that reviving any inactive KD ALSO clears `audience_scope` to NULL (letting Stage 3B's serializer/view mutation-surface pass then re-classify to CHARACTER via server-side inference from the caller-supplied `spokespeople` list), does the SESSION 276 §121 transitional inconsistency disappear without breaking either the SESSION 275 revival gate or the Slice 8 archive contract?*

Falsifiable by extending `ingestion._persist` (~2 lines to add `existing.audience_scope = None` alongside the `deactivated_reason=""` clear at line 173) + adding one assertion to Case 11 that post-revival `audience_scope IS NULL` (transitional-safe until Stage 3B/serializer sets it). Small, well-scoped, addresses the §121 known transitional state directly.

## §127. Slice 8 checklist

- [x] Step 0 — commit + push Slice 7 SHA-record (commit `8e268d5`)
- [x] Slice 8 baseline verified — `main == origin/main == 8e268d5`, working tree clean at slice start
- [x] Q-276-18 falsifiable question stated (§113)
- [x] Signal diff (§114) — one field added to bulk `.update()`; one import extension; docstring block extended
- [x] Test extensions (§115) — 13 tests updated in place with `audience_scope` assertions; no parallel test file
- [x] Test A: singleton orphan gets NONE — Cases 1, 2 pass (§116)
- [x] Test B: narrowing delete does NOT stamp NONE — Cases 3, 4 pass (§116)
- [x] Test C: shared canon untouched — Cases 5, 6 pass (§116)
- [x] Test D: bulk / QuerySet delete stamps NONE for true orphans only — Case 9 pass (§116)
- [x] Test E: atomic failure injection rolls back audience_scope — Case 13 pass with new assertion (§117)
- [x] Test F: preserved SESSION 275 semantics — all 13 lifecycle tests pass (§116)
- [x] Combined Slice 5 + Slice 7 + Slice 8 tests: 28/28 pass (§119)
- [x] Broader regression: 1651/1651 pass (§119)
- [x] `makemigrations --check embeddings` clean (§119)
- [x] Real DB unchanged: 72 KDs, `CHARACTER=59, UNIVERSE=3, NULL=10, NONE=0, inactive=0` (§118)
- [x] Known Stage-3B transitional state documented (§121)
- [x] Prediction vs actual — Q-276-18 CONFIRMED (§120)
- [x] Files changed inventory (§122)
- [x] Explicit STOP gate (§125)
- [x] Smallest next question Q-276-23 (§126)
- [x] Zero provenance / retrieval / mutation-surface / SPA / migration / constraint changes; zero provider spend
- [x] Commit + push Slice 8 — landed as `875b164`
- [x] Chris + ChatGPT review + Slice 9 scoping decision (§124) — Q-276-23 authorized (refined: skip transitional NULL; land directly at CHARACTER)

---

**End of SESSION 276 Slice 8 / Delta Stage 3A. Orphan-archive extended to stamp `audience_scope='none'` atomically. Q-276-18 CONFIRMED — 13/13 SESSION 275 lifecycle tests pass with new audience assertions; failure-injection atomicity holds for all three fields; canon and narrowing untouched. Real DB unchanged (no Teammate deleted). STOP for Chris + ChatGPT review of §124 recommendation, §125 gate, and §126 Q-276-23 next question.**

**Slice 8 landed commit SHA:** `875b164` (`fix(session-276): Slice 8 / Delta Stage 3A — stamp orphaned knowledge audience_scope=none`). Pushed to `origin/main`. Post-push `main == origin/main == 875b164`; working tree clean.

**Slice 8 SHA-record follow-up:** `fba60e1` (`docs(session-276): record Slice 8 landed SHA 875b164`) — doc-only checklist + inline SHA record + records Slice 9 authorization with refined Q-276-23.

---

# SESSION 276 — Slice 9 / Delta Stage 3B-1 — orphan revival lands directly at CHARACTER (Q-276-23 refined)

**Status.** IMPLEMENTATION SLICE — closes the Slice 8 §121 known transitional state. Extends `ingestion._persist` so an orphan-revival with the caller-supplied non-empty spokespersons (already required by the SESSION 275 gate) also stamps `audience_scope=CHARACTER` in the same save, and wraps the revival save + M2M `.set()` in a single `transaction.atomic()` savepoint for atomicity.

Chris + ChatGPT **refined** Q-276-23 before authorization: the smallest coherent Delta transition is *inactive orphan + NONE + explicit non-empty spokespeople → active CHARACTER*, **without** passing through a persisted active-NULL bridge state. This slice implements exactly that refinement.

**Slice 9 baseline.** `main == origin/main == fba60e1` (Slice 8 SHA-record). Working tree clean at slice start. Real-DB state carried forward from Slice 7 and unchanged through Slice 8:

- 72 KDs; `CHARACTER=59`, `UNIVERSE=3`, `NULL=10`, `WORKSPACE=0`, `NONE=0`
- 0 inactive rows
- 1149 chunks, 62 M2M through-rows
- Migration head: `0008_session276_stage2_backfill`

**Authorized rule** (from task): explicit spokesperson selection → `CHARACTER`. NULL remains migration-only for the 10 unresolved historical rows. NULL is NOT a normal runtime bridge state.

## §128. Slice 9 falsifiable question — Q-276-23 (refined)

> When an inactive `KnowledgeDocument` archived as `orphaned_by_teammate_delete` is revived through ingestion with the non-empty spokesperson list already required by the SESSION 275 `OrphanRevivalRejected` gate, can that SAME revival operation set `audience_scope=CHARACTER` directly — rather than NONE or NULL — so the resulting row is immediately Delta-coherent without relying on a later serializer/view pass?

**Prediction:** yes. `_persist` receives `spokespeople` as an explicit keyword argument and the SESSION 275 gate already requires it non-empty on orphan revival. Direct CHARACTER stamp is safe and eliminates the Slice 8 §121 malformed transitional state.

## §129. Source trace — `ingestion._persist` revival path

Read at `shell/apps/embeddings/ingestion.py:95-225`. Key findings:

- **`spokespeople` is a keyword argument** (`ingestion.py:106`) with a `list[Teammate] | None` type. Available at the revival branch.
- **SESSION 275 gate at `ingestion.py:146-158`** enforces `if orphan_reason AND not spokespeople → raise`. Post-gate, on the orphan-revival branch, `spokespeople` is provably non-empty.
- **Revival save + M2M set were NOT wrapped in a transaction** pre-Slice-9 (lines 177-182 of pre-Slice-9). Only the CREATE branch was atomic (`ingestion.py:189-213`). Any failure between `existing.save()` and `existing.spokespeople.set(...)` — for example, an `m2m_changed` signal veto (workspace or Universe cross-check at `apps/embeddings/signals.py:31,93`) — would leave a durable malformed row: `is_active=True + deactivated_reason='' + M2M=∅`.
- **Operator-delete revival falls through the same code** without the gate applying. `spokespeople` may legitimately be None or empty for that branch (preserves prior M2M).

The trace confirmed the assumed shape. Q-276-23 refinement is safe.

## §130. Exact implementation diff (`shell/apps/embeddings/ingestion.py`)

Three surgical changes:

**1.** Import extended:

```python
# Before:
from .models import (
    DeactivationReason, DocumentStatus, DocumentType, IngestedVia,
    KnowledgeDocument,
)

# After:
from .models import (
    AudienceScope,
    DeactivationReason, DocumentStatus, DocumentType, IngestedVia,
    KnowledgeDocument,
)
```

**2.** Orphan-reason branch captures the outcome into a local flag (`is_orphan_revival`) so the save later can conditionally add `audience_scope` to `update_fields` without duplicating the reason-check:

```python
# Before:
if existing.deactivated_reason == (
    DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE
):
    if not spokespeople:
        raise OrphanRevivalRejected(...)

# After:
is_orphan_revival = existing.deactivated_reason == (
    DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE
)
if is_orphan_revival:
    if not spokespeople:
        raise OrphanRevivalRejected(...)
```

**3.** Revival save + M2M set wrapped in `transaction.atomic()`; on the orphan branch, `existing.audience_scope = AudienceScope.CHARACTER` is set alongside the other lifecycle fields; `audience_scope` is appended to `update_fields` conditionally:

```python
# After (essential structure):
with transaction.atomic():
    existing.is_active = True
    existing.status = DocumentStatus.PENDING
    existing.error_message = ""
    existing.deactivated_reason = ""
    new_title = title.strip()
    if new_title:
        existing.title = new_title

    update_fields = [
        "is_active", "status", "error_message",
        "deactivated_reason", "title", "updated_at",
    ]
    if is_orphan_revival:
        existing.audience_scope = AudienceScope.CHARACTER
        update_fields.append("audience_scope")

    existing.save(update_fields=update_fields)
    if spokespeople:
        existing.spokespeople.set(spokespeople)
```

The log-line also gains an `orphan_revival=%s` field for future audit. Operator-delete revival never touches `audience_scope` — the field is NOT in `update_fields` unless `is_orphan_revival` is True.

Zero other code changes. No new function, no refactored dispatch, no signal touched, no admin/serializer/view/retrieval change.

## §131. Test extensions (`shell/apps/spokespeople/tests/test_delete_orphan_archive.py`)

Extended in place (same file as SESSION 275 + Slice 8). Three changes:

### §131.1 Case 11 (`test_ingestion_revival_rejects_orphan_without_spokespeople`)

Replaced the Slice 8 "known transitional state" comment block with the Slice 9 CHARACTER-stamp assertions:

```python
# After successful revival with explicit spokespeople [c]:
kd.refresh_from_db()
assert kd.is_active is True
assert kd.deactivated_reason == ""
assert list(kd.spokespeople.values_list("pk", flat=True)) == [c.pk]
# SESSION 276 Slice 9: primary Q-276-23 assertion.
assert kd.audience_scope == AudienceScope.CHARACTER
# Adversarial invariant.
assert not (
    kd.is_active is True
    and kd.audience_scope in (AudienceScope.NONE, None)
), "revived orphan must never be active + NONE/NULL"
```

The rejection path is unchanged (also asserts audience_scope stays NONE after rejected revival).

### §131.2 Case 12 (`test_ingestion_revival_of_operator_deleted_kd_still_works`)

Added `pre_delete_audience_scope` capture and post-revival assertion that the operator-delete branch does NOT touch `audience_scope`:

```python
pre_delete_audience_scope = original.audience_scope  # NULL in fixture
# ...soft-delete + revive...
assert original.audience_scope == pre_delete_audience_scope
```

This guards against a future regression that widens Slice 9's scope beyond orphan revival.

### §131.3 New Case 14 — multi-spokesperson orphan revival

```python
def test_orphan_revival_with_multiple_spokespeople_stamps_character():
    # ...orphan A, then revive with [b, c]...
    assert kd.audience_scope == AudienceScope.CHARACTER
    assert set(kd.spokespeople.values_list("pk", flat=True)) == {b.pk, c.pk}
```

Multi-character revival lands at CHARACTER (multi-character is a shape variant of CHARACTER, not a distinct audience type — Slice 4 §48).

### §131.4 New Case 15 — revival atomicity (transaction rollback)

```python
def test_orphan_revival_atomic_if_m2m_set_fails(monkeypatch):
    # ...orphan a, then connect m2m_changed pre_add receiver that raises...
    with pytest.raises(InjectedM2MFailure):
        ingest_text(..., spokespeople=[c])
    # Verify the ENTIRE revival rolled back:
    assert kd.is_active is False (unchanged)
    assert kd.deactivated_reason == 'orphaned_by_teammate_delete' (unchanged)
    assert kd.audience_scope == AudienceScope.NONE (unchanged)
    assert kd.spokespeople.count() == 0 (unchanged)
    # Adversarial invariant:
    assert not (active AND CHARACTER AND empty M2M)
```

This proves the new `transaction.atomic()` wrapper actually rolls back the CHARACTER stamp + is_active flip when M2M `.set()` fails. Without the atomic block, the save would commit and the KD would be left in the exact Slice 4 §51 row-3 malformed shape the invariant forbids.

Total: 2 assertions added to existing tests + 2 new tests (14 & 15). The lifecycle test count grows from 13 → 15.

## §132. Orphan-rejection result (Case 11)

`spokespeople=[]` → `OrphanRevivalRejected` raised. Post-rejection assertions verified:

- `is_active=False` (unchanged)
- `deactivated_reason='orphaned_by_teammate_delete'` (preserved)
- `audience_scope='none'` (preserved — the gate short-circuits before any mutation)

**PASS.** SESSION 275 rejection contract is unchanged.

## §133. Orphan successful-revival result (Case 11 continuation)

`spokespeople=[c]` (non-empty) → revival succeeds. Post-revival assertions verified:

- `is_active=True`
- `deactivated_reason=''` (cleared)
- `audience_scope='character'` (NEW Slice 9 stamp)
- `spokespeople=[c.pk]` (attached)
- Adversarial invariant: NOT `(active AND audience_scope IN {NONE, NULL})` — verified

**PASS.** Row is a coherent Delta CHARACTER shape immediately. No transitional NONE / NULL bridge state persists.

## §134. Multi-spokesperson revival result (Case 14 — new)

Orphan A → revive with `spokespeople=[b, c]`. Post-revival:

- `is_active=True`
- `deactivated_reason=''`
- `audience_scope='character'`
- `spokespeople` M2M contains exactly `{b.pk, c.pk}`

**PASS.** Multi-character is CHARACTER shape.

## §135. Operator-delete comparison (Case 12)

Operator-deleted KD created with `audience_scope=None` (fixture default; not yet touched by Stage 3B mutation-surface pass). Revived without new spokespeople. Post-revival:

- `is_active=True`
- `deactivated_reason=''`
- `spokespeople=[a.pk]` (prior M2M preserved per SESSION 275)
- `audience_scope == pre_delete_audience_scope` (None) — Slice 9 did NOT touch this branch

**PASS.** Operator-delete revival is unchanged. `is_orphan_revival` flag in `_persist` is False for this branch; `audience_scope` is NOT added to `update_fields`.

## §136. Atomicity / malformed-state analysis (Case 15 — new)

The new `transaction.atomic()` wrapper is exercised deterministically:

- Setup: an `m2m_changed` `pre_add` receiver on `KnowledgeDocumentSpokesperson.through` that raises `InjectedM2MFailure`.
- Action: `ingest_text(..., spokespeople=[c])` on the orphaned KD.
- Expected: revival save writes fire; `.set([c])` triggers `pre_add`; receiver raises; the whole atomic block rolls back.
- Verified post-rollback:
  - `is_active=False` (unchanged)
  - `deactivated_reason='orphaned_by_teammate_delete'` (preserved)
  - `audience_scope='none'` (preserved)
  - `spokespeople.count()==0` (empty)
  - Adversarial invariant: NOT `(active AND CHARACTER AND empty M2M)` — verified

**PASS.** No malformed CHARACTER-shape+empty-M2M row can be left by a partial revival. This is a *load-bearing* invariant for Delta because Stage 5+ retrieval will fail closed on such a shape but existing SESSION 275 code had no protection against creating it.

Bonus: this test also indirectly proves that Slice 9's atomic wrapper closes a pre-existing SESSION 275 hole where the save/set ordering could leave a similar malformed shape even for operator-delete revival (which the wrapper also now covers).

## §137. Real-DB post-Slice-9 verification

Code changed; real DB rows did not change. No ingestion revival was executed during Slice 9.

```
$ manage.py shell -c "..."
total=72
distribution={'universe': 3, 'character': 59, None: 10}
inactive=0
chunks=1149
m2m=62
```

Byte-identical to Slice 7 §103 / Slice 8 §118. Zero drift across three consecutive slices. Slice 9 changes future ingestion-revival behavior only.

## §138. Regression results

```
$ pytest apps/spokespeople/tests/test_delete_orphan_archive.py -v
15 passed in 5.82s                          # 13 existing + 2 new (Case 14, Case 15)

$ pytest apps/spokespeople/tests/test_delete_orphan_archive.py \
         apps/embeddings/tests/test_audience_scope_stage1.py \
         apps/embeddings/tests/test_stage2_backfill_migration.py \
         apps/embeddings/tests/test_ingestion.py -q
42 passed in 8.09s                          # lifecycle + Stage 1 + Stage 2 + ingestion

$ python manage.py makemigrations --check embeddings
No changes detected in app 'embeddings'    # no schema drift

$ pytest apps/embeddings/ apps/spokespeople/ apps/universe/ apps/compositions/ -q
1653 passed, 2 warnings in 126.86s          # broader — +2 from Slice 8's 1651 (Case 14 + Case 15)
```

Every existing test still passes. The 2 warnings are the same pre-existing DateTime naive-vs-aware warnings unrelated to Slice 9.

## §139. Prediction vs actual

| Prediction | Actual | Status |
|---|---|---|
| Source confirms `_persist` has explicit spokespersons available at revival | `ingestion.py:106` — keyword arg present; gate at `:146-158` provably non-empty | ✓ |
| Orphan revival lands directly at CHARACTER | Case 11 assertion `audience_scope == CHARACTER` passes | ✓ |
| No runtime NULL bridge needed | Case 11 asserts `NOT (active AND audience_scope IN {NONE, NULL})` | ✓ |
| SESSION 275 no-spokesperson rejection remains | Case 11 rejection branch still raises + preserves state | ✓ |
| Operator-delete revival remains unchanged | Case 12 asserts `audience_scope == pre_delete_audience_scope` (unchanged) | ✓ |
| Existing lifecycle contract remains intact | 15/15 lifecycle + 42/42 targeted + 1653/1653 broader | ✓ |
| Multi-spokesperson revival works | Case 14 verifies `{b, c}` attaches + CHARACTER | ✓ |
| Revival atomicity closes M2M-failure hole | Case 15 verifies full rollback under injected `m2m_changed` failure | ✓ |
| Real DB unchanged | 72 KDs, same distribution, 0 inactive | ✓ |

**Q-276-23 (refined) CONFIRMED.** Zero falsifications. Zero unexpected findings.

## §140. Files changed (Slice 9)

```
 M shell/apps/embeddings/ingestion.py                                        (+~35 lines net — import, is_orphan_revival flag, transaction.atomic() wrapper, conditional audience_scope stamp, log-line extension)
 M shell/apps/spokespeople/tests/test_delete_orphan_archive.py               (+~130 lines — Case 11/12 extensions + Case 14 + Case 15)
?? docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md                     (this Slice 9 section)
```

Zero changes to: SPA, retrieval, serializer create/update, view attach/detach, admin, signals, migrations, models, constraints. Slice 9 is scoped strictly to the ingestion revival branch.

## §141. Unresolved questions

Carried from prior slices (all still open):

- Fresh ingest/create audience population (rest of Stage 3B — mutation-surface pass for serializer.create + view.attach/detach).
- Serializer PATCH audience mutation.
- Provenance direction Alpha vs Beta.
- Retrieval predicate switch (Stage 5).
- Operator triage UI for the 10 ambiguous rows (Stage 4).
- DB CHECK constraints + NOT NULL cutover (Stage 6).
- SPA audience UI (deferred).
- Bundle vs split (still open from Slice 1 §8.4).

**No new Slice-9-specific unresolved questions.** The Slice 8 §121 known transitional state is CLOSED by this slice.

**One side-effect worth flagging:** the new `transaction.atomic()` wrapper around the revival branch also protects operator-delete revival from the same M2M-race hole (originally a SESSION 275 latent hole that this slice incidentally closes). That is a defensive improvement, not a broadening of scope — the wrapper serves the CHARACTER-stamp atomicity contract and covering operator-delete revival is free.

## §142. Recommendation

**Q-276-23 (refined) is confirmed. The Slice 8 §121 malformed transitional state is eliminated.** Orphan revival now atomically produces a coherent Delta CHARACTER row; operator-delete revival is unchanged (still preserves prior audience anchor).

Slice 9 does not authorize any further work. Each subsequent Stage 3B step requires an independent Chris + ChatGPT decision:

- **Fresh-create audience inference** — `_persist` CREATE branch (`ingestion.py:189-213`) currently produces new rows with `audience_scope=NULL`. Extending it to infer from `(spokespeople, universe)` at create time (CHARACTER if M2M non-empty; UNIVERSE if universe set + M2M empty; WORKSPACE if both NULL and operator explicitly chose workspace-shared) is the next natural step and directly parallels Slice 9's structure.
- **Serializer PATCH** — extend `KnowledgeDocumentSerializer.update` to handle audience_scope transitions.
- **View attach/detach** — extend view actions to transition audience_scope on M2M changes.
- **Operator triage UI** (Stage 4).
- **Retrieval predicate switch** (Stage 5).

## §143. Explicit STOP gate

**STOP.** Slice 9 authorizes no further work.

Do NOT begin:

- Fresh-create audience inference (`_persist` CREATE branch)
- Serializer audience mutation
- Attach/detach audience transitions
- Universe transitions
- Provenance work
- Retrieval predicate change
- Operator triage UI
- DB CHECK constraints
- NOT NULL cutover
- SPA changes
- Removal of SESSION 275 protections

## §144. Smallest recommended next question

**Q-276-24.** *If `_persist`'s CREATE branch (`ingestion.py:189-213`) is extended so a fresh KnowledgeDocument is stamped `audience_scope=CHARACTER` when `spokespeople` is non-empty at create time, does every existing create path continue to work AND does the resulting row match Slice 4 §51 row #1 or row #2 without any subsequent server-side reclassification?*

Falsifiable by adding `audience_scope=AudienceScope.CHARACTER` to the create call when `spokespeople` is non-empty (~1 conditional in the CREATE branch), then extending an ingestion test to assert the freshly created KD has `audience_scope=CHARACTER` when spokespeople are supplied. Scoped strictly to CHARACTER inference; UNIVERSE and WORKSPACE inference at create time is a separate Q-276-25.

## §145. Slice 9 checklist

- [x] Step 0 — commit + push Slice 8 SHA-record (commit `fba60e1`)
- [x] Slice 9 baseline verified — `main == origin/main == fba60e1`, working tree clean at slice start
- [x] Q-276-23 refined per Chris + ChatGPT (§128 preamble)
- [x] Source trace of `ingestion._persist` revival path (§129) — spokespeople keyword arg present; SESSION 275 gate provably non-empty; save/set not atomic pre-Slice-9
- [x] Ingestion diff (§130) — one import + `is_orphan_revival` flag + `transaction.atomic()` wrapper + conditional CHARACTER stamp
- [x] Test A: orphan revival without spokespersons still rejected (Case 11 rejection branch — preserved SESSION 275 contract; audience_scope stays NONE) (§132)
- [x] Test B: orphan revival with explicit spokesperson lands at CHARACTER (Case 11 successful branch) (§133)
- [x] Test C: multi-spokesperson orphan revival → CHARACTER (new Case 14) (§134)
- [x] Test D: operator-delete revival unchanged — audience_scope preserved (Case 12) (§135)
- [x] Test E: atomicity — M2M failure rolls back CHARACTER stamp + is_active flip (new Case 15) (§136)
- [x] Adversarial invariant — NOT `(active AND audience_scope IN {NONE, NULL})` asserted on revived row (Case 11) (§133)
- [x] Adversarial invariant — NOT `(active AND CHARACTER AND empty M2M)` asserted on rolled-back revival (Case 15) (§136)
- [x] 15/15 lifecycle tests pass (§138)
- [x] 42/42 combined lifecycle + Stage 1 + Stage 2 + ingestion tests pass (§138)
- [x] 1653/1653 broader regression pass (§138)
- [x] `makemigrations --check embeddings` clean (§138)
- [x] Real DB unchanged: 72 KDs, `CHARACTER=59, UNIVERSE=3, NULL=10, NONE=0, inactive=0` (§137)
- [x] Prediction vs actual — Q-276-23 refined CONFIRMED (§139)
- [x] Files changed inventory (§140)
- [x] Explicit STOP gate (§143)
- [x] Smallest next question Q-276-24 (§144)
- [x] Zero create-branch / serializer / attach-detach / provenance / retrieval / SPA / migration / constraint changes; zero provider spend
- [x] Commit + push Slice 9 — landed as `a12a141`
- [x] Chris + ChatGPT review + Slice 10 scoping decision (§142) — Q-276-24 authorized (fresh CREATE branch → CHARACTER only for explicit spokespeople; UNIVERSE/WORKSPACE inference deferred to Q-276-25)

---

**End of SESSION 276 Slice 9 / Delta Stage 3B-1. Orphan revival now atomically transitions inactive+NONE → active+CHARACTER when the required non-empty spokespeople are supplied. Slice 8 §121 malformed transitional state eliminated. Q-276-23 (refined) CONFIRMED — 15/15 lifecycle tests pass (13 existing + 2 new); operator-delete revival unchanged; revival atomicity closes M2M-failure hole (also incidentally covers a pre-existing SESSION 275 latent hole). Real DB unchanged. STOP for Chris + ChatGPT review of §142 recommendation, §143 gate, and §144 Q-276-24 next question.**

**Slice 9 landed commit SHA:** `a12a141` (`fix(session-276): Slice 9 / Delta Stage 3B-1 — orphan revival lands directly at CHARACTER`). Pushed to `origin/main`. Post-push `main == origin/main == a12a141`; working tree clean.

**Slice 9 SHA-record follow-up:** `7c10749` (`docs(session-276): record Slice 9 landed SHA a12a141`) — doc-only checklist + Slice 10 authorization record.

---

# SESSION 276 — Slice 10 / Delta Stage 3B-2 — fresh CREATE with explicit spokespeople stamps CHARACTER (Q-276-24)

**Status.** IMPLEMENTATION SLICE — extends `ingestion._persist`'s CREATE branch so a fresh `KnowledgeDocument` created with one or more explicit spokespersons is stamped `audience_scope=CHARACTER` at creation time. No transitional NULL bridge for character-specific fresh KDs. UNIVERSE / WORKSPACE inference (Q-276-25) explicitly deferred.

**Slice 10 baseline.** `main == origin/main == 7c10749` (Slice 9 SHA-record). Working tree clean at slice start. Real-DB state carried forward from Slice 7 → 8 → 9, all identical:

- 72 KDs; `CHARACTER=59`, `UNIVERSE=3`, `NULL=10`, `WORKSPACE=0`, `NONE=0`
- 0 inactive rows
- 1149 chunks, 62 M2M through-rows
- Migration head: `0008_session276_stage2_backfill`

**Authorized product rule** (from task): explicit spokesperson selection → `CHARACTER`. Fresh no-spokesperson creation stays transitional NULL for now; UNIVERSE and WORKSPACE inference are the "absence of characters" boundary that caused the original bug class and needs separate explicit-intent evidence.

## §146. Slice 10 falsifiable question — Q-276-24

> If the fresh `KnowledgeDocument` CREATE branch in `ingestion._persist` stamps `audience_scope=CHARACTER` whenever the caller supplies one or more explicit spokespeople, does every existing character-specific create path continue to behave correctly and does the newly-created KD immediately satisfy the Delta CHARACTER state without later repair?

**Prediction:** yes. `_persist` receives `spokespeople` as a keyword argument; the CREATE branch already sits inside `transaction.atomic()`; conditional CHARACTER stamp is safe.

## §147. Create-call-path inventory + atomicity trace

Source at `shell/apps/embeddings/ingestion.py`.

### §147.1 Callers into `_persist` CREATE branch

Three ingestion entry points, all keyword-only, all pass `spokespeople` unchanged through to `_persist`:

| Entry point | Location | `spokespeople` handling |
|---|---|---|
| `ingest_text` | `ingestion.py:259-303` | `spokespeople: list[Teammate] | None = None` → passed through to `_persist(..., spokespeople=spokespeople, ...)` |
| `ingest_pdf` | `ingestion.py:306-353` | same shape; same pass-through |
| `ingest_url` | `ingestion.py:354-...` (grepped; same pattern) | same shape; same pass-through |

At `_persist` boundary `spokespeople` is either `None`, an empty list, or a non-empty iterable of `Teammate` rows. The existing `if spokespeople:` truthiness check treats `None` and `[]` identically.

### §147.2 Existing transaction boundary

CREATE branch at `ingestion.py:220-244` is already wrapped in `with transaction.atomic():`. Ordering:

1. `KnowledgeDocument.objects.create(...)` — inserts the row.
2. `if spokespeople: doc.spokespeople.set(spokespeople)` — writes through-rows.

If `.set()` raises (e.g. `m2m_changed` cross-workspace or cross-Universe signal veto), the atomic block rolls back the `create()` too. This is the exact same atomicity contract Slice 9 added to the revival branch; the CREATE branch has had it since original K3 (SESSION 138).

**Conclusion.** Stamping `audience_scope=CHARACTER` on the fresh row at `create()` time is safe: if M2M `.set()` subsequently fails, the CHARACTER-marked row rolls back atomically. No malformed `active CHARACTER + empty M2M` shape can persist from this path.

## §148. Exact implementation diff (`shell/apps/embeddings/ingestion.py`)

One conditional local + one new kwarg on the create call:

```python
# Before (CREATE branch):
try:
    with transaction.atomic():
        doc = KnowledgeDocument.objects.create(
            workspace=workspace,
            universe=universe,
            title=title.strip() or "Untitled",
            ...
            created_by=created_by,
        )
        if spokespeople:
            doc.spokespeople.set(spokespeople)

# After:
try:
    with transaction.atomic():
        # SESSION 276 Slice 10 / Delta Stage 3B-2 (Q-276-24) — explicit
        # spokespeople at create time = CHARACTER scope by construction.
        # Materialise the Delta value now; no transitional NULL bridge.
        # UNIVERSE/WORKSPACE inference for the no-spokespeople case is
        # deferred to Q-276-25.
        create_audience_scope = (
            AudienceScope.CHARACTER if spokespeople else None
        )
        doc = KnowledgeDocument.objects.create(
            workspace=workspace,
            universe=universe,
            title=title.strip() or "Untitled",
            ...
            created_by=created_by,
            audience_scope=create_audience_scope,
        )
        if spokespeople:
            doc.spokespeople.set(spokespeople)
```

Docstring block added between the atomic-open and the create() call explaining the scope, Universe/Workspace deferral, and the atomicity guarantee inherited from the pre-existing wrapper.

**Zero refactor.** No new function; no import change beyond `AudienceScope` which was already imported for Slice 9. No signal touched. No admin/serializer/view/retrieval change. No migration.

## §149. Test extensions (`shell/apps/embeddings/tests/test_ingestion.py`)

Extended the existing ingestion regression file with 5 new tests. Also added `AudienceScope` + `Universe` imports.

| Test | Coverage | Status |
|---|---|---|
| A `test_fresh_create_with_single_spokesperson_stamps_character` | Single explicit sp at create → `audience_scope=CHARACTER`; adversarial invariant NOT `(active + CHARACTER + empty M2M)` | PASS |
| B `test_fresh_create_with_multiple_spokespeople_stamps_character` | `[a, b]` → CHARACTER; both attached | PASS |
| C `test_fresh_create_universe_scoped_character_still_maps_to_character` | `universe=U` + `[a in U]` → `universe=U` preserved AND `audience_scope=CHARACTER` (Slice 4 §51 row #2 shape) | PASS |
| D `test_fresh_create_without_spokespeople_leaves_audience_scope_null` | Fresh create with NO sp → `audience_scope IS NULL` (transitional). **Guards against Slice 10 silently absorbing Q-276-25 scope.** | PASS |
| E `test_fresh_create_rolls_back_atomically_if_m2m_set_fails` | Cross-workspace spokesperson triggers `m2m_changed` cross-workspace signal veto → `ValidationError` raised; asserts pre-vs-post KD count unchanged (whole `create()` rolled back) + asserts titled row does not exist | PASS |

Test D is the important scope-guard: if a future slice accidentally starts inferring UNIVERSE / WORKSPACE at create time without a Q-276-25 authorization, this test will fail deterministically.

## §150. Single-character result (Test A)

`ingest_text(workspace=ws, ..., spokespeople=[a])` produces:

- `is_active=True`
- `deactivated_reason=""`
- `audience_scope='character'`
- `spokespeople.pks == [a.pk]`
- `spokespeople.count() >= 1`
- Adversarial NOT `(active + CHARACTER + empty M2M)` — verified

**PASS.** Fresh CHARACTER row is Delta-coherent immediately, no repair needed.

## §151. Multi-character result (Test B)

`ingest_text(..., spokespeople=[a, b])` produces:

- `audience_scope='character'`
- `spokespeople.pks == {a.pk, b.pk}`

**PASS.** Multi-character is CHARACTER shape; no separate enum needed.

## §152. Universe-scoped CHARACTER result (Test C)

`ingest_text(..., spokespeople=[a in U], universe=U)` produces:

- `universe_id == U.pk`
- `audience_scope='character'`
- `spokespeople.pks == [a.pk]`

**PASS.** Universe is scope context, not audience type. Slice 4 §51 row #2 shape produced directly at create.

## §153. No-character unchanged result (Test D)

`ingest_text(...)` without `spokespeople` argument produces:

- `is_active=True`
- `audience_scope is None` (transitional; unchanged from pre-Slice-10 behavior)
- `spokespeople.count() == 0`

**PASS.** Slice 10 did NOT silently absorb Q-276-25 scope. Fresh no-spokespeople creation still lands at NULL until Q-276-25 authorizes positive UNIVERSE / WORKSPACE inference.

## §154. M2M failure atomicity result (Test E)

`ingest_text(workspace=ws_a, spokespeople=[foreign_sp_in_ws_b])` triggers the cross-workspace `m2m_changed pre_add` receiver at `apps/embeddings/signals.py:31`. Sequence:

1. `KnowledgeDocument.objects.create(...)` inserts a new row with `audience_scope=CHARACTER`.
2. `doc.spokespeople.set([foreign_sp])` fires `m2m_changed pre_add`.
3. The workspace-consistency receiver raises `ValidationError` — `foreign_sp` belongs to a different workspace.
4. The exception propagates out of `.set()`, then out of the atomic block.
5. Django rolls back the `create()` insert.

Post-attempt assertions verified:

- `pre_count == post_count` — no new row committed to `ws_a`.
- `KnowledgeDocument.objects.filter(workspace=ws_a, title=...).exists() is False` — no orphan active-CHARACTER + empty-M2M row.

**PASS.** The pre-existing `transaction.atomic()` boundary handles Slice 10's CHARACTER stamp correctly by inheritance; no additional atomicity work required.

## §155. Real-DB post-Slice-10 verification

Code changed; real DB rows did not change. No ingestion CREATE was executed against production data.

```
$ manage.py shell -c "..."
total=72
distribution={'universe': 3, 'character': 59, None: 10}
inactive=0
chunks=1149
m2m=62
```

Byte-identical to Slice 7 §103, Slice 8 §118, Slice 9 §137. **Zero drift across four consecutive slices.**

## §156. Regression results

```
$ pytest apps/embeddings/tests/test_ingestion.py -v
17 passed in 5.08s                          # 12 existing + 5 new (A/B/C/D/E)

$ pytest apps/embeddings/tests/test_ingestion.py \
         apps/spokespeople/tests/test_delete_orphan_archive.py \
         apps/embeddings/tests/test_audience_scope_stage1.py \
         apps/embeddings/tests/test_stage2_backfill_migration.py -q
47 passed in 8.85s                          # ingestion + lifecycle + Stage 1 + Stage 2

$ python manage.py makemigrations --check embeddings
No changes detected in app 'embeddings'    # no schema drift

$ pytest apps/embeddings/ apps/spokespeople/ apps/universe/ apps/compositions/ -q
1658 passed, 2 warnings in 126.66s          # broader — +5 from Slice 9's 1653
```

Every existing test still passes. The 2 warnings are the same pre-existing DateTime naive-vs-aware warnings unrelated to Slice 10.

## §157. Prediction vs actual

| Prediction | Actual | Status |
|---|---|---|
| Explicit spokesperson(s) available at CREATE boundary | `ingest_text/pdf/url` all pass `spokespeople` unchanged through to `_persist(...)` | ✓ |
| Fresh character-specific KDs land directly at CHARACTER | Test A passes | ✓ |
| Multi-character still maps to CHARACTER | Test B passes | ✓ |
| Universe-scoped character KD remains CHARACTER (Slice 4 §51 row #2) | Test C passes | ✓ |
| No-character creation remains unchanged (NULL) | Test D passes; Slice 10 scope guard | ✓ |
| No active CHARACTER + empty-M2M state can persist | Test E rollback verified via pre-vs-post row count | ✓ |
| Existing create paths remain compatible | 17/17 ingestion + 47/47 targeted + 1658/1658 broader | ✓ |
| Real DB unchanged | 72 KDs, same distribution, 0 inactive | ✓ |

**Q-276-24 CONFIRMED.** Zero falsifications. Zero unexpected findings.

## §158. Files changed (Slice 10)

```
 M shell/apps/embeddings/ingestion.py                                        (+~20 lines net — docstring, create_audience_scope local, audience_scope kwarg on create call)
 M shell/apps/embeddings/tests/test_ingestion.py                             (+~130 lines — 2 imports + 5 new tests A/B/C/D/E)
?? docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md                     (this Slice 10 section)
```

Zero changes to: SPA, retrieval, serializer create/update, view attach/detach, admin, signals, migrations, models, constraints. Slice 10 is strictly scoped to `_persist`'s CREATE branch.

## §159. Unresolved questions

Carried from prior slices (all still open):

- Fresh UNIVERSE-shared and WORKSPACE-shared inference at create time (Q-276-25 — natural next slice).
- Serializer PATCH audience mutation.
- Attach / detach audience transitions.
- Universe reassignment audience implications.
- Provenance direction Alpha vs Beta.
- Retrieval predicate switch (Stage 5).
- Operator triage UI for the 10 ambiguous rows (Stage 4).
- DB CHECK constraints + NOT NULL cutover (Stage 6).
- SPA audience UI (deferred).
- Bundle vs split (still open from Slice 1 §8.4).

**No new Slice-10-specific unresolved questions.**

## §160. Recommendation

**Q-276-24 is confirmed. Fresh CHARACTER-specific KDs now land at Delta CHARACTER shape at create time.** Combined with Slice 8 (orphan-archive stamps NONE) and Slice 9 (orphan revival stamps CHARACTER), the character-lifecycle boundary is fully Delta-aware: create/revive → CHARACTER; final-delete → NONE. Only the "absence of characters" boundary (fresh no-spokespeople creation, and any lifecycle path that reaches empty-M2M outside orphan-archive) still produces NULL / transitional state.

Slice 10 does not authorize any further work. Each subsequent step requires an independent Chris + ChatGPT decision:

- **Q-276-25 — fresh UNIVERSE-shared and WORKSPACE-shared inference at create time.** This is the natural next slice. It requires deciding what positive evidence at create time signals "operator intended shared canon" vs "operator forgot to select characters" — that's exactly the semantic distinction Delta was introduced to make explicit.
- **Serializer PATCH audience_scope handling** — currently the field is not on the serializer read/write surface; extending it needs explicit-intent-payload contract design.
- **Attach / detach audience transitions** — currently CHARACTER-with-M2M stays CHARACTER regardless of the attach/detach path; but detaching the last spokesperson leaves a `CHARACTER + empty M2M` shape (the exact malformed row #3 from Slice 4 §51). This is one of the two "detach-final" holes SESSION 275 didn't close — needs its own falsifiable slice.
- **Retrieval predicate switch** (Stage 5).

## §161. Explicit STOP gate

**STOP.** Slice 10 authorizes no further work.

Do NOT begin:

- Fresh UNIVERSE-shared or WORKSPACE-shared inference (Q-276-25)
- Serializer PATCH audience mutation
- Attach / detach audience transitions
- Universe reassignment audience implications
- Provenance work
- Retrieval predicate change
- Operator triage UI
- DB CHECK constraints
- NOT NULL cutover
- SPA changes
- Removal of SESSION 275 protections

## §162. Smallest recommended next question

**Q-276-25.** *At fresh CREATE time, when the caller supplies NO spokespeople but DOES supply an explicit `universe` value, is that combination positive operator evidence for `audience_scope=UNIVERSE` — and when the caller supplies neither, does that combination require an explicit operator gesture (rather than a silent stamp of WORKSPACE) before the fresh KD can be Delta-coherent?*

Falsifiable by:
1. Inspecting every caller of `ingest_text/pdf/url` (SPA + tests + management commands + serializer create) to enumerate which combinations of `(spokespeople, universe)` are actually generated today.
2. Testing whether a UNIVERSE stamp for the `(no sp, universe=U)` case would preserve current effective audience for the 3 evidence-backed frozen UNIVERSE canon rows (Slice 4 §55.1) and for the SESSION 272 experiment substrates.
3. Testing whether the `(no sp, no universe)` case ever legitimately means "explicit workspace-shared canon" today — or whether it's currently always a transitional / to-be-classified case (matching the 10 ambiguous historical rows).

This is a slightly larger investigation than Q-276-24 because "absence of characters" is the semantic boundary the whole SESSION 276 arc was opened to make explicit — it deserves a first pass that leans on Slice 3's mutation inventory + Slice 4's truth table rather than jumping straight to implementation.

## §163. Slice 10 checklist

- [x] Step 0 — commit + push Slice 9 SHA-record (commit `7c10749`)
- [x] Slice 10 baseline verified — `main == origin/main == 7c10749`, working tree clean at slice start
- [x] Q-276-24 falsifiable question stated (§146)
- [x] Create-call-path inventory (§147.1) — `ingest_text/pdf/url` all pass `spokespeople` through unchanged
- [x] Existing transaction boundary confirmed (§147.2) — pre-existing `transaction.atomic()` already covers create + M2M .set()
- [x] Ingestion diff (§148) — `create_audience_scope` local + one new kwarg on create() + docstring
- [x] Test A: single-character fresh create → CHARACTER (§150)
- [x] Test B: multi-character fresh create → CHARACTER (§151)
- [x] Test C: Universe-scoped CHARACTER preserves both (§152)
- [x] Test D: no-character create unchanged (NULL) — Slice 10 scope guard (§153)
- [x] Test E: M2M failure rolls back CHARACTER stamp + KD create (§154)
- [x] Adversarial invariant — NOT `(active + CHARACTER + empty M2M)` (Test A + Test E) (§150, §154)
- [x] 17/17 ingestion tests pass (§156)
- [x] 47/47 combined ingestion + lifecycle + Stage 1 + Stage 2 tests pass (§156)
- [x] 1658/1658 broader regression pass (§156)
- [x] `makemigrations --check embeddings` clean (§156)
- [x] Real DB unchanged: 72 KDs, `CHARACTER=59, UNIVERSE=3, NULL=10, NONE=0, inactive=0` (§155)
- [x] Prediction vs actual — Q-276-24 CONFIRMED (§157)
- [x] Files changed inventory (§158)
- [x] Explicit STOP gate (§161)
- [x] Smallest next question Q-276-25 (§162)
- [x] Zero UNIVERSE/WORKSPACE inference / serializer PATCH / attach/detach / provenance / retrieval / SPA / migration / constraint changes; zero provider spend
- [x] Commit + push Slice 10 — landed as `b75036d`
- [x] Chris + ChatGPT review + Slice 11 scoping decision (§160) — Q-276-25 authorized as audit-first (UNIVERSE + WORKSPACE fresh-create inference investigation; implementation ONLY if evidence justifies)

---

**End of SESSION 276 Slice 10 / Delta Stage 3B-2. Fresh CREATE with explicit spokespeople now lands directly at Delta CHARACTER shape. Q-276-24 CONFIRMED — 17/17 ingestion tests pass (12 existing + 5 new); multi-character and Universe-scoped character variants covered; M2M failure atomicity inherited from pre-existing create-branch transaction; no-character create explicitly unchanged (Q-276-25 scope guard). Real DB unchanged. STOP for Chris + ChatGPT review of §160 recommendation, §161 gate, and §162 Q-276-25 next question.**

**Slice 10 landed commit SHA:** `b75036d` (`feat(session-276): Slice 10 / Delta Stage 3B-2 — fresh CREATE stamps CHARACTER on explicit spokespeople`). Pushed to `origin/main`. Post-push `main == origin/main == b75036d`; working tree clean.

**Slice 10 SHA-record follow-up:** `4d4635e` (`docs(session-276): record Slice 10 landed SHA b75036d`) — doc-only checklist + Slice 11 audit-first authorization record.

---

# SESSION 276 — Slice 11 / Delta Stage 3B-3 — fresh CREATE UNIVERSE inference (Q-276-25, audit + narrow implementation)

**Status.** AUDIT-FIRST SLICE with narrow authorized implementation for the UNIVERSE case only. WORKSPACE case audit-only per §176. Chris + ChatGPT authorized investigation-first; implementation was performed only for the branch the audit independently justified.

**Slice 11 baseline.** `main == origin/main == 4d4635e` (Slice 10 SHA-record). Working tree clean at slice start. Real-DB state carried forward, unchanged through 5 slices now:

- 72 KDs; `CHARACTER=59`, `UNIVERSE=3`, `NULL=10`, `WORKSPACE=0`, `NONE=0`
- 0 inactive, 1149 chunks, 62 M2M through-rows
- Migration head: `0008_session276_stage2_backfill`

**Load-bearing product rule** (from task, restated): *"Empty / missing character relations must not silently mean 'share more broadly' unless the operator explicitly chose that broader audience."* `no spokespeople` alone is NOT positive evidence for UNIVERSE or WORKSPACE.

## §164. Slice 11 falsifiable question — Q-276-25

> At fresh CREATE time, when no spokespeople are supplied:
>
> 1. does an explicitly supplied Universe constitute sufficient positive operator intent to persist `audience_scope=UNIVERSE`; and
> 2. when neither spokespeople nor Universe are supplied, is there any positive operator evidence that the user intended WORKSPACE-shared canon, or would stamping WORKSPACE merely recreate the old "absence means broadcast" semantics?

## §165. Predictions before evidence

**A.** `spokespeople=∅ + universe=U` likely sufficient positive evidence for UNIVERSE if the caller/API/UI reached that shape because the operator explicitly selected Universe U as the knowledge scope.

**B.** `spokespeople=∅ + universe=NULL` likely NOT sufficient for WORKSPACE unless a positive workspace-sharing gesture exists.

**C.** Some create paths may rely on omission-as-default; Delta must not silently convert those to WORKSPACE.

**D.** The correct answer may be asymmetric (UNIVERSE yes, WORKSPACE no or deferred).

Compared to evidence in §178.

## §166. Complete create-caller inventory

Traced every non-test production caller of `_persist` / `ingest_text` / `ingest_pdf` / `ingest_url`.

| # | Caller | File:line | Operator gesture | `spokespeople` | `universe` | Interpretation |
|---|---|---|---|---|---|---|
| 1 | Workspace paste form (`WorkspacePasteForm`) | `web/src/routes/workspace/knowledge.tsx:288-305` | Operator picks `UniverseScopePicker` (Universe UUID OR "None (legacy)") — submit disabled while unpicked | omitted | explicitly picked (UUID → uuid, "None (legacy)" → null) | Universe: explicit UNIVERSE-shared intent. NULL: explicit workspace-shared per copy |
| 2 | Workspace PDF upload | `knowledge.tsx:395-402` | Same UniverseScopePicker | omitted | explicit | Same as 1 |
| 3 | Workspace URL ingest | `knowledge.tsx:492-498` | Same UniverseScopePicker | omitted | explicit | Same as 1 |
| 4 | Workspace Serper search-then-ingest | `knowledge.tsx:587-596` | Same UniverseScopePicker | omitted | explicit | Same as 1 |
| 5 | Spokesperson ask-panel citation-add | `web/src/components/spokesperson-ask-panel.tsx:613-621` | Operator asks Q, clicks "teach the character" | `[spokesperson.id]` | not sent (defaults to None) | CHARACTER (Slice 10 stamps) |
| 6 | DRF `KnowledgeDocumentSerializer.create` | `shell/apps/embeddings/serializers.py:279-364` | pass-through of SPA payload | `validated_data.get("spokespeople") or []` | `validated_data.get("universe")` | Not an independent gesture — passes SPA payload through |
| 7 | `smoke_ingest` mgmt command | `shell/apps/embeddings/management/commands/smoke_ingest.py:157-178` | Not an operator; diagnostic; savepoint-rolled-back | omitted | omitted | Internal smoke; produces `(no sp, no universe)` shape; rolled back |
| 8 | `scripts/session272_slice_b_setup.py` | `scripts/session272_slice_b_setup.py:154-162` | Not an operator; experimental substrate | omitted | Universe (explicit) | Comment (`:152-153`): *"No spokespeople M2M attach — broadcast (M2M-null) so the cloned Rivet Teammate sees it via the broadcast branch of retrieval."* Positive UNIVERSE-shared intent |
| 9 | `scripts/session273_slice_alpha_ingest_kd.py` | `scripts/session273_slice_alpha_ingest_kd.py:211-220` | Not an operator; Ruby canon substrate | omitted | Universe (explicit) | Comment (`:218`): *"empty M2M = broadcast; Universe scope handles isolation."* Positive UNIVERSE-shared intent. Created the frozen Ruby `8f825c98` |

## §167. UniverseScopePicker semantics

`web/src/routes/workspace/knowledge.tsx:48-117` — load-bearing SPA component driving callers 1-4.

Key behavioral evidence:

- **`export type UniverseScopeValue = "" | typeof UNIVERSE_LEGACY_SENTINEL | string`** — the empty string is the unpicked sentinel (`:48`).
- **`universeScopeToPayload("")` throws** (`:106-108`): *"Universe scope must be explicitly picked"*. Prevents any payload from being sent without a scope decision.
- **`universeScopePicked(value)`** returns `false` for `""` (`:115-117`); every submit handler checks this and refuses to send.
- The `<option value="" disabled>{...}</option>` at `:82` prevents the operator from selecting the empty sentinel.
- The two positive-choice options are:
  - `<option value={UNIVERSE_LEGACY_SENTINEL}>None (legacy — visible to workspace-wide legacy teammates only)</option>` (`:85-86`)
  - `<option key={u.id} value={u.id}>{u.name}</option>` for each Universe (`:88-90`)
- Explanatory helper text (`:94-98`): *"Pick a world to scope this doc to that world's characters, or pick 'None (legacy)' to make it visible to legacy (pre-Universe) characters."*

**Conclusion.** Every workspace-knowledge create surface FORCES an explicit scope decision. There is no path where the operator can send a KD create WITHOUT actively choosing either a Universe or "None (legacy) — visible to workspace-wide legacy teammates only".

## §168. Part B — UNIVERSE case analysis

Case: `spokespeople=∅ + universe=U`.

Callers that produce this shape today:

- **SPA callers 1-4:** operator explicitly picked Universe U in UniverseScopePicker. The submit button was disabled until picked; `universeScopeToPayload` would have thrown otherwise. This is a positive, gated operator gesture.
- **Non-SPA callers 8, 9:** scripts creating the SESSION 272 rivet-debug and Ruby Fox & Flour canon KDs. Both code comments explicitly document the intent as broadcast-in-Universe-scope.

Absent from the inventory: any caller that treats Universe as merely context inherited from surrounding page state without an operator decision. All observed cases are positive-intent.

**Distinguish** *"knowledge is being created while I happen to be inside Universe U"* from *"I choose for this knowledge to be shared with everyone in Universe U"* — the SPA fuses these into a single operator gesture (picking Universe U in UniverseScopePicker), which is intentional per the picker's design and per the explanatory copy.

Would stamping `audience_scope=UNIVERSE` preserve effective audience? YES — under the current retrieval predicate at `shell/apps/embeddings/retrieval.py:194-221`, `(is_active=True, universe=U, spokespeople=∅)` matches every teammate in Universe U (SD state in Slice 4 §31). `audience_scope=UNIVERSE` under the eventual Delta retrieval will produce the same audience.

Would it ever broaden vs what the operator selected? NO — the operator explicitly picked Universe U; the UNIVERSE stamp names that exact choice.

## §169. Part C — WORKSPACE case analysis

Case: `spokespeople=∅ + universe=NULL`.

Callers that produce this shape today:

- **SPA callers 1-4** when the operator explicitly picks "None (legacy)" in UniverseScopePicker. Copy: *"None (legacy — visible to workspace-wide legacy teammates only)"*. This IS positive workspace-sharing operator intent per the copy.
- **`smoke_ingest` mgmt command (caller 7):** produces this shape without any operator gesture; savepoint-rolled-back.

**The load-bearing complication:** at the `_persist` boundary, `universe=None` reaches the function regardless of which upstream caller sent the payload. The DRF serializer at `shell/apps/embeddings/serializers.py:293` uses `validated_data.get("universe")` — this returns `None` both for "SPA sent `universe: null` explicitly" and "SPA didn't send the `universe` key at all". The backend cannot distinguish.

For SPA-generated payloads, `(no sp + no universe)` IS a positive workspace-shared gesture. For non-SPA-generated payloads (mgmt commands, curl, custom scripts), it is not necessarily positive intent — it may be omission.

**Options:**

1. Infer WORKSPACE at `_persist` boundary. **Rejected** — recreates "absence means broadcast" for non-SPA callers. Task instruction: *"Do not preserve accidental broadcast semantics merely for backward compatibility."*
2. Extend SPA payload with an explicit `audience_scope=workspace` field on the "None (legacy)" gesture; infer WORKSPACE only when the field is present.
3. Do nothing yet; `(no sp + no universe)` remains transitional `audience_scope=NULL`.

**Slice 11 chooses Option 3** because Option 2 requires an SPA + DRF payload contract addition that is scope-adjacent to Q-276-25 but not authorized. Option 3 is invariant-safe (no broadening) and forces a future explicit product decision.

## §170. Part D — legacy control comparison

The 10 legacy NULL rows in the current DB have `(is_active=True, universe=None, spokespeople=∅, deactivated_reason='')` — the exact shape a WORKSPACE inference rule would sweep. Slice 1 §4.4 evidence proved these rows represent MULTIPLE meanings simultaneously:

- 1 PROVEN historical orphan (TANK)
- 1 STRONG historical orphan (Tulsi)
- 1 PROVEN never-attached / misconfigured (Riggs)
- 6 mechanically indeterminate (Hearth & Hollow set) + 1 admins-workspace tech note

If a fresh-create WORKSPACE inference rule existed today, and any of these rows had been created via a legacy path that produced the same shape, they would all be indistinguishable from intentional workspace canon. That is exactly the ambiguity Slice 4 §55.2 identified as "cannot be blanket-migrated per the task-added migration invariant."

This adversarial control reinforces the Option 3 decision: without a positive marker distinguishing intent from omission, `(no sp + no universe)` cannot be stamped WORKSPACE at the ingestion boundary.

## §171. Part E — server inference vs explicit intent

Slice 4 §57.1 Stage 3 originally described server-side inference for all three cases. Slice 11 refines:

| Branch | Slice 4 §57.1 Stage 3 assumption | Slice 11 verdict |
|---|---|---|
| explicit spokespeople → CHARACTER | Server infers | CONFIRMED (Slice 10 landed) |
| no sp + universe → UNIVERSE | Server infers | CONFIRMED (Slice 11 implements) |
| neither → WORKSPACE | Server infers | REJECTED — needs explicit payload contract |

CHARACTER inference is proven safe because explicit M2M is positive evidence at every layer (serializer + `_persist` + through-model signals). UNIVERSE inference is proven safe because explicit `universe` FK is positive evidence at every layer. WORKSPACE inference is NOT safe at the `_persist` layer because `universe=None` collapses "explicit None (legacy)" and "omitted" into the same signal.

**Inference stops being trustworthy at the boundary where positive evidence can no longer be distinguished from omission.** For WORKSPACE, that boundary is DRF `validated_data`. To make WORKSPACE inference safe, we must lift the operator gesture into a payload field the backend can positively observe.

## §172. Part F — UI philosophy

Slice 11 does NOT expose `audience_scope` as an operator-facing enum dropdown. If Slice 11 authorized an SPA change (it did not), a simple product gesture such as:

- "Only selected character(s)" → `audience_scope=character` payload
- "Everyone in this Universe" → `audience_scope=universe` payload
- "Everyone in this workspace" → `audience_scope=workspace` payload

...would preserve Chris's product philosophy while giving the backend the positive marker it needs. The UniverseScopePicker "None (legacy)" copy already gestures in this direction; a future slice can promote it to a positive payload field without renaming any operator concept.

## §173. Part G — falsifiable read-only experiments

No provider spend. All evidence gathered via source inspection + regression tests + the pre-existing DB inventory verified through 5 consecutive slices.

- Grep for every caller of `ingest_text` / `ingest_pdf` / `ingest_url` / `_persist` in non-test code (§166 enumerates all 9).
- Inspection of `UniverseScopePicker` semantics (§167).
- Inspection of script-side comments in caller 8 and caller 9 (§166).
- Verification that the 3 frozen UNIVERSE canon rows in Slice 7's Stage 2 backfill correspond exactly to callers 8 and 9's output + Ruby's SESSION 275 §Slice 1 evidence.

No tests were needed to falsify the audit — the evidence is at the source-inspection layer.

## §174. Decision table

| # | Input / gesture | Positive evidence | Current actual audience | Proposed Delta state | Safe to infer? |
|---|---|---|---|---|---|
| 1 | explicit character A supplied | `spokespeople=[A]` non-empty at `_persist` boundary | those legacy teammates via M2M-hit | `CHARACTER` | YES (Slice 10 landed) |
| 2 | explicit A + B supplied | M2M count ≥ 2 at `_persist` | those specific teammates | `CHARACTER` (variant shape) | YES (Slice 10 landed) |
| 3 | explicit character A inside Universe U (`universe=U, spokespeople=[A in U]`) | Both fields positively supplied; Universe M2M-consistency signal passes | those Universe-U teammates | `CHARACTER` (Universe is scope context) | YES (Slice 10 landed) |
| 4 | no characters + explicit Universe U (`spokespeople=∅, universe=U`) | Positive `universe` FK; SPA required explicit UniverseScopePicker pick; scripts document intent explicitly | every teammate in Universe U | `UNIVERSE` | **YES — Slice 11 implements** |
| 5 | no characters + Universe inherited implicitly (hypothetical) | none observed in current caller inventory | n/a | `UNIVERSE` | Not applicable (no such caller today) |
| 6 | no characters + no Universe + explicit workspace-share gesture (SPA "None (legacy)") | Positive SPA-side gesture (picked "None (legacy)" copy explicitly names workspace-wide audience) — but NOT visible to backend as distinct from omission | every legacy teammate in workspace | `WORKSPACE` — but requires explicit payload marker | **NO** — needs future API contract |
| 7 | no characters + no Universe + no explicit share gesture (`smoke_ingest` etc.) | omission | every legacy teammate in workspace (via current predicate) | ambiguous | **NO** — do not stamp WORKSPACE |
| 8 | mgmt / seed caller with no operator gesture (e.g. `smoke_ingest`) | omission | matches whatever shape the caller happens to produce | ambiguous | **NO** — do not stamp WORKSPACE |

## §175. Answers A and B (separately)

### §175.A UNIVERSE inference — **YES, safe to implement now.**

Rows 4 of §174. Every current caller producing `(no sp + universe=U)` does so with positive operator intent (SPA UniverseScopePicker explicit pick; scripts document intent in code comments). The resulting `audience_scope=UNIVERSE` stamp preserves current effective retrieval audience exactly. No caller uses Universe as merely context inheritance without operator intent.

### §175.B WORKSPACE inference — **NO, requires future explicit API contract.**

Rows 6-8 of §174. The SPA's "None (legacy)" gesture IS positive workspace-shared intent, but at the `_persist` boundary the backend cannot distinguish that gesture from omission (`smoke_ingest` produces the same shape without operator intent). Adding a WORKSPACE inference rule at `_persist` would silently re-create the "absence means broadcast" semantics Delta was introduced to eliminate. Correct next step: lift the operator gesture into an explicit payload field the backend can positively observe. That is a future slice with its own falsifiable question.

## §176. Implementation performed

Because §175.A is YES, Slice 11 implements the UNIVERSE-inference branch. §175.B is NO; WORKSPACE is NOT implemented.

### §176.1 Ingestion diff (`shell/apps/embeddings/ingestion.py`)

CREATE branch's audience-scope resolution extended from a 2-way conditional (CHARACTER-or-None) to a 3-way conditional (CHARACTER-or-UNIVERSE-or-None):

```python
# Before (post-Slice-10):
create_audience_scope = (
    AudienceScope.CHARACTER if spokespeople else None
)

# After (Slice 11):
if spokespeople:
    create_audience_scope = AudienceScope.CHARACTER
elif universe is not None:
    create_audience_scope = AudienceScope.UNIVERSE
else:
    # Transitional NULL for the (no sp + no universe) case pending
    # the explicit-intent-payload decision.
    create_audience_scope = None
```

Docstring block extended with Slice 11 rationale, source-citation to `UniverseScopePicker`, and explicit note that WORKSPACE inference is NOT implemented pending API contract decision.

Zero other changes. No new import, no signal touched, no serializer / view / admin / retrieval / migration / model change.

### §176.2 Test extensions (`shell/apps/embeddings/tests/test_ingestion.py`)

Three test changes:

- Test D (existing Slice 10 `test_fresh_create_without_spokespeople_leaves_audience_scope_null`) renamed to `test_fresh_create_without_spokespeople_or_universe_leaves_audience_scope_null` and its docstring extended to document the Slice 11 WORKSPACE-inference rejection reasoning. Still asserts `(no sp, no universe) → NULL`.
- **New Test F `test_fresh_create_no_spokespeople_with_explicit_universe_stamps_universe`** — the primary Slice 11 assertion. `(no sp, universe=U) → audience_scope=UNIVERSE`; adversarial invariant NOT `(UNIVERSE + universe=NULL)`.
- **New Test G `test_fresh_create_universe_inference_asymmetric_with_workspace`** — verifies the deliberate asymmetry: `(no sp, universe=U) → UNIVERSE` AND `(no sp, no universe) → NULL`. Guards against a future slice accidentally coupling the two inference branches.

## §177. Regression results

```
$ pytest apps/embeddings/tests/test_ingestion.py -v
19 passed in 5.35s                          # 17 existing (12 pre-Slice-10 + 5 Slice 10 A/B/C/D/E) + 2 new (F, G)

$ pytest apps/embeddings/tests/test_ingestion.py \
         apps/spokespeople/tests/test_delete_orphan_archive.py \
         apps/embeddings/tests/test_audience_scope_stage1.py \
         apps/embeddings/tests/test_stage2_backfill_migration.py -q
49 passed in 8.82s                          # ingestion + lifecycle + Stage 1 + Stage 2

$ python manage.py makemigrations --check embeddings
No changes detected in app 'embeddings'    # no schema drift

$ pytest apps/embeddings/ apps/spokespeople/ apps/universe/ apps/compositions/ -q
1660 passed, 2 warnings in 127.72s          # broader — +2 from Slice 10's 1658 (Test F + Test G)
```

Every existing test still passes. 2 pre-existing DateTime warnings unrelated.

## §178. Prediction vs actual

| Prediction (§165) | Actual | Status |
|---|---|---|
| A: `(no sp + universe=U)` sufficient positive evidence when caller reached shape by explicit operator selection | Confirmed via UniverseScopePicker semantics (§167) + script comment inspection (§166 callers 8, 9). Slice 11 implements UNIVERSE stamping | ✓ |
| B: `(no sp + universe=NULL)` NOT sufficient for WORKSPACE unless positive gesture exists | Confirmed asymmetric: SPA's "None (legacy)" IS positive gesture, but backend cannot distinguish from omission; Slice 11 defers WORKSPACE inference | ✓ |
| C: some current create paths rely on omission-as-default | Confirmed: `smoke_ingest` mgmt command (caller 7) produces `(no sp, no universe)` with no operator gesture | ✓ |
| D: correct answer may be asymmetric | Confirmed: A = YES (UNIVERSE now), B = NO (WORKSPACE deferred) | ✓ |

All 4 predictions supported. Zero falsifications.

## §179. Real-DB post-Slice-11 verification

Code changed; real DB rows did not change. No ingestion CREATE was executed against production data during Slice 11.

```
$ manage.py shell -c "..."
total=72
distribution={'universe': 3, 'character': 59, None: 10}
inactive=0
chunks=1149
m2m=62
```

Byte-identical to Slice 7 §103, Slice 8 §118, Slice 9 §137, Slice 10 §155. **Zero drift across five consecutive slices.**

## §180. Files changed (Slice 11)

```
 M shell/apps/embeddings/ingestion.py                                        (+~30 lines net — docstring extension + 3-way conditional replacing 2-way)
 M shell/apps/embeddings/tests/test_ingestion.py                             (+~90 lines — Test D docstring update + Test F + Test G)
?? docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md                     (this Slice 11 section)
```

Zero SPA changes, zero serializer / view / admin / signal / retrieval / migration / model / constraint changes. Slice 11 is scoped strictly to `_persist`'s CREATE branch.

## §181. Unresolved questions

Carried from prior slices (all still open):

- **New / promoted: WORKSPACE fresh-create explicit-intent payload contract** — Slice 11 confirmed this needs its own slice (Q-276-26 candidate).
- Serializer PATCH audience mutation.
- Attach / detach audience transitions (especially the detach-final SPA hole; Slice 3 §37.J).
- Universe reassignment audience implications.
- Provenance direction Alpha vs Beta.
- Retrieval predicate switch (Stage 5).
- Operator triage UI for the 10 ambiguous rows (Stage 4).
- DB CHECK constraints + NOT NULL cutover (Stage 6).
- SPA audience UI (deferred).
- Bundle vs split (still open from Slice 1 §8.4).

## §182. Recommendation

**Q-276-25 is answered asymmetrically. UNIVERSE inference is confirmed and implemented; WORKSPACE inference is confirmed to require a future explicit payload-contract slice.**

Slice 11 does not authorize any further work. Each subsequent step requires an independent Chris + ChatGPT decision:

- **Q-276-26 (candidate) — WORKSPACE explicit intent payload.** Extend SPA "None (legacy)" gesture + DRF create serializer + `_persist` to carry a positive `audience_scope=workspace` intent field. Design decision: lift the operator gesture into a payload field vs. tie it to a specific SPA feature flag. Requires SPA + backend + tests.
- **Serializer PATCH audience_scope handling** — currently not on the serializer read/write surface.
- **Attach / detach audience transitions** — the detach-final SPA hole from Slice 3 §37.J is now the largest remaining CHARACTER-shape audience broadening path.
- **Retrieval predicate switch** (Stage 5).

## §183. Explicit STOP gate

**STOP.** Slice 11 authorizes no further work.

Do NOT begin:

- Q-276-26 WORKSPACE explicit-intent payload contract
- Serializer PATCH audience mutation
- Attach / detach audience transitions
- Universe reassignment audience implications
- Provenance work
- Retrieval predicate change
- Operator triage UI
- DB CHECK constraints
- NOT NULL cutover
- SPA changes
- Removal of SESSION 275 protections

## §184. Smallest recommended next question

**Q-276-26.** *If the SPA `UniverseScopePicker`'s "None (legacy)" gesture is extended to send an explicit `audience_scope="workspace"` field on the create payload, and the DRF `KnowledgeDocumentSerializer.create` is extended to forward that field to `_persist`, and `_persist`'s CREATE branch stamps `audience_scope=WORKSPACE` only when that positive field is present (not when the field is merely absent), does every current SPA-generated create path continue to work AND does the "None (legacy)" gesture produce a Delta-coherent WORKSPACE row without silently affecting any non-SPA caller?*

Falsifiable by:
1. Extending the SPA payload type (`web/src/lib/api/knowledge.ts`) with an optional `audience_scope` field.
2. Extending the four UniverseScopePicker call sites to send `audience_scope: "workspace"` when the operator picks "None (legacy)" (and NOT send it when they pick a Universe).
3. Extending the DRF serializer + `_persist` to accept and forward the field, but ONLY stamp WORKSPACE when the field is positively present.
4. Adding regression tests that (a) SPA-generated "None (legacy)" payload → WORKSPACE, (b) non-SPA `_persist` call without the field stays NULL, (c) SPA-generated Universe-picker payload → UNIVERSE (unchanged).

This is a slightly larger slice than Q-276-25's UNIVERSE branch because it touches SPA + serializer + `_persist`, but the invariant it locks in (positive-marker WORKSPACE) is the last piece needed before all four Delta audience states can be stamped at create time.

## §185. Slice 11 checklist

- [x] Step 0 — commit + push Slice 10 SHA-record (commit `4d4635e`)
- [x] Slice 11 baseline verified — `main == origin/main == 4d4635e`, working tree clean at slice start
- [x] Q-276-25 falsifiable question stated (§164)
- [x] Predictions before evidence (§165)
- [x] Complete create-caller inventory (§166) — 9 callers enumerated (4 SPA + 1 SPA-citation + 1 DRF + 1 mgmt + 2 scripts)
- [x] `UniverseScopePicker` semantics documented (§167) — forces explicit operator pick
- [x] Part B UNIVERSE analysis (§168) — every current caller producing `(no sp + universe=U)` is positive-intent
- [x] Part C WORKSPACE analysis (§169) — SPA gesture exists but backend cannot distinguish from omission
- [x] Part D legacy-control comparison (§170) — 10 legacy NULL rows adversarial control
- [x] Part E server-inference vs explicit-intent (§171) — CHARACTER + UNIVERSE safe at boundary; WORKSPACE needs payload marker
- [x] Part F UI philosophy preserved (§172) — no operator-facing `audience_scope` dropdown
- [x] Part G falsifiable experiments (§173) — source-inspection sufficient
- [x] Decision table (§174) — 8 rows
- [x] Answer A UNIVERSE separately: YES (§175.A)
- [x] Answer B WORKSPACE separately: NO (§175.B)
- [x] UNIVERSE narrow implementation (§176) — 3-way conditional in ingestion.py CREATE branch + docstring
- [x] Test D updated to reflect `(no sp + no universe) → NULL` justification
- [x] Test F: fresh (no sp + universe=U) → UNIVERSE
- [x] Test G: asymmetry guard (`(no sp, U) → UNIVERSE` AND `(no sp, None) → NULL`)
- [x] Adversarial invariant — NOT `(UNIVERSE + universe=NULL)` asserted (Test F)
- [x] 19/19 ingestion tests pass (§177)
- [x] 49/49 combined targeted (§177)
- [x] 1660/1660 broader regression pass (§177)
- [x] `makemigrations --check embeddings` clean (§177)
- [x] Real DB unchanged: 72 KDs, `CHARACTER=59, UNIVERSE=3, NULL=10, NONE=0, inactive=0` (§179)
- [x] Prediction vs actual — Q-276-25 answered asymmetrically (§178)
- [x] Files changed inventory (§180)
- [x] Explicit STOP gate (§183)
- [x] Smallest next question Q-276-26 (§184)
- [x] Zero WORKSPACE inference / serializer PATCH / attach-detach / provenance / retrieval / SPA / migration / constraint changes; zero provider spend
- [x] Commit + push Slice 11 — landed as `bd2852c`
- [x] Chris + ChatGPT review + Slice 12 scoping decision (§182) — Q-276-26 authorized (explicit WORKSPACE fresh-create marker contract; fresh-CREATE only, revival paths must ignore marker)

---

**End of SESSION 276 Slice 11 / Delta Stage 3B-3. Q-276-25 answered asymmetrically: UNIVERSE inference implemented (safe positive evidence at `_persist` boundary via explicit `universe` FK); WORKSPACE inference deferred (SPA "None (legacy)" gesture exists but backend cannot distinguish from omission — needs explicit payload-marker contract). 19/19 ingestion tests pass (12 existing + 5 Slice 10 + 2 new Slice 11); real DB unchanged for 5th consecutive slice. STOP for Chris + ChatGPT review of §182 recommendation, §183 gate, and §184 Q-276-26 next question.**

**Slice 11 landed commit SHA:** `bd2852c` (`feat(session-276): Slice 11 / Delta Stage 3B-3 — fresh CREATE UNIVERSE inference (Q-276-25 asymmetric)`). Pushed to `origin/main`. Post-push `main == origin/main == bd2852c`; working tree clean.
