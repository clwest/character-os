---
title: "B-2 ↔ B-3 Composition — script-grounded personalized videos"
status: locked
proposed: 2026-05-20 (SESSION 208, slice BC0)
locked: 2026-05-20 (SESSION 208, slice BC0)
companion_docs:
  - AUTO_SCRIPTING_V1.md
  - PERSONALIZED_VIDEO_V1.md
  - VIDEO_COMPOSITION_V1.md
  - WORKSPACE_FABRIC_V1.md
  - CONTENT_FORMAT_BACKLOG.md
---

# B-2 ↔ B-3 Composition — script-grounded personalized videos

> **Status: PROPOSED (SESSION 208).** First composition arc.
> Connects two completed strategic-axis arcs (B-2 Auto-Scripting
> and B-3 Personalized Video) so per-recipient renders inherit
> the Script's knowledge lineage end-to-end. Nine contract rules;
> six slices BC0-BC5. Estimated 1-2 sessions to ship. Operator
> review + lock target: SESSION 208 (this session).

---

## TL;DR

The E-arc (auto-scripting, SESSION 207) and C-arc (personalized
video, SESSION 203) both shipped real-mode validated, but they
don't talk to each other. A Campaign's per-recipient renders are
vanilla `talking_head_polished` — F-arc brief-mode panel can't
show "drew from Nerva–Antonine dynasty (5 chunks)" because the
Composition's `knowledge_chunk_ids` field is empty. The Script's
K6.4-verified, citation-grounded draft is invisible past the
single-script render surface.

**This arc connects them.** A Campaign can optionally derive
from an approved Script. At launch, every per-recipient
Composition inherits the Script's `knowledge_chunk_ids` +
`synthesized_brief` (template-substituted per recipient) +
verification flags. Every personalized Asset surfaces the same
F-arc citation panel that individual Scripts already get.

The composition value is concrete:

* **Audit trail end-to-end**: query "all personalized videos
  derived from this Script" and "what Script grounds this
  Campaign" from either direction.
* **Per-recipient citation rendering**: F-arc brief-mode on every
  recipient Asset's detail page shows the source documents +
  chunk counts, not just the un-grounded talking-head template.
* **K6.4 verification carries**: if a Script was approved with
  informational warnings, every per-recipient Asset shows those
  same flags — the operator who reviewed the Script once doesn't
  re-review N times.
* **"Composition is the moat" framing**: the combinatorial
  product of two strategic axes (knowledge-grounded synthesis ×
  batched personalization) is structurally defensible. Generic
  LLM-video competitors can produce one or the other; only this
  stack ties them together.

This arc ships:

1. A **nullable FK** (`source_script`) on `PersonalizedCampaign`
   with `on_delete=PROTECT` + cross-workspace guard.
2. An **extended `talking_head_polished` starter** that accepts
   optional `knowledge_chunk_ids` / `synthesized_brief` /
   `verification_status` / `verification_warnings` kwargs and
   propagates them to the Composition row.
3. A **REST surface extension**: `POST /api/campaigns/` accepts
   `source_script_id`; copies `script.draft_text` → `template` at
   create time; launch path propagates Script lineage per
   recipient.
4. A **SPA picker** on `/workspace/campaigns/new` for choosing an
   approved Script as the starting template.
5. **One real-mode dogfood**: 2-recipient batch derived from
   SESSION 207's "Five Good Emperors" Script.

Out of scope for v1: re-verification of modified templates,
Script ↔ Campaign back-references on the Script side, regenerate-
Script-from-Campaign flows, A/B variants across Scripts, multi-
Script composition (one Campaign deriving from N Scripts).

---

## Why now

Five drivers converge:

1. **Both upstream arcs are real-mode validated.** B-2 closed
   SESSION 207 with $0.25 actual end-to-end; B-3 closed SESSION
   203 with $0.50 fan-out validated. The integration surface is
   no longer hypothetical — both sides have known-good shapes.
2. **The "composition is the moat" framing is concrete.** Per
   `00-START-NEXT-SESSION.md`, the highest-leverage SESSION 208
   candidate is exactly this composition. The combinatorial product
   of knowledge-grounded synthesis + batched personalization is
   the defensible feature.
3. **All required primitives exist.** No new Composition kinds,
   no new Asset semantics, no new tier dimensions. Pure integration
   work over established surfaces.
4. **F-arc brief-mode panel is operator-visible.** The per-
   recipient citation rendering pays off immediately in the SPA;
   no new UX surface needed beyond a Script picker.
5. **Scope-lock cadence is 5-for-5** (A/B/C/D/E). A 6-slice arc
   ships in 1-2 sessions per the established rhythm. Composition
   arcs are smaller than strategic-axis arcs by design —
   integration work over pre-validated surfaces.

---

## Contract rules (load-bearing)

Nine rules. None overlap V1's 22 (V1 ×9 + V17 ×4 + Asset Library
×9) or the B-arc ×8, C-arc ×9, B-2 (E-arc) ×10, B-14 ×9 rule
sets. Composition-arc rules don't claim V1 indexes; they live on
this doc.

1. **Script → Campaign is one-direction.** Campaign optionally
   derives from a Script; Script does NOT carry back-references
   to Campaigns. Discovery flows through the Campaign's FK only.
   This keeps Script-side schema clean and avoids a many-to-many
   maintenance surface.

2. **Template is editable after derivation.** Operator can
   modify the copied `draft_text` freely — add `{placeholders}`,
   rephrase, trim, expand. The `source_script` FK is audit trail,
   not constraint. The Campaign owns its `template` field after
   creation; subsequent Script regenerates don't update existing
   Campaigns.

3. **Workspace-isolated end-to-end.** `source_script.workspace
   == campaign.workspace`. Cross-workspace rejected at `clean()`
   + `pre_save` signal. Picker UX in SPA workspace-filters by
   construction. Mirrors V1 rule 1, C-arc rule 3, B-2 rule 1.

4. **Lineage propagates to every per-recipient Asset.** If
   `source_script` is set, every per-recipient `Composition` row
   gets `knowledge_chunk_ids` populated from the Script.
   Per-recipient Assets' F-arc brief-mode panel shows the same
   citation breakdown as the Script's detail page. **This is the
   load-bearing composition value.**

5. **Per-recipient `synthesized_brief` = template-substituted
   text.** At launch, each Composition gets `synthesized_brief =
   render_template(campaign.template, recipient.variables)`.
   Mirrors B-2's `trusted_passthrough` semantic: synthesis
   happened at Script draft time, K6 in-primitive is skipped per
   recipient (the rendered text IS the synthesized brief for that
   recipient).

6. **Script lineage snapshots at launch, not at create.** The
   `source_script` FK is set at create time; the per-Composition
   `knowledge_chunk_ids` + `synthesized_brief` + verification
   fields are populated from the Script at LAUNCH time, reading
   the current Script row state. If the operator regenerates the
   Script between Campaign-create and Campaign-launch, the launch
   uses the regenerated chunks. After launch, per-recipient
   Compositions are frozen (rule 6 of C-arc — recipients can't
   be edited post-launch).

7. **No new primitives or recipes.** Reuses
   `talking_head_polished`. Only the starter is extended with
   optional kwargs (defaults None = current behavior). No new
   Composition `template_kind`, no new starter, no new recipe
   gallery entry. The Composition row's `template_kind` stays
   `talking_head_polished` so the V-arc registry is unchanged.

8. **Verification flags propagate unchanged.** Per recipient,
   `Composition.verification_status` + `verification_warnings`
   are copied from the source Script at launch. The verifier
   does NOT re-run per recipient — recipient variables don't
   change K6's grounding, the rendered text is just a substituted
   surface. If the operator modified the template post-derivation
   in ways that would change verification (e.g. added an
   un-grounded claim), they accept the propagated flags as-is.
   Re-verification of modified templates is a v2 axis.

9. **`on_delete=PROTECT` on `source_script`.** A Script
   referenced by any non-DRAFT Campaign cannot be deleted. The
   operator must delete the referencing Campaign(s) first OR
   archive the Script (which leaves the FK intact and preserves
   the lineage). Prevents orphaned `synthesized_brief` /
   `knowledge_chunk_ids` propagation that would break F-arc
   brief-mode panel queries.

---

## Data model additions

### `apps.campaigns.models.PersonalizedCampaign` — one new field

| Field | Type | Notes |
|---|---|---|
| `source_script` | FK Script, null=True, blank=True, on_delete=PROTECT | new — optional derivation pointer (rule 9). |

All other fields unchanged. The existing `template` field
remains the operator-editable surface; `source_script` adds the
audit trail without changing how `template` flows through the
launch pipeline.

Migration: `apps.campaigns.migrations.0002_source_script` (single
new nullable FK; trivial). Cross-workspace pre_save signal
updated to also reject `source_script.workspace_id !=
workspace_id` when set.

### `apps.compositions.models.Composition` — zero schema change

Existing fields (`knowledge_chunk_ids`, `synthesized_brief`,
`verification_status`, `verification_warnings`) already cover the
propagation surface. Rule 7 keeps `template_kind=
talking_head_polished` unchanged.

### `apps.scripts.models.Script` — zero schema change

Rule 1 — Script doesn't know about Campaigns. No back-reference,
no FK, no `derived_campaign_count` denormalization. Discovery
queries flow through `PersonalizedCampaign.objects.filter(
source_script=script)`.

---

## New / extended endpoints

| Method | Path | Change |
|---|---|---|
| `POST` | `/api/campaigns/` | extend body: optional `source_script_id`. If provided, server fetches the Script (workspace-filtered), copies `draft_text` → `template`, persists the FK. Returns the row with FK + parsed placeholders. |
| `GET` | `/api/campaigns/<id>/` | extend response: include `source_script` block — `{id, name, status, verification_status, chunk_count}` — for SPA detail display. Workspace-filtered defense-in-depth (rule 3). |
| `POST` | `/api/campaigns/<id>/launch/` | unchanged shape; internal behavior extended — if `source_script` is set, propagate `knowledge_chunk_ids` + `synthesized_brief` (template-substituted) + verification fields onto each per-recipient Composition (rule 4 + 5 + 8). |
| `GET` | `/api/scripts/<id>/derived_campaigns/` | NEW. Workspace-filtered list of Campaigns that derive from this Script. For B-arc brief-mode + future Script-detail "Used by N campaigns" surface. v1 returns `[{id, name, status, recipient_count, created_at}]`. Paginated. |

The `/api/scripts/<id>/derived_campaigns/` endpoint is the only
new route. Rule 1 keeps the back-reference on the *query* side
(Campaign queries Script via FK), not the *schema* side (Script
has no Campaigns FK).

---

## Slice breakdown (6 slices, BC0-BC5)

| # | Slice | Effort |
|---|---|---|
| **BC0** | This scope-lock doc | ½ session (current) |
| **BC1** ✓ SHIPPED | Schema: `source_script` FK on PersonalizedCampaign (FK to Script, null=True, blank=True, on_delete=PROTECT, related_name='derived_campaigns') + migration `0002_bc1_source_script` + cross-workspace guard extended in both `clean()` + pre_save signal (added `source_script` to validated_fields). 5 model tests pin nullable default, FK + reverse_name round-trip, cross-workspace clean rejection, cross-workspace signal rejection, ProtectedError on Script delete when referenced. Django 1320 → 1325 (+5). Zero regressions. | ½ session |
| **BC2** ✓ SHIPPED | Extend `talking_head_polished` starter: 4 optional kwargs (`knowledge_chunk_ids` / `synthesized_brief` / `verification_status` / `verification_warnings`) propagate to the Composition row when supplied. Defaults None = current behavior; existing C-arc + recipe-gallery callers unchanged. **Q-bc-7 resolved as-proposed** (warnings JSON is COPIED onto every per-recipient Composition, not joined-through-FK). Defensive `list(...)` copies prevent aliasing. 7 new starter tests pin: back-compat no-kwargs, each kwarg individually, all four together (load-bearing BC3 shape), defensive-copy semantic. Django 1325 → 1332 (+7). Zero regressions across the 1325 baseline (existing 14 polished-starter tests + 75 C-arc tests + 100+ V-arc tests still green). | ½ session |
| **BC3** | REST: `POST /api/campaigns/` accepts `source_script_id` (workspace-filtered Script fetch + draft_text copy + FK persist). Launch path propagates Script lineage per recipient (rule 4 + 5 + 8). New `GET /api/scripts/<id>/derived_campaigns/` action on `ScriptViewSet`. 8-10 REST tests. | ½-1 session |
| **BC4** | SPA: "Use approved Script as starting template" picker on `/workspace/campaigns/new`. Workspace + spokesperson filter. Script preview pane (draft_text + chunk count). "Use as template" pre-fills the textarea + sets `source_script_id` in the create payload. Script detail page gains "Used by N campaigns" badge (links to derived_campaigns list). 10-12 vitest tests. | 1 session (subagent candidate). |
| **BC5** | Real-mode dogfood + arc close. 2-recipient batch derived from SESSION 207's "Five Good Emperors" Script. Validate: per-recipient Composition.knowledge_chunk_ids matches Script's; per-recipient Asset F-arc brief-mode panel shows citations; verification warnings carry over. Close the arc. | ½ session |

Total: ~2 sessions (BC0+BC1+BC2 in session A; BC3+BC4 in session
B; BC5 either same as B or follows). Smaller than strategic-axis
arcs because no new primitives, recipes, or major UI surfaces —
this is pure integration over pre-validated layers.

---

## In-scope clarifications

* **Script copy is one-shot at create time.** Once
  `template` is populated, the Campaign owns the text. Subsequent
  Script regenerates do NOT update existing Campaigns. The
  operator who wants a fresh template re-creates the Campaign.

* **Lineage propagation is at launch time** (rule 6). The
  per-recipient Composition reads the Script's CURRENT
  `knowledge_chunk_ids` + `verification_*` fields at launch. If
  the Script was regenerated between Campaign-create and
  Campaign-launch, the launch uses the regenerated lineage. After
  launch, the per-recipient Composition is frozen.

* **`template` and `source_script.draft_text` can drift.** The
  operator's edits to `template` post-derivation are honored
  verbatim. The F-arc brief-mode panel on per-recipient Assets
  shows the Script's chunks (rule 4), even if the operator
  rephrased the template substantially. This is consistent with
  B-2 rule 8's "verification ran at draft time" semantic — the
  operator vouches for the template's grounding at launch time.

* **`source_script_id` accepts any READY Script in the
  workspace.** No spokesperson-match requirement at the API
  layer (the campaign and Script can have different
  spokespeople — operator may want to use one persona's
  knowledge with another persona's voice). SPA picker filters by
  spokesperson by default (Q-bc-4) but can be widened via a
  toggle.

* **`derived_campaigns` query is workspace-scoped + paginated**
  per V1 rule 1.

---

## Out of scope (v1)

* **Re-verification of modified templates.** Operator-edited
  templates carry the Script's K6.4 flags unchanged. If they
  wanted re-grounded text, they'd regenerate the Script and
  re-derive a Campaign. v2 axis.

* **Script ↔ Campaign back-references on Script model.** Rule 1.
  Queries flow through Campaign's FK only. No
  `Script.campaign_count` denormalization, no FK on Script.

* **Multi-Script composition.** One Campaign = at most one
  `source_script`. Composing N Scripts into one Campaign
  template is a v2 axis.

* **A/B variants across Scripts.** "Send half the recipients
  Script v1, half Script v2" is a B-3-extension axis, not part
  of this composition arc.

* **Personalized regenerate.** Operator can't regenerate the
  Script-derived template per recipient. Either the entire
  Campaign uses the derived template or none of it does.

* **Per-recipient verification override.** Rule 8. Verification
  flags propagate unchanged to all recipients; operator can't
  selectively suppress flags for specific recipients.

* **Script archival auto-deletes Campaigns.** Rule 9 — Script
  archival leaves the FK intact for audit; Campaigns derived
  from archived Scripts remain functional (template + lineage
  are already snapshotted).

* **F-arc brief-mode panel on the Campaign list page itself.**
  v1 surfaces citations on per-recipient Asset detail pages only.
  Aggregating across all recipients into a Campaign-level "drew
  from these docs" panel is a v2 polish slice.

---

## Open questions (resolve in slices)

* **Q-bc-1**: `on_delete` semantic for `source_script` FK.
  **Proposed**: `PROTECT` (rule 9). Operator must explicitly
  delete referencing Campaigns before deleting the Script.
  Alternative `SET_NULL` would orphan the lineage and break
  F-arc brief-mode queries silently. Resolve at BC1.

* **Q-bc-2**: Launch behavior when `source_script.status` is
  ARCHIVED. **Proposed**: launch reads `draft_text` +
  `knowledge_chunk_ids` from the FK at launch time regardless of
  Script status. Archive is an organizational flag, not a
  functional kill switch. If Script is RENDERED (B-2 rule 10
  immutability), same semantic — RENDERED Scripts can ground
  Campaigns just like READY ones. Resolve at BC3.

* **Q-bc-3**: Can `source_script` be modified after Campaign
  creation? **Proposed**: no — `source_script` is set at create
  time and immutable thereafter. To switch Scripts, operator
  creates a new Campaign. (Mirrors C-arc's "recipients can't
  be edited post-launch" semantic; here it's "source_script
  can't be edited post-create.") Resolve at BC3.

* **Q-bc-4**: SPA picker UX — show all workspace READY Scripts
  or only those matching the Campaign's spokesperson? **Proposed**:
  filter by Campaign.spokesperson by default + a toggle to show
  all workspace Scripts. Most operators will want persona
  consistency (Marcus's knowledge on Marcus's videos), but cross-
  persona derivation (use Sasha's Roman-history Script with
  Marcus's voice) is a valid edge case. Resolve at BC4.

* **Q-bc-5**: What if the operator clicks "Use as template" but
  then heavily edits the template? **Proposed**: no warning, no
  re-prompt. The FK is audit trail, not constraint (rule 2).
  Operator owns the text. F-arc brief-mode panel will still show
  the Script's chunks (rule 4) — that's a feature, not a bug
  (the audit shows what the Campaign DERIVED FROM, not what the
  current template literally claims). Resolve at BC4.

* **Q-bc-6**: How does the launch path handle the optional
  kwargs in `talking_head_polished` starter — extend the
  function signature with defaults, or add a new wrapper starter?
  **Proposed**: extend in place with `Optional[...] = None`
  defaults (rule 7). Adding a wrapper would duplicate the
  primitives setup. The starter's existing tests pass with the
  defaults unchanged. Resolve at BC2.

* **Q-bc-7**: `verification_warnings` serialization on
  per-recipient Composition. Each per-recipient render is a
  separate Composition row; do all N rows carry the same
  warnings JSON, or should warnings live only on the source
  Script? **Proposed**: all N rows carry a *copy* of the
  warnings JSON, because the F-arc brief-mode panel renders from
  the Composition row, not the source Script. Storage cost is
  trivial (warnings JSON is typically small); the alternative
  would require a join through `source_script` on every panel
  render. Resolve at BC2.

* **Q-bc-8**: Default for the SPA picker's "use as template" —
  does it pre-fill placeholder hints (e.g.
  `{first_name}` at the top of the textarea) or just copy
  `draft_text` verbatim? **Proposed**: verbatim copy. The
  operator knows what placeholders they want; pre-filling would
  inject decisions about the personalization shape. Resolve at
  BC4.

* **Q-bc-9**: `derived_campaigns` endpoint pagination + status
  filter. **Proposed**: standard DRF pagination + optional
  `?status=` filter (mirrors `/api/campaigns/` shape). Resolve
  at BC3.

---

## Change log

* **2026-05-20 (SESSION 208, slice BC0)** — Initial scope
  proposal. First composition arc. Connects the closed E-arc
  (B-2 Auto-Scripting, SESSION 207) and C-arc (B-3 Personalized
  Video, SESSION 203) via a nullable FK on
  `PersonalizedCampaign` + lineage propagation in the launch
  path. Nine contract rules; six slices BC0-BC5. Nine open
  questions all proposed with default resolutions; awaiting
  operator sign-off to lock.

* **2026-05-20 (SESSION 208, BC0 LOCKED)** — Operator signed
  off as-proposed. All 9 contract rules accepted without
  revision. All 9 open questions accepted with proposed
  resolutions. Status flips proposed → locked. BC1
  (`source_script` FK + migration + workspace guard + 5 model
  tests) opens immediately.

* **2026-05-20 (SESSION 208, BC1 SHIPPED)** — Schema slice
  lands. `PersonalizedCampaign.source_script: FK(Script,
  null=True, blank=True, on_delete=PROTECT,
  related_name='derived_campaigns')`. Migration
  `0002_bc1_source_script` (single AddField). Workspace guard
  extended at two layers: `PersonalizedCampaign.clean()` now
  checks `source_script.workspace_id == workspace_id` when
  source_script is set, mirroring the existing spokesperson
  check shape; pre_save signal's `validated_fields` set picks
  up `source_script` so partial-update saves still trigger
  the workspace check when the FK changes. **Q-bc-1
  resolved as-proposed** (PROTECT, not SET_NULL). 5 BC1 model
  tests pin: nullable default; FK + reverse-name
  (`script.derived_campaigns.all()`) round-trip per rule 1;
  cross-workspace rejection at clean(); cross-workspace
  rejection at signal; ProtectedError raises when a referenced
  Script is deleted. Full Django suite 1320 → 1325 (+5); zero
  regressions across the 1320 baseline. BC2 (extend
  `talking_head_polished` starter with optional
  `knowledge_chunk_ids` / `synthesized_brief` /
  `verification_status` / `verification_warnings` kwargs)
  opens next.

* **2026-05-20 (SESSION 208, BC2 SHIPPED)** — Starter
  extension slice lands. `talking_head_polished()` gains four
  optional kwargs (all default None). When supplied, they
  propagate to the freshly-created `Composition` row via a
  conditional kwarg-assembly pattern — existing callers that
  omit them see no behavior change (Composition's
  `knowledge_chunk_ids` stays `[]`, `synthesized_brief` stays
  `""`, etc.). Defensive `list(...)` copies on the
  `knowledge_chunk_ids` + `verification_warnings` inputs
  prevent post-call mutation by the caller from leaking into
  the persisted row. **Q-bc-7 resolved as-proposed** (per-
  Composition warnings copy, not join-through-FK). 7 starter
  tests cover: back-compat (no kwargs → empty fields); each
  of the 4 kwargs individually; all 4 together (the load-
  bearing BC3 launch-path shape); defensive-copy semantic.
  Django 1325 → 1332 (+7); zero regressions. BC3 (REST:
  `POST /api/campaigns/` accepts `source_script_id` + launch-
  path lineage propagation + new
  `GET /api/scripts/<id>/derived_campaigns/`) opens next.
