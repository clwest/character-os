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

_Slice 1 landed SHA: `471f929` (audit document commit)._

---

# Slice 2 — Q-277-2 — CURRENT WORKSPACE SEMANTICS AUDIT (audit-only)

Chris + ChatGPT reviewed Slice 1. Q-277-1 accepted as **falsified**.
Implementation of the proposed Knowledge audience selector deferred:
operator observation surfaced a deeper question — Chris no longer knows
what "Workspace" represents in the current product. Slice 2 answers
that question before returning to the Knowledge UI.

## §19 Slice 2 baseline

- HEAD @ Slice 2 open: `80f71e5` (Slice 1 SHA-record). Clean working
  tree, HEAD == `origin/main`.
- KnowledgeDocument substrate unchanged (0 rows, 0 chunks, audience
  constraints intact per §1 baseline).
- Read-only. No DB mutations, no source edits.

## §20 Slice 2 checklist

- [x] STEP 0 — verify baseline, Slice 1 landed cleanly, KD substrate empty.
- [x] PART A — trace current Workspace data model.
- [x] PART B — build the Workspace-vs-Universe-vs-Character scope matrix.
- [x] PART C — trace Universe relative to Workspace.
- [x] PART D — tenancy / security audit (queryset filters + permissions).
- [x] PART E — operator-visible Workspace UX (SPA switcher / settings / onboarding / helper text).
- [x] PART F — historical intent vs current behavior (SESSION 259 audit, SESSION 261 substrate, UNIVERSE_BOUNDARY_V1).
- [x] PART G — current real-DB shape.
- [x] PART H — generalization test against Fox & Flour / Patch+Rivet / Riverstone / dealership.
- [x] PART I — WORKSPACE knowledge product interpretation.
- [x] PART J — UNIVERSE knowledge product interpretation.
- [x] PART K — CHARACTER knowledge product interpretation (incl. cross-Universe check).
- [x] PART L — hierarchy diagram (architecture + operator mental model).
- [x] PART M — answer the Knowledge UI blocker.
- [x] PART O — smallest next falsifiable question.
- [ ] Commit + push audit slice; SHA-record.

## §21 Q-277-2

> What role does Workspace actually play in the CURRENT Character OS
> architecture and operator experience, and does it still represent a
> meaningful ordinary knowledge audience — or is WORKSPACE primarily a
> historical/tenant/infrastructure boundary inherited from an earlier
> product model?

Companion:

> If one operator has several unrelated Character OS activities —
> Fox & Flour, Patch+Rivet, Riverstone, a dealership — does the current
> architecture expect those to be N Universes inside one Workspace,
> N Workspaces, or some other hierarchy?

## §22 Prediction (before source inspection)

Prediction: Workspace is architecturally load-bearing as the
**tenant/security boundary** and has been narrowed to that role by
SESSION 261's introduction of Universe, but the operator UX has not
caught up — the SPA never asks the operator to create, switch, name,
or reason about Workspaces, and every user gets exactly one
`default_workspace`. Chris's uncertainty is a symptom of that lag, not
of architectural incoherence. The 4-business scenario is expected to
map to **one Workspace, four Universes** — matching how Chris has
already been using the system.

## §23 PART A — Workspace data model (source)

File: `shell/apps/accounts/models.py`.

`Workspace` (line 108-142):
- `id: UUID`, `name: CharField(120)`, `slug: SlugField(140, unique=True)` — slug is **globally unique** (flagged as a wart by SESSION 259 audit / `UNIVERSE_BOUNDARY_V1.md` §Q2 caveat).
- `owner: FK(User, PROTECT, related_name="owned_workspaces")` — user cannot be deleted while owning workspaces.
- `members: M2M(User, through="Membership", related_name="workspaces")`.
- `created_at`, `updated_at`.
- **No `is_active`, no `archived_at`, no soft-delete.** Deletion is direct.

`Membership` (line 145-173):
- `user × workspace × role` (`unique_together`).
- `Role`: `OWNER | ADMIN | EDITOR | VIEWER`. Model docstring: "v1 only uses `owner`; the other roles exist for the Agency tier (design doc §6.6)."
- Both FKs `CASCADE`.

`default_workspace_for(user)` (line 176-188):
- Returns the user's first owned workspace by `created_at`, else the oldest membership's workspace, else `None`. Called by `/api/me/`.

Backend supports **many workspaces per user** by construction (both
`owned_workspaces` and `workspaces` reverse relations are 1:N and
M:N). There is no uniqueness constraint tying a User to a single
Workspace.

## §24 PART B — Entity → Workspace/Universe scope matrix

Source-traced (grep for `workspace = models.ForeignKey` /
`universe = models.ForeignKey` across `shell/apps/*/models.py`).

| Model | Workspace FK? | Universe FK? | Character/Teammate scope? | Cross-Universe possible? | Cross-Workspace? |
|---|---|---|---|---|---|
| `accounts.Workspace` | — (root) | — | — | — | — |
| `accounts.Membership` | FK (CASCADE) | — | — | — | never |
| `universe.Universe` | FK (CASCADE) | — (self) | — | — | never (unique per workspace by slug) |
| `universe.Episode` | via `.universe.workspace` (no direct FK per EPISODE_SCHEMA_V1 §Q2) | FK (CASCADE) | via `EpisodeCast` M2M | forbidden (cast M2M rejects cross-Universe) | never |
| `universe.EpisodeCast` | via chain | via chain | required | forbidden | never |
| `spokespeople.Teammate` | FK (CASCADE) | FK (RESTRICT, **nullable**) | self | n/a | never (workspace-unique name) |
| `identity.CharacterIdentity` (+ Version/Reference/GenerationRecord/NormalizationManifest/ApprovedRepresentationBundle) | FK | — | via teammate | n/a | never |
| `embeddings.KnowledgeDocument` | FK (CASCADE) | FK (RESTRICT, nullable) | M2M to Teammate | **forbidden** for M2M attach (signals reject cross-Universe attach; legacy NULL-only pairing allowed) | forbidden |
| `embeddings.KnowledgeChunk` | via KD | via KD | via KD | via KD | via KD |
| `embeddings.KnowledgeDocumentSpokesperson` (through) | via KD | via KD | required | forbidden | forbidden |
| `memory.NarrativeMemory` | FK | FK (nullable) | via KD/composition chain | inherited from KD | inherited |
| `compositions.Composition` | FK (CASCADE) | via `.spokesperson.universe` + optional `.episode.universe` | required | forbidden (Composition.clean rejects cross-Universe spokesperson vs episode per line 830-840) | never |
| `compositions.Asset` | FK | — | — | — | never |
| `scripts.Script` | FK | via composition | via composition | inherited | never |
| `campaigns.PersonalizedCampaign` | FK | — | — | — | never |
| `publish.PublishBundle` | FK | — | — | — | never |
| `realtime.RealtimeSession` (+ Event) | FK | via spokesperson | required | inherited | never |
| `videos.Video` | via spokesperson.workspace | — | required | — | never |
| `transcripts.Transcript` | FK | — | — | — | never |
| `billing.*` | (attached at workspace level per `UNIVERSE_BOUNDARY_V1.md` §Q1) | — | — | — | tenant-scoped |

**Every content model FKs Workspace with NOT NULL + CASCADE.**
Cross-workspace access is rejected in multiple defense-in-depth
layers (see §25). Universe is the second, narrower wall — nullable
today because SESSION 261 introduced it as opt-in; every real
teammate created via the SPA wizard still lands `universe=NULL`
(see §27).

## §25 PART C — Universe's relationship to Workspace

Source: `shell/apps/universe/models.py:33-165`.

- `Universe.workspace` — required, `CASCADE`. **One Universe belongs
  to exactly one Workspace.** (`UNIVERSE_SCHEMA_V1.md` §Invariants
  invariant 1.)
- `(workspace, slug)` unique. Slug uniqueness is **per-workspace**,
  not global.
- Universe has `archived_at` (soft-delete). Hard-delete is legal only
  after emptying (`RESTRICT` on `Teammate.universe` +
  `KnowledgeDocument.universe`).
- `Universe.teammate_count()`, `.knowledge_document_count()`,
  `.episode_count()` — Universe is a **scoping shell** for teammates,
  KDs, and Episodes.
- `EpisodeCast.clean()` (`universe/models.py:446-481`) enforces
  `teammate.universe_id == episode.universe_id` AND
  `teammate.workspace_id == episode.universe.workspace_id`.
  **Cross-Universe cast is forbidden**; legacy `teammate.universe=NULL`
  is also rejected from Universe Episode casts.

Consequences:
- A Workspace CAN contain multiple Universes (Chris's real workspace
  already does — see §27).
- A Universe CANNOT belong to multiple Workspaces (single-FK).
- A Teammate CAN exist at Workspace scope without a Universe
  (`Teammate.universe` nullable — the "legacy" state).
- A Teammate CANNOT move freely — moving between Universes is a
  PATCH gated by `SpokespersonUniversePanel`'s `universe-move-preview`
  which surfaces cross-Universe M2M attach rows that would break.
- A Teammate CANNOT participate in multiple Universes simultaneously
  (single-value FK, not M2M).
- Universe currently groups: Teammates, KDs, Episodes, Episode casts,
  and (nullable) NarrativeMemory. Per `UNIVERSE_BOUNDARY_V1.md` §Q3:
  future in-world entities (relationships, locations, style identity)
  belong to Universe as well.

## §26 PART D — Tenancy / security audit

Enforcement points (source-traced):

- **DRF viewset queryset filter.** Every content ViewSet filters
  `workspace__memberships__user=self.request.user`. Grep hits at
  `apps/transcripts/views.py:75`, `apps/embeddings/views.py:69`,
  `apps/memory/views.py:77,146`, `apps/compositions/views.py:173,283,374,668,916`,
  `apps/spokespeople/views.py:259`, `apps/realtime/views.py:100,675,762`,
  `apps/videos/views.py:75`, `apps/publish/views.py:115`.
- **Permission class.** `character_os/permissions.py:18-70`
  `IsWorkspaceMember` resolves the object's workspace (direct FK,
  via `.spokesperson.workspace`, or via `.universe.workspace` for
  Episode) and requires an active `Membership` row. Read requires any
  role; write requires `OWNER`.
- **Defense-in-depth model-level rejects.** See
  `UNIVERSE_BOUNDARY_V1.md` §Q1 enumeration:
  `KnowledgeDocument.clean` + `apps/embeddings/signals.py` `pre_add`
  reject cross-workspace M2M attach; `retrieve_for_teammate` derives
  workspace from `spokesperson.workspace` with no override
  (`retrieval.py`); `Composition.clean`, `Script.clean`, `Asset`,
  `PersonalizedCampaign`, `IdentityReference.clean` all reject
  cross-workspace pairings.
- **Unique namespaces.** `(workspace, content_hash)` unique on KD;
  `(workspace, name)` unique on Teammate. These make Workspace the
  operator-invisible dedup/naming namespace.

Verdict: **Workspace is load-bearing as a tenant / security boundary.**
Cross-workspace data access is intentionally impossible; every write
boundary rejects cross-workspace pairings; every LIST queryset
filters by workspace membership. This is not a fashion choice — it is
the primary security posture of the entire application.

## §27 PART E — Operator-visible Workspace UX (SPA)

SPA-side (files under `web/src/`):

- **Nav rail (`components/nav-rail.tsx:52-134`)** — 11 items:
  Dashboard, Spokespeople, Knowledge, Transcripts, Scripts, Recipes,
  Campaigns, Bundles, Videos, Assets, Images. **No "Workspaces" item.
  No workspace switcher. No workspace settings item.**
- **Dashboard masthead (`routes/dashboard/index.tsx`)** — shows
  `me.data.default_workspace.name` (or email fallback). No switcher
  affordance beside it.
- **Spokesperson-new back link (`routes/spokespeople/new.tsx:187`)** —
  the back-to-dashboard link is labeled simply **"Workspace"**, using
  the word as a casual synonym for "the app's home for my content".
- **`/api/workspaces/` and `/api/memberships/`** — both wired in
  `apps/accounts/urls.py:16-17` as full ModelViewSets. The SPA's
  `lib/api/workspaces.ts` (77 lines total) exports only `useMe` and
  `useSubscription` — **no create, list, switch, rename, delete, or
  invite operations are ever called**.
- **Settings routes (`routes/settings/`)** — 4 pages: `bootstrap-review`,
  `engine-connections`, `provider-status`. None exposes workspace
  configuration; `engine-connections` reads workspace tier for a
  Pro-gate but never lets the operator edit workspace fields.
- **Spokesperson wizard (`routes/spokespeople/new.tsx`, `components/spokesperson-wizard.tsx`)** —
  zero references to `universe` or `Universe`. Every newly-created
  teammate lands `universe=NULL` (legacy). Universe assignment happens
  post-hoc via `SpokespersonUniversePanel` on the detail page.
- **Onboarding tour (`components/onboarding-tour.tsx`)** — no
  workspace-explanation content.

Conclusion: **the operator has no first-class Workspace surface in the
SPA.** Workspace exists as an implicit anchor for every API call
(`?workspace=<uuid>` query param) but is neither shown, switched, nor
managed. The one place the operator sees the word is on a back-link
that means "dashboard".

## §28 PART F — Historical intent vs current behavior

Design docs (`docs/design/`) trace three intent phases:

**Phase 1 — pre-SESSION 259 ("Workspace-does-everything").**
`WORKSPACE_FABRIC_V1.md` (SESSION 144) treats Workspace as "one
workspace, not three sections that share a database". It is the
operator's world.

**Phase 2 — SESSION 259 workspace audit + SESSION 261 substrate ("split the four meanings").**
`UNIVERSE_BOUNDARY_V1.md` §Purpose: > `Workspace` today silently
carries four meanings — **tenant**, **universe**, **project**, and
**studio** — and the operator has never had a UI-level way to
construct additional workspaces or to scope knowledge below the
workspace level. As a result, seven teammates spanning at least four
unrelated fictional worlds (Patch/Rivet workshop, Riverstone Outdoor
Adventures, Surgo Automotive, Hearth & Hollow bookstore, plus Tulsi)
cohabit `chriss-workspace` and all six workspace-wide K2 docs are
cosine-retrievable to every dialogue synthesis call regardless of
world.

`UNIVERSE_BOUNDARY_V1.md` §"Working hypothesis" landed the split:
1. Workspace remains the **tenant / ownership / security boundary**.
2. Universe becomes a child of Workspace and represents one persistent creative world.
3. A Workspace may contain many Universes.
4. Characters, canon, relationships, locations, episodes, and shared world knowledge belong to a Universe.
5. Cross-Universe access must never occur implicitly.
6. Workspace-wide knowledge should NOT automatically become Universe knowledge.

`UNIVERSE_SCHEMA_V1.md` (SESSION 261) implemented (1)-(6) as the
substrate.

**Phase 3 — post-SESSION 276 ("Delta is permanent").**
`AudienceScope` is now a first-class enum with DB CheckConstraints;
`WORKSPACE` is one of four values (`CHARACTER | UNIVERSE | WORKSPACE | NONE`).
`WORKSPACE` audience today mechanically means "everyone in the tenant"
— exactly what SESSION 259 flagged as the leak that motivated the
Universe layer's creation.

**Drift finding:**
- Backend model **has** completed the split (Universe is a first-class
  child; cross-Universe M2M is rejected; `audience_scope` is enforced
  in DB).
- Design doc **has** taken a permanent position (Workspace = tenant).
- Operator UX **has not caught up**: no Workspace switcher / settings
  UI, no Universe picker in the spokesperson-create wizard, `.universe`
  still nullable, 6 of Chris's 8 real teammates still legacy (§29).
- `KnowledgeDocument.audience_scope=WORKSPACE` is the exact
  cosine-leak vector SESSION 259 identified — kept mechanically because
  the SPA still needs a positive marker for the "None (legacy)" gesture.

## §29 PART G — Current real-DB shape

Query executed against local `character_os` DB (port 5434,
`DB_PORT=5434`), read-only.

- Users: 111 (mostly `e2e-*` and `smoke-headless-*` test noise; one
  admin; one real operator).
- Workspaces: 111 (same breakdown).
- Real (non-`E2e`/`Smoke`) workspaces: 11.
- Chris owns **5** workspaces:

| Workspace name | Universes | Teammates | KDs | Notes |
|---|---|---|---|---|
| `"Chris's workspace"` (slug `chriss-workspace`) | 2 (Fox & Flour Bakery + Patch's Workshop) | 8 (Ruby, Rivet, Patch in Universes; Riggs, Repo Red, Mike, Penny, Mason still legacy `universe=NULL`) | 0 (post-SESSION 276 reset) | Chris's primary product workspace. |
| `"EXP266-STRONG"` (disposable) | 1 | 2 | 0 | SESSION 266 experiment. |
| `"EXP266-WEAK"` (disposable) | 1 | 2 | 0 | SESSION 266 experiment. |
| `"SESSION 272 Slice B — EXP"` | 1 | 1 | 0 | SESSION 272 Rivet-debug experiment. |
| `"SESSION 272 Slice B — CTL"` | 1 | 1 | 0 | SESSION 272 Rivet-debug experiment. |

The 4 extra workspaces are **experiment/disposable scaffolding** —
created by dogfood scripts to isolate a control from an experimental
substrate, not by an operator choosing "I want a separate workspace
for this business." They inflate the multi-workspace-per-user count
without representing product behavior.

**Product-usage pattern (from real substrate):**
- Chris uses **one primary Workspace** (`"Chris's workspace"`).
- Inside it, he already runs **multiple worlds** (Fox & Flour + Patch's
  Workshop) as Universes.
- Six legacy teammates (Riggs, Repo Red, Mike, Penny, Mason — and
  historically anyone the SPA wizard created before assignment via
  `SpokespersonUniversePanel`) still bypass the Universe layer.
- This is **exactly the "seven teammates across four unrelated worlds
  cohabit chriss-workspace" pattern** SESSION 259 flagged, partially
  cleaned up (2 of the fictional worlds are now Universes) but not
  finished (the other 4 candidate worlds — Riverstone, Surgo,
  Hearth & Hollow, Tulsi — never got a Universe row).

## §30 PART H — Generalization test (Fox & Flour / Patch+Rivet / Riverstone / dealership)

Test the four-business scenario against the current architecture.

**Interpretation A — ONE Workspace, FOUR Universes.**

- Identity: works. Each Universe scopes its own Teammates via
  `Teammate.universe`. Ruby (Fox & Flour), Patch+Rivet (Workshop),
  Penny (Riverstone), dealership characters (Dealership Universe).
- Knowledge: works. `UNIVERSE`-audience KDs are per-Universe and
  cosine-retrievable only to spokespeople in that Universe (per
  `retrieve_for_teammate` positive-audience Delta).
- Memory: works. `NarrativeMemory.universe` is FK; per-Universe.
- Content continuity: works. Episodes are Universe-scoped; cast is
  Universe-consistent via `EpisodeCast.clean`.
- Compositions: works. `Composition.clean` rejects cross-Universe
  spokesperson vs episode.
- Operator navigation: **partial** — nav rail treats all four
  Universes as siblings under one dashboard; Universe detail page
  (`/workspace/universes/:id`) is the per-world drill-in, but the
  dashboard tile shows aggregate stats across all Universes.
- Permissions: works. One Membership grants access to all four.
- Sharing: works if intended. Cross-Universe sharing is forbidden by
  construction; explicit crossover is deferred
  (`UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md`).
- Cross-business leakage: **only via `audience_scope=WORKSPACE`**.
  Ruby's `WORKSPACE`-audience KD would leak to every eligible
  character across all four unrelated businesses. This is the
  SESSION 259 leak.
- Future multi-user collaboration: works. Membership model is
  multi-role; Agency tier already scaffolded.

**Interpretation B — FOUR Workspaces, one or more Universes each.**

- Identity: works but Chris needs 4 separate accounts-anchor rows.
- Knowledge: strict isolation — no possibility of cross-business
  leak even via WORKSPACE audience.
- Memory: same as knowledge — strict.
- Content continuity: fine per-workspace.
- Compositions / renders: fine per-workspace.
- Operator navigation: **worst-case degradation.** Chris would need
  to switch workspaces to move between businesses. The SPA has no
  switcher (see §27). Every route is workspace-scoped by
  `default_workspace`, which would arbitrarily land on one of the
  four; operator would have no way to see the others without a UX
  we haven't built.
- Permissions: fine but 4 independent Membership rows.
- Sharing: intentionally impossible.
- Cross-business leakage: impossible.
- Future multi-user: fine; each workspace has its own Agency team.

**Interpretation C — mixed** (e.g. Fox & Flour and Patch+Rivet in
one workspace, dealership in another).

- Not currently distinguishable from A or B at the tenancy layer; the
  boundary would be arbitrary and operator-invisible. No architectural
  evidence favors this.

**Interpretation D — architecture does not provide a coherent answer.**

- Falsified: the substrate answers this **cleanly** — Workspace is
  tenant, Universe is world, one Workspace holds many Universes.
  What's incoherent is not the architecture; it is the *operator UX*,
  which never asks the operator to make either choice.

**Verdict:** The current architecture supports Interpretation **A**
best. It supports **B** in principle (backend allows multi-Workspace
per user; Chris in fact owns 5) but the operator UX makes B
impractical today (no switcher, no create-workspace surface). It
does not support C or D.

## §31 PART I — WORKSPACE knowledge product interpretation

**Mechanical meaning** (source-derived):
- `audience_scope=WORKSPACE` + `universe_id IS NULL` (enforced by
  CheckConstraint `session276_workspace_forbids_universe_fk`).
- Retrievable by any Teammate in the same Workspace via
  `retrieve_for_teammate`'s `Q(audience_scope=WORKSPACE)` branch.
- LIST-visible to any Membership in the Workspace via
  `get_queryset`'s `Q(audience_scope=WORKSPACE)` branch.

**Product meaning under Interpretation A** (one workspace, N
Universes):
- "Every character across every unrelated business the operator runs
  in this tenant" — including businesses that share nothing
  contextually. Ruby, Patch, Rivet, Penny, dealership characters,
  future characters — all of them would receive the doc.
- **This is the exact failure mode SESSION 259 flagged** (§28) — it
  is the cosine-leak between worlds that motivated the Universe
  layer's creation.

**Product meaning under Interpretation B** (N workspaces):
- "Every character in this business's workspace" — which for a
  single-business workspace is a sensible answer to "everyone in
  <Business>". But Chris does not use this pattern today; his
  single-workspace multi-Universe layout is the actual usage.

**Legitimate use cases for WORKSPACE audience** (assuming Interpretation A):
- Operator-wide preferences / platform behavior directives (e.g. "we
  always cite sources", "we never speculate about legal matters") —
  **plausibly legitimate** but not content-shaped; more of a system
  prompt or persona overlay.
- Universal safety / compliance policies that must apply regardless
  of world — **plausibly legitimate but rare**; the operator would
  need to actively want this content in every dialogue.
- Reusable expertise that spans businesses — plausible in principle
  but each concrete example dissolves on inspection (Ruby's baking
  knowledge is Fox & Flour's, not dealership's; the dealership's
  financing expertise is not the bakery's).
- Onboarding/help/style guides for the operator themselves — plausible
  but not really "knowledge for characters."

**Classification: C ("system/infrastructure audience not normally chosen
by operators")** with a footnote of **B ("legitimate but advanced/rare")**
for genuine operator-wide preferences. **WORKSPACE audience should NOT
be a primary/ordinary knowledge-audience choice** in an Interpretation-A
tenant model. It should either (a) be hidden behind an "advanced"
disclosure, (b) be repositioned as a system/preferences surface rather
than a knowledge-creation option, or (c) be deprecated in favor of the
"pick every Universe individually" pattern.

The current SPA implicitly acknowledges this by labeling the WORKSPACE
gesture as "None (legacy — visible to workspace-wide legacy teammates
only)" — an accidental confession that the gesture is not a
first-class operator choice.

## §32 PART J — UNIVERSE knowledge product interpretation

**Mechanical meaning** (source-derived):
- `audience_scope=UNIVERSE` + `universe_id IS NOT NULL` (enforced by
  `session276_universe_requires_universe_fk`).
- Retrievable by any Teammate whose `universe_id` matches the doc's
  `universe_id`.
- LIST-visible via `Q(audience_scope=UNIVERSE)` in the workspace
  member's queryset.

**Product meaning:**
- "Everyone in this world/business/cast." Fox & Flour's working
  knowledge; Patch's Workshop safety protocols; Riverstone's route
  library; dealership financing docs.
- This is the **strongest candidate for the everyday "shared group /
  business knowledge" concept.**
- SESSION 274 audit (`SESSION_274_UNIVERSE_SHARED_KNOWLEDGE_DOGFOOD.md`
  §1) explicitly names this: > **Universe-shared knowledge** (facts
  every character in a Universe should be allowed to know) **+
  character-specific knowledge** (expertise for one particular
  character in that Universe).

**Naming caveat** (source-derived, not a decision):
- The word "Universe" is engineering-flavored. Operator-visible copy
  today already reads as "World / Universe" (picker) or "Worlds"
  (dashboard chip) or "world" (Universe listing helper text). The
  UNIVERSE_BOUNDARY_V1.md consistently uses "world". Neither "world"
  nor "business" is fully load-bearing today.

## §33 PART K — CHARACTER knowledge product interpretation

**Mechanical meaning** (source-derived):
- `audience_scope=CHARACTER` + at least one row in
  `KnowledgeDocumentSpokesperson` M2M (invariant #4 in
  `UNIVERSE_SCHEMA_V1.md`; application-layer enforcement, not DB
  CheckConstraint per SESSION 276 §361).
- Retrievable ONLY by the specific Teammate(s) in the M2M via
  `Q(audience_scope=CHARACTER, spokespeople=<sp>)`.
- Multi-character within one Universe: supported (M2M with N rows,
  all sharing the doc's Universe).

**Cross-Universe multi-character CHARACTER share — mechanically forbidden.**
- `apps/embeddings/signals.py:93-154` `reject_cross_universe_spokesperson`
  rejects `doc.spokespeople.add(sp)` when
  `sp.universe_id != doc.universe_id`.
- The only pairing where the check *passes* while spanning "different
  worlds" is legacy (both `doc.universe=NULL` and `sp.universe=NULL`).
  That is not "cross-Universe share" — it is "both are legacy and
  neither has adopted the Universe layer."
- **Ruby (Fox & Flour Universe) + Rivet (Patch's Workshop Universe)
  cannot share one CHARACTER-audience KD** in the current
  architecture. This is intentional per `UNIVERSE_BOUNDARY_V1.md`
  invariant 5 ("Cross-Universe access must never occur implicitly").
- Implication for future Knowledge UI: a "Just these characters"
  choice must constrain its spokesperson multiselect to one Universe
  at a time (or to legacy characters). Cross-Universe multi-select
  will simply fail at the M2M signal.

**Product meaning:** direct, minimal-audience. One or more explicitly
named characters in one Universe (or in the legacy pool). This is the
most narrow of the three audience choices and the most operator-obvious.

## §34 PART L — Hierarchy diagrams

**Architecture (source-derived, current):**

```
Account (User)
  ├── owned_workspaces (1:N, PROTECT)
  └── memberships (M:N via Membership, role=OWNER v1)
       └── Workspace                                        [tenant / security / billing]
            ├── Membership (role = OWNER|ADMIN|EDITOR|VIEWER; v1 uses OWNER only)
            ├── Universe (1:N, CASCADE)                    [world / business / cast]
            │    ├── Teammate (1:N, RESTRICT; nullable — see below)
            │    ├── KnowledgeDocument (1:N, RESTRICT; nullable — see below)
            │    ├── Episode (1:N, CASCADE)
            │    │    └── EpisodeCast (M2M w/ Teammate, Universe-consistent)
            │    └── NarrativeMemory (1:N; nullable)
            ├── Teammate (universe=NULL "legacy" pool)     [pre-SESSION 261 residue]
            ├── KnowledgeDocument (universe=NULL, audience_scope=WORKSPACE)
            │                                              [tenant-wide cosine leak vector]
            ├── Composition / Script / Asset / Campaign / Bundle / RealtimeSession
            │                                              [content provenance, workspace-scoped]
            └── CharacterIdentity + Versions + Bundles     [visual identity substrate]
```

Key: the architecture cleanly separates **Workspace = tenant** from
**Universe = world**, with Universe as an inner wall Chris opted into
in SESSION 261. Legacy teammates and legacy WORKSPACE-audience KDs
remain because the migration is incomplete on the operator side.

**Operator mental model (SPA-derived, current):**

```
Chris's app
  └── "Workspace" (implicit — never seen or switched)
       ├── Nav rail sections:
       │    Dashboard | Spokespeople | Knowledge | Transcripts | Scripts |
       │    Recipes | Campaigns | Bundles | Videos | Assets | Images
       ├── Dashboard tiles: Spokespeople · Knowledge (+ tiny "Worlds" chip) · Costs · Activity
       ├── "Worlds" (Universe) — reachable via a 10px chip on the Knowledge tile
       │    or via /workspace/universes URL. New-teammate wizard does NOT ask.
       └── (No workspace surface. No switcher. No settings.)
```

**Mismatch:** the architectural hierarchy has three levels
(Workspace → Universe → Teammate/KD/Episode). The operator UX has one
and a half (a nav rail that hangs off an unnamed root; a partly-hidden
Universe layer discoverable only from the Knowledge tile chip and the
`/workspace/universes` URL). Chris cannot navigate the mid-level
architectural layer through the SPA's normal chrome — and cannot
navigate the top level at all.

## §35 PART M — Answer the Knowledge UI blocker

Question: Should an ordinary Knowledge creation surface currently
present "Everyone in this workspace" as a peer choice beside
"specific characters" and "everyone in a Universe"?

**Answer: NO** — with an "advanced/secondary" carve-out.

Reasoning:
- Under Interpretation A (which the architecture supports best and
  which Chris actually uses), a WORKSPACE-audience KD reaches every
  character across every unrelated business in the tenant. That is
  the SESSION 259 leak the Universe layer was created to prevent.
- Under Interpretation B (multiple workspaces per business), the SPA
  provides no switcher or workspace-management surface today — so B
  is not an operator-supported product mode.
- The two legitimate WORKSPACE-audience use cases (operator-wide
  preferences; universal safety policy across genuinely unrelated
  businesses) are either (a) better modeled as system/persona
  configuration rather than knowledge documents, or (b) rare enough
  that they belong behind an "advanced" affordance rather than a
  primary tab.

**Recommended framing** (for a future Knowledge audience selector —
not implemented in this slice):
- Primary choices: `Just these characters` (CHARACTER, with
  Universe-constrained spokesperson multiselect), `Everyone in <World>`
  (UNIVERSE, with Universe select).
- Advanced / disclosed under "More options": `Everyone in every
  world in this tenant` (WORKSPACE) — with an explicit warning that
  the doc will reach unrelated businesses; do not use the word
  "legacy". Consider deprecating this option entirely once the
  legacy-teammate migration is complete.

Do NOT implement. This is a product recommendation, not a decision.

## §36 PART N reminder — bounds of this slice

We deliberately did NOT authorize (and this slice did NOT do):
- Workspace model redesign.
- Universe redesign.
- Tenancy rewrite.
- Migrations.
- Moving characters between containers.
- Navigation redesign.
- Workspace switcher / settings surface.
- Membership redesign.
- Knowledge UI changes.
- Assigning the 6 legacy teammates to Universes.
- Data migration.

If Chris + ChatGPT elect to close the operator-UX gap, that becomes a
separate slice with its own scope-lock.

## §37 PART F/G addendum — separated findings

**OBSERVED FACT (source):**
- Workspace has no `is_active` / `archived_at`; deletion is direct
  (`accounts/models.py:108-142`).
- `Membership.Role` has 4 values but v1 policy uses only `OWNER`
  (`accounts/models.py:145-165`).
- Every content ViewSet filters on `workspace__memberships__user`
  (§26 grep enumeration).
- `IsWorkspaceMember` resolves workspace via 3-hop traversal
  (direct FK / `.spokesperson.workspace` / `.universe.workspace`)
  (`character_os/permissions.py:47-70`).
- Universe.workspace is NOT NULL + CASCADE
  (`universe/models.py:55-59`).
- `EpisodeCast.clean` rejects cross-Universe and cross-Workspace
  cast attach (`universe/models.py:446-481`).
- `reject_cross_universe_spokesperson` blocks
  `doc.spokespeople.add(sp)` when doc + sp Universes disagree
  (`apps/embeddings/signals.py:93-154`).
- SPA never calls `POST /api/workspaces/` — `web/src/lib/api/workspaces.ts`
  exports only `useMe` + `useSubscription` (§27).
- Spokesperson-new wizard has zero references to `Universe`
  (`web/src/routes/spokespeople/new.tsx`, `web/src/components/spokesperson-wizard.tsx`).

**SOURCE-DERIVED FACT:**
- Backend supports many workspaces per user by construction; no
  uniqueness constraint on `Workspace.owner`.
- Backend supports many Universes per workspace by construction;
  `(workspace, slug)` unique but no per-workspace count cap.
- Multi-character CHARACTER-audience KDs are Universe-constrained
  by the M2M signal.

**OPERATOR OBSERVATION (Chris):**
- "The platform has changed since we started building the workspace,
  so now I don't know how it works with what we have built now."
- Chris has 5 owned workspaces, 4 of which are experiment scaffolding.
  His single primary workspace holds 2 Universes + 6 legacy teammates
  spanning at least 3 additional unresolved candidate worlds
  (Riverstone/Repo/dealership/etc.).

**INFERENCE:**
- The SESSION 261 substrate split ("Workspace = tenant; Universe =
  world") is materially complete on the backend but only partially
  reflected in the SPA. The operator sees the app as one flat
  container with a lightly-optional "Worlds" chip.
- WORKSPACE audience is a cosine-leak vector for Interpretation-A
  usage; its continued presence as a first-class SPA option is a
  UX artifact of an incomplete migration, not a positive product
  choice.
- Chris's uncertainty about Workspace is architecturally rational:
  the architectural role has narrowed (tenant only) but the SPA has
  never announced or reflected that narrowing.

**PRODUCT RECOMMENDATION:**
- Return to Knowledge UI (Slice 3) with the following framing:
  primary audience choices are CHARACTER (Universe-constrained
  multiselect) and UNIVERSE (Universe select); WORKSPACE is
  disclosed under an "advanced" affordance and never labeled
  "legacy".
- Separately (out of scope for Q-277-2): the operator UX debt of
  "Universe is discoverable only via a 10px chip; spokesperson
  wizard doesn't ask about Universe; there is no workspace surface
  at all" should be tracked as a known gap. Do not fix it during
  Q-277-3.

## §38 Unresolved questions (Slice 2 — deferred)

- Should the SPA gain a first-class Workspace surface at all, or is
  the "workspace is invisible, Universe is the operator-facing
  world" pattern the intended long-term product model? (If the
  latter, "Workspace" should probably disappear from operator copy
  entirely — including from the spokesperson-new back-link.)
- Should the spokesperson-create wizard require a Universe pick,
  making legacy `universe=NULL` unreachable for future rows? This
  would forecast a future migration of the 6 remaining legacy
  teammates.
- If WORKSPACE audience is deprecated / hidden, what happens to the
  three surviving legitimate use cases (operator-wide preferences,
  universal safety policy, cross-tenant reusable expertise)? Do they
  belong on a settings surface instead?
- Should `Universe` be renamed "World" or "Business" in operator
  copy for consistency with existing helper text
  (`UNIVERSE_BOUNDARY_V1.md` uses "world" throughout)?
- Multi-user collaboration: v1 restricts Membership to `OWNER`; does
  the Agency tier arrival change the WORKSPACE-audience recommendation
  (WORKSPACE could plausibly mean "everyone on my agency's team",
  which is closer to a real product concept)?

## §39 PART O — Smallest next falsifiable question

Given Slice 2's evidence, the smallest next question is:

> **Q-277-3** — If the workspace-knowledge picker were reshaped so
> its primary choices are **`Just these characters`** (CHARACTER,
> with a Universe-constrained spokesperson multiselect) and
> **`Everyone in <World>`** (UNIVERSE, with Universe select), and
> **`Everyone in this workspace`** were moved behind a disclosed
> "Advanced" affordance (labeled with its actual consequence, not
> the word "legacy"), and the resolved audience were rendered as a
> badge on every KnowledgeDocument list row and in the detail
> Metadata table, would fresh dogfood-driven creation of CHARACTER
> and UNIVERSE knowledge succeed on the first try for an operator
> who has never read `UNIVERSE_BOUNDARY_V1.md`?

This differs from the Slice 1 recommendation (§17) in exactly one
way: WORKSPACE is demoted from a peer choice to an "advanced"
disclosure, reflecting the Slice 2 finding that Interpretation A is
Chris's actual usage pattern and that Interpretation A makes WORKSPACE
audience a cosine-leak between unrelated worlds.

Answering Q-277-3 requires only a UI experiment (backend contract
already satisfies it). It is small (one screen, two badges), reversible,
and its result would tell us whether the demoted-WORKSPACE framing
matches Chris's operator intent.

**Alternate smaller experiments** (present, do not select):
- Static rename only: replace `"None (legacy — visible to
  workspace-wide legacy teammates only)"` with a neutral positive
  label (`"Every character across every world in this tenant"`),
  no structural change. Cheapest possible test of whether Chris
  ever picks it deliberately once the "legacy" framing is removed.
- Fresh dogfood exactly as the SESSION 277 handoff proposed — with
  today's UI untouched — and observe whether Chris naturally picks
  the "None (legacy)" option when he means "everyone at Fox & Flour"
  (the misclassification failure mode). If yes, that confirms the
  demote decision without needing to prototype it.
- Universe-first onboarding correction: audit whether the
  spokesperson-create wizard should require a Universe pick — a
  separate but pre-requisite question if Chris intends the operator
  UX to catch up to the architectural narrowing.

## §40 Slice 2 landed SHA

_Landed SHA: `d2cbee4` (Slice 2 audit commit)._

