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

**Riggs (#9):** Riggs teammate CURRENTLY EXISTS (`5731a73d`, `status=ready`, `created_at=2026-08-17T15:52:32`); its CharacterIdentity row (`2026-08-17T15:53:11`) has an intact `teammate` link. The Riggs KD was created at `2026-08-17T15:53:36` — 64 seconds AFTER the Riggs teammate row and 25 seconds AFTER its CharacterIdentity row. The KD content is a stub ("Just knows a lot about everything") and was ingested unattached (`spokespeople=∅`). ~~This is **not** an orphan pattern — it is a live teammate + a stub knowledge doc that was ingested without an M2M attach.~~ **CORRECTED — see §279:** the "not an orphan pattern" conclusion is retracted. The raw observations above (name collision + 64s timing proximity + intact CharacterIdentity FK) remain factually correct, but do not establish that the KD was authored for the currently live Riggs Teammate — operator (Chris) clarified 2026-08-21 that this was an auto-select control test. Intended audience is INDETERMINATE.

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
| 9 | `90ad200c` Riggs | ~~**PROVEN — NOT an orphan; unattached / never-attached KD**~~ **CORRECTED → INDETERMINATE (see §279)** | Raw observations preserved: Riggs Teammate `5731a73d` currently exists, `status=ready`; Riggs CharacterIdentity has intact `teammate` link; KD created 64s AFTER Teammate creation; content is a 33-char stub ("Just knows a lot about everything"); no Composition/Asset produced | ~~None. This is a misconfigured / never-attached ingest, not an orphan~~ **CORRECTED (see §279):** name collision + timing proximity is not a fingerprint under the §4.4 hierarchy. Operator (Chris) clarified 2026-08-21 that the KD is not necessarily attributable to the live Riggs Teammate — auto-select control test. Reclassified INDETERMINATE |

**Distribution (CORRECTED — see §279):** 1 PROVEN orphan (TANK), 1 STRONG-INFERENCE orphan (Tulsi), 7 WEAK-INFERENCE / INDETERMINATE (6× Hearth & Hollow + Riggs). ~~Prior wording: "1 PROVEN not-orphan (Riggs), 6 WEAK-INFERENCE" — retracted.~~

### §4.5 Answer to Track A question

> Can any of the nine be safely classified from surviving evidence as intentionally workspace-shared, formerly character-specific/orphaned, simply unattached/misconfigured, or genuinely indeterminate?

- **PROVEN orphan (TANK #8):** yes — CharacterIdentity SET_NULL fingerprint is dispositive. Safe to remediate as "orphaned by past Teammate delete."
- **STRONG-INFERENCE orphan (Tulsi #7):** yes — combined Composition + Asset SET_NULL fingerprint + design-doc + operator testimony is sufficient to remediate as orphan **for Chris's own workspace under his signoff**. Would not survive a hypothetical adversarial audit against a stranger's workspace, but this is Chris's own data.
- ~~**PROVEN not-orphan (Riggs #9):** yes — the Riggs Teammate exists. This is a misconfigured/unattached KD; the correct remediation is either attach it to Riggs or delete it. It is **not** an orphan case.~~ **CORRECTED — see §279.** Retracted. Riggs is now classified INDETERMINATE. Identity continuity between the live Riggs Teammate and KD `90ad200c` was inferred only from name + timing — not a fingerprint tier. Operator (Chris) supplied 2026-08-21 clarification that the KD is not necessarily attributable to the live Riggs Teammate (auto-select control test). Remediation now requires operator signoff on the same tier as Hearth & Hollow, not a mechanical "attach to Riggs" default.
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
| Track A: subset classifiable, subset indeterminate | Confirmed. ~~1 PROVEN orphan (TANK), 1 STRONG orphan (Tulsi), 1 PROVEN not-orphan (Riggs), 6 WEAK / indeterminate (Hearth & Hollow)~~ **CORRECTED (see §279):** 1 PROVEN orphan (TANK), 1 STRONG orphan (Tulsi), 7 WEAK / INDETERMINATE (6× Hearth & Hollow + Riggs). |
| Track B: SESSION 275 signal + revival gate seal orphan-archive; SPA gap remains | Confirmed. Ingestion revival is safe-gated. SPA has zero visibility |
| Track B: DRF API sealed by `is_active=True` queryset filter | Confirmed — but the seal is *coincidental* (queryset filter, not serializer read-only or endpoint invariant). Django admin remains an unguarded revival path |

## §8. Unresolved questions

1. **Hearth & Hollow (KDs #1–#6): true classification.** Cannot be resolved from surviving evidence alone. Depends on Chris's product decision: treat as orphan (delete) or as intentional business canon (attach to a workspace-level "Hearth & Hollow" concept, if such a concept ever gets first-class representation).
2. **Should the SESSION 275 `pre_delete` snapshot persist a durable record?** Currently in-memory only. If yes, that's a small addition (a `KnowledgeDocumentArchiveLog` model with `kd_id`, `teammate_id`, `teammate_name`, `archived_at`) that would enable operator-visible "archived because *teammate X* was deleted" copy in any future recovery UI. Not implemented; not authorized.
3. **Should Django admin enforce the safe-audience contract?** Admin bypasses the ingestion gate. A `KnowledgeDocumentAdmin.save_model` override could refuse `is_active=False → True` transitions on `ORPHANED_BY_TEAMMATE_DELETE` rows without an accompanying non-empty M2M or a Universe change. Not implemented; not authorized.
4. **Bundle vs split slice.** Does Chris want legacy remediation (Question A) and recovery UX (Question B) as (a) one bundled slice, (b) two separate slices where one blocks the other, or (c) two independent slices? This is the scoping question in SESSION 276 handoff §E step 4. **Not answered by evidence — a Chris product decision.**
5. ~~**Riggs KD.** It's not an orphan and it's not an intentional canon — it's a stub. Should the recovery workflow have a "misconfigured / never-attached" concept, or is that class of row always handled by *attach* / *delete* alone?~~ **CORRECTED — see §279.** The "not an orphan / stub attributable to the live Riggs Teammate" framing is retracted; Riggs is INDETERMINATE. The residual product question — *should recovery UX carry a distinct "misconfigured / never-attached" bucket at all?* — is superseded: without a fingerprint distinguishing that bucket from operator-signoff INDETERMINATE, the workflow reduces to "operator classifies each row from the ambiguous set."

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
  - Riggs `90ad200c` — ~~PROVEN never-attached / misconfigured (Riggs teammate exists; KD created 64s after; content stub)~~ **CORRECTED (see §279): INDETERMINATE.** Raw observations preserved; the "attach to the live Riggs Teammate" default is retracted (name + timing is not a fingerprint). Correct Delta target under operator decision: (a) `CHARACTER` if Chris chooses to attach to some specific teammate, (b) `NONE + is_active=False` if Chris decides it was noise, (c) hard-delete.
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
| 9 | Riggs | ~~PROVEN not-orphan / misconfigured~~ **CORRECTED → INDETERMINATE (§279)** | (a) `CHARACTER` (attach to a specific teammate — no longer defaulted to the live Riggs Teammate), (b) `NONE + is_active=False`, (c) hard-delete. Operator decision | Same |
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
- ~~1 PROVEN never-attached / misconfigured (Riggs)~~ **CORRECTED (see §279):** 1 INDETERMINATE (Riggs) — the earlier "PROVEN never-attached / misconfigured attributable to the live Riggs Teammate" verdict is retracted; name + timing is not a fingerprint tier
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

**Slice 11 SHA-record follow-up:** `bfd1282` (`docs(session-276): record Slice 11 landed SHA bd2852c`) — doc-only checklist + Slice 12 authorization record.

---

# SESSION 276 — Slice 12 / Delta Stage 3B-4 — explicit WORKSPACE fresh-create marker (Q-276-26)

**Status.** IMPLEMENTATION SLICE — introduces the smallest explicit `audience_scope="workspace"` payload marker for fresh CREATE only. The SPA's existing "None (legacy)" gesture in `UniverseScopePicker` now carries positive workspace-shared intent through DRF into `_persist`; non-SPA callers that omit the marker continue to produce `audience_scope=NULL`.

**Slice 12 baseline.** `main == origin/main == bfd1282` (Slice 11 SHA-record). Working tree clean at slice start. Real-DB state carried forward, unchanged through 6 slices now:

- 72 KDs; `CHARACTER=59`, `UNIVERSE=3`, `NULL=10`, `WORKSPACE=0`, `NONE=0`
- 0 inactive, 1149 chunks, 62 M2M through-rows
- Migration head: `0008_session276_stage2_backfill`

**Load-bearing product rule** (from task): *"Never restore this inference: `no spokespeople + no Universe => WORKSPACE`. WORKSPACE must require POSITIVE intent."*

## §186. Slice 12 falsifiable question — Q-276-26

> If the existing SPA `UniverseScopePicker` workspace-sharing gesture ("None (legacy)") carries an explicit WORKSPACE audience-intent marker through the create API, and `_persist` stamps WORKSPACE ONLY when that marker is positively present, can fresh workspace-shared creation become Delta-coherent without changing the behavior of callers that merely omit both character and Universe scope?

**Prediction:** yes. The SPA already has positive operator intent; the information is lost only in transport. Threading a positive marker through DRF → `_persist` preserves fail-safe semantics for non-SPA callers.

## §187. Transport-path trace (pre-Slice-12)

Traced end-to-end:

1. Operator picks `UniverseScopePicker` option in one of 4 SPA surfaces (`web/src/routes/workspace/knowledge.tsx:311-318,417-424,514-521,610-617`).
2. `universeScopeToPayload(scope)` returns UUID or `null` (`knowledge.tsx:106-112`).
3. `useCreateKnowledge().mutateAsync({workspace, universe, title, text_content})` builds payload.
4. `createKnowledge` POSTs to `/api/knowledge/` (`web/src/lib/api/knowledge.ts:239-247`).
5. DRF `KnowledgeDocumentSerializer.create` reads `validated_data.get("universe")` (`shell/apps/embeddings/serializers.py:342`).
6. `ingest_text/pdf/url` forwards `universe` and `spokespeople` to `_persist`.
7. `_persist` applies precedence: spokespeople → CHARACTER; universe → UNIVERSE; else NULL.

**Gap.** After step 2, `universe: null` reaches `_persist` and is indistinguishable from a caller that simply omitted the arg.

## §188. Payload contract

New optional field on the create payload (write-only, create-only):

```
audience_scope: "workspace" | undefined
```

Serializer ChoiceField accepts only `"workspace"`. CHARACTER and UNIVERSE audience states continue to derive from their already-proven positive inputs (`spokesperson_ids` and `universe` respectively); the marker is scoped strictly to the third case.

## §189. Precedence + contradiction rules

Precedence:

1. `spokespeople` non-empty → `CHARACTER`
2. `universe` non-NULL → `UNIVERSE`
3. `workspace_shared_intent=True` (from `audience_scope="workspace"` payload) → `WORKSPACE`
4. else → `NULL` (transitional)

Contradictions rejected by the DRF serializer's `validate()` **before** the payload reaches `_persist`:

- `spokesperson_ids` non-empty + `audience_scope="workspace"` → HTTP 400
- `universe` non-NULL + `audience_scope="workspace"` → HTTP 400

Defensive fallback: if a non-DRF caller somehow bypasses the serializer, `_persist` logs a warning and honors the higher-precedence signal (CHARACTER or UNIVERSE) — never silently broadens to WORKSPACE.

## §190. Exact SPA diff (`web/src/routes/workspace/knowledge.tsx` + `web/src/lib/api/knowledge.ts`)

**Three changes:**

**1.** `web/src/lib/api/knowledge.ts:223-247` — extend `CreateKnowledgePayload` interface with the optional `audience_scope?: "workspace"` field. Docstring cites Slice 12 §186-§204.

**2.** `web/src/routes/workspace/knowledge.tsx` — new helper alongside the existing `universeScopeToPayload`:

```ts
export function universeScopeToAudienceMarker(
  value: UniverseScopeValue,
): "workspace" | undefined {
  if (value === UNIVERSE_LEGACY_SENTINEL) return "workspace";
  return undefined;
}
```

Returns `"workspace"` **only** when the operator picks the legacy sentinel. Returns `undefined` for both "unpicked" and "Universe UUID" cases so the field is elided from the payload for both.

**3.** All 4 create call sites now spread `audience_scope: universeScopeToAudienceMarker(scope)` alongside `universe: universeScopeToPayload(scope)`. Call sites: `knowledge.tsx:316, 423, 520, 617`.

Zero other SPA files touched. `spokesperson-ask-panel.tsx` (citation-add flow) is unchanged — that flow always sends `spokesperson_ids` so it produces CHARACTER; no marker needed.

## §191. Exact serializer diff (`shell/apps/embeddings/serializers.py`)

**Four changes:**

**1.** Write-only ChoiceField added at `serializers.py:94-118`:

```python
audience_scope = serializers.ChoiceField(
    write_only=True,
    required=False,
    allow_null=True,
    choices=[("workspace", "Workspace-shared")],
)
```

**2.** Field added to `Meta.fields` list. Not added to `read_only_fields` (write-only per the field decl).

**3.** `validate()` extended with contradiction guard: rejects `audience_scope="workspace"` combined with `spokesperson_ids` or `universe`. Applied only on CREATE (`self.instance is None`); PATCH ignores the marker entirely.

**4.** `create()` reads `validated_data.get("audience_scope") == "workspace"` into local `workspace_shared_intent`, forwards it to all three `ingest_text/pdf/url` call sites.

`update()` extended with `validated_data.pop("audience_scope", None)` to silently drop the field on PATCH (audience-transition PATCH semantics are deferred).

## §192. Exact ingestion diff (`shell/apps/embeddings/ingestion.py`)

**Three changes:**

**1.** `_persist` signature gains `workspace_shared_intent: bool = False`.

**2.** CREATE branch precedence conditional extended from 3-way to 4-way:

```python
if spokespeople:
    create_audience_scope = AudienceScope.CHARACTER
    if workspace_shared_intent:
        logger.warning("...")  # contradiction defensive log
elif universe is not None:
    create_audience_scope = AudienceScope.UNIVERSE
    if workspace_shared_intent:
        logger.warning("...")
elif workspace_shared_intent:
    create_audience_scope = AudienceScope.WORKSPACE
else:
    create_audience_scope = None
```

**3.** `ingest_text` / `ingest_pdf` / `ingest_url` signatures each gain `workspace_shared_intent: bool = False` and forward it to `_persist`.

Revival branch (`_persist:126-218`) is **unchanged**. The marker cannot reach the revival branch's mutations because it's only referenced in the CREATE branch after the dedup miss.

## §193. Fresh WORKSPACE result (Slice 12 Test A + API test)

Backend test `test_slice12_A_explicit_workspace_marker_stamps_workspace`:

```python
ingest_text(workspace=ws, ..., workspace_shared_intent=True)
# → audience_scope=WORKSPACE, universe=NULL, spokespeople=∅
```

DRF-boundary test `test_slice12_api_workspace_marker_stamps_workspace`:

```
POST /api/knowledge/ { workspace, title, text_content,
                       audience_scope: "workspace" }
→ 201 Created; doc.audience_scope == WORKSPACE
```

Both pass. Adversarial invariant NOT `(WORKSPACE AND universe non-NULL)` verified.

## §194. Omission NULL result (Slice 12 Test B + API test)

Backend + DRF: fresh create with no spokespeople + no universe + no marker → `audience_scope IS NULL`. **This is the load-bearing regression.** Prevents Slice 12 from accidentally reinstating "absence means broadcast." Non-SPA callers (mgmt commands, scripts, curl) unchanged.

## §195. UNIVERSE regression (Slice 12 Test C)

`ingest_text(..., universe=U)` still stamps `audience_scope=UNIVERSE` (Slice 11 behavior preserved). Universe precedence wins over marker absence.

## §196. CHARACTER regression (Slice 12 Test D)

`ingest_text(..., spokespeople=[a])` still stamps `audience_scope=CHARACTER` (Slice 10 behavior preserved). CHARACTER precedence wins over marker absence.

## §197. Contradiction rejection (Slice 12 Tests E1, E2 + API tests)

At `_persist` boundary (defensive):

- `spokespeople + marker` → CHARACTER wins; logger warning fires.
- `universe + marker` → UNIVERSE wins; logger warning fires.

At DRF serializer boundary (primary):

- `spokesperson_ids + audience_scope="workspace"` → **HTTP 400** with `{"audience_scope": "Cannot combine..."}`.
- `universe + audience_scope="workspace"` → **HTTP 400** with `{"audience_scope": "Cannot combine..."}`.

Additional DRF test: `test_slice12_api_rejects_invalid_audience_scope_value` — verifies that only `"workspace"` is a valid value. Payloads with `"character"`, `"universe"`, `"none"`, or arbitrary strings are rejected with 400. Ensures the marker cannot be used to stamp CHARACTER / UNIVERSE / NONE via the API.

## §198. Revival regression (Slice 12 Test G)

The load-bearing safety test. Sequence:

1. Create KD attached to teammate A.
2. Delete A → orphan-archive stamps `NONE` (Slice 8).
3. Re-ingest same content with `workspace_shared_intent=True` but no `spokespeople`.
4. **`OrphanRevivalRejected` raised** — SESSION 275/276 recovery invariant honored.
5. Post-state: KD remains `is_active=False, audience_scope=NONE, deactivated_reason=ORPHANED_BY_TEAMMATE_DELETE`.

The marker CANNOT bypass the orphan-revival CHARACTER-recovery gate. This preserves the entire SESSION 275/276 arc's core invariant against silent broadening via any recovery path.

## §199. All-ingestion-types coverage (Slice 12 Tests F1, F2)

Test F1: `ingest_pdf` with `workspace_shared_intent=True` (using mocked PDF extraction) produces `audience_scope=WORKSPACE`. Test F2: same for `ingest_url` with mocked URL fetch. All three ingestion transports (`text`, `pdf`, `url`) correctly thread the marker to `_persist`.

## §200. SPA tests (new file `knowledge.audience-marker.test.tsx`)

Vitest unit tests for the pure `universeScopeToAudienceMarker` helper and its two siblings:

- Legacy sentinel → `"workspace"`
- Universe UUID → `undefined`
- Unpicked → `undefined`
- Asymmetry invariant: helper only ever emits `"workspace"` OR `undefined` — never emits any other audience state (guards against Slice 12 silently absorbing CHARACTER/UNIVERSE inference into the marker path).
- `universeScopeToPayload` behavior unchanged (throws on unpicked; returns null on sentinel; returns UUID otherwise).
- `universeScopePicked` behavior unchanged.

**10/10 SPA tests pass.**

## §201. Regression results

```
$ pytest apps/embeddings/tests/test_ingestion.py \
         apps/embeddings/tests/test_api.py \
         apps/spokespeople/tests/test_delete_orphan_archive.py -v
71 passed in 11.26s        # ingestion (28: 19 pre-Slice-12 + 9 new A-G) + DRF (27: 21 pre + 6 new)
                            # + SESSION 275 lifecycle (15)

$ pytest apps/embeddings/ apps/spokespeople/ apps/universe/ apps/compositions/ -q
1675 passed, 2 warnings in 133.03s
                            # broader — +15 from Slice 11's 1660 (9 ingestion + 6 API)

$ pnpm exec vitest run
651 passed across 48 files
                            # SPA suite — +10 from prior baseline

$ python manage.py makemigrations --check embeddings
No changes detected in app 'embeddings'
```

Every existing test still passes. Zero regressions. 2 pre-existing DateTime warnings unrelated.

## §202. Real-DB post-Slice-12 verification

Code changed; real DB rows did not change. No create/PATCH executed against production data during Slice 12.

```
$ manage.py shell -c "..."
total=72
distribution={'universe': 3, 'character': 59, None: 10}
inactive=0
chunks=1149
m2m=62
```

Byte-identical to Slice 7 §103 → 11 §179. **Zero drift across 6 consecutive slices.**

## §203. Prediction vs actual

| Prediction (§186 prediction) | Actual | Status |
|---|---|---|
| SPA workspace-share gesture provides positive intent | Confirmed via 4 create sites now passing `audience_scope: universeScopeToAudienceMarker(scope)` | ✓ |
| Positive marker survives transport | Confirmed via API test → serializer → ingestion → `_persist` chain | ✓ |
| Fresh explicit workspace share → WORKSPACE | Slice 12 Test A + API test pass | ✓ |
| Omission remains NULL | Slice 12 Test B + API test pass | ✓ |
| Universe remains UNIVERSE | Slice 12 Test C passes | ✓ |
| Characters remain CHARACTER | Slice 12 Test D passes | ✓ |
| Contradictory broad-audience payloads fail safely | Serializer 400s in E1/E2 API tests; `_persist` defensive precedence wins in E1/E2 backend tests | ✓ |
| Orphan revival cannot use marker to bypass CHARACTER recovery contract | Slice 12 Test G confirmed `OrphanRevivalRejected` raised | ✓ |
| Real DB unchanged | 72 KDs, same distribution, 0 inactive; 6 consecutive slices with zero drift | ✓ |

**Q-276-26 CONFIRMED.** Zero falsifications. Zero unexpected findings.

## §204. Files changed (Slice 12)

```
 M shell/apps/embeddings/ingestion.py                                        (+~45 lines net — 4-way precedence + workspace_shared_intent kwarg on _persist + ingest_text/pdf/url)
 M shell/apps/embeddings/serializers.py                                      (+~55 lines net — write-only audience_scope field + Meta.fields + validate() contradiction + create() forwarding + update() drop)
 M shell/apps/embeddings/tests/test_ingestion.py                             (+~230 lines — Slice 12 tests A/B/C/D/E1/E2/F1/F2/G)
 M shell/apps/embeddings/tests/test_api.py                                   (+~155 lines — 6 DRF-boundary tests)
 M web/src/lib/api/knowledge.ts                                              (+~15 lines — optional audience_scope field on CreateKnowledgePayload)
 M web/src/routes/workspace/knowledge.tsx                                    (+~25 lines net — universeScopeToAudienceMarker helper + 4 call-site additions)
?? web/src/routes/workspace/knowledge.audience-marker.test.tsx               (new — 84 lines, 10 tests)
?? docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md                     (this Slice 12 section)
```

Zero migration / model / signal / admin / retrieval changes. Slice 12 is scoped strictly to the fresh-CREATE payload contract.

## §205. Unresolved questions

Carried from prior slices (all still open):

- Serializer PATCH audience_scope transitions (currently silently dropped on PATCH — deferred).
- Attach / detach audience transitions (Slice 3 §37.J detach-final hole still exists).
- Universe reassignment audience implications.
- Provenance direction Alpha vs Beta.
- Retrieval predicate switch (Stage 5).
- Operator triage UI for the 10 ambiguous rows (Stage 4).
- DB CHECK constraints + NOT NULL cutover (Stage 6).
- Bundle vs split (still open from Slice 1 §8.4).

**No new Slice-12-specific unresolved questions.** Every case in the fresh-CREATE decision table (Slice 11 §174) now has a Delta-coherent behavior.

## §206. Recommendation

**Q-276-26 is confirmed. Delta fresh-CREATE contract is now complete for all four audience states.** Combined with Slice 10 (CHARACTER via spokespeople) + Slice 11 (UNIVERSE via universe FK), fresh CREATE now produces:

| SPA operator gesture | Payload | `_persist` stamps |
|---|---|---|
| Pick spokesperson(s), any scope | `spokesperson_ids=[...]` | `CHARACTER` |
| Pick UniverseScopePicker=Universe U, no character | `universe: <uuid>` | `UNIVERSE` |
| Pick UniverseScopePicker="None (legacy)", no character | `universe: null, audience_scope: "workspace"` | `WORKSPACE` |
| Non-SPA caller with no marker | (none) | `NULL` (transitional) |

Slice 12 does not authorize any further work. Each subsequent step requires an independent Chris + ChatGPT decision:

- **Attach / detach audience transitions** — the largest remaining Delta-invariant hole is the detach-final SPA gesture (Slice 3 §37.J) which currently produces the exact malformed CHARACTER + empty-M2M shape Delta was designed to prevent.
- **Serializer PATCH audience_scope transitions** — needed for a general operator audience-change gesture.
- **Retrieval predicate switch** (Stage 5) — once every mutation surface produces Delta-coherent rows, retrieval can begin keying on `audience_scope` positively.
- **Legacy triage UI** for the 10 ambiguous rows (Stage 4).

## §207. Explicit STOP gate

**STOP.** Slice 12 authorizes no further work.

Do NOT begin:

- Serializer PATCH audience transitions
- Attach / detach fixes
- Universe reassignment transitions
- Provenance work
- Retrieval predicate change
- Operator triage UI
- DB CHECK constraints
- NOT NULL cutover
- UI redesign
- Recovery UI

## §208. Smallest recommended next question

**Q-276-27.** *If the SPA `/detach/` endpoint (`web/src/components/knowledge-panel.tsx:199-210`) is extended so that detaching the last remaining spokesperson on an active CHARACTER-shape KD returns a specific 400 with a body describing the three legitimate operator options ("delete this document," "make it Universe-shared," "make it workspace-shared"), and the SPA UI surfaces those choices as a confirmation dialog, does the Slice 3 §37.J detach-final hole close without changing any existing detach behavior for count>1 KDs?*

Falsifiable by:
1. Extending `KnowledgeDocumentViewSet.detach` (`shell/apps/embeddings/views.py:146-159`) with a precondition check: if the detach would leave M2M empty on a CHARACTER-audience KD, return HTTP 400 with a JSON body naming the three options.
2. Adding a SPA confirm dialog on the last-detach case that surfaces the three choices as buttons.
3. Regression tests proving (a) count>1 detach unchanged, (b) count=1 detach on CHARACTER returns 400, (c) each recovery option (delete / promote-Universe / promote-Workspace) is Delta-coherent.

Slice 12 completes fresh-CREATE Delta-coherence; Q-276-27 begins mutation-surface Delta-coherence for existing rows. Together they'd close the last two live SPA-facing audience-broadening paths Slice 3 §37 identified.

## §209. Slice 12 checklist

- [x] Step 0 — commit + push Slice 11 SHA-record (commit `bfd1282`)
- [x] Slice 12 baseline verified — `main == origin/main == bfd1282`, working tree clean at slice start
- [x] Q-276-26 falsifiable question stated (§186)
- [x] Transport-path trace (§187) — pre-Slice-12 gap identified between SPA and `_persist`
- [x] Payload contract defined (§188) — `audience_scope: "workspace" | undefined`, write-only + create-only, single valid value
- [x] Precedence + contradiction rules defined (§189)
- [x] SPA diff (§190) — `CreateKnowledgePayload` extended + `universeScopeToAudienceMarker` helper + 4 call sites
- [x] Serializer diff (§191) — write-only ChoiceField + Meta.fields + `validate()` contradiction guard + `create()` forwarding + `update()` drop
- [x] Ingestion diff (§192) — 4-way precedence + `workspace_shared_intent` kwarg on `_persist` + `ingest_text/pdf/url`
- [x] Test A: explicit WORKSPACE marker stamps WORKSPACE (§193)
- [x] Test B: omission remains NULL — load-bearing regression (§194)
- [x] Test C: UNIVERSE regression unchanged (§195)
- [x] Test D: CHARACTER regression unchanged (§196)
- [x] Test E1/E2: contradiction rejection (`_persist` defensive + DRF 400) (§197)
- [x] Test F1/F2: PDF and URL ingestion transports thread marker (§199)
- [x] Test G: orphan revival gate cannot be bypassed by marker (§198)
- [x] API tests (§193, §194, §197) — 6 new DRF-boundary tests including PATCH-ignores-marker
- [x] SPA tests (§200) — 10 new Vitest tests for `universeScopeToAudienceMarker` + regression coverage of siblings
- [x] Adversarial invariants — NOT `(WORKSPACE + universe non-NULL)`, NOT `(active + CHARACTER + empty M2M)`
- [x] 71/71 combined ingestion + DRF + SESSION 275 lifecycle tests pass (§201)
- [x] 1675/1675 broader backend regression pass (§201)
- [x] 651/651 SPA suite pass (§201)
- [x] `makemigrations --check embeddings` clean (§201)
- [x] Real DB unchanged: 72 KDs, `CHARACTER=59, UNIVERSE=3, NULL=10, NONE=0, inactive=0` (§202)
- [x] Prediction vs actual — Q-276-26 CONFIRMED (§203)
- [x] Files changed inventory (§204)
- [x] Explicit STOP gate (§207)
- [x] Smallest next question Q-276-27 (§208)
- [x] Zero PATCH audience / attach-detach / provenance / retrieval / migration / model / constraint changes; zero provider spend
- [x] Commit + push Slice 12 — landed as `9665461`
- [x] Chris + ChatGPT review + Slice 13 scoping decision (§206) — refined Q-276-27 authorized: close ONLY the unsafe final-detach transition; do NOT wire promotion buttons or audience PATCH in this slice

---

**End of SESSION 276 Slice 12 / Delta Stage 3B-4. Explicit WORKSPACE fresh-create marker landed end-to-end (SPA → DRF → `_persist`). Q-276-26 CONFIRMED — all four Delta audience states (CHARACTER, UNIVERSE, WORKSPACE, NONE) now produced by fresh CREATE with positive operator intent; non-SPA omission remains transitional NULL; contradictions rejected at DRF boundary with defensive precedence at `_persist`; orphan revival gate unbypassable by marker; real DB unchanged for 6th consecutive slice. STOP for Chris + ChatGPT review of §206 recommendation, §207 gate, and §208 Q-276-27 next question.**

**Slice 12 landed commit SHA:** `9665461` (`feat(session-276): Slice 12 / Delta Stage 3B-4 — explicit WORKSPACE fresh-create marker`). Pushed to `origin/main`. Post-push `main == origin/main == 9665461`; working tree clean.

**Slice 12 SHA-record follow-up:** `e2fbdcb` (`docs(session-276): record Slice 12 landed SHA 9665461`) — doc-only checklist + Slice 13 authorization record.

---

# SESSION 276 — Slice 13 / Delta Stage 3C-1 — final-character detach fails closed (refined Q-276-27)

**Status.** IMPLEMENTATION SLICE — closes the Slice 3 §37.J live SPA-facing audience-broadening hole. Backend `_toggle_spokesperson` rejects final-character detach on active `audience_scope=CHARACTER` KDs with a structured 4xx BEFORE any M2M mutation; SPA surfaces the structured message inline. Explicitly does NOT wire audience promotion buttons or PATCH audience transitions — those remain deferred to independently-authorized slices.

**Slice 13 baseline.** `main == origin/main == e2fbdcb` (Slice 12 SHA-record). Working tree clean at slice start. Real-DB state carried forward through 7 slices now:

- 72 KDs; `CHARACTER=59`, `UNIVERSE=3`, `NULL=10`, `WORKSPACE=0`, `NONE=0`
- 0 inactive, 1149 chunks, 62 M2M through-rows
- Migration head: `0008_session276_stage2_backfill`

**Load-bearing rule carried forward:**

> A CHARACTER-scoped KD must never become an active empty-M2M KD as an incidental result of detach. Fail closed.

## §210. Slice 13 falsifiable question — refined Q-276-27

> If the existing detach mutation refuses to remove the final spokesperson from an active `audience_scope=CHARACTER` KnowledgeDocument, while preserving ordinary narrowing detach behavior when another spokesperson remains, does the live detach-final audience-broadening hole close without changing any legitimate existing audience transition?

## §211. Predictions before evidence

1. Existing multi-character detach can remain unchanged.
2. Final-character detach can be detected BEFORE M2M mutation.
3. Returning HTTP 400 before mutation closes the broadening path without introducing an audience transition in this slice.
4. SPA can surface a clear operator-facing message without a new audience picker.
5. No DB transaction is required for a rejected operation.
6. Shared UNIVERSE / WORKSPACE rows are unaffected (guard is CHARACTER-only).
7. Real DB unchanged.

Compared to evidence in §223.

## §212. Source trace — detach path (pre-Slice-13)

- **Endpoint:** `KnowledgeDocumentViewSet.detach` at `shell/apps/embeddings/views.py:146-159` → calls `_toggle_spokesperson(request, attach=False)` at `views.py:161-191`.
- **Available at view boundary:** `doc = self.get_object()` returns the KD (queryset already filters `is_active=True` — inactive KDs 404 pre-guard). `doc.audience_scope` accessible; `doc.spokespeople.count()` and `doc.spokespeople.filter(pk=sp.pk).exists()` available for pre-mutation check.
- **Order of operations pre-Slice-13:** `get_object` → sp lookup → workspace-match check → `.remove()` — no guard between.
- **SPA callers:** `web/src/components/knowledge-panel.tsx:158-160` (spokesperson-detail page). The SPA `useToggleSpokespersonAttachment` hook posts to `/api/knowledge/<id>/detach/`. No other production SPA caller today.
- **`ApiError` shape:** `web/src/lib/api/client.ts:20-30` — carries `status` + parsed `body`; suitable for structured-error discrimination.

## §213. NULL-audience state audit (real DB + tests)

Real DB read-only queries:

```
KnowledgeDocument.objects.filter(
    audience_scope__isnull=True,
).annotate(spc=Count("spokespeople")).filter(spc__gt=0).count()
→ 0

KnowledgeDocument.objects.filter(
    audience_scope="character",
).annotate(spc=Count("spokespeople")).filter(spc=0).count()
→ 0
```

**Zero rows in real DB have `NULL + non-empty M2M`.** Slice 7 Stage 2 backfill classified every M2M-carrying row as CHARACTER, and Slice 10's CREATE stamp guarantees all new M2M-carrying rows land at CHARACTER too. Zero rows have CHARACTER + empty M2M either. The guard scoped to `audience_scope == CHARACTER` covers 100% of production character-scoped KDs unambiguously.

The `NULL + M2M non-empty` shape only appears in test fixtures that call `KnowledgeDocument.objects.create()` directly (bypassing Slice 10's CREATE stamp path). Slice 13 preserves existing detach behavior on those rows (documented deliberate carve-out — see §219).

## §214. Backend guard design

**Location:** `_toggle_spokesperson` at `shell/apps/embeddings/views.py:161-236` (post-Slice-13 line numbers), inserted between the workspace-match check and the `.add()` / `.remove()` block.

**Guard condition** (four-part conjunction; all must be true):

1. `not attach` — this is a detach request.
2. `doc.audience_scope == AudienceScope.CHARACTER` — positive character-audience evidence.
3. `doc.spokespeople.filter(pk=sp.pk).exists()` — the SP is currently attached (idempotent detach of non-attached SP remains a no-op).
4. `doc.spokespeople.count() == 1` — this SP is the only remaining one; removing them would leave empty M2M.

**Action on match:** raise `ValidationError` with a structured body BEFORE `.remove()` runs. No mutation.

**Scope carve-outs:**

- `audience_scope=UNIVERSE` / `WORKSPACE` rows: never guarded (empty M2M is legitimate for these audiences).
- `audience_scope=NULL` legacy rows: never guarded (documented in §213 as fixture-only in real DB).
- `is_active=False` rows: already unreachable via `get_object` (queryset filters `is_active=True`).

## §215. Structured error contract

Response body shape:

```json
{
  "code": "final_character_detach_requires_audience_decision",
  "detail": "'<Name>' is the last character using this knowledge. Removing them would leave the knowledge without an audience. Choose a new audience or archive/delete the knowledge instead."
}
```

- HTTP status: **400** (DRF `ValidationError` default).
- `code`: machine-readable, stable across releases. SPA discriminates on this exact string.
- `detail`: operator-friendly copy interpolating the character's name. NO mention of `M2M` / `audience_scope` / `CHARACTER` / retrieval predicate internals per task rule.

## §216. SPA behavior

- **New pure helper:** `finalDetachErrorMessage(err)` exported from `web/src/components/knowledge-panel.tsx` extracts the `detail` string from an `ApiError` iff `body.code === FINAL_DETACH_ERROR_CODE`. Returns `null` otherwise (caller falls back to existing generic error handling).
- **`handleDetach` extended:** now wraps `toggle.mutateAsync(...)` in try/catch; on `finalDetachErrorMessage`-hit it sets local state and re-throws is skipped. Other errors bubble up unchanged.
- **Inline alert** (role="alert"): appears below the row when `finalDetachMessage` is set. Shows the backend `detail` + a "Dismiss" button (data-testid `final-detach-dismiss-<id>`). No promotion buttons.
- **No new SPA API surface**: no new payload field, no new endpoint, no new hook, no new mutation.

## §217. Backend tests (`shell/apps/embeddings/tests/test_api_k5.py`)

9 new tests appended, `_make_character_doc` helper added.

| Test | Coverage | Status |
|---|---|---|
| A `test_slice13_A_multi_character_detach_narrows_normally` | {A,B} + detach A → {B}, audience_scope stays CHARACTER | PASS |
| B `test_slice13_B_final_character_detach_rejected` | {A} + detach A → HTTP 400 + `code=final_character_detach_requires_audience_decision` + full state preservation | PASS |
| C `test_slice13_C_final_detach_leaves_through_row_intact` | KnowledgeDocumentSpokesperson count pre==post rejection (mechanically verifies pre-mutation guard) | PASS |
| D `test_slice13_D_universe_scoped_character_final_detach_rejected` | Universe=U + CHARACTER + {A} + detach A → 400 (Universe context does NOT auto-promote to UNIVERSE) | PASS |
| E `test_slice13_E_multi_character_universe_scoped_detach_narrows` | Universe=U + CHARACTER + {A,B} + detach A → {B}, Universe stays U | PASS |
| F `test_slice13_F_detach_of_unattached_spokesperson_is_still_noop` | Idempotent detach of non-attached SP still succeeds 200 (guard's `exists()` precondition prevents false positives) | PASS |
| G-workspace `test_slice13_G_workspace_audience_row_unaffected_by_guard` | WORKSPACE canon with empty M2M — detach any SP is a 200 no-op | PASS |
| G-universe `test_slice13_G_universe_audience_row_unaffected_by_guard` | UNIVERSE canon with empty M2M — same | PASS |
| Legacy `test_slice13_legacy_null_audience_detach_behavior_preserved` | Pre-Delta fixture rows (audience_scope=NULL, M2M non-empty) still allow legacy detach behavior — documents deliberate carve-out | PASS |

## §218. SPA tests (new file `knowledge-panel.final-detach.test.tsx`)

5 new Vitest unit tests for `finalDetachErrorMessage`:

- Exact Slice 13 code + structured body → returns `detail` string.
- Different `code` → returns `null`.
- Non-`ApiError` (native Error / null / string) → returns `null`.
- `ApiError` with missing / malformed body → returns `null`.
- Substring-collision guard (`code` with suffix) → returns `null`.

All 5 pass.

## §219. Universe-scoped CHARACTER case + multi-character case + shared-canon case

- **Universe-scoped CHARACTER, final detach:** Test D → 400 (guard fires; Universe context does NOT bypass).
- **Universe-scoped CHARACTER, multi-detach:** Test E → 200 (Universe stays; M2M narrows; audience_scope=CHARACTER preserved).
- **UNIVERSE / WORKSPACE shared canon:** Tests G-workspace / G-universe → 200 no-op (guard is CHARACTER-only; empty M2M is legitimate for these audience states so no false positive).

## §220. PATCH `spokesperson_ids=[]` audit (READ-ONLY, NOT fixed in Slice 13)

**Location:** `shell/apps/embeddings/serializers.py:564-565` — `KnowledgeDocumentSerializer.update()` calls `instance.spokespeople.set(validated_data["spokespeople"])` with zero guard.

**Behavior today:** `PATCH /api/knowledge/<id>/ {"spokesperson_ids": []}` on an active CHARACTER KD → M2M emptied silently → row becomes `CHARACTER + empty M2M` (Slice 4 §51 row #3 malformed shape). Under legacy retrieval predicate this KD would broadcast to eligible teammates in scope.

**Slice 13 detach guard has NO effect on this path** — the guard lives on the `_toggle_spokesperson` view action, not on the serializer's `update()`. Different code path.

**Recorded as Q-276-28 candidate** (§227). Slice 13 does not fix; task instruction explicit.

## §221. Real-DB post-Slice-13 verification

Code changed; real DB rows did not change. No detach executed against production data during Slice 13.

```
$ manage.py shell -c "..."
total=72
distribution={'universe': 3, 'character': 59, None: 10}
inactive=0
chunks=1149
m2m=62
```

Byte-identical to Slice 7 §103 through Slice 12 §202. **Zero drift across 7 consecutive slices.**

## §222. Regression results

```
$ pytest apps/embeddings/tests/test_api_k5.py -v
19 passed in 6.33s                          # 10 existing + 9 new (A/B/C/D/E/F/G-ws/G-u/legacy)

$ pytest apps/embeddings/ apps/spokespeople/ apps/universe/ apps/compositions/ -q
1684 passed, 2 warnings in 133.50s          # broader — +9 from Slice 12's 1675

$ pnpm exec vitest run
656 passed across 49 files                  # SPA suite — +5 from Slice 12's 651

$ python manage.py makemigrations --check embeddings
No changes detected in app 'embeddings'
```

Every existing test still passes. 2 pre-existing DateTime warnings unrelated.

## §223. Prediction vs actual

| Prediction (§211) | Actual | Status |
|---|---|---|
| Count>1 detach unchanged | Tests A, E pass | ✓ |
| Count==1 CHARACTER detach rejected before mutation | Tests B, C, D pass; through-row count preserved | ✓ |
| Universe-scoped CHARACTER behaves identically to legacy CHARACTER on final detach | Test D passes | ✓ |
| Shared canon unaffected | Tests G-workspace, G-universe pass | ✓ |
| SPA clearly explains blocked operation | Inline alert with role="alert" + backend `detail` copy | ✓ |
| No new audience transition introduced | Zero promotion buttons; zero audience PATCH; scope preserved | ✓ |
| PATCH empty-list hole remains separate | Confirmed in §220 audit — hole intact, deferred to Q-276-28 | ✓ |
| Real DB unchanged | 72 KDs, same distribution, 0 inactive; 7 consecutive slices with zero drift | ✓ |

**Refined Q-276-27 CONFIRMED.** Zero falsifications. Zero unexpected findings.

## §224. Files changed (Slice 13)

```
 M shell/apps/embeddings/views.py                                            (+~45 lines net — AudienceScope import + docstring + final-detach guard block)
 M shell/apps/embeddings/tests/test_api_k5.py                                (+~230 lines — 2 imports + _make_character_doc helper + 9 new tests)
 M web/src/components/knowledge-panel.tsx                                    (+~65 lines net — useState + ApiError import + finalDetachErrorMessage helper + handleDetach try/catch + inline alert)
?? web/src/components/knowledge-panel.final-detach.test.tsx                  (new — 64 lines, 5 tests)
?? docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md                     (this Slice 13 section)
```

Zero backend model / migration / signal / serializer / admin / retrieval / ingestion changes. Zero SPA payload / API / hook / mutation changes. Slice 13 is strictly scoped to the detach endpoint + SPA error surfacing.

## §225. Unresolved questions

Carried from prior slices (all still open):

- **Promoted from audit to primary next-slice candidate: PATCH `spokesperson_ids=[]` hole (Q-276-28).** §220 confirms the hole is intact and outside the Slice 13 detach guard's coverage.
- Serializer PATCH `audience_scope` transitions (CHARACTER→UNIVERSE, CHARACTER→WORKSPACE, revival contract). Needs its own falsifiable question.
- Attach/detach transition for `NULL-audience + M2M` legacy fixtures — real DB has zero; test fixtures only. Documented carve-out.
- Universe reassignment audience implications (Slice 3 §37 T14/T15).
- Provenance direction Alpha vs Beta.
- Retrieval predicate switch (Stage 5).
- Operator triage UI for the 10 ambiguous rows (Stage 4).
- DB CHECK constraints + NOT NULL cutover (Stage 6).
- Bundle vs split (still open from Slice 1 §8.4).

**No new Slice-13-specific unresolved questions.**

## §226. Recommendation

**Refined Q-276-27 is confirmed. The live SPA-facing detach-final audience-broadening hole is closed.** Under Delta invariants, the operator cannot silently transform a CHARACTER-scoped KD into a broadcast KD by clicking "Detach" on the last spokesperson. The rejection copy explicitly names the operator's next-choice options (new audience or archive/delete) without wiring any new mutation.

Slice 13 does not authorize any further work. The natural next slice closes the parallel PATCH-empty-list hole so both detach paths on the KD's spokespeople M2M are Delta-coherent.

## §227. Explicit STOP gate

**STOP.** Slice 13 authorizes no further work.

Do NOT begin:

- PATCH `spokesperson_ids=[]` fix (Q-276-28 candidate)
- Generic audience PATCH contract
- CHARACTER → UNIVERSE promotion
- CHARACTER → WORKSPACE promotion
- Universe reassignment audience changes
- Provenance work
- Retrieval predicate change
- Operator triage UI
- DB CHECK constraints
- NOT NULL cutover
- Recovery UI or promotion buttons in the SPA

## §228. Smallest recommended next question

**Q-276-28.** *If `KnowledgeDocumentSerializer.update()` at `shell/apps/embeddings/serializers.py:564-565` is extended so that setting `spokesperson_ids=[]` on an active `audience_scope=CHARACTER` KD is rejected with the same structured `final_character_detach_requires_audience_decision` error the Slice 13 detach endpoint returns, does the parallel PATCH-empty-list broadening path close without changing any legitimate multi-character audience-narrowing PATCH?*

Falsifiable by:
1. Extending `update()` with a pre-set check: if `"spokespeople" in validated_data` AND `validated_data["spokespeople"] == []` AND `instance.audience_scope == CHARACTER` AND `instance.spokespeople.count() >= 1`, raise the same structured 400 the Slice 13 detach guard uses.
2. Regression tests: (a) PATCH `spokesperson_ids=[c]` (multi-character narrowing) still succeeds; (b) PATCH `spokesperson_ids=[]` on CHARACTER rejected with same code; (c) PATCH `spokesperson_ids=[]` on WORKSPACE / UNIVERSE (no-op) unchanged; (d) legacy NULL-audience rows unchanged.

Small change; symmetric with Slice 13; closes the last SPA-independent audience-broadening path on the M2M surface.

## §229. Slice 13 checklist

- [x] Step 0 — commit + push Slice 12 SHA-record (commit `e2fbdcb`)
- [x] Slice 13 baseline verified — `main == origin/main == e2fbdcb`, working tree clean at slice start
- [x] Refined Q-276-27 falsifiable question stated (§210)
- [x] Predictions before evidence (§211)
- [x] Detach source trace (§212)
- [x] NULL-audience state audit — real DB zero + test fixture carve-out documented (§213)
- [x] Backend guard design (§214) — 4-part conjunction, CHARACTER-only, pre-mutation
- [x] Structured error contract defined (§215)
- [x] SPA behavior extended (§216) — `finalDetachErrorMessage` helper + inline alert; NO promotion buttons
- [x] Backend Test A: multi-character detach unchanged
- [x] Backend Test B: final-character detach rejected with structured 4xx
- [x] Backend Test C: no partial mutation (through-row count preserved)
- [x] Backend Test D: Universe-scoped CHARACTER final detach also rejects
- [x] Backend Test E: multi-character Universe-scoped detach narrows normally
- [x] Backend Test F: non-attached SP detach still 200 no-op
- [x] Backend Test G: WORKSPACE / UNIVERSE canon rows unaffected
- [x] Backend legacy-carve-out test: NULL-audience fixture behavior preserved
- [x] SPA tests: 5 unit tests for `finalDetachErrorMessage` discrimination
- [x] PATCH `spokesperson_ids=[]` audit performed (§220) — hole confirmed intact; deferred to Q-276-28
- [x] 19/19 K5 API tests pass (§222)
- [x] 1684/1684 broader backend regression pass (§222)
- [x] 656/656 SPA suite pass across 49 files (§222)
- [x] `makemigrations --check embeddings` clean (§222)
- [x] Real DB unchanged: 72 KDs, `CHARACTER=59, UNIVERSE=3, NULL=10, NONE=0, inactive=0` (§221)
- [x] Prediction vs actual — refined Q-276-27 CONFIRMED (§223)
- [x] Files changed inventory (§224)
- [x] Explicit STOP gate (§227)
- [x] Smallest next question Q-276-28 (§228)
- [x] Zero PATCH audience / CHARACTER→UNIVERSE / CHARACTER→WORKSPACE / Universe reassignment / provenance / retrieval / migration / model / constraint changes; zero recovery UI or promotion buttons; zero provider spend
- [x] Commit + push Slice 13 — landed as `f5dd9e8`
- [x] Chris + ChatGPT review + Slice 14 scoping decision (§226) — Q-276-28 authorized: extend `KnowledgeDocumentSerializer.update` to reject PATCH `spokesperson_ids=[]` on active CHARACTER KDs; reuse Slice 13 error code

---

**End of SESSION 276 Slice 13 / Delta Stage 3C-1. Final-character detach on active CHARACTER KDs now fails closed with a structured 4xx BEFORE any M2M mutation; SPA surfaces the backend `detail` inline without wiring audience-promotion buttons. Refined Q-276-27 CONFIRMED — 19/19 K5 API tests pass (10 existing + 9 new); 1684/1684 broader backend regression + 656/656 SPA suite; multi-character detach unchanged; Universe context does NOT auto-promote to UNIVERSE; shared canon rows unaffected. Real DB unchanged for 7th consecutive slice. STOP for Chris + ChatGPT review of §226 recommendation, §227 gate, and §228 Q-276-28 next question.**

**Slice 13 landed commit SHA:** `f5dd9e8` (`fix(session-276): Slice 13 / Delta Stage 3C-1 — final-character detach fails closed`). Pushed to `origin/main`. Post-push `main == origin/main == f5dd9e8`; working tree clean.

**Slice 13 SHA-record follow-up:** `a154ae3` (`docs(session-276): record Slice 13 landed SHA f5dd9e8`) — doc-only checklist + Slice 14 authorization record.

---

# SESSION 276 — Slice 14 / Delta Stage 3C-2 — PATCH empty-spokesperson-set fails closed (Q-276-28)

**Status.** IMPLEMENTATION SLICE — closes the parallel serializer-equivalent hole flagged in Slice 13 §220. `KnowledgeDocumentSerializer.update()` now rejects `PATCH {"spokesperson_ids": []}` on active `audience_scope=CHARACTER` KDs with a structured 4xx BYTE-IDENTICAL to Slice 13's `/detach/` guard. Backend-only slice; SPA currently has no PATCH-empty-list caller today.

**Slice 14 baseline.** `main == origin/main == a154ae3` (Slice 13 SHA-record). Working tree clean at slice start. Real-DB state carried forward through 8 slices now:

- 72 KDs; `CHARACTER=59`, `UNIVERSE=3`, `NULL=10`, `WORKSPACE=0`, `NONE=0`
- 0 inactive, 1149 chunks, 62 M2M through-rows
- Migration head: `0008_session276_stage2_backfill`

**Load-bearing rule** carried forward + refined:

> `audience_scope=CHARACTER` requires at least one spokesperson at all times while active. Applies to BOTH `/detach/` and PATCH mutation surfaces.

## §230. Slice 14 falsifiable question — Q-276-28

> If `KnowledgeDocumentSerializer.update()` refuses an explicit `spokesperson_ids=[]` replacement on an active `audience_scope=CHARACTER` `KnowledgeDocument` before calling `.set([])`, while preserving legitimate non-empty replacement / narrowing behavior, does the parallel PATCH-empty-list audience-broadening path close without changing any other current PATCH semantics?

## §231. Predictions before evidence

1. Explicit empty replacement on active CHARACTER rejects (Test A).
2. No M2M mutation occurs on rejection.
3. Multi-character narrowing (Test C) remains valid.
4. Character replacement (Test D) remains valid.
5. Universe-scoped CHARACTER also rejects empty list (Test E).
6. Shared canon (UNIVERSE / WORKSPACE) unchanged (Tests F).
7. Legacy NULL-audience rows unchanged (Test G).
8. No partial field mutation on rejection (Test H).
9. `/detach/` and PATCH now enforce the SAME machine-readable error code (Test error-symmetry).
10. Real DB unchanged.

Compared to evidence in §246.

## §232. Serializer source + order trace (pre-Slice-14)

- **`spokesperson_ids` field decl:** `serializers.py:61-66` — `PrimaryKeyRelatedField(many=True, source="spokespeople", required=False)`. No `default=`. On DRF PATCH: an omitted key is absent from `validated_data`; an explicit `[]` is present as `validated_data["spokespeople"] == []`.
- **DRF flow:** `is_valid()` → runs `run_validation` → calls `validate()` → wraps any raised errors via `as_serializer_error()` (which wraps dict values in lists). Then if valid, `save()` calls `update(instance, validated_data)`. Errors raised from `update()` propagate straight to the global exception handler WITHOUT going through `as_serializer_error`.
- **Empty vs omit collapse:** existing code uses `attrs.get("spokespeople") or []` at `serializers.py:211` — collapses omitted / None / empty into `[]`. To distinguish explicit empty from omission, must use `"spokespeople" in validated_data`.
- **`update()` mutation order** (post-Slice-14 line numbers): guard → forbidden-field check → drop `via_serper` → drop `audience_scope` → pop `text_content` → assign `title` → universe preflight + assign → text_content re-ingest → `save(update_fields=...)` → `spokespeople.set(...)`.

## §233. Explicit-empty vs omit distinguishing evidence

DRF's `PrimaryKeyRelatedField(many=True, required=False)` treats:

- **Key omitted** → key absent from `validated_data`.
- **Key present with `[]`** → `validated_data["spokespeople"] == []`.
- **Key present with `[uuid]`** → `validated_data["spokespeople"] == [<Teammate>]` (resolved to objects).

`"spokespeople" in validated_data` is the reliable disambiguator. Test C (narrowing works via `[uuid]`) and Test A (rejection via `[]`) both pass with this check.

## §234. Guard location + rationale — top of `update()`, NOT `validate()`

Initial implementation placed the guard in `validate()`. Test `test_slice14_error_code_matches_slice13_detach_guard` **failed** — DRF's `as_serializer_error()` wraps dict values in lists during `run_validation`, producing `{"code": ["final_character_..."], "detail": [...]}` instead of `{"code": "final_character_...", "detail": "..."}`.

Slice 13's `/detach/` guard raises from a VIEW (`views.py`) which bypasses the serializer wrapping — the global exception handler renders `.detail` as-is.

**Fix applied:** move the guard to the top of `update()` (which is called after `is_valid()` completes). Raising `serializers.ValidationError({...})` from `update()` bypasses `as_serializer_error` — the response body matches Slice 13's shape byte-identically. Verified by `test_slice14_error_code_matches_slice13_detach_guard`.

Atomicity preserved: `update()`'s first mutation-eligible line (`instance.title = validated_data["title"]` at `serializers.py:558`) runs AFTER the guard. Raising from the top of `update()` guarantees no field is partially applied (Test H proves this: `title` change bundled with `spokesperson_ids=[]` results in title NOT persisting alongside the rejected PATCH).

## §235. Serializer diff (`shell/apps/embeddings/serializers.py`)

Two changes:

**1.** Import extended:

```python
# Before:
from .models import DocumentType, KnowledgeChunk, KnowledgeDocument
# After:
from .models import AudienceScope, DocumentType, KnowledgeChunk, KnowledgeDocument
```

**2.** Guard inserted at top of `update()` (before any mutation, before `pdf_data_uri`/`source_url_input` create-only checks that raise for OTHER reasons):

```python
def update(self, instance, validated_data):
    # SESSION 276 Slice 14 guard (docstring block explains rationale)
    if (
        "spokespeople" in validated_data
        and validated_data["spokespeople"] == []
        and instance.is_active
        and instance.audience_scope == AudienceScope.CHARACTER
    ):
        raise serializers.ValidationError({
            "code": "final_character_detach_requires_audience_decision",
            "detail": (
                "This knowledge needs at least one character unless "
                "you choose a different audience or archive it."
            ),
        })
    # ... rest of update() unchanged ...
```

Zero other changes to `validate()`, `create()`, or any other serializer method. Zero view / signal / model / migration / SPA change.

## §236. Error contract consistency with Slice 13

Both guards emit HTTP 400 with body:

```json
{
  "code": "final_character_detach_requires_audience_decision",
  "detail": "<operation-appropriate string>"
}
```

- **`code`** — byte-identical string `"final_character_detach_requires_audience_decision"`. Verified by `test_slice14_error_code_matches_slice13_detach_guard` which hits BOTH endpoints in the same test and asserts equality. Prevents future drift.
- **`detail`** — differs slightly between the two operations (detach interpolates the character's name; PATCH uses generic copy because it may be replacing multi-member set). Both are operator-friendly with no `M2M`/`audience_scope`/`CHARACTER` internals per task rule.
- **Terminology debt** (documented, not resolved): the `code` string contains "detach" which is now used for both `/detach/` and PATCH-empty paths. Renaming would be a scope expansion and would break the Slice 13 SPA test discrimination. Accepted; documented here.

## §237. Test A — CHARACTER {A} + PATCH `[]` rejected

`_make_char_doc_with_sp(ws, "s14-a", [a])` → PATCH `spokesperson_ids=[]` → HTTP 400 with structured `code` + `detail`. Post-rejection: `spokespeople=[a.pk]`, `audience_scope=CHARACTER`, `is_active=True`, `deactivated_reason=""`, `title` unchanged.

## §238. Test B — CHARACTER {A,B} + PATCH `[]` also rejected

Multi-member CHARACTER row + `[]` also rejects. Proves the invariant is about the RESULTING row shape (CHARACTER + empty M2M is malformed), not about "count > 1 protection." Both A and B remain attached post-rejection.

## §239. Test C — Narrowing via PATCH still works

`{A,B}` + `spokesperson_ids=[b]` → HTTP 200, M2M becomes `{B}`, `audience_scope=CHARACTER` preserved. Legitimate audience-narrowing intact.

## §240. Test D — Character replacement via PATCH still works

`{A}` + `spokesperson_ids=[b]` → HTTP 200, M2M becomes `{B}`. Replacement path unchanged.

## §241. Test E — Universe-scoped CHARACTER final empty rejected

`universe=U, CHARACTER, {A}` + PATCH `[]` → HTTP 400. Universe context does NOT bypass the guard — Universe context is not audience intent for UNIVERSE-shared promotion. Symmetric with Slice 13 Test D.

## §242. Test F — Shared canon no-op behavior preserved

- WORKSPACE row with empty M2M + PATCH `[]` → HTTP 200 no-op. `audience_scope=WORKSPACE` unchanged.
- UNIVERSE row with empty M2M + PATCH `[]` → HTTP 200 no-op. `audience_scope=UNIVERSE` + `universe_id` unchanged.

Guard is CHARACTER-only; no false positives on shared-canon rows.

## §243. Test G — NULL legacy carve-out unchanged

Legacy fixture shape (`audience_scope=None`, non-empty M2M) — Slice 14 does NOT guard. PATCH `[]` still empties M2M, matching pre-Slice-14 behavior. Documented transitional debt. Real DB has ZERO such rows (Slice 7 backfill covered all M2M-carrying rows); only test fixtures land here.

## §244. Test H — No partial unrelated-field mutation on rejection

`{"title": "changed-title", "spokesperson_ids": []}` on CHARACTER `{A}` → HTTP 400 (audience code); post-rejection `doc.title` is UNCHANGED. Mechanically proves the guard's top-of-`update()` placement gives atomic all-or-nothing rejection.

## §245. Test I — Combined Universe + empty rejected

`{"universe": <U_to>, "spokesperson_ids": []}` on CHARACTER `{A}` at `universe=U_from` → HTTP 400. Post-rejection `universe_id == U_from.pk` (Universe DID NOT move). Prevents a broadening path where an empty-spokespeople request could sneak through a Universe transition in the same request. Slice 14 does NOT define correct Universe-transition audience semantics — those remain a separate unresolved question.

## §246. PATCH Universe composition audit

Bundled `universe` + `spokesperson_ids=[]` payloads are now atomically rejected (§245). The empty-spokespeople portion trips the guard first (top of `update()`); the Universe change never applies. Any operator gesture that legitimately wants to reassign a KD's Universe must NOT include an empty spokesperson list on a CHARACTER KD — they should either supply the new spokesperson set alongside the Universe change or omit `spokesperson_ids` entirely.

Universe reassignment on non-CHARACTER audiences (UNIVERSE canon, WORKSPACE canon) remains a **separate unresolved question** — Slice 14 does not modify its behavior. Recorded in §249.

## §247. Real-DB post-Slice-14 verification

Code changed; real DB rows did not change. No PATCH executed against production data during Slice 14.

```
$ manage.py shell -c "..."
total=72
distribution={'universe': 3, 'character': 59, None: 10}
inactive=0
chunks=1149
m2m=62
```

Byte-identical to Slice 7 §103 through Slice 13 §221. **Zero drift across 8 consecutive slices.**

## §248. Regression results

```
$ pytest apps/embeddings/tests/test_api.py -v -k "slice14"
11 passed in 5.27s                          # Slice 14 new tests

$ pytest apps/embeddings/tests/test_api.py \
         apps/embeddings/tests/test_api_k5.py \
         apps/embeddings/tests/test_ingestion.py \
         apps/spokespeople/tests/test_delete_orphan_archive.py -q
101 passed in 14.23s                        # combined API + K5 + ingestion + lifecycle

$ pytest apps/embeddings/ apps/spokespeople/ apps/universe/ apps/compositions/ -q
1695 passed, 2 warnings in 130.79s          # broader — +11 from Slice 13's 1684

$ python manage.py makemigrations --check embeddings
No changes detected in app 'embeddings'
```

Every existing test still passes. 2 pre-existing DateTime warnings unrelated.

SPA suite NOT run — zero frontend files touched. Task rule permits skipping SPA suite when no frontend change.

## §249. Unresolved questions

Carried from prior slices (all still open):

- **Generic audience PATCH contract** — CHARACTER→UNIVERSE, CHARACTER→WORKSPACE, UNIVERSE→WORKSPACE, WORKSPACE→UNIVERSE, NONE revival — each requires its own independent semantics/authorization.
- **Universe reassignment on non-CHARACTER rows** — Slice 14 §246 audit noted: PATCH `universe=<new>` on a UNIVERSE-audience row currently succeeds without changing `audience_scope`. Whether that's a broadening path (audience remains UNIVERSE but now points at a different member set) needs its own falsifiable question.
- Provenance direction Alpha vs Beta.
- Retrieval predicate switch (Stage 5).
- Operator triage UI for the 10 ambiguous rows (Stage 4).
- DB CHECK constraints + NOT NULL cutover (Stage 6).
- Bundle vs split (still open from Slice 1 §8.4).
- **Terminology debt** — the shared `code` string `"final_character_detach_requires_audience_decision"` contains "detach" but now applies to both `/detach/` and PATCH-empty operations. A future terminology renaming (e.g. `"character_audience_cannot_become_empty"`) would require coordinated SPA + backend + external-client updates. Deferred.

**No new Slice-14-specific unresolved questions.**

## §250. Recommendation

**Q-276-28 is confirmed. Both KD-spokespeople M2M mutation surfaces (`/detach/` and PATCH `spokesperson_ids=[]`) now fail closed on the CHARACTER-audience broadening path.** The invariant `active CHARACTER requires ≥1 spokesperson` is enforced at both surfaces with byte-identical machine-readable error codes.

Combined with Slice 13, the last two live audience-broadening paths on the KD spokespeople M2M surface (identified in Slice 3 §37.J/T11) are closed. Legitimate narrowing and replacement continue to work; shared canon unaffected; legacy NULL carve-out preserved.

Slice 14 does not authorize any further work. The natural next slices are Universe reassignment audience semantics (§249) or one of the deferred stages (retrieval cutover, legacy triage, constraints).

## §251. Explicit STOP gate

**STOP.** Slice 14 authorizes no further work.

Do NOT begin:

- Generic audience PATCH contract
- CHARACTER → UNIVERSE promotion
- CHARACTER → WORKSPACE promotion
- Universe reassignment redesign (audience semantics)
- Provenance work
- Retrieval predicate change
- Operator triage UI
- DB CHECK constraints
- NOT NULL cutover
- Recovery UI

## §252. Smallest recommended next question

**Q-276-29 (candidate — Universe reassignment audience audit).** *If `KnowledgeDocumentSerializer.update()` receives a PATCH containing `{"universe": <U_new>}` on an active row whose `audience_scope=UNIVERSE`, what is the current behavior and does it change the effective retrieval audience? Is a Universe reassignment on a UNIVERSE-audience row a legitimate scope migration or an audience-broadening path that needs its own guard?*

Falsifiable by:
1. Read-only source trace of the existing `serializers.py:499-514` `universe` PATCH branch under Slice 12/14 code.
2. Tests: (a) PATCH `universe=<U_new>` on `UNIVERSE, universe=U_old, M2M=∅` — does the KD's retrieval audience change from "everyone in U_old" to "everyone in U_new"? (b) PATCH `universe=null` on same → what happens to `audience_scope`? Currently `audience_scope` is not touched by PATCH; that means a Universe-audience row could end up as `UNIVERSE + universe=null` — a Slice 4 §51 row-#5 malformed shape.
3. Decision: whether to reject with a structured 400 (matching the audience-invariant enforcement pattern from Slices 13/14), auto-transition audience_scope, or preserve current behavior.

Small audit-first slice; unresolved whether it needs a code-change slice after or stays audit-only pending broader audience-PATCH contract design.

## §253. Slice 14 checklist

- [x] Step 0 — commit + push Slice 13 SHA-record (commit `a154ae3`)
- [x] Slice 14 baseline verified — `main == origin/main == a154ae3`, working tree clean at slice start
- [x] Q-276-28 falsifiable question stated (§230)
- [x] Predictions before evidence (§231)
- [x] Serializer source + order trace (§232) — `spokesperson_ids` field decl, DRF flow, mutation order
- [x] Explicit-empty vs omit distinguishing evidence (§233)
- [x] Guard location + rationale — top of `update()` NOT `validate()` (§234) — required to preserve error-shape symmetry with Slice 13
- [x] Serializer diff (§235) — one import + one guard block
- [x] Error contract consistency with Slice 13 (§236) — byte-identical `code`, terminology debt documented
- [x] Test A — CHARACTER {A} + PATCH [] rejected (§237)
- [x] Test B — CHARACTER {A,B} + PATCH [] also rejected (§238)
- [x] Test C — narrowing via PATCH still works (§239)
- [x] Test D — character replacement via PATCH still works (§240)
- [x] Test E — Universe-scoped CHARACTER empty rejected (§241)
- [x] Test F — shared canon no-op preserved (WORKSPACE + UNIVERSE) (§242)
- [x] Test G — legacy NULL carve-out unchanged (§243)
- [x] Test H — atomic rejection preserves title (§244)
- [x] Test I — combined Universe + empty rejected (§245)
- [x] Error-code-symmetry test — `/detach/` code === PATCH code byte-identical
- [x] Universe composition audit (§246)
- [x] 11/11 Slice 14 tests pass (§248)
- [x] 101/101 combined API + K5 + ingestion + lifecycle (§248)
- [x] 1695/1695 broader backend regression pass (§248)
- [x] `makemigrations --check embeddings` clean (§248)
- [x] Real DB unchanged: 72 KDs, `CHARACTER=59, UNIVERSE=3, NULL=10, NONE=0, inactive=0` (§247)
- [x] Prediction vs actual — Q-276-28 CONFIRMED (§246 — all 10 predictions supported)
- [x] Files changed inventory (§235 — one file: `serializers.py`; plus 11 new tests in `test_api.py`)
- [x] Explicit STOP gate (§251)
- [x] Smallest next question Q-276-29 candidate (§252)
- [x] Zero SPA changes (backend-only slice); zero generic audience PATCH / CHARACTER→UNIVERSE / CHARACTER→WORKSPACE / Universe reassignment redesign / provenance / retrieval / migration / model / constraint changes; zero provider spend
- [x] Commit + push Slice 14 — landed as `9be7f33`
- [x] Chris + ChatGPT review + Slice 15 scoping decision (§250) — Q-276-29 authorized audit-first: narrow shape-preservation guards allowed only if evidence justifies

---

**End of SESSION 276 Slice 14 / Delta Stage 3C-2. PATCH `spokesperson_ids=[]` on active CHARACTER KDs now fails closed with a structured 4xx BEFORE any mutation, byte-identical to Slice 13's `/detach/` code. Q-276-28 CONFIRMED — 11/11 Slice 14 tests pass; 1695/1695 broader backend regression; legitimate narrowing/replacement PATCH unchanged; shared canon unaffected; legacy NULL carve-out preserved; atomic rejection prevents partial field mutation; combined Universe+empty rejected atomically. Real DB unchanged for 8th consecutive slice. STOP for Chris + ChatGPT review of §250 recommendation, §251 gate, and §252 Q-276-29 candidate next question.**

**Slice 14 landed commit SHA:** `9be7f33` (`fix(session-276): Slice 14 / Delta Stage 3C-2 — PATCH empty-spokespeople fails closed`). Pushed to `origin/main`. Post-push `main == origin/main == 9be7f33`; working tree clean.

**Slice 14 SHA-record follow-up:** `bb077d3` (`docs(session-276): record Slice 14 landed SHA 9be7f33`) — doc-only checklist + Slice 15 authorization record.

---

# SESSION 276 — Slice 15 / Delta Stage 3C-3 — Universe reassignment audience semantics (Q-276-29)

**Status.** AUDIT-FIRST SLICE with two narrow shape-preservation guards independently justified by the audit. Both guards are shape-preservation, NOT audience-transition — they reject Delta-invariant-violating Universe-PATCH shapes without auto-transitioning `audience_scope`. `UNIVERSE→UNIVERSE` swap behavior preserved (no positive-intent evidence for a stricter rule).

**Slice 15 baseline.** `main == origin/main == bb077d3` (Slice 14 SHA-record). Working tree clean at slice start. Real-DB state carried forward through 9 slices:

- 72 KDs; `CHARACTER=59`, `UNIVERSE=3`, `NULL=10`, `WORKSPACE=0`, `NONE=0`
- 0 inactive, 1149 chunks, 62 M2M through-rows
- Zero Delta-invariant violations across all 4 invariants (§256)

## §254. Slice 15 falsifiable question — Q-276-29

> When an active `KnowledgeDocument`'s `universe` field is changed through PATCH, what product/audience transition does that operation actually mean for each existing `audience_scope`, and which transitions are explicit, Delta-coherent audience decisions versus accidental malformed/broadened states?

## §255. Predictions before evidence

- **A** UNIVERSE + U_old → UNIVERSE + U_new may be legitimate IF all callers proved to send it as explicit audience choice.
- **B** UNIVERSE → NULL invalid under Delta; should fail closed.
- **C** WORKSPACE + universe=U creates malformed shape; must not silently succeed.
- **D** CHARACTER Universe reassignment likely already protected by existing M2M-orphan preflight.
- **E** Correct behavior may be scope-specific rather than one generic rule.
- **F** Existing serializer likely permits at least one malformed Delta shape because `audience_scope` isn't touched.

Compared to evidence in §271.

## §256. Real-DB pre-audit — Delta invariant violations

Read-only queries against production data:

```
CHARACTER + empty M2M:      0
UNIVERSE + universe=NULL:   0
WORKSPACE + universe:       0
active + audience_scope=NONE: 0
```

**Zero rows currently violate any Delta invariant.** Guards added by this slice are purely defensive — they protect FUTURE PATCH operations from producing the two reachable malformed shapes (§262).

## §257. Universe-PATCH caller inventory

Full-repo grep for callers that send `universe` in a PATCH payload:

| # | Caller | Sends `universe` on PATCH? | Notes |
|---|---|---|---|
| 1 | SPA `web/src/routes/workspace/knowledge.tsx` — 4 create sites | NO — all use CREATE only (`useCreateKnowledge`); no updateKnowledge callers with universe | |
| 2 | SPA `web/src/components/spokesperson-ask-panel.tsx` — Beat 3 fix-loop | NO — `useUpdateKnowledge` sends `{text_content}` only (`ask-panel.tsx:509-512`) | |
| 3 | DRF `KnowledgeDocumentSerializer.update` | n/a — receives PATCH from external clients | |
| 4 | `smoke_ingest` mgmt command | NO — creates only, never PATCHes | |
| 5 | `scripts/session272_slice_b_setup.py` | NO | |
| 6 | `scripts/session273_slice_alpha_ingest_kd.py` | NO | |

**Zero production callers PATCH the `universe` field today.** External API clients (curl, third-party integrations) could theoretically trigger it via `PATCH /api/knowledge/<id>/ {"universe": ...}` but no such caller exists in the repository. This means:

1. Slice 15 guards CANNOT break any current operator gesture.
2. The `UNIVERSE→UNIVERSE` swap "audience-replacement" question has NO current caller evidence supporting an explicit-intent gesture. Per task Prediction A rule: preserve current behavior; do NOT block. Future audience-transition contract design remains a deferred question.

## §258. Serializer `update()` Universe branch source trace

Post-Slice-14 layout (`shell/apps/embeddings/serializers.py:556-581`):

```python
if "universe" in validated_data:
    new_universe = validated_data["universe"]
    # M2M-orphan preflight (SESSION 261)
    if instance.pk:
        bad = instance.spokespeople.exclude(
            universe_id=(new_universe.pk if new_universe else None),
        )
        if bad.exists():
            raise ValidationError({"universe": "Reassigning would orphan..."})
    instance.universe = new_universe
    changed_fields.append("universe")
```

**Existing preflight only checks M2M-orphan (cross-Universe consistency).** Does NOT consider `audience_scope`. Therefore:

- CHARACTER + M2M non-empty: preflight protects against orphaning M2M members. ✓
- CHARACTER + empty M2M: preflight passes trivially (empty M2M has no cross-Universe rows). Row is ALREADY malformed regardless (Slice 4 §51 row #3).
- UNIVERSE + empty M2M: preflight passes trivially. Universe change applies WITHOUT touching `audience_scope`. Reachable malformed shapes (§262).
- WORKSPACE + empty M2M: same — preflight passes; Universe change applies; malformed reachable.

Save order: `title` → `universe` (with preflight) → `text_content` → `save(update_fields)` → M2M `.set()`. All inside DRF request's atomic block; Slice 14 guard added at top of `update()` runs first.

## §259. Scope × Universe transition matrix

Every reachable combination of start state × PATCH input. "Current" = post-Slice-14 behavior. "Guard-worthy?" = does the transition produce a Delta-malformed shape?

| # | Start state | PATCH | Current behavior | Post-transition Delta shape | Guard-worthy? |
|---|---|---|---|---|---|
| 1 | CHARACTER, universe=NULL, M2M={A legacy} | universe=U | M2M-preflight REJECTS (A.universe=None ≠ U) | n/a (already blocked) | No — existing protection |
| 2 | CHARACTER, universe=U_old, M2M={A in U_old} | universe=U_new | M2M-preflight REJECTS (A.universe=U_old ≠ U_new) | n/a | No |
| 3 | CHARACTER, universe=U, M2M={A in U} | universe=null | M2M-preflight REJECTS | n/a | No |
| 4 | CHARACTER, universe=NULL, M2M=∅ (already malformed) | universe=U | Preflight PASSES; universe assigns | still malformed (row was already) | No — Slice 13/14 territory |
| 5 | UNIVERSE, universe=U_old, M2M=∅ | universe=U_new | Preflight PASSES; universe swaps | **Valid Delta shape** (UNIVERSE + non-null universe); effective audience REPLACES from U_old members to U_new members | **AUDIT-ONLY** — no caller evidence justifies stricter guard (§257) |
| 6 | UNIVERSE, universe=U, M2M=∅ | universe=null | Preflight PASSES; universe→NULL | **MALFORMED** (Slice 4 §51 row #5 — UNIVERSE + universe=NULL) | **GUARD #1** |
| 7 | WORKSPACE, universe=NULL, M2M=∅ | universe=U | Preflight PASSES; universe assigns | **MALFORMED** (Slice 4 §51 row #7 — WORKSPACE + universe non-null) | **GUARD #2** |
| 8 | WORKSPACE, universe=NULL, M2M=∅ | universe=null | No-op | Valid | No |
| 9 | NULL (legacy), universe=NULL, M2M=∅ | universe=U | Preflight PASSES; universe assigns; audience_scope stays NULL | Transitional (NULL is not a Delta-invariant target) | No — carve-out preserved |
| 10 | NONE (inactive) | any | Unreachable — `get_queryset` filters `is_active=True` → 404 | n/a | No — queryset gate protects |

## §260. Effective-audience classification

For each transition:

- Case 5 (UNIVERSE swap): audience REPLACEMENT (not narrowing / broadening — different set entirely). Under the invariant, replacement requires positive operator intent. Absent that intent evidence (§257 caller inventory shows zero callers), preserve current behavior but do NOT prove it's safe. Recorded as deferred design question (§274).
- Case 6 (UNIVERSE→null): audience BROADENING (from "Universe U members" to "everyone in workspace" under legacy retrieval predicate) OR audience UNDEFINED (under Delta retrieval, malformed row fails closed). Guard closes both interpretations.
- Case 7 (WORKSPACE→U): audience NARROWING under legacy predicate (broadcast → Universe-only) but audience UNDEFINED under Delta. Guard closes because the row shape is invalid regardless of retrieval semantics.

## §261. Legacy vs Delta retrieval consequence

Retrieval has NOT switched to Delta (Stage 5 deferred). Current legacy predicate at `shell/apps/embeddings/retrieval.py:194-224`:

- Case 6 post-transition (UNIVERSE + universe=null, empty M2M): legacy predicate matches every legacy teammate in workspace (broadcast). Silent audience-broadening from "Universe U members" to "all legacy teammates." **This is a live audience-broadening path Slice 15 closes.**
- Case 7 post-transition (WORKSPACE + universe=U, empty M2M): legacy predicate for a teammate in Universe U matches empty-M2M rows scoped to U. Effective audience NARROWS from "all legacy teammates" to "Universe U members only." Not a broadening in retrieval terms — but the row shape is malformed under Delta and the audience change was silent regardless.

Delta predicate (Slice 4 §53, deferred to Stage 5): both cases fail closed on malformed shape. Guards make the malformed shape unreachable in the first place, so the Stage 5 cutover has zero pre-existing malformed rows to fail closed on.

## §262. Malformed-state inventory (reachable via Universe PATCH pre-Slice-15)

Two Delta-invariant violations reachable via `PATCH {"universe": ...}` before Slice 15:

- **UNIVERSE + universe=NULL** — Slice 4 §52 invariant #2 violation
- **WORKSPACE + universe non-null** — Slice 4 §52 invariant #3 violation

No other invariants reachable through this mutation surface. CHARACTER's M2M-orphan preflight protects invariant #1 for non-empty M2M rows. Empty-M2M CHARACTER rows are already malformed pre-condition; Slice 13/14 close their entry points (detach + PATCH-empty).

## §263. Answers §H — A, B, C, D

**A. UNIVERSE U_old → U_new:** current caller evidence is INSUFFICIENT to treat as explicit audience reassignment (§257 — zero production callers). Preserve current behavior. Do NOT block. Future explicit audience-transition contract design deferred to a separate falsifiable question.

**B. UNIVERSE → NULL:** never valid under Delta. **Guard implemented.** Rejects with structured 4xx. Does NOT auto-transition to WORKSPACE (that would be exactly the absence-means-audience-change anti-pattern Delta was introduced to eliminate).

**C. WORKSPACE → non-null Universe:** never valid under Delta. **Guard implemented.** Rejects with structured 4xx. Does NOT auto-transition to UNIVERSE.

**D. CHARACTER Universe changes:** existing M2M-orphan preflight already handles all reachable cases for non-empty CHARACTER rows. Empty-M2M CHARACTER is a pre-condition malformed shape not caused by Universe PATCH. No new guard.

## §264. Guard implementation (`shell/apps/embeddings/serializers.py`)

Two new checks at top of `update()`, added after the Slice 14 CHARACTER-empty guard, before the existing `pdf_data_uri`/`source_url_input` create-only rejections. Both fire only on active rows (queryset already gates `is_active=True` but the guards check explicitly for defense-in-depth):

**Guard #1 — UNIVERSE-audience row cannot lose its Universe FK:**

```python
if (
    "universe" in validated_data
    and instance.is_active
    and instance.audience_scope == AudienceScope.UNIVERSE
    and validated_data["universe"] is None
):
    raise serializers.ValidationError({
        "code": "universe_audience_row_requires_universe",
        "detail": (
            "This knowledge is shared with everyone in a specific "
            "World. Removing the World would leave it without a "
            "defined audience. Choose a different World, or delete "
            "this knowledge instead."
        ),
    })
```

**Guard #2 — WORKSPACE-audience row cannot gain a Universe FK:**

```python
if (
    "universe" in validated_data
    and instance.is_active
    and instance.audience_scope == AudienceScope.WORKSPACE
    and validated_data["universe"] is not None
):
    raise serializers.ValidationError({
        "code": "workspace_audience_row_forbids_universe",
        "detail": (
            "This knowledge is shared workspace-wide. Assigning it "
            "to a specific World would change who can see it. That "
            "kind of audience change requires a dedicated audience "
            "action, not a scope edit."
        ),
    })
```

Placed at top of `update()` (post-`is_valid()`) so `serializers.ValidationError` renders `.detail` as-is via DRF's global exception handler (bypasses the `as_serializer_error()` list-wrapping). Byte-identical response-shape contract to Slice 13/14 guards. Atomicity: guards run before ANY field mutation on `instance`.

**Error codes:** two distinct new codes (NOT the Slice 13/14 `final_character_detach_requires_audience_decision` code) because they describe distinct invariants. Machine-readable discrimination allows future SPA UX to route to appropriate operator affordances for each case.

Zero SPA / signal / model / migration / retrieval change.

## §265. Test evidence — Test B (Guard #1)

`test_slice15_universe_row_rejects_universe_removal` — PASSES.

- Setup: UNIVERSE row with universe=U, M2M=∅.
- Action: `PATCH {"universe": null}`.
- Result: HTTP 400, `code=universe_audience_row_requires_universe`, `detail` present.
- Post-rejection state: `audience_scope=UNIVERSE`, `universe_id=U.pk`, `is_active=True` — all unchanged.

## §266. Test evidence — Test C (Guard #2)

`test_slice15_workspace_row_rejects_universe_assignment` — PASSES.

- Setup: WORKSPACE row with universe=NULL, M2M=∅.
- Action: `PATCH {"universe": U.pk}`.
- Result: HTTP 400, `code=workspace_audience_row_forbids_universe`.
- Post-rejection state: `audience_scope=WORKSPACE`, `universe_id=None` — unchanged.

## §267. Test evidence — Test A (UNIVERSE swap preserved)

`test_slice15_universe_row_universe_swap_preserved` — PASSES.

- Setup: UNIVERSE row with universe=U_old, M2M=∅.
- Action: `PATCH {"universe": U_new.pk}`.
- Result: HTTP 200 (current behavior preserved).
- Post-transition: `audience_scope=UNIVERSE`, `universe_id=U_new.pk`. Row shape still valid; effective audience replaced.

Deferred question §274 records the audience-transition contract this transition still needs.

## §268. Test evidence — Test D (CHARACTER existing preflight)

`test_slice15_character_universe_swap_still_protected_by_existing_preflight` — PASSES.

- Setup: CHARACTER row + M2M={A in U_old}.
- Action: `PATCH {"universe": U_new.pk}`.
- Result: HTTP 400 via SESSION 261 M2M-orphan preflight (NOT the Slice 15 code). Response body contains `universe` field error.
- Post-rejection: `universe=U_old`, M2M unchanged.

## §269. Test evidence — Tests E, G, H (characterization)

- **Test E** (CHARACTER + empty M2M + universe removal): passes (200). Row was already malformed; Slice 15 does not add coverage. Slice 13/14 handle entry points.
- **Test G** (NULL legacy + universe assignment): passes (200). NULL rows are transitional; Slice 15 does not classify.
- **Test H** (inactive KD PATCH): passes (404). Queryset gate protects; guards need not handle inactive rows.

## §270. Test evidence — Test F (atomicity)

`test_slice15_universe_removal_rejection_does_not_partially_persist_title` — PASSES.

- Setup: UNIVERSE row.
- Action: `PATCH {"title": "changed", "universe": null}`.
- Result: HTTP 400 with Slice 15 Guard #1 code.
- Post-rejection: `title` UNCHANGED. Guards' top-of-`update()` placement gives atomic all-or-nothing rejection.

## §271. Prediction vs actual

| Prediction (§255) | Actual | Status |
|---|---|---|
| A UNIVERSE swap may be legitimate IF callers prove intent | No callers today; preserve current behavior; do NOT block (Test A passes 200) | ✓ (correctly deferred) |
| B UNIVERSE → NULL invalid, should fail closed | Guard #1 implemented; Test B passes | ✓ |
| C WORKSPACE + U creates malformed; must not silently succeed | Guard #2 implemented; Test C passes | ✓ |
| D CHARACTER Universe changes already protected | Test D passes via SESSION 261 preflight | ✓ |
| E scope-specific behavior needed | Confirmed — 4 different scopes, 4 different treatments | ✓ |
| F serializer permits malformed states | Confirmed — 2 reachable pre-Slice-15 (§262); both closed | ✓ |

All 6 predictions supported.

## §272. Real-DB post-Slice-15 verification

Code changed; real DB rows did not change. No PATCH executed against production data during Slice 15.

```
$ manage.py shell -c "..."
total=72  distribution={'universe': 3, 'character': 59, None: 10}
inactive=0  chunks=1149  m2m=62
```

Byte-identical to Slice 7 §103 through Slice 14 §247. **Zero drift across 9 consecutive slices.**

Also verified: zero real-DB rows violate any of the 4 Delta invariants (§256). Guards are purely defensive; nothing to remediate.

## §273. Regression results

```
$ pytest apps/embeddings/tests/test_api.py -v -k "slice15"
8 passed in 5.05s                           # Slice 15 tests

$ pytest apps/embeddings/ apps/spokespeople/ apps/universe/ apps/compositions/ -q
1703 passed, 2 warnings in 133.77s          # broader — +8 from Slice 14's 1695

$ python manage.py makemigrations --check embeddings
No changes detected in app 'embeddings'
```

SPA suite NOT run — zero frontend files touched. Task rule permits skipping.

## §274. Unresolved questions

Carried forward from prior slices (all still open):

- **Deferred from Slice 15 §263.A** — UNIVERSE audience-transition contract. Current behavior preserved (Test A passes 200 on `UNIVERSE U_old → U_new`). No production caller today. If a future SPA gesture emerges (e.g. "move this canon to a different World"), that slice must design a positive-intent audience-transition contract before enabling stricter guarding here.
- **Generic audience PATCH** — CHARACTER↔UNIVERSE, CHARACTER↔WORKSPACE, UNIVERSE↔WORKSPACE transitions all require independent explicit-intent contracts.
- **Provenance direction Alpha vs Beta** (Slice 2 §24.1).
- **Retrieval predicate switch** (Stage 5) — now safer to attempt because zero malformed rows can reach it via KD PATCH.
- **Operator triage UI for the 10 ambiguous rows** (Stage 4).
- **DB CHECK constraints + NOT NULL cutover** (Stage 6).
- **Terminology debt** — Slice 15 adds two more codes to the vocabulary; a future audience-invariant-error-code review may consolidate.
- **Bundle vs split** (still open from Slice 1 §8.4).

**No new Slice-15-specific unresolved questions.**

## §275. Recommendation

**Q-276-29 answered with two narrow implementation guards + one preserved-behavior finding.** Universe reassignment PATCH is now shape-preservation-safe: UNIVERSE and WORKSPACE audience rows cannot enter Delta-malformed states via `universe` field mutation. CHARACTER rows remain protected by SESSION 261's existing M2M-orphan preflight. UNIVERSE↔UNIVERSE swap (audience replacement) awaits a dedicated audience-transition contract.

Combined with Slices 8/9/10/11/12/13/14, the KD mutation surface for M2M and Universe FK edits is now Delta-coherent for the four legitimate audience states + the fail-closed NONE state. What remains:

- **Retrieval cutover (Stage 5)** — no malformed shape can reach a Delta predicate via any current mutation path.
- **Legacy 10-row triage (Stage 4)** — operator decisions for the ambiguous historical rows.
- **DB constraints + NOT NULL cutover (Stage 6)** — enforce invariants at DB level once all mutation surfaces are audit-verified (that milestone is achieved).
- **Provenance** — orthogonal to the audience-invariant arc.

Slice 15 does not authorize any further work.

## §276. Explicit STOP gate

**STOP.** Slice 15 authorizes no further work.

Do NOT begin:

- Generic audience PATCH
- CHARACTER → UNIVERSE / CHARACTER → WORKSPACE
- Automatic UNIVERSE ↔ WORKSPACE conversion
- Retrieval cutover (Stage 5)
- Provenance work
- Legacy 10-row triage (Stage 4)
- DB CHECK constraints (Stage 6)
- NOT NULL cutover
- Recovery UI
- SPA audience picker

## §277. Smallest recommended next question

Now that every mutation surface for CHARACTER / UNIVERSE / WORKSPACE audience shapes fails closed on Delta-invariant violations, the natural next question is a design-first inspection of the **retrieval cutover** — the last big Delta architectural change before DB-level constraint enforcement.

**Q-276-30 (candidate).** *If the retrieval predicate at `shell/apps/embeddings/retrieval.py:194-224` is switched to key positively on `audience_scope` (Slice 4 §53 design) with a compatibility fallback for `audience_scope IS NULL` legacy rows (10 rows in real DB), does every existing retrieval test pass unchanged AND does every audience-classified row (62 of 72) produce the same effective audience under the new predicate as under the current legacy predicate?*

Falsifiable by:
1. Design the new predicate on paper against the Slice 4 §54 equivalence table.
2. Test the predicate against synthesized instances of every row-shape in Slice 4 §51.
3. Run the full 293+ embeddings retrieval test suite after the predicate switch.
4. Verify Slice 4 §54 equivalence holds row-by-row for the 62 deterministic real-DB rows.

This is Stage 5 opener. Larger investigation than Slice 15 because it touches the load-bearing retrieval surface — but every prior slice has been prep for exactly this cutover.

## §278. Slice 15 checklist

- [x] Step 0 — commit + push Slice 14 SHA-record (commit `bb077d3`)
- [x] Slice 15 baseline verified — `main == origin/main == bb077d3`, working tree clean at slice start
- [x] Q-276-29 falsifiable question stated (§254)
- [x] Predictions before evidence (§255)
- [x] Real-DB pre-audit — zero Delta invariant violations (§256)
- [x] Universe-PATCH caller inventory — zero production callers (§257)
- [x] Serializer update() Universe branch source trace (§258)
- [x] Scope × Universe transition matrix — 10 cases (§259)
- [x] Effective-audience classification (§260)
- [x] Legacy vs Delta retrieval consequence comparison (§261)
- [x] Malformed-state inventory — 2 reachable pre-Slice-15 (§262)
- [x] Answers A/B/C/D (§263) — A preserved (no caller evidence), B/C guards implemented, D existing preflight
- [x] Guard #1 (UNIVERSE + null) implemented (§264)
- [x] Guard #2 (WORKSPACE + non-null) implemented (§264)
- [x] Distinct machine-readable error codes for each guard
- [x] Test B — Guard #1 passes (§265)
- [x] Test C — Guard #2 passes (§266)
- [x] Test A — UNIVERSE swap preserved (§267)
- [x] Test D — CHARACTER Universe swap protected by existing preflight (§268)
- [x] Tests E/G/H — characterization (§269)
- [x] Test F — atomic rejection preserves title (§270)
- [x] 8/8 Slice 15 tests pass (§273)
- [x] 1703/1703 broader backend regression (+8 from Slice 14's 1695) (§273)
- [x] `makemigrations --check embeddings` clean (§273)
- [x] SPA suite skipped — zero frontend files touched (§273)
- [x] Real DB unchanged: 72 KDs, `CHARACTER=59, UNIVERSE=3, NULL=10, NONE=0, inactive=0` (§272)
- [x] Prediction vs actual — all 6 predictions supported (§271)
- [x] Unresolved questions (§274) — no new Slice-15-specific
- [x] Recommendation (§275)
- [x] Explicit STOP gate (§276)
- [x] Smallest next question Q-276-30 (§277) — retrieval cutover
- [x] Zero UNIVERSE↔UNIVERSE audience-transition wiring; zero generic audience PATCH; zero automatic UNIVERSE↔WORKSPACE conversion; zero retrieval / provenance / legacy triage / constraint / NOT NULL / recovery UI / SPA changes; zero provider spend
- [x] Commit + push Slice 15 — landed as `20ee0cc`
- [x] Chris + ChatGPT review + Slice 16 scoping decision (§275) — Q-276-30 authorized (retrieval cutover design/equivalence audit; narrow implementation only if gate passes)

---

**End of SESSION 276 Slice 15 / Delta Stage 3C-3. Universe reassignment PATCH now shape-preservation-safe: UNIVERSE audience row cannot lose its Universe FK; WORKSPACE audience row cannot gain one. UNIVERSE↔UNIVERSE swap preserved pending future audience-transition contract. CHARACTER preflight unchanged. Q-276-29 CONFIRMED with two narrow guards + one preserved-behavior finding. 8/8 Slice 15 tests pass; 1703/1703 broader backend regression. Real DB unchanged for 9th consecutive slice; zero Delta invariant violations across all 4 invariants. Every KD mutation surface for M2M + Universe FK now Delta-coherent. STOP for Chris + ChatGPT review of §275 recommendation, §276 gate, and §277 Q-276-30 retrieval-cutover next question.**

**Slice 15 landed commit SHA:** `20ee0cc` (`fix(session-276): Slice 15 / Delta Stage 3C-3 — Universe reassignment shape guards`). Pushed to `origin/main`. Post-push `main == origin/main == 20ee0cc`; working tree clean.

---

# SESSION 276 — Durable audit correction (pre-Slice-16): Riggs KD reclassification

## §279. Operator historical correction — Riggs KD (`90ad200c-5019-4036-82e9-a1ccc5cbce72`)

**Trigger.** Chris supplied first-party historical context that falsifies the Slice 1 §4.4 / §4.5 conclusion that Riggs `90ad200c` is a *PROVEN not-orphan / never-attached KD attributable to the currently live Riggs Teammate*. This section records the correction inline, preserves the underlying source facts as they were originally observed, and updates every downstream count / statement.

### §279.1 Original Slice 1 evidence (preserved verbatim; still true as raw observations)

The following surviving-artifact evidence gathered during Slice 1 remains factually correct and is preserved as-is. It is the *inference* built on top of it that is retracted.

- A live Teammate row `5731a73d` named "Riggs" exists in `chriss-workspace`, with `status=ready`.
- A `CharacterIdentity[Riggs]` row exists with `teammate_id` populated (intact FK link to `5731a73d`) — i.e. no SET_NULL fingerprint.
- The KD `90ad200c` was created `~64s` after the Riggs Teammate was created (Slice 1 §4.2 timeline row, `2026-08-17T15:53:11` Teammate vs `2026-08-17T15:53:36` KD ingest start).
- KD `90ad200c` has an empty `spokespeople` M2M (0 rows).
- KD content is a 33-character stub: *"Just knows a lot about everything"*.
- No Composition or Asset row was produced from this KD.
- `is_active=True`, `deactivated_reason=''`, `audience_scope=NULL`, `universe=NULL` (Slice 5 §78.3 and Slice 7 §104 real-DB dumps).

**These facts remain the primary evidence for this row.** They are not being deleted or rewritten.

### §279.2 What is retracted

The following Slice 1 conclusions are **RETRACTED** as unsupported by the surviving evidence:

- *"PROVEN — NOT an orphan; unattached / never-attached KD"* (§4.4 row 9)
- *"PROVEN not-orphan (Riggs #9): yes — the Riggs Teammate exists"* (§4.5)
- *"1 PROVEN not-orphan (Riggs)"* in the §4.4 distribution and every downstream restatement (§7 table, §55.2, §56 row 9, §170 legacy control comparison)
- The Slice 1 §8 unresolved question #5 assumption that Riggs is a *stub* whose intended audience is the currently live Riggs Teammate

**Reason for retraction.** Identity continuity between the live Teammate `5731a73d` and the KD `90ad200c` was inferred solely from (a) name collision and (b) temporal proximity. Neither is a load-bearing artifact fingerprint under the Slice 1 evidence hierarchy (`PROVEN > STRONG > WEAK > INDETERMINATE`, §4.4). The prior verdict conflated *"a Teammate with this name exists"* with *"this KD was authored for that Teammate."*

### §279.3 Operator historical context supplied by Chris (recorded separately; NOT treated as system provenance)

Chris's first clarification (2026-08-21):

> The currently live Riggs character is not necessarily the character/concept the knowledge document was intended for. He was testing a new prompting/UI idea and selected the first name presented by an auto-select control. Therefore the temporal proximity and shared "Riggs" name do not establish identity continuity between the live Teammate and the KnowledgeDocument.

Chris's second clarification (2026-08-21, same-day follow-up):

> The historical Riggs associated with the old knowledge was a RACCOON character presented in front of a white-screen background. The currently live Riggs Teammate is an ENGLISH BULLDOG wearing a welder's cap. These are definitively different character identities that reused the same display name. Therefore display-name equality between historical/current Teammates must not be treated as identity continuity or provenance evidence.

**Both clarifications are recorded as OPERATOR HISTORICAL CONTEXT — first-party recall from the operator who authored the row.** They are *not* being treated as fabricated system provenance (no CharacterIdentity/Composition/Asset/log/journal fingerprint), and they are *not* being persisted to the DB as an `audience_scope` or M2M mutation. They stand on the same evidentiary tier as the Hearth & Hollow operator-recollection testimony (Slice 1 §4.5 / SESSION 274 §596): **sufficient basis for operator-signoff remediation, insufficient for mechanical classification.**

The second clarification also strengthens the retraction: the KD's intended character (raccoon Riggs) is *definitively distinct* from the currently live Teammate (bulldog Riggs). The "attach to the live Riggs Teammate" default that Slice 1 §4.5 recommended would have attached the KD to the wrong character identity. Under Chris's own operator-recollection tier the historical raccoon Riggs is now a plausible orphan-of-deleted-character candidate — but no SET_NULL fingerprint survives to promote that from operator recall to STRONG/PROVEN.

### §279.4 Corrected Riggs classification

- **Corrected verdict:** `INDETERMINATE — intended audience not mechanically recoverable from surviving repository evidence.`
- **Evidence tier:** WEAK / INDETERMINATE (no SET_NULL fingerprint; no positive identity fingerprint; name+timing coincidence is not a fingerprint under the §4.4 hierarchy).
- **Operator-recall qualifier:** Chris's §279.3 clarification places Riggs in the same tier as the Hearth & Hollow set for remediation purposes — a decision requires his signoff, not a mechanical rule.
- **Delta target options (unchanged from Slice 4 §56 row 9 shape, but for a different reason):** (a) `CHARACTER` if Chris chooses to attach it to some specific teammate, (b) `NONE + is_active=False` if Chris decides it was noise, (c) hard-delete. Removed as an option: the prior "attach to the currently live Riggs Teammate" default is retracted.

### §279.5 Corrected distribution of the 9 legacy KDs

| Tier | Slice 1 count (retracted) | Corrected count |
|---|---|---|
| PROVEN orphan | 1 (TANK) | 1 (TANK) |
| STRONG-INFERENCE orphan | 1 (Tulsi) | 1 (Tulsi) |
| PROVEN not-orphan | 1 (Riggs) | **0** |
| WEAK / INDETERMINATE | 6 (Hearth & Hollow) | **7** (6× Hearth & Hollow + Riggs) |

Total still 9 rows (chriss-workspace legacy set). The +1 admins-workspace `33c07feb` row (Slice 4 §55.2) is unaffected — it was already tier INDETERMINATE.

### §279.6 Downstream sites corrected in-place

Each of the following inline sites has been amended with a `> **CORRECTED — see §279:**` marker preserving the original text as historical record while replacing the retracted verdict:

- §4.4 table row 9 (line ~144)
- §4.4 distribution summary (line ~146)
- §4.5 PROVEN not-orphan bullet (line ~154)
- §7 prediction-vs-evidence table row (line ~346)
- §8 unresolved question #5 (line ~356)
- §55.2 ambiguous-classification bullet for Riggs (line ~1622)
- §56 table row 9 (line ~1645)
- §170 legacy-control comparison list (line ~4161)

### §279.7 Confirmations required by the operator correction

- **DB mutation:** none. The Riggs KD `90ad200c` is NOT touched. `audience_scope` remains `NULL`; `spokespeople` M2M remains empty; `is_active=True` unchanged. Slice 7 real-DB fingerprint (§104) is unchanged.
- **Stage-2 migration impact:** none. Slice 7's deterministic backfill (`shell/apps/embeddings/migrations/0008_session276_stage2_backfill.py`) explicitly leaves rows with `spokespeople=∅ AND universe=NULL` as `audience_scope=NULL` (Slice 7 §92.3 Rule C). Riggs matched Rule C then and still does now. The Riggs reclassification does not change which rules the migration applied.
- **Q-276-30 (Slice 16) impact:** none. The 62-row *classified* population under Q-276-30 excludes all `audience_scope=NULL` rows by definition — Riggs is a NULL row, so it was never in the classified equivalence population. It falls under the *NULL compatibility fallback* branch (10 rows), which by design preserves legacy shape-derived behavior byte-identically. The Slice 16 equivalence proof is unchanged.
- **Slice 4 §55.2 ambiguous-row count (10):** unchanged. Riggs was already in the 10-row ambiguous set (as "PROVEN not-orphan / misconfigured"); it is now in that same set as "INDETERMINATE / operator-signoff required." The row count is stable.

### §279.8 Evidence-hierarchy discipline lesson

This correction reinforces the Slice 1 §4.4 hierarchy with two general rules:

1. **Name collision + timing proximity is not a fingerprint.** Any future classification that leans on those two artifacts alone must be tiered WEAK / INDETERMINATE, not PROVEN.
2. **Display-name equality between historical and currently live Teammates must not be treated as identity continuity or provenance evidence.** Chris's raccoon-Riggs-vs-bulldog-Riggs clarification (§279.3) proves the operator can — and did — reuse a display name across definitively distinct character identities. A shared display string carries no schema-level identity guarantee; nothing in the Teammate/CharacterIdentity model prevents it.

Load-bearing fingerprints remain: SET_NULL on a related row (CharacterIdentity / Composition / Asset), an intact FK from a related row referencing a *specific* Teammate PK (not just a name), or an explicit audit-log entry. None of these exist tying the Riggs KD to any specific historical Teammate. Both the "attach to live Riggs" and "attach to some deleted raccoon Riggs" verdicts are unfingerprinted — the row is INDETERMINATE.

**Audit consequence for other rows in this doc:** the other 8 legacy KDs in Slice 1 §4.4 (TANK #8 via CharacterIdentity SET_NULL, Tulsi #7 via Composition+Asset SET_NULL, Hearth & Hollow #1-6 already tiered WEAK/INDETERMINATE with no name-based identity claim) are unaffected — their classifications never leaned on display-name equality to a currently live Teammate. The lesson is applied only to Riggs; the rest of the §4.4 tiering is not disturbed.

---

**End of Riggs correction. No code change; no DB mutation. Slice 16 (Q-276-30) authorization is unchanged and proceeds after this correction is committed.**

---

# SESSION 276 — Slice 16 / Delta Stage 5A — retrieval cutover to positive `audience_scope` predicate (Q-276-30)

Falsifiable question, real-DB equivalence proof, narrow implementation of the Delta predicate at `shell/apps/embeddings/retrieval.py:retrieve_for_teammate`, and post-cutover regression evidence.

## §280. Slice 16 falsifiable question — Q-276-30

> If the retrieval predicate at `shell/apps/embeddings/retrieval.py:194-224` is switched to key positively on `audience_scope` (Slice 4 §53 design) with a compatibility fallback for `audience_scope IS NULL` legacy rows (10 rows in real DB), does every existing retrieval test pass unchanged AND does every audience-classified row (62 of 72) produce the same effective audience under the new predicate as under the current legacy predicate?

## §281. Predictions before evidence

1. The Delta predicate is byte-identical to the legacy predicate for every CHARACTER row (M2M non-empty by invariant → both predicates reduce to "teammate in M2M").
2. The Delta predicate is byte-identical for every UNIVERSE row (M2M empty by evidence-backed intentional classification → legacy passes on `spokespeople__isnull=True`; Delta passes on `audience_scope=UNIVERSE`).
3. The NULL fallback branch preserves legacy shape-derived behavior verbatim for the 10 unresolved historical rows.
4. NONE and any future unknown `audience_scope` value fail closed under Delta.
5. The provenance carve-out (`resolve_chunk_ids_to_docs`) is untouched by Slice 16 and remains audience-agnostic.
6. Existing embeddings tests (~277 pre-change) pass unchanged post-cutover because the NULL fallback preserves the shape the fixtures create.
7. Real DB is byte-identical before and after cutover (read-only architectural change; no mutations).

## §282. Real-DB pre-Slice-16 baseline

Executed 2026-08-21 at Slice 16 start (post Riggs correction commit `87802bd`; base for Slice 16 code work):

```
total=72   by_scope={None: 10, 'character': 59, 'universe': 3}
inactive=0   chunks=1149   m2m_nonempty=59
```

Matches Slice 15 §272 fingerprint (72 KDs, 59 CHARACTER + 3 UNIVERSE + 10 NULL + 0 NONE + 0 inactive). Distribution stable for 10 consecutive slices.

## §283. Retrieval entry point inventory (Q-276-30 Part A)

Five buckets, per authorization scope. Only Bucket 1 is Slice 16's target.

### §283.1 Bucket 1 — Audience-filtered semantic retrieval (SLICE 16 TARGET)

- **`retrieve_for_teammate`** (`shell/apps/embeddings/retrieval.py:159-226`). THE canonical audience-filtered retrieval. Production callers:
  - `character_os/realtime_document.py:131` — realtime document lookup
  - `character_os/script_synthesis.py:422, 438` — script/video synthesis
  - `character_os/teammate_ask.py:188, 213` — teammate ask
  - `character_os/dialogue_synthesis.py:1490` — per-character dialogue lane
  - `apps/realtime/tools/recall_knowledge.py:92` — realtime tool
  - `apps/embeddings/views.py:391` — knowledge preview endpoint
- **`retrieve_for_thread`** (`retrieval.py:229-279`). Delegates to `retrieve_for_teammate` for its doc-chunk half; predicate inherited transparently. Production callers: `character_os/conversation_synthesis.py:128, 143`.

### §283.2 Bucket 2 — Provenance resolution (PROVENANCE CARVE-OUT — must NOT change)

- **`resolve_chunk_ids_to_docs`** (`retrieval.py:63-118`). Intentionally does NOT filter `is_active` or audience; resolves already-recorded chunk IDs into a doc-level summary. Callers: `apps/compositions/serializers.py:388`, `apps/scripts/serializers.py:166`. Slice 16 leaves this function byte-identical.
- **`list_chunk_ids_for_document`** (`retrieval.py:121-136`). Lists all chunk IDs of a given document; audience is the caller's responsibility. Unchanged.
- **`count_chunks_for_workspace`** (`retrieval.py:139-156`). Workspace-level chunk count; filters `is_active` but NOT audience (aggregate, not per-teammate view). Unchanged.

### §283.3 Bucket 3 — Admin/operator listing (SPA `/api/knowledge/`)

- **`KnowledgeDocumentViewSet.get_queryset`** (`shell/apps/embeddings/views.py:62-108`). LIST endpoint. Optional `?spokesperson=<uuid>` filter (lines 86-90) uses the pre-Delta shape `Q(spokespeople__isnull=True) | Q(spokespeople=<id>)` and mirrors legacy semantics identically to the audience row of the retrieval predicate. **Out of Slice 16 scope** — the SPA list surface is a separate cutover slice (Q-276-30 explicitly scopes to `retrieval.py:194-224`). Flagged here as follow-up.

### §283.4 Bucket 4 — Ingestion dedup (not audience retrieval)

- **`ingestion._persist`** at `apps/embeddings/ingestion.py:124, 302, 330` — per-workspace CREATE/UPDATE dedup lookups; not audience-filtered retrieval. Untouched by Slice 16.

### §283.5 Bucket 5 — Other retrieval lanes (independent contracts)

- **`retrieve_universe_canon`** (`retrieval.py:282-413`) — SESSION 263 shared-tier lane with its own "M2M empty OR M2M covers every cast member" predicate. Distinct semantic contract; independent Delta consideration for a future slice. Untouched.
- **`retrieve_universe_memory`** (`retrieval.py:439-543`) — SESSION 264 lane returning `NarrativeMemory`, not `KnowledgeChunk`. Different model entirely; not in `audience_scope` scope. Untouched.

## §284. Exact legacy predicate (pre-Slice-16)

`retrieval.py:194-224` verbatim (audience portion only; workspace + `is_active=True` + `status="processed"` + universe filters remain byte-identical under Slice 16):

```python
qs = (
    qs.filter(
        Q(document__spokespeople__isnull=True)
        | Q(document__spokespeople=spokesperson)
    )
    .distinct()
    .annotate(distance=CosineDistance("embedding_vector", vector))
    .order_by("distance")
)
```

Legacy semantics: a doc is audience-visible if its M2M is empty (broadcast) OR the retrieving spokesperson is in its M2M.

## §285. Delta predicate design + NULL compatibility contract

Matches Slice 4 §54 equivalence table row-by-row.

```python
qs = (
    qs.filter(
        # NULL compatibility (10 legacy rows) — legacy shape verbatim
        (
            Q(document__audience_scope__isnull=True)
            & (
                Q(document__spokespeople__isnull=True)
                | Q(document__spokespeople=spokesperson)
            )
        )
        # CHARACTER — explicit M2M membership required
        | Q(
            document__audience_scope=AudienceScope.CHARACTER,
            document__spokespeople=spokesperson,
        )
        # UNIVERSE — broadcast within Universe (universe filter above
        # already narrows to matching universe_id)
        | Q(document__audience_scope=AudienceScope.UNIVERSE)
        # WORKSPACE — legacy broadcast within workspace-with-no-Universe.
        # Universe filter above enforces NULL-vs-NULL match.
        | Q(document__audience_scope=AudienceScope.WORKSPACE)
        # NONE / any future unknown value: no Q branch → fail closed
    )
    .distinct()
    .annotate(distance=CosineDistance("embedding_vector", vector))
    .order_by("distance")
)
```

**NULL compatibility contract (load-bearing).**

The NULL fallback branch matches EXACTLY `audience_scope IS NULL` (`__isnull=True`), NOT "anything other than the known values." Consequences:

- **Preserves** legacy shape-derived semantics for the 10 unresolved historical NULL rows byte-identically.
- **Preserves** it for any future row that somehow slips past all Delta write-boundary guards and lands with `audience_scope=NULL` (defense in depth).
- **Fails closed** for any future unknown `audience_scope` value (e.g., an experimental `LEGACY_EXPERIMENTAL` scope introduced without predicate coverage) — the value does not match the NULL branch (`__isnull=True` is False) and does not match any CHARACTER / UNIVERSE / WORKSPACE branch. Invisible to every teammate until a predicate branch is explicitly added.

**NONE also fails closed** by the same construction (no matching Q branch). Combined with the existing `is_active=True` filter this is defense in depth: NONE rows are ALSO inactive by the Stage-3A orphan-archive contract (Slice 8), so retrieval would already reject them. The Delta predicate now rejects them a second time on scope grounds.

## §286. 62-row real-DB equivalence proof

Executed 2026-08-21 against the real DB via a read-only Python script (`/tmp/slice16_equivalence_proof.py`) that enumerated every `(doc, teammate)` pair in the active + processed dataset and compared visibility under both predicates.

**Result:**

```
Total KDs (all): 72
Scope distribution (all): {None: 10, 'character': 59, 'universe': 3}
Scope distribution (is_active=True, status=processed): {None: 10, 'character': 59, 'universe': 3}

Total (doc, teammate) pairs evaluated: 250
  Pairs on CLASSIFIED rows (CHARACTER/UNIVERSE/WORKSPACE): 176
  Pairs on NULL-fallback rows: 74
  Per-scope pair counts: {'CHARACTER': 166, 'UNIVERSE': 10, 'WORKSPACE': 0, 'NULL': 74, 'NONE': 0}

Divergences (legacy != delta): 0
  Per-scope divergence counts: {'CHARACTER': 0, 'UNIVERSE': 0, 'WORKSPACE': 0, 'NULL': 0, 'NONE': 0}

*** EQUIVALENCE PROVEN ***
```

**Interpretation.**

- Q-276-30 asked for equivalence over the 62 *classified* rows. The scan actually evaluates all 72 active rows against all workspace teammates (250 pairs total), extending the guarantee beyond the classified subset.
- **176 pairs on classified rows** span every combination of (CHARACTER doc, teammate in workspace) plus (UNIVERSE doc, universe-matching teammate). All 176 identical.
- **74 pairs on NULL-fallback rows** span the 10 historical NULL rows against their workspace teammates. All 74 identical — the NULL fallback branch preserves legacy shape byte-identically as designed.
- **0 WORKSPACE pairs** because the real DB has 0 WORKSPACE-scoped rows today (Slice 4 §55 finding preserved). The predicate branch is design-covered but has no live rows to test — Slice 16 tests §291.I / §291.J synthesize such rows to exercise the branch.
- **0 NONE pairs** because the real DB has 0 NONE-scoped rows (no orphan-archive has ever fired in production; Slice 4 §55.3 finding preserved).

Re-executed post-implementation with identical output. Real DB is byte-identical before and after the code change.

## §287. Retrieval-test baseline (pre-change)

Executed against `main == 87802bd` prior to code change:

```
apps/embeddings/tests/  →  277 passed
```

Includes the load-bearing `test_retrieval_privacy` (cross-workspace / M2M / cross-thread isolation), `test_retrieval_universe` (9-row truth table), `test_retrieval_universe_canon`, `test_retrieval_universe_memory`, and `test_preview` suites.

## §288. Implementation gate assessment

| # | Condition | Status | Evidence |
|---|---|---|---|
| 1 | 62/62 real-DB equivalence | ✅ PASS | §286 — 176/176 classified pairs identical; 74/74 NULL pairs identical (250/250 total) |
| 2 | NONE / malformed fail closed | ✅ PASS | §285 — no Q branch for NONE; unknown scopes excluded by construction |
| 3 | NULL compatibility preserves legacy for 10 unresolved rows | ✅ PASS | §286 — 74/74 NULL pairs byte-identical |
| 4 | NULL fallback = `audience_scope IS NULL` exactly (not "other-than-known") | ✅ PASS | §285 — branch uses `__isnull=True`; unknown values fail closed |
| 5 | Provenance carve-out (`resolve_chunk_ids_to_docs`) unchanged | ✅ PASS | §283.2; §291.N verifies |
| 6 | Other retrieval lanes (`universe_canon`, `universe_memory`) unchanged | ✅ PASS | §283.5 — untouched by Slice 16 diff (§289) |
| 7 | Existing retrieval test suite passes pre-change | ✅ PASS | §287 — 277 embeddings tests pass on base commit |

All 7 conditions pass. Implementation authorized and executed (§289).

## §289. Exact implementation diff

Two hunks in `shell/apps/embeddings/retrieval.py`:

**Hunk 1** — add `AudienceScope` import (line 47):

```python
# before
from .models import KnowledgeChunk, KnowledgeDocument

# after
from .models import AudienceScope, KnowledgeChunk, KnowledgeDocument
```

**Hunk 2** — replace audience block at lines 216-224 with the Delta predicate. Workspace + `is_active=True` + `status="processed"` + universe filter (lines 194-214) are byte-identical to pre-Slice-16. Only the audience-M2M section changes:

```python
# Removed (legacy)
qs = (
    qs.filter(
        Q(document__spokespeople__isnull=True)
        | Q(document__spokespeople=spokesperson)
    )
    .distinct()
    .annotate(distance=CosineDistance("embedding_vector", vector))
    .order_by("distance")
)

# Added (Delta) — see §285 for full block + load-bearing comment
qs = (
    qs.filter(
        (Q(document__audience_scope__isnull=True)
         & (Q(document__spokespeople__isnull=True)
            | Q(document__spokespeople=spokesperson)))
        | Q(document__audience_scope=AudienceScope.CHARACTER,
            document__spokespeople=spokesperson)
        | Q(document__audience_scope=AudienceScope.UNIVERSE)
        | Q(document__audience_scope=AudienceScope.WORKSPACE)
    )
    .distinct()
    .annotate(distance=CosineDistance("embedding_vector", vector))
    .order_by("distance")
)
```

The block is documented with a 25-line comment restating the four load-bearing properties (NULL fallback exactness; NULL preservation for 10 legacy rows; NONE fail-closed; UNIVERSE / WORKSPACE reliance on the universe filter above).

Plus one hunk in `shell/apps/embeddings/tests/test_retrieval_privacy.py` — add `test_retrieval_delta_slice16.py` to `ALLOWED_FILES` per K0 rule 2 sanction pattern (identical to the sanction for `test_retrieval_universe.py`, `test_retrieval_universe_canon.py`, etc.).

## §290. Slice 16-specific tests (`test_retrieval_delta_slice16.py`)

New file. 14 tests A-N exercising every Delta predicate branch.

- **A / B — NULL fallback preservation.** `NULL + M2M empty → broadcasts`; `NULL + M2M={T} → visible only to T`. Load-bearing that the compatibility branch preserves legacy byte-identically.
- **C / D / E — CHARACTER.** Visible only to M2M members. E is the load-bearing "CHARACTER + M2M={A} must NOT surface to B" check.
- **F / G / H — UNIVERSE.** Visible to same-universe teammates; NOT visible to legacy (no-Universe) teammates or different-Universe teammates (universe filter enforces).
- **I / J — WORKSPACE.** Visible to legacy teammates; NOT visible to universe-scoped teammates (universe filter enforces NULL-vs-NULL).
- **K — NONE fail-closed.** Row with `audience_scope=NONE` + M2M={T} + `is_active=True` (deliberately breaking the archive invariant for the test) still NOT visible. Defense in depth against a hypothetical is_active gate bug.
- **L — Unknown scope fail-closed.** Row with `audience_scope="future_x"` (fits `max_length=20`; not in the enum) + M2M={T} still NOT visible. Load-bearing: the NULL fallback matches EXACTLY `IS NULL`, not "other-than-known." Directly falsifies any future implementation drift that silently broadcasts unknown values.
- **M — Multi-scope union correctness.** A teammate in Universe U sees CHARACTER-with-M2M-membership + UNIVERSE-with-matching-universe; does NOT see UNIVERSE-with-other-universe or WORKSPACE-canon (they have universe=NULL).
- **N — Provenance carve-out unchanged.** `resolve_chunk_ids_to_docs` surfaces a chunk from an A-only CHARACTER doc even when the caller is teammate B who cannot see the doc via `retrieve_for_teammate`. Proves the carve-out remains audience-agnostic.

**Result:** 14/14 pass.

## §291. Regression results

- **`apps/embeddings/tests/` post-cutover:** 291 passed (277 pre-change + 14 new Slice 16 tests). Zero regressions in the pre-existing 277.
- **Full backend regression (`apps/` + `character_os/`):** 2857 passed, 81 failed, 1 skipped. All 81 failures are pre-existing on base commit `87802bd`:
  - 79 in `apps/bootstrap_review/` (unrelated substrate — verified failing on base with Slice 16 changes stashed).
  - 1 in `character_os/clients/tests/test_media_engine_timeouts.py::test_downstream_deadlines_covers_every_client_method` — missing `image_overlay` in `DOWNSTREAM_DEADLINES_S`; pre-existing media-engine client debt unrelated to retrieval.
  - 1 in `apps/embeddings/tests/test_retrieval_privacy.py::test_only_retrieval_module_queries_chunk_tables` — caused by the new `test_retrieval_delta_slice16.py` file querying `KnowledgeChunk.objects.create` in its fixture helper; resolved in-slice by adding the new file to `ALLOWED_FILES` (identical sanction pattern as prior retrieval-truth-table tests). After the fix: 0 Slice 16-caused failures.
- **Net effect of Slice 16 on regression:** zero new failures across the full backend suite.

## §292. Post-cutover real-DB fingerprint

Executed post-implementation:

```
total=72   by_scope={None: 10, 'character': 59, 'universe': 3}
inactive=0   chunks=1149   m2m_nonempty=59
```

Unchanged from §282 pre-baseline. **Real DB byte-identical for the 10th consecutive slice.** No writes; no schema changes; no migration; no admin/operator triage triggered.

Equivalence proof re-executed post-code-change: **0 divergences across 250 pairs** — identical to pre-implementation proof.

## §293. Prediction vs actual

| Prediction (§281) | Evidence |
|---|---|
| 1. CHARACTER byte-identical | ✓ 166/166 CHARACTER pairs identical |
| 2. UNIVERSE byte-identical | ✓ 10/10 UNIVERSE pairs identical |
| 3. NULL fallback preserves legacy | ✓ 74/74 NULL pairs identical |
| 4. NONE + unknown fail closed | ✓ Tests K, L pass |
| 5. Provenance carve-out untouched | ✓ Test N + no diff to `resolve_chunk_ids_to_docs` |
| 6. Existing tests pass unchanged | ✓ 277/277 pre-existing embeddings tests pass |
| 7. Real DB byte-identical | ✓ Fingerprint unchanged (§292) |

7/7 predictions supported.

## §294. Files changed (Slice 16)

- `shell/apps/embeddings/retrieval.py` — 2 hunks (imports + audience block). Net: −5 lines, +40 lines including the 25-line load-bearing comment.
- `shell/apps/embeddings/tests/test_retrieval_privacy.py` — 1 hunk (7 lines added to `ALLOWED_FILES`).
- `shell/apps/embeddings/tests/test_retrieval_delta_slice16.py` — new file (~320 lines; 14 tests).
- `docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md` — this Slice 16 appendix (§280-§302).

**No touched:** models.py, migrations, serializers.py, ingestion.py, views.py (LIST filter), signals.py, admin.py, any SPA file, any other retrieval helper, any composition/dialogue/talking-head/preview production caller (they consume `retrieve_for_teammate` transparently).

## §295. Unresolved questions

1. **SPA list `?spokesperson=` filter (Bucket 3 in §283.3).** `KnowledgeDocumentViewSet.get_queryset` at `views.py:86-90` still uses the pre-Delta shape `Q(spokespeople__isnull=True) | Q(spokespeople=<id>)`. Under the current DB it produces identical results (same equivalence proof applies) but it is not YET keyed on `audience_scope`. A future slice (Q-276-31 candidate) could cut it over for shape uniformity; this is *not* invariant-required because the SPA list is authenticated + workspace-scoped and Chris's own workspace.
2. **`retrieve_universe_canon` shared-tier predicate.** SESSION 263 lane uses a distinct "M2M empty OR M2M covers cast" predicate. Under Delta it could be reformulated positively (audience_scope=UNIVERSE for the empty case; audience_scope=CHARACTER + full-cast M2M for the "covers all" case). Not blocking — the current implementation is Delta-invariant-safe (universe filter + shape); reformulation is aesthetic / future stage 5B.
3. **Stage 6 removal of the NULL fallback.** Once the 10 unresolved rows are triaged by the operator, the NULL branch can be removed and the CHARACTER / UNIVERSE / WORKSPACE branches tightened. That is a separate Delta Stage 6 slice — not authorized by Q-276-30. Slice 16 leaves the fallback in place indefinitely.
4. **Bucket 3 flag decision.** Does Chris want the SPA list cutover bundled with the next slice, or held for a later dedicated cutover?

## §296. Recommendation

**Slice 16 is complete and safe to land.** All 7 gate conditions passed with evidence. Real DB byte-identical. Legacy retrieval semantics preserved for every existing row. Positive predicate now enforces `audience_scope`-keyed visibility; NONE and future unknown values fail closed; provenance carve-out unchanged.

The retrieval surface is now Delta-coherent. Combined with:
- Slice 8 (orphan-archive stamps `NONE`),
- Slice 9 (revival lands directly at `CHARACTER`),
- Slice 10 (fresh CREATE → CHARACTER),
- Slice 11 (fresh CREATE UNIVERSE inference),
- Slice 12 (explicit WORKSPACE marker),
- Slice 13 (final-detach fails closed),
- Slice 14 (PATCH empty M2M fails closed),
- Slice 15 (Universe reassignment shape guards),

the load-bearing invariants of Direction Delta are enforced end-to-end at every mutation surface AND at the retrieval predicate. The remaining Delta work is:
- Stage 5B — companion cutovers (SPA list filter; universe_canon reformulation) — cosmetic.
- Stage 6 — remove the NULL fallback + add a DB-level `NOT NULL CHECK` + `audience_scope` column constraint — requires operator triage of the 10 unresolved rows first.
- Stage 7 — Legacy row triage — the operator-facing "here are the 10 undecided rows, choose CHARACTER / WORKSPACE / NONE for each" UI.

## §297. Explicit STOP gate

STOP before Stage 5B or Stage 6. Review Slice 16 evidence with Chris + ChatGPT.

- Does Chris want to bundle the SPA list `?spokesperson=` filter cutover with the next slice?
- Does the universe_canon reformulation (§295.2) belong in Delta Stage 5B or is it deferred until after Stage 7 (legacy triage) when the 10 NULL rows are gone?
- Is there any real-world workflow (talking-head render, dialogue synthesis, teammate ask, realtime doc lookup, or preview) Chris wants to smoke-test on the running dogfood workspace before we consider Slice 16 sealed?

## §298. Smallest recommended next question

Two candidates depending on Chris's answer to §297:

**Q-276-31 (candidate — Stage 5B).** *If the SPA list `KnowledgeDocumentViewSet.get_queryset` `?spokesperson=` filter is switched to the same positive `audience_scope`-keyed predicate as `retrieve_for_teammate`, does the SPA workspace-knowledge list still return exactly the same doc IDs for every real teammate in Chris's workspace, and do the 291 embeddings + 656 SPA tests pass unchanged?*

**Q-276-32 (candidate — Stage 7 opener).** *If Chris triages the 10 unresolved NULL rows to their operator-chosen audience_scope (per §279.5 corrected distribution: 1 TANK → NONE; 1 Tulsi → NONE; 1 Riggs → operator decision; 6 Hearth & Hollow → operator decision; 1 admins `33c07feb` → operator decision), does a rehearsal `NOT NULL` constraint on `audience_scope` succeed on the resulting DB shape without violating any invariant?*

Chris's product-order preference decides which lands first.

## §299. Slice 16 checklist

- [x] Step 0 — commit + push Riggs correction (commit `87802bd`)
- [x] Slice 16 baseline verified — `main == origin/main == 87802bd`, working tree clean at slice start
- [x] Q-276-30 falsifiable question stated (§280)
- [x] Predictions before evidence (§281)
- [x] Real-DB pre-Slice-16 baseline (§282)
- [x] Retrieval entry point inventory — 5 buckets (§283)
- [x] Exact legacy predicate (§284)
- [x] Delta predicate design + NULL compatibility contract (§285)
- [x] 62-row real-DB equivalence proof — 250/250 pairs identical (§286)
- [x] Retrieval-test baseline pre-change — 277/277 passing (§287)
- [x] Implementation gate assessment — 7/7 conditions pass (§288)
- [x] Delta predicate implemented at `retrieval.py:194-224` audience block (§289)
- [x] `test_retrieval_delta_slice16.py` A-N — 14/14 tests pass (§290)
- [x] Post-cutover regression: 291/291 embeddings tests pass (§291)
- [x] Full backend regression: 81 pre-existing failures (79 bootstrap_review + 1 media_engine + 1 test_retrieval_privacy allow-list); allow-list fixed in-slice; 0 new failures caused by Slice 16 (§291)
- [x] Post-change real-DB fingerprint unchanged (§292); real-DB equivalence re-run post-code — 0 divergences
- [x] Prediction vs actual — 7/7 predictions supported (§293)
- [x] Files changed (§294)
- [x] Unresolved questions (§295)
- [x] Recommendation (§296)
- [x] Explicit STOP gate (§297)
- [x] Smallest next questions Q-276-31 / Q-276-32 (§298)
- [x] Zero SPA changes; zero migration; zero model / serializer / view / ingestion / signals mutation; zero provider spend
- [x] Commit + push Slice 16 — landed as `791a7df`
- [ ] Chris + ChatGPT review + next slice scoping decision

---

**End of SESSION 276 Slice 16 / Delta Stage 5A. Retrieval predicate now Delta-coherent: positive `audience_scope`-keyed visibility for every classified row; NULL-branch preservation for the 10 unresolved historical rows byte-identical to legacy; NONE and future unknown values fail closed; provenance carve-out untouched. 14/14 Slice 16 tests + 277 pre-existing embeddings tests + 250/250 real-DB equivalence pairs. Real DB unchanged for 10th consecutive slice. Every KD mutation surface AND the retrieval surface are now Delta-invariant enforced end-to-end. STOP for Chris + ChatGPT review of §296 recommendation, §297 gate, §298 next-question candidates.**

**Slice 15 landed commit SHA:** `20ee0cc` (`fix(session-276): Slice 15 / Delta Stage 3C-3 — Universe reassignment shape guards`). SHA-record follow-up: `75047d9`.

**Riggs correction landed commit SHA (pre-Slice-16, §279 addendum):** `87802bd` (`docs(session-276): correct Riggs KD classification — INDETERMINATE (§279)`). Pushed to `origin/main` before Slice 16 code work began; served as `main` baseline for Slice 16.

**Slice 16 landed commit SHA:** `791a7df` (`feat(session-276): Slice 16 / Delta Stage 5A — retrieval cutover to positive audience_scope predicate`). Pushed to `origin/main`. Post-push `main == origin/main == 791a7df`; working tree clean.

**Riggs correction still holds under Slice 16.** Per §279.3 / §279.7: the historical raccoon Riggs (the character the KD `90ad200c` was intended for) and the currently live English-bulldog / welder's-cap Riggs Teammate (`5731a73d`) are definitively distinct character identities. Display-name equality does not establish identity continuity. Riggs remains INDETERMINATE; the Slice 16 cutover leaves the row unchanged and it continues to fall under the NULL compatibility fallback branch (74/74 NULL pairs byte-identical, §286).

---

# SESSION 276 — Slice 17 / Delta Stage 5B — SPA-list `?spokesperson=` cutover to positive `audience_scope` predicate (Q-276-31)

Companion cutover to Slice 16. Applies the same positive-audience predicate shape to the SPA workspace-knowledge LIST endpoint's `?spokesperson=` filter, plus records the operator's newly-supplied legacy-cleanup decision.

## §300. Slice 17 falsifiable question — Q-276-31

> If the SPA-list `KnowledgeDocumentViewSet.get_queryset` `?spokesperson=` filter is switched to the same positive `audience_scope`-keyed semantics as `retrieve_for_teammate`, does the workspace Knowledge list return exactly the same document IDs for every real teammate in the current DB, while preserving the deliberate NULL compatibility behavior and passing the relevant backend + SPA regressions?

## §301. Predictions before evidence

1. Per-teammate LIST result sets are byte-identical between the legacy shape predicate and the Delta predicate for every real teammate in the current DB (16 teammates across all workspaces).
2. CHARACTER, UNIVERSE, and NULL rows all produce byte-identical LIST results. WORKSPACE rows: 0 in real DB — the branch is design-covered but has no live rows to test (Slice 17 tests §311.F synthesize such a row).
3. NONE + any future unknown `audience_scope` value fail closed at the LIST layer, mirroring Slice 16's retrieval predicate.
4. Universe scoping via the `?universe=` query param remains explicit (LIST does NOT auto-derive Universe from the requesting spokesperson; that is `retrieval.py`'s contract). Composing `?spokesperson=T&?universe=U` intersects the two filters.
5. Real DB is byte-identical before and after cutover (read-only architectural change; no mutations).
6. All 303 embeddings tests (291 pre-Slice-17 + 12 new Slice 17) pass; all 656 SPA tests pass (no SPA code changes).

## §302. Slice 17 baseline SHA

- Base commit at Slice 17 start: `31aacd1` (`docs(session-276): record Slice 16 landed SHA 791a7df in audit doc + check off §299 commit-and-push item`).
- `main == origin/main == 31aacd1`; working tree clean prior to Slice 17 code work.
- Slice 16 code landed at `791a7df` — Slice 17 builds on top.

## §303. Real-DB pre-Slice-17 baseline

Executed at Slice 17 start (base `31aacd1`):

```
total=72   by_scope={None: 10, 'character': 59, 'universe': 3}
inactive=0   chunks=1149   m2m_nonempty=59
teammates_across_all_workspaces=16
```

Matches Slice 16 §282/§292 fingerprint exactly. 11 consecutive read-only slices.

## §304. LIST filter path — exact legacy predicate (pre-Slice-17)

`shell/apps/embeddings/views.py:82-90` verbatim (audience portion only; the surrounding `workspace__memberships__user` auth wall + `is_active=True` filter + optional `?workspace=` / `?document_type=` / `?universe=` params remain byte-identical under Slice 17):

```python
# SESSION 138 / K5 — optional spokesperson visibility
# filter. Returns docs visible to this spokesperson:
# either no M2M attachments (visible to all) OR the
# spokesperson is one of the attached.
spokesperson_id = self.request.query_params.get("spokesperson")
if spokesperson_id:
    qs = qs.filter(
        Q(spokespeople__isnull=True) | Q(spokespeople=spokesperson_id)
    ).distinct()
```

Legacy semantics: a doc is `?spokesperson=T`-visible if its M2M is empty (broadcast) OR the requesting spokesperson is in its M2M — SHAPE-DERIVED, identical in structure to the pre-Slice-16 `retrieval.py` audience predicate.

## §305. Comparison to Slice 16 retrieval Delta predicate

The audience-M2M portion of `retrieve_for_teammate` and the LIST `?spokesperson=` filter had *identical* pre-Slice-16 shape. Slice 16 replaced the retrieval version; Slice 17 replaces the LIST version with the parallel Delta shape.

Differences the LIST predicate must preserve (i.e., NOT copy verbatim from retrieval):

- LIST does NOT filter `status="processed"` (retrieval does). Documents in `pending` / `failed` states are still visible in the operator-facing list. Slice 17 preserves this.
- LIST does NOT auto-derive Universe scoping from `spokesperson.universe_id` (retrieval does). The `?universe=` query param is explicit operator input via the SPA. Slice 17 preserves this.
- LIST returns `KnowledgeDocument` rows (not `KnowledgeChunk` rows), so the Q lookups use field names directly (`audience_scope`, `spokespeople`) — no `document__` prefix.

## §306. Delta LIST predicate design + NULL compatibility contract

```python
qs = qs.filter(
    # NULL compatibility (10 legacy rows) — legacy shape verbatim
    (
        Q(audience_scope__isnull=True)
        & (
            Q(spokespeople__isnull=True)
            | Q(spokespeople=spokesperson_id)
        )
    )
    # CHARACTER — explicit M2M membership required
    | Q(
        audience_scope=AudienceScope.CHARACTER,
        spokespeople=spokesperson_id,
    )
    # UNIVERSE — visible; ?universe= param below narrows explicitly
    | Q(audience_scope=AudienceScope.UNIVERSE)
    # WORKSPACE — visible
    | Q(audience_scope=AudienceScope.WORKSPACE)
    # NONE / any future unknown value: no Q branch → fail closed
).distinct()
```

**NULL compatibility contract (load-bearing, mirrors Slice 16 §285).**

The NULL fallback branch matches EXACTLY `audience_scope IS NULL` (via `__isnull=True`), NOT "anything other than the known values." Consequences:

- **Preserves** legacy shape-derived semantics for the 10 unresolved historical NULL rows byte-identically.
- **Fails closed** for any future unknown `audience_scope` value (branch does not match; no CHARACTER/UNIVERSE/WORKSPACE branch either).
- **NONE fails closed** by the same construction. Defense in depth on top of `is_active=True` (NONE rows are also `is_active=False` per Slice 8 orphan-archive contract, so the LIST already excludes them via the base queryset).

Unknown-scope values must NOT silently receive legacy broadcast semantics at either the retrieval OR the LIST layer. This is the load-bearing sibling constraint between Slices 16 and 17.

## §307. Universe scoping — why LIST does not auto-derive

The retrieval predicate at `retrieval.py:211-214` derives Universe scoping from `spokesperson.universe_id`:

```python
if spokesperson.universe_id is None:
    qs = qs.filter(document__universe__isnull=True)
else:
    qs = qs.filter(document__universe_id=spokesperson.universe_id)
```

The LIST endpoint at `views.py:101-106` uses an **explicit** `?universe=` query param passed by the operator via the SPA:

```python
universe_param = self.request.query_params.get("universe")
if universe_param:
    if universe_param.strip().lower() == "none":
        qs = qs.filter(universe__isnull=True)
    else:
        qs = qs.filter(universe_id=universe_param)
```

**Why the asymmetry is correct:** retrieval feeds RAG synthesis at render time — the spokesperson's Universe context is the correct implicit scope. The LIST feeds an operator-facing management surface — the operator picks Universe scope explicitly via UI controls. Copying retrieval's implicit universe derivation into the LIST would silently hide docs the operator expects to see when managing an out-of-Universe teammate. Slice 17 preserves this asymmetry.

## §308. Real-DB LIST equivalence proof

Executed via read-only script `/tmp/slice17_list_equivalence_proof.py` — enumerated every real Teammate (16 across all workspaces) and compared the doc-ID set returned by the legacy predicate vs the proposed Delta predicate, scoped per-workspace (auth wall is orthogonal to the predicate itself).

**Result:**

```
KDs total (all): 72
KDs scope distribution: {None: 10, 'character': 59, 'universe': 3}
KDs inactive: 0
Teammates evaluated: 16

Teammate-level divergences (legacy set != delta set): 0
  Doc-scope buckets in legacy-only diffs: {'CHARACTER': 0, 'UNIVERSE': 0, 'WORKSPACE': 0, 'NULL': 0, 'NONE': 0}
  Doc-scope buckets in delta-only diffs: {'CHARACTER': 0, 'UNIVERSE': 0, 'WORKSPACE': 0, 'NULL': 0, 'NONE': 0}

*** LIST-FILTER EQUIVALENCE PROVEN ***
```

**Per-scope accounting:**

- **CHARACTER (59 rows):** legacy predicate returns those where M2M non-empty AND (M2M empty OR sp in M2M) → reduces to "sp in M2M". Delta CHARACTER branch: `audience_scope=CHARACTER AND sp in M2M`. Identical by construction (CHARACTER-classified rows are M2M-non-empty by Delta invariant).
- **UNIVERSE (3 rows, all M2M empty per Slice 4 §55.1 Rule B):** legacy returns them (M2M empty passes the OR). Delta UNIVERSE branch returns them unconditionally. Identical.
- **WORKSPACE (0 rows in DB):** predicate branch design-covered; no live evidence. Slice 17 tests §311.F synthesize a WORKSPACE row and assert visibility.
- **NULL (10 rows):** legacy predicate applies verbatim. Delta NULL fallback applies the identical predicate under a `__isnull=True` guard. Identical.
- **NONE (0 rows in DB):** predicate design fails closed. Slice 17 tests §311.G synthesize a NONE row (with `is_active=True` forced to isolate the audience branch) and assert invisibility.

Re-executed post-code-change: still 0 divergences.

## §309. Implementation gate assessment

| # | Condition | Status | Evidence |
|---|---|---|---|
| 1 | Real-DB LIST equivalence | ✅ PASS | §308 — 16/16 teammates, 0 divergences on every scope class |
| 2 | NONE + unknown scope fail closed | ✅ PASS | §306 — no matching Q branch; §311.G / §311.H exercise |
| 3 | NULL compatibility preserves legacy exactly | ✅ PASS | §308 — NULL rows byte-identical; §306 uses `__isnull=True` |
| 4 | NULL fallback matches EXACTLY `audience_scope IS NULL` | ✅ PASS by construction (§306); §311.H falsifies drift |
| 5 | Universe `?universe=` param unchanged | ✅ PASS | §307 — LIST retains explicit Universe scoping |
| 6 | Auth wall (`workspace__memberships__user`) unchanged | ✅ PASS | §310 diff scoped to lines 86-90 only |
| 7 | Other query-param filters (workspace, doc_type) unchanged | ✅ PASS | §310 |
| 8 | `retrieval.py` untouched (Slice 16 sealed) | ✅ PASS | zero diff in `apps/embeddings/retrieval.py` |

All 8 conditions pass. Implementation authorized and executed (§310).

## §310. Exact implementation diff

**Single hunk** in `shell/apps/embeddings/views.py:82-90`. `AudienceScope` was already imported (line 39, pre-existing from Slice 5/6). Workspace + `is_active` + optional workspace/doc_type/universe filters are byte-identical.

```python
# Removed (legacy)
spokesperson_id = self.request.query_params.get("spokesperson")
if spokesperson_id:
    qs = qs.filter(
        Q(spokespeople__isnull=True) | Q(spokespeople=spokesperson_id)
    ).distinct()

# Added (Delta) — see §306 for full block + load-bearing comment
spokesperson_id = self.request.query_params.get("spokesperson")
if spokesperson_id:
    qs = qs.filter(
        (
            Q(audience_scope__isnull=True)
            & (
                Q(spokespeople__isnull=True)
                | Q(spokespeople=spokesperson_id)
            )
        )
        | Q(
            audience_scope=AudienceScope.CHARACTER,
            spokespeople=spokesperson_id,
        )
        | Q(audience_scope=AudienceScope.UNIVERSE)
        | Q(audience_scope=AudienceScope.WORKSPACE)
    ).distinct()
```

Documented with a 25-line comment restating the load-bearing NULL contract, NONE/unknown fail-closed property, and the intentional Universe-scoping asymmetry with retrieval.

## §311. Slice 17-specific tests (`test_api_list_delta_slice17.py`)

New file. 12 tests A-L exercising every LIST Delta branch through the DRF API (not just the queryset — the auth wall + serializer + pagination are covered end-to-end).

- **A / B — NULL fallback preserved.** Empty-M2M broadcast + explicit M2M narrow.
- **C / D — CHARACTER.** M2M membership required; non-members excluded.
- **E — UNIVERSE broadcast at LIST layer.** Visible via LIST even when the requesting sp is legacy (no-Universe) — LIST does NOT auto-scope by sp.universe (§307). Load-bearing asymmetry with retrieval preserved.
- **F — WORKSPACE audience.** Visible via LIST.
- **G — NONE fail-closed.** Row forced to `is_active=True` + M2M={T} + `audience_scope=NONE` is still NOT visible. Proves the audience predicate itself excludes NONE, not just the `is_active` gate.
- **H — Unknown scope fail-closed.** Row with `audience_scope="future_x"` + M2M={T} still NOT visible. Falsifies future drift toward "match anything other than known."
- **I — `?spokesperson=T&?universe=U` intersection.** Both filters applied; only Universe-U docs surface when U is passed.
- **J — `is_active=False` invisible regardless of scope.** Baseline preserved.
- **K — Cross-workspace auth wall.** User A queries `?spokesperson=<sp in B>` — auth scoping produces empty set.
- **L — No `?spokesperson=` param.** Filter branch does not fire; full workspace list returned unchanged (baseline preserved).

**Result:** 12/12 pass.

## §312. Test results

- **`apps/embeddings/tests/` post-cutover:** 303 passed (291 pre-Slice-17 + 12 new Slice 17). Zero regressions in the 291 pre-existing tests.
- **SPA test suite (`web/`, `npm test`):** 656 passed / 49 files. Unchanged from Slice 15/16 baseline. No SPA code was modified in Slice 17; the change was scoped to backend `views.py`.
- **Real-DB LIST equivalence re-run post-code-change:** 0 divergences (identical to pre-implementation proof).

Broader backend regression (`apps/` + `character_os/`) not re-executed in Slice 17 — the 81 pre-existing failures documented in Slice 16 §291 (79 `apps/bootstrap_review/` + 1 `character_os/clients/tests/test_media_engine_timeouts.py::test_downstream_deadlines_covers_every_client_method` + 1 previously-fixed allow-list issue) are unrelated to `views.py` and remain out of Slice 17 scope.

## §313. Post-cutover real-DB fingerprint

Executed post-implementation:

```
total=72   by_scope={None: 10, 'character': 59, 'universe': 3}
inactive=0   chunks=1149   m2m_nonempty=59
```

Unchanged from §303 pre-baseline. **Real DB byte-identical for the 11th consecutive slice.** No writes; no schema changes; no migration; no admin/operator triage triggered.

## §314. Prediction vs actual

| Prediction (§301) | Evidence |
|---|---|
| 1. Per-teammate LIST equivalence | ✓ 16/16 teammates, 0 divergences (§308) |
| 2. CHARACTER / UNIVERSE / NULL byte-identical; WORKSPACE branch design-covered | ✓ per-scope breakdown (§308) |
| 3. NONE + unknown fail closed at LIST layer | ✓ tests G, H pass (§311) |
| 4. Universe `?universe=` unchanged; composition intersects | ✓ test I passes (§311) |
| 5. Real DB byte-identical | ✓ fingerprint unchanged (§313) |
| 6. 303 embeddings + 656 SPA tests pass | ✓ §312 |

6/6 predictions supported.

## §315. Files changed (Slice 17)

- `shell/apps/embeddings/views.py` — 1 hunk (audience-M2M portion of `?spokesperson=` filter replaced). Net: −4 lines, +45 lines including the 25-line load-bearing comment.
- `shell/apps/embeddings/tests/test_api_list_delta_slice17.py` — new file (~275 lines; 12 tests).
- `docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md` — this Slice 17 appendix (§300-§321) + §316 operator legacy-cleanup decision.

**Not touched:** `retrieval.py` (Slice 16 sealed); `models.py`, migrations, `serializers.py`, `ingestion.py`, `signals.py`, `admin.py`, any SPA file, any other view or endpoint, `test_retrieval_privacy.py` allow-list (LIST doesn't touch KnowledgeChunk).

## §316. Operator historical-knowledge decision (RECORDED DURABLY)

**Trigger.** Chris supplied a first-party product decision during Slice 17 authorization: the historical/dogfood knowledge represented by the following legacy KDs is no longer relevant to the current Character OS work and may ultimately be deleted:

- **TANK** (`8c6f0c14`) — PROVEN historical orphan (CharacterIdentity SET_NULL fingerprint; §4.4)
- **Tulsi** (`7ecde40b`) — STRONG-INFERENCE historical orphan (Composition + Asset SET_NULL fingerprint; §4.4)
- **Historical raccoon Riggs** (`90ad200c`) — INDETERMINATE per Riggs correction §279; distinct from the currently live English-bulldog / welder's-cap Riggs Teammate (`5731a73d`)
- **Hearth & Hollow Books** (6 KDs: `aa90d895`, `e37ea174`, `b58efd31`, `7f41d8e3`, `c408656d`, `0088f31f`) — WEAK-INFERENCE / operator-recollection tier per §4.4

**Scope of the decision:** the 9 chriss-workspace legacy KDs above (TANK + Tulsi + Riggs + 6× Hearth & Hollow). The +1 admins-workspace NULL row (`33c07feb "Wikipedia is trafilatura's home turf"`, §55.2) is **explicitly NOT covered** by this decision. Its status is deferred until the future legacy-cleanup slice inspects/identifies it independently — the operator has NOT asserted that the same decision applies to it.

**Slice 17 does NOT act on this decision.** No row is deleted or mutated. `audience_scope` is not assigned. The 9 rows remain `audience_scope=NULL, is_active=True` and continue to fall under the NULL compatibility fallback branch introduced in Slices 16 + 17. Their retrieval + LIST semantics are byte-identical to pre-Delta.

**Consequence for the Stage 7 (legacy triage) question.** Prior planning (§298 candidate Q-276-32) assumed operator needed to reconstruct an intended audience for each of the 9 unresolved rows in order to preserve them under a `NOT NULL` constraint. Chris's decision materially simplifies Stage 7:

- The 9 chriss-workspace legacy rows do NOT need audience reconstruction — the operator may choose `NONE + is_active=False` (soft delete) for any or all of them, or hard-delete them, at operator lifecycle timing of Chris's choosing.
- The +1 admins-workspace NULL row remains an audience-reconstruction candidate pending future inspection.
- The Stage 7 question narrows from "operator-classify 10 rows" to "operator lifecycle-decides 9 rows (retain-as-is-decision-deferred OR archive OR delete) + inspect and classify 1 row."
- A future `NOT NULL` constraint on `audience_scope` remains blocked until either (a) all 10 rows are given an explicit scope OR (b) the constraint is deferred until after operator lifecycle actions remove them from the active set.

This decision is recorded as OPERATOR HISTORICAL / LIFECYCLE CONTEXT — first-party product intent from Chris. It stands on the same tier as the Riggs raccoon-vs-bulldog clarification (§279.3): sufficient basis for operator-signoff lifecycle action, insufficient for mechanical inference.

## §317. Unresolved questions

1. **Stage 7 legacy cleanup slice.** When does Chris want to act on §316? A single "archive/delete these 9 legacy rows" slice becomes feasible once he's ready. Not authorized by Q-276-31; blocks the future `NOT NULL` audience_scope constraint.
2. **Admins-workspace `33c07feb` (Slice 4 §55.2).** Belongs to a different operator (admin@mail.com); intended-audience inference remains open. Chris's §316 decision explicitly does NOT cover it.
3. **`retrieve_universe_canon` shared-tier predicate reformulation.** Slice 16 §295.2 flagged this as aesthetic / future stage 5B'; Slice 17 did NOT tackle it (scope was strictly `views.py:86-90`). Still open.
4. **SPA-side smoke test.** Chris may want to poke the Knowledge tab in the running dogfood workspace to confirm the operator-visible list looks identical (Q-276-31 asserts byte-equivalent doc IDs, but operator UX confirmation is a separate signal).

## §318. Recommendation

**Slice 17 is complete and safe to land.** All 8 gate conditions passed with evidence. Real DB byte-identical. Legacy LIST semantics preserved for every existing row across all 16 real teammates. Positive predicate now enforces `audience_scope`-keyed visibility at both retrieval (Slice 16) AND the SPA-facing management list (Slice 17). NONE and future unknown values fail closed at both surfaces.

Combined with the Slices 8-16 chain, the load-bearing invariants of Direction Delta are enforced end-to-end:

- **Every mutation surface** (Slices 8, 9, 10, 11, 12, 13, 14, 15) rejects Delta-invariant violations at the write boundary.
- **Both audience-filtered read surfaces** (Slice 16 retrieval + Slice 17 LIST) key positively on `audience_scope`.
- **NULL compatibility branch** is uniform across both surfaces; preserved verbatim for the 10 unresolved historical rows.
- **NONE + unknown values fail closed** uniformly.

The Direction Delta architecture is now shape-complete at every surface Chris authorized. Remaining Delta work:

- **Stage 7 — Legacy cleanup / triage** — operator lifecycle action on the 9 chriss-workspace rows per §316 + inspection of the +1 admins row.
- **Stage 8 — DB constraint** — `NOT NULL CHECK` on `audience_scope` once §316 lifecycle actions complete.
- **Stage 9 (optional) — universe_canon reformulation** — §317.3 aesthetic cleanup; not invariant-required.

## §319. Explicit STOP gate

STOP before Stage 7 (legacy cleanup) or Stage 8 (constraint). Review Slice 17 evidence with Chris + ChatGPT.

- Does Chris want the next slice to be Stage 7 (legacy cleanup) or Stage 9 (`universe_canon` reformulation) or a different priority?
- If Stage 7 next: does Chris want to lifecycle-decide all 9 rows in one slice, or split them into archive-first / delete-later?
- If Stage 7 next: what to do about the +1 admins-workspace row? (Inspection-first slice, or bundled into Chris's lifecycle-decision slice with a "defer classification" outcome?)
- Any real-world SPA smoke test Chris wants to run before considering Slice 17 sealed?

## §320. Smallest recommended next question

Two candidates depending on Chris's answer to §319:

**Q-276-33 (candidate — Stage 7 opener).** *If Chris archives (or hard-deletes) the 9 chriss-workspace legacy rows identified in §316 (TANK, Tulsi, historical raccoon Riggs, 6× Hearth & Hollow), does the real-DB fingerprint transition to `total=63, by_scope={None: 1, character: 59, universe: 3}, inactive=9` (assuming archive path) without any Delta invariant violation, and do all 303 embeddings + 656 SPA + retrieval equivalence tests pass unchanged? Separately, what inspection is needed for admins-workspace `33c07feb` before its audience_scope can be assigned?*

**Q-276-34 (candidate — Stage 9 aesthetic).** *If `retrieve_universe_canon` (SESSION 263 shared-tier lane) is reformulated positively as `(audience_scope=UNIVERSE) OR (audience_scope=CHARACTER AND M2M covers full cast)`, does its 12-test suite pass unchanged, and does the reformulated predicate produce byte-identical shared-tier results for the 3 UNIVERSE canon rows in the real DB?*

Chris's product-order preference decides which lands first. §316 makes Q-276-33 significantly easier than the pre-Slice-17 formulation (Q-276-32) because operator lifecycle-decides instead of audience-reconstructs.

## §321. Slice 17 checklist

- [x] Step 0 — Slice 16 landed as `791a7df`; catch-up SHA-record commit `31aacd1`
- [x] Slice 17 baseline verified — `main == origin/main == 31aacd1`, working tree clean at slice start (§302)
- [x] Q-276-31 falsifiable question stated (§300)
- [x] Predictions before evidence (§301)
- [x] Real-DB pre-Slice-17 baseline (§303)
- [x] Legacy LIST predicate identified verbatim (§304)
- [x] Comparison to Slice 16 retrieval Delta predicate (§305)
- [x] Delta LIST predicate design + NULL contract (§306)
- [x] Universe scoping asymmetry documented + preserved (§307)
- [x] Real-DB equivalence proof — 16/16 teammates, 0 divergences on every scope class (§308)
- [x] Per-scope accounting for CHARACTER, UNIVERSE, WORKSPACE, NULL, NONE, unknown (§306, §308, §311)
- [x] Implementation gate assessment — 8/8 conditions pass (§309)
- [x] Delta LIST predicate implemented at `views.py:86-90` (§310)
- [x] `test_api_list_delta_slice17.py` A-L — 12/12 tests pass (§311)
- [x] 303/303 embeddings tests pass post-cutover (§312)
- [x] 656/656 SPA tests pass (unchanged; no SPA code touched) (§312)
- [x] Post-change real-DB fingerprint unchanged (§313)
- [x] Real-DB equivalence re-run post-code — 0 divergences (§312)
- [x] Prediction vs actual — 6/6 predictions supported (§314)
- [x] Files changed (§315)
- [x] Operator historical-knowledge decision recorded (§316) — 9 chriss-workspace legacy rows may be lifecycle-deleted; admins-workspace row deferred
- [x] Unresolved questions (§317)
- [x] Recommendation (§318)
- [x] Explicit STOP gate (§319)
- [x] Smallest next questions Q-276-33 / Q-276-34 (§320)
- [x] Zero SPA changes; zero migration; zero retrieval.py modification; zero model / serializer / ingestion / signals mutation; zero legacy row mutation; zero NOT NULL constraint; zero provider spend
- [x] Commit + push Slice 17 — landed as `6e7bd6c`
- [ ] Chris + ChatGPT review + next slice scoping decision

---

**End of SESSION 276 Slice 17 / Delta Stage 5B. SPA-list `?spokesperson=` filter now Delta-coherent: positive `audience_scope`-keyed visibility mirroring Slice 16 retrieval; NULL fallback preserves legacy shape byte-identically for the 10 unresolved historical rows; NONE and future unknown values fail closed at both retrieval + LIST layers; Universe scoping asymmetry preserved (LIST is explicit via `?universe=`; retrieval auto-derives from spokesperson). 12/12 Slice 17 tests + 303/303 embeddings + 656/656 SPA + 16/16 real-DB LIST equivalence teammates. Real DB unchanged for 11th consecutive slice. Every mutation surface AND both audience-filtered read surfaces are now Delta-invariant enforced end-to-end. Operator legacy-cleanup decision for 9 chriss-workspace historical rows recorded durably (§316). STOP for Chris + ChatGPT review of §318 recommendation, §319 gate, §320 next-question candidates.**

**Slice 17 landed commit SHA:** `6e7bd6c` (`feat(session-276): Slice 17 / Delta Stage 5B — SPA-list ?spokesperson= cutover to positive audience_scope predicate`). Pushed to `origin/main`. Post-push `main == origin/main == 6e7bd6c`; working tree clean.

---

# SESSION 276 — Slice 18 / Delta Stage 7 opener — legacy-KD lifecycle archive audit (Q-276-33)

Audit-only slice. Part B triggered the authorization's STOP condition — the existing operator-delete lifecycle path does NOT produce the intended Delta-safe archive shape for the 9 §316 rows. No DB mutation performed. Forensic inspection of the 10th NULL row + NULL-debt analysis + full regression proceeded READ-ONLY.

## §322. Slice 18 falsifiable question — Q-276-33 (refined)

**Primary.** If the 9 chriss-workspace historical KDs explicitly lifecycle-decided by Chris in §316 are archived through the existing safe operator lifecycle semantics, does Character OS remove them from active retrieval/LIST without broadening audience, preserve their chunks/provenance, and leave exactly one historical `audience_scope=NULL` row requiring a decision?

**Secondary.** What exactly is the remaining admins-workspace NULL KD `33c07feb` ("Wikipedia is trafilatura's home turf"), and is there enough evidence to recommend WORKSPACE, NONE/archive, or another explicit state?

## §323. Slice 18 baseline SHA

- Base commit at Slice 18 start: `e2087cd` (`docs(session-276): record Slice 17 landed SHA 6e7bd6c in audit doc`).
- `main == origin/main == e2087cd`; working tree clean prior to Slice 18.
- Slice 17 code landed at `6e7bd6c`; Slice 18 was NEVER expected to modify code (Q-276-33 is a lifecycle-action + audit slice) but Part B's STOP finding means Slice 18 lands as documentation-only.

## §324. Predictions before evidence

1. All 9 §316 rows will be present in the DB with `audience_scope=NULL, is_active=True, deactivated_reason=''` and empty M2M.
2. The 10th NULL row will match `33c07feb` "Wikipedia is trafilatura's home turf" in admins workspace.
3. The existing `destroy()` operator-delete path will EITHER (a) stamp `audience_scope=NONE` on soft-archive (Delta-safe target) OR (b) preserve the pre-existing `audience_scope` value including NULL (revival-preserving semantics).
4. If (3a), the archive proceeds and leaves exactly 1 NULL row (`33c07feb`) + 9 NONE rows.
5. If (3b), the archive would leave the 9 rows as `is_active=False, audience_scope=NULL, deactivated_reason=OPERATOR_DELETE` — NOT Delta-safe for eventual `NOT NULL` constraint. **STOP condition.**
6. TANK + Tulsi have surviving composition provenance (per Slice 1 §4.2 SET_NULL fingerprints); their chunks must remain resolvable via `resolve_chunk_ids_to_docs` after any archive.
7. `33c07feb` is authored by admin@mail.com; product recommendation cannot be made from title alone.
8. Fresh CREATE path can still land at `audience_scope=NULL` when a non-SPA caller omits spokespeople + universe + workspace_shared_intent marker.

## §325. Part A — pre-mutation inventory of all NULL rows

Read-only DB enumeration executed via `/tmp/slice18_partA_inventory.py`.

**Full DB fingerprint (pre-mutation):**

```
total=72   by_scope={None: 10, 'character': 59, 'universe': 3}
inactive=0   chunks=1149   m2m_nonempty=59
```

Matches Slices 15-17 fingerprint verbatim (12th consecutive slice with unchanged real DB).

**The 10 `audience_scope=NULL` rows enumerated:**

| # | Short UUID | Full UUID | Title | Workspace | Chunks | Composition refs | is_active | audience_scope | deactivated_reason | M2M |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `8c6f0c14` | `8c6f0c14-b2c9-4161-b6b7-a17d3f9b4545` | TANK — AUTOMOTIVE FINANCING CONTENT KNOWLEDGE | chriss-workspace | 22 | 12 | True | NULL | '' | 0 |
| 2 | `7ecde40b` | `7ecde40b-6d72-45eb-b676-6feb260e2ff8` | Tulsi — Core Identity and Public Purpose | chriss-workspace | 3 | 8 | True | NULL | '' | 0 |
| 3 | `90ad200c` | `90ad200c-5019-4036-82e9-a1ccc5cbce72` | Riggs (historical raccoon) | chriss-workspace | 1 | 0 | True | NULL | '' | 0 |
| 4 | `aa90d895` | Hearth & Hollow #1 | About Hearth & Hollow Books | chriss-workspace | 1 | 0 | True | NULL | '' | 0 |
| 5 | `e37ea174` | Hearth & Hollow #2 | How We Recommend Books | chriss-workspace | 1 | 0 | True | NULL | '' | 0 |
| 6 | `b58efd31` | Hearth & Hollow #3 | Children's Reading | chriss-workspace | 1 | 0 | True | NULL | '' | 0 |
| 7 | `7f41d8e3` | Hearth & Hollow #4 | Bookstore Events | chriss-workspace | 1 | 0 | True | NULL | '' | 0 |
| 8 | `c408656d` | Hearth & Hollow #5 | Supporting Local Authors | chriss-workspace | 1 | 0 | True | NULL | '' | 0 |
| 9 | `0088f31f` | Hearth & Hollow #6 | Helping Customers Find Their Next Read | chriss-workspace | 1 | 0 | True | NULL | '' | 0 |
| 10 | `33c07feb` | `33c07feb-65ee-4ed3-8fc0-0f2fc33600c7` | Wikipedia is trafilatura's home turf | admins-workspace | 22 | 0 | True | NULL | '' | 0 |

**§316-authorization match:** all 9 short UUIDs specified by Chris are present with the described names. Zero deviation. The 10th NULL row is exactly `33c07feb` per Chris's explicit exclusion. All 9 rows: `chris@donkeybetz.com` author, `is_active=True`, `audience_scope=NULL`, `deactivated_reason=''`, empty M2M, no Universe. Ready-for-archive shape per §316.

**Preservation-critical:** TANK's 22 chunks with 12 composition provenance refs and Tulsi's 3 chunks with 8 composition refs must survive any archive path. The 7 remaining §316 rows have 0 composition refs each and are simpler.

## §326. Part B — archive-path audit + STOP FINDING

**The existing operator-delete lifecycle path is `KnowledgeDocumentViewSet.destroy()` at `shell/apps/embeddings/views.py:147-166`** (invoked by the SPA's delete button via `DELETE /api/knowledge/<id>/`). Exact behavior:

```python
def destroy(self, request, *args, **kwargs):
    instance = self.get_object()
    instance.is_active = False
    instance.deactivated_reason = DeactivationReason.OPERATOR_DELETE
    instance.save(
        update_fields=["is_active", "deactivated_reason", "updated_at"],
    )
    return Response(status=drf_status.HTTP_204_NO_CONTENT)
```

**What it does:**
- Flips `is_active=True → False`
- Sets `deactivated_reason=OPERATOR_DELETE`
- Preserves `audience_scope` unchanged (whatever it was pre-archive)
- Preserves M2M unchanged
- Preserves chunks + embeddings + composition provenance (chunk rows are not touched)

**What it does NOT do:**
- **Does NOT stamp `audience_scope=NONE`.**

**Contrast — Slice 8 orphan-archive signal at `shell/apps/spokespeople/signals.py:211-216`** (fires on Teammate `post_delete` when a KD's M2M becomes empty via cascade):

```python
KnowledgeDocument.objects.filter(pk__in=orphan_ids).update(
    is_active=False,
    deactivated_reason=DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE,
    audience_scope=AudienceScope.NONE,    # ← STAMPS NONE
    updated_at=timezone.now(),
)
```

The orphan-archive path DOES stamp NONE atomically alongside `is_active=False`. The operator-delete `destroy()` path does NOT. This asymmetry was introduced deliberately in Slice 8 for the orphan case (§114) — a truly orphaned row has no surviving audience by construction. The operator-delete case was left unchanged for **revival-preservation semantics**: an operator might un-archive a CHARACTER-scoped doc and expect its audience to survive intact.

**Consequence for the 9 §316 rows (currently `audience_scope=NULL`):**

Running the current `destroy()` path against each of the 9 rows would produce:

- **Before:** `is_active=True, audience_scope=NULL, deactivated_reason=''`
- **After:** `is_active=False, audience_scope=NULL, deactivated_reason=OPERATOR_DELETE`

**Retrieval + LIST safety:** ✅ preserved. Both Slice 16 (`retrieval.py`) and Slice 17 (`views.py` LIST) apply `is_active=True` as a base filter, so the archived rows would be invisible to both retrieval and LIST regardless of `audience_scope`. Under the Delta predicate a NULL row also passes through the NULL-compatibility fallback branch, which further requires `spokespeople__isnull=True OR sp in M2M` — the archived-and-empty-M2M shape naturally continues to satisfy the NULL branch's broadcast case. But no active retrieval would ever reach it because of `is_active=True`.

**Delta-shape completeness:** ❌ NOT met. The archived rows would remain in the `audience_scope=NULL` bucket. The current DB has 10 NULL rows; after archiving 9 the count would still be 10 NULL (9 inactive + 1 active). The intended Delta target for archived knowledge — `audience_scope=NONE` — is not reached.

**Stage 8 (`NOT NULL` constraint) impact:** ❌ BLOCKED. If Stage 8 adds a `NOT NULL` constraint on `audience_scope`, it must first eliminate all NULL rows. Archiving via the current `destroy()` path does NOT eliminate NULL — it merely inactivates the rows. Stage 8 would still require an explicit scope assignment (either NONE via a code change, or a per-row operator/admin decision).

**Per the Slice 18 authorization:** *"If the current archive path does NOT produce the intended Delta-safe state, STOP and report the mismatch before mutating real rows. Do not invent a one-off data patch merely to make the count work."*

**STOP CONDITION MET.** Slice 18 does NOT archive any row. Slice 18 lands as documentation-only.

## §327. Part C — corrected post-archive fingerprint (predicted, hypothetical)

For record and future-slice planning: the correct predicted post-state depends on whether Delta target is reached.

**Scenario A — if a code change lands that makes `destroy()` stamp `NONE` when `audience_scope` is currently NULL:**

- total KDs = 72 (soft archive, no hard delete)
- CHARACTER = 59
- UNIVERSE = 3
- WORKSPACE = 0
- NONE = 9  (the 9 §316 rows post-archive)
- NULL = 1  (only `33c07feb` remaining)
- inactive = 9
- chunks preserved (1149)
- m2m_nonempty = 59

**Scenario B — if `destroy()` is used unchanged (current behavior):**

- total KDs = 72
- CHARACTER = 59
- UNIVERSE = 3
- WORKSPACE = 0
- NONE = 0
- NULL = 10  (all 10 rows remain NULL; 9 now inactive)
- inactive = 9
- chunks preserved (1149)
- m2m_nonempty = 59

The prior Q-276-33 wording predicted `total=63, inactive=9`. That combination is arithmetically inconsistent with soft archive (total should remain 72). It corresponds to hard-delete of 9 rows, which is explicitly forbidden by the Slice 18 authorization ("Do NOT hard-delete them in this slice"). **The correct soft-archive prediction is Scenario A above.**

## §328. Part D / E — SKIPPED (per §326 STOP)

No archive was performed. The 9 §316 rows remain unmutated:
- `is_active=True`
- `audience_scope=NULL`
- `deactivated_reason=''`
- All chunks + embeddings + composition provenance intact
- All M2M relationships unchanged (empty for all 9, as before)
- All Universe FKs unchanged (NULL for all 9, as before)

## §329. Part F — forensic inspection of `33c07feb`

READ ONLY. Executed via `/tmp/slice18_partF_inspect_33c07feb.py`. Full evidence separated into observation / source-derived / inference / recommendation tiers per authorization.

### §329.1 OBSERVED FACT (direct DB read)

- UUID: `33c07feb-65ee-4ed3-8fc0-0f2fc33600c7`
- Title: `"Wikipedia is trafilatura's home turf"`
- Workspace: **Admin's workspace** (`f4f2aa20-e2e2-4ae2-85a0-abacd8bea231`)
- Created by: **admin@mail.com** (workspace superuser, not chris@donkeybetz.com)
- Created at: `2026-05-14T20:35:29.095303+00:00` — pre-Universe (SESSION 261 Universe primitive shipped later)
- Updated at: `2026-05-14T20:35:42.849266+00:00` (~14 seconds after create; single-shot ingest, no manual re-edit)
- Document type: `url` (not `text` or `markdown` — recorded as a URL ingestion)
- Ingested via: `paste`
- Status: `processed`
- is_active: True; audience_scope: NULL; deactivated_reason: `''`
- Universe: NULL; spokespeople M2M count: 0
- Chunk count: 22
- content_hash: `52a6c67f721554f7a491958836866369cdee094fab156a857770513148c46a95`
- raw_content length: 16,656 chars; processed_content length: ~similar

### §329.2 SOURCE-DERIVED FACT (content sniff + composition query)

- First 500 chars of processed_content start with: *"Retrieval-augmented generation\nRetrieval-augmented generation (RAG) is a technique that enables large language models (LLMs) to retrieve and incorporate new information from external data sources.[1] With RAG, LLMs first refer to a specified set of documents, then respond to user queries..."* — this is verbatim from the Wikipedia article on Retrieval-augmented generation.
- Tail of processed_content ends with a bibliography entry citing Kelcey, Chang, Dai, Uszkoreit, Le, Petrov "Natural Questions: a Benchmark for Question Answering Research" — matches Wikipedia RAG article's references section.
- Composition provenance refs (chunks → compositions): **0**. This document was NEVER used to render any teammate composition.
- Same-workspace peer KDs: 45 rows, all `audience_scope=CHARACTER`, all attached to admins-workspace teammates (24/7 Global AI, Contract Concierge, MentorForge, context-kit, etc.). The `33c07feb` row is the ONLY NULL / non-CHARACTER doc in admins-workspace.
- Same-workspace teammates: 2 — Riggs (`cf3b2322`) and Rigby (`d3d0fb14`), both no-Universe. **Note:** the admins-workspace Riggs is a separate Teammate row from chriss-workspace's Riggs (`5731a73d`). Cross-workspace name reuse; not identity continuity.

### §329.3 INFERENCE (evidence-tiered)

- **Author + workspace:** created by admin@mail.com in admins-workspace → likely an operational / engineering test note, not a customer-facing character doc.
- **Empty M2M + no Universe:** never bound to a specific character or Universe. Was ingested unattached.
- **Content = Wikipedia RAG article:** the underlying content is a Wikipedia article about retrieval-augmented generation. The title (*"Wikipedia is trafilatura's home turf"*) is admin's editorial commentary — trafilatura is the HTML-extraction library Character OS uses for URL ingestion; Wikipedia's HTML is famously well-structured; the title reads as an evaluative annotation ("here is an example where trafilatura works exceptionally well").
- **Zero composition provenance:** never rendered into any teammate's output. Pure ingestion-pipeline artifact.
- **Substantive content (~16.6KB, 22 chunks):** not a stub, not a smoke-test placeholder. A real Wikipedia article was extracted end-to-end.

Combined: this row appears to be a **deliberate engineering exemplar** — admin@mail.com ingested a Wikipedia URL to validate that the trafilatura-based ingestion pipeline correctly extracts long-form structured content, then annotated it with an editorial title recording the finding. The document was never intended to feed any teammate; it was a pipeline validation artifact.

### §329.4 PRODUCT RECOMMENDATION

Slice 18 does NOT mutate this row. The lifecycle decision belongs to admin@mail.com.

Two evidence-supported options for the eventual triage slice:

- **Option A — `WORKSPACE`:** if admin considers the row a retained internal engineering reference (example of clean trafilatura extraction) that should remain workspace-visible for future ingestion / extraction work. This would be a positive audience assignment and matches the "retained tech note" tier of the Slice 4 §55.2 ambiguous-classification analysis.
- **Option B — `NONE + is_active=False` (soft archive via same lifecycle path as §316 rows):** if admin considers it obsolete pipeline validation debris that no longer needs to remain visible. Content is easily re-derivable (Wikipedia URL is durable), so there is no information-preservation cost to archiving.

Slice 18 flags this row as **INDETERMINATE pending admin@mail.com's explicit signoff**, on the same evidentiary tier as the Hearth & Hollow / Riggs §316 recall — sufficient basis for operator-signoff lifecycle action, insufficient for mechanical inference.

## §330. Part G — NULL debt analysis

### §330.1 Current NULL count

Post-Slice-18 (no mutation): **10 NULL rows** (the same 10 identified in §325 — nothing changed).

If the Slice 18 archive had proceeded per Scenario A of §327, the NULL count would drop to 1 (only `33c07feb`). Under Scenario B (current path unchanged) it would remain 10. Slice 18 landed as documentation-only, so the count remains 10.

### §330.2 What blocks removing NULL branches at each surface

Both surfaces currently carry a NULL compatibility branch: `retrieval.py:216-269` (Slice 16 §285) and `views.py:106-146` (Slice 17 §306).

| Surface | Would break if NULL branch removed | Why |
|---|---|---|
| Slice 16 retrieval `retrieve_for_teammate` | Yes | 10 real NULL rows would silently become invisible to every teammate. TANK + Tulsi + Hearth & Hollow (all currently retrievable via broadcast) would drop from RAG. `33c07feb` would also drop from admin RAG. |
| Slice 17 LIST `?spokesperson=` filter | Yes | Same 10 rows would drop from SPA workspace-knowledge lists — operator would be unable to see them for triage. |
| Fresh-write path (`ingestion._persist`) | No — the branch is not a "removal" but a "produces NULL" path. See §330.3. |
| Schema (`audience_scope` nullability) | Yes | Currently `null=True` on the model. `NOT NULL` migration would fail while any NULL rows exist. |

### §330.3 Can fresh writes still produce NULL?

**Yes.** The fresh CREATE path at `shell/apps/embeddings/ingestion.py:298-301` explicitly lands at `audience_scope=None` for the `(no spokespeople + no universe + no workspace_shared_intent marker)` case:

```python
elif workspace_shared_intent:
    # No spokespeople, no Universe, explicit workspace marker present
    create_audience_scope = AudienceScope.WORKSPACE
else:
    # Transitional NULL for the ``(no sp + no universe + no marker)`` case
    # — non-SPA callers land here.
    create_audience_scope = None
```

**SPA callers (Slice 12 workflow):** all four SPA CREATE call sites at `web/src/routes/workspace/knowledge.tsx` were wired to pass one of `{spokespeople[], universe, audience_scope: "workspace"}` via the mandatory `UniverseScopePicker`. SPA-originated writes cannot land at NULL.

**Non-SPA callers:** management commands (e.g., `smoke_ingest`), fixture-driven tests, the DRF `POST /api/knowledge/` API called without the workspace_shared_intent marker, and any other programmatic caller CAN still produce `audience_scope=NULL`. This is the "transitional NULL" behavior explicitly preserved by Slice 11's Option 3 decision (§169-§175).

### §330.4 What removing the NULL branches would require

1. **Historical NULL rows resolved** — all 10 rows given an explicit `audience_scope` (via archive to NONE, or explicit CHARACTER/UNIVERSE/WORKSPACE assignment).
2. **Fresh-write path made NULL-impossible** — either:
   - default to a fail-closed value (e.g., NONE) when no positive signal is given, OR
   - require an explicit `audience_scope` param on all CREATE calls and reject those without one, OR
   - restrict CREATE to SPA-shaped payloads that always include a marker.
3. **`NOT NULL` migration on the field** with a `CHECK` constraint enforcing the Delta invariants (Slice 4 §51).
4. **Retrieval + LIST NULL branches removed** from `retrieval.py:216-269` and `views.py:106-146` as clean-up.
5. **Test surface updated** — tests that intentionally create NULL rows (Slice 16 §290 tests A/B; Slice 17 §311 tests A/B) would need to change fixtures to CHARACTER/UNIVERSE/WORKSPACE.

Per the Slice 18 authorization: *"Do NOT implement the fix in this slice unless it is already mechanically impossible and you are only documenting that fact."* Fresh writes are still mechanically able to produce NULL; the fix is not implemented in Slice 18.

## §331. Part H — regression results

- **`apps/embeddings/tests/`** + **`apps/spokespeople/tests/test_delete_orphan_archive.py`** + **`apps/compositions/tests/test_f6_citations.py`** + **`apps/spokespeople/tests/test_delete.py`**: **332 passed** / 4 warnings / 35.58s. Zero regressions (Slice 17 baseline was 303 embeddings + 29 spokespeople-related = 332).
- **`python manage.py makemigrations --check --dry-run embeddings`**: `"No changes detected in app 'embeddings'"` — clean.
- **SPA suite (`web/`, `npm test`)**: **656 passed** / 49 files / 5.97s. Unchanged from Slice 17.

Broader backend regression (bootstrap_review + media_engine) not re-executed — Slice 18 modifies zero code and cannot affect those subsystems.

## §332. Post-Slice-18 real-DB fingerprint

Re-executed post-Part-H:

```
total=72   by_scope={None: 10, 'character': 59, 'universe': 3}
inactive=0   chunks=1149   m2m_nonempty=59
```

Identical to §325 pre-Slice-18 baseline. **Real DB byte-identical for the 12th consecutive slice.** No writes; no mutations of any kind.

## §333. Prediction vs actual

| Prediction (§324) | Evidence |
|---|---|
| 1. All 9 §316 rows present in expected shape | ✓ §325 — all 9 short-UUID matched; all 9 have `is_active=True, audience_scope=NULL, deactivated_reason='', empty M2M, no Universe` |
| 2. 10th NULL = `33c07feb` "Wikipedia is trafilatura's home turf" | ✓ §325 / §329.1 |
| 3. `destroy()` either stamps NONE OR preserves audience_scope | ✓ §326 — path (3b) confirmed: preserves audience_scope unchanged, does NOT stamp NONE |
| 4/5. Archive succeeds → 1 NULL + 9 NONE / STOP if path preserves NULL | STOP triggered (§326); Slice 18 lands doc-only |
| 6. TANK + Tulsi have composition provenance to preserve | ✓ §325 — TANK 12 refs, Tulsi 8 refs. Would need preservation on any future archive |
| 7. `33c07feb` recommendation cannot be made from title alone | ✓ §329.2-4 — content sniff + peer analysis + composition query needed for evidence-tiered recommendation |
| 8. Fresh CREATE can still produce NULL | ✓ §330.3 — ingestion.py:298-301 explicitly lands NULL for `(no sp + no universe + no marker)` case |

8/8 predictions supported. Prediction (3) resolved to path (b); Prediction (5) STOP triggered as the invariant-safe outcome.

## §334. Files changed (Slice 18)

- `docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md` — this Slice 18 appendix (§322-§339).
- **Not touched:** no `.py` files, no test files, no SPA files, no migrations. Zero code delta. Zero DB delta.

## §335. Unresolved questions

1. **Slice 19 archive-path extension.** The current `destroy()` path preserves `audience_scope` for revival-preservation semantics. Should Slice 19 (a) add a NONE-stamping mode to `destroy()` when the pre-archive scope is NULL (or when the operator explicitly signals "final archive, no revival intent"), (b) add a new endpoint / action `POST /api/knowledge/<id>/archive-final/` that stamps NONE atomically, or (c) leave `destroy()` unchanged and require a targeted, one-time signed data migration for the 9 §316 rows? The user's authorization forbids "one-off data patch merely to make the count work" — favoring option (a) or (b) as reusable primitives.
2. **`33c07feb` triage.** Requires admin@mail.com signoff on WORKSPACE vs NONE (§329.4). Not solvable from evidence alone.
3. **Fresh-write NULL closure.** Making the fresh-write path NULL-impossible (§330.4 step 2) is a separate ingestion + serializer + SPA slice. Blocks Stage 8 (`NOT NULL` constraint).
4. **Chunk / composition preservation contract.** Slice 18 established that the Slice 8 orphan-archive path already preserves chunks + embeddings + provenance (chunk table is not touched; only KD lifecycle fields flip). Any future NONE-stamping extension of `destroy()` must preserve the same guarantee. Documented here so Slice 19 spec is unambiguous.
5. **NULL-branch removal timing.** After the 10 NULL rows are resolved AND the fresh-write path is closed, the NULL compatibility branches in retrieval + LIST can be removed. Sequencing: Slice 19 (archive-path extension + `33c07feb` triage) → Slice 20 (fresh-write NULL closure) → Slice 21 (branch removal + `NOT NULL` + schema constraint).

## §336. Recommendation

**Slice 18 is complete as an audit-only slice.** The STOP condition triggered by Part B correctly caught the archive-path mismatch BEFORE any DB mutation, exactly as the Slice 18 authorization requested.

Key durable outputs:

1. **§325 pre-mutation inventory** — the 9 §316 rows are now durably specified by full UUID + shape + preservation-critical facts (chunks, composition refs). Any future archive slice can act on this inventory without re-discovery.
2. **§326 STOP finding** — the current `destroy()` path leaves `audience_scope` unchanged. Slice 19 must either extend `destroy()` or add a companion `archive-final` primitive to close the NULL-to-NONE transition.
3. **§329 `33c07feb` forensic profile** — evidence-tiered recommendation (Option A: WORKSPACE, Option B: NONE + archive) with admin signoff required.
4. **§330 NULL-debt inventory** — 10 rows now; fresh-writes can still produce NULL; complete stage-plan for eventual Stage 8 `NOT NULL` constraint.

**Recommended next action.** Slice 19 as an implementation slice (small): extend the operator-delete lifecycle to atomically stamp `audience_scope=NONE` on soft-archive when the pre-archive scope is NULL (or when the operator explicitly signals "final archive"). Then Slice 20 re-runs §325's inventory against the extended path and actually archives the 9 rows.

## §337. Explicit STOP gate

STOP before Slice 19 (archive-path extension). Review Slice 18 evidence with Chris + ChatGPT.

- Does Chris prefer Slice 19 option (a) — extend `destroy()` with NONE-stamping mode, (b) add new `archive-final` endpoint, or (c) something else?
- Is Chris ready to loop in admin@mail.com for `33c07feb` triage (Slice 19 could bundle both), or should `33c07feb` be deferred further?
- Does Chris want to close the fresh-write NULL loophole in the same slice as the archive-path extension, or as a separate follow-up?

## §338. Smallest recommended next question — Q-276-35

**Q-276-35 (candidate — Slice 19 opener).** *If a NONE-stamping mode is added to the operator-delete lifecycle path (either as an extension of `destroy()` when pre-archive `audience_scope=NULL`, or as a new companion `archive-final` action), does the resulting path atomically stamp `is_active=False + deactivated_reason=OPERATOR_DELETE + audience_scope=NONE` on the 9 §316 rows, preserve all chunks + embeddings + composition provenance, and reduce the DB NULL count to exactly 1 (`33c07feb`) without any Delta invariant violation and with all 332 embeddings-related + 656 SPA tests passing unchanged?*

## §339. Slice 18 checklist

- [x] Slice 17 landed as `6e7bd6c`; catch-up SHA-record `e2087cd`
- [x] Slice 18 baseline verified — `main == origin/main == e2087cd`, working tree clean (§323)
- [x] Q-276-33 falsifiable question stated (§322) — primary + secondary
- [x] Predictions before evidence (§324)
- [x] Part A — pre-mutation inventory of all 10 NULL rows (§325)
- [x] All 9 §316-authorized rows confirmed present with matching UUIDs
- [x] 10th NULL row confirmed as `33c07feb` per §316 exclusion
- [x] Full pre-mutation shape captured (chunks, comp refs, is_active, audience_scope, deactivated_reason, M2M, Universe)
- [x] Part B — archive-path audit revealed `destroy()` does NOT stamp NONE (§326)
- [x] Part C — corrected soft-archive fingerprint prediction (§327); Scenario A (with fix) vs Scenario B (current path); prior `total=63` prediction was hard-delete-shape confusion, corrected to soft-archive `total=72`
- [x] Part D/E — SKIPPED per §326 STOP; no DB mutation
- [x] Part F — `33c07feb` forensic inspection (§329) with evidence-tiered recommendation (Option A: WORKSPACE, Option B: NONE + archive)
- [x] Part G — NULL debt analysis (§330); 10 rows now; fresh-writes can still produce NULL via `ingestion.py:298-301`
- [x] Part H — regression: 332 backend + 656 SPA + `makemigrations --check` clean (§331)
- [x] Real-DB fingerprint unchanged (§332); 12th consecutive read-only slice
- [x] Prediction vs actual — 8/8 predictions supported (§333)
- [x] Files changed — doc only (§334)
- [x] Unresolved questions (§335)
- [x] Recommendation (§336)
- [x] Explicit STOP gate (§337)
- [x] Smallest next question Q-276-35 (§338)
- [x] Zero DB mutation; zero code change; zero migration; zero legacy row mutation; zero `33c07feb` mutation; no hard-delete; no NULL compatibility removal; no NOT NULL constraint; no CHECK constraint; no universe_canon aesthetic cleanup; no recovery UI; no provider spend
- [x] Commit + push Slice 18 documentation — landed as `0855c2f`
- [ ] Chris + ChatGPT review + Slice 19 scoping decision

---

**End of SESSION 276 Slice 18 / Delta Stage 7 opener. Audit-only lands. Part B STOP condition triggered exactly as authorization requested — the existing `destroy()` operator-delete path does NOT stamp `audience_scope=NONE`; NULL rows would remain NULL after soft-archive, which mismatches the intended Delta-safe target. No DB mutation performed. 9 §316 rows durably inventoried by UUID + shape; `33c07feb` forensically profiled with two evidence-supported options (WORKSPACE vs NONE) pending admin@mail.com signoff; NULL-debt analysis proves fresh writes can still produce NULL. 332 backend + 656 SPA tests pass unchanged; real DB byte-identical for 12th consecutive slice. STOP for Chris + ChatGPT review of §336 recommendation, §337 gate, §338 Q-276-35 next-question candidate.**

**Slice 18 landed commit SHA:** `0855c2f` (`docs(session-276): Slice 18 / Delta Stage 7 opener — legacy-KD archive audit (Q-276-33) STOP finding, no mutation`). Pushed to `origin/main`. Post-push `main == origin/main == 0855c2f`; working tree clean. Documentation-only landing (no code, no test, no DB delta).

---

# SESSION 276 — Slice 19 / Delta Stage 7 reframe — disposable-dogfood product decision + cascade audit

Audit-only slice. **Chris supplied a scope-changing product decision that supersedes Q-276-35.** All existing KnowledgeDocument data — the 10 NULL rows AND the 62 classified CHARACTER / UNIVERSE rows — is disposable dogfood with no product-preservation value. Slice 19 records the decision durably, audits the dependency / cascade blast radius of a wholesale KD reset, and reframes the SESSION 276 close plan around a materially simpler cleanup path.

## §340. Operator product decision — existing KnowledgeDocument dataset is disposable dogfood (RECORDED DURABLY)

**Trigger.** Chris supplied first-party product intent on receipt of Slice 18's STOP finding:

> The existing KnowledgeDocument dataset is DOGFOOD / EXPERIMENTAL DATA. None of the existing KnowledgeDocument content needs to be preserved for product reasons. This includes: TANK, Tulsi, historical Riggs, Hearth & Hollow, the admins-workspace trafilatura row, the currently classified CHARACTER / UNIVERSE knowledge rows, other historical knowledge generated during Character OS dogfood. Chris does NOT want us spending additional engineering slices reconstructing, preserving, archiving, or designing special migration behavior around these specific persisted specimens. They were useful as evidence for discovering the product invariants. They are not production/customer records.

**Scope explicitly clarified by Chris:**

- **Disposable:** KnowledgeDocument rows, KnowledgeChunk rows, KnowledgeDocumentSpokesperson through-rows.
- **NOT disposable:** user accounts, Workspace rows, Teammate rows, Universe rows, unrelated Composition / Asset / Script / Video / RealtimeSession rows, application configuration.
- **Composition / Script / Video / RealtimeSession** rows themselves are preserved; only their `knowledge_chunk_ids` JSON provenance arrays would become stale (safe degradation — see §342).

**Consequence.** All prior Delta-triage design in this document that assumed audience reconstruction / archive-preservation for the 10 NULL rows (§55.2 ambiguous-classification analysis, §316 operator legacy-cleanup decision, §320 Q-276-33 candidate, §338 Q-276-35 candidate) is superseded as a product requirement. Those findings remain evidentially valuable — they proved the shape of Delta invariants under pressure of real data — but they are no longer implementation drivers.

### §340.1 Q-276-35 supersession

Q-276-35 (§338) asked whether adding a NONE-stamping mode to the operator-delete lifecycle would produce a Delta-safe archive of the 9 §316 rows. Under §340, the answer is: **no code addition is required merely to preserve rows Chris has said should not be preserved.** Q-276-35 is superseded.

**Slice 18 finding preserved as future product evidence.** The mismatch documented at §326 — that `KnowledgeDocumentViewSet.destroy()` does NOT stamp `audience_scope=NONE` on soft-delete of a NULL row — remains a real characterization of current product behavior. It is preserved here as a durable observation for any future product need that requires the soft-archive semantic to converge on NONE (e.g., if customer-facing lifecycle later demands Stage 8-compatible archive shape). It is NOT justification to implement that behavior in SESSION 276.

### §340.2 What Chris's decision unblocks

- **Wholesale KD dataset reset** becomes a legitimate one-slice cleanup instead of a per-row triage across 10 rows.
- **admin@mail.com triage of `33c07feb`** (§329.4) is no longer required — the row is included in the disposable set.
- **The Stage 7 audience-reconstruction planning burden collapses.** Stages 7-9 can compress into ≤ 2 slices (§344).

## §341. Slice 19 falsifiable question (reframed from Q-276-33/35)

> Given that all existing KnowledgeDocument data is disposable dogfood (§340), what is the smallest safe way to eliminate the legacy NULL-data blocker so SESSION 276 can finish validating the permanent Delta model without inventing preservation requirements for test data?

Slice 19 answers this AUDIT-ONLY. Slice 20 (authorized separately) would execute the recommended cleanup.

## §342. Slice 19 baseline SHA + working tree

- Base commit at Slice 19 start: `aa23235` (`docs(session-276): record Slice 18 landed SHA 0855c2f in audit doc`).
- `main == origin/main == aa23235`; working tree clean prior to Slice 19.
- Slice 19 lands as documentation-only (audit + product-decision record). Zero code changes; zero DB mutation.

## §343. Cascade / dependency audit — impact of hard-deleting all KnowledgeDocuments

Read-only script executed at `/tmp/slice19_cascade_audit.py` — the following evidence is authoritative for §340's cleanup planning.

### §343.1 Pre-cleanup DB inventory

```
KnowledgeDocument rows: 72   (active=72; inactive=0)
KnowledgeChunk rows: 1149    (per-chunk embedding vectors)
KnowledgeDocumentSpokesperson through-rows: 62
```

### §343.2 Direct DB cascade (Django FK on_delete)

Only two tables reference KnowledgeDocument via FK. Both are declared with `on_delete=CASCADE`:

| Model | FK field | on_delete | Impact of `KnowledgeDocument.delete()` |
|---|---|---|---|
| `KnowledgeChunk` (`models.py:409-413`) | `document` → KnowledgeDocument | CASCADE | 1149 rows deleted; pgvector vectors freed |
| `KnowledgeDocumentSpokesperson` (`models.py:135-139`) | `knowledgedocument` → KnowledgeDocument | CASCADE | 62 M2M through-rows deleted |

**Outbound FKs from KnowledgeDocument** (not affected by KD delete; documented for completeness):

- `workspace` (CASCADE from Workspace side — deleting Workspace deletes KDs, but KD delete does NOT touch Workspace).
- `universe` (RESTRICT from KD side — deleting Universe is BLOCKED while any KD references it; KD delete removes the block).
- `created_by` → User (SET_NULL from User side; KD delete does not touch User).
- `spokespeople` M2M via through-table (through rows CASCADE; Teammate rows untouched).

**Grep verification.** `Grep pattern "ForeignKey\([^)]*KnowledgeDocument"` across the entire `shell/` tree returns ZERO hits outside `apps/embeddings/models.py`. No other model has an FK to KnowledgeDocument or KnowledgeChunk. Cascade is 100% contained within the embeddings app.

### §343.3 Non-FK provenance references (JSON UUID arrays — would become STALE, not broken)

Four models carry `knowledge_chunk_ids` JSONFields storing chunk-UUID strings (no DB-level FK):

| Model | Total rows | Non-empty JSON provenance |
|---|---|---|
| `apps/scripts/models.py:123` — Script | 6 | 5 |
| `apps/compositions/models.py:427` — Composition | 162 | 103 |
| `apps/videos/models.py:114` — Video | 0 | 0 |
| `apps/realtime/models.py:102` — RealtimeSession | 40 | 20 |

**Post-cleanup behavior:** JSON arrays retain stale chunk-UUID strings. `resolve_chunk_ids_to_docs` at `retrieval.py:63-118` (Slice 16 §283.2 provenance carve-out) queries `KnowledgeChunk.objects.filter(id__in=chunk_ids)` — stale IDs return an empty QuerySet, resolver returns `[]`, provenance panels show "no docs used" silently. **No 500s; no exceptions; no DB integrity errors.** The stale rows are themselves dogfood-tier artifacts per §340 (all 162 Composition rows + 6 Scripts + 40 RealtimeSessions were produced during Character OS dogfood).

Chris's §340 scope preserves these Composition / Script / Video / RealtimeSession rows themselves — only their provenance-panel display degrades. Acceptable per §340: dogfood provenance for dogfood renders.

### §343.4 Unaffected entities (per §340)

| Entity | Row count | Impact of KD cleanup |
|---|---|---|
| Workspace | 882 | UNAFFECTED |
| User | 878 | UNAFFECTED |
| Teammate | 16 | UNAFFECTED |
| Universe | 6 | UNAFFECTED (RESTRICT blocks removed but Universes not deleted) |

**Blast radius is tightly bounded.** KD hard-delete affects only KnowledgeDocument / KnowledgeChunk / KnowledgeDocumentSpokesperson tables. All other product data survives verbatim.

### §343.5 Universe RESTRICT-block release

6 Universe rows currently have KD references blocking their DELETE. Hard-deleting all KDs releases those blocks — Universe rows become newly deletable. **Slice 19 does not act on this**; documented for future awareness. Universes remain intact under Chris's §340 preservation scope.

## §344. Test / runtime dependency on persisted KDs

Grep for hardcoded UUIDs of the 10 NULL rows across the entire repo:

```
grep -r "8c6f0c14|7ecde40b|90ad200c|aa90d895|e37ea174|b58efd31|7f41d8e3|c408656d|0088f31f|33c07feb"
```

**Results:**

- **Documentation files** (`docs/design/*.md`): 6 files reference the UUIDs as historical evidence. These references are STATIC (text mentions in audit findings) and would remain valid — the audit's job is to record what existed at a point in time; the docs don't require the rows to persist. Files: `SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md`, `SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md`, `SESSION_276_HANDOFF.md`, `SESSION_273_PRODUCT_ORIENTATION_AND_NEXT_DIRECTION.md`, + 2 session_273 experiment JSON files.
- **Test code** (`apps/compositions/tests/test_claim_verifier.py:69-71`): one docstring comment references `33c07feb` as the origin of a hardcoded content excerpt used in the test. The test itself uses the excerpt as inline test data; it does NOT query the persisted row. Safe.
- **Migrations** (`apps/embeddings/migrations/`): only `0008_session276_stage2_backfill.py` uses `RunPython`, and that runs generic classification rules (Slice 7 §92) with no hardcoded UUIDs. Idempotent by design.
- **Fixtures / initial_data / loaddata:** none. No `fixtures/` directory in `apps/embeddings/` or `shell/`. No initial-data files exist.

**Tests use `@pytest.mark.django_db` — transactional per-test DBs isolated from the real dogfood DB.** No test loads or depends on any specific persisted KnowledgeDocument row.

**Runtime startup (Django + Celery boot):** no code paths query for specific KD UUIDs. Startup validates only schema + migrations + connection; no data-content dependencies.

**Conclusion.** Hard-deleting all 72 KDs breaks zero tests, zero runtime paths, and zero user flows. It cosmetically degrades stale JSON provenance in dogfood-tier Composition / Script / RealtimeSession rows (documented at §343.3).

## §345. Fresh-write NULL producibility (independent of dogfood cleanup)

Chris's authorization framed this as: *"The goal is not merely 'DB currently has zero NULL rows.' The goal is 'Normal product behavior cannot recreate ambiguous audience state.'"* Slice 19 audits both criteria.

### §345.1 Current DB NULL state

Post-Slice-18 (unchanged since Slice 15): **10 NULL rows**. All 10 would be swept away by the §343 wholesale KD reset — going to 0 NULL rows mechanically.

### §345.2 Can fresh writes still produce audience_scope=NULL?

**YES.** The fresh CREATE path at `shell/apps/embeddings/ingestion.py:275-301` explicitly lands NULL for the `(no spokespeople + no universe + no workspace_shared_intent marker)` case. The Slice 11 Option 3 decision (§169-§175) preserved this as "transitional NULL" during Delta rollout.

Precise caller enumeration:

**SPA callers (cannot produce NULL):**
- All 4 SPA CREATE call sites at `web/src/routes/workspace/knowledge.tsx` are wired to the mandatory `UniverseScopePicker` per Slice 12. The picker forces one of `{spokespeople[], universe, workspace_shared_intent=True}`. SPA-originated writes **cannot** land at NULL.

**Non-SPA callers (CAN produce NULL):**
1. **`python manage.py smoke_ingest`** — developer-only management command at `apps/embeddings/management/commands/smoke_ingest.py`. Calls `ingest_text(...)` without the workspace_shared_intent marker. Explicitly a dev diagnostic tool.
2. **Direct `POST /api/knowledge/` API without `workspace_shared_intent`** — technically accepted by the serializer as long as the row shape is valid (`(no spokespeople + no universe)` reaches the NULL branch in `_persist`). Not a UI-driven caller — no first-party product surface today invokes it.
3. **Internal Python API** (`ingest_text(...)`, `ingest_pdf(...)`) called from other Python code (tests, fixtures, future dev jobs) without passing spokespeople / universe / workspace_shared_intent=True.

None of (1)-(3) are "normal current product flows." The SPA is the only end-user surface, and it cannot produce NULL.

### §345.3 Why this matters even under §340 disposable-dogfood scope

Chris's decision removes the pressure to preserve the CURRENT NULL rows, but does NOT close the future producibility loophole. A fresh dogfood session that exercises `smoke_ingest` or direct API calls can re-create NULL rows and re-open the same debt the Delta rollout was designed to eliminate.

**Blocks Stage 8 (`NOT NULL` constraint):** the constraint requires that no CURRENT and no FUTURE write can land NULL. §345.2 shows fresh writes can still land NULL, so Stage 8 is blocked until the loophole closes even after wholesale KD reset.

**The fresh-write NULL closure is a genuine permanent-product issue.** It deserves the next small implementation slice per Chris's authorization: *"If yes, THAT is a real permanent-product issue and deserves the next small implementation slice."*

### §345.4 Options for closing the loophole (design record; not implemented in Slice 19)

**Option A — Ingestion default to NONE + is_active=False when no positive signal.** Preserves the API surface; changes silent-NULL to explicit fail-closed. Simple; matches Delta's fail-closed principle at the write boundary. Requires caller code paths that today produce NULL to either supply a marker OR accept the fail-closed default.

**Option B — Serializer rejects payloads without a positive audience signal.** Requires the DRF `POST /api/knowledge/` to fail with 4xx when the payload lacks any of `spokespeople`, `universe`, `workspace_shared_intent`. Breaks the smoke_ingest dev tool unless it's updated; but smoke_ingest is dev-only.

**Option C — Ingestion function signature required-arg change.** Make `ingest_text(...)` / `ingest_pdf(...)` require one of the three positive markers as a keyword arg. Compile-time enforcement (arg-missing = TypeError). Cleanest but breaks every existing internal caller until updated.

**Option D — Combined (Options A + B).** Ingestion defaults + serializer 4xx. Belt-and-suspenders; matches the pattern of Slices 13 + 14 (structured error + failing-closed serializer). Recommended for consistency with prior Delta slices.

Slice 19 does NOT choose. That's a Slice 20 / 21 authorization question.

## §346. Revised shortest path to SESSION 276 close

Compared to the pre-§340 path (which required per-row triage of 10 NULL rows + Q-276-35 code + Q-276-34 admins-workspace triage + Stage 8 constraint), the disposable-dogfood decision compresses SESSION 276 to a much shorter tail. Recommended sequence:

**Slice 20 — Data reset + fresh-write NULL closure (bundled).**

- (a) Hard-delete all 72 KnowledgeDocument rows via a targeted, authorized management command or admin action. Cascades remove 1149 chunks + 62 through-rows. JSON provenance in Composition / Script / RealtimeSession becomes stale (safe degradation per §343.3).
- (b) Implement Option D (or Chris-selected variant) to close the fresh-write NULL loophole (§345).
- (c) Prove `KnowledgeDocument.objects.filter(audience_scope__isnull=True).count() == 0` post-cleanup AND that any test / API call attempting to create a NULL row fails-closed.
- (d) Run full regression + smoke tests.

**Slice 21 — NULL branch removal + `NOT NULL` migration + CHECK constraint.**

- (a) Remove NULL compatibility branches from `retrieval.py:216-269` (Slice 16 §285) and `views.py:106-146` (Slice 17 §306).
- (b) Update Slice 16 / 17 tests A / B (NULL fallback tests) to test CHARACTER / UNIVERSE / WORKSPACE fixtures instead.
- (c) Add migration: `audience_scope` becomes `NOT NULL` with a `CHECK` constraint enforcing Delta invariants per Slice 4 §51 (e.g., CHARACTER → M2M non-empty; UNIVERSE → universe non-null; WORKSPACE → universe NULL; NONE → is_active False).
- (d) Full regression + fresh dogfood session verifies no NULL, no invariant violations.

**Optional Slice 22 — universe_canon aesthetic reformulation** (§317.3). Non-blocking; can defer indefinitely.

**Minimum Slices to close Delta:** 2 (Slice 20 + Slice 21). Down from the pre-§340 estimate of 3-5 slices.

## §347. Prediction vs actual

Slice 19 was AUDIT-only; predictions were about the audit outputs themselves.

| Prediction | Evidence |
|---|---|
| KD-owned cascade is contained within embeddings app | ✓ §343.2 — only KnowledgeChunk + KnowledgeDocumentSpokesperson via FK; grep confirms zero external FK |
| JSON provenance references become stale but not broken | ✓ §343.3 — 128 non-empty JSON arrays across Script/Composition/RealtimeSession would silently return `[]` via `resolve_chunk_ids_to_docs` |
| Workspaces / Teammates / Universes / Users untouched | ✓ §343.4 — none have FKs from KD's perspective |
| Zero test/runtime dependency on specific persisted KD UUIDs | ✓ §344 — only docstring / audit-doc references; no functional dependency |
| SPA callers cannot produce NULL | ✓ §345.2 — Slice 12 UniverseScopePicker enforces marker |
| Non-SPA callers (dev tools + internal Python API) CAN still produce NULL | ✓ §345.2 — 3 caller categories identified |
| Disposable-dogfood decision materially simplifies the close plan | ✓ §346 — 2 slices instead of 3-5 |

7/7 predictions supported.

## §348. Files changed (Slice 19)

- `docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md` — this Slice 19 appendix (§340-§352).
- **Not touched:** zero `.py` files, zero test files, zero SPA files, zero migrations, zero DB rows.

## §349. Unresolved questions

1. **Slice 20 execution mechanism.** For (a) data reset, is Chris's preference: (i) a one-off `python manage.py shell -c "KnowledgeDocument.objects.all().delete()"` invocation under his signoff, (ii) a permanent management command (`python manage.py reset_knowledge_dogfood`) with an interactive confirmation prompt, or (iii) a Django admin bulk action?
2. **Fresh-write NULL closure — chosen option.** §345.4 lists A/B/C/D. Chris + ChatGPT decide which lands in Slice 20.
3. **Composition / Script / RealtimeSession provenance stale-JSON hygiene.** After §343.3 stale references land, is there a follow-up (e.g., "delete-all-dogfood-provenance") desired, or is the silent-empty degradation acceptable indefinitely?
4. **Fresh dogfood after Slice 20.** Chris likely wants to re-populate KDs with a small validation set post-cleanup to prove end-to-end Delta behavior on a fresh substrate. Not part of Slice 20 / 21 but implied by the "fresh dogfood from a clean knowledge substrate" step in the user's likely-session-end plan.
5. **Slice 22 (universe_canon reformulation).** Still open; still non-blocking; still deferrable.

## §350. Recommendation

**Slice 19 is complete as an audit-only documentation slice.** The disposable-dogfood decision (§340) is durably recorded. The cascade / dependency blast radius of a wholesale KD reset is bounded (§343). The fresh-write NULL loophole is precisely identified (§345). The revised close plan collapses SESSION 276 to 2 remaining slices (§346).

**Recommended next action:** Slice 20 (audit-first as usual, then narrow implementation gate). Bundle the wholesale KD reset AND the fresh-write NULL closure into a single slice — they are architecturally coupled (the reset gets NULL count to 0; the closure keeps it at 0). Then Slice 21 removes the compatibility branches and adds the `NOT NULL` + CHECK constraint. Then SESSION 276 closes with a fresh dogfood run on a clean knowledge substrate.

## §351. Explicit STOP gate

STOP before Slice 20. Review Slice 19 evidence with Chris + ChatGPT.

- Does Chris prefer §349.1 mechanism (i), (ii), or (iii) for the data reset?
- Does Chris prefer §345.4 option A, B, C, or D for the fresh-write NULL closure?
- Does Chris want Slice 20 to bundle both (a) + (b), or split them?
- Does Chris want the Slice 21 CHECK constraint to encode all four Delta invariants (Slice 4 §51) or a subset?
- Does Chris want to pre-authorize a "fresh dogfood seed" step for Slice 22, or defer that decision until Slice 21 lands?

## §352. Smallest recommended next question — Q-276-36

**Q-276-36 (candidate — Slice 20 opener).** *If (a) all 72 existing KnowledgeDocument rows are hard-deleted through a single authorized cleanup operation, AND (b) the fresh-write ingestion path is closed to prevent `audience_scope=NULL` recreation (via Chris-selected option from §345.4), does the resulting DB reach `KnowledgeDocument.objects.filter(audience_scope__isnull=True).count() == 0` AND every attempted post-closure write from any caller (SPA, direct API, management commands, internal Python API) either supply a positive audience marker OR fail closed, with all 332 backend + 656 SPA tests passing unchanged after fixtures that intentionally created NULL rows are updated to CHARACTER / UNIVERSE / WORKSPACE?*

## §353. Slice 19 checklist

- [x] Slice 18 landed as `0855c2f`; catch-up SHA-record `aa23235`
- [x] Slice 19 baseline verified — `main == origin/main == aa23235`, working tree clean (§342)
- [x] Chris's disposable-dogfood product decision recorded durably (§340)
- [x] Q-276-35 supersession recorded; Slice 18 finding preserved as future product evidence (§340.1)
- [x] Slice 19 falsifiable question reframed (§341)
- [x] Cascade / dependency audit — direct FKs, JSON references, unaffected entities, Universe RESTRICT block (§343)
- [x] Test / runtime dependency check — zero functional dependency on persisted KD UUIDs (§344)
- [x] Fresh-write NULL producibility audit — SPA cannot; non-SPA can via 3 caller categories (§345)
- [x] 4 closure options for the fresh-write loophole documented (§345.4)
- [x] Revised shortest path to SESSION 276 close — 2 remaining slices (§346)
- [x] Prediction vs actual — 7/7 supported (§347)
- [x] Files changed (§348)
- [x] Unresolved questions (§349)
- [x] Recommendation (§350)
- [x] Explicit STOP gate (§351)
- [x] Smallest next question Q-276-36 (§352)
- [x] Zero DB mutation; zero code change; zero migration; zero legacy row mutation; no hard-delete executed; no NULL closure implemented; no NOT NULL constraint; no CHECK constraint; no universe_canon aesthetic cleanup; no recovery UI; no provider spend
- [ ] Commit + push Slice 19 documentation
- [ ] Chris + ChatGPT review + Slice 20 scoping decision (mechanism + closure option + bundle-vs-split)

---

**End of SESSION 276 Slice 19 / Delta Stage 7 reframe. Chris's disposable-dogfood product decision (§340) collapses the SESSION 276 tail from per-row audience-reconstruction triage into a wholesale KD reset. Q-276-35 superseded; Slice 18 finding preserved as future product evidence. Cascade audit bounds the blast radius: only KnowledgeDocument + KnowledgeChunk + KnowledgeDocumentSpokesperson affected (1149 chunks + 62 through-rows cascade); Workspaces / Users / Teammates / Universes / Composition / Script / RealtimeSession rows all preserved; JSON provenance in dogfood-tier rows becomes silently stale (no errors). Zero test / runtime dependency on any specific persisted KD UUID. Fresh-write NULL loophole precisely identified: SPA cannot produce NULL (Slice 12 mandate); dev tools + internal Python API + direct API without marker CAN. Revised close plan: Slice 20 (data reset + NULL loophole closure bundled) + Slice 21 (NULL branch removal + NOT NULL migration + CHECK constraint). 2 slices to finish Delta. STOP for Chris + ChatGPT review of §350 recommendation, §351 gate, §352 Q-276-36 next-question candidate.**




