---
title: "Session 208 — B-2 ↔ B-3 composition arc lands (lock + 4 implementation slices)"
date: 2026-05-20
status: complete
session: 208
previous_handoff: ./SESSION_207_E_ARC_DOGFOOD.md
---

# Session 208 — BC-arc: lock + 4 of 6 slices shipped

## TL;DR

**First composition arc.** Connects the closed E-arc (B-2
Auto-Scripting, SESSION 207) and C-arc (B-3 Personalized Video,
SESSION 203) so per-recipient renders inherit Script knowledge
lineage end-to-end. Five commits this session, plus the
SESSION 207 close-out commits that opened the day:

* `de2d92e` — BC0 scope lock (411 lines; 9 contract rules)
* `e97b06f` — BC1 schema + workspace guard + 5 model tests
* `863d374` — BC2 `talking_head_polished` starter accepts
  optional lineage kwargs + 7 starter tests
* `5ada363` — BC3 REST + launch propagation +
  `derived_campaigns` endpoint + 11 REST tests
* `e76e173` — BC4 SPA picker + derived campaigns surface +
  21 vitest tests (via `react-web-delivery` subagent)

**One slice remains** — BC5 real-mode dogfood + arc close.
Pulled at operator request to preserve validation quality (same
"dogfood rides to the next session when same-day fatigue would
degrade real-mode quality" pattern from SESSION 206→207).

Tests at close: Django **1320 → 1343 (+23)**; SPA vitest
**405 → 426 (+21)**; media-engine unchanged at **214**.
Real-mode spend SESSION 208: **$0** (BC5 deferred).

Scope-lock cadence holds at the new composition-arc shape: 9
rules + 6 slices ship in 1-2 sessions, smaller than strategic-
axis arcs by design.

## Strategic framing

The strategic-axis quartet (B-1 / B-2 / B-3 / B-14) shipped
in SESSIONS 202-207. Each axis is real-mode validated
end-to-end. **BC is the first arc to compose two axes** rather
than add a new one. The "composition is the moat" framing from
the SESSION 207 start-here doc is now concrete:

* Operator drafts a knowledge-grounded Script in B-2 →
  K6.4 verifies citations → operator approves.
* Operator creates a B-3 Campaign with `source_script_id` set
  → server back-fills `template` from `draft_text` → operator
  edits to add `{placeholders}`.
* Operator launches the Campaign → every per-recipient
  Composition inherits the Script's `knowledge_chunk_ids` +
  verification flags; per-recipient `synthesized_brief` is the
  substituted template (rule 5).
* Every personalized Asset's F-arc brief-mode panel surfaces
  the same citations the Script's detail page shows.

The combinatorial product of knowledge-grounded synthesis ×
batched personalization is structurally defensible. Generic
LLM-video competitors can produce one or the other; this is
the first stack that ties them together at the lineage layer.

## What landed

Six commits across the day (one SESSION 207 close + five BC-arc):

### `e817ee5` + `8a1aa49` — SESSION 207 close-out (start-of-day)

Closed the E-arc dogfood + handoff at the start of this
session. See `SESSION_207_E_ARC_DOGFOOD.md` for the
end-to-end real-mode validation against Marcus + the "Five
Good Emperors" Script ($0.25 actual; 7 findings; verifier
panel patch shipped). The B2.6 patch is BC4's most-direct
upstream — the Script-detail "Used by N campaigns" panel that
BC4 adds sits right alongside the verifier panel B2.6 fixed.

### `de2d92e` — BC0 scope-lock proposed → locked same-commit

411 lines. Nine contract rules:

1. Script → Campaign is one-direction (no Script-side
   back-reference; query through `derived_campaigns`
   related_name).
2. Template editable post-derivation (FK is audit trail).
3. Workspace-isolated end-to-end.
4. **Lineage propagates to every per-recipient Asset**
   (load-bearing composition value).
5. Per-recipient `synthesized_brief` = template-substituted.
6. Snapshot at launch, not at create.
7. No new primitives or recipes.
8. Verification flags propagate unchanged.
9. `on_delete=PROTECT` (prevents silent lineage orphaning).

Six slices BC0-BC5. Nine open questions, all proposed with
default resolutions. Operator signed off as-proposed in the
same session — proposal → lock cadence held.

### `e97b06f` — BC1: schema + workspace guard + 5 tests

`PersonalizedCampaign.source_script: FK(Script, null=True,
blank=True, on_delete=PROTECT, related_name='derived_campaigns')`.
Migration `0002_bc1_source_script`. Workspace guard extended at
two layers (`clean()` + pre_save signal's `validated_fields`).

**Q-bc-1 resolved** as-proposed (PROTECT, not SET_NULL).

5 tests pin: nullable default (back-compat), FK + reverse-name
round-trip per rule 1, cross-workspace clean rejection, cross-
workspace signal rejection, ProtectedError on Script delete
when referenced.

Django **1320 → 1325 (+5)**.

### `863d374` — BC2: starter lineage kwargs + 7 tests

`talking_head_polished()` gains four optional kwargs (defaults
None preserve current C-arc behavior):

* `knowledge_chunk_ids` (rule 4)
* `synthesized_brief` (rule 5)
* `verification_status` (rule 8)
* `verification_warnings` (rule 8 + Q-bc-7)

Conditional kwarg-assembly pattern keeps the
`Composition.create` call clean. Defensive `list(...)` copies
on the two list inputs prevent post-call mutation by the
caller from leaking into the persisted row.

**Q-bc-7 resolved**: warnings JSON is COPIED onto every
per-recipient Composition (storage cost trivial; query path
simpler than join-through-FK).

7 starter tests cover: back-compat (no kwargs → empty
fields), each kwarg individually, all 4 together (the
load-bearing BC3 launch-path shape), defensive-copy
semantic.

Django **1325 → 1332 (+7)**.

### `5ada363` — BC3: REST + launch lineage + derived_campaigns + 11 tests

The biggest slice in the arc by LOC. Extends one ViewSet
(`CampaignViewSet`), adds one action to another
(`ScriptViewSet.derived_campaigns`), and propagates lineage
through both `launch` and `retry_recipient` paths.

* `POST /api/campaigns/` accepts optional `source_script_id`:
  workspace-filter, status ∈ {READY, RENDERED}, defensive
  draft_text copy with re-parse for template-syntax errors,
  persists FK.
* `GET /api/campaigns/<id>/` includes `source_script` block
  (`{id, name, status, verification_status, chunk_count}`)
  when set; `null` otherwise.
* Launch path: new `_build_source_script_lineage(campaign)` +
  `_per_recipient_lineage(...)` helpers propagate to every
  per-recipient Composition via the BC2 starter kwargs.
* `GET /api/scripts/<id>/derived_campaigns/` — workspace-
  filtered paginated reverse query.

**Q-bc-2 resolved**: CREATE requires READY/RENDERED; LAUNCH
reads at-launch state regardless (Script may have been
archived post-create; lineage persists).

**Q-bc-3 resolved by absence**: no PATCH/PUT exposes
`source_script_id` mutation post-create.

**Q-bc-9 resolved** as-proposed: 100-row cap + optional
`?status=` filter on derived_campaigns.

11 REST tests across three files (campaigns API + campaigns
launch + scripts API).

Django **1332 → 1343 (+11)**.

### `e76e173` — BC4: SPA picker + derived panel + 21 tests

Delivered via the `react-web-delivery` subagent against a
tight contract brief. Mirrors the SESSION 206 B2.5 delivery
pattern.

* Extended `web/src/lib/api/campaigns.ts` Zod schema with
  `source_script: sourceScriptBlockSchema.nullable().optional()`.
  The `.optional()` covers pre-BC3 list responses that won't
  include the field at all.
* Extended `web/src/lib/api/scripts.ts` with
  `getDerivedCampaigns()` + `useDerivedCampaigns()` hook.
* `/workspace/campaigns/new` adds a Script picker section
  above the template textarea. Filter defaults to
  `?spokesperson=<current>` + `?status=ready`; "Show all
  workspace scripts" toggle drops the spokesperson filter.
  "Use this draft as starting template" copies `draft_text`
  verbatim to the textarea + sets hidden `sourceScriptId`.
* `/workspace/campaigns/:id` adds the `SourceScriptPanel`
  between the page metadata and the CSV paste panel —
  renders only when `campaign.source_script != null`.
* `/workspace/scripts/:id` adds the `DerivedCampaignsPanel`
  below the verifier panel — collapsed when N=0, expanded
  when N>0.
* "Once you create the campaign, the Script link is fixed"
  hint on the create form documents Q-bc-3's immutability.

**Q-bc-4 resolved**: spokesperson+status filter by default,
toggle to widen.

**Q-bc-5 resolved**: no warning when operator heavily edits
the copied template (FK is audit trail).

**Q-bc-8 resolved**: verbatim copy, no placeholder injection.

21 new vitest tests across 3 new test files
(`campaigns.new.test.tsx`, `campaigns.bc4.test.tsx`,
`scripts.bc4.test.tsx`).

SPA vitest **405 → 426 (+21)**. `pnpm build` exit 0.

## All open questions resolved

Nine Qs total; nine resolved across BC0-BC4:

| # | Resolution | Slice |
|---|---|---|
| Q-bc-1 | `on_delete=PROTECT` | BC1 |
| Q-bc-2 | CREATE requires READY/RENDERED; LAUNCH ignores status | BC3 |
| Q-bc-3 | Immutable by absence — no PATCH/PUT on `source_script_id` | BC3 + BC4 hint |
| Q-bc-4 | Picker filters by spokesperson + status=ready by default; toggle to widen | BC4 |
| Q-bc-5 | No warning on heavy edit of derived template | BC4 |
| Q-bc-6 | Extended starter in place (no wrapper) | BC2 implicit |
| Q-bc-7 | Warnings COPIED per Composition, not joined-through-FK | BC2 |
| Q-bc-8 | Verbatim `draft_text` copy, no placeholder injection | BC4 |
| Q-bc-9 | 100-row cap + optional `?status=` filter | BC3 |

## Tests at close

| Suite | Count | Delta |
|---|---|---|
| Django | **1343** | +23 (BC1+BC2+BC3) |
| SPA vitest | **426** | +21 (BC4) |
| Media-engine | **214** | unchanged (no media-engine changes in BC arc) |

## Commits this session

```
e76e173 feat(BC4): SPA Script picker + derived campaigns surface
5ada363 feat(BC3): REST + launch lineage + derived_campaigns endpoint
863d374 feat(BC2): talking_head_polished starter accepts optional lineage kwargs
e97b06f feat(BC1): source_script FK on PersonalizedCampaign + workspace guard
de2d92e feat(BC0): B-2 ↔ B-3 composition arc — scope lock
e817ee5 docs: SESSION 207 close — E-arc B2.6 dogfood + arc close
8a1aa49 fix(B2.6): script detail verifier panel surfaces informational warnings
```

Seven commits. Five BC-arc + two SESSION 207 close-out. **No
remote pushes** per the hard rule.

## What's queued for SESSION 209

**BC5 — real-mode dogfood + arc close.** Pulled at operator
request after BC4 landed; preserves dogfood quality the same
way SESSION 206→207 did.

Plan:

1. Drift sweep (`context-kit doctor`).
2. Pre-fire: restart Celery (BC1 model field + BC2 starter
   signature + BC3 view changes all in stale-worker blast
   zone).
3. Operator drives `/workspace/campaigns/new`:
   * Pick Marcus + click "Use approved Script as starting
     template" → SESSION 207's Five Good Emperors Script.
   * Confirm verbatim `draft_text` lands in textarea.
   * Edit to add `{first_name}` placeholder + minor reframe.
   * Submit → DRAFT.
   * Paste 2-recipient CSV (e.g. Bob @ Acme, Carol @ Initech).
   * Launch → forecast → fan-out.
4. AI tails Django + Celery + media-engine logs in parallel.
5. Validate per-recipient lineage:
   * Each Composition.knowledge_chunk_ids matches Script's.
   * Each Composition.synthesized_brief is the substituted
     text (with the recipient's first_name).
   * Each per-recipient Asset's F-arc brief-mode panel
     renders the citation breakdown.
   * Campaign detail surfaces "Derived from script" block.
   * Script detail's "Derived campaigns (1)" panel updates.
6. Capture findings as TRUST_CALIBRATION entries.
7. Close the arc: handoff, start-here update, INVENTORY
   regen.

Real-mode cost target: **~$0.50** (2 × $0.25 per
`talking_head_polished` per the C-arc baseline).

## Calibration moments worth carrying

* **Composition arcs are different from strategic-axis arcs.**
  Strategic-axis arcs (A/B/C/D/E) ship in 10-13 slices over
  one extended session each. Composition arcs (BC and future)
  ship in ~6 slices because the upstream work is done — they
  add an FK, propagate optional kwargs through a starter, and
  wire a SPA picker. Plan composition arcs at half the slice
  count of strategic-axis arcs.

* **Subagent delivery on tight contract briefs is reliable.**
  The B2.5 + BC4 SPA subagent deliveries both landed clean
  with zero re-work needed. The pattern that makes this work:
  exhaustive backend contract (request shape, response shape,
  status codes), enumerated test requirements (10-12 tests
  with bullet-point coverage), explicit constraints (no
  backend changes, no remote pushes, doc-with-commit). When
  the brief is tight enough that the subagent doesn't need to
  make architectural decisions, the output matches the
  contract.

* **Backend can ship without SPA in composition arcs.** After
  BC1+BC2+BC3 (backend complete), the integration was already
  queryable via curl/REST. The SPA layer is operator-facing
  polish, not load-bearing. This is a useful split: backend
  slices and SPA slices can be reviewed independently, and
  the backend is real-mode-testable before the SPA lands (BC5
  would have been valid against just curl + DB state if BC4
  had slipped).

* **Pyright Django ORM noise is structural, not bug-shaped.**
  Across BC1-BC3 the new diagnostics surfaced were all
  pre-existing patterns: `*_id` attribute access on FK fields,
  `objects` manager on model classes, `validated_data`
  subscript after `is_valid()`. None signaled a real bug.
  Future sessions can pre-emptively suppress these via a
  shared pyright config if the noise gets in the way.

## Anchor doc state at close

* Narrative anchor `docs/CHARACTER_OS_WHAT_IT_IS.md`: last
  revised 2026-05-20 (SESSION 206); not refreshed this
  session — the BC arc's narrative addition (composition arcs
  vs strategic-axis arcs) belongs in the SESSION 209 close
  update after BC5 ships.
* Runtime anchor `docs/CHARACTER_OS_INVENTORY.md`: regenerated
  this commit against HEAD `e76e173` to reflect BC1's new
  field + the BC3 endpoint.
* `00-START-NEXT-SESSION.md`: overwritten this commit to put
  BC5 as the SESSION 209 FIRST THING.

Status: **complete**. Five BC-arc slices shipped; backend
complete; SPA complete; real-mode dogfood queued for
SESSION 209.
