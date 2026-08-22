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

_Landed SHA: `c9131af` (Slice 4 audit commit)._

---

# Slice 5 — Q-277-5 — Universe-required character creation (IMPLEMENTATION)

Chris + ChatGPT approved Slice 4 and authorized the first implementation
slice. Scope: make World membership explicit + required for new
ordinary character creation, with inline "+ Create new World" so a
fresh operator with zero Worlds is never sent out of the wizard.
Legacy `universe=NULL` teammates remain untouched. No DB migration.

## §87 Slice 5 baseline

- HEAD @ Slice 5 open: `f7fc0cc` (Slice 4 SHA-record). Clean, pushed.
- Substrate: KD=0, KC=0; `chriss-workspace` teammates=8, Universes=2 —
  identical to Slice 4 baseline. Zero drift.

## §88 Q-277-5

> If `/spokespeople/new` adds a required World picker with inline
> "+ Create new World", sends the selected World UUID in the character
> CREATE payload, and the backend independently rejects new
> NULL-Universe ordinary characters, does this fully stop NEW legacy
> state while preserving all existing legacy teammates and requiring
> no model migration?

## §89 Files changed (exact scope)

| File | Kind | What |
|---|---|---|
| `shell/apps/spokespeople/serializers.py` | edit | `TeammateSerializer.validate()` — add CREATE-only positive-Universe guard raising `universe_required_on_create` when `self.instance is None and universe is None`. UPDATE path unchanged. |
| `shell/apps/spokespeople/tests/test_universe_required_on_create.py` | new | 8 regression tests: create-without-universe → 400 (structured code); explicit-null → 400; valid universe → 201; cross-workspace guard still fires; legacy PATCH without universe → 200; legacy row LIST/GET → 200; legacy PATCH-add-universe → 200. |
| `shell/apps/spokespeople/tests/test_rebake_avatar.py` | edit | Two pre-existing tests updated to pass `universe: str(u.id)` in the create POST (added `_universe(ws)` helper). |
| `shell/apps/spokespeople/tests/test_step4d_canonical_migration.py` | edit | Eight pre-existing tests updated with the same helper + payload field. |
| `web/src/lib/api/spokespeople.ts` | edit | `CreateSpokespersonInput` gains `universe?: string`. |
| `web/src/components/spokesperson-wizard.tsx` | edit | Import `useUniverses`/`useCreateUniverse`; extend `WizardState.identity` with `universe: string \| null`; wire step-1 + step-4 gate; new `WorldPicker` component (select + inline create form with sentinel `__CREATE__`); include `universe` in the create POST payload. |
| `web/src/components/spokesperson-wizard.world-picker.test.tsx` | new | 6 regression tests: Next disabled without World; no auto-select even for single-Universe workspace; select existing World enables Next; picking "+ Create new World…" opens inline form; inline submit selects the new World and enables Next; cancel preserves prior selection. |

**Not touched:** `web/src/routes/spokespeople/new.tsx` (only the wizard
was reshaped; the legacy escape hatch behind `?legacy=1` will get a
clean 400 from the backend if someone uses it). No DB migration.
`Teammate.universe` remains `null=True` on the model. Knowledge UI
untouched. Existing legacy teammates untouched.

## §90 Behavior before/after

**Backend serializer — CREATE**

| Payload | Before Slice 5 | After Slice 5 |
|---|---|---|
| `{workspace, name, business_brief}` (no `universe`) | **201** — Teammate created with `universe=NULL` (legacy) | **400** — `{"universe": {"code": "universe_required_on_create", "detail": "..."}}` |
| `{workspace, name, business_brief, universe: null}` | 201 — legacy | 400 — same code |
| `{workspace, name, business_brief, universe: <uuid>}` | 201 — Universe-bound | 201 — unchanged |
| `{workspace, name, business_brief, universe: <cross-workspace-uuid>}` | 400 — cross-workspace | 400 — cross-workspace (unchanged; pre-existing guard fires first) |

**Backend serializer — UPDATE / PATCH**

| Payload | Before | After |
|---|---|---|
| PATCH legacy row `{business_brief: "..."}` (no universe) | 200 | **200** — unchanged (Slice-5 guard is CREATE-only; `self.instance is not None` skips it) |
| PATCH legacy row `{universe: <uuid>}` | 200 | 200 — unchanged (SESSION 261 assignment path preserved) |
| GET legacy row detail | 200 | 200 — unchanged |
| LIST including legacy rows | present | present — unchanged |

**SPA wizard — Step 1 gate**

| State | Before | After |
|---|---|---|
| Name + brief filled, no World picked | Next enabled | **Next disabled** (`canAdvance` now also requires `identity.universe != null`) |
| Name + brief filled, existing World picked | Next enabled | Next enabled — unchanged |
| Zero Worlds in workspace, no "+ Create new World" chosen | not applicable (no picker) | Placeholder "— Pick a World —" holds; Next disabled |
| Zero Worlds, "+ Create new World…" chosen + name submitted | not applicable | Inline `POST /api/universes/` fires; new UUID auto-selected; Next enables |

**SPA wizard — auto-selection**

- Never. Even a workspace with exactly one Universe leaves the picker
  at "— Pick a World —" per Slice 5 §"Scope lock" ("World membership
  must be an intentional operator decision during dogfood"). This is
  enforced by the picker's default state (`identity.universe: null`
  in `INITIAL_STATE`) plus the "— Pick a World —" `disabled`
  placeholder option.

**SPA wizard — Step 4 submit payload**

- Before: `{workspace, name, business_brief, personality?, visual_subject?, visual_template, tone_archetype, portrait_data_uri?, voice_preset?}`.
- After: same fields plus `universe: <uuid>` (the World the operator picked on Step 1). A `state.identity.universe == null` check at the top of `onSubmit` refuses to fire the mutation as a third defense layer.

## §91 Tests added / touched

**New:**
- `shell/apps/spokespeople/tests/test_universe_required_on_create.py` — 8 backend tests. All pass.
- `web/src/components/spokesperson-wizard.world-picker.test.tsx` — 6 SPA tests. All pass.

**Existing tests updated for the new payload requirement** (added
`_universe(ws)` helper + `universe: str(u.id)` in each create POST;
no behavior change):
- `shell/apps/spokespeople/tests/test_rebake_avatar.py` — 2 tests.
- `shell/apps/spokespeople/tests/test_step4d_canonical_migration.py` — 8 tests.

## §92 Test results

**Slice-5 regression file (backend):** 8/8 pass in 4.47s.
```
test_create_without_universe_returns_400 PASSED
test_create_with_explicit_null_universe_returns_400 PASSED
test_create_with_valid_universe_returns_201 PASSED
test_create_with_cross_workspace_universe_returns_400 PASSED
test_patch_existing_legacy_row_without_universe_returns_200 PASSED
test_patch_legacy_row_to_add_universe_returns_200 PASSED
test_get_existing_legacy_row_returns_200 PASSED
test_list_includes_legacy_rows PASSED
```

**Slice-5 regression file (SPA):** 6/6 pass in ~0.5s.
```
keeps Next disabled when name+brief are filled but no World is picked ✓
does NOT auto-select when exactly one World exists (Slice 5 scope-lock) ✓
enables Next once an existing World is selected ✓
opens the inline create surface when '+ Create new World…' is picked ✓
submits inline create, selects the new World, and enables Next ✓
cancels inline create without changing the current selection ✓
```

**Full SPA test suite:** 662 passed / 662 total (50 files). No regressions.

**Change-adjacent backend regression** (spokespeople + universe +
embeddings + compositions + memory + identity + realtime + videos +
accounts + billing): **2302 passed / 2302 total** in 253s. Zero
regressions attributable to Slice 5.

**Full backend suite:** 80 pre-existing failures observed
(76 in `bootstrap_review` — missing frozen candidate fixture data,
`InvalidCandidate: candidate.json not found`; 1 in
`test_media_engine_timeouts.py` — stale `DOWNSTREAM_DEADLINES_S`
manifest missing `image_overlay`; 3 in `apps.spokespeople.tests.test_ask`
which need `EMBEDDING_FORCE_MOCK=1`, which was set — but reruns
show they intermittently pass when the reused-DB fixture cache is
warm; noise, not regression). **None are in code paths this slice
touches**; all pre-date it. Recorded here so future readers can rule
them out.

## §93 Q-277-5 verdict

**CONFIRMED.**

- (a) NEW legacy state fully stopped through the SPA. The wizard
  cannot submit without a World (Step-1 gate + Step-4 defense layer +
  onSubmit guard). Verified by the SPA regression's `wizard-next
  disabled` assertions and by `wizard-world-selected` reflecting the
  chosen UUID before submit is enabled.
- (a) NEW legacy state also stopped through the direct API. Backend
  serializer rejects `universe=NULL` or omitted-`universe` CREATE
  with `HTTP 400 {"universe": {"code": "universe_required_on_create",
  "detail": "..."}}`. Verified by the two backend rejection tests.
- (b) Existing legacy teammates untouched. Verified by
  `test_patch_existing_legacy_row_without_universe_returns_200`,
  `test_patch_legacy_row_to_add_universe_returns_200`,
  `test_get_existing_legacy_row_returns_200`, and
  `test_list_includes_legacy_rows`. Real-DB inspection at Slice 5
  close (§94) shows Chris's 5 legacy teammates unchanged.
- (c) Zero backend model changes, zero migrations, zero Knowledge UI
  changes. Verified by `git diff --stat` (no `.py` file under
  `apps/*/models.py` changed; no file under `apps/*/migrations/`
  changed; no file under `web/src/routes/workspace/knowledge*` or
  `web/src/components/knowledge-panel*` changed).

**No hidden behavior surfaced:** the specific concerns Slice 5 §"Q-277-5
falsification target" flagged were checked one by one during
implementation and did not fire:
- Serializer defaults / omission handling — the new guard treats both
  omission and explicit `null` identically (§90); the
  `test_create_with_explicit_null_universe_returns_400` test locks
  that in.
- Existing auto-selection behavior — none exists at the SPA layer;
  `identity.universe` starts as `null` and stays `null` until the
  operator picks. The `does NOT auto-select when exactly one World
  exists` regression pins that.
- Create/update serializer coupling — the guard's `self.instance is
  None` check cleanly separates CREATE from UPDATE; the two legacy
  PATCH tests confirm.
- React Query cache invalidation after inline World creation — the
  existing `useCreateUniverse` mutation already invalidates
  `["universes", "list", workspaceId]` on success
  (`web/src/lib/api/universes.ts:133-141`); the new World appears in
  the picker's list naturally on the next render. No manual cache
  invalidation added.
- Stale World lists — the mutation's `mutateAsync` resolves with the
  full Universe payload, so the picker selects by UUID directly
  without waiting for the list refetch. No race window between
  create and select.
- Race between World POST and character POST — the wizard is
  sequential: World creation completes (`await create.mutateAsync`)
  before `dispatch({type: "SET_IDENTITY", patch: {universe: world.id}})`
  fires, and the character POST only fires from Step 4's submit
  button, well after Step 1 has closed the inline create panel.
- Workspace scoping — the inline create passes
  `workspace: workspaceId` from `useMe`, matching the character
  create's workspace; the serializer's pre-existing
  cross-workspace guard would still reject any mismatch.
- Accidental legacy-row mutation — none. All Slice-5 code paths
  are additive: the serializer adds a branch that only fires on
  CREATE; the SPA adds a picker whose only backend calls are `POST
  /api/universes/` (creates a new row, never touches existing
  teammates) and the pre-existing `POST /api/spokespeople/`.

## §94 Runtime state at Slice 5 close (read-only)

Re-verified against local DB (`DB_PORT=5434`), read-only:

- KnowledgeDocument = 0, KnowledgeChunk = 0 (substrate unchanged).
- `chriss-workspace` teammates = 8 (unchanged — Mason, Penny, Mike,
  Repo Red, Riggs still legacy; Ruby, Patch, Rivet still
  Universe-bound).
- Universes = 2 (unchanged — Fox & Flour Bakery, Patch's Workshop).
- No Slice-5 code path mutated any of these rows.

## §95 Findings — separated

**OBSERVED FACT (source/test):**
- Backend `TeammateSerializer.validate()` at
  `shell/apps/spokespeople/serializers.py:126-186` now branches on
  `self.instance is None and universe is None` and raises a
  structured `universe_required_on_create` ValidationError.
- SPA `SpokespersonWizard` `INITIAL_STATE.identity.universe = null`;
  `canAdvance()` for step 1 and step 4 both require
  `state.identity.universe != null`; `onSubmit` refuses when
  `state.identity.universe == null` as a third defense layer.
- SPA `WorldPicker` renders a `<select>` with placeholder + existing
  Worlds + `+ Create new World…` sentinel option; picking the
  sentinel opens an inline form (name only) that POSTs `/api/universes/`
  via the existing `useCreateUniverse` mutation; on success the
  new UUID becomes selected.
- 8 backend + 6 SPA new tests pass; 2302 change-adjacent backend
  regressions pass.

**SOURCE/TEST-DERIVED FACT:**
- The Slice 5 change is fully additive at the code-path level. Every
  pre-existing successful create path continues to succeed as long as
  the caller supplies a Universe. Pre-existing tests that POST
  without `universe` needed the payload updated (10 tests, 2 files);
  no test needed a behavior change.
- React Query cache-invalidation behavior is byte-identical to the
  existing `/workspace/universes` CreatePanel because the inline
  wizard variant reuses the same `useCreateUniverse` hook.
- Terminology: the SPA already used "World" throughout
  `/workspace/universes` copy (h1, empty state, CTA button); the
  Step-1 picker's `<Label>World</Label>` + placeholder `"— Pick a
  World —"` + sentinel `"+ Create new World…"` are consistent with
  that existing vocabulary. No terminology sweep performed
  (per scope lock).

**OPERATOR CONTEXT:**
- Penny's 58 compositions belong to an obsolete dogfood era (Slice 4
  §63) and were NOT a blocker for this slice. Slice 5 confirms that
  by preserving Penny (and the other 4 legacy teammates) untouched
  while stopping NEW legacy creation.

**INFERENCE:**
- The compatibility rule proposed in Slice 4 §78 ("existing legacy
  characters continue functioning; new ordinary characters stop
  creating new legacy state") is achievable and now enforced. DB
  nullability can lag indefinitely; the SPA-layer + serializer-layer
  positive-value requirement is sufficient to stop legacy accretion.
- The natural next surface to reshape is the Knowledge UI (§80),
  now that new characters land Universe-bound. But per the scope
  lock, dogfood evidence comes first.

**PRODUCT DECISION (recorded, not further implemented in this slice):**
- Ship Slice 5 to Chris for dogfood before touching Knowledge UI.
- If dogfood succeeds, Slice 6 candidates are (a) reshape Knowledge
  UI around World / audience as recommended in §80; or (b) revisit
  the LegacyCreateForm escape hatch (which currently would fail
  ungracefully behind `?legacy=1`) — either delete it, or add a
  matching World picker.

## §96 Dogfood boundary — instructions for Chris

**Please dogfood the following two flows in the SPA. Do NOT ingest
Knowledge (that's a separate future slice); focus on character
creation.**

### Sequence A — Create a character in an EXISTING World

1. Navigate to `/dashboard`.
2. Click "New spokesperson" (or "+ New" from the masthead).
3. On Step 1, fill in Name (e.g. `Test Bakery Character`) and
   Business Brief (any short paragraph, ≥ 8 characters).
4. Under the new **World** label, use the select and pick either
   **Fox & Flour Bakery** or **Patch's Workshop**.
5. Confirm: the "Selected World" hint appears below the select showing
   the UUID.
6. Click Next. Step 2 should load.
7. Add a portrait (any of Upload / Camera / Generate).
8. Click Next, then Next through Voice (Skip is fine).
9. On Step 4 Confirm, click "Create spokesperson".
10. Expected: the wizard proceeds to `/spokespeople/<id>/welcome`.
11. Verify: the newly-created teammate appears in `/workspace/universes/<world>` "Members" list (or Teammate list) as a Universe-bound spokesperson.

### Sequence B — Create a character in a BRAND-NEW World inline

1. Navigate to `/dashboard`.
2. Click "New spokesperson".
3. On Step 1, fill in Name and Business Brief as above.
4. Under **World**, open the select and pick **"+ Create new World…"**
   (bottom of the list).
5. Expected: the inline create panel appears with a "New World name"
   input.
6. Type a World name (e.g. `Dogfood Test World`).
7. Click "Create World".
8. Expected: the panel closes, the picker returns to the select in
   its normal position, the "Selected World" hint appears showing
   the new UUID, and the newly-created World is now one of the
   options in the select.
9. Continue Step 2 → Step 3 → Step 4 as in Sequence A.
10. Click "Create spokesperson".
11. Expected: the new character is created inside the new World; the
    World also appears in `/workspace/universes` list.

### Negative-path check (Sequence C — optional)

1. Start "New spokesperson".
2. Fill Name + Brief but do NOT pick a World.
3. Expected: the "Next" button at the bottom of Step 1 is disabled.
4. Do NOT click submit; navigating back to the dashboard is fine.

### What to report back

- Whether the picker feels intuitive on Step 1 (or whether "World"
  belongs elsewhere in the flow).
- Whether the inline "+ Create new World…" gesture feels like the
  right ergonomic (or whether we should force a separate
  `/workspace/universes/new` navigation).
- Whether the "Selected World: <uuid>" copy is useful or clutter
  (a name would be nicer but requires threading; deferred).
- Whether either flow behaves unexpectedly at any step — copy issue,
  race, error message, cache staleness, missing option in the picker.
- Any surprise wrt existing teammates. (You shouldn't see any — but
  if a legacy teammate's detail page now behaves differently, that's
  a bug we want to catch.)

Do NOT create the "Dogfood Test World" in a way that would clutter
production for long. It can be archived from
`/workspace/universes/<id>` after the dogfood run.

## §97 PART P — Smallest next falsifiable question (after dogfood)

Deferred until Chris's dogfood evidence is in. If dogfood succeeds
cleanly, the smallest next question is:

> **Q-277-6** — Now that new characters are guaranteed to be
> Universe-bound and the shrinking legacy pool is frozen, does the
> Knowledge audience picker (Slice 1 §17 → Slice 2 §35 → Slice 3
> §58 → Slice 4 §80 collapsed shape "Where does this belong? →
> Who there should know it?") work cleanly when tested against the
> operator's actual creation intent for CHARACTER, UNIVERSE, and
> WORKSPACE audiences?

If dogfood exposes friction (picker feels misplaced, inline create
UX is confusing, or a specific edge case surfaces), the next slice
narrows to that friction rather than moving on to Knowledge UI.

## §98 Slice 5 landed SHA

_Landed SHA: `3d988c1` (Slice 5 implementation commit)._

---

# Slice 6 — Q-277-6 — World / business semantic ownership audit (audit-only)

Chris + ChatGPT began operator dogfood after Slice 5. Slice 5 remains
provisionally accepted (new character creation now Universe-bound;
legacy pool preserved). The dogfood surfaced an upstream semantic
question about where the identity of a business/world actually lives.
Slice 6 investigates only that question. Zero mutation.

## §99 Slice 6 baseline

- HEAD @ Slice 6 open: `623ade4` (Slice 5 SHA-record). Clean, pushed.
- Substrate: KD=0, KC=0 (no Knowledge added during dogfood — expected).
- `chriss-workspace` teammates=**8→8**, Universes=2 (unchanged; Tyson was created via the wizard as documented below and is included in the count).

## §100 Dogfood evidence (Chris's Tyson run)

**OBSERVED FACT (real-DB, `DB_PORT=5434`):**
- `Teammate` "Tyson" exists in `chriss-workspace`, id
  `f4de81f3-ef65-4196-a50e-38cfc6d1854f`, `universe=Fox & Flour
  Bakery`, `status=ready`, created 2026-08-22.
- Tyson's `business_brief` is 342 chars; `personality` is 335 chars.
- `KnowledgeDocument.objects.count() == 0` — no Knowledge added during
  or after the Tyson run.
- Fox & Flour Universe: id `1a0af807-dd6a-47cd-bfaa-3d088f1c105f`,
  `description=""` (0 chars), 2 teammates (Ruby + Tyson), 0 KDs, 2
  episodes.
- Patch's Workshop Universe: id `56d16b63-652e-4f54-bc7e-39114bbfc4c5`,
  `description="First world for Patch and Rivet"` (31 chars — a note,
  not a semantic definition), 2 teammates (Patch + Rivet), 0 KDs,
  27 episodes.

**OBSERVED FACT (operator flow, from Chris + ChatGPT report):**
- Chris opened `/spokespeople/new` (post-Slice-5 wizard).
- Step 1 required the Slice-5 World picker. Chris explicitly picked
  **Fox & Flour Bakery** from the select. No auto-select fired
  (confirmed by the Slice-5 regression + real-DB evidence).
- Chris entered the character's Name = "Tyson" and a Business Brief
  describing the coffee-and-counter side of Fox & Flour (342 chars in
  the resulting row).
- Wizard advanced through portrait, voice, and confirm without new
  friction attributable to Slice 5.
- Character created successfully; navigation to `/spokespeople/<id>/welcome`.
- Welcome page displayed something like "Meet Tyson." with a summary
  of what Tyson currently knows (name / personality / brief / voice)
  and what Tyson does NOT yet know (menu / pricing / policies /
  customer-facing details). Welcome page presented action **"Teach
  Tyson about your business"**.
- Chris clicked "Teach Tyson about your business". The SPA routed
  him to the **generic Knowledge page (`/workspace/knowledge`)** with
  the four tabs (Paste / Upload PDF / URL / Search) and the
  `UniverseScopePicker` at the top requiring re-selection of
  `World / Universe`, still including the option `None (legacy —
  visible to workspace-wide legacy teammates only)`.
- The operator-context handoff was NOT preserved: neither Tyson nor
  Fox & Flour was pre-filled on the Knowledge screen.

## §101 Chris's operator historical recollection (RECORDED, REQUIRES VERIFICATION)

Chris stated approximately:
- Fox & Flour was created around Ruby; Ruby's identity/business material described both Ruby AND Fox & Flour.
- Knowledge/PDF material about the bakery was later uploaded that described the business.
- Patch's Workshop developed similarly around Patch; Patch-related material likely describes both Patch and the Workshop.
- The modern World/Universe substrate was introduced/evolved later.

Not a repository fact until verified. Slice 6 verifies each claim:

**Claim 1: Fox & Flour was created around Ruby / business_brief carried both.**
- **CONFIRMED by git history.** `1b80ebf` (2026-05-13, SESSION 107) introduced `Spokesperson` (later renamed `Teammate` in `175342f` 2026-08-06) with `business_brief` from day one, described in the commit as: > "One-paragraph description of the business this spokesperson represents. Promoted up from the legacy per-campaign brief_prompt."
- **CONFIRMED by current DB state.** Ruby's business_brief (330 chars) is essentially the definition of Fox & Flour: > "Ruby owns Fox & Flour Bakery, a neighborhood artisan bakery known for naturally leavened sourdough, handcrafted pastries, seasonal desserts, and custom celebration cakes. The bakery focuses on locally sourced ingredients, small-batch baking, and creating a warm community gathering place where every customer feels like a regular."
  The paragraph does not distinguish Ruby's personal traits from the business's identity — both are packed together.

**Claim 2: Ruby/Patch PDFs and knowledge material combined character + business details.**
- **CONFIRMED by git history.** Commit `70e3113` (2026-08-20, SESSION 273 §15) landed the KnowledgeDocument `74e7f18f-5b77-459c-bc36-b4ab617d8aca` — "Fox & Flour Bakery — Working Knowledge" — 6,599 chars, ingested via production `ingest_text` into the Fox & Flour Universe. The source material lives in the repo at `docs/design/session_273_experiment_data/03_slice_alpha_proposed_knowledge_document.md`. Its content mixes business facts (sourdough starters, bread lineup, pricing by weight, day-old discount, food-shelf donation) with Ruby's authored details (Ruby maintains the starters; Ruby's motive). This document was Universe-scoped (`audience_scope=UNIVERSE`) — a first-class attempt at World-owned knowledge.
- SESSION 274 (`SESSION_274_UNIVERSE_SHARED_KNOWLEDGE_DOGFOOD.md` §1) explicitly framed the model as > "**Universe-shared knowledge** (facts every character in a Universe should be allowed to know) **+ character-specific knowledge** (expertise for one particular character in that Universe)."
- That doc was subsequently wiped as part of the SESSION 276 §340 disposable-dogfood reset. **KD count today: 0.** The Universe-shared knowledge existed, was validated, and was disposed of. The current Universe rows retain no trace of it.

**Claim 3: Universe substrate was introduced later.**
- **CONFIRMED.** `Teammate.universe` FK landed in commit `ef10d4e` (2026-08-17, SESSION 261 Phase 2) — ~3 months after `business_brief` (2026-05-13). The Universe app itself, `UNIVERSE_SCHEMA_V1.md`, and `UNIVERSE_BOUNDARY_V1.md` also landed in SESSION 261.

**Verdict:** Chris's recollection is accurate. business_brief pre-dates Universe by three months; the historical Fox & Flour Universe-shared KD existed and confirmed the "Universe-shared + character-specific" product model; the current substrate contains only the character-owned brief and no Universe-shared semantic.

## §102 Q-277-6

> Where does the semantic identity of a World/business actually live
> in current Character OS?
>
> Can the current Fox & Flour Universe meaningfully represent "Fox &
> Flour Bakery" independently of Ruby, or is the actual business/world
> definition still primarily stored on Ruby and associated Knowledge?

Companion specimen: same question for Patch's Workshop / Patch.

## §103 Prediction (before source inspection)

Prediction: **B → E** (primarily character-owned; ownership has drifted).
The Universe row is expected to be structurally load-bearing but
semantically thin (name + slug + optional description that nothing
reads); business_brief is expected to be the actual semantic carrier
because it pre-dates Universe by design. Fox & Flour is expected to
"exist" independently of Ruby only as a name — with Ruby removed and
the ingested Fox & Flour KD gone (SESSION 276 reset), no semantic
definition remains on the Universe itself.

## §104 Slice 6 checklist

- [x] STEP 0 — verify baseline; record Tyson dogfood + Knowledge handoff + operator historical recollection.
- [x] PART A — Universe semantic payload.
- [x] PART B — Character semantic payload.
- [x] PART C — business_brief lineage.
- [x] PART D — synthesis composition map.
- [x] PART E — Fox & Flour forensic specimen.
- [x] PART F — Patch's Workshop forensic specimen.
- [x] PART G — historical PDF / Knowledge evidence.
- [x] PART H — multi-character contradiction / precedence.
- [x] PART I — World-without-character test.
- [x] PART J — character-without-business-duplication thought experiment.
- [x] PART K — semantic ownership classification.
- [x] PART L — business_brief overload classification.
- [x] PART M — onboarding-consequence analysis.
- [x] PART N — Slice-5 invariant remains sound analysis.
- [x] PART O — Knowledge handoff consequence.
- [x] PART P — generalization test.
- [x] PART Q — composition-boundary verdict.
- [x] PART R — Q-277-6 answers.
- [x] PART S — smallest next falsifiable question.
- [ ] Commit + push; SHA-record.

## §105 PART A — Universe semantic payload

Universe model (`shell/apps/universe/models.py:33-165`).

| Universe-owned field/state | Structural or semantic? | Used by synthesis? |
|---|---|---|
| `id` (UUID) | structural (identity) | no |
| `workspace` (FK) | structural (tenant) | no directly (used by queryset filters) |
| `name` (Char 120) | semantic-adjacent (operator-facing label) | referenced by `retrieve_universe_canon`'s cast-Universe check via `universe.name`, but never emitted into a prompt |
| `slug` (auto-derived) | structural (URL routing) | no |
| `description` (Text, blank default="") | **claims to be semantic** | **NO — grep `\.description` across `shell/character_os/` and `shell/apps/universe/` returns zero synthesis hits.** Model help text explicitly says "Not consumed by synthesis; purely a management surface field." |
| `created_by` / `created_at` / `updated_at` / `archived_at` | structural / audit | no |
| Reverse `teammates` (M2M via FK) | structural (containment) | consumed by cast filters, not as identity |
| Reverse `knowledge_documents` (FK on KD) | structural (scoping) | consumed by retrieval as scope, not as identity |
| Reverse `episodes` (FK) | structural (containment) | consumed by cast + composition scoping |
| Reverse `narrative_memories` (FK, `apps/memory/models.py:170`) | structural | consumed by `retrieve_universe_memory`, keyed by universe_id |

**Verdict:** the Universe row's only Universe-owned semantic field is
`description`, and **no synthesis path reads it**. Every other
semantic-flavored consumer of a Universe pulls data from related
objects (KD chunks, memories, teammates) — not from the Universe row
itself. The Universe today is **structurally rich, semantically empty**.

## §106 PART B — Character semantic payload

Teammate model (`shell/apps/spokespeople/models.py:27-...`).

| Field | Semantic category | Used by synthesis? |
|---|---|---|
| `id` / `workspace` / `universe` | structural / scoping | scope filters |
| `name` (Char 120) | identity (character name) | referenced by every prompt |
| **`business_brief`** (Text) | **claims character identity + business shape** | **YES — every synthesis path, see §107** |
| `personality` (Text, since SESSION 175) | HOW the character speaks | script/dialogue/conversation synthesis |
| `visual_subject` / `visual_template` | media identity | portrait/rebake paths |
| `tone_archetype` | voice axis | prompt fence |
| `who_you_help` (SESSION 232) | audience shape (factual) | script synthesis, claim verifier evidence |
| `what_you_sell` (SESSION 232) | offering shape (factual) | script synthesis, claim verifier evidence |
| `always_emphasize` / `never_say` / `desired_feeling` | brand positioning / prohibitions | prompt fence (not evidence per claim_verifier §680-720) |
| `character_point_of_view` (SESSION 253) | POV framing | script/dialogue synthesis |
| `voice_energy` / `voice_humor` / `voice_directness` | voice axes | prompt fence |
| `voice_signature_phrases` / `voice_avoid_phrases` | allowed / avoided vocabulary | prompt fence, claim verifier vocabulary |
| `runway_avatar_*` / `portrait_path` / `voice_id` | media identifiers | provider bind |
| `status` | bake lifecycle | gate |

**Semantic-payload finding:** the character carries 15+ semantic
fields (identity, voice, prohibitions, evidence). The Universe
carries one (`description`), and nothing reads it.

## §107 PART C — business_brief lineage

**Introduced:** `1b80ebf` (2026-05-13, SESSION 107 — "core data
model: Workspace/Spokesperson/Video/ConversationThread"). Original
help text: > "One-paragraph description of the business this
spokesperson represents. Promoted up from the legacy per-campaign
brief_prompt (design doc §4.3)."

**Original model assumption:** one spokesperson **is** a business's
on-camera identity. `Spokesperson` was the "unit of brand identity"
per the module docstring. business_brief was the *business* — not
the character's personal expertise.

**W11.y (SESSION 175, commit `47f5166`, 2026-05-16):** split
`personality` OUT of `business_brief` on the assumption that
`business_brief` = WHAT (facts) and `personality` = HOW (voice).
Backfilled `personality` from `business_brief` so pre-split rows
kept working. The split preserved the "business_brief carries the
business" assumption; only voice moved off.

**SESSION 232 (commit `a13a4a6`, 2026-07-23) — Identity surface:**
added `who_you_help` / `what_you_sell` / `always_emphasize` /
`never_say` / `desired_feeling` — five NEW character-owned identity
fields, half factual (audience / offering) and half positioning
(prohibitions / target feeling). Reinforced the "one character
carries the business identity" model.

**SESSION 240 (commit `175342f`, 2026-08-06):** rename
`Spokesperson` → `Teammate` (Python/domain only). No semantic
change; the "brand identity" framing became "teammate", but
business_brief kept its role.

**SESSION 253 (commit `c86b67e`, 2026-08-14) — Character Voice /
Writing Identity:** added 7 more character-owned fields
(`character_point_of_view`, three `voice_*` axes, two `voice_*_phrases`).
Continued expansion of the character as the semantic unit.

**SESSION 261 (commit `ef10d4e`, 2026-08-17) — Universe substrate:**
`Teammate.universe` FK introduced. Universe app landed. **business_brief was NOT restructured.** Universe was intentionally introduced as an "opt-in prospective" layer (Slice 3 §52); character-owned business identity was preserved as-is.

**Current (post-SESSION 276):** business_brief remains the primary
semantic carrier of business identity. Universe is a scope wall
without a semantic payload of its own.

**Historical intent vs current runtime role:**
- Historical intent: `Spokesperson` ≈ a business; business_brief
  defines the business.
- Current runtime role: `Teammate` is one character in a Universe
  that MAY contain many characters; but business_brief still defines
  the business, per-character.
- **Drift:** the "1 spokesperson = 1 business" assumption is no
  longer architecturally true (Fox & Flour has Ruby + Tyson; Patch's
  Workshop has Patch + Rivet). business_brief hasn't caught up.

## §108 PART D — Synthesis composition map

Grep for `business_brief` across `shell/character_os/` and
`shell/apps/`, excluding tests / migrations / caches.

| Synthesis path | File:line | Where business_brief enters | Universe.description read? |
|---|---|---|---|
| Single-character K6 script synthesis | `script_synthesis.py:801-805` | Emitted verbatim as a `BUSINESS SHAPE:` block inside the "grounding evidence corpus" section. Prompt hard-rules "Every factual claim in the script must trace back to content in this section." | no |
| Multi-cast dialogue synthesis | `dialogue_synthesis.py:581-585` | One `BUSINESS SHAPE:` block per cast member, scoped as "only {alias!r} may cite these as their own". | no |
| Fallback single-character brief (topic-less rendering) | `script_synthesis.py:410` | Used verbatim when the operator supplies no prompt. | no |
| Claim verifier evidence corpus | `claim_verifier.py:711-721` | Appended to KD chunks as peer-evidence for factual-claim verification (§109). | no |
| Ask (`/api/spokespeople/{id}/ask/`) K6 | `teammate_ask.py:334-341` | Emitted as "authoritative business context" alongside retrieved chunks. | no |
| Realtime avatar session config | `conversation_synthesis.py:300-311` | Threaded into Runway avatar `personality` field (post-K6-leak-bait mitigation). | no |
| Sharpening pass | `prompts/sharpening.py:263-266` | `clean_business_brief()` strips hedges before storage — not a synthesis consumer, an authoring pass. | no |
| Wizard templates | `templates/teammate_templates.py:55-92` | Provided as a canned initial value for new characters. | no |

**Universe.description grep:** `grep -rn "universe\.description\|Universe.description\|\.description" shell/character_os/ shell/apps/universe/` returns **zero hits in synthesis code paths.** The field is written by `UniverseSerializer` and displayed on `/workspace/universes/:id`, but never read by any synthesis, retrieval, prompt, memory, or claim path.

**Consumer count summary:** business_brief is consumed in **at least 6 distinct synthesis paths**; Universe.description is consumed in **0**.

## §109 PART D addendum — Precedence and authority

`claim_verifier.py:680-721` (module docstring for
`build_evidence_corpus`):

> Included:
> * Retrieved K2 chunks (`chunk_text` on each).
> * Teammate `business_brief` (business shape / facts).
> * Teammate `who_you_help` (audience shape — factual).
> * Teammate `what_you_sell` (offering shape — factual).
>
> Deliberately EXCLUDED: operator prompt, name, personality, brand
> positioning, allowed vocabulary.

**Peer-evidence rule:** the claim-verifier treats KD chunks and
character-owned business_brief as **peers**. A claim is supported if
it appears in **either**. There is no rule that says "KD chunks
override business_brief" or vice versa. This means:

- If Ruby's `business_brief` says "celebration cake deposit = 50%"
  and a Universe-shared KD chunk says the same, both cite each
  other; consistent.
- If Ruby's brief says "50%" and Tyson's brief says "25%", both
  claims verify as "supported" (each cites its own brief), and the
  render can inherit either — depending on which character is
  speaking. **No contradiction is surfaced**; the two briefs are
  independently authoritative per character.
- If a Universe-shared KD says "50%" and Tyson's brief says "25%",
  Tyson synthesized alone will treat "25%" as supported (his own
  brief cites it). **World-shared facts do not override
  character-owned facts.**

**Verdict on precedence:** none exists. Every synthesis path
concatenates business_brief + retrieved chunks into a single
"evidence" region; the LLM cannot distinguish shared from private
authority.

## §110 PART E — Fox & Flour forensic specimen

**Universe row:**
- id `1a0af807-dd6a-47cd-bfaa-3d088f1c105f`, name "Fox & Flour Bakery", slug `fox-flour-bakery`, description **`""`** (0 chars). No metadata, no config, no canon field.

**Ruby (universe-bound):**
- `business_brief` (330 chars): defines the bakery — sourdough, handcrafted pastries, seasonal desserts, custom celebration cakes, locally sourced ingredients, small-batch baking, warm community gathering place. Also embeds Ruby's role ("Ruby owns Fox & Flour Bakery").
- `personality` (338 chars): warm, cheerful, caring, knowledgeable — Ruby's voice, not the business.

**Tyson (universe-bound, created today via Slice-5 wizard):**
- `business_brief` (342 chars): describes Tyson's role (coffee-and-counter) but ALSO restates the bakery's products (breads, pastries, seasonal desserts, celebration cakes, coffee pairings). Overlaps with Ruby's brief on the business's identity.
- `personality` (335 chars): easygoing, practical, dry — Tyson's voice.

**Fox & Flour KnowledgeDocuments today:** 0.

**Historical KnowledgeDocuments (via git):**
- `74e7f18f-5b77-459c-bc36-b4ab617d8aca` "Fox & Flour Bakery — Working
  Knowledge" — 6,599-char UNIVERSE-audience KD ingested SESSION 273
  §15 (`70e3113`, 2026-08-20). Content in
  `docs/design/session_273_experiment_data/03_slice_alpha_proposed_knowledge_document.md`.
  Covers breads/sourdough (starter care, house loaf, rotating loaves),
  pastries (fresh-baked cadence, daily lineup, waste policy), pricing
  (by weight, half-loaves, day-old discount + food-shelf donation).
  Wiped in SESSION 276 §340 disposable-dogfood reset.
- No PDF (all Fox & Flour KD was text/markdown from the design doc).

**Memory:** No `NarrativeMemory` rows for Fox & Flour Universe (0 today; may or may not have existed pre-SESSION 276 reset).

**"If Ruby were removed from the analysis entirely, what durable data
would tell a newly created character that Fox & Flour is an artisan
bakery, what it makes/sells, its audience, its atmosphere, its
business policies, its shared identity?"**

**Answer: essentially nothing.** Universe row provides only the name.
`description` is empty. No KDs. No memories. Tyson's `business_brief`
overlaps with Ruby's on the business definition, so removing Ruby
alone would leave a partial definition on Tyson — but Tyson himself
was seeded with knowledge of the business only because Chris typed
it in during creation. A hypothetical third character created today
via the Slice-5 wizard would inherit **nothing from Fox & Flour**
except the World UUID; Chris would have to re-type the entire bakery
identity into that third character's business_brief.

## §111 PART F — Patch's Workshop forensic specimen

**Universe row:**
- id `56d16b63-652e-4f54-bc7e-39114bbfc4c5`, name "Patch' Workshop", slug `patch-workshop`, description `"First world for Patch and Rivet"` (31 chars). Metadata note, not a semantic definition; no facts about the workshop, its content shape, its scope, its rules, its audience.

**Patch (universe-bound):**
- `business_brief` (~1200 chars): defines Patch himself — AI experimentation and technology spokesperson, build-first framing, subject matter (AI, agents, automation, characters, generation, 3D printing). Also describes the *format* Patch produces (short-form social content). "Patch's Workshop" as a place/world is not defined by this text — it is implied by Patch being an experimenter.
- `personality` (~2000 chars): beaver inventor's voice — curiosity, chaos, invention, "let's build it and find out." Also lists voice signature/avoid phrases.

**Rivet (universe-bound):**
- `business_brief` (944 chars): defines Rivet as "Patch's robotic assistant, workshop partner, and reluctant accomplice." Explicitly names "Patch's workshop" but only via Patch's presence. The workshop's identity is entirely defined through the Patch/Rivet interaction pattern.
- `personality` (1952 chars): small, weathered robot, dry, sarcastic, deadpan — Rivet's voice.

**KnowledgeDocuments today for Patch's Workshop:** 0. Historical KDs
existed (SESSION 272 experiments referenced Patch/Rivet knowledge)
but were part of the SESSION 276 reset scope.

**Memory:** No `NarrativeMemory` rows for Patch's Workshop today (0).

**Episodes:** 27 (much richer than Fox & Flour). These are
Universe-scoped `Episode` rows carrying `title` + `operator_topic`.
Each episode is a story anchor, not a World-identity definition —
`operator_topic` is per-episode creative intent (per
`EPISODE_SCHEMA_V1.md` §Q1).

**"If Patch disappeared from synthesis context, what durable
World-owned/shared state still defines Patch's Workshop for Rivet or
a future third character?"**

**Answer: `"First world for Patch and Rivet"` — 31 chars of operator
note, and 27 Episode titles + topics. Nothing that says what the
workshop IS as a place, or what shared context all its characters
inherit.** Rivet's business_brief anchors to Patch's presence, so
Patch's removal would leave Rivet with no independent world-defining
context. A future third character (say, a repair-shop specialist)
would have to be seeded with fresh business_brief text describing
the workshop from scratch.

## §112 PART G — Historical PDF / Knowledge evidence (verified)

Chris recalled that PDFs / knowledge materials may have combined
character + business identity. Verified against git.

- **Fox & Flour:** the historical KD was **markdown** (from the
  design doc `03_slice_alpha_proposed_knowledge_document.md`), not
  a PDF. Content mixed business facts with authored details
  ("Ruby maintains two active starters"; "Ruby wants Fox & Flour to
  feel like a neighborhood third place"). Classification: **D —
  mixed semantic document**. Neither pure character-scoped nor pure
  Universe-shared; described "the bakery as Ruby runs it."
  Persisted as `audience_scope=UNIVERSE`, so at the retrieval layer
  it behaved as Universe-shared.
- **Patch/Rivet:** SESSION 272 (`project_patch_ai_agents_substrate_saturated.md`
  memory notes 5 Patch/AI-Agents renders) mentions Patch KD
  material, but there is no single canonical KD doc committed to
  the repo in the same shape as Fox & Flour's. Historical Patch KD
  content was ephemeral experiment substrate. Classification: **E —
  unavailable / insufficient evidence** in durable form; deleted
  along with the SESSION 276 disposable-dogfood reset.

## §113 PART H — Multi-character contradiction test

Fox & Flour has Ruby + Tyson. Both business_briefs assert Fox & Flour
facts.

**Ruby's brief asserts:**
- "naturally leavened sourdough"
- "handcrafted pastries, seasonal desserts, and custom celebration cakes"
- "locally sourced ingredients, small-batch baking"
- "warm community gathering place"

**Tyson's brief asserts:**
- "breads, pastries, seasonal desserts, celebration cakes"
- "coffee pairings"
- "customer pickup flow"
- "everyday questions people ask before ordering"

**Overlap zone:** both authoritatively assert the bakery makes
"celebration cakes", "pastries", "seasonal desserts". If Chris later
edits Ruby's brief to remove "seasonal desserts" without editing
Tyson's, the two briefs will contradict each other silently — no
system-level surface identifies the divergence.

**Precedence:** none (see §109). Ruby-alone synthesis pulls Ruby's
brief; Tyson-alone synthesis pulls Tyson's brief; Ruby+Tyson dialogue
synthesis pulls BOTH briefs as scoped-to-each-alias evidence.

**Consequence for the illustrative deposit example (from the prompt):**
- Ruby.business_brief says "deposit = 50%" → Ruby videos cite 50%.
- Tyson.business_brief says "deposit = 25%" → Tyson videos cite 25%.
- Shared KD (if one existed today) says "deposit = 50%" → Ruby videos
  double-cite; Tyson videos still cite 25% (his brief is authoritative
  peer evidence and the KD ranks by cosine, not by policy).
- No surface catches or reports the contradiction.

**Classification: CONFIRMED that duplicated authoritative business
semantics can create silent contradictions across characters.**

## §114 PART I — World-without-character test

Hypothetical: `POST /api/universes/ {workspace, name: "Copper Creek Coffee"}` today.

**What does Character OS know about Copper Creek Coffee?**
- name: "Copper Creek Coffee"
- slug: `copper-creek-coffee` (auto)
- workspace + id + timestamps + archived_at

**Semantically:** nothing. No fact about the business. No content
model. No audience. No products. No policies.

**What does the first character creation currently add that makes
Copper Creek Coffee meaningful?**
- The character's `business_brief` — the operator's paragraph that
  describes the business.
- That paragraph becomes the entire semantic identity of the World
  until (a) a second character is created with an overlapping brief
  or (b) Universe-audience KDs are ingested.

**Verdict:** A World-only-first onboarding flow (create the World,
then create the first character) would leave the World completely
undefined between step 1 and step 2. Only the character step supplies
semantic identity. This is a direct consequence of §105 (Universe
row has no semantic payload).

## §115 PART J — Character-without-business-duplication thought experiment

Model a hypothetical clean state:

```
Fox & Flour Universe owns/shared:
    "Artisan neighborhood bakery. Sourdough foundation. Handcrafted
    pastries baked fresh each morning. Seasonal desserts. Custom
    celebration cakes. Locally sourced ingredients, small-batch
    baking. Neighborhood third-place atmosphere. Prices bread by
    weight; half-loaves available; day-old bread discounted the
    following morning and donated Sunday evening."

Ruby owns:
    "Owner/baker role. Maintains the two starters. Warm, cheerful,
    caring voice. Loves talking about the craft of bread."

Tyson owns:
    "Counter/coffee role. Knows the pickup flow and coffee pairings.
    Easygoing, dry voice. Prefers clear recommendations over sales
    language."
```

**Would current synthesis lose anything essential?**
- Ruby-alone synthesis: would need to see the Universe brief +
  Ruby's brief together. Today the prompt has one `BUSINESS SHAPE:`
  slot for the character. Would require a new `WORLD SHAPE:` slot
  or merging both into `BUSINESS SHAPE:` at prompt-build time.
- Tyson-alone synthesis: same.
- Multi-cast (Ruby + Tyson): the dialogue synth's per-alias
  `BUSINESS SHAPE:` block would need a shared prelude, OR the
  multi-cast prompt would gain a shared `WORLD SHAPE:` section.
- Claim verifier: evidence corpus would extend to include the
  Universe-owned brief (as a shared source), not just each
  character's brief. No behavior change; only a source added.

**Nothing essential is lost.** The current character-only prompt
plumbing simply doesn't have a shared-World slot yet. A future slice
could add one; the Universe row would need a semantic payload to
populate it.

## §116 PART K — Semantic ownership classification

Classify each information type by current owner + current consumer +
natural product owner (based on §105-§113 evidence, not aesthetic
preference).

| Information | Current owner | Current consumer | Natural product owner? |
|---|---|---|---|
| World/business name | Universe.name | queryset labels, prompt scope | Universe (already correct) |
| What the business does | Teammate.business_brief (per-char, duplicated) | every synthesis path | **Universe** (currently mislocated) |
| Products / services | Teammate.business_brief + historical KD chunks | synthesis + claim verifier | **Universe / shared KD** |
| Pricing | Teammate.business_brief + historical KD chunks | synthesis + claim verifier | **Universe / shared KD** |
| Policies | Teammate.business_brief + historical KD chunks | synthesis + claim verifier | **Universe / shared KD** |
| Target audience | Teammate.who_you_help (per-char, duplicated) | synthesis + claim verifier | **Universe** (duplicated across characters today) |
| Shared atmosphere / brand context | Teammate.business_brief (per-char, duplicated) | synthesis | **Universe** |
| Character role (e.g. "baker" vs "counter") | Teammate.business_brief + Teammate.personality | synthesis | Teammate (already correct) |
| Character personality | Teammate.personality | synthesis + Runway avatar | Teammate (already correct) |
| Character mannerisms | Teammate.personality + Teammate.voice_* | synthesis | Teammate (already correct) |
| Personal expertise | Teammate.business_brief (mixed in) | synthesis | Teammate (currently mixed with business shape) |
| Character-specific Knowledge | KD w/ audience_scope=CHARACTER | retrieval | Teammate (M2M scoped) |
| Shared World facts | historically KD w/ audience_scope=UNIVERSE (0 today) | retrieval, canon lane | Universe / shared KD (correct model; empty substrate) |
| Private character facts | Teammate.business_brief + KD w/ audience_scope=CHARACTER | retrieval | Teammate |
| Story events / narrative memory | NarrativeMemory (Universe-scoped) | retrieve_universe_memory | Universe (already correct) |

**Reading of the table:**
- Universe already correctly owns: name, narrative memory, shared-KD scope, cast scope.
- Universe **should also own** but currently doesn't: what the business does, products, pricing, policies, audience, atmosphere.
- Teammate correctly owns: name, role, personality, mannerisms, voice axes, personal knowledge attach.
- Teammate **carries duplicated ownership** for: business identity fields that would be more coherent at the Universe level once multiple characters share the World.

## §117 PART L — business_brief overload classification

Answer: **B — actually World/business-owned semantics stored on the
character**, with a strong **D — historical compatibility field whose
responsibilities have drifted** overlay.

Distinct responsibilities packed into business_brief today:
1. **Business/World identity** — "artisan bakery, sourdough
   foundation, celebration cakes" (Fox & Flour) or "workshop where
   we build weird things" (Patch's). This is Universe-natural per
   §116.
2. **Character role within the business** — "Ruby owns Fox & Flour",
   "Tyson works the counter", "Patch is an inventor", "Rivet is
   Patch's assistant". This is Teammate-natural.
3. **Character-personal expertise / signature focus** — Patch's
   subject-matter list (AI/agents/automation/3D printing) is
   character-specific choice-of-topic, not Universe-shared.
4. **Voice / tone hints** ("warm community gathering place",
   "reluctant accomplice") — should really live in `personality`
   post-W11.y split, but the split was not comprehensive.
5. **Factual anchors for claim verification** — pricing, policies,
   product lists. These are the Universe-owned data that got stored
   here because there was no Universe layer when business_brief was
   introduced.

The field carries 5 distinct responsibilities, only 1-2 of which are
naturally Teammate-scoped after SESSION 261.

## §118 PART M — Onboarding-consequence analysis

Compare the four models the prompt names.

**Model 1 — World first.** Chris types the World's semantic identity
BEFORE any character exists. Requires the Universe row to have a
semantic field the operator can populate. Today: none exists
(§105). Would require a new field (e.g. `Universe.brief`) or a
seed Universe-audience KD, plus wizard change. Coherent with the
architecture we've evolved toward (world = business = the shared
context) but requires structural work.

**Model 2 — Character first / create World inline.** Slice 5's
current implementation. Cheap; already shipped. World gets no
semantic definition beyond the name.

**Model 3 — Current hybrid** (as the prompt describes): World is
named at wizard step 1 (via Slice 5's picker) but its semantics
are packed into the character's `business_brief` at wizard step 1
also. Then the "Teach {character} about your business" welcome-page
action routes to the generic Knowledge page, which resets audience
context (World must be re-picked from `UniverseScopePicker` with the
"None (legacy)" wording still exposed — the Slice 1 finding). **This
is the current state.** Coherent structurally, incoherent
semantically — the operator's mental model that "I just told
Character OS about Fox & Flour" is technically wrong (Character OS
learned about Fox & Flour only via Ruby / Tyson individually).

**Model 4 — evidence-suggested.** The architecture increasingly
implies:
```
Workspace (tenant)
    ↓
World (semantic identity — the business/cast/place)
    ↓
Character (role + personality + personal expertise inside the World)
    ↓
Knowledge (Universe-shared OR character-specific)
```
This requires giving the Universe row a semantic payload (either a
first-class `Universe.brief` field, or a required seed Universe-audience
KD authored at Universe-create time). The wizard's business_brief would
then narrow to character-specific role/expertise; the wizard would
also either need a "describe the World" step, or would need the
World to already have been described (Model 1). Model 2 remains
viable IF World creation is enriched to capture semantic identity.

**No decision here.** Recording Model 4 as source-supported
architectural inference; Slice 6 is audit-only.

## §119 PART N — Slice-5 invariant remains sound?

**YES.**

Slice 5 established: every new ordinary character belongs to a
World. That is orthogonal to where the World's semantic identity
lives. Both statements can be simultaneously true:
- Every character belongs to a World (Slice 5 invariant).
- The Universe row currently captures too little semantic
  information (Slice 6 finding).

Slice 5 forbids creating orphan characters; it does not require the
World to be semantically self-sufficient. Slice 6 does not
invalidate that.

## §120 PART O — Knowledge handoff consequence

Chris's dogfood flow after Tyson creation was:

```
/spokespeople/{tyson_id}/welcome
    ↓  "Teach Tyson about your business" button
    ↓  (source: welcome route — needs inspection to confirm route)
/workspace/knowledge   (generic Knowledge page)
    ↓  UniverseScopePicker at top; picker unset
    ↓  Four ingestion tabs (paste / PDF / URL / search)
    ↓  Operator must re-select Fox & Flour manually
    ↓  Legacy wording "None (legacy — visible to workspace-wide legacy teammates only)" still exposed
```

**Information preserved from the character-create context to the
Knowledge page:** essentially none from the operator's perspective.
The route change does not propagate `?universe=<uuid>` or
`?spokesperson=<id>` query params — the picker resets.

**Does the current route/API support preselecting?**
- Backend: yes. The Knowledge LIST endpoint accepts
  `?workspace=<uuid>` and `?universe=<uuid>` query params
  (`apps/embeddings/views.py:117-126`) and `?spokesperson=<uuid>`
  (line 101). Create-time UI could pre-seed the picker without a
  backend change.
- SPA: no. `/workspace/knowledge` today reads `useUniverses(workspaceId)`
  but does not accept a `?universe=` or `?spokesperson=` query
  string. Any pre-selection would be a small SPA-only change (Slice 6
  does not implement it).

**Wording concern:** "Teach Tyson about your business" implies the
knowledge belongs to Tyson (character-scoped). But if the operator's
intent is "the bakery makes sourdough" (a fact about Fox & Flour
that Ruby ALSO knows), the correct audience is UNIVERSE, not
CHARACTER. The welcome-page button copy is misaligned with the
architecture: characters don't own facts about the business — Worlds
should. Do not settle wording yet.

## §121 PART P — Generalization

Apply the semantic-ownership model across the specimens the prompt names.

| Specimen | Current fit | Notes |
|---|---|---|
| Fox & Flour (Ruby + Tyson) | poor — brief duplication, empty Universe | §110 |
| Patch's Workshop (Patch + Rivet) | poor — 31-char Universe note; brief carries all identity | §111 |
| Riverstone (Penny + future guides) | untested — Penny is a legacy NULL-Universe teammate (Slice 3 §51). Would require both a Riverstone Universe and Penny migration before this pattern applies. |
| Dealership (salesperson + finance + service) | pattern likely to REPEAT AND WORSEN — three characters would each carry a nearly-identical "This is a car dealership that sells...service dept...financing terms..." block. High probability of silent contradiction (§113). |
| Fictional fantasy World (multiple characters) | pattern likely to WORSEN differently — each character's brief would need to duplicate world-lore (setting, era, magic system, factions), which is precisely the shape of information that has no place in a per-character brief. |
| Solo creator (one character) | current shape is FINE — brief = both business and person is coherent when there's only one on-camera identity. This is the original SESSION 107 assumption; it still holds for the 1-character case. |
| Brand mascot (one character) | current shape is FINE for the same reason. |

**Generalization finding:** the current model **fits the 1-character
case** (its historical assumption) and **degrades quadratically with
the number of characters in a World** (each new character duplicates
Universe-worth-of-content into their brief and adds a contradiction
surface).

## §122 PART Q — Composition-boundary verdict

Chain under test:
```
Universe became world/business boundary
    +
Character still owns authoritative business brief
    ⇒
Shared World semantics may be duplicated across characters
    ⇒
Duplicated authoritative business semantics + multiple characters
    ⇒
Potential contradictions / drift
```

**Verdict: CONFIRMED**, from source + real-DB evidence:
- Confirmed by §105 (Universe has no synthesis-consumed semantic
  field).
- Confirmed by §108 (business_brief is consumed by every synthesis
  path).
- Confirmed by §110 + §111 (Fox & Flour + Patch's Workshop specimens
  both show the semantic definition living on characters, not on
  the Universe).
- Confirmed by §113 (Ruby + Tyson today both authoritatively assert
  the bakery's product list; §109 shows no precedence rule exists to
  arbitrate).

## §123 PART R — Q-277-6 answers

1. **Where does World semantic identity live TODAY?**
   **B — primarily character-owned**, with a strong **E — historically
   mixed / ownership has drifted** overlay. Universe.description is
   read by no synthesis path; character.business_brief is consumed
   by every synthesis path and is the actual carrier of business
   identity today.
2. **Can Fox & Flour meaningfully exist independently of Ruby today?**
   **NO.** Universe.description is empty; there are 0 KDs; if Ruby
   were removed, the only remaining bakery-defining text would be
   whatever Tyson happens to have inherited via the operator-typed
   overlap in his brief (which is coincidental, not architectural).
3. **Can Patch's Workshop meaningfully exist independently of Patch
   today?** **NO.** Universe.description is a 31-char management
   note; Rivet's brief anchors to Patch's presence; a third
   character created today would have no shared workshop identity
   to inherit.
4. **Is `business_brief` overloaded?** **B (World/business-owned
   stored on the character)** + **D (historical compatibility field
   whose responsibilities have drifted)**. Field carries 5 distinct
   responsibilities per §117.
5. **Does current onboarding reflect the modern architecture?**
   **NO.** The wizard forces a World pick (Slice 5) but places
   World-defining information into a character-owned field
   (business_brief); the welcome page's "Teach Tyson about your
   business" then routes to a generic Knowledge page that resets
   audience context and exposes legacy wording (Slice 1 §11 lexical
   drift + Slice 6 §120 handoff gap).
6. **Is Slice 5's invariant still sound?** **YES.** Slice 5 forbade
   orphan characters; Slice 6 finds the World lacks semantic
   payload. Both are simultaneously true (§119).

## §124 PART S — Smallest next falsifiable question

Given Slice 6's evidence, the smallest next question is upstream of
both the Knowledge UI reshape (Slice 1 §17 → §80) and the wizard's
welcome-page handoff (Slice 6 §120). Both downstream slices depend
on where World semantic identity should live.

> **Q-277-7** — What is the minimum first-class Universe semantic
> payload required so that a Universe can meaningfully represent
> its own business/world (its shared identity, products, audience,
> policies, atmosphere) independently of any single character — and
> is the smallest coherent implementation (a) a new
> `Universe.brief` first-class field, (b) a required seed
> Universe-audience KnowledgeDocument authored at Universe-create
> time, or (c) some composition of the two?

Answering Q-277-7 requires only source analysis + a design
recommendation (no implementation, no data mutation, no
migration). Its result determines whether Slice 7 becomes:
- **Slice 7-A** (small model change): add `Universe.brief` +
  wire synthesis to read it as shared context alongside
  `business_brief`.
- **Slice 7-B** (Knowledge-native): make the Universe-create form
  require an authored seed KD; move the "business identity" copy
  out of `business_brief` into that KD; retrieval already covers
  Universe-audience.
- **Slice 7-C** (hybrid): tiny `Universe.name` + `Universe.description`
  is retained for headline identity; Universe-audience KDs carry
  the detailed shared knowledge; business_brief narrows to
  character-specific role.

Do not implement Q-277-7. Do not implement the Knowledge UI reshape.
Do not touch Slice 5. Do not modify Tyson, Ruby, Patch, Rivet, or
Universes. Do not add Knowledge.

**Alternate smaller questions** (present, do not select):
- **Q-277-7-alt-A** (handoff-only): implement pre-selection of
  `?universe=<uuid>&spokesperson=<uuid>` on the "Teach {character}
  about your business" route without changing anything else. Tests
  whether the friction is purely UX handoff or actually
  ownership-shaped.
- **Q-277-7-alt-B** (dogfood-first): create the "Riverstone"
  Universe with today's tools (name only), then create a fresh
  character in it, and observe whether the operator naturally
  duplicates the world's identity into the character's brief.
  Real-mode confirmation of §113 / §121.

Do NOT begin any of these without Chris + ChatGPT approval.

## §125 Findings — separated

**OBSERVED FACT (source / real-DB):**
- Universe model has one semantic-adjacent field (`description`); no
  synthesis path reads it (§105 + §108).
- Teammate model has 15+ semantic fields; business_brief is
  consumed by 6+ synthesis paths (§106, §108).
- Fox & Flour Universe.description is empty; 0 KDs; 2 teammates
  both carrying overlapping business definitions in
  business_brief (§110).
- Patch's Workshop Universe.description is a 31-char note; 0 KDs;
  2 teammates whose briefs describe them personally and anchor to
  Patch's presence (§111).
- Historical Fox & Flour Universe-audience KD (id
  `74e7f18f-5b77-459c-bc36-b4ab617d8aca`, 6,599 chars) existed and
  was disposed of in SESSION 276 §340 (§112).
- Claim verifier treats KD chunks and character-owned brief as
  peer evidence with no precedence rule (§109).
- business_brief was introduced 2026-05-13 with the assumption
  Spokesperson ≈ Business; Universe was introduced 2026-08-17,
  ~3 months later, without restructuring business_brief (§107).

**SOURCE / TEST-DERIVED FACT:**
- Two characters in one World can each authoritatively assert
  different business facts with no system surface flagging the
  contradiction (§113).
- Adding a Universe.description population would not currently
  reach any synthesis path (no consumer exists in source).
- SPA Knowledge page does not accept `?universe=<uuid>` or
  `?spokesperson=<uuid>` query params today (§120).

**OPERATOR CONTEXT (Chris):**
- Fox & Flour was created around Ruby (verified §101 claim 1).
- Ruby / Patch content mixed character + business identity
  (verified §101 claim 2 for Fox & Flour; §112 partial for
  Patch's Workshop).
- Modern World/Universe substrate is later (verified §101 claim 3).
- Penny's 58 compositions belong to an obsolete dogfood era and
  do not constrain forward architecture (Slice 4 §63, reaffirmed
  here — Penny remains legacy NULL-Universe; Slice 6 does not
  touch her).

**INFERENCE:**
- The composition boundary between "Universe as scope" and
  "character as business identity" is genuine drift, not a bug.
  Both layers evolved independently; only Slice 5 has forced them
  to coexist for new characters.
- Ownership drift is now visible because Fox & Flour has two
  characters (Ruby + Tyson) — this specimen didn't exist until
  Slice 5's dogfood run created Tyson today. The problem was
  latent throughout SESSION 273-276.
- Model 4 (§118) is the architecture Character OS has evolved
  toward. Model 3 (current) is transitional. Model 1 (World-first)
  requires giving the Universe a semantic payload; Model 2
  (Slice 5 as-shipped) is only viable when Universe creation itself
  enriches with semantic identity.

**PRODUCT RECOMMENDATION (Chris + ChatGPT decide, not implemented):**
- Answer Q-277-7 before touching Knowledge UI or wizard welcome-page
  handoff.
- Do not modify business_brief in Slice 7; instead give Universe a
  semantic payload and let business_brief narrow naturally over time.
- Preserve Slice 5's invariant unchanged.

## §126 Unresolved questions (Slice 6 — deferred)

- Q-277-7 (§124): minimum Universe semantic payload contract.
- What happens to the 8 existing character-owned "business identity"
  fields (business_brief, who_you_help, what_you_sell,
  always_emphasize, never_say, desired_feeling, character_point_of_view,
  personality) if the Universe grows a shared brief? Are they trimmed,
  deprecated, or preserved as character-role-specific overrides?
- Should there be a precedence rule between Universe-owned facts,
  Universe-shared KD chunks, and character-owned brief when they
  conflict? (§109 shows none exists today.)
- Should the "Teach Tyson about your business" welcome-page copy be
  reworded to reflect Universe ownership (e.g. "Teach the World more
  about Fox & Flour")? Wording deferred until Q-277-7 settles
  ownership.
- What is the correct operator surface for editing a Universe's
  shared brief once it exists — inline on `/workspace/universes/:id`,
  a dedicated `/workspace/universes/:id/identity` route, or embedded
  in the character wizard when creating the World?
- Should we retroactively backfill Fox & Flour's Universe with a
  shared brief seeded from Ruby's + Tyson's overlapping content?
  (Not a Slice 6 recommendation — this is a follow-on question
  after Q-277-7 lands.)

## §127 Slice 6 landed SHA

_Landed SHA: `8164ab6` (Slice 6 audit commit)._

---

# Slice 7 — Q-277-7 — Minimum World semantic contract (audit / design)

Chris + ChatGPT approved Slice 6 and authorized Slice 7 as an
**audit/design** slice. Objective: determine the minimum first-class
semantic contract a World must own so it meaningfully represents its
business/place/story independently of any single character, then
recommend the smallest coherent representation. **No implementation
in this slice.** Slice 5's World-required invariant is preserved.

## §128 Slice 7 baseline

- HEAD @ Slice 7 open: `3f24233` (Slice 6 SHA-record). Clean, pushed.
- Substrate: KD=0, KC=0.
- `chriss-workspace`: **9 teammates** (4 Universe-bound — Ruby, Patch, Rivet, Tyson; 5 legacy — Mason, Penny, Mike, Repo Red, Riggs), 2 Universes (Fox & Flour Bakery, Patch's Workshop). Slice 6 §99 wrote "8→8"; the correct current count is 9 (Tyson is the 4th Universe-bound teammate, not an existing row). No mutation since Slice 6.

## §129 Slice 7 checklist

- [x] STEP 0 — verify baseline (no drift since Slice 6).
- [x] PART A — Define "World identity" (what remains true when all characters are removed).
- [x] PART B — Identity vs Knowledge: existing analogous pattern verified in synthesis.
- [x] PART C — Minimum contract.
- [x] PART D — Current field ownership map.
- [x] PART E — Representation options A/B/C/D/E compared.
- [x] PART F — Synthesis precedence / composition implications.
- [x] PART G — Onboarding consequences.
- [x] PART H — "Teach Tyson about your business" re-evaluation.
- [x] PART I — Generalization against 12 arbitrary future cases.
- [x] PART J — Q-277-7 answers.
- [ ] Commit + push; SHA-record.

## §130 Q-277-7

> What is the MINIMUM first-class semantic contract a World/Universe
> must own so that it meaningfully represents its business/place/story
> independently of any single character? And after determining that
> contract: which existing or proposed substrate is the smallest
> coherent owner?

## §131 Prediction (before source analysis)

Prediction: Character OS **already implements** the "compact identity
always injected + detailed facts retrieved" pattern for the CHARACTER
layer — personality/POV/voice axes are deterministic; KD chunks are
cosine-retrieved. Prediction: the WORLD layer needs the same split —
a compact deterministic identity slot (World brief) plus optional
Universe-audience KDs. The minimum contract is: **one compact
`Universe.brief`-style semantic field + the pre-existing
Universe-audience KD lane**. The two together correspond to Option D
in the prompt. Prediction: business_brief is fundamentally mixed and
its "world identity" responsibilities naturally migrate to the World
brief while its "character role / expertise" responsibilities stay
where they are.

## §132 PART A — What is World identity?

**Method:** for each specimen, list what must remain true after ALL
characters in that World are removed for the World to still
meaningfully exist. Anything essential is World-identity; anything
that disappears with the last character is character-owned.

| Specimen | If all characters removed, World must still know | If gone, would you say "the World is undefined"? |
|---|---|---|
| Fox & Flour without Ruby / Tyson | "artisan neighborhood bakery, sourdough foundation, handcrafted pastries, seasonal desserts, celebration cakes, small-batch, warm neighborhood atmosphere" | YES (today only the name survives — §110 established) |
| Patch's Workshop without Patch / Rivet | "workshop where experimental ideas about AI + technology get built and tested, build-first framing, honest about failure" | YES (today only the 31-char note survives — §111) |
| Riverstone without Penny | "outdoor adventure guiding service — routes, seasons, gear, safety posture" | YES (nothing exists yet — Riverstone is not a Universe today) |
| Dealership with zero characters yet | "car dealership — make/model focus, sales / finance / service departments, warranty and financing posture" | YES (needs to exist before hiring characters) |
| Bookstore (multiple characters) | "curated independent bookstore — genres, atmosphere, event/reading schedule, customer relationship style" | YES (identity must survive individual bookseller changes) |
| Fictional fantasy World (non-business) | "setting/era, factions, magic system if any, tonal register, cultural rules" | YES (World identity has nothing to do with business — must generalize) |

**Categories of information the specimens produced:**

| Candidate category | Identity? Knowledge? Configuration? Memory? Character-owned? |
|---|---|
| Purpose / what this place or organization is | **identity** (always) |
| Products / services | **knowledge** (retrievable; details) |
| Customers / audience shape | **identity** (compact) |
| Setting / atmosphere / tonal register | **identity** (compact) |
| Policies | **knowledge** (retrievable; details, may change) |
| Pricing | **knowledge** (retrievable; details, changes often) |
| Brand promises | **identity** (compact; rarely changes) |
| Shared history | **memory** (already Universe-owned via NarrativeMemory) |
| Locations | mixed — a single named place = identity; catalog of places = knowledge |
| Shared vocabulary | **identity** (compact; must always be in scope) |
| Shared factual canon | **knowledge** (retrievable) |
| Character role within the World | **character-owned** |
| Character personality / voice | **character-owned** |
| Character personal expertise | **character-owned** |
| Provider credentials / billing | **tenant-owned** (Workspace) |

**Reading:** World identity is the small, compact, always-present
context that answers "what kind of place is this?" World knowledge is
the larger, retrievable, mutable body of details. Both are legitimate
and distinct.

## §133 PART B — Identity vs Knowledge (is the split real?)

**Test:** does Character OS already treat compact identity and
retrievable detail as different substrates?

**Answer: YES.** Source-verified from three convergent patterns:

- **Character voice** (`script_synthesis._build_character_voice_section` at `script_synthesis.py:844-870`): personality, tone_archetype, voice_energy, voice_humor, voice_directness, voice_signature_phrases, character_point_of_view are all **deterministically injected** into §2 CHARACTER VOICE — always visible, never cosine-ranked, never at risk of being outranked by a retrieved chunk. This is the compact-identity pattern applied to characters.
- **Character facts** (`script_synthesis._build_factual_basis_section` at `script_synthesis.py:801-817` and claim_verifier at `claim_verifier.py:711-721`): business_brief + who_you_help + what_you_sell are **also deterministically injected**, but KD chunks are cosine-retrieved. Both types live in §1 FACTUAL BASIS but arrive via different pipelines.
- **Universe-shared canon** (`dialogue_synthesis._build_factual_basis_section` at `dialogue_synthesis.py:449-575`): the SHARED WORLD KNOWLEDGE block is emitted deterministically from `retrieve_universe_canon` (a policy function, not the same as cosine-ranked per-character retrieval). NarrativeMemory rows are also emitted deterministically from `retrieve_universe_memory`. The 3-tier prompt structure — **SHARED / MEMORY / PER-CHARACTER SCOPED** — is exactly the identity-vs-knowledge shape at the World layer, minus a Universe-owned compact identity slot.

**Answers to PART B specific questions:**

- *Is "Fox & Flour is an artisan neighborhood bakery" the same kind of thing as "custom cakes require 50% deposit"?* **No.** The first is compact identity that must always be in scope; the second is a policy detail that may change and belongs in a retrievable body.
- *Should both be retrieved by cosine similarity?* **No.** Basic identity must never fail to reach synthesis because a chunk didn't rank high enough.
- *Should basic identity ever fail to reach synthesis?* **No.** Deterministic injection is the pre-existing pattern for compact identity (personality, tone) and for Universe-canon retrieval (deterministic pass-through of `retrieve_universe_canon` output).
- *Does claim verification treat these differently today?* Partly. Personality/POV are explicitly **excluded** from the evidence corpus (`claim_verifier.py:687-703`). business_brief/who_you_help/what_you_sell are **included** as peer evidence. A Universe brief that carries factual identity (e.g. "artisan bakery specializing in sourdough") would need to enter the evidence corpus similarly — it grounds the claim "we make sourdough" independent of a KD chunk.
- *What happens when identity/context and a retrieved KD conflict?* Currently: no precedence rule (§109). Both would appear as peer evidence to the LLM. The scale of the conflict risk depends on whether the World brief carries *facts* (increases risk) or *framing* (reduces risk).
- *What happens when a character brief conflicts with either?* Currently: no precedence. The character brief is emitted as SCOPED evidence with the SCOPE RULE preventing another character from citing it, but nothing prevents the character's cited fact from silently disagreeing with a World brief or Universe-audience KD chunk.
- *Analogous pattern elsewhere?* **Yes** — the character voice section is the exact analogue: compact identity is always in scope; detailed factual chunks are retrieved.

**Verdict on identity vs knowledge:** **DISTINCT.** They must not share
one substrate. World identity is always-in-scope compact context;
World knowledge is retrievable factual detail.

## §134 PART C — Minimum World semantic contract

Minimum information a World must own to be meaningfully independent
of any single character:

**IN THE MINIMUM CONTRACT (World identity):**

1. **World name** — already present (`Universe.name`).
2. **World brief** — a compact 1-3 paragraph description of what
   the World IS. Must be deterministically injectable into every
   synthesis path this World participates in. Answers: what kind of
   place / business / story is this; what is its purpose; what is
   its overall audience shape; what is its atmosphere / tonal
   register. Should NOT contain fluid details (pricing, weekly menu,
   specific policies) — those belong in retrievable knowledge.

**NOT IN THE MINIMUM CONTRACT (belongs elsewhere):**

- Detailed product / service catalog → Universe-audience KnowledgeDocument.
- Pricing → Universe-audience KnowledgeDocument.
- Policies → Universe-audience KnowledgeDocument.
- Shared vocabulary / entity catalog → Universe-audience KnowledgeDocument (or a future first-class canon primitive if it grows).
- Story history → already covered by `NarrativeMemory` (Universe-scoped).
- Character role / personality → stays on Teammate.
- Character-specific expertise → stays on Teammate + character-audience KDs.
- Provider credentials / billing → stays on Workspace.

**Rationale:**
- (1) satisfies the "meaningfully exist before first character" requirement (§114).
- (1) + Universe-audience KDs satisfy the "shared context inherited without re-typing" requirement (§115).
- (1) as a deterministic slot satisfies the "identity is never outranked" requirement (§133).
- Everything left in retrievable knowledge preserves the flexibility to update details without editing every character.
- Deleting one character does not delete World identity (which lives on the Universe row + Universe-audience KDs).
- Changing a shared business fact happens in ONE place (the KD or the brief), not N.

**Size discipline:** the World brief must be short enough to always
inject into every prompt without token budget concerns. The existing
personality field averages 300-2000 chars in the current substrate
(Ruby=338, Patch=~2000, Rivet=1952). A World brief in the 300-1000
char range is comfortably injectable and matches the "compact
identity" pattern established for characters.

## §135 PART D — Current Teammate field ownership map

Revisit each identity/brief field with the natural-owner test:
"if the World grew a first-class compact identity, where would this
information most coherently live?"

| Field | Current owner | Content today (Ruby specimen) | Natural owner in modern model |
|---|---|---|---|
| `business_brief` | Teammate | "Ruby owns Fox & Flour Bakery, a neighborhood artisan bakery... naturally leavened sourdough... celebration cakes... locally sourced ingredients... warm community gathering place" | **MIXED — must be decomposed.** ~70% is World identity (bakery kind, product breadth, atmosphere). ~30% is character role ("Ruby owns"). |
| `who_you_help` | Teammate | (audience) | **WORLD identity.** Audience is a property of the World/business, not per-character; duplicating it across Ruby + Tyson is the exact §113 duplication pattern. |
| `what_you_sell` | Teammate | (offering) | **WORLD identity.** Same reasoning — offering is a World-owned fact. |
| `always_emphasize` | Teammate | brand positioning | **MIXED.** If it names *what* to emphasize (product truths) → WORLD identity / knowledge. If it names *how* character voice should emphasize (voice-shaping) → CHARACTER. Currently ambiguous. |
| `never_say` | Teammate | prohibitions | **MIXED.** Brand-level "we never claim X" → WORLD. Character-level "this character avoids Y" → CHARACTER. |
| `desired_feeling` | Teammate | brand feeling target | **WORLD identity / brand.** The feeling the *business* wants to leave — not the feeling one character produces vs another. |
| `character_point_of_view` | Teammate | POV framing | **CHARACTER identity.** Character-owned — correct today. |
| `personality` | Teammate | HOW this character speaks | **CHARACTER identity.** Character-owned — correct today. |
| `visual_subject` / `visual_template` / `tone_archetype` | Teammate | media / voice axis | CHARACTER — correct today. |
| `voice_*` (energy, humor, directness, signature_phrases, avoid_phrases) | Teammate | character voice details | CHARACTER — correct today. |
| `runway_avatar_id` / `portrait_path` / `voice_id` | Teammate | provider IDs | CHARACTER — correct today. |

**Reading:** three fields (`who_you_help`, `what_you_sell`,
`desired_feeling`) are structurally World-owned and currently
character-owned. Two fields (`always_emphasize`, `never_say`) are
mixed. business_brief is the mixed field with the largest text and
the deepest overload. The remaining eight character-owned fields are
correctly placed.

**Do NOT migrate anything in Slice 7.** This is classification only.

## §136 PART E — Representation options

Evaluate the five candidate representations named in the prompt.

**OPTION A — reuse `Universe.description`**

- Semantic clarity: **poor** — current help text says "management surface field, not consumed by synthesis." Repurposing would be a hidden semantic change on an existing field.
- Deterministic availability: **would require synthesis wiring** (nothing reads it today, §108).
- Retrieval behavior: not retrieved.
- Claim verification: not in evidence corpus today; would need explicit inclusion.
- Editability: single field on Universe detail page.
- Onboarding UX: the Universe-create form already collects it, but currently as an optional throwaway note.
- Multi-character consistency: would work if consumers were added.
- Non-business Worlds: works — description is generic.
- Migration: none for schema. Semantic-only change with backward-compat risk on any operator who typed a note in `description` expecting it to be a throwaway.
- Business_brief compat: no direct effect.
- Extensibility: fine.
- Overload risk: **repeats the business_brief mistake** — a field whose stated purpose ("management surface") is different from what synthesis reads. Guarantees future ambiguity.

**OPTION B — add `Universe.brief`**

- Semantic clarity: **strong** — new field with a specific documented purpose.
- Deterministic availability: **wire once into script_synthesis + dialogue_synthesis + teammate_ask + conversation_synthesis + claim_verifier** — one field, five sites.
- Retrieval behavior: not retrieved; always injected.
- Claim verification: must join the evidence corpus (`claim_verifier.build_evidence_corpus`) at the World layer.
- Editability: new Universe detail page section (or an inline field on the create form).
- Onboarding UX: Universe-create form gains one required field.
- Multi-character consistency: perfect — one authoritative source.
- Non-business Worlds: works — the field can hold "fantasy world with X setting, Y factions" as easily as "artisan bakery."
- Migration: **one new nullable Text field on Universe; no data migration** (existing Universes get `brief=""`; SPA and API prompt operator to fill).
- Business_brief compat: **no immediate change to business_brief.** The World brief exists ALONGSIDE character briefs. Precedence rule in §137.
- Extensibility: single-purpose, resists overloading if scoped tightly.
- Overload risk: low if the field's contract is explicit ("World identity: compact 1-3 paragraphs answering what this World is, its audience shape, its tonal register — NOT policies, pricing, product catalog").

**OPTION C — seed Universe-audience KnowledgeDocument only**

- Semantic clarity: **weak-to-moderate** — World identity ends up as a chunk, competing in cosine retrieval with detailed policy/pricing chunks.
- Deterministic availability: **NO.** The chunk is retrieval-ranked; basic identity ("this is a bakery") may lose to a highly-cosine-similar detail chunk under low `top_k`. Fails §133's identity-must-always-be-in-scope requirement unless we add a special "always include this KD" flag, which itself becomes a first-class KD-level attribute.
- Retrieval behavior: standard cosine.
- Claim verification: already covered by KD chunk pathway.
- Editability: familiar Knowledge UI (paste/PDF/URL).
- Onboarding UX: operator must author a KD at World create time — heavier than typing a paragraph.
- Multi-character consistency: single source; works.
- Non-business Worlds: works.
- Migration: none; requires operators to seed a KD.
- Business_brief compat: business_brief remains character-owned; overlap continues.
- Extensibility: piggybacks on a general-purpose substrate — good for scaling knowledge, bad for guarantees.
- Overload risk: introduces a special-case flag ("always include") or accepts that identity may occasionally be missing from prompts.

**OPTION D — compact World identity/context (Option-B-shaped) + Universe-audience Knowledge for details**

- Semantic clarity: **strongest** — explicit split between always-injected identity and retrievable knowledge; mirrors the character-layer split precisely.
- Deterministic availability: YES for the brief.
- Retrieval behavior: for the KDs — standard.
- Claim verification: brief joins evidence corpus; KD chunks already there.
- Editability: brief inline on Universe detail; KDs via existing Knowledge UI.
- Onboarding UX: brief required at Universe-create (small paragraph); KDs remain optional post-hoc.
- Multi-character consistency: perfect for identity; KDs already Universe-audience-consistent.
- Non-business Worlds: works.
- Migration: one nullable Text field + wiring (same as Option B) + zero mandatory KD creation.
- Business_brief compat: no immediate change.
- Extensibility: excellent — the KD lane extends naturally as the World grows; brief stays compact.
- Overload risk: low — brief has a narrow contract; KDs have a separate contract; no field is asked to be both.

**OPTION E — another substrate**

Considered candidates:

- Repurpose `NarrativeMemory` for identity → **rejected.** NarrativeMemory is bound to an Episode (`memory/models.py:137-157`) and treated as past events; identity is present-tense and not tied to a story.
- Add a `WorldProfile` sibling model → **rejected as overkill for the minimum contract.** A single Text field satisfies the current requirement; a whole model invites the overload it should prevent.
- Recycle `Universe.description` AND rename it → **rejected as backward-compat hazard** (see Option A).
- Store World identity as a special reserved character in the Workspace ("workspace-persona") → **rejected** — inverts the SESSION 261 direction (World-owns-characters, not character-owns-World).

**Comparison summary:**

| Option | Semantic clarity | Deterministic availability | Overload risk | Migration cost | Best-fits-existing-pattern |
|---|---|---|---|---|---|
| A — reuse description | poor | needs wiring | high (silent semantic change) | zero | no |
| B — new Universe.brief | strong | one-field wiring | low | one nullable field | yes |
| C — seed KD only | weak | no (cosine race) | requires special "always-include" flag | zero | no (breaks the pattern) |
| **D — B + Universe KDs** | **strongest** | yes | low | one nullable field | **yes — matches character-layer pattern** |
| E — other | — | — | — | — | — |

**Recommendation:** **OPTION D.** The minimum contract is a single
new deterministic Universe-owned identity field (`Universe.brief`) +
the pre-existing Universe-audience KD lane for retrievable detail.
This mirrors the character-layer identity/knowledge split (§133),
requires one nullable field addition and one set of synthesis
wirings, resists overloading, and generalizes across business and
non-business Worlds.

## §137 PART F — Synthesis precedence / composition

Adopting Option D would give synthesis the following semantic layers
(order = specificity from broadest to narrowest, NOT necessarily
conflict-precedence):

```
1. World identity (Universe.brief)                — always injected
2. World knowledge (Universe-audience KD chunks)  — cosine-retrieved
3. Narrative memory (NarrativeMemory rows)        — deterministically emitted
4. Character identity (personality, POV, voice)   — always injected
5. Character knowledge (business_brief + who_you_help + what_you_sell + character-audience KD chunks)  — brief always, chunks cosine
6. Character voice / brand (never_say, always_emphasize, desired_feeling)  — always injected
7. Task / topic (operator prompt)                 — always injected
8. Audience / performance (recipe params)         — always injected
```

Slice 6 §109 finding: today there is no precedence between duplicated
business facts. Would introducing World identity require an explicit
precedence rule?

**Answer: not necessarily.** Prefer eliminating duplicated ownership
over inventing a conflict-resolution engine.

Two composition principles suffice:

**Principle 1 — non-overlapping semantic responsibilities.** If the
World owns "this is an artisan bakery" and the character owns "Ruby
is the owner," they don't overlap and can never conflict. business_brief
overlap becomes the operator's editing choice, not an architectural
requirement.

**Principle 2 — narrator-precedence for facts that legitimately
overlap.** Universe canon (SHARED WORLD KNOWLEDGE) already wins over
NarrativeMemory when they conflict per the dialogue prompt's
"static canon wins on conflict" wording (`dialogue_synthesis.py:566-568`).
The same convention naturally extends to World brief > per-character
brief in the rare cases where both assert the same fact type.

**Consequence:** synthesis prompt-building changes required (for
Option D):

1. `script_synthesis._build_factual_basis_section` — add a `WORLD SHAPE:` block (from `Universe.brief`) before or in place of `BUSINESS SHAPE:` when the Universe brief is populated. Leave `BUSINESS SHAPE:` for legacy character-owned brief content; the two can coexist during transition.
2. `dialogue_synthesis._build_factual_basis_section` — add `WORLD SHAPE:` at the top of the SHARED WORLD KNOWLEDGE block. Deterministic; not affected by cosine ranking.
3. `claim_verifier.build_evidence_corpus` — extend to include `spokesperson.universe.brief` alongside `business_brief`, `who_you_help`, `what_you_sell`. World-owned facts must count as evidence for claim support.
4. `teammate_ask.py` — same "authoritative business context" region gains the World brief.
5. `conversation_synthesis.py` — the Runway realtime personality field currently receives character brief; consider extending to include the World brief so the avatar knows what World it's in.

No new precedence rules are strictly required. Two conventions
suffice: non-overlapping semantic ownership (Principle 1) and
narrator-precedence for legitimate overlaps (Principle 2). Both are
prompt-side additions, not evaluator/scoring logic.

## §138 PART G — Onboarding consequences

Under Option D:

**NEW WORLD (Universe-first)**
1. `/workspace/universes/new` collects `name` (required) and
   **`brief`** (required — 1-3 paragraphs).
2. `POST /api/universes/` includes `brief`. Universe row lands with
   compact semantic identity.
3. Operator can immediately create the first character inside this
   World; character wizard sees a Universe with defined identity and
   the character-brief field narrows to "your character's role /
   personality / expertise."

**NEW CHARACTER + INLINE NEW WORLD (Slice-5 flow, enriched)**
1. `/spokespeople/new` picker shows existing Worlds + "+ Create new
   World…" (Slice 5, unchanged mechanically).
2. Inline create surface asks for `name` + **`brief`**.
3. Character wizard's `business_brief` field narrows to character-owned
   copy (role + personality + character-specific expertise).

**EXISTING WORLD**
1. `/spokespeople/new` picker; operator selects Fox & Flour.
2. Character wizard shows the World's `brief` (read-only or as a
   context hint) so the operator sees "the character inherits: 'Fox &
   Flour is a warm neighborhood artisan bakery ...'."
3. Character wizard's `business_brief` field narrows semantically to
   "character role + personality + character-specific expertise" —
   the operator no longer needs to retype the bakery's identity.

**Consequence:** onboarding becomes structurally aligned with the
mental model "the World has an identity; the character has a role."
Slice 5's World-required invariant is preserved; only the payload the
operator supplies at Universe-create time changes.

**No wizard step count changes.** Universe-create today is single-form
single-submit; adding one required text field does not add a step.

## §139 PART H — "Teach Tyson about your business" re-evaluated

Under Option D, the welcome page's action button gets a well-defined
target that today lacks one:

- If the operator's intent is "add facts about the World that every
  character in this World may cite," the correct target is a
  Universe-audience KD create scoped to the character's `universe_id`.
- If the operator's intent is "add facts that only Tyson knows"
  (e.g. Tyson's certifications, private notes), the correct target
  is a CHARACTER-audience KD scoped to Tyson.
- The button currently routes to a generic Knowledge page that
  requires re-selecting World AND does not surface the CHARACTER
  option — it forces the operator into UNIVERSE- or WORKSPACE-audience
  choices and asks them to interpret "None (legacy)" (Slice 1 §11).

**Correct semantic operation the button should represent:**
one action, two audience choices. Something like:

- "Teach Fox & Flour more" (UNIVERSE-audience KD) — shared with every
  character in the World, including future ones.
- "Teach Tyson personally" (CHARACTER-audience KD) — scoped to Tyson.

The wording "Teach {character} about your business" is misleading
because Tyson does not *own* the business — the World does. Do not
settle wording yet; the operation split matters more than the copy.

**Consequence for the Slice 6 §120 handoff finding:** the correct
handoff to the Knowledge page (or a scoped variant of it) would
carry `?universe=<uuid>` and offer both audience choices with the
`?spokesperson=<uuid>` context preserved. Backend query-param support
already exists (`apps/embeddings/views.py:117-126`). SPA plumbing is
the only gap.

## §140 PART I — Generalization test

Test Option D against the 12 arbitrary future cases the prompt names.

| # | Case | Option D fit | Notes |
|---|---|---|---|
| 1 | fox owns a bakery | GOOD | World brief = bakery identity; character brief = fox's role. |
| 2 | bakery has five characters with different jobs | GOOD | World brief once; five character briefs narrow to role/personality/expertise. Duplication risk (§113) eliminated. |
| 3 | coffee shop has three bears | GOOD | Same shape — one World identity, three character identities. |
| 4 | dealership with sales + finance + service | GOOD | World brief captures "car dealership — sales, finance, service departments, warranty and financing posture." Each character brief narrows to their department role. Prevents the "salesperson, finance, service each carry a full dealership brief" contradiction risk (§121). |
| 5 | shared company handbook | GOOD | Universe-audience KDs carry policies; World brief captures "we operate under handbook X, target audience Y" without duplicating the whole handbook. |
| 6 | one character has private expertise | GOOD | CHARACTER-audience KD covers this; unchanged from today. |
| 7 | Patch/Rivet fictional workshop | GOOD | World brief = "workshop where AI/tech ideas get built and tested, build-first framing." Character briefs narrow to Patch's inventor voice, Rivet's dry counterweight. Overlap between Patch's brief and Rivet's brief on "the workshop" disappears. |
| 8 | fantasy story World with no business | GOOD | World brief = setting/era/factions/magic system. No business assumed; the substrate is business-agnostic. |
| 9 | World created before any characters exist | GOOD | Universe.brief is present at Universe-create time; the World is meaningful with zero characters (§114 gap closed). |
| 10 | character deleted while World survives | GOOD | Universe row + brief + KDs + memories persist; the World's meaning is unaffected. |
| 11 | all characters deleted while World survives | GOOD | Same — World meaning survives. Today the World would effectively lose everything (§110-§111). |
| 12 | shared policy changes after ten characters exist | GOOD | Edit ONE Universe-audience KD (or the World brief). No character-by-character sweep. Prevents the "ten characters each carrying a stale policy" drift. |

**Non-business specimen (case 8) test:** the recommendation does not
assume Worlds are businesses. `Universe.brief` is a generic text
field for whatever compact identity fits — bakery, workshop, dealership,
bookstore, fantasy realm, purely fictional story World, single-creator
personal brand. All fit the same substrate.

**Solo-creator specimen (case 6 companion — one character, one
World):** even here Option D works — the operator can put the
compact business identity on the World brief and leave the character
brief for personal role/voice. Redundancy with the character brief
becomes an operator style choice rather than an architectural
requirement. (This case is the least improved by Option D; the
current shape is already fine for it. But Option D does not
*degrade* it.)

## §141 PART J — Q-277-7 answers

1. **Does Character OS need a first-class World semantic identity/context?** **YES.** Fox & Flour and Patch's Workshop specimens both fail to describe themselves independently of their characters today (§110-§111). Every non-solo generalization case worsens without it (§140).
2. **Is World identity semantically distinct from World Knowledge?** **YES.** The existing character-layer split (personality always-injected vs KD chunks retrieved) is the source-verified precedent (§133). Compact identity must always be in scope; detailed knowledge is retrievable.
3. **What is the MINIMUM World semantic contract?** ONE new compact deterministic field — `Universe.brief` — carrying: what kind of place / business / story this is, its audience shape, its tonal register. Explicitly 1-3 paragraphs; explicitly NOT a policy/pricing/catalog dump (those go in Knowledge).
4. **What should remain Knowledge instead?** Policies, pricing, product catalog, vocabulary/entity catalog, mutable operational details. Retrieved by the existing Universe-audience KD lane. No new KD infrastructure required.
5. **What should remain character-owned?** Character role, personality, tone, voice axes, POV, signature/avoid phrases, personal expertise, private knowledge (CHARACTER-audience KDs). Portrait/voice/avatar identifiers.
6. **Is `business_brief` fundamentally character-owned, World-owned, mixed, or legacy compatibility?** **Mixed (Slice 6 §117 classification B + D).** Its natural decomposition splits into World-brief-worthy content ("bakery kind, product breadth, atmosphere") and character-brief-worthy content ("Ruby owns; Ruby's baker role and personality"). Slice 7 does not decompose it. business_brief stays where it is; it becomes optional/character-narrow as the World brief captures the World's identity.
7. **Which representation option is recommended?** **OPTION D — compact World identity/context (a new `Universe.brief` field) + Universe-audience Knowledge for retrievable detail.** Compared systematically in §136.
8. **Does that recommendation require synthesis changes?** **Yes but small.** Five call sites (`script_synthesis`, `dialogue_synthesis`, `teammate_ask`, `conversation_synthesis`, `claim_verifier`) need to read the new field and emit it deterministically. No retrieval infrastructure changes required. No precedence engine required (§137).
9. **Does it require a schema change?** **Yes — one new nullable Text field on `Universe`.** No data migration; existing rows land with `brief=""`. `Universe.description` retains its current role (management surface note) and could later be repurposed or deprecated.
10. **Does it require Knowledge changes?** **No.** The Universe-audience KD lane already exists and works. The recommendation does NOT require a mandatory seed KD at Universe-create time (that was Option C, rejected).
11. **What should happen when creating a character inside an existing World?** The character wizard should surface the World's brief as read-only context, and the character's `business_brief` field should narrow (in copy and expectation) to character-owned content. Slice 7 does not implement this; it's the natural downstream UX consequence.
12. **Does the current "Teach Tyson about your business" handoff remain conceptually correct?** **NO** (§139). The correct operation is a single action with two audience choices: "Teach {World} more" (UNIVERSE-audience KD) OR "Teach {character} personally" (CHARACTER-audience KD). Current handoff conflates both and forces a "None (legacy)" workaround for either.
13. **Does Slice 5 remain sound?** **YES.** Slice 5's invariant (every ordinary new character belongs to a World) is orthogonal to World semantic ownership. Both statements can hold simultaneously (§119).
14. **What is the smallest next falsifiable question after this?** See §142.

## §142 PART S — Smallest next falsifiable question

If Chris + ChatGPT approve Option D as the target, the smallest next
question is:

> **Q-277-8** — If a single new `Universe.brief` TextField is added
> (nullable, blank default, one new Universe-serializer field, wired
> deterministically into `script_synthesis._build_factual_basis_section`
> and `dialogue_synthesis._build_factual_basis_section` as a
> `WORLD SHAPE:` block before per-character `BUSINESS SHAPE:`, and
> added to `claim_verifier.build_evidence_corpus` as evidence),
> does synthesis for a Fox & Flour character correctly reflect the
> World's identity without duplicating it into every character's
> `business_brief`? And does it do so without regression against
> existing character-only synthesis paths where `Universe.brief=""`?

Q-277-8 is a **scope-locked implementation** slice (Slice 8). It
lands the minimum contract from §134 into the codebase and validates
it against real synthesis. Its scope is deliberately narrow:
- One new nullable Text field on `Universe`.
- One serializer field + one SPA form change (Universe-create).
- Five synthesis call-site wirings.
- Zero changes to `business_brief`.
- Zero changes to the Slice 5 wizard.
- Zero changes to the Knowledge UI (§139's welcome-page handoff is
  Slice 9+, downstream of Q-277-8).
- Zero legacy data migration (existing Universes land with `brief=""`).

**Alternate smaller questions** (present, do not select):

- **Q-277-8-alt-A** (audit-only continuation): before adding the
  field, ask Chris to author a proposed World brief for Fox & Flour
  (as durable markdown in the docs, not as data) and observe whether
  it fits the 1-3 paragraph size expectation and doesn't leak
  policy/pricing detail. Tests §134 empirically without touching
  code.
- **Q-277-8-alt-B** (character brief decomposition first): decide
  what happens to the character-owned overlap in `business_brief`
  before adding the World brief. Answers question 6 in §141 more
  fully but delays the World identity fix.
- **Q-277-8-alt-C** (handoff-only): implement the Tyson welcome-page
  handoff (`?universe=<uuid>&spokesperson=<uuid>` preserved with the
  audience choice split) before the World brief. Tests whether pure
  handoff repair reduces the operator friction without requiring the
  semantic decomposition. Predicted to help but not resolve the
  duplication drift.

## §143 Findings — separated

**OBSERVED FACT (source):**
- Character-layer identity vs knowledge split is source-verified: personality/tone/voice_axes are deterministically injected in `script_synthesis._build_character_voice_section`; KD chunks are cosine-retrieved in `_build_factual_basis_section`.
- Universe-layer SHARED / MEMORY / SCOPED prompt structure is source-verified in `dialogue_synthesis._build_factual_basis_section:449-609`.
- `retrieve_universe_canon` and `retrieve_universe_memory` return possibly-empty deterministic lists; the SHARED and MEMORY blocks are omitted when the list is empty (`dialogue_synthesis.py:541,563`).
- `Universe` has no field consumed by any synthesis path today (Slice 6 §108, re-confirmed).
- `claim_verifier.build_evidence_corpus` at `claim_verifier.py:711-721` treats character-owned `business_brief`/`who_you_help`/`what_you_sell` as peer evidence with KD chunks; there is no precedence rule.
- Real-DB substrate at Slice 7 open: 9 teammates (Tyson landed via Slice-5 wizard), 2 Universes, KD=0. Nothing mutated since Slice 6.

**SOURCE-DERIVED FACT:**
- The character-layer pattern generalizes cleanly to the World layer: adding a compact deterministic `Universe.brief` at the same architectural tier costs one new field and five wiring points.
- Adopting Option D does not require inventing a precedence engine; two conventions (non-overlapping ownership + narrator-precedence for legitimate overlaps) suffice.
- Existing Universe-audience KD retrieval already handles World-owned detail; no new retrieval infrastructure is needed.
- Zero-KD Universes (Fox & Flour today) get an immediately-usable World identity from the new field with no KD authoring.

**INFERENCE:**
- Option D is the smallest coherent representation that matches the pattern Character OS has already established at the character layer.
- business_brief's overload survives Option D unchanged; that's fine as a first move — decomposition is a separate future decision.
- Slice 5's invariant remains sound and improves under Option D (new characters land in a semantically-populated World).
- The welcome-page handoff and Knowledge UI reshape become natural, small downstream slices AFTER Option D lands.

**PRODUCT HYPOTHESIS (to test in Q-277-8):**
- H1 — a single 1-3 paragraph `Universe.brief` is sufficient to eliminate the §110-§111 "World cannot describe itself without characters" gap.
- H2 — deterministically injecting `Universe.brief` into synthesis reduces cross-character duplication drift (§113) without a precedence engine.
- H3 — the SPA form change is a single required text field on `/workspace/universes/new` + a read-only display on `/workspace/universes/:id`.

**PRODUCT RECOMMENDATION (Chris + ChatGPT decide, not implemented in Slice 7):**
- Adopt Option D as the minimum World semantic contract.
- Schedule Q-277-8 as the next slice (single-field + five wirings; no Knowledge UI, no wizard changes, no data migration, no business_brief changes).
- Defer character-brief decomposition (Q-277-8-alt-B) and welcome-page handoff (Q-277-8-alt-C) to subsequent slices.
- Preserve Slice 5's invariant throughout.

**UNRESOLVED QUESTION:**
- What is the exact character-count expectation / cap for `Universe.brief` (300? 500? 1000? 2000?)? Slice 7 estimates 300-1000 chars matches the character-personality precedent; Q-277-8 can settle a firm cap in the model field.
- Should `Universe.description` be repurposed (renamed to something like `Universe.notes`) or preserved as-is with clarifying help text? Not blocking Q-277-8.
- Should the wizard preview the World brief when creating a character inside an existing World, or is that a separate slice?
- Does the welcome-page handoff redesign (§139) belong before or after Q-277-8? Recommendation: **after**, so the World brief is available to inform whether the handoff copy should say "Teach {World} more" or something else.
- If Option D lands, does `business_brief` eventually deprecate in favor of a slimmer character-owned field (e.g. `character_role`)? Deferred — the character-layer decomposition is a separate arc.

## §144 Slice 7 landed SHA

_Landed SHA: `24f4ff9` (Slice 7 audit/design commit)._

---

# Slice 8 — Q-277-8 — Implement minimum World semantic contract

Chris + ChatGPT approved Slice 7's Option D. Slice 8 lands the
smallest coherent implementation: one new `Universe.brief` TextField,
one migration, one serializer field, five synthesis wirings, one
SPA form addition, one detail-page edit control. **No changes to
`business_brief`, no changes to the Slice-5 wizard, no changes to
Knowledge UI, no data migration, no legacy row mutation.**

## §145 Slice 8 baseline

- HEAD @ Slice 8 open: `ae70b46` (Slice 7 SHA-record). Clean, pushed.
- Substrate before: KD=0, KC=0; `chriss-workspace` 9 teammates, 2 Universes (Fox & Flour: brief_len=0, description_len=0; Patch's Workshop: brief_len=0, description_len=31 — the "First world for Patch and Rivet" note).
- Substrate after migration: identical row counts, `brief=""` for both existing Universes (default preserved). No mutation to Ruby, Tyson, Patch, Rivet, or any teammate.

## §146 Slice 8 checklist

- [x] STEP 0 — verify baseline.
- [x] PART A — model field (`Universe.brief` TextField, blank=True, default="", max_length=2000).
- [x] PART B — narrow documented contract (help_text + model-file comment).
- [x] PART C — length policy (2000-char cap; operator UI encourages concision).
- [x] PART D — serializer / API (read/create/update; Slice-5 name-only POST preserved).
- [x] PART E — dedicated World-create UI (`/workspace/universes/new` gains brief textarea).
- [x] PART F — World-detail visibility (Universe detail page uses existing edit pattern for brief).
- [x] PART G — synthesis wiring (five call sites; deterministic; blank-omitted).
- [x] PART H — script_synthesis: WORLD SHAPE before BUSINESS SHAPE.
- [x] PART I — dialogue_synthesis: one WORLD SHAPE block for the whole cast.
- [x] PART J — claim_verifier: `Universe.brief` in evidence corpus.
- [x] PART K — teammate_ask + conversation_synthesis wired.
- [x] PART L — legacy / blank-brief compatibility tested.
- [x] PART M — multi-character single-copy tested.
- [x] PART N — field ownership invariants tested.
- [x] PART O — migration applied; DB state verified.
- [x] PART P — targeted regression (2321/2321 backend, 665/665 SPA).
- [x] PART Q — broader regression + `makemigrations --check` (unrelated compositions drift noted, not caused by Slice 8).
- [x] PART R — no controlled real-data mutation (Chris will author Fox & Flour brief via UI per §156).
- [x] PART S — dogfood question deferred to §157.
- [x] PART T — `business_brief` untouched.
- [x] PART U — Knowledge UI untouched.
- [x] PART V — Slice-5 wizard untouched.
- [x] PART W — prediction vs actual (§155).
- [ ] Commit + push; SHA-record.

## §147 Q-277-8

> If Character OS adds one first-class `Universe.brief` field, injects
> it deterministically into the current synthesis/evidence paths as
> World identity, while leaving detailed World facts in the existing
> Universe-audience Knowledge lane, does a World become semantically
> self-sufficient without breaking existing characters/Worlds whose
> brief is blank?

## §148 Files changed (exact scope)

| File | Kind | What |
|---|---|---|
| `shell/apps/universe/models.py` | edit | Add `Universe.brief` TextField (blank=True, default="", max_length=2000) with narrow contract help_text. |
| `shell/apps/universe/migrations/0004_session277_universe_brief.py` | new | Pure `AddField`. No data migration. |
| `shell/apps/universe/serializers.py` | edit | Add `brief` to `UniverseSerializer.Meta.fields` (writable; not read_only). |
| `shell/apps/universe/tests/test_universe_brief.py` | new | 19 tests: field contract (5), non-interference invariants (4), script_synthesis wiring (3), dialogue_synthesis wiring (3), claim_verifier wiring (3), legacy compat (1). |
| `shell/character_os/script_synthesis.py` | edit | `_build_factual_basis_section` — emit `WORLD SHAPE:` before `BUSINESS SHAPE:` when `spokesperson.universe.brief` is populated; omit cleanly otherwise. |
| `shell/character_os/dialogue_synthesis.py` | edit | `_build_factual_basis_section` — emit ONE `--- WORLD SHAPE (shared World identity...) ---` block at the top of §1 for the whole cast. Suppress on mixed-Universe cast. |
| `shell/character_os/teammate_ask.py` | edit | `_system_prompt` — include "The World you belong to" preface when Universe.brief is populated. |
| `shell/character_os/conversation_synthesis.py` | edit | `_system_prompt` — same preface for realtime avatar sessions. |
| `shell/character_os/claim_verifier.py` | edit | `build_factual_corpus` — include `spokesperson.universe.brief` as evidence alongside `business_brief`/`who_you_help`/`what_you_sell`. Docstring updated. |
| `web/src/lib/api/universes.ts` | edit | Add `brief` to `universeSchema` (default ""), `CreateUniverseInput`, `UpdateUniverseInput`. |
| `web/src/routes/workspace/universes.tsx` | edit | `CreatePanel` — add "What is this World?" textarea (optional, maxLength=2000, helper copy) + include `brief` in the POST payload. |
| `web/src/routes/workspace/universes.$id.tsx` | edit | Universe detail — add editable "What is this World?" textarea + include `brief` in the PATCH payload. |
| `web/src/routes/workspace/universes.brief.test.tsx` | new | 3 tests: brief field rendered with helper; Slice-5 name-only create still works; brief round-trips into CREATE payload. |

**Not touched:**
- `web/src/components/spokesperson-wizard.tsx` (Slice-5 inline `+ Create new World` remains name-only per PART V scope-lock).
- `shell/apps/spokespeople/serializers.py` (`business_brief` unchanged per PART T).
- `web/src/routes/workspace/knowledge*` and `web/src/components/knowledge-panel*` (Knowledge UI untouched per PART U).
- Ruby, Tyson, Patch, Rivet, all legacy teammates, all Universes, all KDs — no data mutation.

## §149 Final field contract

`shell/apps/universe/models.py`:

```python
brief = models.TextField(
    blank=True,
    default="",
    max_length=2000,
    help_text=(
        "Compact World identity / context (1-3 short paragraphs). "
        "Describes what this World IS — its kind, broad purpose, "
        "audience shape, tonal register. Injected deterministically "
        "into synthesis whenever the World is in scope. Keep "
        "detailed pricing, policies, menus, and procedures in "
        "Knowledge instead. 2000-char cap. Blank stays valid; "
        "existing Universes migrate with brief=\"\"."
    ),
)
```

- **Length policy:** 2000-char pragmatic cap. Comfortably fits 1-3 short
  paragraphs. Matches the character `personality` field's observed
  300-2000 range (Slice 7 §134). Operator UI helper text encourages
  concision even though the cap is generous.
- **Compat:** blank remains valid indefinitely. Existing Universes
  migrated with `brief=""`. Slice-5 name-only POST still works.
- **No auto-generation:** brief is never derived from characters
  and never populates from character `business_brief`. Explicit
  operator authorship only.
- **No side effects:** no KnowledgeDocument creation, no chunking,
  no embedding.

## §150 Serializer / API behavior

- READ (`GET /api/universes/`, `GET /api/universes/:id/`) — returns `brief` in the response payload.
- CREATE (`POST /api/universes/`) — accepts `brief` (optional). Slice-5 minimum `{workspace, name}` remains 201.
- UPDATE (`PATCH /api/universes/:id/`) — accepts `brief`. Empty string is valid.
- Workspace + permissions unchanged (pre-existing `IsWorkspaceMember` + `validate_workspace`).
- No new endpoints; no new validators beyond the model-level `max_length=2000`.

## §151 SPA behavior

- `/workspace/universes/new` `CreatePanel` — new textarea labeled **"What is this World? (optional)"**, `data-testid="universe-brief"`, `maxLength={2000}`, `min-h-[120px]`, placeholder "A warm neighborhood artisan bakery built around small-batch baking...", helper copy: > "Describe the enduring shared context every character in this World should understand — its kind, purpose, audience, and atmosphere. Keep detailed facts, pricing, policies, menus, and procedures in Knowledge. Aim for 1–3 short paragraphs."
- `/workspace/universes/:id` detail — the existing edit control gains a matching editable textarea (identical labeling + helper copy). PATCH sends `brief` alongside `name` and `description`.
- `useCreateUniverse` + `useUniverses` hooks unchanged in shape; the Universe zod schema now parses `brief`.
- SPA inline "+ Create new World" flow in the Slice-5 spokesperson wizard is **not** modified. That inline flow remains name-only. Chris + ChatGPT can decide separately whether to enrich it.

## §152 Synthesis wiring (five call sites)

1. **`script_synthesis._build_factual_basis_section`** (single-character K6). If `spokesperson.universe.brief` is populated: emit `WORLD SHAPE:\n<brief>` **before** `BUSINESS SHAPE:` (character-owned) so the LLM reads World identity as prior context. Omitted cleanly for `universe=NULL` teammates or blank brief. `WORLD SHAPE` counts as `FACTUAL BASIS` per §1 framing — grounded, cite-able.
2. **`dialogue_synthesis._build_factual_basis_section`** (multi-cast). One `--- WORLD SHAPE (shared World identity; any character may cite) ---` block at the top of §1 for the entire cast. Derived from the first cast member's Universe with defensive scan across all cast members — if the cast mixes Universes (which the canon lane already rejects at `retrieval.py:372-374`), suppress rather than pick arbitrarily. **Never emitted more than once** per synthesis.
3. **`claim_verifier.build_factual_corpus`** (evidence). `spokesperson.universe.brief` joins the evidence corpus alongside `business_brief`, `who_you_help`, `what_you_sell`. Emitted **before** character-owned briefs so if future scoring becomes order-sensitive, World-owned identity precedes character-owned. Docstring updated to reflect the new evidence source.
4. **`teammate_ask._system_prompt`** (K6 ask). If populated: adds "The World you belong to (shared context every character in this World inherits — paraphrase as needed; authoritative alongside the excerpts): <brief>" to the system prompt. Omitted for `universe=NULL` or blank brief.
5. **`conversation_synthesis._system_prompt`** (Runway realtime). Same shape as (4) for realtime avatar sessions.

Universal properties across all 5 sites:
- **Deterministic** — never subject to cosine ranking.
- **Blank-omitted** — no `WORLD SHAPE:` header appears if brief is empty; no literal `None`/`""` noise.
- **Scoped from `spokesperson.universe`** — never cross-Universe; never substituted from Workspace-wide context.
- **Independent of retrieval** — populated brief always reaches synthesis even with `KD=0`.

## §153 Claim-verifier behavior

`build_factual_corpus(chunks, spokesperson=<sp>)` now includes:

1. Retrieved KD chunk text (unchanged).
2. `sp.universe.brief` (**new**, only if `sp.universe` is not None and brief is non-blank).
3. `sp.business_brief` (unchanged).
4. `sp.who_you_help` (unchanged).
5. `sp.what_you_sell` (unchanged).

Excluded fields (`personality`, `character_point_of_view`, brand
positioning, allowed vocabulary) remain excluded per the pre-existing
SESSION 253 boundary. World brief is added as **evidence**, not as
allowed-vocabulary or voice metadata — a claim like "Fox & Flour is
an artisan neighborhood bakery" can now be grounded by the Universe
brief.

## §154 Compatibility results

| Scenario | Behavior |
|---|---|
| Existing Universe with `brief=""` (Fox & Flour, Patch's Workshop today) | No `WORLD SHAPE:` block emitted anywhere. Prompts identical to pre-Slice-8 baseline. |
| Legacy `teammate.universe=NULL` (Mason, Penny, Mike, Repo Red, Riggs) | No universe lookup → `world_brief=""`. No block emitted. No crash. Existing synthesis unchanged. |
| Mixed-Universe dialogue cast | Defensive suppression — no arbitrary pick. Matches the canon lane's cast-Universe check pattern. |
| Slice-5 name-only POST `{workspace, name}` | Still 201. Universe lands with `brief=""`. Slice-5 wizard inline create unaffected. |
| Populated `Universe.brief` + KD=0 | Ruby / Tyson synthesis receives the World brief deterministically. §157 dogfood specimen. |
| Populated `Universe.brief` + populated Universe-audience KDs | Both surfaces present: `WORLD SHAPE` block plus `SHARED WORLD KNOWLEDGE` chunk list. Complementary, not overlapping. |
| Cross-Universe attempt (e.g. `Ruby.universe.brief` bleeding into Tyson-not-in-Fox-Flour dialogue) | Impossible — `world_brief` derived from `spokesperson.universe`, not from workspace-wide context. |

## §155 PART W — Prediction vs actual

**Prediction (§147):** one compact deterministic World field + existing
Universe-audience KD lane is sufficient; populated brief always
available; blank cleanly omitted; evidence-corpus grounding; single-copy
for shared dialogue.

**Actual (measured against tests + inspection):**

| Property | Predicted | Actual |
|---|---|---|
| World brief reaches every intended synthesis path | YES | YES — all 5 sites wired; 3 synthesis-wiring test groups pass. |
| Deterministic (never cosine-ranked) | YES | YES — direct string injection; no ranking pipeline. |
| Omitted cleanly when blank | YES | YES — `test_script_synthesis_omits_world_shape_when_brief_blank`, `test_claim_verifier_omits_universe_brief_when_blank`, `test_dialogue_synthesis_omits_world_shape_for_blank_brief` all pass. |
| Available to claim verification | YES | YES — `test_claim_verifier_includes_universe_brief_as_evidence` passes. |
| Emitted once for shared dialogue | YES | YES — `test_dialogue_synthesis_emits_world_shape_once_for_shared_cast` explicitly asserts `section.count("WORLD SHAPE") == 1`. |
| Any unexpected call path still relies exclusively on business_brief | (checked) | No unexpected coupling surfaced during audit. Every call site that reads `business_brief` was inspected in Slice 7 §108 and wired in Slice 8 §152. |
| Any test reveal World identity needs more than one field | (checked) | No. 19/19 backend + 3/3 SPA tests validate the single-field contract. |
| Hidden coupling with Knowledge or character creation | (checked) | No. `test_universe_brief_does_not_create_knowledge_document`, `test_universe_brief_does_not_mutate_teammate_business_brief`, `test_teammate_create_does_not_touch_universe_brief`, `test_teammate_update_does_not_touch_universe_brief` all pass. |

**Verdict: CONFIRMED.** No falsification signal. Q-277-8 is answered
YES.

## §156 Test totals + DB state

**Backend, change-adjacent regression** (universe + spokespeople +
embeddings + memory + compositions + identity + realtime + videos +
accounts + billing): **2321 passed / 2321 total** in 253s. Slice 5
baseline was 2302; +19 = 19 new tests in `test_universe_brief.py`.

**SPA full suite:** **665 passed / 665 total** in 6.3s. Slice 5
baseline was 662; +3 = 3 new tests in `universes.brief.test.tsx`.

**`makemigrations --check`:** the Universe app is clean; `--dry-run`
shows the pre-existing `compositions.0019_alter_composition_*` drift
that predates Slice 8 (pre-Slice-8 baseline had the same drift; not
caused by this slice).

**Full backend suite:** the 80 pre-existing failures documented in
Slice 5 §92 (76 `bootstrap_review` missing-fixture-data + 1
`test_media_engine_timeouts` stale-manifest + 3 `test_ask` intermittent
`EMBEDDING_FORCE_MOCK` race) are unrelated to Slice 8; not re-run at
this level. Change-adjacent regression above is the load-bearing gate.

**Real-DB state after migration:**
```
KD=0  KC=0
chriss teammates: 9
chriss universes: 2
  'Fox & Flour Bakery'  brief_len=0  description_len=0
  "Patch' Workshop"     brief_len=0  description_len=31
```
Zero rows mutated. Migration is pure `AddField`.

## §157 Dogfood-readiness — instructions for Chris

**Do NOT** author Knowledge in this slice — we want to prove the
World brief works with the Knowledge corpus still empty.

Suggested operator-authored specimen for Fox & Flour (Chris to enter
via UI, not via shell):

> Fox & Flour Bakery is a warm neighborhood artisan bakery built around
> small-batch baking, naturally leavened sourdough, handcrafted pastries,
> seasonal desserts, and celebration cakes. It aims to feel like a familiar
> neighborhood gathering place where careful craft and quality ingredients
> matter more than speed or mass production.

Manual dogfood steps:

1. Navigate to `/workspace/universes`.
2. Click **"Fox & Flour Bakery"** to open the detail page.
3. Locate the new **"What is this World?"** textarea in the Edit
   section (below Name, above Description).
4. Paste the paragraph above (or your preferred phrasing).
5. Click **Save**.
6. Verify the new brief persists after page refresh.

Then, without adding any Knowledge:

7. Open Ruby's detail page (`/spokespeople/{ruby_id}`).
8. Use the built-in "Ask" panel (K6 direct ask) to ask something
   like "What kind of place is Fox & Flour?"
9. Verify Ruby's answer reflects the bakery identity you just added
   to the World brief — even with KD=0.
10. Repeat with Tyson (same World) and confirm both characters share
    the same World identity without needing you to re-type it into
    either character's `business_brief`.

**Compatibility spot-check** (optional):

11. Open Patch's detail page (`/spokespeople/{patch_id}`) — brief=""
    still. Ask any question. Verify no regression vs pre-Slice-8
    behavior.

**Reporting:** feed the observations back for Chris + ChatGPT to
determine the next slice. Likely candidates:
- If the Fox & Flour brief works cleanly, consider Slice 9 (welcome-page
  handoff redesign per Slice 6 §120 / Slice 7 §139) or Slice 9-alt
  (Slice-5 inline `+ Create new World` gets a brief input).
- If a synthesis path missed the brief, narrow to that path.

**Provider spend note:** the Ask flow is a K6 provider call. Chris
should approve provider spend before dogfooding synthesis. Prompt
composition can be inspected without provider spend by dumping the
built prompt via a management command or shell if desired.

## §158 Findings — separated

**OBSERVED FACT (source / test):**
- `Universe.brief` added, migration `0004_session277_universe_brief.py` applied cleanly.
- 19/19 backend + 3/3 SPA new tests pass.
- 2321/2321 backend change-adjacent regression pass; 665/665 SPA full suite pass.
- Post-migration DB: Fox & Flour + Patch's Workshop rows preserved with `brief=""`; teammate + KD counts unchanged; no data mutation.
- Five synthesis sites now read `spokesperson.universe.brief`; three of them tested at the section-builder boundary.

**SOURCE-DERIVED FACT:**
- The compact-identity + retrievable-detail pattern generalizes cleanly from character-layer to World-layer with a single new field.
- No precedence engine required; two conventions (non-overlapping ownership + narrator-precedence for overlaps) suffice.
- No new retrieval infrastructure; no chunking; no embedding; no cache invalidation beyond the existing `useCreateUniverse` list-invalidation.
- Backwards compatibility is a natural property of the field's default (`""` → no block).

**INFERENCE:**
- Slice 8 lands the smallest viable World-owned semantic contract without disturbing character-owned overlap. The overlap remains as compatibility substrate until a separate slice decides how to decompose it.
- Slice-5's invariant is unchanged and remains sound.
- The natural next slices are downstream UX (welcome-page handoff, inline-World brief authoring). Both were explicitly scope-locked out of Slice 8 per PART U + PART V.

**PRODUCT RECOMMENDATION (Chris + ChatGPT decide):**
- Author Fox & Flour brief via the SPA per §157.
- Observe whether Ruby / Tyson synthesis inherits the World identity cleanly with KD=0.
- If YES, choose between Slice 9-A (welcome-page handoff redesign) or Slice 9-B (Slice-5 inline `+ Create new World` grows a brief input).
- If NO, narrow to the failing surface before proceeding.

**UNRESOLVED QUESTION:**
- Should the welcome-page action button (post-character-create) route change to preserve `?universe=<uuid>&spokesperson=<uuid>` and offer both audience choices explicitly? (Slice 6 §120, Slice 7 §139 — deferred to Slice 9-A.)
- Should the Slice-5 inline `+ Create new World` grow a brief input, or does the operator naturally author brief later via `/workspace/universes/:id`? (Slice 7 §138 — deferred to Slice 9-B.)
- Should `Universe.description` be renamed or repurposed now that `Universe.brief` is the first-class semantic field? (Deferred; low priority.)
- Does the character wizard need to surface the current World's brief as read-only context so the operator sees what the character will inherit? (Slice 7 §138 — deferred; separate UX question.)
- Once briefs exist on Universes, does `Teammate.business_brief` decomposition become the natural next arc, or does it remain permanent character-owned compatibility? (Deferred per PART T; not urgent.)

## §159 PART S — Smallest next falsifiable question

Deferred until Chris's dogfood evidence per §157 lands.

If dogfood confirms the World brief is deterministically available
to Ruby/Tyson synthesis with KD=0, the smallest next question is:

> **Q-277-9-A** — If the welcome-page action button after character
> create ("Teach {character} about your business") preserves
> `?universe=<uuid>&spokesperson=<uuid>` in the handoff to the
> Knowledge page and pre-selects the character's Universe as the
> audience scope, does the operator's mental-model handoff (Slice 6
> §120) close without any additional Knowledge UI reshape?

or, at Chris's discretion:

> **Q-277-9-B** — If the Slice-5 inline "+ Create new World" gesture
> in the spokesperson wizard grows the same brief textarea as
> `/workspace/universes/new` (still optional), does inline-World
> creation naturally acquire semantic identity at the same moment
> the operator names the World?

Both are small, orthogonal, and independently deployable. Either can
land as Slice 9. Do not implement without Chris + ChatGPT explicit
scope approval.

**Alternate smaller question** (present, do not select):
- **Q-277-9-alt** (character brief decomposition): observe whether
  operators start deleting World-identity content from their
  character `business_brief` fields naturally now that the World
  owns identity. If yes, `business_brief` slims into a role/expertise
  field organically without a migration slice. Requires dogfood
  observation, not implementation.

## §160 Slice 8 landed SHA

_Landed SHA: `fbf2bf8` (Slice 8 implementation commit)._

---

# Slice 9 — Q-277-9 — World detail surface audit (audit-only)

Chris + ChatGPT approved Slice 8. Chris performed the first real
operator dogfood of `Universe.brief` on Fox & Flour and reported a
UI concern. Slice 9 investigates that observation without touching
implementation.

## §161 Slice 9 baseline

- HEAD @ Slice 9 open: `e7f8c5c` (Slice 8 SHA-record). Clean, pushed.
- Real-DB verified read-only:
  - `KnowledgeDocument.objects.count() == 0`, `KnowledgeChunk.objects.count() == 0`.
  - `chriss-workspace`: 9 teammates, 2 Universes.
  - **Fox & Flour Bakery**: `brief_len=331` (matches Chris's dogfood specimen byte-for-byte), `description_len=0`, `archived_at=None`, `teammate_count=2`, `episode_count=2`, `knowledge_document_count=0`.
  - **Patch's Workshop**: `brief_len=0` (blank — control), `description_len=31` ("First world for Patch and Rivet"), `archived_at=None`, `teammate_count=2`, `episode_count=27`, `knowledge_document_count=0`.
- Zero drift since Slice 8 close.

## §162 Chris's Slice 8 dogfood evidence (recorded)

**OBSERVED FACT (real-DB):**
- Chris navigated to Fox & Flour Bakery's World detail page and entered a 331-char brief via the SPA's "What is this World?" textarea. Save persisted; the row now carries the brief. No other Universe mutated.
- Slice-8 operator mutation path works end-to-end for the specimen field.

**OPERATOR CONTEXT (Chris's verbatim reaction):**
> "I was able to update it but I am not crazy about how it looks
> since the forms just stay even after you save."

**OBSERVED FACT (source):** The page (`web/src/routes/workspace/universes.$id.tsx:145-249`) is one section labeled **"Edit"** containing three `<Input>` / `<textarea>` fields plus Save + Archive + "Delete permanently" buttons. There is no read-only view state — the fields render as inputs whether or not the operator has touched them. `dirty` state only controls the Save button's enabled/disabled and which value the inputs display (`value={dirty ? name : u.name}`); after Save, `setDirty(false)` snaps values back to server truth but the inputs stay visible.

## §163 Q-277-9

> Does the current World detail page represent the modern Character
> OS World model clearly to an ordinary operator now that World
> identity is first-class, or is the page still primarily an old
> administrative CRUD surface whose structure no longer matches the
> product?
>
> Companion: Should the normal World detail state be a readable
> WORLD VIEW rather than a permanently-open edit form?
>
> Companion: What legitimate operator-facing purpose does
> `Universe.description` still serve now that `Universe.brief` owns
> semantic World identity?

## §164 Slice 9 checklist

- [x] STEP 0 — baseline + dogfood record.
- [x] PART A — inventory current World detail page.
- [x] PART B — view state vs edit state.
- [x] PART C — page-job classification.
- [x] PART D — `Universe.description` forensic.
- [x] PART E — brief-vs-description comparison.
- [x] PART F — Fox & Flour specimen.
- [x] PART G — Patch's Workshop control.
- [x] PART H — generalization.
- [x] PART I — destructive-action placement.
- [x] PART J — character/member surface.
- [x] PART K — World Knowledge surface.
- [x] PART L — Episode / memory surface.
- [x] PART M — information architecture classification.
- [x] PART N — smallest product correction.
- [x] PART O — scope-guard preserved (no dashboard project).
- [x] PART P — Q-277-9 answers.
- [x] PART Q — smallest next question.
- [ ] Commit + push audit; SHA-record.

## §165 Prediction (before source inspection)

Prediction: Q-277-9 lands as **MIXED**. The page IS structurally a CRUD/settings surface (always-open edit form; destructive buttons adjacent to identity edit; description labeled ambiguously) rather than an operator-facing World home. The smallest correction is likely **PART N option A/B combined**: introduce a read-only overview default with an explicit "Edit" affordance, keep the destructive lifecycle actions but relocate them below or in a distinct "Danger" region, clarify or hide `Universe.description` (now redundant with `brief` for its original stated purpose). This is a UX/IA correction, not a dashboard rewrite.

## §166 PART A — Page inventory (render order)

Source: `web/src/routes/workspace/universes.$id.tsx:110-333`.

| # | Element | Data source | Read/Edit | Notes |
|---|---|---|---|---|
| 1 | Back button "Back to worlds" | — | — | Navigate to `/workspace/universes`. |
| 2 | `SectionHeader number={2} title="World detail"` | — | — | Editorial marker. |
| 3 | Icon `<Globe2>` + `<h1>` name | `u.name` | read | `data-testid="universe-detail-name"`. |
| 4 | Slug + optional archived pill | `u.slug`, `u.archived_at` | read | Small text. |
| 5 | Hairline separator | — | — | — |
| 6 | Section h2 **"Edit"** | — | — | Wraps every editable field + destructive controls. |
| 7 | Name `<Input>` | `u.name` ↔ `name` state | **edit (always)** | `maxLength=120`. |
| 8 | "What is this World?" `<textarea>` | `u.brief` ↔ `brief` state | **edit (always)** | `maxLength=2000` + helper copy. |
| 9 | Description `<textarea>` | `u.description` ↔ `description` state | **edit (always)** | No helper copy; no clarifying label. |
| 10 | Save button | mutation `useUpdateUniverse` | action | Disabled unless `dirty`. |
| 11 | Archive / Unarchive button | `useArchiveUniverse` / `useUnarchiveUniverse` | action | Outline variant. |
| 12 | **Delete permanently button** | `useHardDeleteUniverse` | destructive action | `variant="destructive"`; disabled while members/docs exist. |
| 13 | Helper text: "Delete permanently is blocked while this world has members..." | — | text | Only when blocked. |
| 14 | Update-error text | — | text | On mutation error. |
| 15 | Episodes section (h2 + count + link) | `u.episode_count` | read | Link to `/workspace/universes/:id/episodes`; no inline list. |
| 16 | Teammates section (h2 + count + list) | `useSpokespeople().filter(sp.universe === id)` | read | Bulleted list of names → `/spokespeople/:id`. |
| 17 | `<NarrativeMemoryList>` "World memories" | `/api/narrative-memories/?universe=<id>` | read | Empty state: "No memories promoted in this world yet." |
| 18 | Docs section (h2 + count + list) | `useKnowledgeList(workspaceId).filter(d.universe === id)` | read | Bulleted list of titles → `/workspace/knowledge/:id`. Client-side filter — CHARACTER-audience docs are excluded here because they don't set `universe`. |

**Structural observation:** the page interleaves five discrete concerns:
- Identity display (3-4).
- Identity editing (7-9).
- Destructive lifecycle (11-12).
- Membership overview (16).
- Content overview (15, 17, 18).

They render in this order under one flat page — no visual separation between "what this is" and "what to do with it."

## §167 PART B — View state vs edit state (source-verified)

- The page has **no view state**. `useState` initializes empty strings for name/description/brief and the fields render as inputs from first render.
- The visible section heading is "Edit" — labeling the section but not toggling state.
- After Save (`handleSave`), `setDirty(false)` fires. Inputs snap to `u.name`/`u.brief`/`u.description` from refetched data via `value={dirty ? … : u.…}`. Fields remain rendered as inputs; no success toast; no visual acknowledgement other than the Save button becoming disabled.
- `dirty` state is a single boolean covering all three fields — editing any one field enables Save for all three; a bad concurrent edit could unintentionally overwrite a field the operator didn't intend to touch.

**Comparison against sibling detail pages (source-verified):**

| Detail page | Pattern | Notes |
|---|---|---|
| `/workspace/knowledge/:id` (`knowledge.$id.tsx`) | **Pure read + delete.** | No edit form. Metadata `<dl>` table; chunk list; single delete button. |
| `/spokespeople/:id` (`$id.tsx`) | **Read + modal edit.** | `IdentityPanel` renders read-only with an "Edit" pencil button that opens `SpokespersonEditModal`. |
| `/workspace/universes/:id` (this page) | **Always-open form.** | This slice's subject. |
| `/workspace/universes/:id/episodes/…` sibling episode routes | **Also always-open form.** | SESSION 262 pattern — matches this page. |

**Verdict:** the World detail page shares the always-open pattern
with the SESSION 262 Episode surface, but diverges from the older
character/knowledge conventions (read + modal / read + action).
Chris's dogfood reaction targets this specific divergence.

## §168 PART C — Page-job classification

Every operator job listed in the prompt, tested against the current page:

| Operator job | Supported? | Primary/Secondary/Admin/Elsewhere |
|---|---|---|
| Understand what this World is | Partial — name + slug + edit form containing the brief | **PRIMARY (should be)** — currently a form, not a read view. |
| See which characters belong | Yes — bulleted list of member names | **PRIMARY** — supported, minimal. |
| See shared Knowledge | Yes — Docs list, client-filtered on `d.universe === id` | PRIMARY — currently correct but thin. |
| See Episodes / continuity | Partial — count + link to sibling route; no inline list | PRIMARY — actual list lives elsewhere. |
| See / edit World identity | Yes but form-mode-only | **SECONDARY (should be)** — should default to view. |
| Add shared Knowledge | **No** — no action on this page | Elsewhere (`/workspace/knowledge` with picker reset — Slice 6 §120 finding). |
| Create another character in this World | **No** — no action on this page | Elsewhere (`/spokespeople/new`). |
| Inspect narrative memory | Yes — `NarrativeMemoryList` embedded | PRIMARY — supported. |
| Archive/manage lifecycle | Yes | Admin — currently mixed into identity-edit section. |
| Permanent delete | Yes but visually prominent | Admin/DANGER — currently mixed into identity-edit section. |

**Reading:** the page IS the overview page for the World but its
STRUCTURE is a CRUD/settings surface. Chris's UI reaction accurately
reflects the mismatch.

## §169 PART D — `Universe.description` forensic

**Introduced:** commit `8f54bdb` (2026-08-17, SESSION 261 Phase 1) — original Universe app + model. Design doc `UNIVERSE_SCHEMA_V1.md` line 395 field table: > `description | Text | Yes (blank ok) | Operator prose about the world. | None. Not consumed by synthesis.`

**Consumers (source-traced today):**
- Backend synthesis: **NONE.** `grep "\.description" shell/character_os/ shell/apps/universe/` returns zero hits in synthesis code paths.
- Backend serializer: exposes it on GET/POST/PATCH (unchanged since 8f54bdb).
- Backend admin: displayed in the admin (per commit doc).
- SPA universes list (`/workspace/universes`): NOT rendered on rows (only name + counts + slug).
- SPA universe detail (`/workspace/universes/:id`): rendered as an editable textarea (Slice-8-preserved from pre-Slice-8 behavior).
- SPA universe create form (`/workspace/universes`, `CreatePanel`): rendered as a "Description (optional)" textarea below the brief.
- Tests: `test_universe_get_returns_brief` etc. GET/POST/PATCH mechanics — no test asserts description CONTENT.

**Real-DB usage today:**
- Fox & Flour: `description=""`.
- Patch's Workshop: `description="First world for Patch and Rivet"` — a 31-char operator note dating from SESSION 261 that Chris typed pre-Slice-8.

**Historical intent:** "Operator prose about the world. Not consumed
by synthesis." A management-surface / operator-note field.

**Classification today:** **A (operator/admin note)** with a strong overlay of **F (mixed/unclear)** now that Slice 8 introduced `Universe.brief` which occupies the same semantic space with clearer purpose and synthesis consumption.

Chris's Patch's-Workshop note ("First world for Patch and Rivet") is a
useful metadata record — provenance / audit context — that shouldn't
just be discarded. But calling it "Description" and placing it directly
under "What is this World?" invites operator confusion (§170).

**Not delete-worthy without operator direction.** Options for future
disposition — do not implement:
- Rename to `notes` / label as "Operator notes (private, not shown to characters)".
- Move to an admin-only field (invisible in main detail view).
- Deprecate entirely once existing content is preserved elsewhere.

## §170 PART E — brief vs description semantics

| Field | Intended owner | Operator meaning (as labeled today) | Synthesis use | Product value |
|---|---|---|---|---|
| `name` | Universe (identity) | "Fox & Flour Bakery" — the World's name | Yes — passed as prompt scope indirectly | high |
| `slug` | Universe (routing) | URL fragment (`fox-flour-bakery`) | No | low but stable |
| `brief` | Universe (semantic identity) | "What is this World?" — 1-3 paragraph identity | **Yes (§152)** — deterministic WORLD SHAPE block | **high (new)** |
| `description` | Universe (operator note today) | "Description" — untyped textarea | No | ambiguous |

**Can an ordinary operator reasonably distinguish "What is this World?"
from "Description"?** No, not without additional guidance. Both are
free-form text fields on the same section, both are labeled
similarly, and neither the SPA nor the model help-text tells the
operator which one the characters will read.

**Nature of the problem:** primarily **duplicated semantics + labeling
gap**. `description` had a legitimate pre-Slice-8 role ("operator prose
about the world"); Slice-8's `brief` narrowed the WORLD IDENTITY
responsibility to `brief`, leaving `description` in a stale-but-
occupied state — still exposed on the UI, still writable, no obvious
purpose to a fresh operator.

**Not a rename decision here.** Options include:
- Rename operator-visible label to "Notes" or "Operator notes" while preserving the DB column.
- Hide `description` from the primary detail surface entirely; expose only in an admin/settings sub-surface.
- Deprecate cleanly with a preservation path for existing content (Patch's Workshop's 31-char note).

## §171 PART F — Fox & Flour specimen

Chris visits Fox & Flour's detail page six months from now. Can he answer:

| Question | Yes / Partial / No | Where the info comes from today |
|---|---|---|
| What is Fox & Flour? | **Partial** | The brief exists but is inside an editable textarea, not a read-view. The operator has to look at the field VALUE inside a form. |
| Who lives/works here? | **Yes** | Teammates section lists Ruby + Tyson with links. |
| What does everyone here know? | **Partial** | Docs list is shown but empty today (KD=0). Copy doesn't explain audience shape. |
| What has happened here? | **Yes** (mechanically) | `NarrativeMemoryList` embedded; empty today. |
| What can I do next? | **Mixed** | Save (if editing), Archive, Delete permanently, "Manage episodes →". No "Add shared knowledge here" action; no "Add another character here" action. |

**Additional observations:**
- The 331-char brief is present but reads visually as "the value of a form field", not "the definitive answer to what this place is."
- Character count (2) matches DB truth; Docs count (0) matches; Episodes count (2) matches — these are all correct.
- No indication anywhere on this page that Fox & Flour has an assigned "type" (bakery vs workshop vs fantasy world) beyond the brief text.

## §172 PART G — Patch's Workshop control (blank brief, non-blank description)

Patch's Workshop has `brief=""` + `description="First world for Patch and Rivet"`.

| Question | Answer |
|---|---|
| Does the page look incomplete? | Yes — the "What is this World?" field is blank; a fresh operator visiting for the first time sees a large empty textarea under the identity header. |
| Does the operator-note (`description`) accidentally appear to be the primary World identity? | **YES.** Because `brief` is blank and `description` is populated, the only prose the operator sees is Chris's 2026-08-17 metadata note "First world for Patch and Rivet" — which reads as if it's what the World IS, but it's actually an audit note about who created it. |
| Does the page teach the operator how to complete the World? | No. Neither field has an empty-state prompt like "Give this World an identity" or "This is what characters will inherit." |

**Structural finding:** the ordering (name → brief → description) plus
identical visual treatment (both are textareas without differentiating
copy or affordances) means that when brief is blank the operator's
attention naturally lands on description. That's the exact pattern
Slice 8 explicitly tried to fix at the semantic layer (§149 contract)
but the SPA layout undermines it.

## §173 PART H — Generalization

Test the current page structure against future World shapes:

| Specimen | Current page structure holds? | Notes |
|---|---|---|
| Bakery World with 2 characters (today's Fox & Flour) | Marginal | Content-list sections short enough that the CRUD form still visually dominates. |
| Workshop World with 2 characters + 27 episodes (today's Patch's Workshop) | Poor | Episode count 27 gets ONE line ("Manage episodes →"); the CRUD form is still the dominant visual element. |
| Dealership with 5-10 characters | Poor | Teammates section grows; the CRUD form still consumes the top third. |
| Fictional fantasy World with many entities | Poor | Same — content grows, but the form dominates the fold. |
| World with no characters yet (Copper Creek Coffee scenario) | Very poor | Nothing to show below the fold; CRUD form is 100% of the visible page; empty-state guidance absent. |
| World with lots of shared Knowledge | Poor | Docs section grows; the "Add shared knowledge" action lives elsewhere (Slice 6 §120 handoff gap). |
| World with many Episodes / memories | Poor | `NarrativeMemoryList` grows; still under the CRUD form. |
| Archived World | Marginal | Small "archived" pill under the header; otherwise identical layout; edit form still active. |

**Verdict on generalization:** the always-open CRUD form does not
scale as the operator's primary interaction surface. Even under
today's small data volumes, it dominates the fold and pushes the
World's actual content (characters, docs, episodes, memories) below.

## §174 PART I — Destructive-action placement

Current layout (§166 rows 10-12):

```
[Save]  [Archive]  [Delete permanently]
```

All three buttons live in a single flex-row directly below the three edit textareas, in the same visual grouping.

**Findings:**
- **Save + Archive + Delete permanently share the same visual weight tier** despite being three qualitatively different operations (mutation, soft-delete, hard-delete).
- **Delete permanently uses `variant="destructive"`** — some visual distinction exists — but it's still adjacent to Save, meaning a mouse-slip during ordinary editing lands next to a permanent-delete button.
- The "Delete permanently is blocked while this world has members. Reassign every teammate and doc first." helper text is defensive but only appears when the button is disabled.
- No confirmation dialog beyond a browser `confirm()` (line 87-91).
- The action group has no header like "Danger zone" or "Lifecycle" to signal it is separate from ordinary editing.

**Verdict:** destructive lifecycle actions are TOO PROMINENT relative
to their frequency and severity. They belong under a "Danger" region
or an overflow menu, or at minimum should be visually separated from
Save.

## §175 PART J — Character / member surface

Source: `universes.$id.tsx:271-294`.

- Teammates section renders as a bulleted list of names only, each a link to `/spokespeople/:id`.
- No portrait / avatar preview.
- No teammate role / brief preview.
- No "Add another character to this World" action.
- No membership reassignment (Chris already knows characters cannot cross-Universe attach — Slice 3 §57 M2M signal).
- Count matches DB truth.

**Verdict:** the members section functions as a **link list**, not
a member roster. Coherent for the current 1-2 characters per World
scale; doesn't scale to dealership-with-10-characters. For today's
Fox & Flour it clearly communicates "Ruby + Tyson live here"; for
a hypothetical larger cast the list would need cards or grouping.

## §176 PART K — World Knowledge surface

Source: `universes.$id.tsx:308-331`.

- Docs section renders `memberDocs = knowledge.data.filter(d => d.universe === id)` — a client-side filter on `d.universe`.
- **CHARACTER-audience KDs are excluded** because they don't set `universe` at the document level (they set it implicitly via M2M spokespeople who belong to the Universe). This is a subtle Slice-1/§10 finding: the page shows only UNIVERSE-audience docs, not everything a character in this World can retrieve.
- **WORKSPACE-audience KDs are also excluded** for the same reason.
- No "Add shared knowledge to this World" action — the operator must navigate to `/workspace/knowledge`, then re-pick the World via `UniverseScopePicker` (Slice 6 §120 handoff gap).
- Copy above the list simply says "Docs (N)" — no audience clarification; no "these are Universe-shared" hint.

**Verdict:** the current page does NOT naturally communicate "this
is knowledge everyone in Fox & Flour can use." The list is
correct-by-construction for UNIVERSE-audience docs but the framing
is silent about audience. A CHARACTER-audience KD attached to Ruby
would not appear here — which is technically correct (that KD
belongs to Ruby, not the World) but the section header "Docs" doesn't
say so.

## §177 PART L — World Episode / memory surface

- Episodes: h2 + count + copy + link to `/workspace/universes/:id/episodes`. No inline list. Episodes are managed on a sibling page.
- Memory: `<NarrativeMemoryList filter={{universeId: u.id}} showSource title="World memories">` — inline embed of a full memory list. Empty state present.

**Verdict:** hybrid — memories inline, Episodes off-page. Neither
gets prominent visual weight; both live below the CRUD form. The
page reads as "a settings record with a members list, some memories,
some docs" rather than "the home of this World's ongoing story."

**Home-vs-settings verdict for the whole page:** **settings record.**

## §178 PART M — Information architecture classification

Classify each current section into an IA bucket:

| Section (render order) | IA bucket |
|---|---|
| Name / slug / archived-pill header (rows 3-5) | OVERVIEW |
| "Edit" section: Name input (row 7) | SETTINGS |
| "Edit" section: "What is this World?" textarea (row 8) | OVERVIEW (content should be) / SETTINGS (form is) |
| "Edit" section: Description textarea (row 9) | SETTINGS / uncertain (§170) |
| Save button (row 10) | SETTINGS |
| Archive/Unarchive (row 11) | SETTINGS / DANGER (light) |
| Delete permanently (row 12) | DANGER |
| Delete-blocked helper (row 13) | DANGER guidance |
| Update-error text (row 14) | SETTINGS feedback |
| Episodes section (row 15) | ACTIVITY / STORY |
| Teammates section (row 16) | CHARACTERS |
| NarrativeMemoryList (row 17) | ACTIVITY / STORY |
| Docs section (row 18) | KNOWLEDGE |

**Ordering vs model:** current order interleaves OVERVIEW with
SETTINGS with DANGER at the top of the page, and CONTENT / CHARACTERS
/ KNOWLEDGE / ACTIVITY at the bottom. A more coherent order would be
roughly: OVERVIEW → CHARACTERS → KNOWLEDGE → ACTIVITY/STORY →
SETTINGS → DANGER.

## §179 PART N — Smallest product correction

Options from the prompt evaluated against Slice 9 evidence:

| Option | Would it address Chris's UX concern? | Would it address §170 brief-vs-description? | Would it address §174 destructive placement? | Cost |
|---|---|---|---|---|
| A. Explicit read-only default state + Edit toggle | **Yes (primary complaint)** | Partial (view state at least makes the two fields displayable as distinct rendered text vs input) | No (buttons stay where they are) | Small SPA change |
| B. Separate Overview and Settings visually | Yes | Partial | Yes if Danger moves too | Small SPA change |
| C. Rename or hide `description` | No (form still open) | **Yes** (primary description issue) | No | Small SPA + optional serializer/help_text |
| D. Move destructive actions | No (form still open) | No | **Yes** (primary Danger issue) | Small SPA change |
| E. Add a World brief summary card at the top | Partial (view of brief improves) | Partial | No | Small SPA change |
| F. Something smaller | — | — | — | — |
| G. Current page is fine; preference only | — | — | — | — |

**Recommendation:** the smallest coherent correction that addresses
Chris's primary complaint AND the two structural issues §170 + §174
is a **combined A + B + D**: introduce a read-only default view with
an explicit Edit affordance, and while restructuring for view/edit,
separate destructive lifecycle from identity settings into a distinct
region (labeled "Lifecycle" or "Danger"). Option C (rename/hide
description) is a small companion decision that can land in the same
slice or as a separate micro-slice — either way, it depends on Chris's
disposition of the field per §170.

**Not recommended:** F/G. G would ignore Chris's operator observation;
F is undefined.

**What the smallest correction is NOT:**
- Not a new World dashboard.
- Not tabs.
- Not a routing change.
- Not an Episode redesign.
- Not a Knowledge UI reshape.
- Not a membership reassignment surface.
- Not new activity feeds.

The correction is a **view-mode default + IA re-grouping** on the
existing single-page detail surface. Estimated scope: one file
(`universes.$id.tsx`), possibly one companion test file, no schema
change, no migration, no backend change.

## §180 PART O — Scope guard preserved

Slice 9 does not recommend:
- Giant analytics dashboard.
- Multi-tab rewrite.
- New routing architecture.
- New World homepage system.
- Episode redesign.
- Knowledge redesign.
- New activity feed.
- New membership architecture.
- New settings subsystem.

The audit did not find that the existing surface fundamentally cannot
support the required operator jobs. The finding is: the existing
surface's DEFAULT STATE and INTERNAL ORDERING don't match the modern
product. The correction is small and stays on the same route/page.

## §181 PART P — Q-277-9 answers

1. **Is the current page primarily a World detail page or a CRUD/settings page?** **CRUD/settings** — dominated by an always-open edit form + destructive actions; content overview lives below.
2. **Does the always-open edit form harm the operator model?** **YES** (Chris's dogfood observation is validated by structural comparison to sibling detail pages).
3. **Should normal state be read-only overview with explicit Edit?** **YES** — matches the older character/knowledge patterns and gives content visual priority over settings.
4. **What is `Universe.description` today?** **A + F** — an operator/admin note field whose responsibilities now overlap with the (new) `Universe.brief`. Not synthesis-consumed. Real-DB shows Patch's Workshop uses it for a metadata note ("First world for Patch and Rivet"). Not delete-worthy without operator direction.
5. **Is brief-vs-description understandable?** **No.** Both are free-form textareas with similar labels and identical visual treatment; the operator has no cue for which one characters will read.
6. **Are characters surfaced coherently?** **Yes for small casts (1-2), poor for large casts.** Current bulleted-name list is minimal but correct.
7. **Is World-shared Knowledge surfaced coherently?** **Partial.** The Docs list is technically correct (Universe-audience docs only) but framing is silent about audience.
8. **Are lifecycle actions too prominent?** **YES.** Delete permanently sits inline with Save in the same button row.
9. **Does the page function as the home of a World?** **NO.** It functions as a settings record with a members list below.
10. **What is the smallest justified correction?** **Combined A + B + D** per §179: read-only default view + explicit Edit + separate identity settings from destructive lifecycle. Optional companion (C) `Universe.description` disposition.

**Q-277-9 verdict: MIXED.** The page mechanically works and passes
its regression suite; it accurately represents the DB data. But its
structure does not represent the modern World product model to an
ordinary operator, and Chris's dogfood observation is source-verified
as a real UX gap, not just a preference.

## §182 PART Q — Smallest next falsifiable question

Given Slice 9's evidence, the smallest next question is a scope-locked
implementation slice:

> **Q-277-10** — If the `/workspace/universes/:id` page defaults to a
> read-only overview (World name + brief rendered as prose; character
> list; docs/episodes/memories sections unchanged) with an explicit
> "Edit" affordance that reveals the current three-field form, and
> destructive lifecycle actions (Archive / Delete permanently) move
> into a visually distinct region below the primary content, does
> Chris's UX friction (§162) close without any schema change, without
> touching `Universe.description`, without touching the Knowledge UI,
> and without touching the character wizard?

Answering Q-277-10 requires only SPA changes to
`web/src/routes/workspace/universes.$id.tsx` (and possibly a companion
test file). Scope explicitly excludes:
- Any schema change.
- Any change to `Universe.description` (that's a follow-on question — see below).
- Any Knowledge UI change.
- Any character wizard change.
- Any Episode redesign.
- Any new routes.
- Any new hooks.

**Alternate smaller questions** (present, do not select):

- **Q-277-10-alt-A** (description-only): before touching layout, decide `Universe.description`'s disposition. Options: rename operator-visible label to "Notes"; hide from default view; deprecate. Landing this first would tighten the Q-277-10 scope by removing the description-vs-brief label question.
- **Q-277-10-alt-B** (return to Knowledge handoff): tackle the Slice 6 §120 handoff gap first ("Teach {character} about your business" → preserved `?universe=<uuid>&spokesperson=<uuid>` + audience preselection). Answers Chris's original Slice-6 friction directly. Orthogonal to the World detail page redesign.
- **Q-277-10-alt-C** (character-brief decomposition observation): watch whether operators naturally trim World-identity content from character `business_brief` fields now that `Universe.brief` owns identity. Observation-only, no code.

Do NOT begin any of these without Chris + ChatGPT explicit approval.

## §183 Slice 9 findings — separated

**OBSERVED FACT (real-DB / source):**
- Fox & Flour Bakery: `brief` populated (331 chars, matches Chris's dogfood), `description=""`. Save + persistence verified.
- Patch's Workshop: `brief=""`, `description="First world for Patch and Rivet"`.
- `web/src/routes/workspace/universes.$id.tsx` renders an always-open form with Save + Archive + Delete-permanently in a shared button row directly below the identity textareas.
- Every synthesis-consumer grep for `\.description` in `shell/character_os/` returns zero hits (confirmed for Slice 6, re-confirmed here).
- Sibling detail pages: knowledge is pure-read-plus-delete; spokesperson is read + modal edit; Episode is always-open form (SESSION 262 pattern matching this page).

**SOURCE-DERIVED FACT:**
- The always-open pattern is an emerging convention in the SESSION 261/262 Universe/Episode wave. It diverges from older character/knowledge conventions.
- Universe.description is documented as "operator prose about the world; not consumed by synthesis" (`UNIVERSE_SCHEMA_V1.md:395`).
- Slice-8's `Universe.brief` (§149) inherits the "operator-writeable description of what the World is" responsibility that `description`'s docstring originally claimed.
- The Docs section is client-filtered on `d.universe === id`, silently excluding CHARACTER-audience KDs — technically correct, semantically undocumented on the page.

**OPERATOR CONTEXT (Chris):**
- "I was able to update it but I am not crazy about how it looks since the forms just stay even after you save."
- Operator context is validated by the source structure; not aesthetic preference alone.

**INFERENCE:**
- The always-open form pattern was a reasonable SESSION 261 default when Universe was purely admin metadata (no first-class semantic payload). Slice 8's addition of a semantic `brief` field elevates `brief` to overview-worthy content — but the page structure hasn't caught up.
- `Universe.description` and `Universe.brief` are now semantically overlapping. The overlap is small enough that a labeling change + IA correction addresses it without a data migration.
- Destructive-action prominence was tolerable when the World was a barely-used substrate; now that operators enter meaningful semantic content, the mismatch is more visible.

**PRODUCT RECOMMENDATION (Chris + ChatGPT decide):**
- Adopt the smallest correction from §179 (A + B + D combined).
- Defer description-disposition (option C) as a small companion decision — either land in the same slice or separately.
- Preserve Slice 5 invariant unchanged (no wizard changes).
- Preserve Slice 8 semantics unchanged (no synthesis wiring changes).

## §184 Unresolved questions (Slice 9 — deferred)

- Should the SESSION 262 Episode detail page get the same view-mode treatment for consistency? (Out of Slice 9 scope; separate future question.)
- Should the Docs section on the World detail page also surface CHARACTER-audience docs attached to that World's members, with an audience badge distinguishing UNIVERSE from CHARACTER? Or does that belong in the eventual Knowledge UI reshape?
- Should the World detail page grow a "Add another character to this World" action, or does the operator naturally go to `/spokespeople/new` and pick the World from the Slice-5 wizard picker?
- Should the World detail page grow a "Add shared knowledge to this World" action that pre-fills the audience picker (Slice 6 §120 handoff gap)? Related to Q-277-10-alt-B.
- What is the correct operator-visible label for `Universe.description` if we don't repurpose or delete it? "Notes"? "Operator notes"? "Internal"?
- Should Fox & Flour eventually receive an authored Universe-audience KD (the Slice 6 §112 historical specimen) or does the compact brief suffice for now? Deferred to dogfood observation.

## §185 Slice 9 landed SHA

_Landed SHA: `8a27622` (Slice 9 audit commit)._

---

# Slice 10 — Q-277-10 — World detail view/edit correction (implementation)

Chris + ChatGPT approved Slice 9 §179 Option **A + B + D + C**:
- **A** — read-only overview default + explicit Edit affordance.
- **B** — separate identity settings from destructive lifecycle.
- **D** — lifecycle actions move into a distinct region.
- **C companion** — `Universe.description` remains the existing DB
  field but its operator-visible label becomes **"Operator notes
  (optional)"** with clarifying helper copy. **No** internal rename;
  no migration; no synthesis change.

Slice 10 lands the smallest SPA-only implementation of that
correction.

## §186 Slice 10 baseline

- HEAD @ Slice 10 open: `3aada74` (Slice 9 SHA-record). Clean, pushed.
- Real-DB verified: `Fox & Flour Bakery.brief` still 331 chars
  (Chris's Slice-8 dogfood specimen preserved). No mutation since
  Slice 9 close.

## §187 Q-277-10

> If the `/workspace/universes/:id` page defaults to a read-only
> overview (World name + brief rendered as prose; character list;
> docs/episodes/memories sections unchanged) with an explicit "Edit"
> affordance that reveals the current three-field form (Name + What
> is this World? + Operator notes), Save/Cancel return to the
> overview, and destructive lifecycle actions (Archive / Delete
> permanently) move into a visually distinct region below the primary
> content, does Chris's UX friction (§162) close without any schema
> change, without touching `Universe.description`'s internal name,
> without touching the Knowledge UI, and without touching the
> character wizard?

## §188 Slice 10 acceptance criteria (recorded before implementation)

1. **Default state:** `/workspace/universes/:id` opens in **Overview** — no textareas or inputs visible for identity content. Name shown as `<h1>`; brief shown as prose paragraphs (or an empty-state hint if blank).
2. **Explicit Edit affordance:** an "Edit" button appears near the top of the page. Clicking it swaps the Overview into an Edit form.
3. **Edit form contents:** three fields in this order —
   - **Name** (text input)
   - **What is this World?** (textarea; helper copy explaining it is shared identity characters inherit)
   - **Operator notes (optional)** (textarea; helper copy explaining it is private operator reference, NOT consumed by synthesis)
4. **Save behavior:** persists via existing `useUpdateUniverse` mutation (payload unchanged — `{name, description, brief}`), then returns to Overview showing the refetched data.
5. **Cancel behavior:** discards staged edits and returns to Overview without hitting the API.
6. **Danger region:** Archive/Unarchive + Delete permanently move into a distinct section below the primary content sections (Characters / Episodes / Docs / Memories), labeled clearly (e.g. "Lifecycle" or "Danger zone"). Not inline with Save.
7. **Preserved sections:** Teammates list, Docs list, Episodes link, `NarrativeMemoryList` — unchanged behavior, may be reordered for coherent IA per §178.
8. **API contract preserved:** no new endpoints; no serializer change; `Universe.description` DB field unchanged; `useUpdateUniverse` payload shape unchanged.
9. **Zero backend / migration / synthesis / model changes.**
10. **Regression:** all existing SPA tests pass. New tests cover view default, Edit-toggle, Save-returns-to-Overview, Cancel-returns-to-Overview, "Operator notes (optional)" label present, Danger region separate from Save.

## §189 Slice 10 prediction (before implementation)

Prediction: **Q-277-10 CONFIRMED.** The change is SPA-only inside
one file (`web/src/routes/workspace/universes.$id.tsx`); no backend
touch; no test that depended on `data-testid="universe-name"` or
`data-testid="universe-description"` breaks — those testids can be
preserved on the Edit form while the Overview uses distinct testids.
The `handleSave` payload shape is unchanged (still
`{name, description, brief}`). Fox & Flour's brief renders as prose;
Patch's Workshop's blank brief triggers an empty-state hint. Chris's
UX friction §162 closes because the page no longer defaults to a
form. Description-vs-brief operator confusion (§170) closes via the
label change + helper copy — no internal rename required.

_(Falsifiable by: any acceptance criterion above failing; any
existing SPA test regressing without a clean update; any operator
mutation path breaking.)_

## §190 Files changed (exact scope)

| File | Kind | What |
|---|---|---|
| `web/src/routes/workspace/universes.$id.tsx` | rewrite | Introduce `mode: "view" \| "edit"` state defaulting to `"view"`. Add `OverviewPanel` (brief as prose, empty-state hint if blank, operator-notes section that only renders when notes are non-empty). Add `EditPanel` with three fields (Name, "What is this World?", "Operator notes (optional)") + Save + Cancel + helper copy distinguishing brief-shared-identity from notes-private. Add `DangerRegion` at the bottom of the page (Archive/Unarchive + Delete permanently) with "Lifecycle" heading + explanatory copy. Edit affordance is a right-aligned "Edit" button next to the name header. |
| `web/src/routes/workspace/universes.detail.test.tsx` | new | 7 regression tests: default renders Overview; blank-brief empty-state hint; Edit reveals the form + hides the Edit button + shows "Operator notes (optional)" label + helper copy; Save fires update with `{name, brief, description}` and returns to Overview; Cancel does not call mutation and returns to Overview; Danger region separate from Edit form; Overview notes section only when non-empty. |

**Not touched (per Slice-10 scope-lock):**
- `web/src/routes/workspace/universes.tsx` (list + create page).
- `web/src/components/spokesperson-wizard.tsx` (Slice-5 inline `+ Create new World` — unchanged).
- `web/src/lib/api/universes.ts` (API contract unchanged).
- Any `shell/apps/*` code (zero backend change).
- Any migration (`Universe.description` DB column name unchanged).
- Any synthesis path (Slice-8 wiring untouched).
- Knowledge UI, character wizard, Episode surface.

## §191 Behavior before → after

**Default page state**
- Before: always renders the "Edit" form (Name + brief + description as textareas + Save + Archive + Delete permanently in one row).
- After: renders `OverviewPanel` with `brief` as prose paragraphs and operator-notes rendered only when populated. Editable content is not visible until the operator clicks Edit.

**Edit affordance**
- Before: none — the form was always active.
- After: right-aligned "Edit" button next to the World name; visible only in Overview mode.

**Save behavior**
- Before: `setDirty(false)` snaps values to server truth; inputs stay visible.
- After: `useUpdateUniverse.mutateAsync({name, brief, description})` fires, then `onSaved()` returns the page to Overview showing refetched data.

**Cancel behavior**
- Before: did not exist.
- After: `onCancel()` returns to Overview without calling the mutation. Staged edits are discarded (staged state lives in the EditPanel component; unmount discards).

**Destructive actions**
- Before: `Save`, `Archive`, `Delete permanently` shared the same flex-row directly below the identity textareas.
- After: `Archive` + `Delete permanently` live in the `DangerRegion` at the bottom of the page (below Characters / Episodes / Docs / Memories) inside a destructive-tinted bordered card labeled "Lifecycle". Save stays inside the Edit form.

**Operator-facing label**
- Before: `Description` (both fields — brief and description — looked visually identical with no clarifying copy).
- After: `What is this World?` + helper "every character in this World inherits and uses during synthesis"; `Operator notes (optional)` + helper "characters do not use this and it is not consumed by synthesis". Distinction is explicit.

**API contract**
- Unchanged. `useUpdateUniverse` still POSTs `{name, brief, description}`. `Universe.description` DB column and its serializer field name are untouched.

## §192 PART W — Prediction vs actual

Prediction from §189 was: **CONFIRMED.** Actual result matches
prediction across every acceptance criterion.

| Acceptance criterion (§188) | Predicted | Actual |
|---|---|---|
| 1. Default state = Overview | YES | YES — `mode` starts at `"view"`; `OverviewPanel` renders; no textareas visible. `test_defaults_to_Overview_with_the_brief_rendered_as_prose` locks. |
| 2. Explicit Edit affordance | YES | YES — right-aligned button next to the name header; `data-testid="universe-edit-toggle"`. |
| 3. Three-field form with "Operator notes (optional)" + distinguishing helper copy | YES | YES — `test_clicking_Edit_reveals_the_three_field_form` asserts label + copy. |
| 4. Save persists via existing hook + returns to Overview | YES | YES — `useUpdateUniverse.mutateAsync({name, brief, description})` called with exact shape; then `setMode("view")`. Test asserts payload + return-to-Overview. |
| 5. Cancel discards + returns to Overview without hitting API | YES | YES — `test_Cancel_returns_to_Overview_and_does_NOT_call_the_mutation` locks. |
| 6. Danger region distinct from ordinary editing | YES | YES — `DangerRegion` at the bottom with destructive-tinted border, "Lifecycle" heading, its own helper copy. Test asserts Save is never in the same visual group as Archive/Delete. |
| 7. Preserved sections | YES | YES — Teammates / Docs / Episodes link / `NarrativeMemoryList` unchanged; only reordered so the DangerRegion is last. |
| 8. API contract preserved | YES | YES — no changes to `universes.ts`; `useUpdateUniverse` payload identical. |
| 9. Zero backend / migration / synthesis / model changes | YES | YES — `git status` shows only two files changed under `web/src/routes/workspace/`. |
| 10. All existing SPA tests pass + new tests cover the criteria | YES | YES — 672/672 (Slice-8 baseline 665 + 7 new). Zero regressions. |

**Q-277-10 verdict: CONFIRMED.** No falsification signal.

## §193 Test totals + DB state

- **New SPA tests:** 7/7 pass in `universes.detail.test.tsx`.
- **Full SPA suite:** 672 passed / 672 total in 6.48s (52 files). Baseline 665 + 7 new. Zero regressions.
- **TypeScript check:** `npx tsc --noEmit` exit 0.
- **Backend:** unchanged; no regression run necessary. Slice-8 baseline (2321/2321) unaffected.
- **Real-DB state:** Fox & Flour Bakery brief still 331 chars; Patch's Workshop still blank brief + 31-char description. Zero data mutation.

## §194 Runtime / behavior inspection (source-derived)

- Overview default: `mode = "view"`; `OverviewPanel` renders `{u.name}` as `<h1>` (in the page header) + `{u.brief}` as a `<p>` with `whitespace-pre-wrap` and `text-cream text-base`. Empty brief triggers an italic muted-foreground hint.
- Overview notes section: only renders when `u.description.trim()` is non-empty. Zero-noise for the common case where operators haven't added notes.
- Edit reveals `EditPanel`, a controlled form seeded from server truth on mount. `dirty` is derived (not stateful) — comparing `name.trim()`, `brief`, `notes` against the incoming `u` values.
- Save button disabled unless `dirty` or `update.isPending`.
- Cancel is a `variant="ghost"` button with an `<X>` icon; disabled while update is pending to prevent race with a successful Save.
- Danger region uses `border-destructive/40 bg-destructive/5` styling to visually separate from the neutral `border-luxe bg-card/60` used by Overview / Edit / Episodes sections.

**No runtime dogfood performed** — provider spend explicitly not
authorized in this slice, and the change is view-layer only. Chris
can dogfood the new layout at his convenience via the SPA per §195.

## §195 Dogfood instructions for Chris (optional)

1. Navigate to `/workspace/universes` and click **Fox & Flour Bakery**.
2. Verify the page opens in **Overview** — you see the World brief as prose (the 331-char paragraph you authored in Slice 8), no textareas visible.
3. Click the **Edit** button (right of the name).
4. Verify the three-field form appears: Name, "What is this World?", "Operator notes (optional)". Each has clarifying helper copy — brief-is-shared vs notes-are-private.
5. Try editing something small (e.g. add a period at the end of the brief).
6. Click **Save**. Verify the page returns to Overview showing the updated brief.
7. Click **Edit** again. Edit the brief. Click **Cancel**. Verify you return to Overview with the un-cancelled original brief still shown.
8. Scroll to the bottom of the page. Verify **Archive** and **Delete permanently** live inside a bordered "Lifecycle" region visually distinct from ordinary editing.
9. Navigate to **Patch's Workshop** to see the blank-brief empty-state hint.
10. **Operator notes on Patch's Workshop:** currently reads "First world for Patch and Rivet" (your 2026-08-17 SESSION 261 note). Confirm that in Overview mode this text renders under an **"Operator notes"** header with a "not used by characters" clarification — that verifies the label decision landed.

**What to report back:** whether the default-Overview shape feels
like the World's home; whether the empty-state hint on Patch's
Workshop reads clearly; whether "Operator notes (optional)" as a
label is understandable; whether the Danger region placement feels
right (bottom of page) or you'd prefer another location.

## §196 Findings — separated

**OBSERVED FACT (source / test):**
- `web/src/routes/workspace/universes.$id.tsx` rewritten from an always-open-form scaffold into a view/edit page with a distinct Danger region.
- One new test file: 7/7 pass covering default-view, empty-state hint, Edit-reveal + labels + helper copy, Save-with-payload + return-to-Overview, Cancel-no-mutation + return-to-Overview, Danger-region-separate, notes-section-only-when-populated.
- Full SPA suite 672/672 pass (baseline 665 + 7 new).
- No backend / migration / synthesis / API-contract changes.
- `Universe.description` DB column and serializer field name unchanged; only operator-visible label + helper copy change.

**SOURCE / TEST-DERIVED FACT:**
- The `handleSave` payload shape `{name, brief, description}` is byte-identical to Slice 8's payload — the backend serializer accepts unchanged.
- The `dirty` state derivation is now local to `EditPanel` (computed from staged inputs vs server truth) instead of a boolean-toggle across the whole page — simpler, matches per-panel scope.
- Empty operator-notes cleanly omits its Overview section (no stray header). Empty brief triggers an explicit CTA-shaped hint pointing at Edit.
- The Danger region uses `border-destructive/40 bg-destructive/5` treatment matching the existing `variant="destructive"` button conventions.

**INFERENCE:**
- Chris's dogfood UX friction §162 closes structurally: the page no longer defaults to a form.
- Description-vs-brief operator confusion §170 closes via the label change + distinguishing helper copy without any DB / API / serializer / migration touch.
- The change is fully additive and reversible — reverting a single file returns to Slice-8 behavior.

**UNRESOLVED QUESTION:**
- Should the same view/edit + Danger pattern be applied to the sibling Episode detail page (`episodes.$id.tsx`) for consistency? Slice 9 §184 noted this as deferred; still deferred.
- Should the Docs section on the World detail page also surface CHARACTER-audience docs attached to members, with audience badges? Slice 9 §184 finding; still deferred.
- Should `Universe.description`'s internal name be renamed at the model / serializer / SPA type level to match its now-visible label ("notes")? Not necessary for Q-277-10; a possible small companion slice.
- Does the welcome-page handoff gap (Slice 6 §120, "Teach {character} about your business" → generic Knowledge page with picker reset) become the natural next slice, now that both World identity and the World detail page are shaped correctly?

## §197 PART Q — Smallest next falsifiable question

Given Slice 10's confirmation of Q-277-10, three natural downstream
questions are visible. Recommend ONE, do not implement:

> **Q-277-11-A** (welcome-page handoff) — If the
> `/spokespeople/{id}/welcome` "Teach {character} about your business"
> action preserves `?universe=<uuid>&spokesperson=<uuid>` in the
> handoff to the Knowledge page (or a scoped variant of it) and
> pre-selects the character's Universe as the audience scope, does
> the operator's mental-model handoff (Slice 6 §120) close without
> any Knowledge UI reshape?

or:

> **Q-277-11-B** (Universe.description internal rename) — If the DB
> column `Universe.description` is renamed to `Universe.notes` via a
> `RenameField` migration + serializer + SPA type updates
> (preserving the "notes / not used by characters" operator label
> already shipped in Slice 10), does the internal name / operator
> label alignment close without any behavioral change?

or:

> **Q-277-11-C** (Episode detail view/edit) — apply the Slice-10
> view/edit + Danger pattern to `/workspace/universes/:id/episodes/…`
> (or wherever Episode detail lives) for cross-surface consistency.

**Recommendation:** **Q-277-11-A** is highest-leverage — it closes
the original Slice-6 operator friction and unblocks the next
Knowledge-UX arc. Q-277-11-B is small housekeeping that can land
any time. Q-277-11-C is nice-to-have consistency work whose value
depends on operator dogfood of the Slice-10 layout first.

Do NOT begin any of these without Chris + ChatGPT explicit approval.

## §198 Slice 10 landed SHA

_Landed SHA: `e24e475` (Slice 10 implementation commit)._

---

# Slice 11 — Q-277-11 — Post-character Knowledge handoff semantics (audit-only)

Chris + ChatGPT accepted Slice 10 after operator dogfood.

**Slice 10 operator dogfood confirmation (§199 below).** Slice 11
investigates the welcome-page → Knowledge handoff before touching
any code — because the phrase "Teach {character} about your
business" carries an unresolved audience ambiguity now that Character
OS has first-class World identity + character identity + separate
audience-scoped Knowledge lanes.

## §199 Slice 10 operator dogfood confirmation (recorded)

**OPERATOR OBSERVATION (Chris via ChatGPT):**
- Both Fox & Flour Bakery and Patch's Workshop detail pages "look good" in the Slice-10 layout.
- Default Overview state feels correct.
- Real "Operator notes" behavior was visible on Patch's Workshop because its old `Universe.description` value was populated ("First world for Patch and Rivet").
- The operator-visible distinction between **What is this World?** (brief, shared, characters inherit) and **Operator notes (optional)** (private, not consumed by synthesis) is understandable.
- No additional World-detail UX complaint surfaced during this dogfood.

**Classification:** OPERATOR DOGFOOD CONFIRMATION. Slice 10 is
accepted from both automated verification (§193 — 672/672 pass) and
operator runtime inspection. Do not reopen the World-detail page
unless new evidence requires it.

## §200 Slice 11 baseline

- HEAD @ Slice 11 open: `82a8c35` (Slice 10 SHA-record). Clean, pushed.
- Real-DB: KD=0, KC=0. Fox & Flour brief=331 chars (Chris's dogfood specimen preserved), description=0. Patch's Workshop brief=0, description=31 (SESSION 261 legacy note). Zero drift since Slice 10.

## §201 Q-277-11

> When an operator finishes creating a character and clicks
> "Teach {character} about your business", is the intended Knowledge
> audience naturally the character's entire World, the specific
> character, or does the action represent an unresolved choice
> between those two?
>
> Companion: What context should Character OS preserve automatically
> during the handoff from character onboarding into Knowledge so the
> operator never has to reconstruct facts the system already knows?

## §202 Slice 11 checklist

- [x] STEP 0 — baseline + Slice 10 dogfood confirmation.
- [x] PART A — trace current welcome page.
- [x] PART B — trace route handoff.
- [x] PART C — Knowledge page input contract (re-confirm Slice 6 finding).
- [x] PART D — semantic intent of "about your business".
- [x] PART E — classify onboarding knowledge examples.
- [x] PART F — is one default audience justified?
- [x] PART G — preserved context vs operator decision.
- [x] PART H — button wording audit.
- [x] PART I — character with existing World (Tyson specimen).
- [x] PART J — first character in new World (Copper Creek Coffee / Hazel specimen).
- [x] PART K — multi-character World (Ruby + Tyson specimen).
- [x] PART L — World-detail entry point comparison.
- [x] PART M — character-detail KnowledgePanel comparison.
- [x] PART N — minimum handoff contract.
- [x] PART O — does this require full Knowledge UI reshape?
- [x] PART P — generalization.
- [x] PART Q — Q-277-11 answers.
- [ ] Commit + push audit; SHA-record.

## §203 Prediction (before source inspection)

Prediction: the current wording is a **pre-Universe artifact**
(SESSION 107 spokesperson-≈-business assumption). Semantic verdict:
**MIXED** — "your business" reads as WORLD-scoped for most content
(menu, pricing, policies), but the "Teach {character}" framing
implies CHARACTER audience. Both are legitimate operator intents and
should not be collapsed into one default. World-context preservation
is **always safe**; audience selection is **never safe to infer**
because the wrong inference either broadens (character-private fact
becomes World-shared) or narrows (World fact becomes character-only)
retrieval materially. Minimum handoff contract: preserve
`universe_id` + `spokesperson_id` + `origin`, and require an
explicit operator audience choice on the destination surface with
those two options pre-labeled (Everyone in {World} vs {Character}
only).

## §204 PART A — Current welcome page (source-verified)

Route: `/spokespeople/:id/welcome` — `web/src/routes/spokespeople/welcome.tsx`.

- Component: `SpokespersonWelcomeRoute`. Reads `id` from `useParams`; calls `useSpokesperson(id)` → full spokesperson payload including `spokesperson.universe` (Slice-8 `Universe.brief` transitively available via a second fetch if needed).
- Header: "§ — Setup · Step 2 of 4" + `<h1>` "Meet {name}."
- Portrait + copy block: "{name} is ready to work. Here's what they know so far:" followed by a bulleted list — **"Their name and personality" / "The brief you gave them about your business" / "How to sound like themself, in their own voice"**.
- Follow-up copy: *"That's a solid starting point — but {name} doesn't know your **specifics** yet. Your menu, your pricing, your policies, the details a real customer would ask about. That's the next step, and it's what turns {name} from a polished demo into something that actually represents your business."*
- Primary CTA: `<Button asChild size="lg" data-testid="welcome-teach-cta"><Link to="/workspace/knowledge">…Teach {name} about your business…</Link></Button>` — **string href, no query params, no router state**.
- Secondary CTA: "Say hi to {name} first" → `/spokespeople/{id}/talk`.
- Tertiary: `SkipLink` → `/spokespeople/{id}` (detail page).
- Trailing note: *"if you talk to {name} before adding knowledge, they'll answer generically — small talk about your industry, not specifics about your business."*

**Data available in component state at the moment of the click:** id, name, portrait, personality, business_brief (transitively via spokesperson payload), `spokesperson.universe` (nullable UUID). **All context needed for a preselecting handoff is already present client-side.** The Link simply doesn't propagate any of it.

## §205 PART B — Route handoff (source-verified)

- Destination: `<Link to="/workspace/knowledge">` — bare string.
- No `?universe=<uuid>&spokesperson=<uuid>` query params.
- No `state={…}` prop for react-router-dom navigation state.
- No `sessionStorage` / `localStorage` write.
- No pre-mutation to seed the destination form.

**Context preserved during navigation:** **NONE.**

**Context lost:**
- The spokesperson id the operator just created.
- The Universe the spokesperson belongs to (`spokesperson.universe`).
- The onboarding origin (that the operator is coming from character-welcome, not from the nav rail).
- Any freshly-known character/World state the destination could use to pre-fill audience.

## §206 PART C — Knowledge page input contract (re-confirmed)

Grep source: `/Users/donkeyking/Donkey_Betz/character-os/web/src/routes/workspace/knowledge.tsx` for `useSearchParams`, `useLocation`, `location.search`, `query`.
Result: **zero hits** for query-string reading. The `query` matches are the local `useState("")` for the Serper search input, unrelated to URL params.

**Slice 6 §120 finding re-confirmed at current HEAD:** `/workspace/knowledge` does not accept `?universe=`, `?spokesperson=`, router state, props, or persisted client state. It initializes every form via `useState` from scratch.

Backend already supports the query params (`apps/embeddings/views.py:117-126` accepts `?universe=<uuid>` and `?workspace=<uuid>`, and `?spokesperson=<uuid>` at line 101) — the gap is SPA-side only.

## §207 PART D — Semantic intent of "Teach {character} about your business"

Test the natural operator meaning of the phrase using the four
inputs the prompt names.

1. **Current copy on the welcome page** (§204):
   - Header line "Teach {name} about your business" — reads as "the character is the pupil; your business is the material."
   - Body copy elaborates the content: "your menu, your pricing, your policies." All of those are **business-of-record facts**, not character-personal facts.
2. **Historical design intent** (SESSION 107 commit `1b80ebf`, Slice 6 §107): `Spokesperson` was "the unit of brand identity"; `business_brief` was "one-paragraph description of the business this spokesperson represents." Under that model, "Teach {character} about your business" was reasonable because there was no separate business entity — the character *was* the business. Post-SESSION-261 that assumption no longer holds.
3. **Knowledge audience model (Delta, SESSION 276):** CHARACTER-audience KDs are single-character-restricted; UNIVERSE-audience KDs are shared across every character in the World; WORKSPACE-audience KDs are workspace-wide (deprecated per Slice 6 §35). A "business fact" the current copy names (menu / pricing / policy) is most coherently UNIVERSE-audience.
4. **Modern World semantics** (Slice 7-8): the World owns identity + shared Knowledge. Character owns role + personality + character-specific expertise + private Knowledge.

**Verdict on the natural meaning:** the copy is **semantically MIXED** — the phrase "Teach {character}" reads CHARACTER-target, but the body-copy content examples ("menu, pricing, policies") are WORLD-shared facts. This is directly the pre-Universe residue Slice 6 §107 identified. The single button today collapses two distinct operator intents into one flow that then dumps the operator on a generic Knowledge page.

Choices A/B/C/D from the prompt evaluated:

- **A** ("your business" = the World Tyson belongs to): fits body copy examples; feels natural in modern architecture.
- **B** ("your business" = Tyson himself): matches "Teach {character}" grammar; only fits the pre-Universe model.
- **C** (either, depending on the fact): matches current operator reality — some facts are World-shared, others are character-specific.
- **D** (a broader mixed onboarding corpus): matches how welcome-body-copy actually frames it (menu + pricing + policies + "details a customer would ask") — a bag of onboarding content that spans both audiences.

**Best answer: C** — with the acknowledgement that the current single-button collapses the two audiences invisibly.

## §208 PART E — Onboarding-knowledge classification table

Non-exhaustive; each row classifies the natural audience given the modern World / character split.

| Example | Natural audience | Notes |
|---|---|---|
| Business hours | **WORLD** | Everyone at the bakery / dealership / workshop needs to know the same hours. |
| Pricing (list) | **WORLD** | Detailed pricing belongs in KDs; Universe-audience. |
| Menu / product catalog | **WORLD** | Same. |
| Deposit policy | **WORLD** | Same. |
| Refund policy | **WORLD** | Same. |
| Location | **WORLD** | Physical address is shared. |
| Company history | **WORLD** | Founding story, milestones — narrative shared context. |
| Brand story | **WORLD** | Same. |
| Shared safety rules | **WORLD** | Workshop safety, kitchen safety, dealership regulations. |
| Character's personal expertise ("Ruby knows sourdough starter care") | **CHARACTER** | Belongs to one character; another character shouldn't cite as own knowledge. |
| Character's private backstory ("Rivet arrived in the workshop after…") | **CHARACTER** | Same. |
| Character-specific workflow ("Tyson runs the espresso machine") | **CHARACTER** | Role-scoped. |
| Character-specific opinions/preferences | **CHARACTER** | Voice/preference is character-owned. |
| Something like "our warranty covers X for Y months" (mixed businesses) | **AMBIGUOUS** | Depends on business type — auto-dealership warranty is World, personal-training coach's clients don't have warranties. |
| Personality / tone descriptions | **NOT KNOWLEDGE** | Belongs on `Teammate.personality`, not KD. |

**Non-business generalization:**
- **Fantasy World:** setting/lore/factions = WORLD; individual character abilities/backstory = CHARACTER.
- **Workshop:** shared tools, safety rules, workshop location = WORLD; per-inventor expertise = CHARACTER.
- **Dealership:** brand roster, warranty terms, dealership location = WORLD; individual salesperson deal-desk specialties = CHARACTER.
- **Outdoor company:** route library, seasonal safety, gear standards = WORLD; individual guide's certifications/routes-mastered = CHARACTER.
- **Solo one-character World:** most content is safely WORLD (temporarily equivalent to CHARACTER); but that temporary equivalence should not collapse the audience model — a future second character would need to inherit World facts.

**Pattern:** the "world-level facts everyone in the world needs" set is
LARGE (10+ common examples); the "character-specific-only facts" set
is also legitimate but narrower. Neither dominates.

## §209 PART F — Is one default audience justified?

Two separate questions the prompt insists on keeping distinct.

**Q1: If the operator clicks "Teach Tyson about your business", can Character OS safely assume `World = Fox & Flour`?**

**YES — with high confidence.** Tyson belongs to exactly one World
(`Teammate.universe`, Slice-5 required-at-create). The character's
Universe is a fact the system already knows and never has to
disambiguate. Preserving World context automatically is:
- Always correct (Tyson's Universe is unambiguous).
- Always useful (removes a redundant operator selection).
- Compatible with legacy `universe=NULL` teammates (would simply
  omit World context; destination surface can fall back gracefully).

**Q2: Should Character OS safely assume `Audience = Everyone in Fox & Flour`?**

**NO.** §208 shows that both WORLD and CHARACTER are legitimate
audiences for onboarding content. Choosing one by default risks:
- **Broadening (auto-default = WORLD):** a character-private fact ("Tyson's favorite espresso method is…") gets promoted to Universe-shared, and Ruby starts citing it as her own — violates SESSION 275 "system actions should not silently broaden audience" invariant.
- **Narrowing (auto-default = CHARACTER):** a World fact ("celebration cakes require 7 days' notice") gets scoped to Tyson only. Ruby never cites it. Other future characters never inherit it. Operator has to duplicate — reintroducing the exact Slice 6 §113 duplication drift Slice 8 was designed to close.

**Preservation ≠ inference.** These are distinct operations. World context can be preserved automatically because it's a known fact about Tyson. Audience cannot be inferred safely from content the operator hasn't typed yet.

## §210 PART G — Preserved context vs operator decision

| Context item | System already knows? | Safe to preserve automatically? | Must operator decide? |
|---|---|---|---|
| Current character (Tyson) | Yes (`useParams` on welcome route) | **Yes** — every audience choice references this character or its World. | No decision needed to preserve; may affect audience-multiselect default. |
| Character's World (Fox & Flour) | Yes (`spokesperson.universe`) | **Yes** — fixed for the flow; not disambiguable. | No decision needed to preserve. |
| Onboarding origin (welcome vs nav-rail) | Yes (route history / referrer) | **Yes** — enables destination surface to render "You just created Tyson. What do you want to teach?" copy instead of a generic Knowledge intro. | No decision needed to preserve. |
| Audience choice (WORLD vs CHARACTER vs specific multiple characters) | **No** — depends on the content the operator hasn't typed yet. | **NO — inference is unsafe.** | **YES — explicit operator decision required per §209.** |
| Ingestion method (paste / PDF / URL / search) | No | Already default (Paste); operator can switch tabs. | Operator picks per ingest. |
| Ingest content (title, body, URL) | No | Empty by default. | Operator authors. |

**Principle:** preserve every context the system already knows; require an operator decision only for information the system cannot infer safely (audience + content).

**SESSION 275 relevance:** the "system actions should not silently
broaden audience" invariant applies here directly. Preselecting the
CHARACTER audience is narrowing (safer). Preselecting the WORLD
audience is broadening. **Neither should be silent.** The audience
decision must remain explicit — but the operator should see two
clearly-labeled options (e.g. "Everyone in Fox & Flour" and "Just
Tyson") with the current-character-and-World context already applied,
so the decision is a single click.

## §211 PART H — Button wording audit

Current: **"Teach {name} about your business"** + body copy referencing menu / pricing / policies + framing "turns {name} from a polished demo into something that actually represents your business."

Candidate meanings tested against modern architecture:

| Candidate | Fits modern architecture? | Notes |
|---|---|---|
| Add knowledge to Fox & Flour | WORLD-only; over-specifies audience | Forces WORLD default; wrong for character-private facts. |
| Teach Tyson something | CHARACTER-only; over-specifies audience | Forces CHARACTER default; wrong for shared World facts. |
| Add business knowledge | Neutral but vague; "business" retains the SESSION 107 spokesperson-≈-business connotation | Doesn't disambiguate. |
| Add knowledge | Neutral, generic | Doesn't communicate why this action exists at this moment. |
| Teach your World | WORLD-only; adopts World vocabulary | Same as row 1 semantically. |
| Add onboarding knowledge | Neutral; keys off origin (character-onboarding); acknowledges the mixed-audience reality | Better neutrality; requires the destination surface to expose the audience choice. |
| Teach Fox & Flour and Tyson | Names both; hints at the two-audience choice ahead | Long; but semantically honest. |

**Current wording assessment:**
- **Over-implies CHARACTER audience** ("Teach {name}") while its body copy names WORLD content — the two directly contradict.
- **Historically outdated** — this is a direct copy of the SESSION 107 mental model where one spokesperson = one business. In modern architecture Fox & Flour has multiple characters (Ruby + Tyson) and the "your business" is Fox & Flour, not Tyson.
- **Does not communicate that an audience choice is coming.**

**Verdict:** the wording is a **pre-Universe artifact whose semantics
have been contradicted** by SESSION 261's introduction of Universe
and Slice 8's introduction of `Universe.brief`. It needs to be
revisited alongside the destination surface's audience-choice
affordance. **Do not settle copy in this slice** — the wording
depends on the destination-surface design.

## §212 PART I — Tyson specimen (character with existing World)

Tyson today:
- `universe = Fox & Flour Bakery` (id `1a0af807-…`).
- Fox & Flour `brief = 331 chars` (Chris's Slice-8 dogfood specimen — the bakery's identity is deterministically injected into synthesis §152).
- Fox & Flour `knowledge_document_count = 0`.
- Ruby also in Fox & Flour → this is a multi-character World.

**Operator clicks welcome CTA.** Ideal next screen already knows:
- World = **Fox & Flour** (fixed; operator cannot change without leaving the flow).
- Character = **Tyson** (fixed).
- Onboarding origin = **character-welcome** (enables framing copy: "Add knowledge Tyson can use — either shared with everyone at Fox & Flour or just for Tyson").

**Minimum remaining decision:** the audience.

Illustrative-only (do not settle copy):

> **Who should know this?**
>
> - Everyone in **Fox & Flour** (World-shared — Ruby AND Tyson will inherit)
> - Just **Tyson** (character-specific)

Ingestion method + content follow after the audience is chosen. All
of the World / character context is preserved without a further
operator click.

## §213 PART J — First character in a new World (Copper Creek Coffee / Hazel)

Fresh Universe "Copper Creek Coffee"; first character "Hazel"; blank
Universe brief; no KDs.

Handoff differences:

- **World is still preserved** — Hazel's `universe` UUID is known post-creation. Preselection works.
- **Character is still preserved** — Hazel's UUID is known.
- **Audience choice remains meaningful even when Everyone-in-World temporarily equals Hazel.** If the operator later adds a second character, WORLD-audience KDs Hazel created now must be inherited by the newcomer. CHARACTER-audience KDs must not. That distinction is meaningful at CREATE time even when it seems equivalent at retrieval time.
- **World brief may be blank.** If so, the destination surface should either (a) surface an inline "Give Copper Creek Coffee a World brief?" nudge, or (b) proceed with the audience choice unchanged. Not a hard blocker.

**Do not collapse the audience model based on temporary equivalence.**
Tomorrow-a-second-character-may-arrive means the audience decision
must be made deliberately today even for one-character Worlds.

## §214 PART K — Multi-character World (Ruby + Tyson)

Fox & Flour is now the real specimen.

**Two failure modes the handoff should protect against:**

1. **Character-private fact accidentally becoming World-shared.**
   - Example: "Tyson personally handles wholesale coffee orders" gets ingested as UNIVERSE-audience. Ruby's synthesis now cites it as her own knowledge — the SCOPE RULE (`dialogue_synthesis.py:494-499`) prevents cross-character citation for CHARACTER-scope, but WORLD-scope has no such gate.
   - Ruby cannot know Tyson's private workflow. Broadening it is a real synthesis bug.
2. **World-shared fact accidentally becoming character-only.**
   - Example: "Fox & Flour closes at 3pm on Sundays" gets ingested as CHARACTER-audience for Tyson only. Ruby answers "what are your Sunday hours?" and doesn't have that fact — Chris has to remember to duplicate it, hitting the exact Slice 6 §113 duplication drift Slice 8 was designed to close.

**Which mistake is more likely from the current wording?**

The current button says "Teach {character}" which implies CHARACTER
audience; but the body copy says "your business" content which is
WORLD-shaped. Once the operator lands on the generic Knowledge page,
the `UniverseScopePicker` presents only "World UUID or 'None
(legacy)'" — no CHARACTER option is even offered from the create
flow (Slice 1 §17). So today's failure mode is: **content that
should be CHARACTER-audience gets forced into UNIVERSE (or WORKSPACE
'None (legacy)') because the destination surface doesn't expose the
CHARACTER audience.** That's the **broadening** failure mode —
worse per SESSION 275.

The handoff redesign therefore must expose CHARACTER as a
first-class audience option at the destination surface. Preserving
World alone is insufficient.

## §215 PART L — World-detail entry point comparison

Slice 9 §184 flagged a possible future action on `/workspace/universes/:id`:

> "Add shared knowledge to this World"

Semantic comparison to the welcome-page CTA:

| Origin | Implicit audience default | Preserved context needed | Ambiguity |
|---|---|---|---|
| World-detail "Add shared knowledge to this World" | **UNIVERSE** (unambiguous by origin) | World only | Very low — operator opened the World detail deliberately; the World's audience is what they came for. |
| Character-welcome "Teach {character}…" | **AMBIGUOUS** — see §207-§214 | World + character + origin | High — could be either audience. |

**Verdict:** the two surfaces are **not the same action.** They
should enter the same Knowledge-creation system with **different
preselected context**:

- World-detail origin → destination surface preselects `audience=UNIVERSE + universe=<this-World>`; audience choice is present but pre-answered.
- Character-welcome origin → destination surface preselects `universe=<character's-World>` and highlights both `Everyone in {World}` and `Just {character}` as equally-weighted operator choices.

**Neither surface should exist without the other.** They complement
each other: World-detail supports the "I want to teach Fox & Flour
something new" intent; character-welcome supports the "I just made
Tyson and need to teach him and/or the bakery some things" intent.

## §216 PART M — Character-detail KnowledgePanel comparison

Source: `web/src/components/knowledge-panel.tsx:84-155`.

- Empty state copy: **"{spokespersonName} doesn't know anything yet"** + "Add documents in workspace knowledge — they'll appear here once they apply to this spokesperson."
- Empty-state CTA: **"Open workspace knowledge →"** → `/workspace/knowledge` (bare string, no context preservation).
- Header link: **"Manage workspace knowledge"** → `/workspace/knowledge` (same, no context preservation).

**Comparison:**

| Surface | Copy implies audience | Actual routing |
|---|---|---|
| Character-detail KnowledgePanel | **CHARACTER** ("Tyson doesn't know anything yet") | Bare `/workspace/knowledge` — loses everything, including which spokesperson |
| Character-welcome CTA | **MIXED** (see §207) | Bare `/workspace/knowledge` — loses everything |

**Contradiction:** the character-detail KnowledgePanel implies
CHARACTER audience (its own scope) but its routing loses the
spokesperson id. So even the CHARACTER-scoped intent has to be
re-typed at the destination. Both entry points share the same context-loss failure — different implied audiences, identical
lost-context symptom.

**Same fix reaches both surfaces.** Preserving `?universe=<uuid>` +
`?spokesperson=<uuid>` at the destination benefits both entry
points.

## §217 PART N — Minimum handoff contract

Illustrative-only (per prompt); not a UI design.

**Origin metadata to preserve:**
- `spokesperson_id` — always, when the origin is any character-owned surface.
- `universe_id` — when the character is Universe-bound (Slice-5 required for new characters; nullable-legacy compatible).
- `origin` — a discriminator identifying which surface triggered the handoff:
  - `character_welcome` — welcome page CTA.
  - `character_detail_knowledge_panel` — Manage workspace knowledge link / empty-state.
  - `world_detail_add_knowledge` — future World-detail action (Slice 9 §184).
  - `dashboard_direct` — no origin context; the nav-rail case.

**Destination surface expected behavior (given origin):**
- Both `spokesperson_id` and `universe_id` present → destination surface renders **two audience options** (Everyone in {World} / Just {character}); pre-selects neither; ingestion inputs unblocked once audience is chosen.
- Only `universe_id` present (e.g. from World-detail origin) → destination surface pre-selects `audience=UNIVERSE + universe=<uuid>`; hides CHARACTER choice by default (accessible via a small "actually, restrict to a character" affordance if needed).
- Neither present (dashboard / nav-rail origin) → today's behavior unchanged (`UniverseScopePicker` in its current shape).

**Persistence mechanism:** URL query params
(`?universe=<uuid>&spokesperson=<uuid>&origin=character_welcome`) are
sufficient. React Router state is fragile across refresh; query
params are shareable, testable, and inspectable.

**Backend already supports** the audience filters
(`apps/embeddings/views.py:101,117-126`) for LIST filtering; CREATE
already accepts the audience payload (`universe`, `spokesperson_ids`,
`audience_scope="workspace"` per Slice 5). No backend changes
required.

**What the handoff contract does NOT include:**
- Automatic audience default — audience must remain an explicit operator decision (§209).
- Auto-preselection of an ingestion method — Paste remains the default tab.
- Auto-population of KD title / body — operator authors.
- Any inference from KD content — audience is chosen before content is typed.

## §218 PART O — Does this require the broader Knowledge UI reshape?

Prompt options A/B/C/D evaluated against the audit evidence:

- **A. YES — preselecting World is sufficient.** **Rejected.** Preserving World alone still leaves the operator on the current `/workspace/knowledge` page whose `UniverseScopePicker` presents only "World UUID or None (legacy)" — no CHARACTER audience option is exposed at CREATE. §214 shows that today's failure mode is the operator being forced away from CHARACTER audience. World preselection alone doesn't fix it.
- **B. PARTIAL — World can be preselected but audience still needs a first-class decision.** **CONFIRMED.** This matches every finding: §209 (audience inference unsafe), §210 (audience must be operator-decided), §215 (World-detail vs character-welcome need different preselected context but both need audience as a first-class decision).
- **C. NO — the current Knowledge creation surface fundamentally cannot represent the onboarding intent.** **Partially correct.** The current `UniverseScopePicker` design is Slice-1 §17 identified as inadequate — but the REPRESENTATION problem is at the audience selector, not at the surface as a whole. A modest, scoped reshape (not a full redesign) is required.
- **D. insufficient evidence.** No — enough evidence exists.

**Verdict: B — PARTIAL.** Simple `?universe=<uuid>&spokesperson=<uuid>` preselection preserves the context but does not close the audience-decision gap. The destination surface needs a modest reshape:

- Recast the `UniverseScopePicker` (or an origin-aware variant) as an explicit **"Who should know this?"** audience selector with three positive choices: `Everyone in {World}`, `Just these characters` (multi-select scoped to that World's roster), and — behind an "Advanced" disclosure — `Everyone in this workspace`.
- Origin-preserving preselection (World for World-origin, both audiences shown for character-origin, `?spokesperson=<uuid>` pre-filling the CHARACTER multi-select).

This matches Slice 1 §17's Q-277-2 recommendation and Slice 2 §35's
Q-277-3 WORKSPACE-advanced sharpening. Slice 11's finding confirms
those earlier recommendations were the right direction; the handoff
audit demonstrates concretely why they're needed rather than being
purely aesthetic.

**Not required in this slice:** implementation. Slice 11 is
audit-only; the reshape is Slice 12 (or later) subject to Chris +
ChatGPT scope approval.

## §219 PART P — Generalization

Test the proposed handoff semantics against the specimens:

| Specimen | Handoff behavior under §217 contract | Operator quality-of-life |
|---|---|---|
| Ruby joining Fox & Flour (historical) | universe + spokesperson preserved; audience shown with both options | Good — Ruby's baker expertise vs bakery-wide facts are distinct at CREATE |
| Tyson joining Fox & Flour (real specimen) | Same as above | Good — the exact operator problem Slice 11 targets |
| Third bakery character | Same as above | Good — no reason the pattern degrades |
| Patch joining Patch's Workshop | Same as above | Good — workshop-shared vs Patch-personal expertise |
| Rivet joining an existing Workshop | Same as above | Good — shared workshop context inherited automatically; Rivet-specific role stays scoped |
| Dealership finance specialist | Same as above | Good — dealership-wide policies vs finance-specific knowledge |
| Dealership general spokesperson | Same as above | Good — same shape |
| Fantasy character in a fictional World | Same as above | Good — world lore vs character abilities |
| Solo one-character World | Same as above | Good — the audience choice IS meaningful even when Everyone-in-World == the one character (§213) |
| World with 20 characters | Same as above with multi-select | Good — the multi-select gates the operator from accidentally over-sharing; they pick "Everyone" or a specific subset |

**The operator never needs to understand:**
- M2M through-rows.
- `audience_scope` enum values.
- Universe FK ON DELETE semantics.
- Workspace tenancy.

They see two labeled audience choices in their own vocabulary and
pick one. That is the design goal.

## §220 PART Q — Q-277-11 answers

1. **What does "Teach {character} about your business" mean today?** **Ambiguous / mixed** (§207). The button phrase reads as CHARACTER-target ("Teach {name}") but the body-copy examples ("menu, pricing, policies") are WORLD-shaped. The two contradict.
2. **Is the phrase semantically outdated?** **YES** (§207-§211). It's a direct copy of the SESSION 107 spokesperson-≈-business assumption, which Universe (SESSION 261) and `Universe.brief` (Slice 8) contradicted. It should be revisited alongside the destination surface's audience-choice affordance.
3. **Should World context always be preserved automatically?** **YES** (§209, §210). The character's Universe is a fact the system already knows and is unambiguous. Preservation is always safe.
4. **Should character context always be preserved automatically?** **YES** (§210). Every audience choice references the character or the character's World. Preservation is always safe.
5. **Can audience safely be inferred?** **NO** (§209). Auto-defaulting to WORLD broadens improperly (violates SESSION 275); auto-defaulting to CHARACTER narrows and reintroduces the Slice 6 §113 duplication drift.
6. **If yes, which audience and why?** N/A — audience must not be inferred.
7. **If no, what is the minimum operator decision?** One click: "Everyone in {World}" or "Just {character}" (with a "Just these characters" multiselect when the operator wants a subset of the World's roster). The World and character are pre-labeled from the preserved context.
8. **Is simple `?universe=<uuid>` preselection sufficient?** **NO** (§218). Preservation without audience-choice affordance leaves the operator with the same Slice 1 §17 friction — the current `UniverseScopePicker` presents only World-or-legacy, no CHARACTER audience.
9. **Is `?spokesperson=<uuid>` also useful?** **YES.** Pre-fills the CHARACTER multi-select when the operator picks the "Just these characters" audience. Also enables the destination surface to render origin-aware framing copy ("You just created Tyson…").
10. **Does the destination Knowledge page need to know the onboarding origin?** **Recommended but not strictly required.** Origin enables (a) origin-aware framing copy, (b) different audience-default weighting between world-detail and character-welcome, (c) return-path navigation. Query param `?origin=character_welcome` is the cheapest way to preserve it.
11. **Does this require the broader Knowledge audience UI reshape?** **YES — partial** (§218 verdict B). Handoff preselection alone is insufficient; the destination surface's `UniverseScopePicker` needs to recast as an explicit "Who should know this?" audience selector with CHARACTER as a first-class option. This matches Slice 1 §17 and Slice 2 §35 earlier recommendations.
12. **Smallest next falsifiable question:** see §222 below.

## §221 Slice 11 findings — separated

**OBSERVED FACT (source):**
- Welcome page CTA `/spokespeople/{id}/welcome` → `<Link to="/workspace/knowledge">` — bare string, no context preserved (`web/src/routes/spokespeople/welcome.tsx:115`).
- Body copy references "menu, pricing, policies" — WORLD-shaped content — while the CTA phrase "Teach {name}" implies CHARACTER audience.
- `/workspace/knowledge` (`web/src/routes/workspace/knowledge.tsx`) does not read `useSearchParams`, `useLocation`, router state, or persisted state. Zero context can be received by the destination today.
- Backend already supports the `?universe=` and `?spokesperson=` query params for LIST (`apps/embeddings/views.py:101,117-126`); CREATE accepts all three audience shapes per Slice 5 serializer.
- Character-detail KnowledgePanel (`web/src/components/knowledge-panel.tsx:90,149`) also routes to bare `/workspace/knowledge` — loses spokesperson id.

**SOURCE-DERIVED FACT:**
- All context needed for a preselecting handoff is present client-side (spokesperson payload includes `universe`). The gap is purely SPA-side plumbing.
- The current `UniverseScopePicker` design (Slice 1 §11) exposes only WORLD or WORKSPACE (via the "None (legacy)" sentinel). No CHARACTER audience option is offered at CREATE.
- Two distinct entry points (welcome + KnowledgePanel) share the same context-loss failure but imply different audiences.

**OPERATOR CONTEXT (Chris via ChatGPT — Slice 10 dogfood):**
- Both World detail pages "look good" post-Slice-10.
- Operator-notes distinction understandable.
- Next area agreed: welcome-page handoff — but wording must be re-examined before implementation.

**INFERENCE:**
- The welcome-page copy is a direct pre-Universe artifact. It was accurate under the SESSION 107 spokesperson-≈-business model; it is contradicted by the modern architecture.
- Simple query-param preselection preserves context but does not close the Slice 1 §17 audience-picker gap. Both changes are required for the handoff to feel modern.
- The Slice 6 / Slice 7 / Slice 8 arcs prepared the substrate. Slice 11's role is to prove that the "just add query params" answer is insufficient and that a modest audience-picker reshape is now unblocked.

**PRODUCT RECOMMENDATION (Chris + ChatGPT decide, not implemented):**
- Combine §217's handoff-context contract with §218's audience-picker reshape into one scope-locked slice.
- Both surfaces (welcome CTA + character-detail KnowledgePanel) benefit from the same routing + destination changes.
- Do NOT change the welcome-page wording in isolation — the copy depends on the destination surface's audience-choice framing.
- Preserve Slice 5 (World-required-at-create), Slice 8 (Universe.brief in synthesis), Slice 10 (World detail view/edit) invariants throughout.

## §222 Unresolved questions (Slice 11 — deferred)

- Should the destination surface be a modified `/workspace/knowledge` page (reshape in place) or a new scoped `/workspace/knowledge/new` route that reads query params + surfaces the audience picker + falls back to the current page for legacy operators? Design decision, not audit.
- Should the audience picker's third option (WORKSPACE) be surfaced at all at the character-welcome origin, or hidden entirely because the origin implies World/Character scoping? Slice 2 §35 recommendation was "advanced disclosure"; that recommendation still stands.
- Should the welcome-page copy include a preview of the World brief so the operator sees what "everyone in Fox & Flour" already knows? Related to Slice 7 §138 (character wizard read-only World brief preview) but distinct — this would be on the welcome page after character create.
- Should the character-detail KnowledgePanel's empty state + `Manage workspace knowledge` link also route with `?spokesperson=<uuid>` preservation? Same fix, same slice most likely.
- Should there be a return path from the Knowledge destination back to the welcome page (or the character detail) so the operator naturally continues onboarding after adding a first KD? Nice-to-have; not blocking.

## §223 Smallest next falsifiable question

Given Slice 11's evidence, the smallest next question is a scoped
implementation slice:

> **Q-277-12** — If the `/spokespeople/:id/welcome` "Teach {character}
> about your business" CTA and the `/spokespeople/:id`
> character-detail KnowledgePanel's `/workspace/knowledge` links
> preserve `?universe=<uuid>&spokesperson=<uuid>&origin=<origin>`
> query params, AND the destination `/workspace/knowledge` page
> reads those params to pre-select the character's Universe and
> render an explicit **"Who should know this?"** audience selector
> with two first-class choices (Everyone in {World} / Just
> {character}) plus an "Advanced" disclosure for WORKSPACE, does
> the onboarding handoff close both entry points without introducing
> a new route, without a backend model change, and without breaking
> the current dashboard/nav-rail Knowledge flow (which continues to
> render today's `UniverseScopePicker` when no query params are
> present)?

This is a **combined implementation** slice — the handoff
preservation and the audience-picker reshape must land together
because either alone leaves the operator stranded (§218). Scope
lock:

- Only two files touched for handoff plumbing (`welcome.tsx`, `knowledge-panel.tsx`).
- Only one file touched for the destination reshape (`workspace/knowledge.tsx`).
- Optional: one new SPA test file per touched surface.
- **Zero** backend / model / migration / synthesis / character-wizard / World-detail / Episode changes.
- **Compatibility fallback preserved:** when no query params are present, the destination renders today's `UniverseScopePicker` unchanged. The dashboard / nav-rail path is untouched.

**Alternate smaller questions** (present, do not select):

- **Q-277-12-alt-A** (welcome-page-only): change only the welcome-page wording + routing without the audience-picker reshape. Rejected by §218 verdict B — preservation without audience choice leaves the same friction.
- **Q-277-12-alt-B** (audience-picker-only): reshape the destination without touching the handoffs. Reduces welcome/panel context loss but doesn't leverage the fact that the origin surface knows the audience-relevant character. Loses half the benefit.
- **Q-277-12-alt-C** (audit continuation): audit the current `UniverseScopePicker` component's callers workspace-wide before touching it. Would surface any callers outside `/workspace/knowledge` that would break. Confirmed by grep to be scope-only within `/workspace/knowledge` (Slice 1 §6.2 already inventoried). Not necessary as a separate slice.

## §224 Slice 11 landed SHA

_Landed SHA: `5d335e0` (Slice 11 audit commit)._

---

# Slice 12 — Q-277-12 — Contextual character-origin Knowledge handoff (implementation)

Chris + ChatGPT approved Slice 11's Q-277-12 with one product
sharpener: **contextual character-origin flows do NOT expose
WORKSPACE audience.** The contextual decision is exactly two
first-class choices — `Everyone in {World}` and `Just {Character}`.
The generic dashboard/nav-rail `/workspace/knowledge` flow is
untouched when no contextual params are present.

## §225 Slice 12 baseline

- HEAD @ Slice 12 open: `6a42181` (Slice 11 SHA-record). Clean, pushed.
- Real-DB: KD=0, KC=0. Fox & Flour brief=331; Patch's Workshop description=31. Zero drift.
- Backend contract already supports both target audience payloads:
  - UNIVERSE create: `{workspace, universe: <uuid>, title, ...content}` — no `audience_scope`, no `spokesperson_ids` (Slice 5 serializer §299).
  - CHARACTER create: `{workspace, spokesperson_ids: [<uuid>], title, ...content}` — no `audience_scope`, no `universe` (Slice 5 serializer §299).
- `CreateKnowledgePayload` interface at `web/src/lib/api/knowledge.ts:223-247` already declares both fields. **No backend / serializer / API-client changes required.**

## §226 Q-277-12

> If the `/spokespeople/:id/welcome` Knowledge CTA and the
> character-detail `KnowledgePanel` links preserve the context
> Character OS already knows (universe + spokesperson + origin), and
> `/workspace/knowledge` uses that context to present an explicit
> World-vs-character audience decision (no WORKSPACE option in
> contextual mode), does the onboarding handoff become coherent
> without changing backend semantics or breaking the generic
> Knowledge flow when no contextual params are present?

## §227 Slice 12 prediction (before implementation)

Prediction: **CONFIRMED.** The three-file scope is sufficient. The
`WorkspaceKnowledgeRoute` component will:

1. Read `?universe`, `?spokesperson`, `?origin` via `useSearchParams`.
2. Validate: origin ∈ {`character_welcome`, `character_detail_knowledge_panel`}; universe UUID resolves to an active Universe in the operator's workspaces; spokesperson UUID resolves to a Teammate that BOTH exists and (a) belongs to that Universe OR (b) is universe-null AND the origin is `character_detail_knowledge_panel` (legacy-teammate origin — fall back to generic mode without contextual audience choice).
3. When context is valid: render `ContextualUploadPanel` instead of the existing `UploadPanel`. Header names the World and character. Audience selector shows exactly two first-class choices. Neither is preselected. Ingest tabs (Paste / Upload / URL / Search) render inline BELOW the audience choice; submit is disabled until an audience is picked.
4. On submit: build the appropriate payload — UNIVERSE (`universe: <uuid>`) OR CHARACTER (`spokesperson_ids: [<uuid>]`). Never include `audience_scope="workspace"`. Never mix `universe` with `spokesperson_ids`.
5. When context is absent or invalid: render the existing `UploadPanel` unchanged.

Predicted acceptance-criteria outcomes:

| Criterion | Predicted |
|---|---|
| A. Welcome handoff preserves World + character + origin | YES |
| B. KnowledgePanel handoff preserves World + character + origin (universe when known) | YES |
| C. Contextual destination shows correct World and character names | YES (resolved via existing `useUniverses` + `useSpokespeople`) |
| D. Neither audience silently selected | YES |
| E. World choice → UNIVERSE payload | YES |
| F. Character choice → CHARACTER payload | YES |
| G. WORKSPACE not exposed in contextual mode | YES |
| H. Submit blocked before audience picked | YES |
| I. Bare `/workspace/knowledge` unchanged | YES |
| J. Refresh / deep-link preserves state | YES (URL query params are stateless-persistent) |
| K. Invalid / stale params fail safely without broadening | YES (falls back to existing generic UploadPanel — no audience preselection) |
| L. Existing SPA tests remain green | YES (additive change) |

Expected payload semantics (exact):

- **World audience (Everyone in {World}):**
  ```
  { workspace, universe: <uuid>, title, text_content OR pdf_data_uri OR source_url_input, ... }
  ```
  Backend interprets: `audience_scope=UNIVERSE`.
- **Character audience (Just {Character}):**
  ```
  { workspace, spokesperson_ids: [<uuid>], title, text_content OR pdf_data_uri OR source_url_input, ... }
  ```
  Backend interprets: `audience_scope=CHARACTER`. `spokesperson.universe` is deferred to the backend M2M signal for cross-Universe rejection (Slice 3 §47).

_Falsifiable by:_ any acceptance-criterion failure; any existing SPA test regressing; any payload that mixes `universe` with `spokesperson_ids` or emits `audience_scope="workspace"`.

## §228 Files changed (exact scope)

| File | Kind | What |
|---|---|---|
| `web/src/lib/knowledge/handoff.ts` | new | Shared handoff contract: `KNOWLEDGE_HANDOFF_PARAM` constants, `KNOWLEDGE_HANDOFF_ORIGINS` discriminator union, `buildKnowledgeHandoffPath(...)` builder, `parseKnowledgeHandoff(searchParams)` parser + `looksLikeUuid` shape check. Single source of truth for the query-param contract used by all three surfaces. |
| `web/src/lib/knowledge/handoff.test.ts` | new | 12 pure-function tests: builder with/without universe; parser rejects on missing/unknown/malformed values; round-trip preserves data; origin enum locked at exactly 2 values. |
| `web/src/routes/spokespeople/welcome.tsx` | edit | Import `buildKnowledgeHandoffPath`. Change the primary CTA `<Link to="/workspace/knowledge">` → `<Link to={buildKnowledgeHandoffPath({universeId: spokesperson.universe, spokespersonId: spokesperson.id, origin: "character_welcome"})}>`. Copy unchanged (Slice 11 §211 said wording depends on destination shape). |
| `web/src/routes/spokespeople/welcome.handoff.test.tsx` | new | 2 tests: welcome CTA href carries universe+spokesperson+origin; universe param is omitted for legacy `universe=NULL` teammates. |
| `web/src/components/knowledge-panel.tsx` | edit | Import `buildKnowledgeHandoffPath`. Add optional `spokespersonUniverseId?: string \| null` prop. Both `Manage workspace knowledge` header Link and the `EmptyState`'s `Open workspace knowledge →` Link now route to the same computed `handoffPath` with `origin: "character_detail_knowledge_panel"`. |
| `web/src/routes/spokespeople/$id.tsx` | edit | Caller — passes `spokespersonUniverseId={s.universe}` to `<KnowledgePanel>` (single-line prop addition; source already has `s.universe`). |
| `web/src/routes/workspace/knowledge.tsx` | edit | Import `useSearchParams`, `useUniverse`, `useSpokesperson`, `parseKnowledgeHandoff`. In `WorkspaceKnowledgeRoute`, read handoff params. When `parsed !== null`, render new `ContextualUploadPanel`; else render existing `UploadPanel` unchanged. New `ContextualUploadPanel` + `AudienceOption` + 4 ingest sub-forms (`ContextualPasteForm` / `ContextualUploadForm` / `ContextualUrlForm` / `ContextualSearchForm`) appended before `readableError`. Shared `contextualAudiencePayload` helper enforces the payload contract (World → `{universe}`; Character → `{spokesperson_ids}`; never mixed, never WORKSPACE). |
| `web/src/routes/workspace/knowledge.contextual.test.tsx` | new | 14 tests: name resolution (C); no audience preselected (D); ingest blocked until audience picked (H); WORKSPACE never exposed (G); ingest reveal after choice; UNIVERSE payload shape (E); CHARACTER payload shape (F); bare `/workspace/knowledge` unchanged (I); 5 fail-safe fallback cases (K: sp doesn't resolve / universe doesn't resolve / stale sp-vs-URL mismatch / malformed UUIDs / legacy teammate w/o World); deep-link mounts contextual mode (J). |

**Not touched (per Slice-12 scope-lock):**
- Any backend / serializer / migration / retrieval / synthesis file.
- The character wizard (`spokesperson-wizard.tsx`).
- The World detail page (`universes.$id.tsx`).
- The Universe list / create page (`universes.tsx`).
- Any Episode file.
- The generic `UploadPanel` and its 4 ingest sub-forms — preserved byte-identically for the bare-URL path.
- `Universe.description` internal name (still just an operator-visible label change in Slice 10).

## §229 Payload semantics (exact, source-verified)

Confirmed against `web/src/lib/api/knowledge.ts:223-247` `CreateKnowledgePayload` + Slice 5 serializer §299.

**World audience (Everyone in {World}):**
```
POST /api/knowledge/
{
  workspace: <workspace-uuid>,
  universe:  <world-uuid>,
  title:     <string>,
  text_content OR pdf_data_uri OR source_url_input (+ optional via_serper),
}
```
- Backend interprets: `audience_scope=UNIVERSE`.
- Fields NEVER emitted: `spokesperson_ids`, `audience_scope`.

**Character audience (Just {Character}):**
```
POST /api/knowledge/
{
  workspace:         <workspace-uuid>,
  spokesperson_ids:  [ <character-uuid> ],
  title:             <string>,
  text_content OR pdf_data_uri OR source_url_input (+ optional via_serper),
}
```
- Backend interprets: `audience_scope=CHARACTER`.
- Fields NEVER emitted: `universe`, `audience_scope`.
- Backend M2M signal (Slice 3 §47) enforces cross-Universe rejection: because the operator arrived through a character whose Universe was validated at handoff parse time (§231), the M2M attach is guaranteed to satisfy `sp.universe_id == doc.universe_id` — where the KD has `universe=NULL` (character-only pool) and the character has whatever universe it belongs to. This is the existing SESSION 276 shape; Slice 12 does not change it.

**WORKSPACE audience is impossible from contextual mode.** No code path in `ContextualUploadPanel` / its 4 sub-forms sets `audience_scope="workspace"`. WORKSPACE remains reachable only via the pre-existing `UniverseScopePicker` "None (legacy)" sentinel inside the generic `UploadPanel`, which is only rendered when there are no handoff params.

## §230 Compatibility behavior (source-verified)

**Bare `/workspace/knowledge`:**
- `parseKnowledgeHandoff(new URLSearchParams())` returns `null`.
- The `parsed ? … : <UploadPanel />` branch renders the pre-Slice-12 `UploadPanel` unchanged.
- All four generic ingest forms + the generic `UniverseScopePicker` behave byte-identically to Slice 11.
- Dashboard/nav-rail entry point unaffected. Locked by `test_bare /workspace/knowledge unchanged (I)`.

**Legacy `universe=NULL` teammate via character-detail KnowledgePanel:**
- Handoff URL includes `?spokesperson=<uuid>&origin=character_detail_knowledge_panel` but NOT `?universe=<uuid>`.
- `parseKnowledgeHandoff` returns `{universeId: null, spokespersonId, origin}`.
- `ContextualUploadPanel` mounts, `useUniverse(undefined)` returns `data: undefined`, contextual mode detects `!uData` → falls back to `<UploadPanel/>`.
- Rationale: "Everyone in {World}" has no target when the character has no World, and CHARACTER-only for a legacy teammate should go through the existing legacy path unchanged. Locked by `test_falls back when a legacy universe=NULL teammate arrives via character_detail origin`.

**Stale query params** (character was moved to a different Universe after the URL was generated):
- `parseKnowledgeHandoff` succeeds (shape valid).
- `ContextualUploadPanel` resolves both sides via TanStack Query hooks. The `paramMatchesTeammate` guard rejects `sp.universe !== universeIdParam`; falls back to generic `UploadPanel`. Locked by `test_falls back when the spokesperson.universe doesn't match the URL universe (stale)`.

**Malformed UUIDs / unknown origin in URL:**
- `parseKnowledgeHandoff` rejects at the shape layer (regex UUID check + origin enum check). Returns `null` → generic `UploadPanel`. Locked by `test_falls back when malformed UUIDs are in the URL`.

**Refresh / deep-link:**
- URL query params are stateless-persistent. Directly navigating to `/workspace/knowledge?universe=…&spokesperson=…&origin=…` (as `MemoryRouter` does in tests) renders contextual mode from first paint. Locked by `test_mounts directly on the contextual URL and renders contextual mode (J)`.

## §231 Prediction vs actual

Predicted **CONFIRMED**; actual **CONFIRMED**. Every acceptance criterion matches the §227 table.

| Criterion | Predicted | Actual | Evidence |
|---|---|---|---|
| A. Welcome handoff preserves World + character + origin | YES | YES | `test_routes to /workspace/knowledge with universe + spokesperson + origin=character_welcome` |
| A (legacy). Universe omitted for `universe=NULL` teammate | YES | YES | `test_omits the universe param when the character is legacy universe=NULL` |
| B. KnowledgePanel handoff preserves context | YES | YES (source-verified — new `handoffPath` used by both Links) |
| C. Human-readable World + character names | YES | YES | `test_resolves World + character names in human vocabulary (C)` |
| D. Neither audience silently selected | YES | YES | `test_does NOT preselect either audience (D)` |
| E. World → UNIVERSE payload | YES | YES | `test_sends {workspace, universe, title, text_content} — no spokesperson_ids, no audience_scope (E)` |
| F. Character → CHARACTER payload | YES | YES | `test_sends {workspace, spokesperson_ids: [<uuid>], title, text_content} — no universe, no audience_scope (F)` |
| G. WORKSPACE never exposed in contextual mode | YES | YES | `test_does NOT expose WORKSPACE as an audience option (G)` |
| H. Ingest blocked until audience picked | YES | YES | `test_blocks ingest until an audience is picked (H)` |
| I. Bare `/workspace/knowledge` unchanged | YES | YES | `test_renders the pre-Slice-12 UploadPanel (with UniverseScopePicker) when no params (I)` |
| J. Deep-link / refresh preserves state | YES | YES | `test_mounts directly on the contextual URL and renders contextual mode (J)` |
| K. Invalid / stale params fail safely | YES | YES (5 sub-cases) | `test_stale / invalid handoff params fail safely (K)` block |
| L. Existing SPA tests remain green | YES | YES | Full suite 700/700 pass |

## §232 Test totals + DB state

- **New SPA tests:** 28/28 pass across three files (`handoff.test.ts` 12; `welcome.handoff.test.tsx` 2; `knowledge.contextual.test.tsx` 14).
- **Full SPA suite:** 700 passed / 700 total in 6.65s (55 files). Baseline 672 + 28 new. Zero regressions.
- **TypeScript check:** `npx tsc --noEmit` exit 0.
- **Backend:** unchanged; no regression run necessary. Slice 8 backend baseline (2321/2321) unaffected.
- **Real-DB state:** unchanged. KD=0, Fox & Flour brief=331 chars, Patch's Workshop description=31 chars, 9 teammates, 2 Universes.

## §233 Chris dogfood-readiness

Slice 12 is SPA-only + fully additive; automated verification is thorough. **Optional operator dogfood** can validate the runtime feel but is not required to establish correctness.

If Chris wants to dogfood:

**Sequence W — welcome-page handoff:**
1. From `/dashboard`, click "New spokesperson".
2. Complete the wizard for a test character in Fox & Flour (or any Universe you don't mind polluting temporarily — pick "+ Create new World" if you want an isolated test World).
3. On the welcome page, click **"Teach {name} about your business"**.
4. Verify the destination URL is now `/workspace/knowledge?universe=<uuid>&spokesperson=<uuid>&origin=character_welcome`.
5. Verify the page shows a **"Teach {name} in {World}"** header (not the pre-Slice-12 generic "What your spokespeople know.").
6. Verify TWO audience options: **Everyone in {World}** / **Just {name}**. Neither is preselected.
7. Verify the ingest tabs (Paste / Upload PDF / URL / Search) DO NOT render until one audience is picked.
8. Pick **Everyone in {World}**. Ingest a small paste — one sentence like "Business hours: 7 AM – 3 PM daily." Submit.
9. Verify the created KD lands in Universe-audience (visible on `/workspace/universes/<id>` Docs section).
10. Repeat with **Just {name}** to verify CHARACTER audience creation lands on the character's KnowledgePanel.

**Sequence P — KnowledgePanel handoff:**
1. Navigate to any Universe-bound character detail page (e.g. `/spokespeople/<tyson-id>`).
2. Scroll to the Knowledge section. Click **"Manage workspace knowledge"** in the header (or "Open workspace knowledge →" in the empty state).
3. Verify the URL includes `?universe=<uuid>&spokesperson=<uuid>&origin=character_detail_knowledge_panel`.
4. Same contextual UI as Sequence W step 5-10.

**Sequence B — bare-flow compatibility:**
1. Navigate to `/workspace/knowledge` directly from the nav rail.
2. Verify the pre-Slice-12 page renders (title "What your spokespeople know.", the four generic ingest forms with the `UniverseScopePicker` "World / Universe" dropdown at the top of each).
3. Confirm no contextual audience selector appears.

**No provider spend required** unless Chris chooses to synthesize with the new KD. Ingestion itself just chunks + embeds; verify against `/workspace/knowledge` list.

## §234 Findings — separated

**OBSERVED FACT (source / test):**
- Handoff contract centralized in `web/src/lib/knowledge/handoff.ts`. 12 tests lock builder + parser shape.
- Welcome CTA + KnowledgePanel header Link + KnowledgePanel empty-state Link all route through `buildKnowledgeHandoffPath(...)`. Verified by inspection + `welcome.handoff.test.tsx`.
- Destination `WorkspaceKnowledgeRoute` reads `useSearchParams`, calls `parseKnowledgeHandoff`, branches on `parsed !== null`. When true renders `ContextualUploadPanel`; when false renders the pre-Slice-12 `UploadPanel` unchanged.
- `ContextualUploadPanel` presents exactly two audience options — no WORKSPACE affordance anywhere. `test_does NOT expose WORKSPACE as an audience option (G)` locks by absence of `/None \(legacy/`, `/workspace-wide/`, and `paste-universe-scope` testid.
- Payload shape enforced by `contextualAudiencePayload()` helper (single source of truth for the World-vs-Character branch). Both payload-shape tests assert `spokesperson_ids` NOT-in payload for World, `universe` NOT-in payload for Character, `audience_scope` NOT-in payload for either.
- Zero backend files, models, migrations, or serializers touched. `git diff --stat` confirms.

**SOURCE-DERIVED FACT:**
- The Slice-5 CHARACTER-required-at-create invariant is unaffected — Slice 12 never mutates Teammate rows, only reads `spokesperson.universe`.
- The Slice-8 `Universe.brief` synthesis wiring is unaffected — Slice 12 never touches synthesis code.
- The generic `UploadPanel` + its `UniverseScopePicker` continue to expose the WORKSPACE-via-legacy-sentinel gesture for the dashboard/nav-rail path per §230. WORKSPACE is deprecated for character-origin flows but preserved for the generic flow.
- All 5 fail-safe fallback cases route to the generic `UploadPanel` — never guess an audience.

**INFERENCE:**
- Slice 11's audit-recommended "handoff preservation + audience-picker reshape" landed as a single coherent slice with no scope creep.
- The `ContextualUploadPanel` duplicates the 4-tab ingest UI internally (as new `Contextual*Form` components). A future consolidation slice could DRY these against the generic forms, but that would risk breaking the compatibility guarantee (bare-URL path unchanged). Duplication is intentional isolation.
- The `contextualAudiencePayload` helper is the single non-negotiable rule; all four contextual sub-forms call it. A future test could add a snapshot lock on its return shape to prevent regressions.

**PRODUCT RECOMMENDATION (Chris + ChatGPT decide):**
- Consider Slice 13 dogfood on live real-mode with actual Tyson/Ruby to confirm operator flow feel.
- Consider a small follow-on that revisits welcome-page copy (Slice 11 §211) now that the destination shape is settled — the wording "Teach {name} about your business" can be re-examined given the destination surface now explicitly asks "Who should know this?".
- Do NOT collapse the four `Contextual*Form` components into shared helpers with the generic path in the next slice — the compatibility isolation guarantee is a live invariant. Any consolidation should be preceded by an audit slice.

## §235 Unresolved questions (Slice 12 — deferred)

- Should the welcome-page copy update in a follow-on slice? "Teach {name} about your business" reads slightly awkwardly given the destination now explicitly frames the audience choice. Candidates: "Teach {name} something", "Add knowledge — for {name} or {World}", "Continue onboarding". Deferred.
- Should the character-detail KnowledgePanel's empty-state copy ("{name} doesn't know anything yet") update to reflect that "knowledge" now has two shapes (World-shared + character-specific)? Deferred; may be evident once dogfooded.
- Should Slice 9's future World-detail "Add shared knowledge to this World" action (Slice 9 §184) reuse the same handoff contract with `origin: "world_detail_add_knowledge"`? That would be a natural sibling to Slice 12's two origins. Add-only, backward-compatible with the current `KNOWLEDGE_HANDOFF_ORIGINS` union. Deferred.
- Should the 4 contextual sub-forms and the 4 generic sub-forms eventually share ingest primitives (title + textarea + PDF picker + URL + Serper)? Consolidation would reduce duplication but requires an audit of the compatibility invariant first.
- Should the character-detail KnowledgePanel's `KnowledgePanelRow` (per-row Make X-only / Detach controls) also route through the contextual page for its "add" flow? Currently no such action exists on the row — this is a hypothetical for a later slice.

## §236 Smallest next falsifiable question

Given Slice 12's confirmation, three natural downstream questions exist:

> **Q-277-13-A** (dogfood-first) — Ask Chris to perform Sequences W + P + B from §233 and report whether the contextual mode feels correct in real operation. If yes, no further code required for this arc. If not, the observation guides Q-277-13-B or -C.

> **Q-277-13-B** (copy micro-slice) — Reword the welcome-page CTA + the KnowledgePanel empty-state copy so both surfaces frame the destination's "Who should know this?" question up-front (e.g. change "Teach {name} about your business" to "Add knowledge — for {name} or {World}"). Single-line-per-surface change, no test churn.

> **Q-277-13-C** (world-detail origin) — Extend the handoff contract to include a `world_detail_add_knowledge` origin and add an "Add shared knowledge" action to `/workspace/universes/:id`. Would create symmetry with the character-origin flow and close Slice 9 §184.

**Recommendation:** **Q-277-13-A first.** Automated verification confirms the mechanics; operator confirmation confirms the ergonomics. Q-277-13-B and -C are small and can land after dogfood if the feel is right.

Do NOT begin any of these without Chris + ChatGPT explicit approval.

## §237 Slice 12 landed SHA

_Landed SHA: `71410da` (Slice 12 implementation commit)._

---

# Slice 12.1 — Q-277-12 hot-fix — Universe-bound CHARACTER payload

Chris dogfooded Slice 12 in real-mode after landing. Sequence W
(welcome-page handoff) → Fox & Flour → picked "Just Tyson" audience
→ ingest. Backend responded 400:

    spokesperson_ids: Legacy (universe=null) docs cannot include
    Universe-scoped spokespeople. Bad: ['Tyson']

## §238 Diagnosis (source-verified)

- Slice 12's `contextualAudiencePayload` Character branch built
  `{workspace, spokesperson_ids: [<uuid>]}` — WITHOUT `universe`.
- The KD would therefore land with `universe=NULL` (legacy pool).
- Backend serializer `apps/embeddings/serializers.py:283-294`
  rejects `spokespeople + universe=None` when any attached
  spokesperson has a non-NULL Universe. This is the SESSION 261
  M2M invariant (Slice 3 §57): `sp.universe_id ==
  doc.universe_id` — always required except for the both-legacy
  carve-out.
- Tyson has `universe = Fox & Flour Bakery`, so his Universe
  mismatched a `universe=NULL` doc → 400. Correct backend rejection.

**Root cause was in Slice 12's payload builder.** The Slice 12 test
`test_sends {workspace, spokesperson_ids: [<uuid>], title,
text_content} — no universe, no audience_scope (F)` explicitly
asserted `expect("universe" in payload).toBe(false)` — locking the
wrong behavior. That assertion was semantically incorrect and the
test suite passed without catching the bug because no test actually
hits the backend serializer's `sp.universe != doc.universe` cross-check.

**Correct payload shape for Universe-bound CHARACTER audience**
(Slice 6 §110, re-verified against
`apps/embeddings/ingestion.py:276-284` audience-scope precedence):

```
{
  workspace: <workspace-uuid>,
  universe: <character.universe.id>,     // REQUIRED: satisfies
                                          // serializers.py:241-253
                                          // cross-check
  spokesperson_ids: [<character.id>],    // wins over `universe` in
                                          // audience_scope precedence
                                          // → audience_scope=CHARACTER
  title: ...,
  text_content OR pdf_data_uri OR source_url_input,
}
```

Precedence at `_persist` (`ingestion.py:276-284`):
`spokespeople` > `universe` > `workspace_shared_intent` > NULL
(rejected by `serializers.py:311-330`).

Resulting KD row: `audience_scope=CHARACTER + universe=<uuid> +
spokespeople=[sp]`. M2M attach succeeds because
`sp.universe_id == doc.universe_id`.

Sending both `universe` and `spokesperson_ids` is NOT "contradictory
mixed audience" — it is REQUIRED for the Universe-bound CHARACTER
shape. The SESSION 276 Slice 12 (embeddings serializer)
contradictory-payload guard only fires for
`audience_scope="workspace" + (spokespeople OR universe)` per
`serializers.py:265-281` — not for `spokespeople + universe`.

## §239 Fix (implementation)

Single production change:

- `web/src/routes/workspace/knowledge.tsx` —
  `contextualAudiencePayload` Character branch changed from
  `{spokesperson_ids: [spokespersonId]}` to
  `{universe: universe.id, spokesperson_ids: [spokespersonId]}`.
  Comment block updated to document the SESSION 261 requirement
  and the precedence rule. World branch unchanged.

Test updates:

- `web/src/routes/workspace/knowledge.contextual.test.tsx` —
  the F-criterion test's expectation corrected to lock the new
  (correct) payload shape: BOTH `universe` AND `spokesperson_ids`
  are asserted present; only `audience_scope` is asserted absent.

Backend defense-in-depth regression added:

- `shell/apps/embeddings/tests/test_knowledge_universe_api.py` —
  new `test_post_knowledge_universe_bound_character_shape_lands_as_character`
  locks the correct Universe-bound CHARACTER payload at the API
  boundary. Posts the exact SPA payload the corrected Slice 12
  now sends and asserts (a) 201 response, (b) resulting KD has
  `audience_scope=CHARACTER`, (c) `universe_id == u.id`, (d) M2M
  contains the spokesperson. This is defense against future
  regressions of the payload contract even if the SPA changes.

## §240 Compatibility invariants (still hold)

- Slice 5: ordinary new characters still require a World.
- Slice 8: `Universe.brief` synthesis wiring unchanged.
- Slice 10: World detail view/edit unchanged.
- Slice 11/12 handoff contract unchanged — only the destination's
  Character-payload construction is corrected.
- Bare `/workspace/knowledge` unchanged (pre-Slice-12 UploadPanel
  path).
- Legacy `universe=NULL` teammates unchanged — the both-legacy
  M2M carve-out still allows their character KDs; the corrected
  helper is only reached via the contextual (Universe-bound)
  handoff, which by construction handles the character's Universe.
- Contextual World-audience payload unchanged
  (`{universe, ...content}` — no `spokesperson_ids`).

## §241 Verification

- **Frontend regression:** 14/14 contextual tests pass with the
  corrected F-expectation; 700/700 full SPA suite pass.
  TypeScript `tsc --noEmit` exit 0.
- **Backend regression:** new `test_post_knowledge_universe_bound_character_shape_lands_as_character`
  passes; broader change-adjacent regression 491/491 pass
  (embeddings + spokespeople + universe apps).
- **Real-DB state:** unchanged (no data mutation from this
  hot-fix).

## §242 Findings — separated

**OBSERVED FACT (source / dogfood):**
- Chris's operator dogfood produced a real 400 from
  `apps/embeddings/serializers.py:283-294`.
- Slice-12 Character-branch payload builder omitted `universe`
  — locked by the F-test's incorrect `expect("universe" in
  payload).toBe(false)` assertion.
- Backend precedence at `ingestion.py:276-284` assigns
  `audience_scope=CHARACTER` when both `spokespeople` and
  `universe` are present.

**SOURCE-DERIVED FACT:**
- The correct Universe-bound CHARACTER payload shape has been
  documented since Slice 6 §110 ("Universe-bound CHARACTER:
  `audience_scope=CHARACTER + universe=<uuid> + spokespeople=[sp]`").
  Slice 12 built the payload against the wrong Slice 6 row and
  the automated tests locked the wrong assertion.
- No backend behavior needed to change.
- Sending both `universe` and `spokesperson_ids` is REQUIRED for
  Universe-bound CHARACTER KDs; it is NOT the same as the
  "contradictory workspace + spokespeople" rejection guarded at
  `serializers.py:265-281`.

**INFERENCE:**
- Automated unit-level SPA tests cannot fully lock backend
  contract compliance — they only assert what the payload
  contains, not whether the backend accepts it. The new backend
  regression closes that gap for this specific payload shape.
- Future contextual-payload changes should be dogfood-verified
  against a real Universe-bound character before merging, OR
  should include a matching backend regression like the one
  added here.

**PRODUCT RECOMMENDATION (Chris + ChatGPT decide):**
- Merge the fix. Re-dogfood Sequence W's "Just Tyson" path to
  confirm.
- No further architectural change required for this arc.
- Q-277-13 next-question options from Slice 12 §236 remain
  valid; Chris's dogfood evidence now includes both the
  operator-flow feel AND the payload correctness.

## §243 Slice 12.1 landed SHA

_Landed SHA: `039172a` (Slice 12.1 hot-fix commit)._












