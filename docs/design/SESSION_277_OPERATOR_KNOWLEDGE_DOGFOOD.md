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

---

# Slice 3 — Q-277-3 — NULL-UNIVERSE CHARACTER SEMANTICS AUDIT (audit-only)

Chris + ChatGPT reviewed Slice 2. Workspace classification accepted
(tenant boundary; Universe = world). Knowledge UI implementation
deferred again — Slice 2 exposed that the ordinary character-create
flow neither requires nor asks for a Universe, and legacy `universe=NULL`
teammates persist in production. Before reshaping Knowledge around
Universe membership, Slice 3 must determine what NULL-Universe
actually represents in the CURRENT product.

## §41 Slice 3 baseline

- HEAD @ Slice 3 open: `bad5cc9` (Slice 2 SHA-record). Clean, pushed.
- KnowledgeDocument substrate unchanged (0 rows / 0 chunks; audience
  constraints intact).
- Read-only. No DB mutations, no source edits.

## §42 Slice 3 checklist

- [x] STEP 0 — verify baseline (git + KD empty + Slice 2 landed).
- [x] PART A — inventory every current character-create path.
- [x] PART B — reconstruct ordinary SPA character-create flow.
- [x] PART C — build NULL-Universe capability matrix.
- [x] PART D — Knowledge composition boundary (Delta interaction).
- [x] PART E — Episode / cast composition boundary.
- [x] PART F — Memory / continuity composition boundary.
- [x] PART G — current-DB provenance for legacy NULL teammates.
- [x] PART H — historical intent (SESSION 259 → 261 substrate).
- [x] PART I — falsification: search for legitimate modern NULL use case.
- [x] PART J — generalization test (Fox & Flour / Patch+Rivet / Riverstone / dealership + non-business cases).
- [x] PART K — active vs draft state.
- [x] PART L — operator mental model.
- [x] PART M — current vs emerging hierarchy diagrams.
- [x] PART N — Q-277-3 classification + Universe-required recommendation.
- [x] PART O — effect on the proposed Knowledge UI.
- [x] PART P — smallest next falsifiable question.
- [ ] Commit + push audit; SHA-record.

## §43 Q-277-3

> Is `Teammate.universe=NULL` still a legitimate CURRENT Character OS
> product state that an ordinary operator should be able to create and
> use, or is it primarily historical/transition residue from before
> Universe became the world/business/cast boundary?

Companion:

> Has Universe become sufficiently load-bearing across current Character OS
> that every newly created ordinary character should have an explicit
> Universe before becoming an active usable character?

## §44 Prediction (before source inspection)

Prediction: NULL-Universe is currently **compatibility residue**. The
SPA character-create wizard never asks for a Universe, so every new
teammate lands NULL by default; but every downstream Universe-aware
workflow (Episode cast, UNIVERSE-audience Knowledge retrieval,
NarrativeMemory, retrieve_universe_canon shared-tier lane) either
excludes NULL teammates outright or falls back to a shrinking
legacy-only pool. Composition without Episode still works for NULL
teammates today. Expect the answer to be **classification C** with a
**LIKELY YES** on the required-Universe recommendation, gated on
first-Universe onboarding UX.

## §45 PART A — Every current character-create path

Grep results across `shell/apps/` for `Teammate.objects.create` +
`perform_create` (see also `shell/apps/spokespeople/views.py:277-306`).

| Create path | File | Universe accepted? | Universe required? | Default if omitted | Operator-visible? |
|---|---|---|---|---|---|
| SPA `/spokespeople/new` → `POST /api/spokespeople/` | `web/src/routes/spokespeople/new.tsx:87-100` → `web/src/lib/api/spokespeople.ts:157-194` → `apps/spokespeople/views.py:277-345` | payload accepts `universe` (serializer field, `apps/spokespeople/serializers.py:53`) | **no** (no validate-side requirement; only cross-workspace consistency) | `NULL` (nothing sent from SPA) | primary — the wizard the operator uses |
| Direct API `POST /api/spokespeople/ {universe: <uuid>}` | same viewset | yes | no | `NULL` | dev/automation path |
| `python manage.py seed_cast` | `apps/spokespeople/management/commands/seed_cast.py:198-204` | not passed | no | `NULL` | developer command, not product |
| `SpokespersonUniversePanel` PATCH | `web/src/components/spokesperson-universe-panel.tsx` | yes (post-hoc) | no | n/a (edit) | secondary — appears on the spokesperson detail page after creation |
| Django admin | `apps/spokespeople/admin.py` (default ModelAdmin) | yes | no | `NULL` | staff-only |
| Test factories | `apps/spokespeople/tests/**` | yes when explicit | never | `NULL` | not product |

**Conclusion:** every product-shaped create path (SPA wizard, seed
command, admin) lands `universe=NULL` unless the caller *deliberately*
sends a Universe FK. The SPA has no code path that sends one at create
time — Universe assignment is always a second, later step through
`SpokespersonUniversePanel`.

## §46 PART B — Ordinary operator character-create flow (SPA)

Trace: `/dashboard` → click "New spokesperson" → `/spokespeople/new`.

Fields shown (from `web/src/routes/spokespeople/new.tsx:107-171`):
- `Name` (required)
- `Business brief` (required)
- `Portrait` (optional — reveals a portrait upload widget)
- Submit button `Create spokesperson`.

Not shown:
- Workspace (implicit from `me.data.default_workspace.id`).
- Universe / World — no picker, no radio, no chip. Zero references to `universe` or `Universe` in the file.
- Draft / active toggle (`Teammate.Status` is bake-lifecycle; see §54).

API payload emitted (line 90-95):
```
{ workspace: <uuid>, name: <str>, business_brief: <str>, portrait_data_uri?: <base64> }
```

Backend persistence:
- Serializer accepts payload (`apps/spokespeople/serializers.py:41-95`); universe field defaults to NULL.
- `perform_create` fires optional avatar bake against media-engine; row is `SETUP_NEEDED` (or `READY` after successful bake).
- Persisted `universe_id`: `NULL`.

Subsequent Universe assignment happens post-hoc via
`SpokespersonUniversePanel` on the detail page. Assignment is
optional — no warning banner, no "incomplete" badge, no dashboard
call-out indicates a NULL-Universe teammate is anything other than
finished. The operator receives no signal that Universe assignment
matters.

## §47 PART C — NULL-Universe capability matrix

Source-derived from viewsets, retrieval, and clean-hook rejections.

| Capability | `universe=NULL` teammate works? | Different behavior vs Universe-bound teammate? | Evidence |
|---|---|---|---|
| Detail page (`/spokespeople/{id}`) | yes | none | `web/src/routes/spokespeople/$id.tsx` renders identically |
| Edit basic fields (name, business_brief, personality, voice etc.) | yes | none | serializer PATCH path |
| Portrait / avatar bake / rebake | yes | none | `perform_create` + `rebake_avatar` don't consult universe |
| Voice preset / bake | yes | none | independent of universe |
| Universe assignment (post-hoc) | yes | is the operation itself | `SpokespersonUniversePanel` PATCH with `universe-move-preview` |
| Delete + orphan-archive | yes | none | `apps/spokespeople/signals.py` pre_delete handles either state |
| CHARACTER-audience KD create with this teammate in M2M | yes IF the KD is also `universe=NULL` | doc lands `audience_scope=CHARACTER + universe=NULL` in legacy pool | `apps/embeddings/signals.py:117-138` allows both-NULL pairing only |
| CHARACTER-audience KD share with a Universe-bound teammate | **no** | signal rejects cross-Universe attach (`sp.universe=NULL` + `doc.universe=U_X` forbidden per SESSION 261 M2M contract) | `apps/embeddings/signals.py:108-110` |
| UNIVERSE-audience KD retrieval (`retrieve_for_teammate`) | **no** | LIST predicate branches on `spokesperson.universe_id is None → document.universe__isnull=True`; UNIVERSE-audience row must have `universe_id NOT NULL` (CheckConstraint `session276_universe_requires_universe_fk`) → impossible combination | `apps/embeddings/retrieval.py:211-247` |
| WORKSPACE-audience KD retrieval | yes | doc universe must be NULL (constraint `session276_workspace_forbids_universe_fk`), matches teammate's NULL filter | same |
| `retrieve_universe_canon` shared-tier lane | **no** | `if top_k <= 0 or universe is None or not cast: return []` — legacy dialogue gets no canon lane; mixed cast returns empty (`retrieval.py:362-374`) | same file |
| `retrieve_universe_memory` | **no** | Universe-scoped lane; NULL teammate has no Universe to key on | `apps/embeddings/retrieval.py` §"SESSION 264 Slice 2" |
| Episode cast (`EpisodeCast`) | **no** | `EpisodeCast.clean` explicitly rejects legacy teammate: "Teammate ... has no Universe (legacy). A Universe-scoped Episode cannot include a legacy Teammate in its cast" | `apps/universe/models.py:454-464` |
| Composition without Episode | yes | none | `apps/compositions/models.py` clean only rejects when Episode is attached |
| Composition WITH Episode (SESSION 262+) | **no** | `Composition.clean` rejects legacy spokesperson: "spokesperson has no Universe (legacy). A Universe-scoped Episode cannot attach a legacy Composition" | `apps/compositions/models.py:820-831` |
| NarrativeMemory | **no** | NarrativeMemory FKs Universe (NOT nullable, `apps/memory/models.py:170-175`); promoted from a Composition-with-Episode which itself requires Universe | derived |
| Talk / SpokespersonAskPanel (K6 synthesize with knowledge) | yes but shrunken corpus | uses `retrieve_for_teammate` → only WORKSPACE + legacy-CHARACTER docs available | `apps/spokespeople/views.py::ask` |
| Realtime avatar session | yes | independent of universe scope for the session itself | `apps/realtime/models.py` |
| Video generation | yes | independent | `apps/videos/` |
| Campaigns / bundles / assets | yes | workspace-scoped; independent | respective apps |

**Reading:** a NULL-Universe teammate can do everything a Universe-bound
teammate can do at the **workspace-tenant** layer (avatar, voice,
portrait, composition-without-episode, video, campaigns). It **cannot
participate in any Universe-anchored workflow** — no episodes, no
episode-derived memory, no shared-tier canon lane, no UNIVERSE-audience
knowledge, and CHARACTER-audience knowledge shares are restricted to
the shrinking legacy-legacy pool.

## §48 PART D — Knowledge composition boundary (Delta interaction)

Focus on the specific interaction between `Teammate.universe=NULL` and
the SESSION 276 Delta `audience_scope` model.

1. **CHARACTER-scoped Knowledge for a NULL teammate.**
   - Allowed: the doc must also be created with `universe=NULL`. The
     M2M signal (`apps/embeddings/signals.py:117-138`) rejects any
     non-NULL doc-universe when attaching a NULL sp (and vice versa).
   - Persisted shape: `audience_scope=CHARACTER + universe=NULL +
     spokespeople=[<NULL-sp>...]`.
   - Retrieval: `retrieve_for_teammate` filters to `document__universe__isnull=True`
     for NULL teammates, then the CHARACTER Q branch matches. Works.
2. **Multiple NULL-Universe characters sharing one CHARACTER doc.**
   - Allowed. All spokespeople must be NULL-universe; workspace must
     match. The legacy pool is fungible.
3. **NULL teammate receiving UNIVERSE-scoped Knowledge.** Impossible.
   `retrieve_for_teammate` narrows to `document__universe__isnull=True`
   for NULL teammates, but every UNIVERSE-audience doc has
   `universe_id NOT NULL` (Check `session276_universe_requires_universe_fk`).
   Zero rows.
4. **NULL teammate receiving WORKSPACE-scoped Knowledge.** Yes.
   `document.universe=NULL` matches, and `Q(audience_scope=WORKSPACE)`
   matches. This is the entire mechanical purpose of the WORKSPACE
   fallback branch today — Slice 21 §"Load-bearing properties" §3:
   "WORKSPACE is visible to legacy no-Universe teammates
   (universe filter enforces NULL-vs-NULL match)."
5. **Semantic retrieval semantics.** NULL-Universe CHARACTER knowledge
   is retrieved by exactly the same predicate as Universe-anchored
   CHARACTER knowledge (M2M presence + audience_scope=CHARACTER); the
   only difference is the universe scope. From the retrieval code's
   perspective, both are legitimate — the Delta enum treats
   `audience_scope=CHARACTER` as a first-class positive audience,
   regardless of universe.
6. **Universe-consistency guards on both-NULL pairings.** The M2M
   signal (`apps/embeddings/signals.py:112-115`) has an *explicit
   docstring exception* for the both-NULL pair: **"Allowed:
   `doc.universe = NULL` and `sp.universe = NULL` (legacy)."** This
   is a deliberate carve-out, not an accident. The signal was written
   to keep the legacy pool functional during the SESSION 261
   transition.

**Net product effect:** the Delta audience model is coherent for
NULL-Universe teammates *within the legacy pool*. As soon as any
Universe boundary is crossed (mixed teammates, or a UNIVERSE-audience
doc), the NULL teammate is silently excluded. The legacy pool has no
Universe-derived narrative continuity, no shared-tier canon lane, and
no route to UNIVERSE-audience content.

## §49 PART E — Episode / cast composition boundary

- Episode is Universe-scoped; `Episode.universe` is NOT NULL, CASCADE
  (`apps/universe/models.py:278-287`).
- `EpisodeCast.clean` at `apps/universe/models.py:446-481` enforces
  three invariants at attach time:
  1. `teammate.universe_id` must equal `episode.universe_id` (cross-Universe forbidden).
  2. `teammate.universe_id` must be non-NULL (**legacy teammates explicitly rejected**, with the operator-visible message: "A Universe-scoped Episode cannot include a legacy Teammate in its cast. Assign the Teammate to Universe ... first.").
  3. `teammate.workspace_id` must equal `episode.universe.workspace_id`.
- SPA behavior: `episode-cast-picker` filters to same-Universe teammates
  (see `web/src/routes/workspace/episode-cast-picker.test.tsx` for the
  contract). Legacy teammates would not appear as pickable.
- Consequence: **a NULL-Universe teammate cannot join any Episode**.
  Every narrative anchoring (title, cast, composition-with-episode)
  is invisible to them. To include Penny in an Episode, Chris must
  first assign her a Universe.

## §50 PART F — Memory / continuity composition boundary

- `NarrativeMemory.universe` is **NOT NULL** (`apps/memory/models.py:170-175`,
  CASCADE); denormalized from `Episode.universe`.
- `NarrativeMemory.source_composition` FK is RESTRICT-typed;
  NarrativeMemory is promoted from a Composition-with-Episode, which
  requires a Universe-bound spokesperson (§47).
- `retrieve_universe_memory` (SESSION 264 Slice 2) is Universe-keyed
  by construction.
- Consequence: **NULL-Universe teammates have no continuity boundary**
  — no promoted memories, no cross-composition narrative recall, no
  Universe-scoped memory retrieval at synthesis time. A NULL teammate's
  every conversation is contextually amnesic beyond the raw
  KnowledgeDocument corpus.

## §51 PART G — Current DB evidence

Query executed against `character_os` DB (port 5434), read-only. Only
`chriss-workspace` is analyzed (the four experimental workspaces from
Slice 2 §29 are scaffolding).

**Chris's real workspace ("Chris's workspace", 8 teammates):**

| Teammate | Universe | Created | Provenance class | Compositions | Videos | Episode cast rows |
|---|---|---|---|---|---|---|
| Ruby | Fox & Flour Bakery | 2026-07-23 | (universe-assigned) | — | — | — |
| Patch | Patch's Workshop | 2026-08-16 | (universe-assigned) | — | — | — |
| Rivet | Patch's Workshop | 2026-08-16 | (universe-assigned) | — | — | — |
| Mason | NULL | 2026-07-23 | A (pre-SESSION 261) | 1 | 0 | 0 |
| Penny | NULL | 2026-07-23 | A (pre-SESSION 261) | **58** | 0 | 0 |
| Mike | NULL | 2026-08-16 | A (pre-SESSION 261) | 3 | 0 | 0 |
| Repo Red | NULL | 2026-08-16 | A (pre-SESSION 261) | 4 | 0 | 0 |
| Riggs | NULL | 2026-08-17 | B/A boundary (same day as SESSION 261 landing) | 1 | 0 | 0 |

Observations:
- Only ONE real NULL-Universe teammate was created on/after the
  SESSION 261 substrate landing date (2026-08-17) — Riggs — and there
  is no evidence of intentional "keep me outside a Universe" intent
  (the SPA wizard has no such affordance to begin with).
- Zero NULL-Universe teammates appear in any Episode cast (as
  expected — `EpisodeCast.clean` blocks them).
- All 5 legacy teammates DO participate in Compositions (Penny alone
  has 58) — they are actively used, not abandoned rows. But every one
  of those compositions has `episode = NULL`, so no story continuity,
  no memory promotion, no shared-tier canon.
- **Classification:** 5/5 legacy teammates fit "A. clearly historical/legacy dogfood"; 0/5 fit "C. intentionally kept outside any Universe" (no source evidence supports that reading).

## §52 PART H — Historical intent (SESSION 259 → 261)

Cited from `UNIVERSE_BOUNDARY_V1.md` and `UNIVERSE_SCHEMA_V1.md`.

- **`UNIVERSE_SCHEMA_V1.md` §"Teammate.universe FK addition":** The
  FK was introduced as `null=True` (nullable) specifically because
  every existing teammate in `chriss-workspace` would have needed a
  data migration on Day 1; SESSION 261 opted for **opt-in
  prospective adoption** rather than forced backfill.
- **Teammate.universe helptext (source, `apps/spokespeople/models.py:86-89`):** > "World this teammate belongs to. NULL = legacy workspace-wide semantics (pre-SESSION 261)."
- **`UNIVERSE_BOUNDARY_V1.md` §"Working hypothesis" position 3:** "A Workspace may contain many Universes."
- **`UNIVERSE_BOUNDARY_V1.md` §"Working hypothesis" position 4:** "Characters, canon, relationships, locations, episodes, and shared world knowledge belong to a Universe." — future intent.
- **`UNIVERSE_BOUNDARY_V1.md` §Q1 opening:** the audit finding that motivated the Universe substrate was that "seven teammates spanning at least four unrelated fictional worlds ... cohabit `chriss-workspace`" — the current NULL-teammate population is the direct remainder of that inventory (Penny → Riverstone, Mike/Repo Red → dealership candidate, Mason → ambiguous, Riggs → ambiguous).
- Design docs treat `universe=NULL` as **"legacy"** in every context — helptext, invariants doc, retrieval commentary. Not "workspace-wide", not "unassigned by design", not "valid alternative state". The word chosen was "legacy" and it is used consistently.
- No design doc describes a **forward** use case for NULL-Universe teammates. The nullability is documented as a migration accommodation only.

**Historical verdict:** `universe=NULL` was **explicitly a transitional
compatibility state**, chosen to avoid a forced Day-1 backfill.
Universe-required at create was deferred, not designed as a permanent
optional state.

## §53 PART I — Falsification: does a legitimate modern "no Universe" use case exist?

For each candidate, ask whether current source/UI supports it.

| Candidate | Modern current support in source/UI? | Verdict |
|---|---|---|
| Reusable character shared across Worlds | No — `Teammate.universe` is single-value FK, not M2M; there is no cross-Universe character mechanism (see `UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md` — crossover deferred). NULL doesn't create this; it just opts out. | falsified |
| Generic workspace spokesperson | Backend permits it. Product-wise it means "excluded from every Universe-anchored feature" (§47). Not "generic" — "amputated." | falsified |
| Draft character not yet assigned | No lifecycle state expresses this. `Teammate.Status` is bake-lifecycle, not universe-lifecycle (§54). | falsified as a *represented* state; potentially useful as a *future* state if introduced |
| Template character | Not a Character OS concept today. No template model. | falsified |
| System / helper character | None persisted as a Teammate row. Would be an accounts / preferences concern. | falsified |
| Operator assistant | Same — not a spokesperson concept. | falsified |
| Character intentionally outside story continuity | Coherent in principle, but the SPA offers no way to express this intent and no post-CREATE surface communicates "this character is outside continuity." Currently indistinguishable from "operator forgot to assign a Universe." | not currently supported; would need affirmative product concept |
| Temporary creation state | Would require a real draft/active lifecycle (§54). Does not exist. | falsified |

No current source or UI evidence supports a modern legitimate "no
Universe" use case for an ordinary operator-created character. NULL
today is definitionally "everything Universe-based is unavailable, and
nothing else changes."

## §54 PART K — Active vs draft state (does a lifecycle already exist?)

- `Teammate.Status` = `SETUP_NEEDED | READY | ARCHIVED`
  (`apps/spokespeople/models.py:30-33`). Toggled by:
  - `SETUP_NEEDED → READY` when the avatar bake succeeds
    (`apps/spokespeople/views.py:424-425` on create; `:874` on rebake).
  - `→ ARCHIVED` via delete/archive path.
- Every current gate that consults `.status` is checking the
  **avatar/portrait bake state**, not Universe assignment.
- There is **no existing "draft-until-Universe-assigned" lifecycle**.
  Adding one would be a new state machine, not an enrichment of
  `Teammate.Status`.

So the "NULL as temporary construction state" reading is **not
mechanically expressible today**. If Chris wanted to model that, it
would be a Slice-4-or-later product concept, not an interpretation of
the existing schema.

## §55 PART L — Operator mental model

- The character-create wizard's helper text says "What this spokesperson
  is called inside the **workspace**." (`new.tsx:113`). The word "world"
  or "universe" is never used.
- The back-link at the top of the wizard is labeled **"Workspace"**
  (`new.tsx:187`) — reinforcing "you are creating a character *inside
  a workspace*", not "inside a world".
- The dashboard's `KnowledgeCorpusPanel` has a tiny sibling "Worlds"
  chip that Chris himself annotated as a discoverability compromise
  (SESSION 262 note in `dashboard/index.tsx:37-46`).
- The `Onboarding tour` component has three milestones: "hasSpokesperson",
  "hasKnowledge", "hasComposition". No milestone mentions Universe.
- `SpokespersonUniversePanel` is a post-hoc panel on the detail page;
  there is no banner, badge, or count on the dashboard telling Chris
  "N of your M spokespeople are unassigned to a World."

**Mental-model conclusion:** the SPA still communicates the older
model — "a character inside my Workspace." The backend model has
narrowed (Workspace = tenant, Universe = world) but the operator has
been offered no chrome or copy that would prompt him to think in
Universes at create time. This is the same class of drift as the
Knowledge lexical drift documented in Slice 1: architectural
narrowing without operator-UX propagation.

## §56 PART M — Hierarchy diagrams

**Current mechanical model (source-derived, unchanged from Slice 2 §34):**

```
Account (User)
  └─ Workspace                                    [tenant / security]
        ├─ Universe                              [world / cast / continuity]
        │    ├─ Teammate  (universe FK set)
        │    ├─ KnowledgeDocument (audience_scope in {CHARACTER, UNIVERSE})
        │    ├─ Episode → EpisodeCast → NarrativeMemory
        │    └─ (retrieve_universe_canon + retrieve_universe_memory lanes)
        └─ Teammate  (universe = NULL)           [legacy pool]
             └─ KnowledgeDocument (audience_scope in {CHARACTER (legacy pair), WORKSPACE})
             └─ Composition WITHOUT Episode
             └─ (retrieve_for_teammate over legacy docs only)
```

Legacy pool is fully functional at the composition-without-episode
layer but structurally *excluded* from every Universe-anchored
feature (episode, memory, canon lane, UNIVERSE-audience Knowledge).

**Emerging modern product inference (source-supported, NOT yet enforced):**

```
Account (User)
  └─ Workspace                                    [tenant / security]
        └─ Universe                              [world / cast / continuity]
             └─ Teammate  (universe REQUIRED)
                  ├─ CHARACTER-audience KDs (Universe-consistent M2M)
                  ├─ Episode participation
                  ├─ NarrativeMemory (Universe-anchored)
                  └─ Universe canon + memory retrieval lanes
```

Label the second diagram: **SOURCE-SUPPORTED PRODUCT INFERENCE**. It
is not established architecture — `Teammate.universe` remains
nullable — but every downstream Universe-aware feature enforces it de
facto by rejecting the legacy case. The two diagrams differ only in
whether `Teammate.universe` is optional or required.

## §57 PART N — Q-277-3 classification + Universe-required recommendation

**Classification:** **C — historical/compatibility state still
mechanically tolerated.** Justification: (a) no design doc describes a
forward NULL-Universe use case (§52 — every doc uses the word
"legacy"); (b) no source evidence supports a legitimate modern
use case (§53); (c) no lifecycle expresses NULL as a construction
state (§54); (d) every DB observation is consistent with pre-SESSION 261
residue (§51); (e) every Universe-aware feature (Episode,
NarrativeMemory, UNIVERSE-audience retrieval, canon lane) explicitly
rejects NULL teammates rather than accommodating them; (f) the SPA
never asks the operator whether they want a Universe.

Weak carve-out: NULL is not *harmful* — legacy teammates still work
for composition-without-episode + WORKSPACE-audience knowledge. So it
is C with a small "still-functions-in-a-shrinking-envelope" footnote,
not classification D ("mixed — specific modern use cases remain").

**Should new ordinary characters require explicit Universe?** **LIKELY YES,
BUT ANOTHER QUESTION MUST BE ANSWERED FIRST.**

The prerequisite is the same class of gap Slice 2 identified: the SPA
has no first-class Universe-management UX. Specifically, before we can
require a Universe at teammate-create, we must answer:

- Is there a low-friction "create your first Universe" onboarding path
  a fresh operator can complete on the way to creating their first
  character? Today: no. Universe creation lives at
  `/workspace/universes`, discoverable via a 10px chip on the Knowledge
  tile.
- What happens to Chris's 5 real legacy teammates (Mason, Penny, Mike,
  Repo Red, Riggs) — do we (a) migrate them to Universes with an
  operator-driven backfill flow, (b) leave them as a permanent legacy
  pool with a visible badge, or (c) archive them? SESSION 276 §340
  established that dogfood data is disposable, but Penny has 58
  compositions and archiving those unread would be a real signal loss.
- If Universe is required at create, is the SPA wizard the correct
  place to also let the operator create a new Universe inline, or
  does the create-Universe step have to happen first as a separate
  gesture?

Answering these three prerequisites is upstream of the
"require-Universe-at-create" implementation decision.

## §58 PART O — Effect on the proposed Knowledge UI

Slice 1 §17 recommended a Knowledge audience picker with three peer
choices; Slice 2 §35 demoted WORKSPACE to "Advanced". Slice 3 further
sharpens the model.

**If (and only if) every ordinary character belongs to exactly one
Universe**, the ordinary Knowledge mental model becomes:

```
Where does this knowledge belong?
    → pick a World / Universe
Who there should know it?
    → Everyone in <World>
    OR
    → Just these characters:  [multi-select of that World's characters]
```

Advantages of this shape (evaluated against the permanent Delta model):
- Every audience choice becomes *automatically Universe-consistent* —
  the M2M signal's cross-Universe rejection becomes impossible-by-UI
  rather than impossible-by-post-hoc-error.
- CHARACTER assignment is expressible at CREATE (fixes the primary
  gap identified in Slice 1 §17).
- The `spokespeople.length` filter constraint (§47) is enforceable by
  the picker itself: once the operator picks a World, the multi-select
  is scoped to that World's roster.
- WORKSPACE audience gracefully falls off the primary picker (Slice 2
  recommendation) — it becomes a system/preferences concept anchored
  at the Workspace level, not a per-KD audience choice.
- The audience question ("Where does this knowledge belong?") sits at
  the same conceptual level as the character-create question ("Which
  World is this character in?") — consistent operator vocabulary
  across two surfaces.

But this shape depends on Universe-required-at-create. As long as a
teammate can be `universe=NULL`, the picker must retain either a
"legacy" branch or a "no World — restricted to legacy characters"
option, reintroducing the exact lexical drift Slice 1 identified.

**Net effect on WORKSPACE audience:** under Slice 2 + Slice 3 combined,
WORKSPACE audience is a compatibility path serving exactly one
population — the legacy NULL-Universe teammate pool. Once Chris either
migrates or archives those 5 teammates and requires Universe at create,
WORKSPACE audience has no remaining ordinary-operator use case.
Reposition it as a *system preference* surface (operator-wide
directives, cross-tenant policy), not a knowledge-document audience.

## §59 Slice 3 findings — separated

**OBSERVED FACT (source):**
- SPA wizard does not send `universe` at create; every wizard-created
  teammate lands `universe=NULL` (`web/src/routes/spokespeople/new.tsx:87-100`).
- Serializer accepts `universe` optionally with no positive-value
  requirement (`apps/spokespeople/serializers.py:41-149`).
- `Teammate.Status` is bake-lifecycle only, not Universe-lifecycle
  (`apps/spokespeople/models.py:30-33`, `views.py:329,424-425,874`).
- Six enforcement sites explicitly reject legacy teammates from
  Universe-aware features: `EpisodeCast.clean` (`universe/models.py:454-464`);
  `Composition.clean` (`compositions/models.py:820-844`); M2M signal
  cross-Universe rejection (`embeddings/signals.py:108-110`);
  `retrieve_for_teammate` universe-branching (`embeddings/retrieval.py:211-214`);
  `retrieve_universe_canon` (`retrieval.py:362-374`);
  `NarrativeMemory.universe` NOT NULL (`memory/models.py:170-175`).

**SOURCE-DERIVED FACT:**
- The both-NULL M2M pairing is an explicit design carve-out (docstring
  at `signals.py:112-115`), not an accident — the legacy pool was
  intentionally preserved during the SESSION 261 transition.
- A NULL teammate's retrieval envelope shrinks to
  `document.universe=NULL` (legacy CHARACTER + WORKSPACE only) —
  it never reaches UNIVERSE audience.
- `retrieve_universe_canon` returns empty for legacy dialogue
  (`retrieval.py:362`), so legacy-teammate synthesis loses the
  shared-tier canon lane silently.

**OPERATOR OBSERVATION:**
- Chris's operator observation from the SESSION 277 handoff and from
  Slice 2 review remains active: he no longer knows what Workspace
  represents in the current product. Slice 3 finds an analogous gap
  at the character-create layer — the wizard silently produces
  NULL-Universe teammates and offers no signal that this is a
  degraded state.

**INFERENCE:**
- `universe=NULL` today is best described as "everything Universe-based
  is unavailable to this character, but nothing else changes." That
  is not a modern product concept; it is a compatibility silhouette.
- The current 5 real legacy teammates are pre-SESSION-261 residue.
  Only Riggs was created on/after the SESSION 261 landing date, and
  the SPA still gives no way to affirmatively opt out of a Universe —
  so even his NULL state is "the default the wizard produces," not
  "a state Chris deliberately chose."
- The recommendation to require Universe at create is well-supported
  by every downstream feature enforcement point; the blocker is
  operator UX (no first-Universe onboarding path), not architectural
  incoherence.

**PRODUCT RECOMMENDATION (Chris + ChatGPT to decide):**
- Treat `universe=NULL` as a **transitional compatibility state**, not
  a permanent product option.
- Before requiring Universe at teammate-create, land one prerequisite:
  a first-Universe onboarding path (either inline-in-the-wizard or a
  guided-once-per-workspace flow), and a decision about the 5 legacy
  teammates (migrate / badge / archive).
- After those two prerequisites, remove nullability from
  `Teammate.universe` (mirror of what SESSION 276 did for
  `KnowledgeDocument.audience_scope`) and treat the Knowledge UI as
  Universe-primary per §58.
- Do **not** attempt any of this in Slice 4 without an explicit
  scope-lock.

## §60 Unresolved questions (Slice 3 — deferred)

- Should the SPA character-create wizard grow a Universe picker with
  an inline "create a new World" option, or should Universe creation
  remain a separate up-front gesture?
- What is the right treatment for Chris's 5 current legacy teammates?
  Migration to Universes (Penny → Riverstone, Mike/Repo Red →
  Dealership, Mason/Riggs → ?), permanent legacy pool with a visible
  badge, or archival?
- If Universe becomes required at teammate-create, does the SPA also
  gain a Universe switcher / management surface (Slice 2 §38 already
  flagged this class of gap)?
- If WORKSPACE audience is repositioned as a system preference, where
  does it live? Settings? A dedicated "workspace policy" surface? A
  future Membership/agency-tier surface?
- Does the "one character in exactly one Universe" model rule out
  future cross-World characters (a personified assistant that appears
  in both bakery and workshop episodes)? If yes, is that acceptable
  given the current explicit position that cross-Universe access is
  deferred (`UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md`)?

## §61 PART P — Smallest next falsifiable question

Given Slice 3's findings, the smallest next question is a scoped
**prerequisite** question, not a Knowledge UI question.

> **Q-277-4** — What is the smallest UI/product change that lets a new
> operator create their first Universe on their way to creating their
> first character, without redesigning the spokesperson wizard or the
> `/workspace/universes` surface, and without requiring a data
> migration for Chris's 5 existing legacy teammates?

This is the question that stands between "we know Universe should be
required at create" and "we can safely change the create flow." It is
a UI-scoping question with three plausible shapes to evaluate:

1. **Inline `<Create a new World>` option in the spokesperson wizard's
   Universe picker.** Zero navigation, one new gesture.
2. **Onboarding banner on the dashboard** when a workspace has zero
   Universes but ≥1 teammate. Redirects to `/workspace/universes/new`,
   returns to the dashboard on completion.
3. **A single scope-locked onboarding step** that gates the "New
   spokesperson" button until at least one Universe exists in the
   workspace.

Answering Q-277-4 is a design exercise (not an implementation)
producing a scope-locked recommendation for the smallest change that
makes Universe-required-at-create safe. Do not implement without an
explicit follow-up scope lock.

**Alternate smaller experiments** (present, do not select):
- Static banner on the spokesperson detail page for NULL-Universe
  teammates: "This spokesperson isn't in a World yet. They cannot
  participate in Episodes, canon retrieval, or Universe knowledge."
  A read-only visibility fix; tests whether Chris ever picks a
  Universe once the consequence is made visible.
- SPA form validation that requires Universe at create *only* when at
  least one Universe already exists in the workspace. Zero migration;
  smallest possible enforcement; falls back gracefully for zero-Universe
  workspaces.
- Return to Slice 1's Q-277-2 Knowledge UI (three peer choices, one
  screen) with an explicit "legacy character mode" branch — accept the
  Slice-1 lexical drift as a permanent cost of keeping legacy
  supported, and revisit the require-Universe question separately.

## §62 Slice 3 landed SHA

_Landed SHA: `647f139` (Slice 3 audit commit)._

---

# Slice 4 — Q-277-4 — MINIMUM VALID UNIVERSE CREATION CONTRACT (audit-only)

Chris + ChatGPT reviewed Slice 3. NULL-Universe teammate classified C
(historical compatibility). Universe-required-at-create endorsed in
principle, gated on one prerequisite: is Universe creation cheap
enough that inline-in-the-wizard is safe? Slice 4 answers that
prerequisite.

## §63 Penny operator-history correction (recorded before substantive investigation)

Chris clarified the significance of the Slice 3 §51 finding "Penny has
58 compositions." Recording per the three-line contract the SESSION 277
prompt requires:

- **OBSERVED FACT:** Penny has 58 compositions attached in the DB
  (`Composition.objects.filter(spokesperson=<Penny>).count() == 58`);
  every one has `episode = NULL`.
- **OPERATOR CONTEXT:** those compositions belong to an obsolete
  dogfood / content-generation era — Penny has not been used since the
  newer Patch + Rivet development flow began. The Penny-era work was
  closer to "Can I make a commercial?", produced by a substantially
  older content-generation model + workflow. Chris considers the
  outputs materially outdated compared with current Patch/Rivet-era
  character-driven content.
- **PRODUCT CONSEQUENCE:** Penny's existence should NOT block new-character
  Universe requirements and should NOT force preservation of the legacy
  NULL-Universe product model. General SESSION 276 §340 rule stands —
  dogfood data provides evidence without becoming a permanent product
  requirement.

Slice 4 does **not** mutate Penny. Slice 3's classification (C) stands;
its recommendation ("LIKELY YES on require-Universe, prerequisite is
first-Universe onboarding UX") is now sharpened — Penny is not the
blocker; the actual blocker is the cost/ergonomics of creating a
Universe. Slice 4 investigates only that cost.

## §64 Slice 4 baseline

- HEAD @ Slice 4 open: `38a55d0` (Slice 3 SHA-record). Clean, pushed.
- Substrate: KD=0, KC=0, `chriss-workspace` teammates=8 (unchanged),
  Universes=2 (unchanged). Zero drift since Slice 3.
- Read-only. No source/data changes.

## §65 Slice 4 checklist

- [x] STEP 0 — verify baseline + insert Penny operator-history correction.
- [x] PART A — inventory every Universe create path.
- [x] PART B — exact model requirements + minimum valid row.
- [x] PART C — exact API contract + minimum valid POST body.
- [x] PART D — current SPA create-World flow.
- [x] PART E — immediate-usability test (Teammate / KD / Episode / cast / memory / retrieval / composition).
- [x] PART F — name / slug / identity semantics.
- [x] PART G — zero-Universe fresh account scenario.
- [x] PART H — existing-Universe scenario.
- [x] PART I — inline-create feasibility classification A/B/C/D/E.
- [x] PART J — separate-onboarding-necessity assessment.
- [x] PART K — legacy-character coexistence analysis.
- [x] PART L — Penny-specific record (deferred; see §63).
- [x] PART M — effect on the Knowledge model.
- [x] PART N — terminology (Universe vs World in current copy).
- [x] PART O — Q-277-4 answer + product recommendation.
- [x] PART P — smallest next falsifiable question.
- [ ] Commit + push; SHA-record.

## §66 Q-277-4

> What is the minimum valid operator input required to create a fully
> usable Universe / World in current Character OS, and can that existing
> creation contract safely support an inline "Create new World" action
> inside the ordinary character creation flow without duplicating or
> bypassing important Universe configuration?

Companion:

> If a fresh operator has zero Universes and clicks "Create character",
> can Character OS create the required World with a tiny amount of
> operator input and then continue character creation coherently?

## §67 Prediction (before source inspection)

Prediction: Universe creation is **already extremely cheap** — a single
required field (`name`) plus the implicit workspace, with slug
auto-derived. A minimally-created Universe is immediately usable for
Teammate assignment, KD creation, Episode creation, and every
Universe-aware retrieval lane. Inline-create feasibility will land at
**A (trivially feasible)** or **B (feasible with small shared-component
work)**. Separate onboarding is unlikely to be necessary. Legacy NULL
teammates coexist trivially — DB nullability does not need to change
in this slice.

_(This prediction is falsifiable by finding any of: additional required
fields hidden in the serializer, a post-create dependency step
enforced by signals, or a validation gate that makes a name-only
Universe unusable for downstream Universe-aware features.)_

## §68 PART A — Universe create-path inventory

Grep across `shell/apps/`, `shell/apps/*/management/`, and
`web/src/` for `Universe.objects.create` / `POST /api/universes/` /
`createUniverse`.

| Create path | Required fields | Optional fields | Defaults | Operator-visible? |
|---|---|---|---|---|
| SPA `/workspace/universes` → `CreatePanel` → `POST /api/universes/` (`web/src/routes/workspace/universes.tsx:118-193` → `web/src/lib/api/universes.ts:117-141`) | `workspace`, `name` | `description` | slug auto-derived; archived_at=NULL; created_by=request.user | primary — the operator's create surface |
| Direct API `POST /api/universes/` | `workspace`, `name` | `description` | same | dev/automation path |
| Django admin (`apps/universe/admin.py:6-27`) | same | same | same | staff-only |
| Test factories (`apps/universe/tests/**`) | `workspace`, `name` when explicit | — | — | not product |
| No management commands create Universes (`grep Universe.objects.create` in `shell/apps/*/management/` → zero non-test hits). | — | — | — | — |
| No post_save / pre_save signals fire on Universe (`apps/universe/signals.py` only defines `m2m_changed` on `Episode.cast`; no save-side receivers anywhere for Universe). | — | — | — | — |

**Conclusion:** exactly two product-shaped create paths — SPA and
direct API — with identical contracts. No hidden second-step
requirement, no signal-driven side-effects on Universe creation.

## §69 PART B — Exact model requirements + minimum valid row

Universe fields (`shell/apps/universe/models.py:33-165`), classified
per the prompt schema:

| Field | Requirement class | Source |
|---|---|---|
| `id` (UUID) | E — generated automatically | `default=uuid.uuid4` |
| `workspace` (FK, CASCADE) | A — required from operator (or B if inferred from `?workspace` context) | line 55-59; NOT NULL |
| `name` (Char 120) | A — required from operator | line 63-71; `clean()` rejects blank; `validate_name` also rejects blank |
| `slug` (Slug 140) | E — generated automatically via `save()` | line 76-84 (`db_index=True` implicit via SlugField); `save()` at line 144-165 auto-derives from name with per-workspace collision suffix |
| `description` (Text, blank=True, default="") | C — optional | line 89-96 |
| `created_by` (FK User, SET_NULL, null=True) | B — required but safely derived (stamped by viewset from `request.user`) | line 100-106; `perform_create` sets it at `views.py:67-73` |
| `created_at` / `updated_at` | E — generated | `auto_now_add`, `auto_now` |
| `archived_at` (nullable) | D — defaulted (NULL = active) | line 115 |

Uniqueness: `(workspace, slug)` unique constraint
(`universe_unique_slug_per_workspace` at line 120-124). Not `(workspace, name)` — names are NOT unique; only slugs.

Related-object requirements at create time: **none**. No membership
row is created; no default Universe knowledge; no default cast; no
first Episode; no first NarrativeMemory.

**Minimum valid database row:**

```
Universe(
    id=<generated>,
    workspace=<the operator's workspace>,
    name="Fox & Flour Bakery",     # only operator-required field
    slug=<auto-derived by save()>,
    description="",                # default
    created_by=<request.user>,     # stamped by view
    archived_at=NULL,              # default
)
```

## §70 PART C — Exact API contract + minimum valid POST body

Serializer: `apps/universe/serializers.py::UniverseSerializer` (Meta
lines 37-68).

- **Payload-required fields:** `workspace` (UUID), `name` (non-blank string).
- **Payload-optional fields:** `description` (defaults to blank).
- **Payload-forbidden (read-only in serializer):** `id`, `workspace_name`, `slug`, `created_by`, `created_at`, `updated_at`, `archived_at`, `teammate_count`, `knowledge_document_count`, `episode_count`.
- **Slug is NOT operator-supplied**; the SlugField is in `read_only_fields`. Auto-derivation runs server-side.
- **Validation:**
  - `validate_workspace` (line 74-84) — rejects with 403-equivalent 400 if the caller is not a Membership of the workspace.
  - `validate_name` (line 91-96) — rejects blank/whitespace-only.
- **Duplicate name behavior:** allowed. Two Universes with the same name in the same workspace produce distinct slugs (`foo` and `foo-2` via `save()`'s per-workspace collision loop).
- **Cross-workspace protection:** `validate_workspace` + `Universe.workspace` FK CASCADE together prevent cross-workspace Universe attach.
- **Permission class:** `IsWorkspaceMember` (`apps/universe/views.py:41`). On create, `has_permission` requires only `is_authenticated`; per-workspace membership is enforced by `validate_workspace` before save.
- **Post-create side effects:** none beyond `perform_create` stamping `created_by`. No signals, no cascade seeds, no dependent-row creation.
- **Error contract:** DRF `ValidationError` → 400 `{field: [messages]}`.

**Minimum valid API request:**

```
POST /api/universes/
Content-Type: application/json
Authorization: <session/cookie>

{"workspace": "<workspace-uuid>", "name": "Fox & Flour Bakery"}
```

Response (201): full Universe serialized (id, slug auto-derived,
teammate/KD/episode counts = 0, description="", archived_at=null,
created_by=<user id>).

## §71 PART D — Current SPA create-World flow

Route: `/workspace/universes` (`web/src/routes/workspace/universes.tsx`).

Discoverability: three entry points — nav rail has no Universes item;
dashboard `KnowledgeCorpusPanel` has a 10px "Worlds" chip
(`web/src/routes/dashboard/index.tsx:582-588`); `/workspace/universes`
also reachable by URL. Slice 2 §27 already flagged this as thin
discoverability.

Fields shown on `CreatePanel` (line 118-193):
- `Name` — single-line Input, required, `maxLength=120`, placeholder `"e.g. Workshop, Bakery, Riverstone"`.
- `Description (optional)` — textarea, `min-h-[80px]`.

Helper text: **"Pick a name; describe it in a sentence. Slug is auto-derived."**

Submit behavior: sends `{workspace, name, description?}`, invalidates
the `["universes", "list", workspaceId]` query, clears the form
in place. Operator stays on `/workspace/universes` and sees the new row
in the list below.

Steps: **one form, one submit.** Zero navigation between fields and
submit. No advanced fields, no templates, no presets.

Immediately available after create: yes — the Universe row exists,
the SPA lists it, and every downstream Universe-aware feature can
reference it by UUID immediately (see §72).

**Verdict:** Universe creation is fundamentally **simple**, not
configuration-heavy.

## §72 PART E — Immediate usability test (source-derived, no runtime)

Given a Universe row with only `workspace + name + auto-slug + created_by`:

| Downstream feature | Immediately usable? | Source evidence |
|---|---|---|
| Assign a Teammate (`Teammate.universe = <new-universe>`) | yes | `apps/spokespeople/serializers.py:126-149` — only cross-workspace consistency check |
| CHARACTER-audience Knowledge (M2M attach) | yes | M2M signal (`apps/embeddings/signals.py:93-154`) requires `sp.universe_id == doc.universe_id`; a fresh Universe with matching teammates just works |
| UNIVERSE-audience Knowledge (`audience_scope=UNIVERSE + universe=<new>`) | yes | Delta serializer (`apps/embeddings/serializers.py:311-330`) accepts `universe` as the positive audience marker; CheckConstraint `session276_universe_requires_universe_fk` satisfied |
| Episode creation (`Episode.universe = <new-universe>`) | yes | `apps/universe/models.py:278-287` — only `universe` FK required plus `title` + `operator_topic` (both operator-supplied at Episode create) |
| EpisodeCast (`teammate.universe_id == episode.universe_id`) | yes as soon as ≥1 teammate is assigned to this Universe | `EpisodeCast.clean` at line 446-481 |
| NarrativeMemory (Universe-anchored) | yes as soon as a Composition-with-Episode promotes one | `apps/memory/models.py:170-175` denormalizes universe from Episode |
| `retrieve_universe_canon` shared-tier lane | yes as soon as ≥1 KD exists in the Universe | `apps/embeddings/retrieval.py:305-440` — key is `universe_id`, no seed row required |
| `retrieve_universe_memory` | yes (same shape as canon) | `retrieval.py` §"SESSION 264 Slice 2" |
| Compositions | yes | independent of Universe unless attached to an Episode |

**Nothing requires a second setup step.** The minimal Universe is
immediately operational across every Universe-aware feature. No
default KD is required, no default cast is required, no seed
Episode is required.

## §73 PART F — Name / slug / identity semantics

- **Name.** Single Char 120 field. Not unique per workspace (§69). Operator-visible identity handle. `__str__` at `universe/models.py:133-134` returns `f"{self.name} ({self.workspace.name})"`.
- **Slug.** Auto-derived by `save()` at line 144-165 from `slugify(name)`; collision handled by suffixing `-2`, `-3`, ... per workspace. Unique per workspace (`universe_unique_slug_per_workspace`). Server-side only — the SPA never asks for it.
- **Durable identity:** UUID `id`, not slug. Every FK across the codebase references `Universe.id`. Slug is a URL routing convenience (`/workspace/universes/:id` today uses id, not slug — see `universes.$id.tsx`).
- **Rename safety.** `Universe.save()` regenerates the slug only when `self.slug` is empty. Renaming an existing Universe does NOT change the slug (line 149 `if not self.slug`). Safe by default.
- **Duplicate names.** Legal at the DB layer; distinguished only by slug suffix. Operators would see two "Fox & Flour Bakery" rows sharing a name — no rejection, no warning. That's a UX opportunity for a future slice; not a blocker for inline create.
- **Description.** Blank by default; no downstream feature reads it. `Universe.description` is a management-surface field per its help text (line 89-96) — "Not consumed by synthesis; purely a management surface field." Omitting it has zero functional consequence.

**For an inline create,** a name is sufficient. Nothing beyond a name
is required for correctness or to avoid later problems. Slug will be
auto-derived; description can be added later on the Universe detail
page.

## §74 PART G — Zero-Universe fresh account scenario

Fresh operator: workspace exists (created by allauth signup /
`default_workspace_for`), zero Universes, zero characters.

**Current path** (SPA today, before any change):
1. Operator clicks "New spokesperson" → `/spokespeople/new`.
2. Fills name + business_brief (+ optional portrait).
3. Submit → `POST /api/spokespeople/` with no `universe` field.
4. Backend creates `Teammate` with `universe=NULL`.
5. Character exists as a legacy NULL-Universe teammate.
6. Downstream: as documented in Slice 3 §47 — locked out of Episodes,
   Universe-audience knowledge, canon/memory lanes.

**Hypothetical path** (evaluate only; no implementation):
1. Operator clicks "New spokesperson".
2. Wizard shows a Universe picker; empty list; picker offers "+ Create a new World" inline.
3. Operator types "Fox & Flour Bakery"; inline sends `POST /api/universes/ {workspace, name}` (this is the exact minimum request from §70).
4. Response returns new Universe UUID; picker selects it automatically.
5. Operator submits the character form; SPA sends `POST /api/spokespeople/ {workspace, name, business_brief, universe: <new-uuid>}`.
6. Backend creates `Teammate` with `universe=<new-uuid>`.

**Backend obstacles:** none. Every step uses existing endpoints in
their documented shape. Universe create endpoint is idempotent-safe
in the sense that a repeated submission produces a distinct Universe
with a suffixed slug (no partial-state risk). Teammate serializer
already accepts `universe` via its default ModelSerializer field
(`spokespeople/serializers.py:53`); it just isn't sent by today's SPA
payload.

## §75 PART H — Existing-Universe scenario

Existing: Fox & Flour + Patch's Workshop (Chris's real workspace).

Would adding a Universe selector to the existing wizard suffice?

- **API already accepts universe?** Yes (`spokespeople/serializers.py:41-149`; universe field, optional, cross-workspace validated).
- **SPA payload simply omits it today?** Yes (`web/src/lib/api/spokespeople.ts:157-184` — `CreateSpokespersonInput` does not include `universe`).
- **Character serializer validates workspace/Universe consistency?** Yes (`spokespeople/serializers.py:126-149`).
- **Universe list already available through an API hook?** Yes (`web/src/lib/api/universes.ts:74-96` `useUniverses(workspaceId)`, used today by `UniverseScopePicker` on the Knowledge screen).
- **Extra backend work required?** None.

**This distinguishes cleanly:** the gap is **UI debt** (SPA doesn't
render a Universe picker at create time and doesn't send the field in
the payload), not a **backend capability gap**. Both the serializer
and the query hook already exist.

## §76 PART I — Inline-create feasibility

Evaluate an inline "+ Create new World" gesture within character creation.

Can the inline create safely:

1. **Ask for minimal required fields?** Yes — a single Name input is
   sufficient (§73).
2. **POST the Universe?** Yes — reuse `useCreateUniverse` (which the
   `/workspace/universes` CreatePanel already uses).
3. **Receive the new Universe ID?** Yes — the mutation returns the
   full `Universe` payload including `id`.
4. **Select it automatically in the picker?** Trivial — set the
   picker's state to the returned UUID.
5. **Continue the character-create submission?** Yes — same
   `useCreateSpokesperson` call with `universe: <new-uuid>` added.

Without:
- **Bypassing validation?** Not bypassed — both endpoints run their
  standard serializer validation independently.
- **Duplicating substantial Universe setup?** Nothing to duplicate;
  Universe setup is a single name field.
- **Creating partially configured Worlds?** No partial state exists
  in the model — a name-only Universe is fully valid (§72).
- **Requiring navigation?** No — both requests fire from the wizard.
- **Changing backend models?** No.

The only latent concern is **error-recovery UX**: if the character
POST fails after the Universe POST succeeds, the operator has a
Universe row and no character. That's not a data-integrity problem
(the Universe is a legitimate stand-alone row) but it is a
"what-just-happened" cliff for the operator. Mitigation is
front-end-only (a retry that reuses the just-created Universe id).

**Classification: A — trivially feasible.** Zero backend changes; two
existing endpoints; one existing API hook; the only new SPA work is
UI plumbing to render the picker + optional inline create + include
the universe field in the payload.

_(Note: this is the strongest possible answer to the falsification
premise. If Chris + ChatGPT want a more conservative reading — e.g.
inline-create-with-shared-form-component reuse of `CreatePanel` from
`universes.tsx` — that's classification B. Either way, no larger
onboarding redesign is required.)_

## §77 PART J — Do we even need a separate onboarding flow?

Given §72-§76:

- Universe creation is single-name-field.
- No signals, no seed rows, no configuration required.
- SPA form already exists.
- Character wizard has a natural place for the picker + inline create.
- Backend accepts `universe` at teammate create.

**Answer: no separate onboarding flow is required to make
Universe-required-at-create safe.** The character wizard can carry
the entire prerequisite through inline create.

A dashboard banner, gated onboarding, separate World setup page, or
multi-step wizard would be ceremony without operator payoff. The
smallest coherent product surface is: **augment the existing
spokesperson wizard with a Universe picker + inline "+ Create new
World" option**.

_(Onboarding-shaped alternatives remain worth considering later for
first-time-user education, but they are **not** blockers for
require-Universe-at-create. That is Slice 4's specific finding.)_

## §78 PART K — Legacy-character coexistence

Slice 3 §57 identified the "existing NULL rows remain readable/usable +
SPA future CREATE requires Universe" model as compatible in principle.
Slice 4 confirms mechanically:

- `Teammate.universe` remains `null=True` at the DB layer. The 5
  current legacy teammates (Mason, Penny, Mike, Repo Red, Riggs) keep
  their rows unchanged.
- Requiring `universe` only at the **SPA payload layer** (SPA form
  validation + zod schema on `CreateSpokespersonInput`) blocks NEW
  legacy creation without disturbing existing rows.
- Every current view/queryset already handles both states (`universe=NULL`
  branch in `retrieve_for_teammate` at `retrieval.py:211-214`;
  `SpokespersonUniversePanel` reads current value and offers assignment).
- No source invariant requires making the DB column NOT NULL to stop
  new legacy creation. Payload-layer + serializer-layer requirement
  is sufficient.

**Compatibility rule** (proposed for Chris + ChatGPT, not implemented):
> Existing legacy characters continue functioning under compatibility
> behavior. New ordinary characters stop creating new legacy state.
> DB column stays nullable; SPA + serializer stop accepting NULL on
> create.

This mirrors the SESSION 276 Delta pattern precisely: nullability is
frozen at the DB layer until the SPA has stopped producing NULLs, at
which point a future slice can flip the column NOT NULL.

## §79 PART L — Penny (deferred)

Per §63: Penny's 58 compositions are historical dogfood. She stays
untouched in Slice 4. Future Chris may create a Riverstone Universe
and migrate her, recreate her, archive her, or ignore her — that
decision is downstream of the Universe-required-at-create question,
not a prerequisite for it.

## §80 PART M — Effect on the Knowledge model

If new characters land under Universe-required create (§76-§78), the
downstream Knowledge model becomes:

```
World (Universe)
    ↓
Knowledge belongs here
    ↓
Everyone in <World>
    OR
Specific character(s) in <World>
```

**Consequence for the ordinary Knowledge UI:**
- The picker's placeholder question becomes "Where does this knowledge belong?" with the choice list being the operator's Universes.
- The audience sub-question becomes "Who there should know it?" — Everyone / just these characters (multi-select scoped to the picked Universe's roster).
- The "None (legacy — visible to workspace-wide legacy teammates only)" option (Slice 1 §11) has **no ordinary use case remaining**: it exists today only to serve the shrinking legacy NULL-Universe pool, and new characters no longer enter that pool.

**Consequence for WORKSPACE audience:**
- Serves only the 5 legacy teammates (§78) and any KDs already created
  under that shape.
- Reposition as a **system/preferences concept**, not a
  KnowledgeDocument audience choice — matches Slice 2 §35 recommendation
  and Slice 3 §58 sharpening.

**Consequence for the Delta CheckConstraints:**
- No change required. `session276_universe_requires_universe_fk`,
  `session276_workspace_forbids_universe_fk`,
  `session276_none_requires_inactive` remain load-bearing exactly as
  today. Universe-required-at-create for Teammate does not touch KD
  invariants.

## §81 PART N — Terminology observation

- Universe create page title uses **"Universes"** (`SectionHeader number={1} title="Universes"` at `universes.tsx:48`) and **"Your worlds."** as the h1 (line 53).
- Empty state: **"No worlds yet"** (line 105-106).
- Create panel: **"Create a world"** (line 146-147).
- List heading: **"Worlds"** (line 71).
- Row description: **"N teammates, M docs, slug <slug>"** (line 229-234).
- Nav rail (Slice 2 §27) has no Universes item; the sole dashboard entry is a "Worlds" chip.

The SPA is already predominantly using **"World(s)"** as the operator-facing word; "Universe" appears as the section marker but the everyday copy is "world". An inline gesture reading **"+ Create new World"** would be consistent with existing SPA copy and would not require a terminology sweep. Universe/World terminology cleanup is a separate concern (Slice 2 §38 already noted the synonym pair) and does not block Slice 4's recommendation.

## §82 PART O — Q-277-4 answer

1. **Minimum operator fields to create a fully usable Universe:** ONE — `name`. Workspace is implicit from `me.data.default_workspace.id` in the SPA (still sent explicitly in the API payload). Slug is server-generated. Description is optional and has zero functional consequence.
2. **Whether a new Universe is immediately operational:** **YES.** No signals, no seed rows, no dependent-row creation. Every Universe-aware feature (Teammate assignment, CHARACTER + UNIVERSE audience KDs, Episode create, EpisodeCast, NarrativeMemory, canon and memory retrieval lanes, Compositions) works immediately by referencing the new Universe UUID.
3. **Inline-create feasibility:** **A — trivially feasible.** Zero backend changes required. Two existing endpoints (`POST /api/universes/`, `POST /api/spokespeople/`); one existing API hook (`useCreateUniverse`); one existing query hook (`useUniverses`). Only new work is SPA UI plumbing.
4. **Whether a separate onboarding flow is necessary:** **NO.** The character wizard can carry the entire prerequisite through inline create. Onboarding ceremony would add friction without operator payoff.
5. **Whether existing NULL teammates block enforcing Universe on NEW SPA character creation:** **NO.** DB nullability stays. Legacy rows continue functioning. New rows stop creating legacy state via SPA-payload-layer + serializer-layer positive-value requirement. Mirror of the SESSION 276 Delta pattern (freeze representation before flipping DB column).

**Product recommendation** (Chris + ChatGPT to decide; do not implement in this slice):
- Confirm the **inline-Create-World-inside-character-wizard** as the smallest coherent product surface.
- Scope-lock exactly the SPA changes needed (Universe picker + inline "+ Create new World" + payload change + serializer positive-value guard) — do not bundle DB nullability changes, do not bundle legacy migration, do not bundle Knowledge UI reshape.
- The Knowledge UI reshape (Slice 1 §17 → Slice 2 §35 → Slice 3 §58 → Slice 4 §80) becomes the *next* slice after Universe-required-at-create ships and legacy stops accreting.

## §83 Slice 4 findings — separated

**OBSERVED FACT (source):**
- Universe serializer marks `slug`, `created_by`, `created_at`, `updated_at`, `archived_at`, and counts as `read_only_fields` (`apps/universe/serializers.py:56-66`).
- `validate_name` rejects blank/whitespace-only name (`serializers.py:91-96`).
- `perform_create` stamps `created_by` from `request.user` (`views.py:67-73`); no other post-create logic.
- No `post_save`/`pre_save` signals on Universe anywhere in the codebase (`apps/universe/signals.py` only defines `m2m_changed` on Episode.cast).
- SPA `CreatePanel` collects only Name + optional Description (`web/src/routes/workspace/universes.tsx:118-193`).
- Teammate serializer already accepts `universe` (`apps/spokespeople/serializers.py:41-149`); SPA payload just omits it today.
- Both `useCreateUniverse` and `useUniverses` API hooks already exist (`web/src/lib/api/universes.ts:74-141`).

**SOURCE-DERIVED FACT:**
- Two visually-distinct create paths (SPA, direct API) share one serializer with identical minimum requirements.
- Duplicate Universe names in one workspace are legal; slugs collide via per-workspace suffix loop.
- `Universe.description` is documented as management-surface only and consumed by no synthesis path.
- SPA copy already uses "World(s)" as the operator-facing term for `/workspace/universes`.

**OPERATOR HISTORICAL CONTEXT (Chris):**
- Penny's 58 compositions belong to an obsolete "Can I make a commercial?" dogfood era, produced with a substantially older content-generation model. They provide evidence, not a permanent product requirement.

**INFERENCE:**
- Requiring Universe at new-character-create is a SPA/serializer change only, not a schema change. DB nullability can safely lag by design.
- The gap between "backend can already do this" and "operator can do this" is UI plumbing — the same class of gap Slice 3 identified for Teammate creation, and Slice 1 identified for Knowledge audience.
- Inline "+ Create new World" is the smallest coherent implementation because Universe creation is single-field and every downstream feature is immediately operational.

**PRODUCT RECOMMENDATION (Chris + ChatGPT decision, not implementation):**
- Adopt the compatibility rule (§78): existing legacy characters continue functioning; SPA + serializer stop accepting new NULL-Universe creates.
- Scope Slice 5 (if approved) to the minimum SPA change to require Universe at teammate-create + serializer positive-value guard. No other changes bundled.
- Defer Knowledge UI reshape to a subsequent slice (Slice 6+) once legacy stops accreting.

## §84 Unresolved questions (Slice 4 — deferred)

- Should the SPA's compatibility rule land as a client-side zod required validation, or also as a serializer-level positive-value requirement mirroring the SESSION 276 Delta `audience_scope_required_on_create` pattern? (Both together is defense-in-depth; either alone gets us most of the way.)
- Duplicate Universe names — legal today, potentially confusing when a picker lists two "Fox & Flour Bakery" rows. Is this something to reject at the API layer (add `(workspace, name)` unique) or handle in the picker with a distinguishing badge?
- Terminology: SPA uses "World" predominantly and "Universe" as a section marker. Chris + ChatGPT to decide whether an inline gesture should read "+ Create new World" (consistent with existing empty-state and h1 copy) or "+ Create new Universe" (consistent with the URL and the section header).
- Error recovery: what happens if the Universe POST succeeds but the character POST fails? Front-end-only mitigation (retry reuses the just-created Universe id); acceptable or does it need a rollback path?
- Should the inline picker default to "the operator's most-recently-used Universe" when Universes already exist? Zero-Universe case sends the operator into inline create; single-Universe case could pre-select; multi-Universe case requires explicit pick.

## §85 PART P — Smallest next falsifiable question

Given Slice 4's evidence (inline create trivially feasible), the
smallest next question is implementation-adjacent — a **scope-lock
question** rather than an audit question:

> **Q-277-5** — If the SPA `/spokespeople/new` wizard adds a required
> Universe picker with an inline "+ Create new World" option that
> POSTs `{workspace, name}` to the existing `/api/universes/` endpoint
> and then includes `universe: <uuid>` in the character POST, does
> this change: (a) fully prevent new `universe=NULL` teammate creation
> through the SPA, (b) leave the 5 existing legacy teammates
> untouched, and (c) require zero backend model changes, zero
> migrations, and zero Knowledge UI changes? Or does implementation
> expose a gap not visible from source inspection alone (for example:
> a hidden auto-select behavior that would still fire on payload
> omission, or a client-caching interaction that would race the
> Universe create/select cycle)?

Answering Q-277-5 requires a small implementation experiment — the
wizard change itself. It is the natural implementation slice, but
Chris + ChatGPT should approve the exact scope before it lands.

**Alternate smaller questions** (present, do not select):
- **Q-277-5-alt-A** (defense-in-depth prompt): should the serializer ALSO require a positive `universe` on create (mirroring Delta `audience_scope_required_on_create`), or is SPA-only zod validation sufficient given the SESSION 276 pattern?
- **Q-277-5-alt-B** (terminology-first): before touching the wizard, spend one micro-slice on Universe-vs-World copy consistency across the SPA so the inline gesture wording is settled first.
- **Q-277-5-alt-C** (dogfood-first): with today's UI unchanged, run the fresh SESSION 277 handoff dogfood (three audience creations from the current Knowledge UI). Use the observed friction to confirm that reshaping the wizard first is the right ordering vs reshaping the Knowledge UI first.

## §86 Slice 4 landed SHA

_Landed SHA: TBD (SHA-record commit after Slice 4 lands)._

