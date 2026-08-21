# SESSION 277 — Operator Knowledge Dogfood (audit-only)

Fresh document. SESSION 276 is closed; audit history / evidence lives in
`SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md` and is not extended here.

## §1 Baseline (Slice 1 open)

- Working tree: clean.
- HEAD @ Slice 1 open: `b6989df` (docs: record Slice 21 FINAL landed SHA).
- `origin/main` == local HEAD.
- Substrate:
  - `KnowledgeDocument` = 0
  - `KnowledgeChunk` = 0
  - `embeddings_knowledgedocument_spokespeople` through-rows = 0
  - `embeddings_knowledgedocument.audience_scope` `is_nullable = NO`
  - CheckConstraints present: `session276_none_requires_inactive`,
    `session276_universe_requires_universe_fk`,
    `session276_workspace_forbids_universe_fk`
- Embeddings migration head: `0009_session276_final_delta_constraints` (applied).
- **Zero drift** vs. SESSION 276 §377 permanent-enforcement matrix / the SESSION 277 handoff §"Facts about the current substrate".

## §2 Handoff pointers (do-not-repeat)

- Delta model + invariants: `SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md` §46-§71, §51, §377.
- Serializer positive-audience guard: `shell/apps/embeddings/serializers.py` `KnowledgeDocumentSerializer.validate` (raises `audience_scope_required_on_create` on CREATE without positive signal).
- LIST predicate: `shell/apps/embeddings/views.py` `KnowledgeDocumentViewSet.get_queryset` (`?spokesperson=` branch — positive `audience_scope` `Q`-fan).
- SPA scope picker + payload helpers: `web/src/routes/workspace/knowledge.tsx` (`UniverseScopePicker`, `universeScopeToPayload`, `universeScopeToAudienceMarker`).
- Attach/detach control: `web/src/components/knowledge-panel.tsx`.
- `AudienceScope` enum: `shell/apps/embeddings/models.py` line 81 — `CHARACTER | UNIVERSE | WORKSPACE | NONE`.

## §3 Q-277-1

> Does the current Character OS Knowledge UI expose the permanent
> audience model clearly enough that an ordinary operator can
> intentionally create CHARACTER, UNIVERSE, or WORKSPACE knowledge
> without understanding Character OS's internal database/API semantics?

Companion:

> Is the UI currently presenting ingestion method (text/PDF/URL) as
> though it were the primary knowledge-creation decision while the
> more important audience/ownership decision is hidden, implicit,
> confusing, or separated from the operator's mental model?

## §4 Prediction (before inspection)

Operator observation says the visible creation surface reads as three
ingestion tabs (paste / upload / URL) with the audience decision
hidden or lexically drifted. Prediction: **Q-277-1 will be
falsified for CHARACTER** (no direct create path from the workspace
knowledge screen — CHARACTER audience is only reachable via a
post-hoc "Make X-only" gesture on the spokesperson detail page) and
**partially confirmed for UNIVERSE / WORKSPACE** (the picker exists
and is mandatory, but its label wording ("None (legacy — visible to
workspace-wide legacy teammates only)" as the positive
WORKSPACE gesture) obscures what the operator is choosing).

## §5 Investigation plan — checklist

- [x] STEP 0 — verify baseline (git + DB + migration).
- [x] STEP 1 — create this document.
- [x] STEP 2 — inventory operator-visible knowledge surfaces.
- [x] STEP 3 — reconstruct current operator flow (paste / PDF / URL / search).
- [x] STEP 4 — separate content / ingestion-method / audience / lifecycle dimensions.
- [x] STEP 5 — operator language audit.
- [x] STEP 6 — trace UI choice → API payload → persisted audience.
- [x] STEP 7 — `UniverseScopePicker` comprehension audit.
- [x] STEP 8 — Knowledge list / management "who knows this" audit.
- [x] STEP 9 — generalization specimens (bakery / dealership / cross-Universe policy).
- [x] STEP 10 — capability matrix (backend vs. UI vs. comprehension).
- [x] STEP 11 — page-count / flow-scatter audit (Knowledge only; Episode redesign out of scope).
- [x] STEP 12 — findings separated OBSERVED / SOURCE / OPERATOR / INFERENCE / HYPOTHESIS / PREFERENCE.
- [x] STEP 13 — smallest next falsifiable question.
- [ ] Commit + push audit doc; record SHA; verify clean pushed state.

## §6 STEP 2 — SPA knowledge-surface inventory

Every operator-facing surface that touches KnowledgeDocument state.

### §6.1 Global entry / discovery
- Persistent nav rail item **"Knowledge"** → `/workspace/knowledge` (`web/src/components/nav-rail.tsx:72-77`; F0 rule 7 authorized).
- Dashboard tile **"Knowledge"** (`KnowledgeCorpusPanel`, `web/src/routes/dashboard/index.tsx:549-652`) — shows `doc_count`, `chunk_count`, source-mix breakdown by `ingested_via`, most-recent link. Sibling **"Worlds"** link (line 587) is the sole Universe entry point.
- Onboarding tour "hasKnowledge" milestone → drives operator to `/workspace/knowledge`.

### §6.2 Create surface — `/workspace/knowledge`
Single page. File: `web/src/routes/workspace/knowledge.tsx`.
- Header (line 170-186): `"What your spokespeople know."` — descriptive.
- **`UploadPanel` (line 245-291)** — one shadcn `Tabs` control with four `TabsTrigger`s:
  - `Paste` → `PasteForm` (line 294)
  - `Upload PDF` → `UploadForm` (line 385)
  - `URL` → `UrlForm` (line 501)
  - `Search` → `SearchForm` (line 590; Serper-powered web-search → per-result "Ingest" button)
- Each form embeds `UniverseScopePicker` at the top (paste line 331, upload line 440, url line 534, search line 636) plus its own title / content / file / URL / query field. Submit is disabled until the picker is picked. All four submit shapes are identical wrt audience: `{ workspace, universe, audience_scope, title, <one of text_content|pdf_data_uri|source_url_input> }`.
- **`UniverseScopePicker` (line 50-101)** — `<Label>`: "World / Universe". `<select>` options: `"— Pick a scope —"` (disabled placeholder), `"None (legacy — visible to workspace-wide legacy teammates only)"`, then each Universe's `.name`. Helper text: `"Pick a world to scope this doc to that world's characters, or pick 'None (legacy)' to make it visible to legacy (pre-Universe) characters."`
- No spokesperson selector, no explicit "audience", no "workspace-wide" toggle.

### §6.3 Detail surface — `/workspace/knowledge/:id`
File: `web/src/routes/workspace/knowledge.$id.tsx`.
- Header: title + status pill.
- **`Metadata` table (line 189-256)** — rows shown to operator: `Type` (labelForType: Plain text / Markdown / PDF / Web page), `Ingested via` (labelForVia: Pasted / Uploaded / Web search / Seeded), `Chunks`, `Source URL`, `Hostname`, `Author`, `Date`, `Extracted (chars)`, `Fetched (chars)`, `PDF pages`, `Created`.
- **No audience / spokespeople / universe row exists in this table.** `universe` and `spokespeople` are in the payload (see `web/src/lib/api/knowledge.ts:59-60`) but never rendered.
- Actions: `Delete` (soft delete, chunks stay).
- `UsedByCompositionsPanel` (line 135) — shows compositions that referenced this doc's chunks (spokesperson name is exposed there, but as a byproduct of usage, not as a statement of assignment).

### §6.4 Character-scoped surface — spokesperson detail
File: `web/src/routes/spokespeople/$id.tsx:159-164` embeds `KnowledgePanel`.
File: `web/src/components/knowledge-panel.tsx` (K5).
- Header link: `"Manage workspace knowledge"` → `/workspace/knowledge`.
- Empty state: `"{Name} doesn't know anything yet"` + link back.
- Row copy (line 222-226):
  - `spokespeople.length === 0` → `"Visible to every spokesperson in the workspace"` (`data-visibility="workspace-wide"`).
  - non-empty M2M including this spokesperson → `"Attached to N spokespe{rson|ople}"` (`data-visibility="restricted-includes-me"`).
- Row action (line 232-256):
  - workspace-wide row → **`Make {Name}-only`** button (calls `attach`, tooltip `"Restrict to {Name} only"`).
  - restricted row → **`Detach`** button (backend rejects last-detach on active CHARACTER doc with the structured Slice 13 error, surfaced inline).
- **This is the only visible path that produces a doc whose backend `audience_scope` is `CHARACTER`.** The workspace create forms cannot originate one directly (they never send `spokesperson_ids`).

### §6.5 Universe-scoped surface — universe detail
File: `web/src/routes/workspace/universes.$id.tsx`.
- Section: `"Docs (N)"` (line 285-307) — filters `knowledge.data.filter(d => d.universe === id)`. Client-side: this **only** lists UNIVERSE-scoped docs by SPA filter, though the backend also supports `?universe=<uuid>` (see `views.py:121-126`). CHARACTER docs with `spokespeople.universe === id` and WORKSPACE docs are NOT shown here.
- No create form on this page — the operator returns to `/workspace/knowledge` and chooses that Universe in the picker.

### §6.6 Lifecycle / recovery
- Soft delete on both `/workspace/knowledge` row (line 762-772) and detail page (line 111-123).
- Empty confirm copy: `Delete "{title}"? Chunks stay searchable in admin only.` (no recovery UI in SPA per handoff §"Optional / non-blocking follow-ups").
- Hard-delete of docs: admin-only. Universes have a separate hard-delete path with an emptiness precheck (line 81-96 of `universes.$id.tsx`).
- `AudienceScope.NONE` (orphan/archived by spokesperson deletion) — no operator surface; excluded from LIST by `is_active=True` + no positive-audience `Q` branch (`views.py:94-96` fails closed).

## §7 STEP 3 — Reconstructed operator flows

Baseline flow lengths (post-login, workspace loaded).

### A. Paste text into knowledge
1. `/dashboard` → click `Knowledge` in nav rail (or Knowledge tile "View all").
2. `/workspace/knowledge` → default tab is `Paste`.
3. Fill picker (`World / Universe`) → pick Universe or "None (legacy…)".
4. Type title, paste content.
5. Click `Add to knowledge`.
6. Row appears in `Documents` list; polls at 3s until `processed`.

**Navigation steps to submit: 2 (dashboard → knowledge, then submit).**
**Audience-decision surface: 1 control (the picker), rendered above title.**

### B. Upload PDF
Same as A, tab `Upload PDF`, file input replaces text area (auto-fills title from filename). Same picker, same payload shape modulo `pdf_data_uri` in place of `text_content`. Same 2 navigation steps.

### C. URL ingest
Same as A, tab `URL`, `url` field required, `title` optional (defaults to page's title tag). Same picker, `source_url_input` in place of `text_content`. Same 2 navigation steps.

### D. Web search + ingest
Same as A, tab `Search`. Picker + Serper query field. Search returns snippet cards; each has an `Ingest` button that requires the picker be picked (`canIngest = universeScopePicked(scope)`). Each ingest is a separate CREATE. Same 2 navigation steps.

### E. Character-restricted creation
No direct path. The operator must:
1. Create a workspace-wide OR Universe-scoped doc via A / B / C / D above.
2. Navigate away from `/workspace/knowledge` → `/spokespeople/{id}` → find the `Knowledge` panel.
3. Locate the row (may need to know the title; no search here) → click `Make {Name}-only`.
4. If the operator wants MORE than one character on the same doc, repeat step 3 for each other spokesperson on their respective detail pages.

**Navigation steps to end at a CHARACTER-audience doc: 4-plus, spanning two unrelated screens.** Path is not signposted from `/workspace/knowledge`.

## §8 STEP 4 — Dimensional separation

Backend concepts:
- **CONTENT** — `text_content` / `pdf_data_uri` / `source_url_input` (mutually exclusive at CREATE).
- **INGESTION METHOD / SOURCE** — persisted as `document_type` (`text|markdown|pdf|url`) + `ingested_via` (`paste|upload|serper|seed`).
- **AUDIENCE / OWNERSHIP** — persisted as `audience_scope` (`character|universe|workspace|none`) + `universe_id` + M2M `spokespeople`. Delta invariants at `models.py:331-351`.
- **LIFECYCLE** — `is_active` + `deactivated_reason` (`OPERATOR_DELETE | ORPHAN_ARCHIVE`; `AudienceScope.NONE` is the fail-closed rest state for orphans).

Operator-visible surface today:
- CONTENT and INGESTION METHOD are **co-located and dominant**: the four `Tabs` at the top of `UploadPanel` bind ingestion method to the primary UI structure. Each tab's form fields are the CONTENT.
- AUDIENCE is exposed as **one** control (`UniverseScopePicker`), rendered inside each tab, with **two** apparent choices (a Universe from the list, or "None (legacy)"). CHARACTER is **not** an option here.
- LIFECYCLE is a delete button + a status pill; recovery of soft-deleted docs is admin-only.

The four dimensions are not visibly labeled as such. The picker collapses UNIVERSE and WORKSPACE into one selector; CHARACTER lives on another screen entirely.

## §9 STEP 5 — Operator language audit

Terms shipped to the operator today, verbatim:

| Term (surface) | Where | Backend meaning | Operator risk |
|---|---|---|---|
| `Knowledge` | nav / dashboard / route / headers | KnowledgeDocument corpus | Understandable — no exposed jargon. |
| `Universe` / `World` / `Worlds` | picker label ("World / Universe"), Universe tile, dashboard link | `Universe` FK on doc | Two synonyms in flight ("World" on the label, "Worlds" on the dashboard chip, "Universe" in the picker option list). Not obviously wrong but inconsistent. |
| `Scope` | picker helper text; placeholder `— Pick a scope —` | Reflects `audience_scope` | Correct engineering word, but "scope" without an object leaves the operator asking "scope of what?" |
| `None (legacy — visible to workspace-wide legacy teammates only)` | picker option that emits `audience_scope="workspace"` | Positive WORKSPACE marker | **The primary lexical drift.** The word "legacy" suggests deprecation; the operator would reasonably infer that picking this is a fallback, not the correct choice for workspace-shared knowledge. The parenthetical says the right thing but is buried in an option label. |
| `Visible to every spokesperson in the workspace` | knowledge-panel row copy for workspace-wide docs | Backend `audience_scope=WORKSPACE` (or empty-M2M pre-Delta) | Understandable — describes effective reach. |
| `Attached to N spokespe{rson\|ople}` | knowledge-panel row copy for restricted docs | `audience_scope=CHARACTER` with N in M2M | Understandable but does not name the invariant ("this doc will not be visible outside these characters"). |
| `Make {Name}-only` | knowledge-panel action to attach | Toggles to `audience_scope=CHARACTER` with M2M=[Name] | Understandable in isolation. Non-obvious that this changes the doc's audience contract for every future spokesperson in the workspace. |
| `Detach` | knowledge-panel action | Removes spokesperson from M2M | Understandable, but the failure ("cannot detach last spokesperson from a Character doc — decide audience first") comes through only after the click. |
| `Manage workspace knowledge` | link at top of KnowledgePanel | Navigate to `/workspace/knowledge` | Understandable. |
| `Spokespeople` | nav / dashboard / KnowledgePanel row copy | `Teammate` model | Consistent SPA-wide. |
| `Audience`, `Audience scope`, `Character-only`, `Universe-shared`, `Workspace-shared`, `Broadcast`, `Restricted` | — | The Delta model's own vocabulary | **None of these terms appear anywhere the operator can see.** The load-bearing product concept has no operator-facing name. |

## §10 STEP 6 — UI choice → API payload → persisted audience

All four ingestion tabs send the SAME audience shape. The only distinguishing field is the content payload.

| Operator gesture | SPA state | POST /api/knowledge/ body (audience-relevant fields) | Serializer branch | Persisted `audience_scope` | Persisted `universe_id` | Persisted M2M `spokespeople` |
|---|---|---|---|---|---|---|
| Picker set to a Universe UUID + paste/upload/url/search-ingest | `scope=<uuid>` | `universe=<uuid>` + `audience_scope` **omitted** | positive-audience branch: `universe not None` | `UNIVERSE` | `<uuid>` | `[]` |
| Picker set to "None (legacy)" + any ingest | `scope=UNIVERSE_LEGACY_SENTINEL` | `universe=null` + `audience_scope="workspace"` | positive-audience branch: `audience_scope_intent == "workspace"` | `WORKSPACE` | `null` | `[]` |
| Picker unpicked | disabled submit | — | — | — | — | — |
| (**Not reachable via workspace/knowledge**) | — | Would need `spokesperson_ids=[…]` in payload | positive-audience branch: `bool(spokespeople)` | `CHARACTER` | inherited from spokespeople (see serializer) | `[…]` |
| Post-create attach via KnowledgePanel `Make {Name}-only` | — | POST `/api/knowledge/{id}/attach/` `{spokesperson_id}` | attach action → transitions doc to `audience_scope=CHARACTER` via M2M change (see `views.py` `_toggle_spokesperson` / signals) | `CHARACTER` | pre-existing | pre-existing + `{sp}` |
| Post-create detach last spokesperson from CHARACTER doc | — | POST `/api/knowledge/{id}/detach/` `{spokesperson_id}` | Rejected 400 `final_character_detach_requires_audience_decision` | (unchanged) | (unchanged) | (unchanged) |

Two visually-similar gestures do **not** produce materially different audiences today — the picker is exhaustive at CREATE. The **inverse** IS true: materially different audiences (`WORKSPACE` vs. `UNIVERSE` vs. `CHARACTER`) appear visually similar on the KnowledgeDocument detail page (none of them surface `audience_scope`).

## §11 STEP 7 — `UniverseScopePicker` operator-comprehension audit

**Mechanical correctness** (SESSION 276 §Slice 12): confirmed. Every CREATE call site emits a positive marker; unpicked disables submit; three markers cover all three positive audiences the picker actually offers.

**Operator comprehension gaps:**
- Label: `"World / Universe"` reads as an ontology question ("what world does this belong to?"), not an audience question ("who can retrieve this?"). Correct as a UNIVERSE-picker; misleading as a WORKSPACE gesture.
- Option list mixes categories: N Universe rows + one `"None (legacy — visible to workspace-wide legacy teammates only)"` row. The word "legacy" is defensive engineering language — it signals "deprecated / bandaid" to almost any operator.
- The picker's helper text explicitly names workspace-visibility only for the legacy branch and only in terms of *"legacy (pre-Universe) characters"*, not "everyone in this workspace." An operator who has no legacy characters would reasonably infer that this option does nothing useful to them.
- The picker cannot express CHARACTER-audience intent. An operator who thinks *"only Ruby should know this recipe"* has no path from this screen.
- Placement is at the top of each tab (good — audience is picked first), but the picker is per-tab (four instances of the same widget). If the operator switches tabs mid-flow, the picker state resets to unpicked (each form owns its own `useState`, `knowledge.tsx:299,389,504,593`). Silent, not surfaced.

## §12 STEP 8 — Knowledge list / management — "who knows this?"

On `/workspace/knowledge` list row (`KnowledgeRow`, line 716-775):
- Shown: title, `labelForType(document_type)`, chunk count, `labelForIngestedVia(ingested_via)`, status pill, delete button.
- Not shown: `audience_scope`, `universe`, `spokespeople`, `is_active` (implicit — soft-deleted rows are excluded by LIST).

On `/workspace/knowledge/:id` detail (`Metadata`, line 189-256):
- Same absence — `universe` and `spokespeople` are in the schema (`api/knowledge.ts:59-60`) and reach the client, but no row of the metadata table renders them.

Consequence — an operator staring at either surface cannot answer:
- "Why does Ruby know this?" → No `spokespeople` list, no `universe` name, no `audience_scope` badge. The `Used by compositions` panel (detail page) exposes spokesperson names via *usage* history, but that's downstream of assignment, not a statement of it.
- "Who else can use this?" → Same gap. The operator would have to go to each spokesperson's KnowledgePanel and search for this doc.
- "Is this a workspace policy or a per-character note?" → Not visible from either surface.

The KnowledgePanel on `/spokespeople/{id}` *does* answer "who knows this" for the current spokesperson (workspace-wide vs. restricted), but only per-spokesperson; there is no global answer view.

## §13 STEP 9 — Generalization specimens

Test the current model against Chris's arbitrary future examples.

| # | Example | Achievable today? | How | Comprehension risk |
|---|---|---|---|---|
| A | Bakery recipe known only by Ruby | Yes, but indirect | Create workspace/Universe-wide via `/workspace/knowledge`, then `/spokespeople/ruby` → `Make Ruby-only`. | Operator has to know to leave the knowledge screen to restrict. |
| B | Recipe known by Ruby + one more bakery character | Yes, but indirect + repetitive | Same as A + navigate to the second spokesperson and attach. Two separate detail pages, two attaches, no bulk selector. | Same as A, plus operator must repeat per character. |
| C | Fox & Flour company policy shared across that Universe/business | Yes, direct | `/workspace/knowledge`, pick the Fox & Flour Universe, ingest. | UNIVERSE label is "World / Universe" — matches "Fox & Flour is a world." Reasonable. |
| D | Workspace-wide safety policy across every appropriate character | Yes, direct **but poorly signposted** | `/workspace/knowledge`, pick "None (legacy — visible to workspace-wide legacy teammates only)", ingest. | "Legacy" wording suggests operator is misusing the tool. Correct answer looks wrong. |
| E | Dealership financing expertise belonging only to one dealership character | Same as A. | Same. | Same. |
| F | Shared dealership policy for all characters in that dealership | Same as C, if the dealership is a Universe. | Same as C. | Same as C. |
| G | Second unrelated business in the same workspace that should NOT receive the dealership knowledge | Depends. If both businesses are Universes: pick the correct Universe on ingest and cross-Universe leak is impossible by design (per `universes.tsx:56-58` copy + backend `retrieve_for_teammate`). If one business is workspace-shared ("None (legacy)"), the OTHER business's characters *will* see it via the WORKSPACE `Q` branch (`views.py:109`). | High. An operator who picks "None (legacy)" for Business A's docs will unknowingly leak them to Business B, because WORKSPACE means "everyone in the workspace" — but the picker label doesn't say that. |

Verdict: the model generalizes for UNIVERSE-shaped businesses and single-character notes. It **does not** cleanly generalize for the workspace-wide policy case, and the CHARACTER case is achievable but operator-hostile.

## §14 STEP 10 — Capability matrix

| Capability | Backend supports | UI exposes at CREATE | UI exposes post-CREATE | Operator meaning clear | Gap |
|---|---|---|---|---|---|
| CHARACTER single-assignment | Yes | **No** (workspace/knowledge picker has no character slot) | Yes (KnowledgePanel `Make X-only`) | Partial | No signposted create path from Knowledge screen. |
| CHARACTER multi-assignment | Yes (M2M) | No | Yes but one-at-a-time, per-spokesperson-page | No | No bulk attach; operator visits N detail pages. |
| UNIVERSE-shared | Yes | Yes (pick Universe from picker) | Yes (Universe detail Docs section shows `d.universe === id`) | Yes, if operator understands "World" == "Universe" | Label uses two words ("World / Universe"); consistent enough. |
| WORKSPACE-shared | Yes | Yes (pick "None (legacy)") | Row copy in KnowledgePanel: "Visible to every spokesperson in the workspace" | **No** — the CREATE gesture is labeled "None (legacy)". | Lexical drift between correct-choice-at-CREATE and correct-description-at-VIEW. |
| Text ingest | Yes | Yes (Paste tab) | Shown in Metadata `Type: Plain text/Markdown` + `Ingested via: Pasted` | Yes | — |
| PDF ingest | Yes | Yes (Upload PDF tab) | Shown in Metadata | Yes | — |
| URL ingest | Yes | Yes (URL tab, and Search → Ingest) | Shown in Metadata + Source URL clickable | Yes | K7 known silent-failure on some URL hosts (memory `project_youtube_ingest_silent_failure.md`) — out of scope for this slice. |
| Current audience visibility on list rows | Data present in payload | — | **No** — list row shows title / type / chunk count / ingested_via / status; no audience marker | No | Load-bearing invariant is invisible after creation. |
| Current audience visibility on detail page | Data present in payload | — | **No** — Metadata table omits `universe` and `spokespeople`. | No | Same. |
| Reassignment / editing audience | Yes (PATCH `spokesperson_ids`, `universe`; attach/detach; serializer guards forbid orphaning invariants) | — | KnowledgePanel attach/detach; no UI to change Universe or reclassify to WORKSPACE. | No | Universe-move and WORKSPACE-conversion are backend-supported but not UI-exposed. |
| Archive / delete | Soft delete | Delete button on list row + detail page | Same | Yes | Recovery UI intentionally deferred. |
| Provenance / source visibility | Yes | — | Yes on detail page (author, date, hostname, source URL, extracted/fetched chars, PDF pages) | Yes | Strong. |

Reading of the matrix:
- Backend: **A** (fully exposing Delta correctly).
- UI: mostly **B** (mechanically exposing but poorly communicating) for UNIVERSE/WORKSPACE, mostly **C** (hiding important capabilities) for CHARACTER create and audience visibility.
- UI: partly **D** (exposing pre-Delta concepts) via the "None (legacy)" wording — the "legacy" framing is a pre-Delta artifact, not a Delta description.

## §15 STEP 11 — Page-count / flow-scatter (Knowledge only)

Knowledge does not exhibit Episode-shaped scatter (there is no multi-page wizard). But it exhibits a different scatter pattern:

- Creation of WORKSPACE / UNIVERSE knowledge: one page, one form. Coherent.
- Creation of CHARACTER knowledge: **two unrelated pages, minimum** (`/workspace/knowledge` for content ingest → `/spokespeople/{id}` for restriction). Restriction to N characters: **N+1 pages**.
- "Who knows this" answer: requires reading N spokesperson detail pages (one per character) since neither the list nor the detail page shows assignment.
- Universe scoping of an existing doc: not surfaced — the backend accepts `PATCH {universe: <uuid>}` (see `api/knowledge.ts:284-288`) but no UI control invokes it.
- The Universe detail page's `Docs` section is CLIENT-filtered on `d.universe === id`, ignoring the backend's more expressive `?universe=<uuid>` query param. UNIVERSE-mode LIST is available but underused.

Not automatically a call to consolidate to one page. Recording it as evidence of controls scattered across unrelated screens for a single operator task ("decide who knows this thing").

## §16 STEP 12 — Findings (typed)

**OBSERVED FACT (source)**
- The only positive-audience gestures at CREATE are "pick a Universe" (→ UNIVERSE) and "pick 'None (legacy)'" (→ WORKSPACE). CHARACTER is not creatable from `/workspace/knowledge` (`web/src/routes/workspace/knowledge.tsx:283-641`).
- `audience_scope`, `universe`, and `spokespeople` are present in the client payload (`web/src/lib/api/knowledge.ts:52-79`) but not rendered in either the list row (`knowledge.tsx:716-775`) or the detail Metadata table (`knowledge.$id.tsx:189-256`).
- WORKSPACE creation reads to the operator as `"None (legacy — visible to workspace-wide legacy teammates only)"` (`knowledge.tsx:85-87`).
- `KnowledgePanel` describes workspace-wide docs as `"Visible to every spokesperson in the workspace"` (`knowledge-panel.tsx:222-223`) — accurate and understandable.
- Attach transitions a workspace/Universe doc to CHARACTER via M2M and the `_toggle_spokesperson` action; detach guards the last-spokesperson case with a structured, operator-visible error message (`knowledge-panel.tsx:38-53, 187-205`).
- The Universe detail page lists only client-filtered UNIVERSE docs; CHARACTER docs whose spokespeople live in that Universe are absent from that view (`universes.$id.tsx:51`).

**SOURCE-DERIVED FACT (inferred from code, not observed at runtime)**
- Switching tabs in `UploadPanel` resets the picker to unpicked (four independent `useState` scopes at `knowledge.tsx:299,389,504,593`). Not asserted with a runtime test but visible in source.
- Restricting an existing doc to N characters requires N navigations, N clicks — no bulk selector exists in the codebase.

**OPERATOR OBSERVATION (Chris — see prompt "IMPORTANT NEW PRODUCT OBSERVATION")**
- The visible creation experience reads as three ingestion methods rather than as an audience decision.
- The UI does not clearly answer who will know this, where it belongs, or who can retrieve it.

**INFERENCE**
- The picker's `"None (legacy — visible to workspace-wide legacy teammates only)"` copy is a Slice 12 concession from the pre-Delta era where NULL was the shape-derived WORKSPACE marker. Post-Delta (`AudienceScope.WORKSPACE` is a first-class value, not a fallback), the "legacy" framing is stale. The parenthetical clause is now the actual description; the "None (legacy)" prefix is misdirection.

**PRODUCT HYPOTHESIS (to be confirmed / falsified with Chris + ChatGPT)**
- H1 — Consolidating audience into a single operator-labeled control ("Who should know this?" with three answers: `Just these characters`, `Everyone in a World`, `Everyone in this workspace`) would make Q-277-1 answerable YES for all three audiences without any backend change.
- H2 — Rendering the resolved audience on both the list row and the detail Metadata table would eliminate the "why does Ruby know this?" gap without any backend change.
- H3 — Chris's observation that ingestion-method is over-elevated is correct in structure but not because ingestion-method is unimportant — it is because audience is *coequal* and today gets one dropdown while ingestion-method gets four tabs.

**PRODUCT PREFERENCE (Chris to decide — do not decide here)**
- Whether the audience question stays visually on the same page (compact) or splits into a step ("Pick audience → then pick ingest").
- Whether "Universe" is renamed "World" (or "Business") in operator-facing copy, or those synonyms co-exist as they do today.
- Whether CHARACTER creation from `/workspace/knowledge` becomes a first-class create path (adds `spokesperson_ids` field), replacing the "create then restrict" two-step.

## §17 STEP 13 — Recommendation + smallest next falsifiable question

**Q-277-1 answer:** falsified for CHARACTER audience; partially falsified for WORKSPACE (mechanically exposed but lexically misleading); confirmed for UNIVERSE (mechanically exposed and reasonably named).

**Companion answer:** confirmed — ingestion method is the dominant visual axis (`Tabs`); audience is a single dropdown that (a) collapses two of the three audience choices, (b) hides the third entirely, (c) frames the WORKSPACE gesture as legacy, and (d) never renders the resolved audience on any post-CREATE surface.

**Recommended next slice — NOT implementation, one falsifiable question:**

> Q-277-2 — If the workspace-knowledge picker were reshaped as **"Who should know this?"** with three positive labeled choices (`Just these characters` [+ spokesperson multiselect], `Everyone in <World>` [+ Universe select], `Everyone in this workspace`), and the resolved audience were rendered as a badge on every KnowledgeDocument list row and in the detail Metadata table, would fresh dogfood-driven creation of CHARACTER, UNIVERSE, and WORKSPACE knowledge succeed on the first try for an operator who has never read `SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md`?

Answering Q-277-2 requires only a UI experiment (backend contract already satisfies it). It is small (one screen, one badge on two surfaces), reversible, and its result would tell us whether the mismatch identified in Slice 1 is the actual friction or a symptom of something deeper (e.g. the operator's mental model is really "which business is this for", not "who should know this").

Do NOT implement Q-277-2 without Chris + ChatGPT explicit approval — Slice 1 is audit only.

**Alternate smaller experiments** (present, do not select):
- Rename only: replace `"None (legacy — visible to workspace-wide legacy teammates only)"` with a positive `"Everyone in this workspace"` label, no structural change. Cheapest possible test of the "legacy" lexical-drift finding alone.
- Read-only audience badge on list rows, no CREATE change. Tests whether the "who knows this" post-creation gap is felt at all before touching the CREATE flow.
- Fresh dogfood exactly as the SESSION 277 handoff proposed — see whether real ingestion under today's UI produces the audience Chris intended, and use the delta as forcing function for a smaller UI change than the full Q-277-2 reshape.

## §18 Unresolved questions (deferred to Chris + ChatGPT review)

- Should CHARACTER creation be a first-class path on `/workspace/knowledge`, or does the "assign after upload" split remain intentional (e.g. because most character-restricted knowledge starts as workspace/Universe knowledge that later gets restricted)?
- What is the correct operator-facing name for `AudienceScope`? Candidates: `Audience`, `Who knows this`, `Shared with`, `Visible to`. No implementation-driven answer here.
- Do the picker's synonyms (`World` vs. `Universe`, `Worlds` on the dashboard chip) confuse operators, or is the plurality intentional?
- Is the WORKSPACE audience real product surface today, or is it a compatibility artifact for pre-Universe workspaces that Chris wants deprecated? If deprecated, the picker should not offer it at all.
- Should the KnowledgeDocument detail page gain a first-class "Audience" section (badge + list of spokespeople + Universe name + reassignment controls), or is per-spokesperson KnowledgePanel the only assignment surface?

---

_Slice 1 landed SHA: TBD (SHA-record commit after audit doc lands)._
