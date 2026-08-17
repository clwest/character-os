---
title: "SESSION 261 — Capability inventory audit (read-only)"
status: draft — read-only inventory, no design, no implementation
date: 2026-08-17
depends_on:
  - "handoffs/SESSION_259_WORKSPACE_AUDIT.md"
  - "handoffs/SESSION_259_OBSERVABILITY_BACKLOG.md"
  - "handoffs/SESSION_260_DIALOGUE_CPS_CALIBRATION.md"
  - "CHARACTER_OS_INVENTORY.md"
scope: What already exists in Character OS that could support persistent
       characters, worlds, casts, locations, continuity, episodes, and
       reusable visual identities — and what is genuinely missing. Read-only.
       No writes. No provider calls. No architecture design. No schema
       proposals.
---

# SESSION 261 — Capability inventory audit

Read-only investigation triggered by the operator's observation that
`CharacterIdentityVersion.spec` already carries versioned visual
identity, `NormalizationManifest.background_id` already carries the
backdrop as a separate identifier, teammate voice/context lives in
mutable fields, and K-docs are separately bound. Therefore "same
character, different background" may already be partly supported. The
operator asked for the same level of evidence across the entire
platform — model by model — before any Universe / world / persistent-
character work is designed.

**Nothing was written to any file other than this audit doc. No models,
migrations, schemas, or existing docs were modified.**

---

## Motivating precedent

`apps.identity.models` (SESSION 241–245, §19 Steps 2–6 of the Canonical
Identity Contract) already decouples four things that most systems
conflate:

- **Identity** — `CharacterIdentity` + `CharacterIdentityVersion` +
  `spec` (branch-schema-validated JSON), workspace-scoped, versioned,
  approved-state gated (`identity/models.py:96–334`).
- **Approved representations** — `ApprovedRepresentationBundle` binds
  one version to a `CanonicalVoiceReference` + `CanonicalRealtimeReference`
  + admitted `IdentityReference` set (`identity/models.py:1121–1218`).
- **Backdrop** — `NormalizationManifest.background_id` is an id from
  `docs/design/visual/portrait_qualification/schemas/background_family_v1.yaml`,
  carried on the per-generation manifest, not on identity
  (`identity/models.py:955–961`). Background family YAML lists five
  round-one identifiers (`neutral_warm_studio`, `neutral_cool_studio`,
  `warm_material_surround`, `soft_environmental_depth`,
  `conversational_darker_surround`) and a `reviewer_override` mechanism
  (`background_family_v1.yaml:67–184`).
- **Knowledge** — bound to teammate via `KnowledgeDocument.spokespeople`
  M2M; independent of identity substrate (`embeddings/models.py:130–140`).

So identity, representation, backdrop, and knowledge are already four
axes at the substrate layer. Whether that decoupling holds end-to-end
across every axis the operator cares about is the question this audit
answers.

---

## Codebase orientation

37 project-owned Django models across 14 apps
(`docs/CHARACTER_OS_INVENTORY.md:30–83`). Enumerated model files (from
`find shell/apps -name models.py`):

- Real content models: `accounts`, `billing`, `bootstrap_review`,
  `campaigns`, `compositions`, `conversations`, `embeddings`,
  `identity`, `publish`, `realtime`, `scripts`, `spokespeople`,
  `transcripts`, `videos`.
- **Empty scaffolds:** `apps/memory/models.py` (0 lines),
  `apps/agents/models.py` (0 lines). Both apps have `apps.py` +
  `admin.py` + `urls.py` (also empty) + `migrations/__init__.py` only —
  **registered but never populated**. Notably `memory` (which one
  might expect to be the character-memory home) is a stub; every
  actual memory-adjacent code path lives elsewhere.

---

## 1. CHARACTER IDENTITY

**Models.**

- `CharacterIdentity` (`identity/models.py:96–171`) — one per identity
  per workspace. Fields: `workspace` FK (CASCADE, NOT NULL), `teammate`
  FK (SET_NULL, nullable during bootstrap), `kind`
  (`human` / `non_human`), `name`, `created_at`, `archived_at`.
  Partial unique on `(teammate) WHERE teammate IS NOT NULL`
  (line 163–167): "one canonical identity per real teammate."
- `CharacterIdentityVersion` (`identity/models.py:174–334`) — one row
  per authored revision. Fields: `identity` FK, `revision`, `state`
  (`draft`|`approved`|`superseded`|`rejected`), `spec` (JSONB,
  branch-schema-validated), `spec_schema_version` (0 =
  `legacy_unvalidated` sentinel; ≥ 1 = canonical), `approved_by`,
  `reviewer_notes`, timestamps. Partial unique
  `one_approved_version_per_character_identity` at line 282–286.
- Branch schemas: `schemas/human_identity_schema_v1.yaml` (405 lines,
  full identity JSON Schema + `required_for_identity` +
  `surface_requirements`); `schemas/non_human_test_schema_v1.yaml` (191
  lines, NON-CANONICAL, `character_type` enum
  `animal|fictional_creature|stylized_object|other`).

**Classification: ACTIVE + PARTIAL.**

- Human branch is fully authored and schema-validated at write time.
- Non-human branch is a substrate exercise only. The schema explicitly
  says "purpose_of_existence: substrate_exercise_only" and "This file
  is DELETED, not amended, when Character Presence Language lands"
  (`non_human_test_schema_v1.yaml:14–46,183–192`).
- **Read/write runtime:** `apps.identity.services` (create_draft,
  approve, supersede, approve_prequalification — 1959 lines).
- **Versioned:** yes, via `CharacterIdentityVersion.revision`.
- **Workspace-scoped:** yes (mandatory FK).
- **Character-scoped:** yes (partial unique on `teammate`).
- **UI support:** Bootstrap review admin surface only
  (`shell/apps/bootstrap_review/views.py`, SPA route
  `web/src/routes/settings/bootstrap-review/slot.tsx`). Regular
  operator UI does not create/approve versions.
- **Tests:** `apps/identity/tests/test_services_write_path.py`,
  `test_models_references.py`,
  `test_normalization_manifest_pipeline_version.py`.
- **Safe to reuse:** yes — this is the strongest substrate in the repo.

**Identity continuity across generations.** Enforced structurally.
Every `GenerationRecord` (`identity/models.py:606–867`) FKs an
`identity_version` (PROTECT) and is append-only (`save` guard at
line 852–867). "Which identity version produced this pixel" is
answerable from the graph.

**Non-human identity support.** Substrate accepts the branch; schema
is a placeholder. **Patch and Rivet do not currently live in this
substrate at all** — see §6 special question below and §13 cast.

---

## 2. CHARACTER VISUALS

**Models.**

- `IdentityReference` (`identity/models.py:385–494`) — typed
  Asset ↔ IdentityVersion link. `kind` enum:
  `portrait_reference` / `motion_reference` / `speech_reference` /
  `body_reference` / `environment_reference` / `expression_reference`.
  `purpose` = free-text validated against branch purpose schema
  (`purpose_schema_human_v1.yaml`). `state` = `raw` / `normalized` /
  `provisional` / `approved` / `superseded` / `rejected`.
  Partial unique `one_approved_reference_per_slot` on
  `(identity_version, kind, purpose) WHERE state=approved`.
- `GenerationRecord` (`identity/models.py:606–867`) — immutable
  provider-attempt evidence. Fields include `provider`, `provider_model`,
  `direction_hypothesis` (five Portrait Language directions +
  `identity_only`), `prompt_snapshot`, `raw_output_asset`,
  `normalized_output_asset`, `execution_mode` /
  `execution_mode_actual`, `approval_state`.
- `NormalizationManifest` (`identity/models.py:891–1022`) — one per
  generation. Immutable. Fields include `pipeline_version`,
  `surface_profile_id`, `surface_profile_version`, **`background_id`
  (CharField(64), pulled from `background_family_v1.yaml`)**,
  `stages_executed`, `stages_skipped`, `eye_line_adjustments`,
  `crop_metadata`, `execution_duration_ms`.
- `CanonicalVoiceReference` (`identity/models.py:1034–1077`) — per-
  version canonical voice; provider details on the FKed `GenerationRecord`.
- `CanonicalRealtimeReference` (`identity/models.py:1080–1118`) — per-
  version canonical realtime avatar reference.
- `ApprovedRepresentationBundle` (`identity/models.py:1121–1218`) —
  binds version + approved voice + approved realtime + admitted
  references. Partial unique `one_approved_bundle_per_identity_version`.

**Legacy visuals live parallel on Teammate** for the growth window
(§17.10.a, `spokespeople/models.py:149–169`):
`runway_avatar_id` (CharField(120)), `runway_avatar_status`,
`portrait_path` (TextField), `voice_id` (CharField(120)),
`visual_subject` (CharField(750)), `visual_template` (enum:
`mascot`|`founder`|`coach`|`local_guide`). Kept alive by
`apps.identity.compat` (770 lines) with an explicit Step-13 deletion
horizon.

**Asset visuals surface.** `compositions.Asset`
(`compositions/models.py:132–354`) with 12-value `AssetRole` enum
(TALKING_HEAD / BACKDROP / COMPOSITE_OUTPUT / POLISH_OUTPUT /
REFERENCE_IMAGE / B_ROLL / TRANSCRIPT / AUDIO_TRACK / VOICEOVER_AUDIO
/ RAW_UPLOAD / EXPERIMENT / BRIDGE_ANSWER), plus image-specific
provenance columns (`purpose`, `model`, `style_preset`, `prompt`,
`subject`, `negative_prompt`, `aspect_ratio`) — see §11.

**Classification: ACTIVE for identity substrate; PARTIAL for the
end-to-end visual path.**

- Substrate lets multiple approved reference-view assets exist for
  one identity across kind/purpose slots (front, neutral_rest,
  slight_left, listening, consideration, gentle_positive, etc. —
  enumerated per surface in
  `human_identity_schema_v1.yaml:314–363`).
- `background_id` is on the manifest, not on identity — background
  is orthogonal to identity **at the normalization stage**.
- **However:** the composition pipeline (`compositions.starters`
  `talking_head_with_backdrop`, `backdrop_layout`, `pip_layout`,
  `cohost_layout`, `broll_splice`, `composite_video`) uses its own
  `backdrop` concept — an `Asset(role=BACKDROP)` produced by
  `generate_visual_clip` or picked from the library. This is a
  DIFFERENT `backdrop` from `NormalizationManifest.background_id`.
  See §12 for full analysis.

**Versioned:** identity references yes (`IdentityReference.state`);
Asset (`compositions.Asset`) no version chain — assets are treated as
immutable byte streams.
**Workspace-scoped:** yes (all Assets have workspace FK, cross-workspace
references rejected at `IdentityReference.clean` line 476–494).
**Character-scoped:** identity references bound to version → identity →
teammate. Composition Assets have optional
`Asset.spokesperson` FK (SET_NULL).
**UI support:** bootstrap review UI only for the canonical substrate;
`/workspace/assets` browser for legacy Asset (Asset Library v1,
`ASSET_LIBRARY_V1.md`).
**Tests:** `apps/identity/tests/` (multiple);
`apps/compositions/tests/test_backfill_asset_roles.py`.
**Safe to reuse:** substrate yes; composition-side backdrop
naming collision requires disambiguation (§12).

---

## 3. VISUAL STYLE / PRESETS

**Findings.**

- `Teammate.visual_template` (`spokespeople/models.py:116–130`) —
  four-value enum `mascot` / `founder` / `coach` / `local_guide`.
  Persisted so re-bake can default to the operator's original
  template choice. **Legacy Teammate compatibility field.**
- `Teammate.visual_subject` (`spokespeople/models.py:103–115`) —
  free-text description ("armored battle unicorn", "neon-pink
  raccoon in a denim jacket") threaded into the media-engine's
  `/internal/portrait/` subject parameter.
- `Asset.style_preset` (`compositions/models.py:267–276`) — CharField
  referencing `media-engine/app/services/style_library.py` preset slug.
  Populated only for image assets generated via `POST /api/images/`.
- `SurfaceProfile` YAMLs
  (`docs/design/visual/portrait_qualification/schemas/surface_profiles/`)
  — declarative per-surface rendering profile, referenced by
  `NormalizationManifest.surface_profile_id` +
  `surface_profile_version`. Data, not a Django table.
- Direction hypothesis enum on `GenerationRecord.direction_hypothesis`
  (`identity/models.py:544–558`): five Portrait-Language directions
  (`softened_photographic`, `cinematic_naturalistic`,
  `painterly_naturalistic`, `contemporary_portrait_illustration`,
  `lightly_stylized_realism`) + `identity_only`.
- Recipe form field `style_preset` on `style_remix_pass` recipe
  (`compositions/recipes.py:1420`).

**Classification: PARTIAL.**

- Style lives in three unrelated places: legacy `Teammate.visual_template`
  (mascot/founder/coach/local_guide); per-image `Asset.style_preset`
  (media-engine style library); benchmark `direction_hypothesis` on
  `GenerationRecord` (Portrait Language directions).
- **Style is neither identity, nor generation-input primitive, nor
  asset metadata cleanly** — it is spread across all three layers
  under different vocabularies.
- Can style vary independently of identity today? For image
  generation via `/api/images/`, yes — `Asset.style_preset` is per-asset.
  For teammate portrait bake, no — `visual_template` is fixed on the
  teammate. For identity substrate qualification, direction is
  per-`GenerationRecord`.

**Naming concern (findings only, per audit rules).** "Style" is
overloaded across (a) `visual_template` (4-choice teammate visual
axis), (b) `style_preset` (image-generation library), (c) Portrait
Language "direction". No single surface unifies them.

**Versioned:** no.
**Workspace-scoped:** yes (all surfaces are).
**Character-scoped:** partially — `visual_template` yes, `style_preset`
per-asset.
**UI support:** style preset picker in image gen surface;
`visual_template` in wizard.
**Tests:** `apps/compositions/tests/test_v11_style_remix.py`,
`test_images_api.py`.
**Safe to reuse for persistent-world architecture:** requires a
disambiguation slice first.

---

## 4. VOICE / CHARACTER BEHAVIOR

**Fields on Teammate** (`spokespeople/models.py`):

- `personality` (line 90–102) — **HOW** the teammate speaks (voice /
  character / mannerisms). Backfilled from `business_brief` in
  migration 0005.
- `tone_archetype` (line 131–142) — 5-value enum
  `tutor`/`authority`/`friend`/`expert`/`performer`.
- SESSION 253 Character Voice suite (lines 247–320):
  - `character_point_of_view` (TextField) — what the character
    notices / believes / opines. "Orthogonal to `personality`
    (HOW they write)."
  - `voice_energy` — enum `low`/`medium`/`high`.
  - `voice_humor` — enum `none`/`dry`/`warm`/`playful`.
  - `voice_directness` — enum `soft`/`balanced`/`direct`.
  - `voice_signature_phrases` — TextField, "possibilities not
    catchphrases"; proper nouns enter K6.4 allowed vocabulary.
  - `voice_avoid_phrases` — TextField, merged with platform anti-AI-
    copy default list at K6 prompt-assembly time.
- Voice provider ID: legacy `Teammate.voice_id` (line 169). Canonical
  form is `CanonicalVoiceReference` (see §2).

**Consumers (runtime).**

- `character_os/script_synthesis.py:621–662` —
  `_build_character_voice_section` reads all six SESSION 253 fields +
  `personality` + `character_point_of_view`.
- `character_os/dialogue_synthesis.py:464–532` —
  `_build_character_voice_block` reads the same set; SESSION 259
  Slice B wires `voice_avoid_phrases`.
- `character_os/conversation_synthesis.py` — conversation reply
  synthesis; reads `business_brief` + `personality`.
- `character_os/realtime_document.py` — realtime document composition;
  reads `personality` (mapped to Runway realtime `personality` field).
- `character_os/claim_verifier.py` — K6.4 verifier; extracts allowed
  vocabulary from `voice_signature_phrases`.

**Classification: ACTIVE, MUTABLE, UNVERSIONED.**

- **Mutable in place** — no version history on any voice field.
  Overwriting `personality` today loses the prior value silently.
- **Backfill-from-business_brief history** — SESSION 175 split
  personality out of `business_brief`. SESSION 253 added six more
  fields backfilled from `tone_archetype`. Neither has a version log.
- **Character Voice can leak into K2** (memory:
  `feedback_character_voice_can_leak_into_k2.md`, SESSION 259).
  Content-type violations both directions happen routinely; audit
  requires checking three surfaces per character.

**Versioned:** **no**. (Contrast with visual identity, which is
versioned via `CharacterIdentityVersion`.)
**Workspace-scoped:** yes (via Teammate).
**Character-scoped:** yes.
**UI support:** operator-editable at
`/spokespeople/{id}/identity` (SPA); wizard for initial values.
**Tests:** `apps/compositions/tests/test_session253_character_voice_prompt.py`,
`test_session259_slice_b_avoid_phrases.py`.
**Safe to reuse:** yes, but voice/POV changes are silently
destructive today — future architecture must decide whether these
belong on Teammate (mutable) or migrate under the identity substrate
(versioned).

---

## 5. CHARACTER CONTEXT / ROLE

**Fields on Teammate** (`spokespeople/models.py:71–232`, SESSION 232
"Identity surface"):

- `business_brief` (line 71–82) — **WHAT** the business does; facts
  the teammate grounds claims in. Post-SESSION 175 this is facts-only.
- `who_you_help` (line 186) — identity slot 2, target customer.
- `what_you_sell` (line 195) — identity slot 3, offering.
- `always_emphasize` (line 204) — identity slot 4, positive brand
  claims.
- `never_say` (line 213) — identity slot 5, guardrails.
- `desired_feeling` (line 222) — identity slot 6, emotional outcome.
- `identity_fields_filled_count()` method (line 360–369) — drives SPA
  "N of 6 filled" progress signal.

**No dedicated "creator-role" / "business-role" / "narrative-role"
field.** The Teammate is treated as a single opaque persona. There is
no distinction between "spokesperson for a business" vs "character in
a narrative" vs "operator's AI proxy" — these all collapse to one
Teammate row.

**Consumers.** Read from every synthesis module
(`script_synthesis`, `dialogue_synthesis`, `conversation_synthesis`,
`realtime_document`, `teammate_ask`, `prompts/brand.py`,
`prompts/sharpening.py`, `templates/teammate_templates.py`,
`claim_verifier`).

**Classification: ACTIVE, MUTABLE, UNVERSIONED.**

- Six-slot identity surface exists as first-class Teammate columns.
- No "role" abstraction anywhere. The word "role" appears in
  `Membership.Role` (accounts) and `Asset.role` (asset taxonomy) —
  neither is a character-role concept.

**Versioned:** no.
**Workspace-scoped:** yes.
**Character-scoped:** yes.
**UI support:** yes — `/spokespeople/{id}/identity`.
**Tests:** `apps/spokespeople/tests/` (identity field coverage).
**Safe to reuse:** yes for context/copy; missing for role/purpose.

---

## 6. KNOWLEDGE

**Models.**

- `KnowledgeDocument` (`embeddings/models.py:111–245`) — workspace FK
  (CASCADE), teammate M2M via explicit through
  `KnowledgeDocumentSpokesperson`, `title`, `document_type` (enum:
  `text`|`markdown`|`pdf`|`url`), `raw_content`, `processed_content`,
  `content_hash` (SHA-256; unique `(workspace, content_hash)` for
  dedup), `source_url`, `source_metadata`, `ingested_via`
  (`paste`|`upload`|`serper`|`seed`), `status`
  (`pending`|`processing`|`processed`|`failed`), `is_active`, audit
  fields.
- `KnowledgeChunk` (`embeddings/models.py:248–321`) — 1536-dim pgvector
  embedding column, HNSW index, chunk_text, chunk_index, chunk_size,
  overlap_size, cost + timing telemetry.
- `KnowledgeDocumentSpokesperson` — explicit through model preserving
  legacy `spokesperson_id` DB column across the SESSION 240
  rename (`embeddings/models.py:70–108`).

**Retrieval.**

- `apps.embeddings.retrieval.retrieve_for_teammate(spokesperson, ...)`
  is the only sanctioned consumer of `KnowledgeChunk.objects`
  (contract rule 2). Filters by `document__workspace=spokesperson.workspace`
  before the visibility clause; visibility clause is
  `Q(document__spokespeople__isnull=True) | Q(document__spokespeople=spokesperson)`.
- **Empty M2M = "visible to all teammates in this workspace"**
  (SESSION 259 audit §4).
- **No `workspace=` param exists on `retrieve_for_teammate`** —
  cross-workspace leaks are structurally impossible.

**Conversation embeddings live in a separate table**
(`conversations/models.py:124–176`, `ConversationEmbedding`) so
`retrieve_for_teammate` cannot reach conversation turns and vice
versa (`conversations/models.py:1–16` design note).

**Document typing.** `document_type` enum is coarse
(`text`|`markdown`|`pdf`|`url`); no notion of "K2 doc" vs
"business brief" vs "product spec" vs "curriculum." Categories are
implicit in the operator's titling and per-teammate M2M assignment.

**Shared vs character-specific.** Sharing is expressed via empty M2M
= workspace-wide; specific assignment via M2M attach. **No "cast"
subset** — an M2M attach is 1:N (doc to teammates) but the operator
UX to attach one doc to multiple teammates is per-teammate click-by-
click (SESSION 259 audit §7). Cross-teammate leak within a workspace
is real and unavoidable at retrieval time; K6 dialogue synthesis
sees whatever the cosine query surfaces (SESSION 259 audit §6).

**Classification: ACTIVE, PARTIAL for scoping UX.**

**Versioned:** no (only `content_hash` for dedup identity).
**Workspace-scoped:** yes.
**Character-scoped:** yes via M2M — with sharing semantics.
**UI support:** yes (`/workspace/knowledge`).
**Tests:** `apps/embeddings/tests/test_retrieval_privacy.py`,
`test_retrieval_isolation.py` (gate-blocking).
**Safe to reuse:** yes for facts; **not** a home for behavior — the
Character Voice / K2 leak class of bugs
(`feedback_character_voice_can_leak_into_k2.md`) means K2 must remain
factual-only.

**Known bleed implication.** Tulsi (3 chunks), TANK (22),
Riverstone (7), Hearth & Hollow (six 1-chunk docs), Surgo Automotive
Mike KB (16), Surgo Financing (5) — all cohabit `chriss-workspace`
with empty M2M; Patch/Rivet dialogue synthesis can (and does)
retrieve from any of them if the topic embedding is close.

---

## 7. WORKSPACES / TENANCY

**Model:** `Workspace` (`accounts/models.py:108–142`) — id (UUID),
name (≤120), slug (**globally unique**, ≤140), owner FK (PROTECT),
members M2M through `Membership`. `Membership.Role` enum:
`owner`|`admin`|`editor`|`viewer` (v1 uses `owner` only,
line 149–153). `default_workspace_for(user)` (line 176–188) declares
"v1 model: every user has one workspace they own."

**Scoping.** Every meaningful model carries mandatory `workspace` FK
with CASCADE (SESSION 259 audit table §1): Teammate, KnowledgeDocument,
CharacterIdentity, Asset, Composition, TranscriptHighlight, Script,
PersonalizedCampaign, PublishBundle, RealtimeSession,
EngineConnection.

**Classification: ACTIVE.** But semantically overloaded — see §11
special question. In today's shipped UI, one workspace serves as:

- **Tenant** (privacy boundary for isolation).
- **Universe / world** (all teammates cohabit; K2 shared by default).
- **Project** (all compositions/scripts/campaigns roll up here).
- **Studio** (asset library, publish bundles).

Operator has never intentionally created more than one; SPA has no
picker or creation UI (SESSION 259 audit §2).

**Versioned:** no.
**Workspace-scoped:** self.
**Character-scoped:** no.
**UI support:** creation exposed only via API (SESSION 259 §2);
sign-up literally says "One workspace per account."
**Tests:** `apps/accounts/tests/`.
**Safe to reuse:** yes — the invariants are strong. But do not
overload it with new semantic duties without acknowledging the
existing four-way overload.

---

## 8. RELATIONSHIPS

**Search performed:**

- Grep for class names containing `Relation`, `Relationship`,
  `Edge`, `Graph`, `Link`, `Bond`, `Trust`, `Affinity`, `Kinship`,
  `Family`, `Parent`, `Child`, `Sibling` — no character-to-character
  models found.
- Grep for FK / M2M patterns naming another Teammate:
  `from_teammate`, `to_teammate`, `parent_teammate`,
  `linked_teammate`, `related_teammate`, `creator_of` — no results
  in models (only in tests / synthesis strings).
- `CharacterIdentity.teammate` is the only FK from an identity model
  back to Teammate (`identity/models.py:116–128`); it identifies
  ownership, not relationship.
- No graph edge table exists in any app.

**Adjacencies that carry weak relational signal (but not typed
relationships):**

- `KnowledgeDocument.spokespeople` M2M (`embeddings/models.py:135–140`)
  — teammates who "know" a doc. Sharing semantic, not relational.
- Multi-character `dialogue_scene` recipe
  (`compositions/recipes.py:1480–1596`) — passes
  `primary_spokesperson_id` + `secondary_spokesperson_id` + a
  `lines` list at composition time. **No persisted relationship
  between the two** — it is a per-scene wiring only.
- `handoff_to_spokesperson` realtime tool
  (`apps/realtime/tools/handoff_to_teammate.py`) — suggests
  switching to a different teammate in the same workspace. No
  relationship model consulted.

**Classification: ABSENT.**

- There is **no substrate for "Patch created Rivet,"** "Rivet is
  Patch's apprentice," "Mike works for Surgo," or any typed
  character-to-character relationship.
- The dialogue prompt sometimes names other characters (SESSION 260
  test corpus mentions Patch/Rivet co-authoring turns), but this is
  free text inside the operator topic, not a persisted graph.

**Search performed to confirm absence:** grepped `shell/apps` for
class definitions matching every relationship word above; grepped
model files for `Teammate` FKs pointing to another Teammate;
inspected `identity/models.py` (no relational fields);
inspected `spokespeople/models.py` (no relational fields).

---

## 9. MEMORY / HISTORY / STATE

**Empty scaffolds.**

- `apps/memory/models.py` — **0 lines**. App registered
  (`apps/memory/apps.py:MemoryConfig`) but no models, no views
  (0-line `views.py`), no urls (0-line `urls.py`), no migrations
  beyond `__init__.py`.

**Actual memory-adjacent code.**

- **Conversation history:** `ConversationThread` +
  `ConversationMessage` + `ConversationEmbedding`
  (`conversations/models.py`). Thread FKs a Teammate. Messages carry
  role/content/verification. Embeddings enable RAG over past turns
  but live in a **separate table from KnowledgeChunk** so a
  workspace knowledge query cannot reach conversation content
  (contract rule 4).
- **Realtime cross-session memory projection:**
  `shell/character_os/realtime_memory.py` — reads prior
  `Asset(TRANSCRIPT)` rows attached to `RealtimeSession.transcript_asset`,
  summarizes via gpt-5 (`MEMORY_MODEL = "gpt-5"`,
  `MAX_OUTPUT_TOKENS = 400`, `reasoning_effort='low'`), projects into
  next session's Runway document (default 3 prior sessions). This
  is **transcript-summary projection, not persistent memory** — the
  summary is generated fresh at each session-create and written into
  the document body; nothing is stored.
- **Attach memory tool:** `apps/realtime/tools/attach_memory.py` —
  mid-session commit. Captures current session's transcript as
  `Asset(TRANSCRIPT)`, last-write-wins on
  `RealtimeSession.transcript_asset`. Q-r-8 resolution.
- **Session history:** `RealtimeSession`
  (`realtime/models.py:36–192`) has full lifecycle timestamps but
  no per-session narrative state, no "unresolved tasks / promises,"
  no relationship memory, no timeline.
- **Composition history:** `Composition` rows are per-render; there
  is no cross-composition "narrative state" concept.
- **`SESSION_259_OBSERVABILITY_BACKLOG.md`** documents that
  operator topic string, corrective-retry hints, per-attempt raw
  synthesis, first-pass char count, retry count, and retrieved
  chunk IDs on failed renders are all **not persisted**. Same-family
  gap.

**Classification: PARTIAL (conversation transcripts + projected
summaries) + ABSENT (persistent narrative memory).**

- The mechanism to represent "Rivet warned Patch in a prior episode
  and can say I told you so later" does **not exist**. There is no
  event log, no promise ledger, no relational memory store, no
  timeline model, no episodic marker. Dialogue synthesis has no
  concept of "prior scene" — each render is self-contained modulo
  K2 retrieval.
- The `memory` and `agents` apps are declared scaffolds that were
  never populated. Their existence is a Chesterton's fence: a
  reserved namespace where a real memory layer would go.

**Versioned:** no.
**Workspace-scoped:** conversation entities yes.
**Character-scoped:** conversation thread yes; realtime memory
projection yes (via spokesperson filter).
**UI support:** realtime session UI reads recent conversations;
no dedicated "memory browser."
**Tests:** `apps/realtime/tests/test_r6_session_memory.py`,
`test_r7_3_attach_memory.py`.
**Safe to reuse:** transcripts + summaries yes for continuity of
conversation. **Not sufficient** as an in-world memory substrate.

---

## 10. COMPOSITIONS / EPISODES

**Model:** `Composition` (`compositions/models.py:357–548`).

- Anchors: `workspace` (CASCADE, NOT NULL), `spokesperson` (SET_NULL).
- Identity: `name` (≤200), `template_kind` (free-text; values include
  `talking_head`, `talking_head_with_backdrop`, `long_form_ad`, etc.).
- State: `status` (`draft`|`planning`|`running`|`partial`|`completed`|
  `failed`), `error_message`.
- Deliverable: `final_asset` FK (SET_NULL) — always type `clip`.
- Knowledge log: `knowledge_chunk_ids` (JSONField list).
- Verifier output: `verification_status` (4-state enum),
  `verification_warnings`, `rejected_synthesis`.
- Synthesized artifact: `synthesized_brief` (populated on successful
  K6 renders; SESSION 168).
- Contract snapshot: `writing_contract_version` (SESSION 253) —
  positive int matches `WRITING_CONTRACT_VERSION` at synthesis time.
- Cost: `cost_estimate_micros`, `cost_actual_micros`.
- Ops: `mock_mode`, `created_by`, timestamps.

**Related:** `CompositionStep` (`compositions/models.py:551–711`) —
linear ordering, `(composition, position)` unique. Fields: `primitive`
(free-text, one of ~19 primitive names), `inputs` (JSON list),
`params` (JSON dict), `output_asset` FK, cost + telemetry,
`media_engine_task_id`.

**Is topic persisted?** **No.**
`SESSION_259_OBSERVABILITY_BACKLOG.md:37–46` confirms:
"Operator topic string (verbatim) — NO. Not on Composition; not on
any step. Inferable only from a truncated `name` prefix (~40 chars)
and only when the naming derives from topic vs opener."

**Does Composition contain enough metadata to serve as an Episode
record?** **No.**

- Missing: verbatim operator topic, recipe kwargs (raw), retrieved
  chunk IDs on rejection paths, per-attempt synthesis (first-pass
  vs corrective), retry count.
- Present: template_kind, writing_contract_version, verification
  triple, knowledge_chunk_ids on success, synthesized_brief on
  success, cost, timestamps.
- **No linkage to prior Compositions** — no `previous_composition`
  FK, no scene number, no episode ID, no arc grouping.

**Classification: PARTIAL.**
- Excellent single-render provenance shell.
- Missing multi-render narrative shape.
- Would need at minimum: `operator_topic` + per-attempt log +
  narrative linkage before it could serve as an Episode record.

**Versioned:** partially (writing_contract_version snapshotted).
**Workspace-scoped:** yes.
**Character-scoped:** yes (spokesperson FK).
**UI support:** yes (composition detail + gallery).
**Tests:** many under `apps/compositions/tests/`.
**Safe to reuse:** yes as a render-history primitive. Do not silently
promote to "episode" without observability additions.

---

## 11. ASSETS / PERSISTENT OBJECTS

**Model:** `Asset` (`compositions/models.py:132–354`) — 25 fields
covering both output media (clip/audio/image/transcript/voice) and
image-generation provenance (purpose/model/style_preset/prompt/
subject/negative_prompt/aspect_ratio/spokesperson).

- 12-value `AssetRole` enum (§2 above).
- `source_spec` (JSONField) — production-method provenance
  (`primitive`, `inputs`, `params`).
- Nullable `composition` FK (SET_NULL) — allows "library asset"
  reuse across compositions.

**Reusable assets:** yes — `composition=NULL` is the library case
(`compositions/models.py:230–241` docstring).

**Can Asset represent an in-world persistent object?**

- Not in the "in-world entity with recurring appearances across
  scenes" sense. Assets are output-media records + generation
  provenance. There is no `Asset.identity` / `Asset.entity_id` /
  `Asset.persistent_object_ref` field.
- The closest existing linkage: `Asset.spokesperson` (SET_NULL,
  `compositions/models.py:324–330`) — "the image was generated *for*
  a specific spokesperson."
- No "product catalog" model, no "entity catalog," no "object
  library." A recurring in-world object (Rivet's wrench, Patch's
  workbench) has no substrate today.

**Classification: ACTIVE for output media; ABSENT for in-world
objects/entities.**

**Versioned:** no.
**Workspace-scoped:** yes.
**Character-scoped:** optional (spokesperson FK SET_NULL).
**UI support:** yes (`/workspace/assets` per
`ASSET_LIBRARY_V1.md`).
**Tests:** many under `apps/compositions/tests/`.
**Safe to reuse:** yes as a media artifact. Wrong home for
persistent in-world objects — those need a distinct entity model.

---

## 12. LOCATIONS / SCENES / BACKGROUNDS

**Two distinct "backdrop" concepts exist in the codebase — and they
do not agree.**

### 12a. Substrate-side backdrop — normalization background

- `NormalizationManifest.background_id` (`identity/models.py:955–961`)
  — CharField(64), identifier from
  `docs/design/visual/portrait_qualification/schemas/background_family_v1.yaml`.
- Five round-one identifiers: `neutral_warm_studio`,
  `neutral_cool_studio`, `warm_material_surround`,
  `soft_environmental_depth`, `conversational_darker_surround`.
- Mapped from tonal environment class via
  `tonal_environment_class_default_background`
  (`background_family_v1.yaml:159–166`).
- `reviewer_override` allowed at benchmark time
  (`background_family_v1.yaml:168–184`).
- **This is a background REPLACEMENT for portrait normalization** —
  the background the identity's canonical portrait sits against
  (Portrait Language §8 same-room discipline). Not a rendering scene.
- Consumed by `media-engine/app/services/normalization/stages/background_replacement.py`.

### 12b. Composition-side backdrop — cinematic scene clip

- `Asset(role=BACKDROP)` (`compositions/models.py:AssetRole` line
  62–65).
- Produced by `generate_visual_clip` primitive
  (`compositions/primitives/visual_clip.py`) or picked from library
  via `talking_head_with_backdrop` recipe's `backdrop_clip_id`
  asset-picker field (`compositions/recipes.py:604–616`).
- Consumed by `composite_video` primitive layout kind `backdrop`
  (`compositions/primitives/composite_video.py:56` —
  `_VALID_LAYOUT_KINDS = {"pip", "backdrop", "cohost", "broll"}`).
- Recipes involved: `talking_head_with_backdrop`, `backdrop_layout`,
  `cohost_layout`, `pip_layout`, `broll_splice`.
- **This is a cinematic clip that plays behind a talking head** —
  a scene, not a normalized portrait background.

### 12c. Environment reference

- `IdentityReferenceKind.ENVIRONMENT_REFERENCE`
  (`identity/models.py:359`) — declared in the enum but "Only
  `portrait_reference` is exercised in round-one benchmark"
  (`identity/models.py:353–354`).

### Location / Scene / Set / Stage / Room?

Grep of `shell/apps` for class definitions matching
`Location|Scene|Backdrop|Background|Environment|Stage|Room|Set`
returns no character-scoped location model. Only:

- `background_family_v1.yaml` (5 identifiers — normalization scope
  only).
- `AssetRole.BACKDROP` enum value (composition scope).
- `ENVIRONMENT_REFERENCE` enum value (identity substrate, dormant).

**Classification:**
- 12a: ACTIVE but narrowly scoped (portrait normalization only, 5
  identifiers).
- 12b: ACTIVE for composition (arbitrary Runway-generated backdrop
  clips + operator library picks).
- 12c: DORMANT (declared enum value, unused).

**No substrate for a "location" / "recurring place" concept.**

- A recurring workshop (Patch/Rivet's shop) has no persistent identity
  today. Each `talking_head_with_backdrop` render either bakes a fresh
  Runway backdrop from a prompt or picks a library Asset — the "same
  workshop" reappearance is an operator-discipline convention, not a
  substrate guarantee.
- No `Location.name`, `Location.canonical_visual`,
  `Location.characters_present`, `Scene.location` — none exist.

**Versioned:** substrate side yes (via NormalizationManifest immutability);
composition side no.
**Workspace-scoped:** both yes.
**Character-scoped:** substrate side yes; composition side no —
`Asset(role=BACKDROP)` has no required teammate binding.
**UI support:** composition-side backdrop pickers in recipe forms;
substrate-side background is not operator-facing.
**Tests:** `apps/compositions/tests/test_v8_backdrop.py`,
`test_v16_remove_avatar_background.py`;
`media-engine/tests/normalization/test_background_replacement.py`.

---

## 13. CAST / GROUPING

**Search:**

- No `Cast` model (grep of `class \w*Cast\w*\(` returns only view /
  serializer / admin classes for other models).
- No `Team`, `Group`, `Roster`, `Ensemble`, `Collection` model.
- `generate_cast.py` (`apps/spokespeople/management/commands/generate_cast.py`)
  — utility command that generates portraits for four Character OS
  marketing cast members. Writes PNG to `shell/data/cast/`. Not a
  persisted grouping.
- `seed_cast.py` — bootstrap-fixture seeder for the demo/example cast.

**Multi-character configuration.**

- **Only in the `dialogue_scene` recipe**
  (`compositions/recipes.py:1480–1596`).
- Manual mode: `primary_spokesperson_id` + free-form `lines` list of
  `{spokesperson_id, text}`.
- AI Topic mode (SESSION 257): `primary_spokesperson_id` +
  `secondary_spokesperson_id` + `topic` + `target_duration_seconds` +
  `use_knowledge`. **Two characters only.**
- Custom resolver `_dialogue_resolver`
  (`compositions/recipes.py:271–355`) validates the primary/secondary
  pairing.
- Starter `dialogue_scene` (`compositions/starters.py:3325`) walks
  the lines and issues one `generate_avatar_speech` per turn.

**Persistent grouping across dialogue scenes?** **None.** Each
`dialogue_scene` composition specifies its cast independently; there
is no `Cast` row that says "Patch + Rivet always render together."

**Classification: PARTIAL for two-character composition;
ABSENT for N-character cast / group / ensemble at any layer.**

- `Membership` (`accounts/models.py:145–163`) groups **users** to a
  workspace with a role — not characters.
- `KnowledgeDocument.spokespeople` M2M groups **docs** to
  **characters** for visibility — not a cast primitive.
- No M2M `Teammate.related_teammates`, no through-model
  `CastMember`, no `Ensemble` row.

**Versioned:** n/a.
**Workspace-scoped:** dialogue recipe fields are per-render.
**Character-scoped:** per-render only.
**UI support:** dialogue recipe form (two-picker).
**Tests:** `apps/compositions/tests/test_v14_dialogue.py`,
`test_dialogue_ai_topic_wiring.py`,
`test_session260_dialogue_cps_calibration.py`.

---

## 14. VERSIONING

**Versioned concepts present:**

- `CharacterIdentityVersion` (`identity/models.py:174–334`) —
  full draft→approved→superseded lifecycle, monotonic revision,
  DB partial-unique on approved state, `spec_schema_version`
  distinguishes canonical vs legacy-unvalidated.
- `IdentityReference.state` — reference lifecycle with
  `SUPERSEDED` distinct from `REJECTED`
  (`identity/models.py:363–382`, §17.10.a Amendment 4).
- `ApprovedRepresentationBundle.state` — bundle lifecycle
  (draft/approved/superseded).
- `GenerationRecord` — append-only immutable evidence with `save`
  guard (`identity/models.py:852–867`).
- `NormalizationManifest` — append-only immutable, `pipeline_version`
  captured, `surface_profile_version` captured
  (`identity/models.py:891–1022`).
- `PromotionAudit` + `BootstrapEvidenceIndex`
  (`bootstrap_review/models.py`) — dedup + audit for §19 Step 9.b.3a.
- `Composition.writing_contract_version`
  (`compositions/models.py:487`) — snapshots K6 writing contract
  version at synthesis time. Positive integer, 0 = pre-contract.
- `PublishVariant.target_ratio` / `max_duration_ms` snapshotted at
  create time (Rule 7, `publish/models.py:198–204`).
- `Script.revision_history` — snapshot-on-regenerate JSON list
  (`scripts/models.py:151–153`).
- Recipe registry itself is code-versioned (not row-versioned) —
  `RECIPES` dict in `compositions/recipes.py:393`.
- Schema files: `background_family_v1.yaml` (schema_version=1),
  `human_identity_schema_v1.yaml` (schema_version=1),
  `purpose_schema_human_v1.yaml`, `non_human_test_schema_v1.yaml`.

**Mutable data currently lacking audit / version history:**

- **All Teammate fields** — `name`, `business_brief`, `personality`,
  `who_you_help`, `what_you_sell`, `always_emphasize`, `never_say`,
  `desired_feeling`, `tone_archetype`, `visual_subject`,
  `visual_template`, `character_point_of_view`, `voice_energy`,
  `voice_humor`, `voice_directness`, `voice_signature_phrases`,
  `voice_avoid_phrases`. Overwriting these silently loses history.
- Knowledge docs (only dedup by content_hash — edits create new docs,
  no version log).
- Realtime session `personality` field is derived at session-create
  from `Teammate.personality`; no snapshot of what was used.
- Recipe params on a Composition (`CompositionStep.params`) — SESSION
  259 observability backlog names this as a gap.

---

## 15. PROVENANCE / OBSERVABILITY

**Present.**

- `Composition.knowledge_chunk_ids` (list; empty on failure paths per
  observability backlog).
- `Composition.synthesized_brief` (SESSION 168 — final assembled
  scene text with metadata prefix).
- `Composition.rejected_synthesis` (K6.4 strict-mode rejection).
- `Composition.verification_status` + `verification_warnings` (K6.4
  v1.2 four-state — `verified` / `trusted_passthrough` / `skipped` /
  `rejected`).
- `Composition.writing_contract_version` (SESSION 253).
- `Composition.cost_estimate_micros` + `cost_actual_micros`.
- `Composition.mock_mode` boolean.
- `CompositionStep.cost_estimate_micros`, `.cost_actual_micros`,
  `.elapsed_ms`, `.media_engine_task_id`, `.error_message`.
- `Asset.source_spec` (JSON: primitive + inputs + params).
- `Asset.prompt` / `.subject` / `.negative_prompt` (for image assets).
- `GenerationRecord.prompt_snapshot`,
  `.seed_or_reproduction_data`, `.provider_model`,
  `.direction_hypothesis`, `.execution_mode`,
  `.execution_mode_actual`, `.elapsed_ms`.
- `NormalizationManifest.stages_executed`, `.stages_skipped`,
  `.eye_line_adjustments`, `.crop_metadata`,
  `.execution_duration_ms`.
- `ImportProvenance` + `PrequalificationProvenance`
  (`identity/models.py:1232+`) — origin evidence for identity versions.
- `RealtimeToolInvocation` (`realtime/models.py:195–314`) — full
  audit of tool calls per session, produced_asset / produced_composition
  linkage.
- `RealtimeSession.provider_session_id`, `.knowledge_chunk_ids`,
  cost + duration.

**Absent / gapped.**

- **No `LLMCallEvent` model, no `ToolCallRecord` beyond realtime
  tools, no cross-app call trace.** Grep of `LLMCall|ToolCall|LlmCall|CallEvent|CallRecord` returns no matches.
- **Composition observability gaps** documented at length in
  `handoffs/SESSION_259_OBSERVABILITY_BACKLOG.md`:
  - operator topic string not persisted.
  - Recipe kwargs (raw) not persisted.
  - First-pass synthesis (raw) not persisted (only rejected on failure).
  - Corrective retry hint not persisted.
  - Corrective retry output not persisted.
  - First-pass char count / predicted duration not persisted.
  - Retry-count field not present.
  - Retrieved chunk IDs on failed comps not persisted.
- No `topic` field on `Composition`. Only `name` (≤200) which
  sometimes truncates the first-turn opener.
- No first-pass vs corrective-pass persistence for either dialogue
  or talking-head synthesis.
- Ability to answer "why did this character say this?" is
  partial — you get the synthesized_brief + chunk IDs + verifier
  outcome on success, but not the operator topic, the recipe kwargs,
  or any first-pass evidence.

**Classification: PARTIAL.** Strong on structural provenance (workspace
scoping, cost, cross-workspace guards, immutable
GR/NM); weak on synthesis-time / attempt-level narrative.

---

## 16. EDUCATION / CURRICULUM / GOAL STRUCTURES

**Search:** grep of `shell/apps` for
`education|learning|curriculum|lesson|goal|objective|outcome`
returns only:

- Test filenames referencing dialogue objectives / verifier goals
  (calibration test naming; not models).
- `apps/compositions/primitives/avatar_speech.py` — inline docstring
  mentions of "goal" in the pacing calibration comments.
- `apps/compositions/script_splitter.py` — string mentions of "goal."
- `apps/scripts/models.py:71` — `WARNED` enum member (unrelated).
- `apps/bootstrap_review/*` — bootstrap-review "goal" naming for the
  identity qualification flow (not a curriculum model).

**Models with any of these words in the name:** **none.**

**Classification: ABSENT.**

No generic primitive represents `LearningObjective`, `Audience`,
`Purpose` (as a first-class thing distinct from `Charge` in the
IDENTITY_MODEL_V1 ontology draft), `Curriculum`, `Topic`,
`Goal`, `Outcome`, `Lesson`, `CampaignObjective`, `ContentObjective`.

- `PersonalizedCampaign` (`campaigns/models.py:44+`) is the closest
  "campaign" model but it is a **CSV-driven personalized-video batch
  send** — one template + N recipients — not a learning campaign
  with objectives.
- `Composition.template_kind` (free-text) is the closest "content
  type" hint but it names the render recipe, not a learning /
  curriculum objective.

The `IDENTITY_MODEL_V1.md` ontology draft names **Charge** as the CORE
dimension "what the creator is FOR" — this is close to a persistent
purpose concept but is design-only and unimplemented.

---

## 17. GENERIC PROJECT / UNIVERSE-LIKE CONTAINERS

**Search:** grep of `shell/apps` for class names matching
`Universe|World|Project|Campaign|Brand|Creator|Studio|Collection|Namespace|Container`
returns:

- `Workspace` (`accounts/models.py:108`) — see §7.
- `PersonalizedCampaign` (`campaigns/models.py:44`) — see §16;
  personalized-video batch container, not a project container.
- `PublishBundle` (`publish/models.py:37`) — one source clip → N
  platform variants; not a universe container.
- No `Project`, `Universe`, `World`, `Brand`, `Creator`, `Studio`,
  `Collection`, `Namespace` model.

**Design-doc references (not implementation):**

- `docs/design/CREATOR_CONTENT_STUDIO_V1.md` — Creator Content Studio
  concept; not implemented.
- `docs/design/BRAND_IDENTITY_V1.md` / `V2.md` / `V3.md` +
  `BRAND_ECOSYSTEM_V1.md` — brand palette CSS-var swap system;
  frontend token layer, not a container model.

**Classification: ABSENT (except Workspace).**

- Workspace is the only meaningful grouping layer in the shipped
  schema.
- Could Workspace become a Universe container? Structurally yes — it
  already carries teammates + knowledge + compositions + assets. But
  it currently ALSO plays tenant + project + studio roles (§7 + §11
  special question). Adding "universe" as a fifth semantic layer on
  Workspace risks worsening the overload.

---

## Classification lists

### A. EXISTS AND CAN PROBABLY BE REUSED

1. **Identity substrate** (`CharacterIdentity` + version + spec +
   references + bundle + provenance) — versioned, workspace-scoped,
   branch-neutral. Already decouples identity from representation
   from backdrop from knowledge.
2. **Workspace tenancy + cross-workspace isolation** — mandatory FK
   + defense-in-depth `clean()` + signals + `IsWorkspaceMember`
   permission class. Strong enough to underpin any future container
   layer.
3. **KnowledgeDocument + retrieval contract** — retrieval hard-scoped
   to `spokesperson.workspace`; conversation embeddings live in
   separate table; empty M2M semantics documented and enforced.
4. **Asset + AssetRole taxonomy** — 12-role enum, source_spec
   provenance, workspace-scoped, nullable composition FK for library
   reuse.
5. **GenerationRecord + NormalizationManifest** — append-only
   evidence with cross-workspace guards, `background_id` on manifest
   already proves backdrop can vary independently of identity at
   the normalization stage.
6. **ConversationThread + ConversationMessage + ConversationEmbedding**
   — full session persistence with separate embedding table.
7. **RealtimeSession + RealtimeToolInvocation** — full lifecycle +
   tool audit trail.
8. **Composition + CompositionStep** — render provenance shell;
   `writing_contract_version` snapshotted; `knowledge_chunk_ids`
   logged on success.

### B. EXISTS BUT NEEDS PRODUCT/UI SURFACING

1. **Multi-workspace support** — backend fully supports N workspaces
   per user; SPA has zero picker / creation UI (SESSION 259 audit §2).
2. **Per-teammate knowledge scoping at upload time** — API accepts
   `spokesperson_ids`; SPA upload form never sends it, silently
   defaulting to workspace-wide visibility.
3. **Identity substrate write path** — services layer complete
   (1959 lines); operator UI is only the bootstrap-review admin
   surface (not the regular teammate editor).
4. **Membership roles** — `admin` / `editor` / `viewer` enum
   scaffolded; v1 uses only `owner`.
5. **Direction hypothesis** — enum + benchmark harness surface;
   operator UI does not expose Portrait Language directions.
6. **Handoff between teammates** — realtime tool exists but no
   relationship or hand-off history is persisted.
7. **`ENVIRONMENT_REFERENCE` identity kind** — declared in the enum
   (`identity/models.py:359`); dormant — no purpose schema defined.

### C. EXISTS BUT IS THE WRONG SEMANTIC HOME

1. **Behavior stored in Teammate.personality (mutable)** — behavior
   is arguably an identity dimension (per `IDENTITY_MODEL_V1.md`
   §4.2 EXPRESSION) but lives outside the versioned identity
   substrate. Character Voice fields (POV, energy, humor,
   directness, signatures, avoids) are the same class — first-class
   identity content stored as mutable teammate columns.
2. **Character Voice fields sometimes end up in K2 knowledge**
   (`feedback_character_voice_can_leak_into_k2.md`, SESSION 259) —
   customers routinely paste voice guidance into K2 docs. K2 is a
   factual corpus, not a behavior home.
3. **Business brief fused with personality historically** (SESSION 175
   fix) — a prior split. The lesson generalizes: "context" is
   heterogenous (facts / brand / personality / POV / audience) and
   was previously conflated.
4. **"Backdrop" naming collision** — `NormalizationManifest.background_id`
   (identity normalization) vs `Asset(role=BACKDROP)` (composition
   scene clip). Two orthogonal concepts, one word.
5. **Workspace overloaded four ways** — tenant + universe + project
   + studio. Adding new duties to Workspace makes overload worse
   (§7, §17).
6. **`memory` and `agents` apps** — registered scaffolds; namespace
   reserved but empty. The reserved namespace is fine; keeping them
   empty while `realtime_memory` lives in `character_os/` and
   attach_memory lives in `realtime/tools/` fragments the memory
   concept across three homes.
7. **`Video` model** (`videos/models.py`) — legacy pre-Composition
   surface (design doc §4.4); every real render now runs through
   Composition. Video rows are backwards-compat shim. Do not add
   new work here.

### D. GENUINELY MISSING

Absent capabilities (search confirmed no candidate substrate exists):

1. **Character-to-character relationships.** No `Relationship` /
   `Edge` / `Bond` / `Kinship` / typed `Teammate → Teammate` FK / M2M
   model in any app. "Patch created Rivet," "Mike hired Repo Red,"
   "Penny mentors Ruby" — no substrate. Grep confirmed absence.
2. **Persistent narrative memory / event log.** `memory` app is a
   0-line scaffold. No event / promise / commitment / arc / episode-
   marker table anywhere. Realtime memory projection is transcript
   summarization only; nothing durable. Grep confirmed absence of
   `Memory`, `Event`, `Timeline`, `Episode` models.
3. **Location / Scene / Set / Environment as a persistent entity.**
   `background_family_v1.yaml` has 5 normalization identifiers;
   `Asset(role=BACKDROP)` carries scene clips. Neither is a
   persistent-place substrate. No `Location.name`, no
   `Scene.location_id`, no "recurring workshop." Grep confirmed
   absence.
4. **Cast / Ensemble / Group / Roster.** No N-character grouping
   model. Multi-character dialogue is a per-render two-picker
   configuration only. Grep confirmed absence.
5. **In-world persistent objects / entity catalog.** No
   `Entity` / `Object` / `Prop` / `Product` catalog model. Assets are
   output-media records. Grep confirmed absence.
6. **Universe / World / Project / Brand container above Workspace.**
   Workspace is the only container. Grep confirmed absence.
7. **Creator-role / narrative-role / business-role field on
   Teammate.** No `Teammate.role` distinction between
   "spokesperson," "character," "operator proxy." Charge from
   `IDENTITY_MODEL_V1.md` is design-only.
8. **Curriculum / LearningObjective / CampaignObjective /
   ContentObjective / Lesson / Goal / Outcome.** Grep confirmed
   absence.
9. **LLMCallEvent / ToolCallRecord (general-purpose observability).**
   Only realtime tool invocations are logged; K6/K9 synthesis calls,
   R6 memory calls, K6.4 verifier calls, embedding calls, image gen
   calls all persist their result in domain models (Composition,
   Script, KnowledgeChunk, Asset) but no call-event table exists.
10. **Composition observability primitives**
    (`operator_topic`, per-attempt log, first-pass raw synthesis on
    success paths, corrective-hint text, retrieval snapshot on
    failure) — documented at
    `handoffs/SESSION_259_OBSERVABILITY_BACKLOG.md`.
11. **Versioning of Teammate voice / context / behavior fields.**
    No `TeammateFieldVersion` / `PersonalityRevision` / voice
    snapshot on Composition. Overwrites are silent.
12. **Cross-composition narrative linkage.** No
    `Composition.previous_composition_id`,
    `Composition.scene_number`, `Composition.episode_id`,
    `Composition.arc_id`. Each render is self-contained.
13. **Relationship memory ("last time we spoke you were considering
    closing Tuesday").** Realtime memory is transcript-summary
    projection at session-create only. Relationship state does not
    persist between operator conversations or between characters.
14. **"Same character, different context" role-projection substrate.**
    IDENTITY_MODEL_V1.md §5 names Situational Role as a projection
    rule (`Relational disposition + current context → situational
    posture`). No implementation.

---

## Special questions

### 1. Can one existing character identity safely have multiple backgrounds today?

**Yes — at the normalization stage.** `NormalizationManifest.background_id`
(`identity/models.py:955–961`) is per-generation and can select any of
the five identifiers in `background_family_v1.yaml`, plus
`reviewer_override` allows any listed background. Multiple
`GenerationRecord` rows on the same identity version, each with a
different manifest and background_id, are structurally supported and
enforced by the append-only pipeline. **However** this is scoped to
portrait normalization for benchmark qualification — it is not the
same "backdrop" used by `talking_head_with_backdrop` composition
renders (which is an `Asset(role=BACKDROP)` clip, not a
normalization background).

### 2. Can one identity have multiple approved visual assets/variants without creating a new character?

**Yes.** `IdentityReference` allows multiple `(kind, purpose)` slots
on one `CharacterIdentityVersion`
(`identity/models.py:385–494`). Per human branch schema
(`human_identity_schema_v1.yaml:333–363`), Live_Conversation surface
requires seven reference-view purposes:
`portrait_reference/front`, `slight_left`, `slight_right`,
`neutral_rest`, `listening`, `consideration`, `gentle_positive`.
Multiple approved references coexist. Partial-unique
`one_approved_reference_per_slot` prevents more than one approved
per `(version, kind, purpose)` triple but supersedes cleanly.

### 3. Can the same character appear in multiple recurring "locations" today without losing identity continuity?

**Partially, and not through a substrate.** The identity substrate
does not know about locations. In the composition layer, a
`talking_head_with_backdrop` render can pick any
`Asset(role=BACKDROP)` clip — so operationally the same teammate can
render against many backdrops. But there is no "location" identity —
recurring the "same workshop" across many renders is an operator-
discipline convention (reuse the same `backdrop_clip_id`), not a
structural guarantee. Identity continuity is preserved because
identity and backdrop are independent axes; **location identity is
absent** because location is not a thing.

### 4. Is background actually independent from identity throughout the full render path, or only at one normalization stage?

**Independent at two layers, coupled only if the operator conflates
them.**
- Identity substrate side: yes — `background_id` on
  `NormalizationManifest` is orthogonal to the `spec` on
  `CharacterIdentityVersion`.
- Composition side: yes — `Asset(role=BACKDROP)` is picked or
  generated separately from the talking-head render; `composite_video`
  primitive composes them.
- The **normalization background** and the **composition backdrop**
  are two different concepts sharing the word "backdrop." Neither
  belongs on the identity; identity remains independent of both.

### 5. Is there already any dormant scene/location/environment abstraction?

**One dormant enum value.** `IdentityReferenceKind.ENVIRONMENT_REFERENCE`
(`identity/models.py:359`) — declared as a valid kind but no purpose
schema defines any purpose values for it; the docstring explicitly
says "Only `portrait_reference` is exercised in round-one benchmark"
(`identity/models.py:353–354`). No Django model uses it. Reserved
namespace; unimplemented.

### 6. Is CharacterIdentity capable of representing non-human characters like Patch and Rivet correctly, or are they using a different/legacy path?

**Substrate can accept non-human; Patch/Rivet do NOT use it.**

- `CharacterIdentity.kind` accepts `non_human`
  (`identity/models.py:106–108`).
- `non_human_test_schema_v1.yaml` is a **substrate exercise only**,
  explicitly marked non-canonical, `canonical: false`,
  `purpose_of_existence: substrate_exercise_only`
  (`non_human_test_schema_v1.yaml:40–46`), and is scheduled for
  deletion when Character Presence Language is authored
  (line 183–192).
- The `character_type` enum in that test schema is
  `animal|fictional_creature|stylized_object|other`.
- Patch (workshop mascot) and Rivet (Patch's creation) currently
  live as ordinary `Teammate` rows with `visual_template=mascot`,
  `visual_subject` = free-text creature description. Their identity
  substrate row (if any) would be `kind=non_human` schema-validated
  against the test schema, which is not intended as a durable home.
- The comfortable-reuse path is blocked: authoring canonical
  non-human identity requires Character Presence Language, which is
  not yet written.

### 7. Is there any existing relationship model we have overlooked?

**No.** Full search performed:

- Grep for class names matching `Relationship`, `Relation`, `Edge`,
  `Graph`, `Link`, `Bond`, `Trust`, `Affinity`, `Kinship`, `Family`,
  `Parent`, `Child`, `Sibling`, `Follows`, `Mentor`, `Apprentice` —
  no character-to-character models.
- Grep of every models.py for a FK/M2M whose target is `Teammate`
  (from another Teammate row) — only ownership/attachment FKs exist
  (`CharacterIdentity.teammate`, `KnowledgeDocument.spokespeople` M2M,
  `Composition.spokesperson`, `Asset.spokesperson`,
  `Script.spokesperson`, `PersonalizedCampaign.spokesperson`,
  `ConversationThread.spokesperson`, `RealtimeSession.spokesperson`,
  `Video.spokesperson`). None is a character-to-character link.
- `handoff_to_spokesperson` realtime tool exists but performs no
  persistence of the handoff event beyond the standard
  `RealtimeToolInvocation` audit row.

### 8. Is there any existing memory/history mechanism capable of representing: "Rivet warned Patch in a prior episode and can say I told you so later"?

**No.**

- The `memory` app is a 0-line scaffold; no models exist there.
- Conversation history (`ConversationMessage` + `ConversationEmbedding`)
  is per-thread, per-teammate — not per-character-pair, not per-arc.
- Realtime cross-session memory
  (`character_os/realtime_memory.py`) summarizes the current
  teammate's prior transcripts into the next session's document —
  it does not carry knowledge of another character's prior actions.
- No event log, no promise ledger, no arc / episode / scene sequence,
  no cross-character memory table.
- `Composition` rows are self-contained; no `previous_composition`
  linkage.
- The `attach_memory` tool captures a transcript snapshot but does
  not extract a structured commitment or warning.

**The substrate to represent inter-character narrative memory does
not exist today.**

### 9. Could Composition be evolved into an Episode concept, or would that be semantic misuse?

**Partial fit; would require additions.**

- Composition already carries workspace, spokesperson, template_kind,
  status, knowledge_chunk_ids, synthesized_brief, verification triple,
  writing_contract_version, mock_mode, cost triple. Enough shell for
  "a rendered scene lives here."
- Missing to be a real Episode: verbatim `operator_topic`, per-attempt
  log, retrieval snapshot on failure paths, corrective-hint,
  `previous_composition` / `scene_number` / `episode_id` /
  `arc_id`, cast list (currently only `spokesperson` FK), location
  reference, prior-episode references (call-backs).
- **Semantically compatible** — `template_kind='dialogue_scene'`
  already renders multi-character content into one Composition row.
  A future Episode concept could layer on top of Composition without
  displacing it. Evolving vs replacing is a design question this
  audit does not answer.

### 10. Is Workspace currently carrying too many meanings because the UI only exposes one workspace?

**Yes.** Workspace today serves as:

- **Tenant** (privacy boundary — cross-workspace isolation is a hard
  invariant asserted by `retrieve_for_teammate`, IdentityReference
  clean(), Composition clean(), RealtimeSession clean(), etc.).
- **Universe** (all characters cohabit; K2 shared by default via
  empty-M2M).
- **Project** (compositions, scripts, campaigns all roll up here).
- **Studio** (asset library, publish bundles, engine connections).

The single-workspace-per-user reality (SESSION 259 audit §3: 878 rows
total, 2 non-test workspaces, operator has always used exactly one)
means these four meanings are silently unified and never tested apart.
Introducing a second meaningful workspace (or a Universe grouping
layer) would expose which invariants belong on which axis.

### 11. Which current primitives would likely form the foundation of a future persistent world system if we built nothing new except a grouping layer?

**Load-bearing primitives already present.** If a grouping layer
(call it World / Universe / whatever) were added above Workspace,
the following primitives would slot in without needing invention:

1. **`CharacterIdentity` + version + spec** — the character substrate,
   ready.
2. **`ApprovedRepresentationBundle` + `CanonicalVoiceReference` +
   `CanonicalRealtimeReference` + `IdentityReference`** — the
   approved-representation substrate, ready.
3. **`KnowledgeDocument` + retrieval** — factual knowledge scoped
   per-teammate or workspace-wide, ready.
4. **`ConversationThread` + `ConversationMessage`** — per-character
   conversation persistence, ready.
5. **`RealtimeSession` + `RealtimeToolInvocation`** — live session
   history + tool audit, ready.
6. **`Composition` + `CompositionStep` + `Asset`** — render provenance
   shell, ready (needs observability additions to be Episode-shaped).
7. **`NormalizationManifest.background_id` +
   `background_family_v1.yaml`** — proof that "backdrop lives on the
   generation, not on identity" pattern is already substrate-legal.
8. **Workspace isolation invariants** — the guardrails that would
   also guard World/Universe rows structurally.

**Primitives that would need to be authored fresh** (from D above):
Character-to-character relationships, persistent narrative memory
beyond transcripts, Location/Scene/Set entity, Cast/Ensemble grouping,
in-world entity catalog, cross-composition linkage, versioned voice /
context fields.

**Existing brand palette / CSS-var swap** (`feedback_css_var_brand_swap.md`)
proves that per-workspace visual identity swap is already a
data-brand attribute flip, so a per-World palette would layer on the
existing pattern.

---

## Questions to answer BEFORE designing a Universe model

These ten questions surfaced from the audit and must be resolved
(operator-level intent) before any Universe / persistent-world schema
work begins. They are recorded here so the next session has the
decision surface in one place.

1. **Grouping layer position.** Does "Universe" sit *above* Workspace
   as a new grouping layer, or does it *replace / split* Workspace's
   four overloaded meanings (tenant + universe + project + studio)?

2. **Non-human canonicals.** Are non-human characters (Patch, Rivet)
   supported through the existing identity substrate, or does
   Character Presence Language / a non-human schema branch need to
   land before Universe work can proceed?

3. **Voice/POV ownership.** Does the identity substrate expand to own
   voice / POV / behavior fields (versioned), or do those stay on the
   mutable Teammate row and inherit their audit gap into the Universe
   era?

4. **Composition vs Episode.** Is `Composition` promoted to Episode
   (with additions like operator_topic, previous_composition,
   scene_number), or does Episode become a *new* model that wraps
   Composition without changing its shape?

5. **Relationship substrate location.** Where does character-to-
   character relationship live — a new `Relationship` model, an M2M
   on Teammate, or edges on a Universe graph?

6. **Location primitive shape.** Does Location get its own model, or
   does the existing `background_family_v1.yaml` + normalization
   `background_id` pattern extend into a workspace-scoped table?

7. **Narrative memory home.** Does persistent narrative memory reuse
   the dormant `apps/memory` scaffold, spawn under `character_os/`,
   or extend `RealtimeSession.realtime_memory` semantics?

8. **Cast representation.** Does cast become an M2M through-model on
   Universe, a per-Composition `cast_ids` list, or a first-class
   `Cast` row with its own lifecycle?

9. **Backdrop naming resolution.** Does the naming collision between
   `NormalizationManifest.background_id` (portrait normalization) and
   `Asset(role=BACKDROP)` (cinematic scene clip) get resolved before
   or after Universe lands? (If Location becomes an entity, this
   collision becomes three-way.)

10. **Tenancy vs world boundary.** Does Workspace remain the tenant
    boundary while Universe becomes the world boundary — and if so,
    which invariants (isolation checks, membership, retrieval scope)
    move to Universe and which stay on Workspace?

---

**STOP.** Read-only audit complete. Every claim above is cited to
file:line where non-trivial. No models, migrations, schemas, or
existing docs were modified. No architecture designed. No
implementation proposed.
