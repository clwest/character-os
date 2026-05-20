---
title: "Session 206 — E-arc Auto-Scripting shipped (scope lock + 5 implementation slices)"
date: 2026-05-20
status: complete
session: 206
previous_handoff: ./SESSION_205_D_ARC_LANDS.md
---

# Session 206 — B-2 / E-arc Auto-Scripting: lock + 5 of 7 slices

## TL;DR

Fifth strategic-axis arc. Scope-lock cadence held into a
**5-for-5** result (A/B/C/D/E arcs all opened + landed
in single-session blocks). Six commits this session:

* `47d73b1` — B2.0 scope lock
* `66068e8` — B2.1 model + migration + signal
* `b9e095a` — B2.2 synthesis module + revision helpers
* `e0f5139` — B2.3 REST + tier gate + auto_script starter
* `67f309d` — B2.4 recipe-gallery registration
* `a4bc3c9` — B2.5 SPA `/workspace/scripts` surface

**One slice remains** — B2.6 real-mode dogfood + arc close.
Pulled at operator request to avoid same-day fatigue on
real-mode validation; the prior arcs all left the dogfood
to its own focused block.

The arc lifts K6's in-primitive script synthesis into a
first-class persistent artifact with explicit operator
approval before render spend. Operator types a topic → K2
retrieves → gpt-5 drafts → K6.4 verifier runs → operator
reviews draft + cited chunks → operator approves → operator
fires `auto_script` Composition. **Renders cannot fire
without an approved Script.**

Tests at close: Django **1269 → 1320 (+51)**; SPA vitest
**371 → 405 (+34)**; media-engine unchanged at **214**.
Real-mode spend: **$0** (all force-mock + unit tests).

## Strategic framing

Closes the strategic-axis quartet:

* B-1 (transcripts, SESSION 202) — **mine** input
* **B-2 (auto-scripting, SESSION 206) — auto-script the output**
* B-3 (personalized, SESSION 203) — personalize per recipient
* B-14 (publish bundle, SESSION 205) — distribute

Operators previously had to manually write every script
that consumed their knowledge — the friction defeated the
"grounded in your knowledge" differentiator. B-2 removes
that friction; a draft fires from a typed topic and
operator approval, with citations and verifier flags
inline before any Runway spend.

## What landed

Six slices across the day:

### B2.0 — scope lock (`docs/design/AUTO_SCRIPTING_V1.md`)

Ten contract rules + seven implementation slices + 11 open
questions. Operator accepted as-proposed after one push-back
on premature sign-off framing (worth carrying — the
4-for-4 cadence biased the AI toward "lock now"; operator
recalibrated to "we're just getting started for the day").

Key contract rules:

1. **Spokesperson + workspace anchor.** K6 system prompt
   is heavily spokesperson-anchored — cross-spokesperson
   reuse rejected by construction; clone-to-edit is the
   escape valve.
2. **One named function for drafting.** All Script-row
   writes go through `apps.scripts.synthesis.draft_script`.
3. **Citations persist as first-class data.** Every Script
   row carries `knowledge_chunk_ids` for pre-render audit.
4. **K6.4 claim verifier runs on every draft.** Cheap
   rejection at $0.001 beats expensive rejection at $0.25.
5. **Drafts are cheap; renders gate behind explicit
   approval.** No auto-fire on approval — two-click is the
   safety gate.
6. Workspace-scoped end-to-end.
7. **No new primitives.** `auto_script` reuses
   `generate_avatar_speech` with `use_knowledge=False`
   (the draft IS already synthesized).
8. **Scripts are reusable within their spokesperson.**
9. **Empty knowledge degrades gracefully.**
10. **Approved-and-rendered Scripts are immutable.**

### B2.1 — `apps.scripts` Django app

* New app + `Script` model: UUID PK, FK Workspace +
  Spokesperson, prompt + opener + draft_text +
  knowledge_chunk_ids + verifier outputs +
  revision_history JSONField + state machine (DRAFT /
  READY / RENDERED / ARCHIVED).
* Migration `0001_initial` (migration count 51 → 52).
* Cross-workspace `pre_save` signal mirrors `apps.publish`
  + `apps.campaigns` shape.
* Admin registration.
* 9 model tests pin: cross-workspace rejection (clean +
  signal), enum coverage, JSON-default independence
  (regression guard for the bare-list Django footgun),
  revision_history round-trip.

### B2.2 — synthesis adapter over K6

* `apps.scripts.synthesis.draft_script(spokesperson, prompt,
  *, opener, verifier_mode) -> ScriptDraftResult` — thin
  Script-row-shaped adapter over K6's `build_render_brief`.
  Same K2 retrieve → gpt-5 → K6.4 pipeline; remapped result
  field names (brief → draft_text, chunk_ids →
  knowledge_chunk_ids).
* Strict-mode `ClaimVerifierError` caught + persisted as
  `verification_status='blocked'` instead of raising
  (rule 4 — operator sees flags + LLM output without firing
  a render).
* `snapshot_to_revision_history(script)` — chronological
  audit helper for B2.3's regenerate flow. Idempotent
  no-op on never-drafted rows.
* `apply_draft_to_script(script, result)` — convenience
  copier that explicitly does NOT touch `status` /
  `approved_at` (state machine owned by viewset per
  rule 10).
* 12 synthesis tests pin force-mock / empty-knowledge /
  strict-rejection / field-mapping / opener-propagation /
  snapshot semantics.
* **Zero K6 regressions** — `apps.videos.views` + the
  `generate_avatar_speech` primitive + V6 shim all
  unchanged. The new module wraps the existing
  `build_render_brief` callable rather than moving it.

### B2.3 — REST + tier gate + Composition starter

Largest backend slice. Three pieces in one commit:

**REST surface — `/api/scripts/`** with all 8 actions:

| Verb | Path | Behavior |
|---|---|---|
| POST | `/api/scripts/` | tier-gate + fire `draft_script` + persist |
| GET | `/api/scripts/` | workspace-scoped, filterable list |
| GET | `/api/scripts/<id>/` | detail + `cited_documents` resolved |
| POST | `/api/scripts/<id>/regenerate/` | snapshot + re-fire + READY→DRAFT |
| POST | `/api/scripts/<id>/approve/` | DRAFT→READY; refuses blocked verification |
| POST | `/api/scripts/<id>/render/` | fire `auto_script` Composition, Script→RENDERED |
| POST | `/api/scripts/<id>/clone/` | escape valve from RENDERED immutability |
| DELETE | `/api/scripts/<id>/` | refuses RENDERED |

**Billing surface — `drafts_per_month` tier gate (Q-e-9)**:

* `TIER_LIMITS` extended: Starter=10, Pro=100, Agency=None.
* `Subscription.drafts_per_month` property added.
* `check_drafts_per_month(workspace)` raises
  `TierLimitExceeded` with `code='draft_limit_reached'`.
* `Usage` dataclass + `get_usage()` extended; `drafts_used`
  counts both initial-create (via `Script.created_at` in
  period) AND each regenerate (via JSON `revision_history`
  ts filtering — Python iteration; v1 pragmatic).

**Composition wiring — `apps.compositions.starters.auto_script`**:

* Takes a Script row (status≥DRAFT, non-empty draft_text)
  + creates a one-step Composition with:
  * `template_kind="auto_script"`
  * step 0 = `generate_avatar_speech` with
    `script=draft_text`, `use_knowledge=False` (rule 7 —
    in-primitive K6 explicitly skipped because draft is
    already synthesized at draft-time)
  * `Composition.knowledge_chunk_ids` populated from
    Script's persisted chunks for F-arc brief-mode lineage
  * `synthesized_brief` + `verification_status` +
    `verification_warnings` carried from Script row

Plus a defense-in-depth UUID filter in
`ScriptDetailSerializer.cited_documents` so legacy / mock
fixtures with non-UUID chunk_ids don't 500 the detail
endpoint.

21 REST tests pin every action + tier gate + cross-
workspace isolation.

### B2.4 — recipe-gallery registration

* `auto_script` registered in `apps.compositions.recipes.RECIPES`
  with new `script_picker` form field type.
* `resolve_kwargs` extended to handle `script_picker` —
  workspace + `status=READY` filtered lookup. Raises
  `Script.DoesNotExist` on non-READY / cross-workspace /
  unknown ids (view layer turns into 400).
* Form metadata intentionally OMITS the talking_head
  recipe's `script` textarea, `spokesperson_id` picker, and
  `use_knowledge` checkbox — all three would dilute the
  load-bearing UX bet from rule 7 (Q-e-11).
* Recipe gallery count **19 → 20**.
* `auto_script_polished` + `auto_script_cinematic`
  variants deferred to v2 per scope-lock "if scope permits"
  hedge.
* 9 recipe tests pin registry shape, form-field
  constraints, `/api/recipes/` surface, `script_picker`
  resolution + cross-workspace + non-READY + unknown-id
  rejections.

### B2.5 — SPA `/workspace/scripts` (subagent)

Delivered via the `react-web-delivery` subagent against a
tight backend-contract brief.

* Three new routes (`/workspace/scripts` +
  `/workspace/scripts/new` + `/workspace/scripts/:id` —
  `/new` registers BEFORE the `:id` catch-all per the
  campaigns + bundles precedent).
* New `web/src/lib/api/scripts.ts` with Zod schemas + 8
  React Query hooks (`useScripts`, `useScript`,
  `useCreateScript`, `useRegenerateScript`,
  `useApproveScript`, `useRenderScript`, `useCloneScript`,
  `useDeleteScript`). All mutations invalidate every
  dependent query on success per the SESSION 203
  cache-invalidation calibration.
* Detail page renders brief panel + cited documents
  (linked to `/workspace/knowledge/:doc_id`) + verifier
  flags + status-dependent action toolbar + collapsible
  revision_history.
* Regenerate modal lets operator update prompt / opener /
  verifier_mode before re-firing.
* Recipe gallery picks up the new `auto_script` recipe via
  `LIVE_RECIPE_KINDS` extension + new `script_picker`
  form-field type. Empty-state hint ("Draft one at
  /workspace/scripts") when no READY scripts exist.
* 402 tier-exhaustion handling shows the suggested-tier
  upgrade copy inline (mirror of bundles.new tier-
  exhaustion pattern).
* 34 new vitest tests; SPA total **371 → 405**.
* `pnpm build` exit 0; bundle chunk-size warning is pre-
  existing advisory only.

## Tests at session close

| Suite | Count | Delta vs SESSION 205 |
|---|---|---|
| Django | **1320** | +51 |
| - apps.scripts.tests.test_models | 9 | new |
| - apps.scripts.tests.test_synthesis | 12 | new |
| - apps.scripts.tests.test_api | 21 | new |
| - apps.scripts.tests.test_recipe | 9 | new |
| - billing updates | 0 net | (existing tier-gate tests covered) |
| Media-engine | 214 | unchanged |
| SPA vitest | **405** | +34 |

Real-mode spend: **$0** (B2.6 dogfood is queued for next
session).

## Calibration moments worth carrying

**Two new TRUST_CALIBRATION entries (39 total)**:

1. **Scope-lock cadence is now 5-for-5.** Five strategic-
   axis arcs (A SESSIONS 185-192, B SESSION 202, C SESSION
   203, D SESSION 205, E SESSION 206) all opened + landed
   their implementation slices in single-session blocks.
   Pattern is no longer aspirational — it's the design
   default for any new strategic axis. Plan around: 8-10
   contract rules + 7-10 slices (¼ to 1 session each) +
   real-mode dogfood closing. The dogfood can ride into
   the next session when timing matters (today's call).

2. **K6 refactor via adapter pattern preserved zero
   regressions across an existing 600-test surface.** The
   E-arc's central technical question was "how do we add
   B-2's pre-render persistence without breaking K6's
   in-primitive synthesis?" The answer was the adapter
   pattern: `apps.scripts.synthesis.draft_script` calls
   `character_os.script_synthesis.build_render_brief`,
   then remaps the result shape. Both paths share the
   underlying machinery via call, not via shared mutable
   state. Result: 1320 Django tests pass; the existing
   K6 callers (`apps.compositions.primitives.avatar_speech`,
   `apps.videos.views`, V6 shim) are unchanged. **Pattern
   generalization**: when adding a new persistence layer
   over an existing operational function, the
   adapter-wraps-callable shape is strictly safer than
   move-and-shim. Move-and-shim invites import-path
   drift; adapter-wraps-callable preserves the original
   call graph by construction.

Also worth noting (no new entry, but reinforcement):

* **Operator pushback on "sign-off now" framing.** Early
  in the session the AI proposed locking the scope doc
  with sign-off language; the operator pushed back ("Why
  are you signing off we are just getting started for the
  day?"). The 4-for-4 cadence had biased the AI toward
  closure pressure. Calibration: cadence is *opportunity*,
  not *obligation*; let the operator set the lock cue.

## What's still queued

### B2.6 — real-mode dogfood (½ session)

The arc's closing slice. Plan:

1. Bring up the HARD REQUIREMENTS stack — Django dev
   server + SPA + Redis + Celery worker (with `.env`
   sourced) + media-engine.
2. **Restart Celery first** — this session committed
   `apps.compositions.starters.auto_script` + a new
   signal-related billing function. The SESSION 200
   pre-fire check applies.
3. Operator drives the SPA at `/workspace/scripts/new` —
   pick Marcus (has knowledge attached), type a topic
   ("teach Roman dates"), submit. AI tails Django + Celery
   + media-engine logs in parallel (human/AI testing
   split memory).
4. Review the draft + cited chunks in the detail page.
5. Approve. Render.
6. Validate: the rendered Asset's `source_spec.knowledge_chunk_ids`
   matches the Script's persisted chunks; the
   `Composition.synthesized_brief` matches the Script's
   `draft_text`; the F-arc brief-mode panel surfaces the
   right citations.
7. **Q-e-10 brief-mode display** validation — confirm the
   detail page's cited_documents links navigate correctly.

Real-mode cost target: **$0.25** (one `auto_script`
render against Marcus + Clara).

### Larger backlog (unchanged from SESSION 205)

* **Asset upload UI** (1-2 sessions) — operator-content
  bottleneck.
* **B-1 v2 slices** — external transcripts, batch mining,
  highlight chaining.
* **B-14 v2 `offset_x`** — ½ session; SESSION 205 dogfood
  finding.
* **B-3 ↔ B-14 composition** — Q-d-5.
* **B-2 ↔ B-3 composition** — Q-e-6 (Script becomes
  PersonalizedCampaign.template). Deferred from B2.0
  scope-lock.
* **B-2 ↔ R7 realtime tool** — Q-e-8 (mid-conversation
  `draft_script`). Deferred from B2.0 scope-lock.

### Architectural debt surfaced this session

* **`drafts_used` accounting via Python iteration over
  `revision_history` JSON.** Pragmatic v1 (O(scripts ×
  revisions) per workspace; bounded by Pro tier's 100
  drafts/month). If `drafts_per_month` becomes hot under
  Agency-tier traffic, denormalize via a `DraftEvent`
  table.

### `auto_script` variants queued (B-2 v2)

* `auto_script_polished` — wraps `talking_head_polished`
  starter.
* `auto_script_cinematic` — wraps `cinematic_visual`
  starter.

Both deferred per scope-lock rule 8 + "if scope permits"
hedge.

## Recommended next direction

The natural next move is **B2.6 — real-mode dogfood**.
Closes the arc, validates the lineage chunk_ids carry
through to the rendered Asset, and proves the cadence is
5-for-5 in the same shape as A/B/C/D.

After B2.6 closes, three candidates surface for the next
strategic-axis session:

1. **B-14 v2 `offset_x`** — ½ session; addresses SESSION
   205 dogfood finding while it's fresh. Lowest risk.
2. **Asset upload UI** — operator-content bottleneck;
   unblocks B-1 v2.
3. **B-2 ↔ B-3 composition** — Script becomes
   PersonalizedCampaign.template. Composes the just-shipped
   E-arc with the C-arc; might be the highest-leverage
   move per "composition is the moat" framing.

Operator picks.

## Pointer chain

* **Last commit:** `a4bc3c9` (B2.5).
* **Design lock:** `docs/design/AUTO_SCRIPTING_V1.md`
  (status: LOCKED, B2.0-B2.5 marked ✓ SHIPPED).
* **Start-here next session:** `00-START-NEXT-SESSION.md`
  — FIRST THING = B2.6 dogfood.
* **Inventory:** regenerated against `a4bc3c9`. Migration
  count 52; 8 Celery tasks (unchanged from SESSION 205);
  20 recipes in the gallery (19 + auto_script).
* **Open Q's not yet resolved:** all 11 (Q-e-1 through
  Q-e-11) resolved at B2.0 lock with their proposed
  defaults.
