---
title: "Auto-Scripting (B-2) — persistent K6-drafted scripts with operator approval before render spend"
status: locked
proposed: 2026-05-20 (SESSION 206, slice B2.0)
locked: 2026-05-20 (SESSION 206, slice B2.0)
closed: null
companion_docs:
  - CONTENT_FORMAT_BACKLOG.md
  - KNOWLEDGE_LAYER.md
  - VIDEO_COMPOSITION_V1.md
  - PERSONALIZED_VIDEO_V1.md
  - PUBLISH_BUNDLE_V1.md
---

# Auto-Scripting — knowledge-grounded drafts as a first-class artifact

> **Status: LOCKED (SESSION 206).** Fifth strategic-axis arc.
> Per `CONTENT_FORMAT_BACKLOG.md` §B-2: "removes the blank-page
> problem — the most defensible product story the platform has."
> Closes the strategic-axis quartet alongside B-1 (mine input)
> + B-3 (personalize) + B-14 (distribute). Ten contract rules;
> seven slices B2.0-B2.6. B2.1 (apps.scripts app + Script model)
> opens immediately after lock commit.

---

## TL;DR

K6 already runs LLM script synthesis grounded in K2 knowledge
chunks — but it fires **inside** the render primitive. The
operator types a brief, hits launch, and only sees what the
LLM produced *after* $0.25 of Runway spend has fired. There's
no pre-render preview, no approval gate, no way to iterate on
the script without re-baking, and no way to reuse a good
script across `talking_head` / `talking_head_polished` /
`cinematic_visual`.

**B-2 lifts script synthesis out of the render primitive and
into a first-class artifact.** Operator types a topic ("30s
about our new pricing") → K2 retrieves → gpt-5 drafts → K6.4
verifier runs → operator reviews the draft + cited chunks →
operator approves → operator separately fires `talking_head`.
**Renders cannot fire without an approved Script.** Iteration
is cheap (~$0.001 per regenerate); the expensive render gate
moves from "implicit after typing" to "explicit after
reviewing."

This arc ships:

1. **A `Script` model** persisting prompt, opener, draft text,
   citation chunk_ids, K6.4 verification status, revision
   history, and approval state. FK to spokesperson + workspace.
2. **A `draft_script` synthesis function** — refactored
   extraction of K6's `build_render_brief` into a callable
   that returns a draft instead of mutating a Composition.
3. **A `ScriptViewSet` REST surface** — create / list / detail /
   regenerate / approve / render / delete + tier-gated
   drafts/month + cross-workspace signal guard.
4. **An `auto_script` recipe** — reads an APPROVED Script and
   fires `talking_head` mechanics with the persisted brief +
   chunk_ids (bypassing K6's in-primitive synthesis because
   the script is already done).
5. **A SPA `/workspace/scripts` surface** — list + create +
   detail with side-by-side brief + cited chunks + regenerate
   + approve + render-now CTA.

Out of scope for v1: B-2 ↔ B-3 composition (Script becomes a
PersonalizedCampaign template); B-2 ↔ R7 realtime tool
(avatars invoking `draft_script` mid-conversation); cross-
spokesperson script reuse; multi-language drafts;
script-to-script chaining (sequel / series memory — covered
by §B-19 in the backlog).

---

## Why now

Five drivers converge:

1. **K6 already does the hard part.** `character_os.script_synthesis.build_render_brief`
   ships the full K2 retrieve → gpt-5 → K6.4 verifier
   pipeline. B-2 is refactor + persist + REST + recipe + SPA,
   not new LLM work. The K6.6 / K6.6.1 / W11.y calibrations
   (SESSION 168 / 171 / 175) bake in.
2. **Strategic quartet completion.** B-1 (SESSION 202) mines
   input. B-3 (SESSION 203) personalizes. B-14 (SESSION 205)
   distributes. **B-2 closes the missing axis** — auto-script
   the output. Operators currently still type every brief by
   hand; B-2 removes the blank-page friction that defeats the
   "grounded in your knowledge" differentiator.
3. **Approval pattern is proven.** R7.0 (SESSIONS 149-151)
   shipped AWAITING_APPROVAL state machine for tool
   invocations. B-1 (SESSION 202) shipped PENDING →
   APPROVED → RENDERED for highlights. Same shape applies
   directly here.
4. **K6.4 verifier exists.** Hallucination flags fire on every
   K6 synthesis today; the SESSION 158 Donny "trafilatura"
   incident motivated the verifier. Surfacing those flags
   pre-render (vs. on a rendered Asset) is the cheap win.
5. **Backlog priority.** §B-2 ranks fourth strategically in
   `CONTENT_FORMAT_BACKLOG.md` ("a close fourth — the single
   biggest reduction in blank-page friction"). The other
   three top axes have shipped.

---

## Contract rules (load-bearing)

Ten rules. None overlap V1's existing 22 + B-1's 8 + B-3's 9 +
D-arc's 8. B-2 rules become V1 rules 56-65 if a future V-arc
lock merges them; v1 keeps them on this doc.

1. **Scripts FK to spokesperson + workspace.** `Script.workspace`
   is required (DB-level NOT NULL). `Script.spokesperson` is
   required + must belong to the same workspace as the script.
   Cross-workspace refs rejected at clean() + pre_save signal.
   K6's system prompt is heavily spokesperson-anchored
   (tone_archetype + personality + business_brief) — reusing
   the same script under a different spokesperson would
   produce off-tone output. Mirrors K-arc rule 1 + V1 rule 1.

2. **Drafting flows through one named function.**
   `apps.scripts.synthesis.draft_script(spokesperson, prompt,
   *, opener=None) -> ScriptDraftResult`. Internally calls
   `retrieve_for_spokesperson` (K2 path, unchanged) → gpt-5
   Responses API → K6.4 verifier. No code outside that module
   calls the synthesis primitives directly. Mirrors K-arc
   rule 2.

3. **Citations persist as first-class data.** Every Script
   row stores `knowledge_chunk_ids: JSONField (list[str])` —
   the K2 chunks the most recent draft was grounded in. The
   SPA renders these inline with the draft so the operator
   can audit "this sentence ties to chunk #3" before
   approval. Empty list = K6 degraded-to-prompt path (no
   knowledge visible).

4. **K6.4 claim verifier runs on every draft.** Same shape as
   K6 today (warn mode default; strict / off via
   `settings.K6_CLAIM_VERIFIER_MODE`; per-script override
   landing in B2.3). Verifier flags surface on the Script
   row (`verification_status` + `verification_warnings`).
   Rejecting a hallucinated claim at $0.001 draft cost is
   strictly cheaper than rejecting on a rendered $0.25 Asset.

5. **Drafts are cheap; renders gate behind explicit approval.**
   `draft_script` fires synchronously on POST `/api/scripts/`
   (and on POST `/api/scripts/<id>/regenerate/`) without
   approval gates because the cost is ~$0.001. Firing a
   Composition off a Script requires (a) `Script.status ==
   READY` (operator approved) AND (b) an explicit POST to
   `/api/scripts/<id>/render/`. No auto-fire on approval.
   Mirrors B-1 rule 5 + R7.0 cost-threshold pattern.

6. **Workspace-scoped end-to-end.** Script + revision_history
   + Composition outputs all FK to the same workspace. Cross-
   workspace lookups rejected at clean() + pre_save signal.
   Mirrors V1 rule 1 + B-1 rule 2 + B-3 rule 3 + B-14 rule 2.

7. **No new primitives.** v1 reuses every K6 piece + every
   V-arc primitive. The `auto_script` recipe is the existing
   `talking_head` mechanics taking a Script-FK input instead
   of a free-form operator prompt. Composition step 0
   (`generate_avatar_speech`) receives `Script.draft_text`
   verbatim + `Script.knowledge_chunk_ids` for the asset's
   provenance field — **skipping** the in-primitive K6
   synthesis because the script is already drafted +
   verified.

8. **Scripts are reusable within their spokesperson.** Same
   approved Script can fire `auto_script` (talking_head),
   `auto_script_polished` (talking_head_polished), and
   `auto_script_cinematic` (cinematic_visual) variants — each
   produces a separate Composition + Asset, all pointing back
   to the same Script row. Reuse is per-spokesperson by rule
   1; cross-spokesperson reuse is structurally rejected.

9. **Empty knowledge degrades gracefully.** If
   `retrieve_for_spokesperson` returns no chunks (spokesperson
   has no docs, or M2M visibility excludes all docs),
   `draft_script` follows K6 contract rule 6 — operator's
   prompt flows through verbatim as the draft, `chunk_ids`
   empty, `used_knowledge=False`, no LLM call. Operator can
   still approve + render; the script just runs on the
   pre-knowledge path.

10. **Approved-and-rendered Scripts are immutable.** Once a
    Script row has fired at least one Composition (regardless
    of that Composition's status), the draft + prompt + opener
    fields become read-only. Operator can clone-to-edit
    (`POST /api/scripts/<id>/clone/`) but cannot mutate the
    original — audit trail. Status transitions only forward:
    DRAFT → READY → RENDERED → ARCHIVED. No re-enter previous
    states. Mirrors B-3 rule 6's "once launched, recipient
    cannot be edited."

---

## Data model additions

### `apps.scripts.models.Script`

New app, new table. Mirrors the PersonalizedCampaign /
PublishBundle pattern.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `workspace` | FK Workspace | rule 6 isolation |
| `spokesperson` | FK Spokesperson | rule 1; clean() enforces workspace match |
| `name` | CharField(120) | operator-supplied |
| `prompt` | TextField | operator's topic input (the RAG query + the topic) |
| `opener` | CharField(280, blank) | K6.6 pin — verbatim first line (optional) |
| `draft_text` | TextField | most recent synthesized brief (60-100 words) |
| `knowledge_chunk_ids` | JSONField (list[str]) | K2 chunks cited (rule 3) |
| `model` | CharField(40) | `gpt-5` / `gpt-5 (mock)` / `degraded` |
| `tokens_input` / `tokens_output` | PositiveInteger | provenance |
| `verification_status` | CharField(20) | from K6.4 — `verified` / `warned` / `skipped` / `blocked` |
| `verification_warnings` | JSONField (list[dict]) | K6.4 flag list |
| `verifier_mode` | CharField(10, blank) | per-script override of `K6_CLAIM_VERIFIER_MODE` (rule 4) |
| `revision_history` | JSONField (list[dict]) | prior drafts (rule 10 audit) |
| `status` | TextChoices | DRAFT / READY / RENDERED / ARCHIVED |
| `created_by` | FK User | |
| `created_at` / `updated_at` / `approved_at` | DateTime | `approved_at` set on DRAFT → READY transition |

Indexes:
- `(workspace, status)` — list view filter
- `(spokesperson, status)` — spokesperson-detail "scripts using this character" panel
- `(verification_status)` — admin filter for blocked / warned scripts

`revision_history` entry shape (one per regenerate):
```json
{
  "ts": "2026-05-20T15:04:21Z",
  "draft_text": "<prior draft>",
  "prompt": "<prior prompt if changed>",
  "opener": "<prior opener if changed>",
  "knowledge_chunk_ids": ["...", "..."],
  "model": "gpt-5",
  "verification_status": "warned",
  "tokens_input": 1240,
  "tokens_output": 380
}
```

Snapshot-on-regenerate; never mutated. The `revision_history`
list grows; the live `draft_text` / `knowledge_chunk_ids` /
etc. always reflect the most recent successful draft.

### Cross-workspace signal

Mirrors B-3 + B-14. Post-save on `Script`:
- `script.spokesperson.workspace == script.workspace` (else raise)

Post-save on the `auto_script` Composition output (extending
the existing signal infrastructure):
- `composition.script.workspace == composition.workspace` (else raise)

---

## New / extended endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/scripts/` | Body `{spokesperson_id, name, prompt, opener?, verifier_mode?}`. Creates the Script, fires `draft_script` synchronously, persists the result, returns the Script (status=DRAFT). |
| `GET` | `/api/scripts/` | List workspace scripts. Filterable: `?status=`, `?spokesperson=`, `?verification_status=`. |
| `GET` | `/api/scripts/<id>/` | Detail — draft_text + chunks resolved via `resolve_chunk_ids_to_docs` (so SPA shows "drew from doc A / doc B"). |
| `POST` | `/api/scripts/<id>/regenerate/` | Body `{prompt?, opener?, verifier_mode?}`. Snapshots current draft to `revision_history`, re-fires `draft_script`, persists. Refuses on status=RENDERED (rule 10). |
| `POST` | `/api/scripts/<id>/approve/` | Flip DRAFT → READY. Sets `approved_at`. No side effects (rule 5). Refuses if `verification_status=='blocked'` (strict mode rejected). |
| `POST` | `/api/scripts/<id>/render/` | Body `{recipe?='auto_script'}`. Requires status=READY. Creates an `auto_script` Composition (or chosen variant per rule 8), enqueues via `execute_composition.delay`. Flips Script status → RENDERED on first launch. |
| `POST` | `/api/scripts/<id>/clone/` | Rule 10 — produces a new DRAFT Script with the same prompt + opener + spokesperson, fresh draft fired. |
| `DELETE` | `/api/scripts/<id>/` | Cascade-safe: detaches from any Composition outputs (the Compositions stay; lineage breaks). Refuses on RENDERED (clone first, then archive). |

Tier gate (new):
- `apps.billing.services.check_drafts_per_month(workspace)`
- `TIER_LIMITS["*"]["drafts_per_month"]`: Starter=10, Pro=100,
  Agency=null (unlimited). Fires on POST `/api/scripts/` and
  `/regenerate/`. Each regenerate counts; revision_history
  snapshot doesn't.

---

## New recipe

### `auto_script`

| Field | Notes |
|---|---|
| `kind` | `auto_script` |
| `template_kind` on Composition | `auto_script` (counts against `videos_per_month` per SESSION 204's `get_usage()` — this IS a render, unlike B-14 variants) |
| Inputs | `script_id` (Script with status=READY) |
| Steps | step 0: `generate_avatar_speech` (passes `Script.draft_text` as the script + skips in-primitive K6); step 1: `generate_visual_clip` (existing talking_head step 1) |

The recipe is operator-facing in the recipe gallery — added
to `LIVE_RECIPE_KINDS`. Q-e-11 for confirmation. The forms
metadata exposes a Script picker instead of the free-form
prompt textarea (different from every other recipe).

The starter at `apps.compositions.starters.auto_script` takes
`(script, workspace, name=None)` and creates the 2-step
composition with `template_kind="auto_script"`. The script's
`draft_text` flows verbatim to step 0; the script's
`knowledge_chunk_ids` populate `Composition.knowledge_chunk_ids`
for lineage on the rendered Asset.

**Variants (rule 8) ship as separate recipe keys reading the
same Script row:**
- `auto_script` → talking_head mechanics
- `auto_script_polished` → talking_head_polished mechanics
- `auto_script_cinematic` → cinematic_visual mechanics

Variant proliferation deferred to B2.4 implementation —
v1 ships only `auto_script` (the talking_head variant). The
other two land in B2.4 if scope permits, otherwise queue as
v2.

---

## Slice breakdown (7 slices, B2.0-B2.6)

| # | Slice | Effort |
|---|---|---|
| **B2.0** | This scope-lock doc | ½ session (current) |
| **B2.1** ✓ SHIPPED | `apps.scripts` Django app + Script model + migration + cross-workspace signal + admin registration. 9 tests; Django 1269 → 1278. | ½ session |
| **B2.2** ✓ SHIPPED | `apps.scripts.synthesis.draft_script` adapter over K6's `build_render_brief` + `ScriptDraftResult` dataclass + `snapshot_to_revision_history` + `apply_draft_to_script` helpers. K6 in-primitive callers unchanged. Strict-mode `ClaimVerifierError` caught + persisted as `blocked` (rule 4). 12 tests; Django 1278 → 1290. | ½ session |
| **B2.3** ✓ SHIPPED | `ScriptViewSet` REST (8 actions) + `check_drafts_per_month` tier gate (Starter=10, Pro=100, Agency=∞) + `auto_script` Composition starter wiring. State machine enforced at viewset (DRAFT→READY→RENDERED + regenerate snaps READY→DRAFT). 21 REST tests; Django 1290 → 1311. | 1 session |
| **B2.4** ✓ SHIPPED | `auto_script` registered in `RECIPES` registry + new `script_picker` field type + `resolve_kwargs` extension. Surfaces in `/api/recipes/` gallery (count 19 → 20). `auto_script_polished` variant deferred to v2 per "if scope permits" hedge. 9 recipe tests; Django 1311 → 1320. | ½ session |
| **B2.5** ✓ SHIPPED | SPA `/workspace/scripts` list + create + detail (regenerate / approve / render / clone / delete) + recipe-gallery `script_picker` field type extension. Delivered via `react-web-delivery` subagent. SPA vitest 371 → 405. | 1 session |
| **B2.6** ✓ SHIPPED | Real-mode dogfood + arc close. Marcus + "Five Good Emperors" topic → Script `0f837a40-…` → Composition `fbfb8cf6-…` → Asset `62d8397c-…` (54.2s mp4, $0.25 actual = exactly the predicted cost). Lineage validated end-to-end: Script.draft_text ≡ Composition.synthesized_brief byte-identical; 5 chunk_ids match exactly; Composition status `trusted_passthrough` confirms rule 7 (no double K6 synthesis). One in-session bug-fix patch shipped (Script-detail verifier panel was gated on `status ∈ {warned, blocked}` and hid the 2 informational warnings K6 produces on `verified` status — now triggers on `warnings.length > 0` with three tone variants). Six v2 findings filed (cross-surface inconsistency on Composition detail page, `Curious?` false positive, Asset.spokesperson missing, Asset dimensions missing, cost_estimate_micros=0, source_spec chunk_ids indirection). Real-mode-finds-bugs streak: **7-for-7**. | ½ session |

**Total: ~4-5 sessions** matching the backlog estimate.
Smaller than C-arc (10 slices) because K6 already does the
synthesis + verifier work — B-2 is persist + REST + recipe +
UI orchestration on top.

---

## In-scope clarifications

* **K6's in-primitive synthesis stays.** `build_render_brief`
  is refactored into `draft_script` (B2.2) but K6 in-primitive
  callers (legacy `talking_head` with operator-typed prompt)
  continue to work unchanged. Existing renders don't break.
  Operators can opt into B-2's persist-and-approve flow OR
  continue with the implicit-K6 flow.

* **`auto_script` skips in-primitive K6.** The Composition
  starter populates `Composition.knowledge_chunk_ids` from
  the Script row at create time. The `generate_avatar_speech`
  primitive detects the populated field and skips the
  internal `build_render_brief` call — Script wins. No double
  synthesis.

* **`Script.draft_text` is the source of truth for the
  voiceover.** Step 0 sends it verbatim to Runway. No
  re-grounding, no re-verification at render time. K6.4 ran
  at draft time (rule 4).

* **Citation rendering.** Detail endpoint resolves chunk_ids
  via the existing `resolve_chunk_ids_to_docs` helper (added
  in F6). SPA shows "this script cites doc A (3 chunks) and
  doc B (1 chunk)" — same brief-mode UX as composition detail.

* **Tier counting.** Drafts/month counts both initial create
  AND regenerate. revision_history snapshots don't count.
  Renders count separately under `videos_per_month` per
  SESSION 204's migrated query.

---

## Out of scope (v1)

* **B-2 ↔ B-3 composition.** Script becomes a
  PersonalizedCampaign template (one-script-many-recipients).
  v2 axis — needs scope-lock around template-substitution at
  draft time vs. at render time.
* **B-2 ↔ R7 realtime tool.** `draft_script` invokable mid-
  conversation by the avatar. v2 axis — R7 tool catalog needs
  the integration + a script-preview surface for the
  conversation thread.
* **Cross-spokesperson script reuse.** Rule 1 forbids by
  construction. v2 if operator demand surfaces.
* **Multi-language drafts.** Single language per Script. V10's
  `dub_audio` covers translation post-render.
* **Script-to-script chaining** (sequel / series memory —
  Episode 7 references Episode 6). Covered by §B-19 in the
  backlog; separate arc.
* **External LLM models.** gpt-5 only in v1 (per K6's SESSION
  171 calibration). Anthropic Claude / others deferred until
  operator demand surfaces.
* **Operator-pinned chunks** ("always cite this chunk in
  every draft"). K2 retrieval is unconditional; pinning is a
  K10-adjacent feature.
* **Bulk regenerate** ("redraft all scripts that cite doc X
  after I re-uploaded doc X"). v2 axis — needs an embedding-
  invalidation surface that doesn't exist yet.
* **Variants beyond `auto_script_polished`.** `cinematic_visual`
  variant + other recipe mappings deferred to v2 unless B2.4
  scope permits.

---

## Open questions (resolve in slices)

* **Q-e-1**: App namespace — `apps.scripts` (new) or extend
  `apps.compositions`? **Proposed**: new `apps.scripts` app.
  Script is a pre-render artifact with its own lifecycle;
  compositions are render-time entities. Same separation
  rationale as B-3 (apps.campaigns) and B-14 (apps.publish).
  Resolve at B2.0 lock.

* **Q-e-2**: Script reusable across spokespeople? **Proposed**:
  NO. Rule 1 — K6 system prompt is spokesperson-anchored;
  cross-spokesperson reuse would produce off-tone scripts.
  Clone-to-edit pattern (rule 10) covers "I want a similar
  script for a different spokesperson." Resolve at B2.0 lock.

* **Q-e-3**: Auto-fire renders on approval, or two-click
  (approve → "render now")? **Proposed**: two-click. Rule 5
  + R7.0 pattern. The $0.25 render cost is well above R7.0's
  $0.05 threshold; explicit second action is the safety gate.
  Resolve at B2.0 lock.

* **Q-e-4**: Regeneration shape — overwrite draft + snapshot
  to history, or version-rows? **Proposed**: overwrite +
  `revision_history` JSONField. Same shape as
  `Composition.verification_warnings`. Cheaper schema; fewer
  joins. Resolve at B2.0 lock.

* **Q-e-5**: K6.4 verifier mode default for drafts?
  **Proposed**: inherit `settings.K6_CLAIM_VERIFIER_MODE`
  (which is "warn" by default). Per-script override via
  `verifier_mode` field on the Script row. Strict mode
  blocks approval (rule 4 — `verification_status=='blocked'`
  refuses approve). Resolve at B2.0 lock.

* **Q-e-6**: B-2 ↔ B-3 composition (Script becomes
  PersonalizedCampaign.template)? **Proposed**: v2 axis. v1
  ships Script → `auto_script` (single-recipient renders)
  only. B-3 keeps its existing `template_text` free-form
  shape. Resolve at B2.0 lock.

* **Q-e-7**: Does `auto_script` count against
  `videos_per_month`? **Proposed**: YES. This IS a render —
  unlike B-14 variants which are ffmpeg-only repackaging,
  `auto_script` fires Runway. Same `template_kind="auto_script"`
  marker but no SESSION 204 exclusion. Resolve at B2.0 lock.

* **Q-e-8**: R7 realtime tool (`draft_script` invokable
  mid-conversation)? **Proposed**: v2 axis. Composes
  naturally with R7's tool registry; needs conversation-
  thread approval surface that doesn't exist yet. Resolve at
  B2.0 lock.

* **Q-e-9**: Tier gates on drafts/month? **Proposed**:
  Starter=10, Pro=100, Agency=unlimited. LLM calls are
  cheap (~$0.001 each, ~$0.10/mo at the Pro cap) but
  unlimited drafting would invite abuse + degrade verifier
  signal. Each regenerate counts; clone counts the new
  Script's initial draft. Resolve at B2.0 lock.

* **Q-e-10**: Brief-mode display on Script detail (cited
  chunks expanded inline)? **Proposed**: YES. Same UX as
  F-arc's composition-detail brief mode. The "I can see what
  the LLM grounded in before approving" is the central UX
  promise of this arc. Resolve at B2.5.

* **Q-e-11**: Should `auto_script` appear in the `/recipes`
  SPA gallery? **Proposed**: YES, but with a special form
  shape — Script picker (workspace scripts filtered by
  status=READY) instead of the free-form prompt textarea.
  Unlike B-14's `publish_variant` (which was an internal-only
  recipe), `auto_script` is the operator's primary surface
  for B-2 rendering. Resolve at B2.4.

---

## Change log

* **2026-05-20 (SESSION 206, slice B2.0)** — Initial scope
  proposal. Fifth strategic-axis arc. Closes the quartet:
  B-1 (mine) + B-2 (script) + B-3 (personalize) + B-14
  (distribute). Per `CONTENT_FORMAT_BACKLOG.md` §B-2 ranking
  ("close fourth — biggest reduction in blank-page
  friction"). Ten contract rules; seven slices B2.0-B2.6.
  Eleven open questions all proposed with default
  resolutions; awaiting operator sign-off to lock.

* **2026-05-20 (SESSION 206, B2.0 LOCKED)** — Operator signed
  off as-proposed. All 10 contract rules accepted without
  revision. All 11 open questions accepted with proposed
  resolutions. Status flips proposed → locked. B2.1
  (`apps.scripts` app + Script model + migration + signal)
  opens immediately.

* **2026-05-20 (SESSION 206, B2.1 SHIPPED)** —
  `apps.scripts` Django app + Script model
  (DRAFT/READY/RENDERED/ARCHIVED state machine; rule-1
  cross-workspace clean() + pre_save signal; full
  provenance + revision_history JSONField; K6.4
  verification_status surface) + migration
  `0001_initial` + admin registration. 9 model tests pin
  cross-workspace rejection (clean + signal), enum
  coverage, JSON-default independence, revision_history
  round-trip. Django 1269 → 1278. INSTALLED_APPS extended.
  Inventory regenerated. B2.2 (refactor K6's
  `build_render_brief` → `apps.scripts.synthesis.draft_script`)
  opens next.

* **2026-05-20 (SESSION 206, B2.5 SHIPPED)** —
  SPA surface for the E-arc lands. Delivered via the
  `react-web-delivery` subagent against a tight backend-
  contract brief (8 REST actions + the new `script_picker`
  form-field type + the auto_script recipe gallery
  extension). Three new routes (`/workspace/scripts` +
  `/workspace/scripts/new` + `/workspace/scripts/:id` — `/new`
  registers BEFORE the `:id` catch-all per the campaigns +
  bundles precedent). New `web/src/lib/api/scripts.ts` with
  Zod schemas + 8 React Query hooks (`useScripts`,
  `useScript`, `useCreateScript`, `useRegenerateScript`,
  `useApproveScript`, `useRenderScript`, `useCloneScript`,
  `useDeleteScript`) all honoring the SESSION 203 calibration
  ("every dependent query must invalidate on mutation
  onSuccess"). Detail page renders the brief panel + cited
  documents (linked to `/workspace/knowledge/:doc_id`) +
  verifier flags + status-dependent action toolbar +
  collapsible revision_history. Regenerate modal lets
  operator update prompt / opener / verifier_mode before
  re-firing. Recipe gallery picks up the new `auto_script`
  recipe via `LIVE_RECIPE_KINDS` extension + new
  `script_picker` form-field type with empty-state hint
  ("Draft one at /workspace/scripts" when no READY scripts
  exist). 402 tier-exhaustion handling shows the suggested-
  tier upgrade copy inline (mirror of bundles.new tier-
  exhaustion pattern). 34 new vitest tests; SPA total
  371 → 405. `pnpm build` exit 0; bundle warning is pre-
  existing chunk-size advisory. **Five backend slices
  (B2.0-B2.4) + SPA slice (B2.5) shipped this session.**
  B2.6 (real-mode dogfood + arc close) opens next — fire
  draft_script against Marcus (existing dogfood spokesperson
  with knowledge attached), approve, render, validate the
  rendered Asset uses the persisted chunk_ids for lineage.

* **2026-05-20 (SESSION 206, B2.4 SHIPPED)** —
  `auto_script` registered in `apps.compositions.recipes.RECIPES`
  with the `script_picker` form field type (new, B-2 specific)
  + Q-e-11 resolved as-proposed. Recipe gallery count
  19 → 20. `resolve_kwargs` extended to handle the new field
  type — workspace + status=READY filtered lookup raises
  `Script.DoesNotExist` on non-READY / cross-workspace /
  unknown ids (view layer turns into 400). Form metadata
  intentionally OMITS the free-form `script` textarea, the
  `spokesperson_id` picker, and the `use_knowledge` checkbox —
  all three would dilute the load-bearing UX bet that
  auto_script is just "pick an approved Script, fire it" (per
  rule 7). The `auto_script_polished` variant deferred to v2
  per scope-lock "if scope permits, otherwise queue as v2";
  shipped scope is the base `auto_script` only. Updated 3
  V15 registry tests (19 → 20 + script_picker added to
  allowed-types vocab). 9 new recipe tests pin registry
  shape, form-field constraints, /api/recipes/ surface,
  script_picker resolution + cross-workspace + non-READY +
  unknown-id rejections. Django 1311 → 1320. B2.5 (SPA
  `/workspace/scripts` list + create + detail + regenerate +
  approve + render-now flow) opens next.

* **2026-05-20 (SESSION 206, B2.3 SHIPPED)** —
  `ScriptViewSet` REST surface ships all 8 actions:
  `create` (tier-gated draft fire) / `list` (workspace-
  scoped, filterable by `?status=` / `?spokesperson=` /
  `?verification_status=`) / `retrieve` (resolves chunk_ids
  → docs via F6's helper) / `regenerate` (snapshots +
  re-fires + READY→DRAFT step-back) / `approve` (DRAFT→
  READY, refuses on blocked verification per rule 4) /
  `render` (fires `auto_script` Composition via the new
  starter, flips Script→RENDERED, enqueues Celery) /
  `clone` (rule-10 escape valve from RENDERED
  immutability) / `destroy` (refuses RENDERED). New
  `check_drafts_per_month` billing gate (Starter=10,
  Pro=100, Agency=∞); counts both initial-create AND
  regenerate events (regenerates surface via revision_history
  ts filtering). New `apps.compositions.starters.auto_script`
  builds a one-step `generate_avatar_speech` Composition
  with `use_knowledge=False` (rule 7 — Script's draft is
  already synthesized; in-primitive K6 skipped via
  explicit False) + `Composition.knowledge_chunk_ids` +
  `synthesized_brief` populated from the Script row for
  F-arc brief-mode lineage. Defense-in-depth UUID filter
  in `ScriptDetailSerializer.cited_documents` so legacy
  seed / mock fixtures don't 500 the detail endpoint. 21
  REST tests pin every action + tier gate + cross-workspace
  isolation. Django 1290 → 1311. B2.4 (`auto_script`
  recipe gallery registration + variant recipes) opens
  next.

* **2026-05-20 (SESSION 206, B2.2 SHIPPED)** —
  `apps.scripts.synthesis` module ships rule-2's one
  named function: `draft_script(spokesperson, prompt, *,
  opener, verifier_mode) -> ScriptDraftResult`. Thin
  Script-row-shaped adapter over K6's
  `build_render_brief` — same K2 retrieve → gpt-5 →
  K6.4 pipeline, remapped field names (brief →
  draft_text, chunk_ids → knowledge_chunk_ids). Strict-
  mode `ClaimVerifierError` caught + persisted as
  `verification_status='blocked'` instead of raising
  (rule 4 — "cheaper rejection at $0.001 than at
  $0.25"). Plus `snapshot_to_revision_history(script)`
  for B2.3's regenerate flow (append-only audit; skips
  no-op on never-drafted rows) + `apply_draft_to_script
  (script, result)` convenience copier that explicitly
  does NOT touch `status` / `approved_at` (state machine
  owned by viewset). 12 synthesis tests pin force-mock /
  empty-knowledge / strict-rejection / field-mapping /
  opener-propagation / verifier-mode-propagation /
  snapshot semantics / apply semantics. Django 1278 →
  1290. Zero K6 regressions. B2.3 (`ScriptViewSet`
  REST: create / list / retrieve / regenerate / approve
  / render / clone / delete + tier gate) opens next.

* **2026-05-20 (SESSION 207, B2.6 SHIPPED — E-ARC
  CLOSES)** — Real-mode dogfood end-to-end against
  Marcus (Roman tutor spokesperson with 1 active
  knowledge doc — "Nerva–Antonine dynasty - Wikipedia",
  9 chunks). Topic: "explain the Five Good Emperors and
  why their reign is called the Antonine peace" — a
  knowledge-aligned happy-path test. Pipeline:
  `POST /api/scripts/` → Script `0f837a40-9226-4244-
  a743-067361cc2b93` (DRAFT, `verification_status=
  verified`, 5 chunks cited [0/3/4/5/6], 596 chars,
  gpt-5 1720+518 tokens). Operator Approve → READY
  (`approved_at` set). Operator Render → Composition
  `fbfb8cf6-5913-4cfe-9c30-abb56a7c0044` fires async
  via Celery. 76-second wall time for the
  `generate_avatar_speech` step polling Runway. Final
  Asset `62d8397c-cfbf-4477-84bb-d03f76df7ff8` — 54.2s
  mp4 at the predicted $0.25 actual cost (zero estimate
  deviation). **Lineage validated end-to-end**:
  Script.draft_text ≡ Composition.synthesized_brief
  byte-identical; chunk_ids match exactly (5/5);
  Composition.verification_status =
  `trusted_passthrough` confirms rule 7 holds (Script
  pre-synthesized → in-primitive K6 skipped). F-arc
  brief-mode panel on Composition detail surfaces
  citations correctly.

  **In-session bug-fix patch** (committed separately):
  Script-detail SPA verifier panel was gated on
  `verification_status ∈ {warned, blocked}` and hid
  the 2 informational warnings K6 produces on
  `verified` status. Patch relaxes the gate to
  `warnings.length > 0` and adds a third neutral
  `info` tone alongside existing `warned` (amber) +
  `blocked` (destructive). Heading text:
  "Verifier noted N informational flag(s)" instead
  of the alarm framing. ~15 LOC change to
  `web/src/routes/workspace/scripts.$id.tsx`.

  **Six v2 findings filed**:
  1. Cross-surface inconsistency — Composition detail
     page renders the same verifier_warnings JSON as
     "Warn — 2 flags" even though
     Composition.verification_status =
     `trusted_passthrough`. Same bug-class as the
     patched Script-detail page, opposite direction.
     Polish slice — ~10 LOC in
     `web/src/routes/compositions/$id.tsx`.
  2. K6.4 verifier false-positive: flagged `Curious?`
     as a `proper_noun`. Rhetorical English word, not
     a name. Upstream K6 issue, not B-2 surface.
  3. `Asset.spokesperson = None` — Marcus is not
     back-linked from the rendered Asset row. Lookups
     by spokesperson would miss this. Either
     `auto_script` starter should set it, or the
     downstream Asset-build path should propagate.
  4. `Asset.width / height / size_bytes = None` —
     Runway response fields not captured. Cosmetic;
     Asset Library may show "?×?" dimensions.
  5. `Composition.cost_estimate_micros = 0` —
     estimation didn't run for the `auto_script`
     starter. Actual was $0.25 so this didn't matter
     here, but other starters populate the estimate.
  6. `Asset.source_spec` doesn't carry
     `knowledge_chunk_ids` directly — lineage flows
     through `Asset → composition_id →
     Composition.knowledge_chunk_ids`. B2.6 plan in
     start-here said the chunk_ids would be on
     `source_spec` directly; actual architecture is
     cleaner (single source of truth on Composition)
     but the doc text needs aligning.

  **Two calibration findings** (separate TRUST_CALIBRATION
  entries):
  * Marcus avatar rig has a baked-in mouth/portrait
    quality issue ("noted as a bad image" — operator).
    Re-bake candidate. Matches the SESSION 158 pattern
    (avatar rig quality varies; some clips have
    artifacts at the portrait level vs. SESSION 158's
    voice-level mismatch).
  * **Real-mode-finds-bugs streak: 7-for-7.** Every
    dogfood across SESSIONS 195/197/200/202/203/205/
    **207** has surfaced at least one finding. Pattern
    is now the design default.

  **One verifier win**: K6.4 correctly flagged
  `Machiavelli and Gibbon` as `multi_word` — Gibbon is
  in chunk [7], but "Machiavelli" only appears in the
  Wikipedia source's bibliography (Strauss's *Thoughts
  on Machiavelli* — citation metadata, not substantive
  claim). The draft asserting Machiavelli "praised" the
  era is weakly grounded. Strict-mode verifier would
  have blocked at $0.001 cost; warn-mode let it ride
  and surfaced the flag for operator review. This is
  exactly the rule-4 promise working as designed.

  **E-ARC COMPLETE. Five strategic-axis arcs landed in
  consecutive scope-lock blocks** (A/B/C/D/E). Scope-
  lock cadence is now 5-for-5 + each closed with real-
  mode validation.
