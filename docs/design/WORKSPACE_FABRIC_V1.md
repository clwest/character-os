---
title: "Workspace Fabric — scope lock"
status: active (scope-locked, no code yet)
generated: 2026-05-14 (SESSION 144)
companion_docs:
  - "UI_REDESIGN_V2.md"
  - "SPA_ARCHITECTURE.md"
  - "KNOWLEDGE_LAYER.md"
  - "VIDEO_COMPOSITION_V1.md"
  - "REALTIME_AVATAR_V1.md"
phase: 4
---

# Workspace Fabric

> **Read first:** `KNOWLEDGE_LAYER.md` (the prior scope-lock
> doc this one mirrors), `VIDEO_COMPOSITION_V1.md` §"Out of
> scope" (the V-arc closure that made this arc necessary),
> and `00-START-NEXT-SESSION.md` SESSION 144 entry.
>
> **Prior art:** None in the runway-hackathon predecessor —
> that app was a single-page render form. The fabric arc is
> the first architectural slice in this repo that doesn't
> port from u-d-b or runway-hackathon. It exists because of
> a product seam the operator named mid-V15.2.

---

## Purpose

The platform shipped three operator-facing sections across
SESSIONS 137-144: **Spokespeople** (the on-camera identities),
**Knowledge** (workspace docs informing renders), and
**Recipes** (the V15 gallery for creating compositions).
Each section works in isolation. They touch at narrow seams
— Knowledge attaches to Spokespeople via M2M, Spokesperson
FK flows into recipe params, K6's `build_render_brief` pulls
knowledge at render time inside `generate_avatar_speech` —
but the operator journey is still three separate tabs.

The fabric arc closes the gaps. After it ships, the operator
should experience one workspace, not three sections that
share a database. Concretely:

- From a spokesperson, you can answer "what can she do?"
  without context-switching to a different URL with no
  context bound.
- From a recipe form, you can answer "will this render
  actually use my knowledge docs?" before clicking submit.
- From a composition status page, you can answer "where did
  this base clip come from?" and "what knowledge fed this
  render?"
- From the dashboard, you can answer "what's my workspace
  doing right now?" without clicking into three sections to
  reconstruct the picture.

### Why scope-lock first

The fabric arc is the first arc that doesn't add
persistence. Every model it touches already exists. The
load-bearing question is **what cross-cuts are worth
showing** and which would be over-engineering. Without a
scope lock, the obvious failure mode is building a
spaghetti-merged super-dashboard that none of the three
underlying sections actually need. The lock keeps the
implementation honest: one operator journey per slice,
demonstrated against current data.

This doc plays the same role for the fabric arc that
`KNOWLEDGE_LAYER.md` plays for the knowledge arc and
`VIDEO_COMPOSITION_V1.md` plays for the video composition
arc — locks shape, not implementation.

### Provenance

The operator named this seam during SESSION 144 immediately
after V15.2 shipped:

> "Something we need to think about is at some point all
> three of the sections we have Spokespeople / Knowledge /
> Video recipes at some point are all going to need to be
> able to merge together if that makes sense."

The memory `project_workspace_fabric_merge.md` captured the
four sketch surfaces inline; this doc converts them into a
slice plan. The legacy `MakeVideoRoute` (S-12, retired-via-CTA
in V15.4 but file intact) is the canary use case the fabric
arc will retire-by-replacement.

---

## Contract rules (load-bearing)

These bind every fabric-arc slice the same way V0's nine
rules bind every composition slice.

1. **No new persistence in v1.** This arc adds zero models,
   zero migrations, zero new tables. Every fabric surface
   is a cross-cut of existing data (`Spokesperson`,
   `KnowledgeDocument`, `KnowledgeChunk`, `Composition`,
   `CompositionStep`, `Asset`). If a slice feels like it
   needs a new model, that's a sign we're solving the wrong
   problem at the wrong layer — kick it back to one of the
   producing arcs (K, V, R) instead.

2. **URL hints, not URL bindings.** Cross-section
   navigation passes hints via query params (e.g.
   `/recipes?spokesperson=<uuid>`) that the receiving
   surface honors but does not depend on. A form whose
   spokesperson dropdown is pre-bound by a hint must still
   accept the operator changing it. A hint never
   short-circuits server-side validation.

3. **Workspace stays the boundary.** Every fabric surface
   is workspace-scoped. The dashboard may eventually show
   "all my workspaces" once Membership across workspaces
   becomes common (agency tier, Phase 5), but per-workspace
   data never leaks across — even in the cross-cut shapes.

4. **Lineage surfaces are read-only.** "Used by" and
   "Derived from" panels show existing edges between assets
   and compositions; they never let operators create new
   edges or reroute existing ones. To use Asset Y as input
   for a new composition, operator opens the recipe gallery
   and picks Y in the asset_picker. Lineage is a view of
   the graph, not an editor.

5. **`/recipes` is the single canonical "make something"
   entry.** Spokesperson-detail CTAs, dashboard CTAs,
   onboarding walkthroughs — all converge to `/recipes` (or
   `/recipes/<kind>` with optional hints). No new
   "shortcut" entry points that fork the create flow. The
   legacy `/spokespeople/<id>/render` route exists only
   until F9 (legacy retirement); it does not get extended.

6. **Knowledge preview is best-effort.** The "would draw
   from N chunks" surface on recipe forms makes a real
   retrieval call against the K2 module. If retrieval is
   slow (>500ms), fails, or returns empty, the form still
   submits — preview is informative, not blocking. Render
   degradation (K0 rule 6) still applies at execute time.

7. **Cross-section navigation is stable after F2.** Once
   the persistent navigation rail ships (F2), the four
   top-level surfaces — Dashboard, Spokespeople, Knowledge,
   Recipes — are the operator's mental model. Adding a
   fifth top-level surface requires its own scope-lock
   event, not a fabric slice. This rule prevents nav
   churn that re-trains the operator with every release.

8. **Legacy retirement is the closing event, not a
   prerequisite.** The legacy single-form
   `/spokespeople/<id>/render` route + `MakeVideoRoute`
   component stay functional through F1-F8. F9 deletes
   them once the fabric surfaces fully cover the
   single-form use case. Deleting earlier creates a
   regression window; deleting later locks in technical
   debt. F9 is the explicit decision point.

9. **One operator journey per slice.** Every fabric slice
   delivers a single concrete journey the operator can
   walk through end-to-end, demonstrably better than what
   shipped before the slice. Composite slices ("F4 + F6
   land together as one PR") are out of scope — they
   smear the value question and make rollback expensive.

---

## Operator journeys (the merge)

The four sketch surfaces from the memory crystallize into
six distinct operator journeys, each becoming a slice.

### J1 — "What can Sasha do?"

Today: operator clicks a spokesperson → lands on
`/spokespeople/<id>` → clicks "Make a video" → lands on
`/recipes` with no spokesperson context → manually picks
Sasha in every form.

After F1: operator clicks a spokesperson → "Make a video" →
lands on `/recipes?spokesperson=<id>` → recipe gallery
unchanged, but every form pre-binds Sasha into the
`spokesperson_picker` field with the dropdown defaulted +
the option focused. Operator can change it; the URL hint
just sets the initial value.

Optional refinement (F1.5): the gallery itself filters /
re-orders cards based on which recipes meaningfully apply
to that spokesperson (e.g. demote layout recipes if the
spokesperson has no produced clips yet). v1 just pre-binds
the form; intelligent filtering is a v1.1 polish.

### J2 — "Where am I in the workspace?"

Today: the SPA has a knowledge link in the masthead and
hand-coded back-links inside each section. There is no
shared navigation that tells operator "you are here,
these are your other sections."

After F2: a persistent nav rail (left sidebar at >=md, top
bar at sm) shows Dashboard / Spokespeople / Knowledge /
Recipes as four sibling sections. The active section is
highlighted. The rail replaces the current ad-hoc
back-links + masthead links.

This is a UI scaffolding slice, not a feature. But until
it lands every other fabric surface feels bolted-on rather
than integrated, so it's a high-leverage early slice.

### J3 — "What is my workspace doing right now?"

Today: `/dashboard` shows three panels — primary CTA,
spokespeople grid, recent renders. Knowledge and
composition activity aren't surfaced at all.

After F3: the dashboard adds two cross-cut tiles:

- **Activity feed** — recent compositions (running +
  recently terminal) with status, recipe kind,
  spokesperson, cost-actual-micros. Replaces the existing
  "Recent renders" list with a richer one that handles
  composition + legacy Video rows together.
- **Knowledge corpus stats** — total docs, chunks, source
  mix (paste / PDF / URL / search), most recently
  ingested. Links to `/workspace/knowledge`.

The existing "Spokespeople" panel grows a small per-card
badge: how many compositions has this spokesperson driven,
how many docs are attached. Drilling in goes to the
spokesperson detail (existing route).

### J4 — "Will this render actually use my knowledge?"

Today: operators tick `use_knowledge` on four recipes
(talking_head, talking_head_with_backdrop,
talking_head_polished, long_form_ad). They get no
feedback about which docs would inform the render. The
K6 `knowledge_chunk_ids` field on the Composition row is
populated server-side but never shown.

After F4: when a recipe form has `use_knowledge` checked
**and** a spokesperson selected, an inline preview panel
shows "Would draw from: <doc A> (3 chunks), <doc B> (1
chunk)" — a live retrieval against the K2 module using
the script as the query. Panel updates as the operator
edits the script (debounced 500ms). Submit is unchanged.

This is the most technically interesting fabric slice —
it forces a synchronous retrieval call in a hot path the
SPA has never made. The implementation needs a new
read-only REST endpoint (`POST /api/knowledge/preview/`
with `{spokesperson, query}` → list of doc-level summaries)
that wraps `retrieve_for_spokesperson` without persisting
anything.

### J5 — "Where did this clip come from?"

Today: `/compositions/<id>` shows the step plan and final
asset. If a layout recipe picks `base_clip` from a prior
talking_head composition, that origin is invisible.

After F5: composition status page adds:

- **Derived from** chip — when any asset input was
  selected (not generated by an earlier step in the same
  composition), show the source composition link with its
  recipe kind.
- **Used by** panel on the final_asset section — list
  compositions that have used this asset as input. Empty
  state until V15 outputs accumulate.

Both surfaces query the existing `Asset.composition` FK +
`CompositionStep.inputs` JSON.

### J6 — "What knowledge fed this render?"

Today: `Composition.knowledge_chunk_ids` is populated by
K6 but the SPA shows nothing.

After F6: composition status page adds a "Knowledge"
section listing the source docs + chunks that fed the
render. Each entry: doc title, chunk count from that doc,
optional link to `/workspace/knowledge/<id>`. Empty when
the composition didn't use knowledge (no
`use_knowledge=True` step, or empty retrieval).

The reverse direction — `/workspace/knowledge/<id>` showing
"Used in N compositions" — lands as F7.

---

## Surface inventory — existing vs new

### Existing (no change in this arc)

| Surface | Status | Owner arc |
|---|---|---|
| `/dashboard` | ships | Phase 3 (S-09) |
| `/spokespeople/<id>` | ships | Phase 3 (S-10) |
| `/spokespeople/<id>/render` | ships (CTA retired V15.4; route intact) | Phase 3 (S-12) — retires at F9 |
| `/spokespeople/new` | ships | Phase 3 (W1-W11) |
| `/workspace/knowledge` | ships | K4 |
| `/workspace/knowledge/<id>` | ships | K4.1 |
| `/recipes` + `/recipes/<kind>` + `/compositions/<id>` | ships | V15.1-V15.4 |
| `/videos/<id>` | ships | Phase 3 (S-11) |
| `POST /api/compositions/` | ships | V15.0 |
| `GET /api/recipes/` | ships | V15.0 |
| `GET /api/assets/` | ships | V15.2 |

### New (this arc adds)

| Surface | Slice | Shape |
|---|---|---|
| Persistent nav rail | F2 | SPA component, not a route |
| `POST /api/knowledge/preview/` | F4 | New shell endpoint wrapping `retrieve_for_spokesperson` |
| `GET /api/compositions/<id>/lineage/` | F5 | Custom action returning "derived_from" + "used_by" |
| `GET /api/workspace/overview/` | F3 | Aggregate cross-cut shape (or a query-param on `/api/me/`) |

Three of the four new endpoints are read-only views over
existing data. None create new rows. Contract rule 1.

---

## Slice breakdown

Like the V-arc and K-arc, fabric is a sequence of
independently-shipping slices.

- **F0 — Scope lock (this doc).** No code. Shipped
  SESSION 144 (`825e0b9`).
- **F1 — Per-spokesperson recipe entry.** ✓ SHIPPED
  SESSION 144 (`3f9c057`). Spokesperson detail "Make a
  video" CTA → `/recipes?spokesperson=<id>`. Recipe
  gallery reads the hint, shows it in the header ("What
  can <name> do?" + a chip with a "clear" link), and
  passes it through to every card link. The form
  pre-binds the spokesperson_picker field (and
  `primary_spokesperson_id` for `dialogue_scene`) from
  the hint via a useEffect that fires once recipe
  metadata lands. Operator can still change the
  selection — the hint is the initial value only (F0
  contract rule 2). Cancel + "All recipes" back-links
  in the form preserve the hint so cancelling returns
  to the filtered gallery. New e2e spec covers the URL
  contract.
- **F2 — Persistent nav rail.** ✓ SHIPPED SESSION 144
  (`bcc8914`). Four-section sidebar (vertical at >=md,
  horizontal tab bar at sm) shipping in
  `web/src/components/nav-rail.tsx` and wired into
  `_layout.tsx`. Sections: Dashboard / Spokespeople /
  Knowledge / Recipes. Active section computed by
  pathname prefix; the matching is conservative so
  detail routes stay on their parent (e.g.
  `/spokespeople/<id>/...` highlights Spokespeople).
  Rail mounts only when authenticated + not on auth
  routes; auth pages stay minimal. Retired the ad-hoc
  Knowledge link from the dashboard masthead — the
  rail covers it. New e2e spec (`nav-rail.spec.ts`)
  asserts the four-item hard count + active highlight
  + auth-route hiding.
- **F3 — Workspace overview dashboard.** ✓ SHIPPED
  SESSION 144 (`59e5fdc`). New `GET /api/workspace/overview/`
  endpoint (`apps/accounts/views.py:workspace_overview`)
  returns one aggregate shape — spokespeople with
  composition + doc badges, knowledge corpus stats
  (counts, source mix, most recent), and recent
  compositions feed with cost. Chunk counting goes
  through a new sanctioned `count_chunks_for_workspace`
  in `apps/embeddings/retrieval.py` so K0 contract
  rule 2 stays intact. Dashboard SPA tiles:
  `ActivityFeedPanel` (replaces "Recent renders" with
  a unified composition feed; per-row link to
  `/compositions/<id>`) + `KnowledgeCorpusPanel`
  (counts, source mix, most-recent link) + per-card
  badges below each Spokesperson card. SpokespersonCard
  tightened to a squarer ratio (portrait switched from
  aspect-square to aspect-[4/3], padding p-6→p-5, brief
  line-clamp-2) per operator feedback that the cards
  looked too tall. +13 backend tests
  (`apps/accounts/tests/test_workspace_overview.py`).
  Dashboard e2e spec updated (videos-empty →
  activity-empty + knowledge-corpus zero state).
- **F4 — Knowledge preview on recipe forms.** ✓ SHIPPED
  SESSION 144 (`0122f26`). New
  `POST /api/knowledge/preview/` endpoint (custom action
  on `KnowledgeDocumentViewSet`) wraps
  `retrieve_for_spokesperson`, groups returned chunks by
  document, returns `{docs_used: [{id, title,
  chunk_count}], total_chunks, query_used,
  preview_failed?}`. Workspace-scoped via spokesperson's
  workspace + Membership check. Best-effort per F0
  contract rule 6 — retrieval failure becomes
  `preview_failed=true` + empty list, never an HTTP 500.

  SPA additions in
  `web/src/routes/recipes/$kind.tsx`:
  * `useDebounced` hook (500ms, Q-f-4).
  * `KnowledgePreviewPanel` rendered below the form's
    fields when `use_knowledge` is checked. Shows
    "would draw from N docs (M chunks)" with per-doc
    chunk counts. Empty-state messaging for the four
    transition cases (no spokesperson, no query yet,
    loading, no matches).
  * **Expanded F4 scope** added at operator's prompt: a
    "Knowledge mode" brief-mode helper text rendered
    under the primary textarea when `use_knowledge` is
    on. Explains explicitly that gpt-5-mini expands the
    input into a polished script — surfaces K6's
    already-shipped capability that the SPA had been
    hiding. New `briefModeHelper` prop on
    `FieldRenderer`.

  Original F4 scope was preview-only. The expansion
  (brief-mode helper + clearer field semantics)
  resolves a UX bug: operators were writing full
  scripts in a field whose value K6 was already
  treating as a brief. Operator caught this mid-F4
  scoping. The brief-mode helper is the structural
  fix; the preview panel makes the seam visible.

  +10 backend tests
  (`apps/embeddings/tests/test_preview.py`) covering
  auth gate, cross-workspace rejection, missing
  spokesperson/query 400s, empty-workspace zero
  shape, doc-grouping math, top_k clamp, workspace
  isolation, best-effort retrieval failure. SPA
  build green. 416 backend tests total.
- **F5 — Asset lineage on composition status.** ✓ SHIPPED
  SESSION 144 (`f50ba2b`). New
  `GET /api/compositions/<id>/lineage/` custom action.
  Returns `{composition_id, derived_from, used_by}`.
  * `derived_from` walks this composition's step inputs
    for `asset_id` references (excluding the same-comp
    `from_step_position` shape), resolves each to its
    producing composition, dedups by composition_id.
    One hop only per Q-f-5.
  * `used_by` scans `CompositionStep.inputs` JSON for
    substring matches on this composition's produced
    asset ids, filters to in-workspace consumers, dedups
    by composition_id. Caps to 100 candidates.
  Workspace scoping is structural — both queries filter
  through the workspace FK so cross-workspace lineage
  is impossible.

  SPA additions in `web/src/routes/compositions/$id.tsx`:
  * `useCompositionLineage` hook in
    `web/src/lib/api/recipes.ts` (alongside the existing
    composition hooks). staleTime 30s.
  * `DerivedFromPanel` — rendered above the step list
    when `derived_from` is non-empty. Each row is a
    link to the source composition with template_kind
    + asset_type + status badge.
  * `UsedByPanel` — rendered after the final asset when
    `used_by` is non-empty. Same row shape minus the
    asset metadata.
  Both panels hide entirely when their respective lists
  are empty (lineage is read-only and unobtrusive per
  F0 contract rule 4).

  +10 backend tests
  (`apps/compositions/tests/test_f5_lineage.py`)
  covering auth gate, cross-workspace 404, empty
  shape on standalone compositions, derived_from
  surfaces the parent, dedup when multiple assets
  share a parent, `from_step_position` is NOT
  treated as lineage, used_by surfaces consumers,
  dedup on multi-input consumers, multiple
  consumers, workspace isolation.

  426 backend tests total. SPA build green.
- **F6 — Knowledge citations on composition status.** ✓
  SHIPPED SESSION 144 (`7980de7`). No new endpoint —
  the existing `GET /api/compositions/<id>/` now resolves
  `knowledge_chunk_ids` server-side into a doc-level
  `knowledge_docs_used: [{id, title, chunk_count}]` field
  on the response (CompositionSerializer
  SerializerMethodField). Resolution flows through a new
  sanctioned `resolve_chunk_ids_to_docs(chunk_ids,
  workspace=...)` helper in
  `apps/embeddings/retrieval.py` so K0 contract rule 2
  stays intact. The resolver:
  * Dedups by document, ordered by first-occurrence
    (same shape as F4's preview).
  * Optional workspace filter is defense in depth —
    K6 only writes in-workspace chunk ids, but a stale
    foreign id in the JSON list would silently drop here
    instead of surfacing in another workspace's UI.
  * Stale chunk ids (deleted-since-render) silently
    drop without 500.
  SPA: new `CitationsPanel` rendered after the final
  asset on `/compositions/:id` (hidden when empty). Each
  row links to `/workspace/knowledge/<id>`.
  +5 backend tests
  (`apps/compositions/tests/test_f6_citations.py`)
  covering empty list, single-doc count, multi-doc
  ordering, stale-id resilience, workspace isolation.
  431 backend tests total. SPA build green.
- **F7 — Knowledge document → compositions reverse.** ✓
  SHIPPED SESSION 144 (`0b6be9d`). Scope-lock said
  "SPA-only" but the inverse query needed an endpoint —
  new `@action` `GET /api/knowledge/<id>/compositions/`
  on `KnowledgeDocumentViewSet`. Returns
  `{compositions: [{composition_id, composition_name,
  template_kind, status, spokesperson_name, created_at,
  chunk_count}]}` ordered newest first, capped 100.
  Implementation walks workspace compositions, intersects
  each one's `knowledge_chunk_ids` set with the doc's
  chunk ids (sourced via a new sanctioned
  `list_chunk_ids_for_document` helper in
  `apps/embeddings/retrieval.py` — K0 rule 2 stays
  intact). Python-side filter for v1 dataset sizes; a
  Postgres-native JSONB lookup is the upgrade once we
  outgrow it.

  SPA: new `useKnowledgeCompositions` hook +
  `UsedByCompositionsPanel` rendered below the chunks
  list on `/workspace/knowledge/:id`. Each row links to
  `/compositions/<id>` and shows the spokesperson +
  chunk_count from this doc. Panel hides when the doc
  has no consumers.

  Together with F6, the F7 panel closes the round-trip:
  a composition's status page shows which docs informed
  it (F6); each doc's detail page shows which renders
  drew from it (F7). Operator can navigate the
  knowledge ↔ composition graph in either direction
  without an audit query.

  +7 backend tests
  (`apps/embeddings/tests/test_f7_compositions_reverse.py`)
  covering auth gate, cross-workspace 404, unused-doc
  empty list, single-consumer surface, unrelated-comp
  exclusion, multi-consumer dedup, workspace
  isolation. 438 backend tests total. SPA build green.
- **F8 — Onboarding walkthrough (split).** ✓ SHIPPED
  SESSION 144 (`d23bc8c`). Scope-lock originally
  conflated the tour UI with the K10 seed corpus — per
  F0 rule 9 (one journey per slice) these are two
  journeys, and the seed corpus is operator-authored
  marketing copy that shouldn't be ghost-written. F8
  ships the tour only; F8.1 carries the seed.

  Tour shape: a state-derived dashboard banner
  (`web/src/components/onboarding-tour.tsx`) rather
  than a multi-step modal. The "current step" is
  computed from actual workspace data — first spokesperson
  missing → step 1, first knowledge doc missing →
  step 2, first composition missing → step 3, all set
  → banner hides silently. The operator can complete
  steps in any order or in another tab; the banner
  reflects the world.

  Steps:
    1. Create your first spokesperson → /spokespeople/new
    2. Add some knowledge → /workspace/knowledge
    3. Pick a recipe and render → /recipes
  Three steps, not four — "watch it render" isn't its
  own step because the operator is already on
  /compositions/<id> at that point. The terminal state
  is "everything set up; banner gone."

  Dismiss persists via localStorage (Q-f-6 resolved —
  v1 keeps it local, server-side dismiss is v1.1). The
  dismiss flag is permanent until the operator clears
  it (or another browser).

  Wired into `/dashboard` above PrimaryAction. The
  banner derives loading state from useMe +
  useSpokespeople + useWorkspaceOverview so it never
  flashes "Step 1" before the queries land.

  New e2e spec
  (`web/e2e/onboarding-tour.spec.ts`): fresh signup
  sees step 1, dismiss persists across reload, the
  step CTA navigates to /spokespeople/new.

  Test progression: 438 backend (unchanged — tour is
  SPA-only). SPA build green.

- **F8.1 — K10 seed corpus.** Queued — needs operator
  to author the curated docs in
  `docs/seeds/character_os/*.md` first. Once those
  land, F8.1 wires the migration (`Workspace.is_operator`
  bool), the seed Celery task, the post_save signal,
  and idempotency tests. The auto-ingested corpus
  fills the F8 banner's step-2 prerequisite for
  operator workspaces.
- **F9 — Legacy single-form deletion.** Delete
  `web/src/routes/spokespeople/render.tsx` +
  `/spokespeople/<id>/render` route. The legacy
  `/api/videos/` endpoint stays (V6 backwards-compat
  shim) because composition→Video sync rides through it;
  only the SPA surface is removed. The deletion is gated
  on F1 covering the use case + the operator confirming
  no external bookmarks point at the legacy URL.
- **F10 — Arc closure.** Summary + retro. Identify what
  the next arc should be (K-arc finish via K8-K10, R-arc
  start via R1, or Phase 5 agency-tier UI).

Roughly 10 slices, 4-6 sessions of work. F1 is the highest
single-slice leverage; F2 is the highest scaffolding
leverage; F4 is the highest "the platform feels smart"
leverage.

---

## Out of scope (explicitly)

- **New persistence.** Contract rule 1. Every fabric
  slice is a cross-cut of existing data. Adding models
  to support a fabric surface kicks the slice back to
  the producing arc.

- **Across-workspace surfaces.** No "all my workspaces"
  dashboard, no agency-tier consolidated views, no
  cross-workspace asset sharing. The Membership shape
  supports this; Phase 5 (agency tier) builds it. Fabric
  v1 stays single-workspace.

- **Composition editing.** Once a composition has been
  created, the fabric surfaces show its state but offer
  no edit affordances (re-order steps, swap inputs,
  re-run with different params). Composition is
  immutable in v1; "edit" means "create a new one." DAG
  editing is V0 §"Out of scope" — explicitly deferred.

- **Asset upload UI.** Workspace assets in v1 are
  produced by composition runs. The fabric arc does not
  add an upload endpoint, drag-drop surface, or import
  flow. Operators feed layout recipes with assets the
  recipes themselves produced. Asset upload is its own
  scope-lock event if/when it lands.

- **Search across surfaces.** No global search bar that
  hits docs + compositions + spokespeople. Each section
  has its own list view; the operator scans them. A
  unified search index is a v2 hardening; the fabric arc
  doesn't pre-bake it.

- **Real-time updates via WebSocket.** Dashboard tiles
  poll on TanStack Query intervals (existing pattern from
  K4 + V15.1). WebSocket / SSE arrives with the R-arc
  (realtime avatar) for conversation streams; the fabric
  surfaces don't pre-empt that decision.

- **Cost dashboards.** `Composition.cost_actual_micros`
  + `KnowledgeChunk.embedding_cost_micros` exist. The F3
  activity tile shows per-composition cost. A real cost
  dashboard (totals, projections, alerts) is out of
  scope; cost telemetry is K7.1's queued slice that
  belongs to a separate billing arc once it gets
  scoped.

- **Multi-user collaboration UI.** Workspace ownership +
  membership exist (`Membership.role`), but the fabric
  surfaces don't add presence indicators, locking,
  commenting, or multi-user awareness. v1 is
  single-operator per moment.

- **Recipe authoring UI.** Operators pick from the 18
  starter recipes. Authoring a new recipe via the SPA
  is V0 §"Out of scope" — fabric doesn't reopen it.

- **Spokesperson edit modal.** The queued "W11.1 —
  Edit-spokesperson modal" is its own slice in the
  Phase 3 backlog; fabric does not subsume it. The
  modal lands when scoped, independent of fabric.

---

## Open questions (resolve in implementation slices)

- **Q-f-1 — URL hint propagation across the gallery.**
  F1 sets `/recipes?spokesperson=<id>`. Does the gallery
  card link preserve it (e.g.
  `/recipes/talking_head?spokesperson=<id>`), or does the
  form re-read from the route's referrer? Cleanest is
  query-param propagation; resolve in F1 planning.

- **Q-f-2 — Nav rail layout breakpoints.** F2 picks a
  vertical sidebar at >=md and a horizontal tab bar at
  sm. Verify against the existing `_layout.tsx` width
  conventions. Resolve in F2 planning.

- **Q-f-3 — Activity feed unification.** F3 merges
  `Composition` rows and legacy `Video` rows into one
  activity stream. The V6 shim auto-creates a
  `talking_head` composition under every Video, so the
  duplication is real. Hide the Video shadow rows? Show
  only the composition? Pick in F3 — likely "show only
  the composition, the Video is an implementation
  detail."

- **Q-f-4 — Knowledge preview debounce.** F4's debounce
  defaults to 500ms but real retrieval latency varies
  (embedding + pgvector cosine). Tune in F4 — could be
  300ms or 1000ms depending on observed P50.

- **Q-f-5 — Lineage depth.** F5's "Derived from" can
  chain — composition C's base_clip is composition B's
  output, which is composition A's output. v1 shows
  one hop only (immediate parent). Resolve whether to
  show the chain or stop at one in F5.

- **Q-f-6 — Onboarding walkthrough trigger.** F8's tour
  could fire on first dashboard load, on first
  workspace creation, or only when invoked manually. v1
  default: first dashboard load + dismissible. Resolve
  in F8.

- **Q-f-7 — F9 deletion safety.** Before deleting
  `MakeVideoRoute`, audit external bookmarks (none
  currently — this is local-only — but the rule
  generalizes). Resolve at F9 planning.

---

## How to verify the merge

Before F8 closes, three operator scenarios should walk
end-to-end without context-switching:

1. **Fresh workspace → first render.** New user signs
   up → walks the F8 tour → first composition completes
   → status page shows the knowledge that fed it + the
   asset that produced it. Single coherent journey, no
   tab-switching.

2. **Returning operator → repeat workflow.** Operator
   on dashboard sees the activity feed → clicks a
   spokesperson card → picks a recipe → renders → all
   bindings carry through.

3. **Audit trail walk.** Operator clicks a composition
   from the activity feed → reads the knowledge
   citations → clicks a citation → lands on the
   knowledge doc → reads other compositions that used
   it → walks the asset lineage backward to its
   originating render. Read-only graph traversal across
   all three sections.

Each scenario is exercised as a playwright spec at the
matching slice. The first lands at F8; the second at
F3; the third at F7.

---

## Companion docs and where they intersect

- `KNOWLEDGE_LAYER.md` — F4 and F6 lean directly on K2's
  retrieval surface + K6's citation logging. No changes
  to either are needed; the fabric arc consumes them.
- `VIDEO_COMPOSITION_V1.md` — F1, F3, F5 lean on V0's
  Asset / Composition / CompositionStep models. No
  changes needed.
- `SPA_ARCHITECTURE.md` — F2 (nav rail) is the largest
  scaffolding change since the original SPA arc; the
  layout doc may need a follow-up note after F2 lands.
- `REALTIME_AVATAR_V1.md` — fabric arc and realtime arc
  are independent. R1+ slices can land in parallel with
  fabric slices. The conversation surface eventually
  added by K8/K9 may want a nav-rail tab after F2; that
  decision is K9's, not fabric's.

---

## Naming

Slices use the `F` prefix (Fabric). Files / commits /
handoffs / start-here entries follow the same convention
as K-slices and V-slices.

Working title for the arc is "workspace fabric." Internal
shorthand: "fabric arc." Operator-facing copy should not
use either name — the operator should experience one
workspace, not a "fabric." Internal naming is for slice
planning + commit messages only.

---

## Sign-off

This scope lock is the F0 slice. After it commits, F1 is
unblocked. Operator may direct any single-slice deviation
(e.g. "F2 before F1") in start-here updates; the
contract rules above stay binding either way.
